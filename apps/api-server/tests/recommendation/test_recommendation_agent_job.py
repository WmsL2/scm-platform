from typing import Any
from uuid import uuid4

import pytest

from app.integrations.deepseek.client import DeepSeekConfigurationError
from app.jobs.recommendation_agent import execute_recommendation_agent
from app.modules.recommendation.application.agent_runner import RecommendationAgentCancelled


class FakeRunner:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    async def run(self, requirement: str, **_: Any) -> Any:
        assert requirement == "一段足够长的自由推品业务需求说明，用来执行测试任务"
        if self.error:
            raise self.error
        return self.result


class FakeJobPort:
    def __init__(self) -> None:
        self.completed: Any = None
        self.failed: str | None = None
        self.was_cancelled = False

    async def requirement_for(self, _: object) -> str:
        return "一段足够长的自由推品业务需求说明，用来执行测试任务"

    async def is_cancelled(self, _: object) -> bool:
        return False

    async def record_progress(self, *_: object) -> None:
        pass

    async def complete(self, _: object, result: Any) -> None:
        self.completed = result

    async def fail(self, _: object, safe_error: str) -> None:
        self.failed = safe_error

    async def cancelled(self, _: object) -> None:
        self.was_cancelled = True


@pytest.mark.asyncio
async def test_job_completes_through_port_without_owning_persistence() -> None:
    port = FakeJobPort()
    expected = object()
    await execute_recommendation_agent(uuid4(), runner=FakeRunner(expected), job_port=port)  # type: ignore[arg-type]
    assert port.completed is expected


@pytest.mark.asyncio
async def test_job_redacts_failures_and_records_cancellation() -> None:
    port = FakeJobPort()
    await execute_recommendation_agent(  # type: ignore[arg-type]
        uuid4(), runner=FakeRunner(error=RuntimeError("database-password")), job_port=port
    )
    assert port.failed == "推荐任务执行失败，请稍后重试"
    assert "database-password" not in port.failed

    cancelled_port = FakeJobPort()
    await execute_recommendation_agent(  # type: ignore[arg-type]
        uuid4(), runner=FakeRunner(error=RecommendationAgentCancelled()), job_port=cancelled_port
    )
    assert cancelled_port.was_cancelled is True

    configuration_port = FakeJobPort()
    await execute_recommendation_agent(  # type: ignore[arg-type]
        uuid4(),
        runner=FakeRunner(error=DeepSeekConfigurationError("请设置 DEEPSEEK_API_KEY")),
        job_port=configuration_port,
    )
    assert configuration_port.failed == "请设置 DEEPSEEK_API_KEY"
