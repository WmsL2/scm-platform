from __future__ import annotations

import uuid
from collections.abc import Mapping
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
    total_item_count: int
    processed_item_count: int


class BidItemCandidateResponse(BaseModel):
    candidate_id: uuid.UUID
    product_id: uuid.UUID
    supplier_id: uuid.UUID
    product_name: str | None
    brand: str | None
    model: str | None
    category_path: str
    product_specification: str | None
    supplier_code: str
    supplier_name: str
    cost_price: Decimal | None
    jd_price: Decimal | None
    agreement_price: Decimal | None
    score: Decimal = Field(ge=0)
    rank: int = Field(ge=1)
    method: str
    match_reason: Mapping[str, object]


class BidItemSelectionCreateRequest(BaseModel):
    """Select only a persisted candidate, so supplier and product remain coupled."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: uuid.UUID
    selected_unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    note: str | None = Field(default=None, max_length=2000)


class NoQuoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: NoQuoteReason
    reason_detail: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_detail_for_other(self) -> NoQuoteCreateRequest:
        if self.reason is NoQuoteReason.OTHER and not (self.reason_detail or "").strip():
            raise ValueError("reason_detail is required when reason is OTHER")
        return self


class BidItemSelectionResponse(BaseModel):
    selection_id: uuid.UUID | None
    project_item_id: uuid.UUID
    status: str
    current_selection_id: uuid.UUID | None
