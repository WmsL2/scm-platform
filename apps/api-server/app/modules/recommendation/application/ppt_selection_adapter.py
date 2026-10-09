from __future__ import annotations

import logging
from uuid import UUID

from app.common.contracts import AppError
from app.core.database import SessionLocal
from app.integrations.deepseek.client import DeepSeekStructuredOutputError
from app.modules.recommendation.application.agent_runner import StructuredProvider
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    RequirementAnalysis,
)
from app.modules.recommendation.application.ppt_catalog_service import PptCatalogService
from app.modules.recommendation.application.ppt_selection_runner import PptCatalogTools
from app.modules.recommendation.application.ppt_service import PptSolutionService
from app.modules.recommendation.schemas import CategoryCatalogSnapshot, ParsedRequirement

logger = logging.getLogger(__name__)


class PptSelectionServiceTools(PptCatalogTools):
    """Type-5-only application boundary for its independent V8 workflow."""

    def __init__(
        self,
        run_id: UUID,
        *,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> None:
        self.run_id = run_id
        self.provider = provider
        self.model = model
        self.prompt_version = prompt_version

    async def prepare(self, analysis: RequirementAnalysis) -> CategoryCatalogSnapshot:
        requirement = ParsedRequirement(
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
        )
        async with SessionLocal() as session:
            await PptCatalogService(session).config_for_run(self.run_id)
        async with SessionLocal() as session:
            await PptCatalogService(session).begin_analysis(self.run_id)
        async with SessionLocal() as session:
            await PptCatalogService(session).save_parsed_requirement(
                self.run_id,
                requirement,
                provider=self.provider,
                model=self.model,
                prompt_version=f"{self.prompt_version}:ppt-v8",
            )
        async with SessionLocal() as session:
            return await PptCatalogService(session).create_category_catalog_snapshot(self.run_id)

    async def record_catalog_category_matches(self, category_keys: list[str]) -> None:
        async with SessionLocal() as session:
            await PptCatalogService(session).record_catalog_category_matches(
                self.run_id, category_keys
            )


class PptSelectionJobPort:
    def __init__(self, provider: StructuredProvider) -> None:
        self.provider = provider

    async def requirement_for(self, run_id: UUID) -> str:
        async with SessionLocal() as session:
            return await PptCatalogService(session).requirement_for(run_id)

    async def is_cancelled(self, run_id: UUID) -> bool:
        async with SessionLocal() as session:
            return await PptCatalogService(session).is_cancelled(run_id)

    async def record_progress(self, run_id: UUID, status: str, percent: int, message: str) -> None:
        del run_id, status, percent, message

    async def complete(self, run_id: UUID, result: AgentRecommendationResult) -> None:
        if result.analysis.needs_input:
            async with SessionLocal() as session:
                await PptCatalogService(session).mark_needs_input(
                    run_id, "；".join(result.analysis.questions)
                )
            return
        try:
            async with SessionLocal() as session:
                count = await PptCatalogService(session).persist_eligible_candidates(run_id)
        except AppError as exc:
            logger.warning(
                "ppt candidate freeze failed run_id=%s code=%s message=%s",
                run_id,
                exc.code,
                exc.message,
            )
            raise
        if not count:
            return
        try:
            async with SessionLocal() as session:
                service = PptSolutionService(session)
                run = await service.repository.run(run_id)
                direct_selection = bool(
                    run
                    and isinstance(run.ppt_config_snapshot, dict)
                    and run.ppt_config_snapshot.get("selection_mode") == "DIRECT"
                )
                if direct_selection:
                    await service.retain_ai_matched_candidates(run_id, self.provider)
                else:
                    # Historical Runs keep their persisted plan cards available.
                    await service.create_ai_generated_plans(run_id, self.provider)
        except DeepSeekStructuredOutputError as exc:
            logger.warning(
                "ppt plan structured output failed run_id=%s stage=%s error_kind=%s "
                "validation=%s",
                run_id,
                exc.response_model_name,
                exc.error_kind,
                exc.safe_validation_summary,
            )
            async with SessionLocal() as session:
                await PptCatalogService(session).record_plan_failure(
                    run_id,
                    "类型 5 AI 商品匹配返回格式异常，自动重试后仍失败"
                    f"（{exc.error_kind}），请重新生成。",
                )
        except AppError as exc:
            logger.warning(
                "ppt direct selection failed run_id=%s code=%s message=%s",
                run_id,
                exc.code,
                exc.message,
            )
            async with SessionLocal() as session:
                await PptCatalogService(session).record_plan_failure(
                    run_id, f"类型 5 AI 商品匹配失败：{exc.message}，请重新生成。"
                )
        except Exception as exc:
            # Candidate recall remains usable and auditable even if direct matching fails.
            detail = f"（{type(exc).__name__}）"
            async with SessionLocal() as session:
                await PptCatalogService(session).record_plan_failure(
                    run_id, f"类型 5 AI 商品匹配失败{detail}，请调整配置后重新生成。"
                )

    async def fail(self, run_id: UUID, safe_error: str) -> None:
        async with SessionLocal() as session:
            await PptCatalogService(session).mark_failed(run_id, safe_error)

    async def cancelled(self, run_id: UUID) -> None:
        async with SessionLocal() as session:
            await PptCatalogService(session).mark_cancelled(run_id)
