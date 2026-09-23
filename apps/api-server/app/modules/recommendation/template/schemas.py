from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.bid.schemas import BidProjectFileResponse


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
    mapping_json: dict[str, str]

    @field_validator("mapping_json")
    @classmethod
    def validate_mapping(cls, value: dict[str, str]) -> dict[str, str]:
        allowed = {
            "category_level1_name",
            "category_level2_name",
            "category_level3_name",
            "brand",
            "sku",
            "product_name",
            "jd_price",
            "agreement_price",
            "discount_rate",
            "purchasing_agent",
            "profit",
            "gross_margin",
            "factory_direct",
            "shipping_courier",
        }
        if any(key not in allowed or not header.strip() for key, header in value.items()):
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
