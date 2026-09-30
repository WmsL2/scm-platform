from __future__ import annotations

from uuid import UUID

from app.modules.recommendation.application.agent_runner import (
    RecommendationAgentContractError,
    StructuredProvider,
)
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    RequirementAnalysis,
)
from app.modules.recommendation.application.ppt_catalog_service import PptCatalogService
from app.modules.recommendation.application.ppt_selection_runner import PptCatalogTools
from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.schemas import CategoryCatalogSnapshot, ParsedRequirement


class PptSelectionServiceTools(PptCatalogTools):
    """Type-5-only application boundary for its independent V8 workflow."""

    def __init__(
        self,
        run_id: UUID,
        service: PptCatalogService,
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

    async def prepare(self, analysis: RequirementAnalysis) -> CategoryCatalogSnapshot:
        await self.service.config_for_run(self.run_id)
        await self.service.begin_analysis(self.run_id)
        await self.service.save_parsed_requirement(
            self.run_id,
            ParsedRequirement(
                requirement_version="ppt-v8",
                gross_margin_min=analysis.gross_margin_min,
                gross_margin_max=analysis.gross_margin_max,
                agreement_price_min=analysis.agreement_price_min or analysis.budget_min,
                agreement_price_max=analysis.agreement_price_max or analysis.budget_max,
                jd_price_min=analysis.jd_price_min,
                jd_price_max=analysis.jd_price_max,
                discount_rate_min=analysis.discount_rate_min,
                discount_rate_max=analysis.discount_rate_max,
                required_brands=analysis.required_brands,
                explicit_category_keywords=analysis.explicit_category_keywords,
                category_intents=[],
            ),
            provider=self.provider,
            model=self.model,
            prompt_version=f"{self.prompt_version}:ppt-v8",
        )
        return await self.service.create_category_catalog_snapshot(self.run_id)

    async def record_catalog_category_matches(self, category_keys: list[str]) -> None:
        await self.service.record_catalog_category_matches(self.run_id, category_keys)


class PptSelectionJobPort:
    def __init__(self, service: PptCatalogService, provider: StructuredProvider) -> None:
        self.service = service
        self.provider = provider

    async def requirement_for(self, run_id: UUID) -> str:
        return await self.service.requirement_for(run_id)

    async def is_cancelled(self, run_id: UUID) -> bool:
        return await self.service.is_cancelled(run_id)

    async def record_progress(self, run_id: UUID, status: str, percent: int, message: str) -> None:
        del run_id, status, percent, message

    async def complete(self, run_id: UUID, result: AgentRecommendationResult) -> None:
        if result.analysis.needs_input:
            await self.service.mark_needs_input(run_id, "；".join(result.analysis.questions))
            return
        count = await self.service.persist_eligible_candidates(run_id)
        if not count:
            return
        try:
            await PptSolutionService(self.service.session).create_ai_generated_plans(
                run_id, self.provider
            )
        except Exception as exc:
            # Candidate recall remains usable and auditable even if plan composition fails.
            detail = (
                f"：{exc}"
                if isinstance(exc, RecommendationAgentContractError)
                else f"（{type(exc).__name__}）"
            )
            await self.service.record_plan_failure(
                run_id, f"类型 5 AI 方案编排失败{detail}，请调整配置后重新生成。"
            )

    async def fail(self, run_id: UUID, safe_error: str) -> None:
        await self.service.mark_failed(run_id, safe_error)

    async def cancelled(self, run_id: UUID) -> None:
        await self.service.mark_cancelled(run_id)
