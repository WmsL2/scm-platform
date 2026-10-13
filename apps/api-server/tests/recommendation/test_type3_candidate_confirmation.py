from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.type3_recommendation.schemas import Type3CandidateConfirmationRequest


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
