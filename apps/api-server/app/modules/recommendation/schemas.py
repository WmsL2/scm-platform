from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.common.contracts import PageResult
from app.modules.recommendation.template.schemas import RecommendationRunStatus


class FactoryDirectStatus(StrEnum):
    PENDING = "PENDING"
    YES = "YES"
    NO = "NO"


class ParsedRequirement(BaseModel):
    """Validated bridge from C's AI parser to B's deterministic query."""

    model_config = ConfigDict(extra="forbid")

    requirement_version: str | None = Field(default=None, max_length=16)
    # 模块4业务口径：点位复用既有正式字段 gross_margin，6% = 0.06。
    gross_margin_min: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=9, decimal_places=4
    )
    gross_margin_max: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=9, decimal_places=4
    )
    jd_price_min: Decimal | None = Field(default=None, ge=0, max_digits=65, decimal_places=30)
    jd_price_max: Decimal | None = Field(default=None, ge=0, max_digits=65, decimal_places=30)
    agreement_price_min: Decimal | None = Field(
        default=None, ge=0, max_digits=65, decimal_places=30
    )
    agreement_price_max: Decimal | None = Field(
        default=None, ge=0, max_digits=65, decimal_places=30
    )
    discount_rate_min: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=9, decimal_places=4
    )
    discount_rate_max: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=9, decimal_places=4
    )
    # V2 separates deterministic constraints from ranking signals.  The three legacy
    # fields remain readable so historical Run JSON can still be rendered.
    category_keywords: list[str] = Field(default_factory=list, max_length=20)
    brand_keywords: list[str] = Field(default_factory=list, max_length=20)
    scenario_keywords: list[str] = Field(default_factory=list, max_length=20)
    explicit_category_keywords: list[str] = Field(default_factory=list, max_length=20)
    category_intents: list[str] = Field(default_factory=list, max_length=20)
    excluded_category_keywords: list[str] = Field(default_factory=list, max_length=20)
    required_brands: list[str] = Field(default_factory=list, max_length=20)
    preferred_brands: list[str] = Field(default_factory=list, max_length=20)
    excluded_brands: list[str] = Field(default_factory=list, max_length=20)
    search_keywords: list[str] = Field(default_factory=list, max_length=20)
    scenarios: list[str] = Field(default_factory=list, max_length=20)
    promotion_preference: str | None = Field(default=None, max_length=64)
    demand_mode: str | None = Field(default=None, max_length=64)
    quantity: int | None = Field(default=None, ge=1)
    fulfillment_mode: str | None = Field(default=None, max_length=64)
    # Kept read-compatible for historical JSON; it is not evaluated by any flow.
    manual_checks: list[dict[str, object]] = Field(default_factory=list, max_length=20)

    @field_validator(
        "category_keywords", "brand_keywords", "scenario_keywords",
        "explicit_category_keywords", "category_intents", "excluded_category_keywords",
        "required_brands", "preferred_brands", "excluded_brands", "search_keywords", "scenarios",
    )
    @classmethod
    def normalize_keywords(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value and value.strip()]
        if any(len(value) > 64 for value in normalized):
            raise ValueError("keyword length must not exceed 64")
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_price_range(self) -> "ParsedRequirement":
        for lower, upper, label in (
            (self.jd_price_min, self.jd_price_max, "jd_price"),
            (self.agreement_price_min, self.agreement_price_max, "agreement_price"),
            (self.discount_rate_min, self.discount_rate_max, "discount_rate"),
            (self.gross_margin_min, self.gross_margin_max, "gross_margin"),
        ):
            if lower is not None and upper is not None and lower > upper:
                raise ValueError(f"{label}_min must not exceed {label}_max")
        return self


class RecommendationRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: RecommendationRunStatus
    raw_requirement_snapshot: str
    parsed_requirement: ParsedRequirement | None
    provider: str | None
    model: str | None
    prompt_version: str | None
    error: str | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class CategoryPath(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level1_name: str | None = Field(default=None, max_length=255)
    level2_name: str | None = Field(default=None, max_length=255)
    level3_name: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_category_value(self) -> "CategoryPath":
        if not any((self.level1_name, self.level2_name, self.level3_name)):
            raise ValueError("at least one category level is required")
        return self


class CategoryPoolItem(CategoryPath):
    candidate_count: int = Field(ge=0)


class CategoryChoiceInput(CategoryPath):
    source: str = Field(min_length=1, max_length=32)
    reason: str | None = Field(default=None, max_length=2000)
    candidate_count: int = Field(default=0, ge=0)


class ProductCandidateRow(BaseModel):
    product_id: UUID
    supplier_id: UUID
    sku: str | None
    product_name: str | None
    brand: str | None
    category_path: str
    jd_price: Decimal | None
    agreement_price: Decimal | None
    profit: Decimal | None
    gross_margin: Decimal | None
    discount_rate: Decimal | None
    sales_volume: int | None
    positive_rating: Decimal | None
    selling_points: str | None
    image_reference: str | None
    supplier_name: str
    shipping_courier: str | None


class CandidateRankInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    rank: int = Field(ge=1, le=30)
    score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=9, decimal_places=4)
    reason: str | None = Field(default=None, max_length=4000)
    manual_flags: dict[str, object] | None = None


class PersistCandidatesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[CandidateRankInput] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def require_unique_product_and_rank(self) -> "PersistCandidatesRequest":
        product_ids = [candidate.product_id for candidate in self.candidates]
        ranks = [candidate.rank for candidate in self.candidates]
        if len(product_ids) != len(set(product_ids)) or len(ranks) != len(set(ranks)):
            raise ValueError("candidate product_id and rank must both be unique")
        return self


class RecommendationConfirmationResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    campaign_price: Decimal | None
    delivery_status: str | None
    inventory_status: str | None
    factory_direct: FactoryDirectStatus
    fulfillment_cycle: str | None
    evidence: str | None
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    updated_at: datetime


class RecommendationCandidateResponse(BaseModel):
    id: UUID
    run_id: UUID
    product_id: UUID
    rank: int
    score: Decimal | None
    reason: str | None
    manual_flags: dict[str, object] | None
    product_snapshot: dict[str, object]
    supplier_snapshot: dict[str, object]
    price_snapshot: dict[str, object]
    confirmation_id: UUID | None = None
    factory_direct: FactoryDirectStatus | None = None
    confirmation: RecommendationConfirmationResponse | None = None
    created_at: datetime


class RecommendationCandidatePageResponse(PageResult[RecommendationCandidateResponse]):
    """A page of candidate snapshots plus selection-safe aggregate counts."""

    unconfirmed_total: int = Field(ge=0)
    confirmed_total: int = Field(ge=0)


class BatchConfirmationResult(BaseModel):
    confirmed_count: int = Field(ge=0)


class ConfirmationUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_price: Decimal | None = Field(default=None, ge=0, max_digits=65, decimal_places=30)
    delivery_status: str | None = Field(default=None, max_length=32)
    inventory_status: str | None = Field(default=None, max_length=32)
    factory_direct: FactoryDirectStatus = FactoryDirectStatus.PENDING
    fulfillment_cycle: str | None = Field(default=None, max_length=255)
    evidence: str | None = Field(default=None, max_length=4000)

    @field_validator("delivery_status", "inventory_status", "fulfillment_cycle", "evidence")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class BatchConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[UUID] = Field(default_factory=list, max_length=500)
    select_all: bool = False
    excluded_candidate_ids: list[UUID] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def require_unique_candidates(self) -> "BatchConfirmationRequest":
        if len(self.candidate_ids) != len(set(self.candidate_ids)):
            raise ValueError("candidate_ids must be unique")
        if len(self.excluded_candidate_ids) != len(set(self.excluded_candidate_ids)):
            raise ValueError("excluded_candidate_ids must be unique")
        if self.select_all:
            if self.candidate_ids:
                raise ValueError("candidate_ids must be empty when select_all is true")
        elif not self.candidate_ids:
            raise ValueError("candidate_ids is required when select_all is false")
        return self
