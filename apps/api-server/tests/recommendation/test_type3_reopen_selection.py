from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.bid.domain.lifecycle import BidProjectStatus
from app.modules.bid.infrastructure.models import BidProjectEvent
from app.modules.type3_recommendation.application.service import Type3RecommendationService


@pytest.mark.asyncio
async def test_type3_reopen_selection_restores_manual_selection_after_export() -> None:
    actor_id = uuid4()
    project = SimpleNamespace(
        id=uuid4(), status=BidProjectStatus.EXPORTED.value, updated_by=None
    )
    run = SimpleNamespace(id=uuid4(), project_id=project.id, status="EXPORTED")
    session = MagicMock()
    session.in_transaction.return_value = True
    session.scalar = AsyncMock(return_value=1)
    session.add = MagicMock()
    service = Type3RecommendationService(session)
    service._project = AsyncMock(return_value=project)  # type: ignore[method-assign]
    service._run = AsyncMock(return_value=run)  # type: ignore[method-assign]

    await service.reopen_selection(project.id, run.id, actor_id)

    assert project.status == BidProjectStatus.SELECTING.value
    assert project.updated_by == actor_id
    assert run.status == "CONFIRMED"
    event = session.add.call_args.args[0]
    assert isinstance(event, BidProjectEvent)
    assert event.event_type == "TYPE3_SELECTION_REOPENED"
    assert event.from_status == BidProjectStatus.EXPORTED.value
    assert event.to_status == BidProjectStatus.SELECTING.value
