from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.bid.domain.lifecycle import (
    BidFileType,
    BidImportStatus,
    BidItemStatus,
    BidProjectStatus,
)


class BidProjectFileResponse(BaseModel):
    id: UUID
    file_type: BidFileType
    version_no: int
    original_filename: str
    file_size: int
    sha256: str
    created_at: datetime


class BidProjectEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    from_status: BidProjectStatus | None
    to_status: BidProjectStatus | None
    event_type: str
    actor_id: UUID | None
    note: str | None
    occurred_at: datetime


class BidProjectListItem(BaseModel):
    id: UUID
    project_code: str
    project_name: str
    buyer_name: str
    start_at: datetime | None
    deadline_at: datetime | None
    status: BidProjectStatus
    import_status: BidImportStatus
    total_item_count: int
    processed_item_count: int
    created_at: datetime


class BidProjectDetailResponse(BidProjectListItem):
    remark: str | None
    template_id: UUID | None
    template_version: int | None
    import_error: str | None
    submitted_file_id: UUID | None
    files: list[BidProjectFileResponse]
    events: list[BidProjectEventResponse]


class BidProjectCreateResponse(BaseModel):
    id: UUID
    project_code: str
    status: BidProjectStatus
    import_status: BidImportStatus
    import_error: str | None
    template_id: UUID | None
    template_version: int | None
    total_item_count: int


class BidCurrentSelectionResponse(BaseModel):
    selection_id: UUID
    product_id: UUID
    supplier_id: UUID
    selected_unit_price: Decimal
    requirement_snapshot: dict[str, object]
    product_snapshot: dict[str, object]
    supplier_snapshot: dict[str, object]
    price_snapshot: dict[str, object]
    note: str | None
    created_at: datetime


class BidProjectItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sheet_name: str
    source_row_number: int
    product_name: str | None
    brand: str | None
    model: str | None
    specification: str | None
    category_text: str | None
    quantity: Decimal | None
    unit: str | None
    max_price: Decimal | None
    buyer_item_code: str | None
    status: BidItemStatus
    current_selection_id: UUID | None
    no_quote_reason: str | None
    current_selection: BidCurrentSelectionResponse | None = None


class BidSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submitted_file_id: UUID
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class BidProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_name: str = Field(min_length=1, max_length=255)
    buyer_name: str = Field(min_length=1, max_length=255)
    start_at: datetime | None = None
    deadline_at: datetime | None = None
    remark: str | None = Field(default=None, max_length=5000)


class BidVoidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be blank")
        return value


class BidResultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class BidProjectStatusResponse(BaseModel):
    id: UUID
    status: BidProjectStatus
    submitted_file_id: UUID | None
