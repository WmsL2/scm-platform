from uuid import UUID

from app.modules.recommendation.application.agent_runner import RecommendationTools
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    RequirementAnalysis,
)
from app.modules.recommendation.application.service import RecommendationService
from app.modules.recommendation.schemas import ParsedRequirement
from app.modules.recommendation.template.schemas import RecommendationRunStatus


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
                requirement_version="v5",
                gross_margin_min=analysis.gross_margin_min,
                gross_margin_max=analysis.gross_margin_max,
                agreement_price_min=analysis.agreement_price_min or analysis.budget_min,
                agreement_price_max=analysis.agreement_price_max or analysis.budget_max,
                jd_price_min=analysis.jd_price_min,
                jd_price_max=analysis.jd_price_max,
                discount_rate_min=analysis.discount_rate_min,
                discount_rate_max=analysis.discount_rate_max,
                # Only explicitly mandatory brand/category requirements are filters.
                required_brands=analysis.required_brands,
                explicit_category_keywords=analysis.explicit_category_keywords,
                category_intents=(
                    analysis.category_intents if analysis.explicit_category_keywords else []
                ),
            ),
            provider=self.provider,
            model=self.model,
            prompt_version=self.prompt_version,
        )


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
        await self.service.persist_all_eligible_candidates(run_id)

    async def fail(self, run_id: UUID, safe_error: str) -> None:
        await self.service.mark_failed(run_id, safe_error)

    async def cancelled(self, run_id: UUID) -> None:
        await self.service.mark_cancelled(run_id)
