from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PptGenerationStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class PptRecommendationMode(StrEnum):
    SINGLE = "SINGLE"
    COMBINATION = "COMBINATION"
    MIXED = "MIXED"


class PptPriceBandInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def valid_range(self) -> "PptPriceBandInput":
        if self.min_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price must not exceed max_price")
        return self


class PptRecommendationConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recommendation_mode: PptRecommendationMode
    price_bands: list[PptPriceBandInput] = Field(min_length=1, max_length=12)
    candidate_count_per_band: int = Field(ge=1, le=500)
    plan_count_per_band: int = Field(ge=1, le=20)
    fulfillment_deadline: date | None = None


class PptRecommendationConfigResponse(PptRecommendationConfigUpdateRequest):
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class PptSolutionPlanItemResponse(BaseModel):
    candidate_id: UUID
    rank: int
    product_snapshot: dict[str, object]
    price_snapshot: dict[str, object]


class PptSolutionPlanResponse(BaseModel):
    id: UUID
    run_id: UUID
    price_band_index: int
    plan_no: int
    plan_type: Literal["SINGLE", "COMBINATION"]
    name: str
    summary: str | None
    candidate_ids: list[UUID]
    items: list[PptSolutionPlanItemResponse]
    created_at: datetime


class PptPackageItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: UUID
    quantity: int = Field(ge=1, le=9999)


class PptPackageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    price_tier: Decimal | None = Field(default=None, ge=0)
    reason: str | None = Field(default=None, max_length=2000)
    items: list[PptPackageItemInput] = Field(min_length=2, max_length=50)

    @model_validator(mode="after")
    def unique_candidates(self) -> "PptPackageCreateRequest":
        ids = [item.candidate_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("package candidates must be unique")
        return self


class PptPackageItemResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    sort_order: int
    product_snapshot: dict[str, object]
    price_snapshot: dict[str, object]


class PptPackageResponse(BaseModel):
    id: UUID
    run_id: UUID
    name: str
    price_tier: Decimal | None
    total_price: Decimal
    reason: str | None
    is_selected: bool
    items: list[PptPackageItemResponse]
    created_at: datetime
    updated_at: datetime


class PptGenerationTaskResponse(BaseModel):
    id: UUID
    project_id: UUID
    run_id: UUID
    template_file_id: UUID | None
    output_file_id: UUID | None
    status: PptGenerationStatus
    provider: str
    model: str
    prompt_version: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class PptGenerationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    use_default_template: bool = False
