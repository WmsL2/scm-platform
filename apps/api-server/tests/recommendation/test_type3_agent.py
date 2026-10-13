from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.type3_recommendation.application import agent


class _Session:
    def __init__(self) -> None:
        self.rollbacks = 0

    async def rollback(self) -> None:
        self.rollbacks += 1


class _Service:
    def __init__(self) -> None:
        self.session = _Session()
        self.failures: list[str] = []

    async def get_run(self, _run_id: object) -> SimpleNamespace:
        return SimpleNamespace(raw_remark_snapshot="")

    async def fail(self, _run_id: object, message: str) -> None:
        self.failures.append(message)


@pytest.mark.asyncio
async def test_type3_agent_closes_read_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _Service()

    def failing_provider() -> object:
        raise RuntimeError("provider setup failed")

    monkeypatch.setattr(agent, "DeepSeekClient", failing_provider)

    await agent.execute_type3_agent_inline(uuid4(), service)  # type: ignore[arg-type]

    assert service.session.rollbacks == 1
    assert service.failures == ["类型 3 推品任务执行失败，请稍后重试"]
