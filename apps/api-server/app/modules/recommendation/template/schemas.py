from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.bid.schemas import BidProjectFileResponse
from app.modules.catalog.application.product_export_columns import PRODUCT_EXPORT_COLUMN_KEYS


class RecommendationDerivedField(StrEnum):
    SUPPORTS_JD_OR_SF = "supports_jd_or_sf"

RECOMMENDATION_MAPPING_FIELD_KEYS = frozenset(
    (
        *PRODUCT_EXPORT_COLUMN_KEYS,
        "factory_direct",
        "campaign_price",
        "delivery_status",
        "inventory_status",
        "fulfillment_cycle",
        "evidence",
        RecommendationDerivedField.SUPPORTS_JD_OR_SF.value,
    )
)


class RecommendationRunStatus(StrEnum):
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    ANALYZING = "ANALYZING"
    RETRIEVING = "RETRIEVING"
    RANKING = "RANKING"
    CANDIDATES_READY = "CANDIDATES_READY"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    CONFIRMED = "CONFIRMED"
    EXPORTED = "EXPORTED"
    FAILED = "FAILED"
    NO_CANDIDATES = "NO_CANDIDATES"
    NEEDS_INPUT = "NEEDS_INPUT"
    CANCELLED = "CANCELLED"


class RecommendationTemplateMappingUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_name: str = Field(min_length=1, max_length=128)
    header_row: int = Field(ge=1)
    data_start_row: int = Field(ge=1)
    mapping_json: dict[str, str] = Field(min_length=1)

    @field_validator("mapping_json")
    @classmethod
    def validate_mapping(cls, value: dict[str, str]) -> dict[str, str]:
        if any(
            key not in RECOMMENDATION_MAPPING_FIELD_KEYS or not header.strip()
            for key, header in value.items()
        ):
            raise ValueError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID")
        return value

    @model_validator(mode="after")
    def validate_row_order(self) -> "RecommendationTemplateMappingUpdateRequest":
        if self.data_start_row <= self.header_row:
            raise ValueError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID")
        return self


class RecommendationTemplateMappingResponse(BaseModel):
    template_file: BidProjectFileResponse
    sheet_name: str
    header_row: int
    data_start_row: int
    mapping_json: dict[str, str]
    confirmed_by: UUID | None
    confirmed_at: datetime | None


class RecommendationTemplateFileResponse(BidProjectFileResponse):
    mapping_confirmed: bool


class RecommendationTemplateColumnResponse(BaseModel):
    column_index: int = Field(ge=1)
    header: str
    duplicate: bool


class RecommendationTemplateStructureResponse(BaseModel):
    sheet_names: list[str]
    sheet_name: str
    header_row: int
    max_row: int
    columns: list[RecommendationTemplateColumnResponse]
