"""Type-5-only AI proposal composer over an immutable candidate snapshot."""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.integrations.deepseek.client import (
    DeepSeekConfigurationError,
    DeepSeekStructuredOutputError,
)
from app.modules.recommendation.application.agent_runner import (
    RecommendationAgentContractError,
    StructuredProvider,
)
from app.modules.recommendation.infrastructure.models import (
    PptRecommendationConfig,
    RecommendationCandidate,
)
from app.modules.recommendation.ppt_schemas import (
    PptPlanProposal,
    PptPlanProposalList,
    PptPlanReferenceProposal,
)

logger = logging.getLogger(__name__)


class PptPlanAgentRunner:
    """The model composes plans; it never searches products or invents IDs."""

    MAX_PROVIDER_ATTEMPTS = 2
    # This is a provider-transport guard for one *price band*, rather than a
    # business cap on the complete Type-5 candidate pool.  A run may freeze
    # thousands of valid products; only products in the band being composed
    # are sent in that request.
    MAX_CANDIDATES_PER_PRICE_BAND = 5000

    def __init__(self, provider: StructuredProvider) -> None:
        self.provider = provider

    async def run(
        self, config: PptRecommendationConfig, candidates: list[RecommendationCandidate]
    ) -> PptPlanProposalList:
        plans: list[PptPlanProposal] = []
        for index, band in enumerate(config.price_bands, 1):
            eligible_candidates = self._band_candidates(band, candidates)
            payload, reference_map = self._band_payload(index, band, eligible_candidates)
            payload_candidates = payload["candidates"]
            if not isinstance(payload_candidates, list):
                raise RecommendationAgentContractError("类型 5 价格档候选数据格式异常")
            count = len(payload_candidates)
            if count < config.candidate_count_per_band:
                continue
            if count > self.MAX_CANDIDATES_PER_PRICE_BAND:
                label = self._band_label(band)
                raise RecommendationAgentContractError(
                    f"价格档 {label} 有 {count} 件候选商品，超过单个价格档可编排的 "
                    f"{self.MAX_CANDIDATES_PER_PRICE_BAND} 件上限，请拆分价格档后重新生成。"
                )
            previous_selections: set[frozenset[str]] = set()
            for plan_no in range(1, config.plan_count_per_band + 1):
                result = await self._compose_plan(
                    config=config,
                    price_band=payload,
                    plan_no=plan_no,
                    reference_map=reference_map,
                    previous_selections=previous_selections,
                )
                selected_refs = frozenset(result.candidate_refs)
                previous_selections.add(selected_refs)
                plans.append(
                    PptPlanProposal(
                        price_band_index=index,
                        plan_no=plan_no,
                        name=result.name,
                        summary=result.summary,
                        candidate_ids=[reference_map[value] for value in result.candidate_refs],
                    )
                )
        return PptPlanProposalList(plans=plans)

    @classmethod
    def _band_payload(
        cls,
        index: int,
        band: dict[str, object],
        candidates: list[RecommendationCandidate],
    ) -> tuple[dict[str, object], dict[str, UUID]]:
        reference_map: dict[str, UUID] = {}
        values: list[list[str | None]] = []
        for position, candidate in enumerate(candidates, start=1):
            reference = f"P{position:04d}"
            reference_map[reference] = candidate.id
            product = candidate.product_snapshot
            price = cls._decimal(candidate.price_snapshot.get("agreement_price"))
            values.append(
                [
                    reference,
                    cls._prompt_text(product.get("product_name"), 160),
                    cls._prompt_text(product.get("brand"), 80),
                    cls._prompt_text(product.get("product_specification"), 160),
                    str(price) if price is not None else None,
                    cls._prompt_text(product.get("category_level3_name"), 120),
                ]
            )
        return (
            {
                "price_band_index": index,
                "min_price": band.get("min_price"),
                "max_price": band.get("max_price"),
                "candidate_columns": [
                    "candidate_ref",
                    "product_name",
                    "brand",
                    "specification",
                    "agreement_price",
                    "category",
                ],
                "candidates": values,
            },
            reference_map,
        )

    @classmethod
    def _band_candidates(
        cls, band: dict[str, object], candidates: list[RecommendationCandidate]
    ) -> list[RecommendationCandidate]:
        minimum = cls._decimal(band.get("min_price"))
        maximum = cls._decimal(band.get("max_price"))
        if maximum is None:
            return []
        return [
            candidate
            for candidate in candidates
            if (price := cls._decimal(candidate.price_snapshot.get("agreement_price")))
            is not None
            and price <= maximum
            and (minimum is None or price >= minimum)
        ]

    async def _compose_plan(
        self,
        *,
        config: PptRecommendationConfig,
        price_band: dict[str, object],
        plan_no: int,
        reference_map: dict[str, UUID],
        previous_selections: set[frozenset[str]],
    ) -> PptPlanReferenceProposal:
        base_payload = json.dumps(
            {
                "recommendation_mode": config.recommendation_mode,
                "items_per_plan": config.candidate_count_per_band,
                "plan_no": plan_no,
                "price_band": price_band,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        retry_note = ""
        last_structured_error: DeepSeekStructuredOutputError | None = None
        for attempt in range(self.MAX_PROVIDER_ATTEMPTS):
            try:
                result = await self.provider.structured_completion(
                    system_prompt=(
                        "你是类型 5 PPT 商品方案编排助手。只能使用 price_band.candidates 中的 "
                        "candidate_ref，不得返回 SKU、供应商、商品详情或数据库 ID。"
                        "必须返回恰好 items_per_plan 个不重复 candidate_ref。"
                        "SINGLE、COMBINATION、MIXED 的方案类型由服务器决定，不要输出类型字段。"
                        "方案应与同价格档的其他方案尽量不同。严格返回 JSON。"
                    ),
                    user_prompt=f"{base_payload}{retry_note}",
                    response_model=PptPlanReferenceProposal,
                )
            except DeepSeekConfigurationError:
                raise
            except DeepSeekStructuredOutputError as exc:
                last_structured_error = exc
                if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                    raise
                logger.warning(
                    "ppt plan schema retry plan_no=%s validation=%s",
                    plan_no,
                    exc.safe_validation_summary,
                )
                retry_note = (
                    "\n上一次输出未通过 JSON Schema 校验。请仅重新输出合法 JSON；"
                    f"脱敏错误：{exc.safe_validation_summary}"
                )
                continue

            unknown = [value for value in result.candidate_refs if value not in reference_map]
            selected_refs = result.candidate_refs[: config.candidate_count_per_band]
            duplicate_plan = frozenset(selected_refs) in previous_selections
            if not unknown and not duplicate_plan:
                if len(result.candidate_refs) != config.candidate_count_per_band:
                    logger.warning(
                        "ppt plan quantity differs from target plan_no=%s target=%s actual=%s "
                        "persisted=%s",
                        plan_no,
                        config.candidate_count_per_band,
                        len(result.candidate_refs),
                        len(selected_refs),
                    )
                return result.model_copy(update={"candidate_refs": selected_refs})
            if attempt + 1 == self.MAX_PROVIDER_ATTEMPTS:
                reasons = []
                if unknown:
                    reasons.append("包含未知商品引用")
                if duplicate_plan:
                    reasons.append("与已有方案完全重复")
                raise RecommendationAgentContractError(
                    f"类型 5 第 {plan_no} 个方案{'、'.join(reasons)}"
                )
            retry_note = (
                "\n上一次方案未通过后端校验。请重新编排：只能使用清单中的 candidate_ref，"
                "且不能与已有方案完全相同。"
            )
        if last_structured_error is not None:
            raise last_structured_error
        raise RecommendationAgentContractError(f"类型 5 第 {plan_no} 个方案编排失败")

    @classmethod
    def _band_label(cls, band: dict[str, object]) -> str:
        minimum = cls._decimal(band.get("min_price"))
        maximum = cls._decimal(band.get("max_price"))
        lower = minimum if minimum is not None else 0
        upper = maximum if maximum is not None else "?"
        return f"{lower}～{upper} 元"

    @staticmethod
    def _decimal(value: object) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            return None

    @staticmethod
    def _prompt_text(value: object, limit: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text[:limit] if text else None
