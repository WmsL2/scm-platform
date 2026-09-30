import json
from collections.abc import Sequence
from uuid import UUID

from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    CategoryOption,
    RequirementAnalysis,
)
from app.modules.recommendation.application.ppt_selection_runner import (
    PptRecommendationTools,
)
from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.application.service import RecommendationService
from app.modules.recommendation.schemas import CategoryChoiceInput, CategoryPath, ParsedRequirement
from app.modules.recommendation.template.schemas import RecommendationRunStatus


def _encode(path: CategoryPath) -> str:
    return json.dumps(
        [path.level1_name, path.level2_name, path.level3_name],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _decode(value: str) -> CategoryPath:
    parts = json.loads(value)
    if not isinstance(parts, list) or len(parts) != 3:
        raise ValueError("invalid controlled category key")
    return CategoryPath(level1_name=parts[0], level2_name=parts[1], level3_name=parts[2])


class PptSelectionServiceTools(PptRecommendationTools):
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
        await self.service.ppt_recommendation_config_for_run(self.run_id)
        brands = list(dict.fromkeys([*analysis.preferred_brands, *analysis.required_brands]))
        await self.service.begin_analysis(self.run_id)
        await self.service.save_parsed_requirement(
            self.run_id,
            ParsedRequirement(
                requirement_version="ppt-v1",
                gross_margin_min=analysis.gross_margin_min,
                gross_margin_max=analysis.gross_margin_max,
                agreement_price_min=analysis.agreement_price_min or analysis.budget_min,
                agreement_price_max=analysis.agreement_price_max or analysis.budget_max,
                jd_price_min=analysis.jd_price_min,
                jd_price_max=analysis.jd_price_max,
                discount_rate_min=analysis.discount_rate_min,
                discount_rate_max=analysis.discount_rate_max,
                category_keywords=analysis.category_keywords,
                brand_keywords=brands,
                scenario_keywords=analysis.scenarios,
                category_intents=analysis.category_intents,
                excluded_category_keywords=analysis.excluded_category_keywords,
                required_brands=analysis.required_brands,
                preferred_brands=brands,
                excluded_brands=analysis.excluded_brands,
                search_keywords=analysis.search_keywords or analysis.keywords,
                scenarios=analysis.scenarios,
                promotion_preference=analysis.promotion_preference,
                demand_mode=analysis.demand_mode,
                quantity=analysis.quantity,
                fulfillment_mode=analysis.fulfillment_mode,
            ),
            provider=self.provider,
            model=self.model,
            prompt_version=self.prompt_version,
        )

    async def list_categories(self, keywords: Sequence[str], *, limit: int) -> list[CategoryOption]:
        del keywords
        return [
            CategoryOption(
                key=_encode(item),
                level1=item.level1_name,
                level2=item.level2_name,
                level3=item.level3_name,
                product_count=item.candidate_count,
            )
            for item in (await self.service.category_pool(self.run_id))[:limit]
        ]

class PptSelectionJobPort:
    def __init__(self, service: RecommendationService) -> None:
        self.service = service

    async def requirement_for(self, run_id: UUID) -> str:
        return (await self.service.get_run(run_id)).raw_requirement_snapshot

    async def is_cancelled(self, run_id: UUID) -> bool:
        return (await self.service.get_run(run_id)).status == RecommendationRunStatus.CANCELLED

    async def record_progress(self, run_id: UUID, status: str, percent: int, message: str) -> None:
        del run_id, status, percent, message

    async def complete(self, run_id: UUID, result: AgentRecommendationResult) -> None:
        if result.analysis.needs_input:
            await self.service.mark_needs_input(run_id, "；".join(result.analysis.questions))
            return
        if not result.category_choices:
            await self.service.mark_no_candidates(run_id)
            return
        await self.service.record_category_choices(
            run_id,
            [
                CategoryChoiceInput(
                    **_decode(choice.category_key).model_dump(),
                    source="AI",
                    reason=choice.reason,
                )
                for choice in result.category_choices
            ],
        )
        await self.service.persist_ppt_eligible_candidates(run_id)
        await PptSolutionService(self.service.session).create_generated_plans(run_id)

    async def fail(self, run_id: UUID, safe_error: str) -> None:
        await self.service.mark_failed(run_id, safe_error)

    async def cancelled(self, run_id: UUID) -> None:
        await self.service.mark_cancelled(run_id)
