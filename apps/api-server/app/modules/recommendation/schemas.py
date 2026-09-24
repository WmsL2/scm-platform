from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.recommendation.template.schemas import RecommendationRunStatus


class FactoryDirectStatus(StrEnum):
    PENDING = "PENDING"
    YES = "YES"
    NO = "NO"


class ManualCheckStatus(StrEnum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"


class ManualCheckType(StrEnum):
    DROP_SHIPPING = "DROP_SHIPPING"
    INVENTORY_AVAILABLE = "INVENTORY_AVAILABLE"
    DELIVERY_DEADLINE = "DELIVERY_DEADLINE"
    LOGISTICS_CARRIER = "LOGISTICS_CARRIER"
    CUSTOM_PACKAGING = "CUSTOM_PACKAGING"
    INVOICE_REQUIREMENT = "INVOICE_REQUIREMENT"
    WARRANTY_REQUIREMENT = "WARRANTY_REQUIREMENT"
    REGION_RESTRICTION = "REGION_RESTRICTION"
    OTHER = "OTHER"


class ManualCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ManualCheckType
    label: str = Field(min_length=1, max_length=128)
    requirement_text: str = Field(min_length=1, max_length=1000)
    required: bool = True
    status: ManualCheckStatus = ManualCheckStatus.PENDING
    evidence: str | None = Field(default=None, max_length=4000)


class ParsedRequirement(BaseModel):
    """Validated bridge from C's AI parser to B's deterministic query."""

    model_config = ConfigDict(extra="forbid")

    gross_margin_min: Decimal | None = Field(
        default=None, ge=0, le=1, max_digits=9, decimal_places=4
    )
    jd_price_min: Decimal | None = Field(default=None, ge=0, max_digits=65, decimal_places=30)
    jd_price_max: Decimal | None = Field(default=None, ge=0, max_digits=65, decimal_places=30)
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
    manual_checks: list[ManualCheck] = Field(default_factory=list, max_length=20)

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
        if (
            self.jd_price_min is not None
            and self.jd_price_max is not None
            and self.jd_price_min > self.jd_price_max
        ):
            raise ValueError("jd_price_min must not exceed jd_price_max")
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


class ManualCheckUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checks: list["ManualCheckReviewUpdate"] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def require_unique_codes(self) -> "ManualCheckUpdateRequest":
        codes = [check.code for check in self.checks]
        if len(codes) != len(set(codes)):
            raise ValueError("manual check codes must be unique")
        return self


class ManualCheckReviewUpdate(BaseModel):
    """The review API cannot alter the server-created check contract."""

    model_config = ConfigDict(extra="forbid")

    code: ManualCheckType
    status: ManualCheckStatus
    evidence: str | None = Field(default=None, max_length=4000)

    @field_validator("evidence")
    @classmethod
    def strip_evidence(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class BatchConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[UUID] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def require_unique_candidates(self) -> "BatchConfirmationRequest":
        if len(self.candidate_ids) != len(set(self.candidate_ids)):
            raise ValueError("candidate_ids must be unique")
        return self
