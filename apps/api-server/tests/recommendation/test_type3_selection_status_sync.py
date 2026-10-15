from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.bid.domain.lifecycle import BidProjectStatus
from app.modules.bid.infrastructure.models import BidProjectEvent
from app.modules.type3_recommendation.application.service import Type3RecommendationService
from app.modules.type3_recommendation.schemas import Type3RemarkAnalysis


@pytest.mark.asyncio
async def test_type3_execute_moves_project_to_selecting_after_candidates_are_created() -> None:
    actor_id = uuid4()
    project = SimpleNamespace(
        id=uuid4(), status=BidProjectStatus.MATCHING.value, updated_by=None
    )
    run = SimpleNamespace(
        id=uuid4(),
        project_id=project.id,
        status="RETRIEVING",
        parsed_remark=None,
        provider=None,
        model=None,
        prompt_version=None,
        category_catalog_snapshot={"items": []},
        sheet_snapshot=[],
        created_by=actor_id,
    )
    session = MagicMock()
    session.in_transaction.return_value = True
    session.flush = AsyncMock()
    session.scalar = AsyncMock(return_value=2)
    session.add = MagicMock()
    service = Type3RecommendationService(session)
    service._run = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._project = AsyncMock(return_value=project)  # type: ignore[method-assign]

    await service.execute(
        run.id,
        Type3RemarkAnalysis(),
        provider="test",
        model="test",
        prompt_version="test",
        category_matches={},
    )

    assert run.status == "WAITING_CONFIRMATION"
    assert project.status == BidProjectStatus.SELECTING.value
    assert project.updated_by == actor_id
    event = session.add.call_args.args[0]
    assert isinstance(event, BidProjectEvent)
    assert event.event_type == "TYPE3_CANDIDATES_READY"
    assert event.from_status == BidProjectStatus.MATCHING.value
    assert event.to_status == BidProjectStatus.SELECTING.value


@pytest.mark.asyncio
async def test_type3_recover_selection_unblocks_historic_waiting_run_without_ai() -> None:
    actor_id = uuid4()
    project = SimpleNamespace(
        id=uuid4(), status=BidProjectStatus.MATCHING.value, updated_by=None
    )
    run = SimpleNamespace(
        id=uuid4(), project_id=project.id, status="WAITING_CONFIRMATION"
    )
    session = MagicMock()
    session.in_transaction.return_value = True
    session.scalar = AsyncMock(return_value=540)
    session.add = MagicMock()
    service = Type3RecommendationService(session)
    service._run = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._project = AsyncMock(return_value=project)  # type: ignore[method-assign]

    await service.recover_selection(project.id, run.id, actor_id)

    assert project.status == BidProjectStatus.SELECTING.value
    assert project.updated_by == actor_id
    event = session.add.call_args.args[0]
    assert isinstance(event, BidProjectEvent)
    assert event.event_type == "TYPE3_SELECTION_RECOVERED"
    assert event.from_status == BidProjectStatus.MATCHING.value
    assert event.to_status == BidProjectStatus.SELECTING.value
