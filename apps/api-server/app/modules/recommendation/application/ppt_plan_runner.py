"""Type-5-only AI proposal composer over an immutable candidate snapshot."""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from app.modules.recommendation.application.agent_runner import (
    RecommendationAgentContractError,
    StructuredProvider,
)
from app.modules.recommendation.infrastructure.models import (
    PptRecommendationConfig,
    RecommendationCandidate,
)
from app.modules.recommendation.ppt_schemas import PptPlanProposal, PptPlanProposalList


class PptPlanAgentRunner:
    """The model composes plans; it never searches products or invents IDs."""

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
            payload = self._band_payload(index, band, candidates)
            band_candidates = payload["candidates"]
            if not isinstance(band_candidates, list):
                raise RecommendationAgentContractError("类型 5 价格档候选数据格式异常")
            count = len(band_candidates)
            if count < config.candidate_count_per_band:
                continue
            if count > self.MAX_CANDIDATES_PER_PRICE_BAND:
                label = self._band_label(band)
                raise RecommendationAgentContractError(
                    f"价格档 {label} 有 {count} 件候选商品，超过单个价格档可编排的 "
                    f"{self.MAX_CANDIDATES_PER_PRICE_BAND} 件上限，请拆分价格档后重新生成。"
                )
            result = await self.provider.structured_completion(
                system_prompt=(
                    "你是类型 5 PPT 商品方案编排助手。只能使用 price_band 中给出的 candidate_id，"
                    "不得新增、遗漏校验规则或使用其他商品。每张方案必须恰好包含 "
                    "items_per_plan 个不重复 candidate_id。SINGLE、COMBINATION、MIXED 的方案类型由"
                    "服务器决定，不要输出类型字段。返回严格 JSON。"
                ),
                user_prompt=json.dumps(
                    {
                        "recommendation_mode": config.recommendation_mode,
                        "items_per_plan": config.candidate_count_per_band,
                        "plans_per_band": config.plan_count_per_band,
                        "price_band": payload,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                response_model=PptPlanProposalList,
            )
            plans.extend(result.plans)
        return PptPlanProposalList(plans=plans)

    @classmethod
    def _band_payload(
        cls, index: int, band: dict[str, object], candidates: list[RecommendationCandidate]
    ) -> dict[str, object]:
        minimum = cls._decimal(band.get("min_price"))
        maximum = cls._decimal(band.get("max_price"))
        values: list[dict[str, object]] = []
        if maximum is not None:
            for candidate in candidates:
                price = cls._decimal(candidate.price_snapshot.get("agreement_price"))
                if price is None or price > maximum or (minimum is not None and price < minimum):
                    continue
                product = candidate.product_snapshot
                values.append(
                    {
                        "candidate_id": str(candidate.id),
                        "product_name": product.get("product_name"),
                        "brand": product.get("brand"),
                        "specification": product.get("product_specification"),
                        "agreement_price": str(price),
                        "category": product.get("category_level3_name"),
                    }
                )
        return {
            "price_band_index": index,
            "min_price": band.get("min_price"),
            "max_price": band.get("max_price"),
            "candidates": values,
        }

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
