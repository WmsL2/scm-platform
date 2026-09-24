from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.recommendation.schemas import ManualCheck

MAX_RANKING_CANDIDATES = 30


class RequirementBlockingReason(StrEnum):
    UNUSABLE_REQUIREMENT = "UNUSABLE_REQUIREMENT"
    CONTRADICTORY_CONSTRAINTS = "CONTRADICTORY_CONSTRAINTS"
    COMPLIANCE_DECISION_REQUIRED = "COMPLIANCE_DECISION_REQUIRED"


class RequirementAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1000)
    keywords: list[str] = Field(min_length=1, max_length=20)
    category_keywords: list[str] = Field(default_factory=list, max_length=20)
    scenarios: list[str] = Field(default_factory=list, max_length=10)
    preferred_brands: list[str] = Field(default_factory=list, max_length=20)
    budget_min: Decimal | None = Field(default=None, ge=0)
    budget_max: Decimal | None = Field(default=None, ge=0)
    gross_margin_min: Decimal | None = Field(default=None, ge=0, le=1)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    fulfillment_mode: str | None = Field(default=None, max_length=64)
    explicit_category_keywords: list[str] = Field(default_factory=list, max_length=20)
    category_intents: list[str] = Field(default_factory=list, max_length=20)
    excluded_category_keywords: list[str] = Field(default_factory=list, max_length=20)
    required_brands: list[str] = Field(default_factory=list, max_length=20)
    excluded_brands: list[str] = Field(default_factory=list, max_length=20)
    search_keywords: list[str] = Field(default_factory=list, max_length=20)
    promotion_preference: str | None = Field(default=None, max_length=64)
    demand_mode: str | None = Field(default=None, max_length=64)
    quantity: int | None = Field(default=None, ge=1)
    manual_checks: list[ManualCheck] = Field(default_factory=list, max_length=20)
    needs_input: bool = False
    blocking_reasons: list[RequirementBlockingReason] = Field(default_factory=list, max_length=3)
    questions: list[str] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def validate_budget(self) -> "RequirementAnalysis":
        if self.budget_min is not None and self.budget_max is not None:
            if self.budget_min > self.budget_max:
                raise ValueError("budget_min cannot exceed budget_max")
        if self.needs_input and not self.questions:
            raise ValueError("questions are required when needs_input is true")
        if self.needs_input and not self.blocking_reasons:
            raise ValueError("blocking_reasons are required when needs_input is true")
        if not self.needs_input and self.blocking_reasons:
            raise ValueError("blocking_reasons require needs_input to be true")
        return self


class CategoryOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=512)
    level1: str | None = Field(default=None, max_length=255)
    level2: str | None = Field(default=None, max_length=255)
    level3: str | None = Field(default=None, max_length=255)
    product_count: int = Field(ge=0)


class CategoryChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_key: str = Field(min_length=1, max_length=512)
    reason: str = Field(min_length=1, max_length=1000)
    search_keywords: list[str] = Field(min_length=1, max_length=10)


class CategoryChoiceList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    choices: list[CategoryChoice] = Field(min_length=1, max_length=5)


class ProductSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_key: str = Field(min_length=1, max_length=512)
    keywords: list[str] = Field(min_length=1, max_length=10)
    preferred_brands: list[str] = Field(default_factory=list, max_length=20)
    agreement_price_min: Decimal | None = Field(default=None, ge=0)
    agreement_price_max: Decimal | None = Field(default=None, ge=0)
    limit: int = Field(default=20, ge=1, le=50)


class ProductCandidate(BaseModel):
    """Controlled product projection; never contains contacts or arbitrary database fields."""

    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    product_name: str = Field(min_length=1, max_length=1000)
    brand: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    category_path: str = Field(max_length=1000)
    agreement_price: Decimal | None = Field(default=None, ge=0)
    jd_price: Decimal | None = Field(default=None, ge=0)
    gross_margin: Decimal | None = None
    discount_rate: Decimal | None = None
    sales_volume: int | None = None
    positive_rating: Decimal | None = None
    selling_points: str | None = Field(default=None, max_length=1000)
    shipping_courier: str | None = Field(default=None, max_length=255)
    highlights: list[str] = Field(default_factory=list, max_length=10)


class RankedCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    score: Decimal = Field(ge=0, le=100)
    reason: str = Field(min_length=1, max_length=2000)


class CandidateRanking(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[RankedCandidate] = Field(min_length=1, max_length=MAX_RANKING_CANDIDATES)


class AgentRecommendationResult(BaseModel):
    analysis: RequirementAnalysis
    category_choices: list[CategoryChoice]
    candidates: list[RankedCandidate]
    provider: str
    model: str
    prompt_version: str
    tool_call_count: int = Field(ge=0, le=8)
