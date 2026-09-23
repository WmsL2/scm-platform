from typing import Protocol
from uuid import UUID

from app.integrations.deepseek.client import DeepSeekConfigurationError
from app.modules.recommendation.application.agent_runner import (
    AgentRunner,
    RecommendationAgentCancelled,
)
from app.modules.recommendation.application.agent_schemas import AgentRecommendationResult


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
    except Exception:
        await job_port.fail(run_id, "推荐任务执行失败，请稍后重试")
