from __future__ import annotations

import uuid
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NoQuoteReason(StrEnum):
    NO_PRODUCT_MATCH = "NO_PRODUCT_MATCH"
    BRAND_MODEL_MISMATCH = "BRAND_MODEL_MISMATCH"
    PRICE_NOT_MATCH = "PRICE_NOT_MATCH"
    SUPPLIER_UNAVAILABLE = "SUPPLIER_UNAVAILABLE"
    OTHER = "OTHER"


class StartMatchingResponse(BaseModel):
    task_id: uuid.UUID
    status: str


class BidItemCandidateResponse(BaseModel):
    candidate_id: uuid.UUID
    product_id: uuid.UUID
    supplier_id: uuid.UUID
    score: int = Field(ge=0)
    rank: int = Field(ge=1)
    method: str
    match_reason: dict[str, object]


class BidItemSelectionCreateRequest(BaseModel):
    """Select only a persisted candidate, so supplier and product remain coupled."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: uuid.UUID
    selected_unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)


class NoQuoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: NoQuoteReason
    reason_detail: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_detail_for_other(self) -> NoQuoteCreateRequest:
        if self.reason is NoQuoteReason.OTHER and not (self.reason_detail or "").strip():
            raise ValueError("reason_detail is required when reason is OTHER")
        return self
