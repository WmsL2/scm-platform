from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.bid.domain.lifecycle import (
    BidFileType,
    BidImportStatus,
    BidItemStatus,
    BidProjectStatus,
    BidProjectType,
    BidRecommendationType,
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
    project_type: BidProjectType
    recommendation_type: BidRecommendationType | None = None
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
    project_type: BidProjectType
    recommendation_type: BidRecommendationType | None = None
    import_error: str | None
    template_id: UUID | None
    template_version: int | None
    total_item_count: int


class BidOutputMappingFieldResponse(BaseModel):
    key: str
    label: str
    required: bool
    header: str | None


class BidOutputMappingResponse(BaseModel):
    project_id: UUID
    sheet_name: str
    header_row: int
    headers: list[str]
    suggested_headers: list[str]
    fields: list[BidOutputMappingFieldResponse]
    mapping: dict[str, str]
    confirmed: bool
    confirmed_by: UUID | None
    confirmed_at: datetime | None


class BidOutputMappingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping: dict[str, str | None]


class BidInputMappingFieldResponse(BaseModel):
    key: str
    label: str
    required: bool
    header: str | None


class BidInputMappingResponse(BaseModel):
    project_id: UUID
    sheet_names: list[str]
    sheet_name: str
    header_row: int
    data_start_row: int
    headers: list[str]
    fields: list[BidInputMappingFieldResponse]
    mapping: dict[str, str]
    confirmed: bool
    import_error: str | None


class BidInputMappingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet_name: str = Field(min_length=1, max_length=128)
    header_row: int = Field(ge=1)
    data_start_row: int = Field(ge=2)
    mapping: dict[str, str | None]


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


class BidProjectPurgeRequest(BaseModel):
    """Require an exact visible project code for an irreversible deletion."""

    model_config = ConfigDict(extra="forbid")

    confirm_project_code: str = Field(min_length=1, max_length=32)

    @field_validator("confirm_project_code")
    @classmethod
    def strip_project_code(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("confirm_project_code must not be blank")
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


class BidProjectPurgeResponse(BaseModel):
    id: UUID
    status: str = "PURGED"
