import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.modules.matching.schemas import (
    BidItemSelectionCreateRequest,
    NoQuoteCreateRequest,
    NoQuoteReason,
)


def test_selection_contract_accepts_only_a_persisted_candidate_and_decimal_price() -> None:
    candidate_id = uuid.uuid4()

    request = BidItemSelectionCreateRequest(
        candidate_id=candidate_id,
        selected_unit_price="99.9900",
    )

    assert request.candidate_id == candidate_id
    assert request.selected_unit_price == Decimal("99.9900")


def test_selection_contract_rejects_extra_supplier_or_product_fields() -> None:
    with pytest.raises(ValidationError):
        BidItemSelectionCreateRequest(
            candidate_id=uuid.uuid4(),
            selected_unit_price="99.9900",
            supplier_id=uuid.uuid4(),
        )


def test_other_no_quote_reason_requires_human_explanation() -> None:
    with pytest.raises(ValidationError, match="reason_detail is required"):
        NoQuoteCreateRequest(reason=NoQuoteReason.OTHER, reason_detail="  ")

    request = NoQuoteCreateRequest(
        reason=NoQuoteReason.OTHER,
        reason_detail="客户指定的交期无法满足",
    )

    assert request.reason_detail == "客户指定的交期无法满足"
