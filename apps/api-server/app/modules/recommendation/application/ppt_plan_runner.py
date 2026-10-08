"""Token-bounded Type-5 plan composition over an immutable candidate snapshot."""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from decimal import Decimal, InvalidOperation

from app.core.config import Settings, get_settings
from app.integrations.deepseek.client import (
    DeepSeekConfigurationError,
    DeepSeekStructuredOutputError,
)
from app.modules.recommendation.application.agent_runner import (
    RecommendationAgentContractError,
    StructuredProvider,
)
from app.modules.recommendation.infrastructure.models import RecommendationCandidate
from app.modules.recommendation.ppt_schemas import (
    PptFrozenRecommendationConfig,
    PptPlanProposalList,
    PptPriceBandInput,
)

logger = logging.getLogger(__name__)


class PptPlanAgentRunner:
    """Let AI choose seeds from a bounded window; never transmit real UUIDs.

    Character/token conversion deliberately overestimates (four characters per
    token) because no provider tokenizer is available in the local-first runtime.
    The complete pool remains frozen in MySQL and fills the remaining positions.
    """

    MAX_PROVIDER_ATTEMPTS = 2

    def __init__(self, provider: StructuredProvider, settings: Settings | None = None) -> None:
        self.provider = provider
        self.settings = settings or get_settings()

    async def run(
        self, config: PptFrozenRecommendationConfig, candidates: list[RecommendationCandidate]
    ) -> PptPlanProposalList:
        plans = []
        for index, band in enumerate(config.price_bands, 1):
            if len(self.band_candidates(band, candidates)) >= config.candidate_count_per_band:
                plans.extend((await self.run_band(index, band, config, candidates)).plans)
        return PptPlanProposalList(plans=plans)

    async def run_band(
        self,
        index: int,
        band: PptPriceBandInput,
        config: PptFrozenRecommendationConfig,
        candidates: list[RecommendationCandidate],
    ) -> PptPlanProposalList:
        eligible = self.band_candidates(band, candidates)
        if len(eligible) < config.candidate_count_per_band:
            return PptPlanProposalList()
        window, key_map = self._window(eligible)
        seed_count = min(config.candidate_count_per_band, self.settings.ppt_ai_seed_count_per_plan)
        payload = json.dumps(
            {
                "price_band_index": index,
                "recommendation_mode": config.recommendation_mode,
                "items_per_plan": config.candidate_count_per_band,
                "plans_per_band": config.plan_count_per_band,
                "seed_count_limit": seed_count,
                "candidate_window_count": len(window),
                "candidates": window,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        retry_note = ""
        for attempt in range(self.MAX_PROVIDER_ATTEMPTS):
            try:
                result = await self.provider.structured_completion(
                    system_prompt=(
                        "你是类型 5 PPT 商品方案编排助手。只能从 candidates 中返回 server-issued "
                        "short candidate_keys（例如 c1），绝不能生成 UUID、商品或清单外 key。"
                        f"每张方案仅选择 1 到 {seed_count} 个不重复核心商品；"
                        "服务器会从完整合格池补齐剩余数量。返回严格 JSON。"
                    ),
                    user_prompt=f"{payload}{retry_note}",
                    response_model=PptPlanProposalList,
                    max_tokens=min(
                        self.settings.ppt_ai_output_token_budget, self.settings.deepseek_max_tokens
                    ),
                )
            except DeepSeekConfigurationError:
                raise
            except DeepSeekStructuredOutputError as exc:
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
                logger.warning(
                    "ppt token-safe plan schema retry band=%s validation=%s",
                    index,
                    exc.safe_validation_summary,
                )
                retry_note = (
                    "\n上一次输出未通过 JSON Schema 校验。请仅重新输出合法 JSON；"
                    f"脱敏错误：{exc.safe_validation_summary}"
                )
                continue

            for proposal in result.plans:
                if proposal.price_band_index != index or any(
                    key not in key_map for key in proposal.candidate_keys
                ):
                    raise RecommendationAgentContractError("类型 5 方案 AI 返回了清单外商品")
            return result
        raise RecommendationAgentContractError("类型 5 AI 未返回可用方案")

    def window_key_map(
        self, candidates: list[RecommendationCandidate]
    ) -> dict[str, RecommendationCandidate]:
        """Rebuild the deterministic short-key mapping used for one AI window."""
        return self._window(candidates)[1]

    def _window(
        self, candidates: list[RecommendationCandidate]
    ) -> tuple[list[dict[str, object]], dict[str, RecommendationCandidate]]:
        buckets: dict[tuple[str, str], deque[RecommendationCandidate]] = defaultdict(deque)
        for candidate in candidates:
            product = candidate.product_snapshot
            buckets[
                (str(product.get("category_level3_name") or ""), str(product.get("brand") or ""))
            ].append(candidate)
        ordered = deque(sorted(buckets))
        selected: list[RecommendationCandidate] = []
        limit_chars = max(800, int(self.settings.ppt_ai_input_token_budget * 4 * 0.65))
        total_chars = 2
        while ordered:
            bucket = ordered.popleft()
            candidate = buckets[bucket].popleft()
            row_size = (
                len(
                    json.dumps(
                        self._row(f"c{len(selected) + 1}", candidate),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                )
                + 1
            )
            if selected and total_chars + row_size > limit_chars:
                break
            selected.append(candidate)
            total_chars += row_size
            if buckets[bucket]:
                ordered.append(bucket)
        if not selected:
            raise RecommendationAgentContractError("类型 5 AI 请求预算不足，无法构造候选窗口")
        key_map = {f"c{index}": candidate for index, candidate in enumerate(selected, 1)}
        return [self._row(key, candidate) for key, candidate in key_map.items()], key_map

    @staticmethod
    def _row(key: str, candidate: RecommendationCandidate) -> dict[str, object]:
        product = candidate.product_snapshot
        return {
            "id": key,
            "name": product.get("product_name"),
            "brand": product.get("brand"),
            "price": str(candidate.price_snapshot.get("agreement_price")),
            "category": product.get("category_level3_name"),
        }

    @classmethod
    def band_candidates(
        cls, band: PptPriceBandInput, candidates: list[RecommendationCandidate]
    ) -> list[RecommendationCandidate]:
        minimum, maximum = band.min_price, band.max_price
        return [
            candidate
            for candidate in candidates
            if (price := cls._decimal(candidate.price_snapshot.get("agreement_price"))) is not None
            and price <= maximum
            and (minimum is None or price >= minimum)
        ]

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        try:
            return Decimal(str(value)) if value is not None else None
        except (InvalidOperation, TypeError):
            return None
