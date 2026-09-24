import json
from collections.abc import Sequence
from uuid import UUID

from app.modules.recommendation.application.agent_runner import RecommendationTools
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    CategoryOption,
    ProductCandidate,
    ProductSearchRequest,
    RequirementAnalysis,
)
from app.modules.recommendation.application.service import RecommendationService
from app.modules.recommendation.schemas import (
    CandidateRankInput,
    CategoryChoiceInput,
    CategoryPath,
    ParsedRequirement,
    PersistCandidatesRequest,
)
from app.modules.recommendation.template.schemas import RecommendationRunStatus


def encode_category_key(path: CategoryPath) -> str:
    return json.dumps(
        [path.level1_name, path.level2_name, path.level3_name],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def decode_category_key(value: str) -> CategoryPath:
    try:
        parts = json.loads(value)
        if not isinstance(parts, list) or len(parts) != 3:
            raise ValueError
        return CategoryPath(
            level1_name=parts[0], level2_name=parts[1], level3_name=parts[2]
        )
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid controlled category key") from exc


class RecommendationServiceTools(RecommendationTools):
    """C Agent tools implemented only through B's public application service."""

    def __init__(
        self,
        run_id: UUID,
        service: RecommendationService,
        *,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> None:
        self.run_id = run_id
        self.service = service
        self.provider = provider
        self.model = model
        self.prompt_version = prompt_version

    async def prepare(self, analysis: RequirementAnalysis) -> None:
        await self.service.begin_analysis(self.run_id)
        await self.service.save_parsed_requirement(
            self.run_id,
            ParsedRequirement(
                gross_margin_min=analysis.gross_margin_min,
                jd_price_min=analysis.budget_min,
                jd_price_max=analysis.budget_max,
                category_keywords=analysis.category_keywords,
                brand_keywords=analysis.required_brands,
                scenario_keywords=analysis.scenarios,
                explicit_category_keywords=analysis.explicit_category_keywords,
                category_intents=analysis.category_intents,
                excluded_category_keywords=analysis.excluded_category_keywords,
                required_brands=analysis.required_brands,
                preferred_brands=analysis.preferred_brands,
                excluded_brands=analysis.excluded_brands,
                search_keywords=analysis.search_keywords or analysis.keywords,
                scenarios=analysis.scenarios,
                promotion_preference=analysis.promotion_preference,
                demand_mode=analysis.demand_mode,
                quantity=analysis.quantity,
                fulfillment_mode=analysis.fulfillment_mode,
                manual_checks=analysis.manual_checks,
            ),
            provider=self.provider,
            model=self.model,
            prompt_version=self.prompt_version,
        )

    async def list_categories(
        self, keywords: Sequence[str], *, limit: int
    ) -> list[CategoryOption]:
        del keywords
        pool = await self.service.category_pool(self.run_id)
        return [
            CategoryOption(
                key=encode_category_key(item),
                level1=item.level1_name,
                level2=item.level2_name,
                level3=item.level3_name,
                product_count=item.candidate_count,
            )
            for item in pool[:limit]
        ]

    async def search_products(self, request: ProductSearchRequest) -> list[ProductCandidate]:
        rows = await self.service.search_products(
            self.run_id,
            [decode_category_key(request.category_key)],
            keywords=request.keywords,
            preferred_brands=request.preferred_brands,
        )
        return [
            ProductCandidate(
                product_id=row.product_id,
                product_name=row.product_name,
                brand=row.brand,
                category_path=row.category_path,
                agreement_price=row.agreement_price,
                jd_price=row.jd_price,
                gross_margin=row.gross_margin,
                discount_rate=row.discount_rate,
                sales_volume=row.sales_volume,
                positive_rating=row.positive_rating,
                selling_points=(row.selling_points or "")[:1000] or None,
                shipping_courier=row.shipping_courier,
                highlights=[
                    value
                    for value in (row.sku, row.shipping_courier)
                    if value
                ],
            )
            for row in rows
            if row.product_name
        ][: request.limit]


class RecommendationServiceJobPort:
    def __init__(self, service: RecommendationService) -> None:
        self.service = service

    async def requirement_for(self, run_id: UUID) -> str:
        return (await self.service.get_run(run_id)).raw_requirement_snapshot

    async def is_cancelled(self, run_id: UUID) -> bool:
        return (await self.service.get_run(run_id)).status == RecommendationRunStatus.CANCELLED

    async def record_progress(
        self, run_id: UUID, status: str, percent: int, message: str
    ) -> None:
        del run_id, status, percent, message

    async def complete(self, run_id: UUID, result: AgentRecommendationResult) -> None:
        if result.analysis.needs_input:
            await self.service.begin_analysis(run_id)
            await self.service.mark_needs_input(run_id, "；".join(result.analysis.questions))
            return
        if not result.candidates:
            await self.service.mark_no_candidates(run_id)
            return
        await self.service.record_category_choices(
            run_id,
            [
                CategoryChoiceInput(
                    **decode_category_key(choice.category_key).model_dump(),
                    source="AI",
                    reason=choice.reason,
                )
                for choice in result.category_choices
            ],
        )
        candidates = result.candidates[:30]
        await self.service.persist_ranked_candidates(
            run_id,
            PersistCandidatesRequest(
                candidates=[
                    CandidateRankInput(
                        product_id=item.product_id,
                        rank=index,
                        score=item.score,
                        reason=item.reason,
                    )
                    for index, item in enumerate(candidates, start=1)
                ]
            ),
        )

    async def fail(self, run_id: UUID, safe_error: str) -> None:
        await self.service.mark_failed(run_id, safe_error)

    async def cancelled(self, run_id: UUID) -> None:
        await self.service.mark_cancelled(run_id)
