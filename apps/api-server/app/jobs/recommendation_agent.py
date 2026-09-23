import logging
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.deepseek.client import (
    DeepSeekClient,
    DeepSeekConfigurationError,
    DeepSeekProviderError,
    DeepSeekStructuredOutputError,
)
from app.modules.recommendation.application.agent_runner import (
    AgentRunner,
    RecommendationAgentCancelled,
    RecommendationAgentContractError,
)
from app.modules.recommendation.application.agent_schemas import AgentRecommendationResult
from app.modules.recommendation.application.agent_service_adapter import (
    RecommendationServiceJobPort,
    RecommendationServiceTools,
)
from app.modules.recommendation.application.service import RecommendationService

logger = logging.getLogger(__name__)

_STRUCTURED_FAILURE_MESSAGES = {
    "CandidateRanking": "候选排序结果格式异常，已自动重试仍失败，请重新生成推荐",
    "RequirementAnalysis": "需求解析结果格式异常，已自动重试仍失败，请重新生成推荐",
    "CategoryChoiceList": "类目选择结果格式异常，已自动重试仍失败，请重新生成推荐",
}


class RecommendationJobPort(Protocol):
    async def requirement_for(self, run_id: UUID) -> str: ...

    async def is_cancelled(self, run_id: UUID) -> bool: ...

    async def record_progress(
        self, run_id: UUID, status: str, percent: int, message: str
    ) -> None: ...

    async def complete(self, run_id: UUID, result: AgentRecommendationResult) -> None: ...

    async def fail(self, run_id: UUID, safe_error: str) -> None: ...

    async def cancelled(self, run_id: UUID) -> None: ...


async def execute_recommendation_agent(
    run_id: UUID,
    *,
    runner: AgentRunner,
    job_port: RecommendationJobPort,
) -> None:
    """Queue-compatible job entry; persistence stays behind the B-owned port."""

    async def report(status: str, percent: int, message: str) -> None:
        await job_port.record_progress(run_id, status, percent, message)

    async def cancelled() -> bool:
        return await job_port.is_cancelled(run_id)

    try:
        requirement = await job_port.requirement_for(run_id)
        result = await runner.run(
            requirement,
            report_progress=report,
            is_cancelled=cancelled,
        )
        if await cancelled():
            await job_port.cancelled(run_id)
            return
        await job_port.complete(run_id, result)
    except RecommendationAgentCancelled:
        await job_port.cancelled(run_id)
    except DeepSeekConfigurationError as exc:
        await job_port.fail(run_id, str(exc))
    except DeepSeekStructuredOutputError as exc:
        logger.warning(
            "recommendation structured output failed run_id=%s "
            "stage=%s attempt=%s error_kind=%s validation=%s",
            run_id,
            exc.response_model_name,
            AgentRunner.MAX_PROVIDER_ATTEMPTS,
            exc.error_kind,
            exc.safe_validation_summary,
        )
        await job_port.fail(
            run_id,
            _STRUCTURED_FAILURE_MESSAGES.get(
                exc.response_model_name, "推荐结果格式异常，已自动重试仍失败，请重新生成推荐"
            ),
        )
    except DeepSeekProviderError as exc:
        logger.warning(
            "recommendation provider failed run_id=%s error_class=%s",
            run_id,
            type(exc).__name__,
        )
        await job_port.fail(run_id, str(exc))
    except RecommendationAgentContractError as exc:
        logger.warning("recommendation contract failed run_id=%s reason=%s", run_id, str(exc))
        await job_port.fail(run_id, str(exc))
    except Exception as exc:
        logger.error(
            "recommendation job failed run_id=%s error_class=%s",
            run_id,
            type(exc).__name__,
        )
        await job_port.fail(run_id, "推荐任务执行失败，请稍后重试")


async def execute_recommendation_agent_inline(run_id: UUID, session: AsyncSession) -> None:
    """Local-first execution wired only through B's public RecommendationService."""

    provider = DeepSeekClient()
    service = RecommendationService(session)
    tools = RecommendationServiceTools(
        run_id,
        service,
        provider=provider.provider,
        model=provider.model,
        prompt_version=provider.prompt_version,
    )
    await execute_recommendation_agent(
        run_id,
        runner=AgentRunner(provider, tools),
        job_port=RecommendationServiceJobPort(service),
    )
