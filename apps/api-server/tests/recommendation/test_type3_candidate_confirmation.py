from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.bid.domain.lifecycle import BidProjectStatus
from app.modules.bid.infrastructure.models import BidProjectEvent
from app.modules.type3_recommendation.application.service import Type3RecommendationService
from app.modules.type3_recommendation.schemas import (
    Type3CandidateConfirmationRequest,
    Type3CandidateUnconfirmationRequest,
)


def test_type3_confirm_all_accepts_sheet_scope_and_exclusions() -> None:
    payload = Type3CandidateConfirmationRequest(
        select_all_unconfirmed=True,
        sheet_name="家用电器",
        excluded_candidate_ids=[uuid4()],
    )

    assert payload.select_all_unconfirmed is True
    assert payload.sheet_name == "家用电器"


def test_type3_confirmation_requires_exactly_one_selection_mode() -> None:
    with pytest.raises(ValidationError):
        Type3CandidateConfirmationRequest()
    with pytest.raises(ValidationError):
        Type3CandidateConfirmationRequest(
            candidate_ids=[uuid4()], select_all_unconfirmed=True
        )


def test_type3_unconfirmation_requires_exactly_one_selection_mode() -> None:
    with pytest.raises(ValidationError):
        Type3CandidateUnconfirmationRequest()
    with pytest.raises(ValidationError):
        Type3CandidateUnconfirmationRequest(
            candidate_ids=[uuid4()], select_all_confirmed=True
        )


@pytest.mark.asyncio
async def test_type3_unconfirm_returns_candidate_to_pending_and_writes_audit_event() -> None:
    actor_id = uuid4()
    project = SimpleNamespace(
        id=uuid4(), status=BidProjectStatus.SELECTING.value, updated_by=None
    )
    run = SimpleNamespace(id=uuid4(), project_id=project.id, status="CONFIRMED")
    candidate = SimpleNamespace(
        id=uuid4(), run_id=run.id, confirmed_by=actor_id, confirmed_at=object()
    )
    session = MagicMock()
    session.in_transaction.return_value = True
    session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: [candidate]))
    session.scalar = AsyncMock(return_value=0)
    session.flush = AsyncMock()
    session.add = MagicMock()
    service = Type3RecommendationService(session)
    service._run = AsyncMock(return_value=run)  # type: ignore[method-assign]
    service._project = AsyncMock(return_value=project)  # type: ignore[method-assign]

    count = await service.unconfirm_candidates(
        run.id,
        Type3CandidateUnconfirmationRequest(candidate_ids=[candidate.id]),
        actor_id,
    )

    assert count == 1
    assert candidate.confirmed_by is None
    assert candidate.confirmed_at is None
    assert run.status == "WAITING_CONFIRMATION"
    assert project.updated_by == actor_id
    event = session.add.call_args.args[0]
    assert isinstance(event, BidProjectEvent)
    assert event.event_type == "TYPE3_CANDIDATES_UNCONFIRMED"
