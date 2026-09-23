from typing import Any
from uuid import uuid4

import pytest

from app.integrations.deepseek.client import (
    DeepSeekConfigurationError,
    DeepSeekStructuredOutputError,
)
from app.jobs.recommendation_agent import execute_recommendation_agent
from app.modules.recommendation.application.agent_runner import RecommendationAgentCancelled
from app.modules.recommendation.application.agent_schemas import (
    AgentRecommendationResult,
    CategoryChoice,
    RankedCandidate,
    RequirementAnalysis,
)
from app.modules.recommendation.application.agent_service_adapter import (
    RecommendationServiceJobPort,
)


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


@pytest.mark.asyncio
async def test_job_reports_candidate_ranking_schema_failure_without_raw_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    port = FakeJobPort()
    await execute_recommendation_agent(  # type: ignore[arg-type]
        uuid4(),
        runner=FakeRunner(
            error=DeepSeekStructuredOutputError(
                response_model_name="CandidateRanking",
                safe_validation_summary=(
                    "candidates.31.score: less_than_equal: "
                    "Input should be less than or equal to 100"
                ),
                error_kind="SCHEMA_VALIDATION",
            )
        ),
        job_port=port,
    )
    assert port.failed == "候选排序结果格式异常，已自动重试仍失败，请重新生成推荐"
    assert "stage=CandidateRanking" in caplog.text
    assert "API key" not in caplog.text
    assert '"product_id"' not in caplog.text


@pytest.mark.asyncio
async def test_job_port_never_persists_more_than_thirty_ranked_candidates() -> None:
    class CapturingService:
        def __init__(self) -> None:
            self.payload: Any = None

        async def record_category_choices(self, _: object, __: object) -> None:
            pass

        async def persist_ranked_candidates(self, _: object, payload: Any) -> None:
            self.payload = payload

    service = CapturingService()
    result = AgentRecommendationResult(
        analysis=RequirementAnalysis(summary="测试", keywords=["测试"]),
        category_choices=[
            CategoryChoice(
                category_key='["一级",null,null]', reason="测试", search_keywords=["测试"]
            )
        ],
        candidates=[
            RankedCandidate(product_id=uuid4(), score=90, reason="测试") for _ in range(31)
        ],
        provider="fake",
        model="fake",
        prompt_version="test",
        tool_call_count=0,
    )
    await RecommendationServiceJobPort(service).complete(uuid4(), result)  # type: ignore[arg-type]
    assert service.payload is not None
    assert len(service.payload.candidates) == 30
