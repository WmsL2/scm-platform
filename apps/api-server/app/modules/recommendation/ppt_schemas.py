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
    item_count: int = Field(ge=1, le=500)

    @model_validator(mode="after")
    def valid_range(self) -> "PptPriceBandInput":
        if self.min_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price must not exceed max_price")
        return self


class PptRecommendationConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recommendation_mode: PptRecommendationMode
    price_bands: list[PptPriceBandInput] = Field(min_length=1, max_length=12)
    fulfillment_deadline: date | None = None

    @model_validator(mode="after")
    def require_non_overlapping_price_bands(self) -> "PptRecommendationConfigUpdateRequest":
        ordered = sorted(self.price_bands, key=lambda item: item.min_price or Decimal("0"))
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if (current.min_price or Decimal("0")) <= previous.max_price:
                raise ValueError("price bands must not overlap")
        return self


class PptRecommendationConfigResponse(PptRecommendationConfigUpdateRequest):
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class PptFrozenRecommendationConfig(PptRecommendationConfigUpdateRequest):
    """Immutable Type-5 generation inputs stored with one RecommendationRun."""

    # Legacy snapshots retain the former global fields. New direct-selection Runs
    # always use each price band's item_count and a single internal selection pass.
    candidate_count_per_band: int = Field(default=1, ge=1, le=500)
    plan_count_per_band: int = Field(default=1, ge=1, le=20)
    selection_mode: Literal["PLANS", "DIRECT"] = "PLANS"
    frozen_pool_statistics: "PptFrozenPoolStatistics | None" = None

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_band_quantities(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        result = dict(value)
        legacy_count = result.get("candidate_count_per_band")
        raw_bands = result.get("price_bands")
        if isinstance(raw_bands, list):
            result["price_bands"] = [
                {**band, "item_count": band.get("item_count", legacy_count)}
                if isinstance(band, dict)
                else band
                for band in raw_bands
            ]
        return result


class PptFrozenPoolPriceBandStatistics(BaseModel):
    """Immutable Type-5 pool count recorded before direct AI selection prunes it."""

    price_band_index: int = Field(ge=1, le=12)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal = Field(gt=0)
    frozen_candidate_count: int = Field(ge=0)
    requested_item_count: int = Field(ge=1, le=500)


class PptFrozenPoolStatistics(BaseModel):
    frozen_candidate_count: int = Field(ge=0)
    price_bands: list[PptFrozenPoolPriceBandStatistics] = Field(default_factory=list)


class PptPriceBandAvailabilityResponse(BaseModel):
    """Frozen candidate availability for one Type-5 price band."""

    price_band_index: int = Field(ge=1, le=12)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal = Field(gt=0)
    candidate_count: int = Field(ge=0)
    required_count: int = Field(ge=1)
    can_generate: bool
    generated_plan_count: int = Field(default=0, ge=0)
    requested_plan_count: int = Field(default=0, ge=0)
    failure_reason: str | None = None
    message: str


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
    selection_source: str
    selection_provider: str | None
    selection_model: str | None
    selection_prompt_version: str | None
    is_selected: bool
    selected_by: UUID | None
    selected_at: datetime | None
    items: list[PptSolutionPlanItemResponse]
    created_at: datetime


class PptPlanProposal(BaseModel):
    """AI selects a few server-issued short keys; the server fills the rest."""

    model_config = ConfigDict(extra="forbid")

    price_band_index: int = Field(ge=1, le=12)
    plan_no: int = Field(ge=1, le=20)
    name: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=2000)
    candidate_keys: list[str] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def unique_candidates(self) -> "PptPlanProposal":
        if len(self.candidate_keys) != len(set(self.candidate_keys)):
            raise ValueError("candidate_keys must be unique")
        if any(
            not value.startswith("c") or not value[1:].isdigit() for value in self.candidate_keys
        ):
            raise ValueError("candidate_keys must be server-issued short keys")
        return self


class PptPlanProposalList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plans: list[PptPlanProposal] = Field(default_factory=list, max_length=240)


class PptCandidateAssessment(BaseModel):
    """One compact scene-and-value assessment for a server-issued candidate key."""

    model_config = ConfigDict(extra="forbid")

    candidate_key: str = Field(pattern=r"^c[1-9]\d*$", max_length=32)
    scene_score: int = Field(ge=0, le=100)
    value_score: int = Field(ge=0, le=100)
    overall_score: int = Field(ge=0, le=100)


class PptCandidateAssessmentList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessments: list[PptCandidateAssessment] = Field(default_factory=list, max_length=500)


class PptDirectSelectionProposal(BaseModel):
    """Final direct Type-5 selection using only server-issued candidate keys."""

    model_config = ConfigDict(extra="forbid")

    candidate_keys: list[str] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_candidates(self) -> "PptDirectSelectionProposal":
        if len(self.candidate_keys) != len(set(self.candidate_keys)):
            raise ValueError("candidate_keys must be unique")
        if any(
            not value.startswith("c") or not value[1:].isdigit()
            for value in self.candidate_keys
        ):
            raise ValueError("candidate_keys must be server-issued short keys")
        return self


class PptPlanReferenceProposal(BaseModel):
    """One provider-authored plan using short, run-local candidate references."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    summary: str | None = Field(default=None, max_length=2000)
    candidate_refs: list[str] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def unique_candidate_refs(self) -> "PptPlanReferenceProposal":
        if len(self.candidate_refs) != len(set(self.candidate_refs)):
            raise ValueError("candidate_refs must be unique")
        return self


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
