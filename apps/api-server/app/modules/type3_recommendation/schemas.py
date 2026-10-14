from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Type3Node(BaseModel):
    model_config = ConfigDict(extra="forbid")
    node_id: str = Field(min_length=1, max_length=128)
    coordinate: str = Field(min_length=1, max_length=32)
    level: Literal["LEVEL1", "LEVEL2", "LEVEL3"]
    label: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=64)


class Type3SheetPreview(BaseModel):
    sheet_name: str
    header_row: int
    data_start_row: int
    max_row: int
    max_column: int
    mapping_json: dict[str, object]
    nodes: list[Type3Node]


class Type3TemplatePreview(BaseModel):
    template_file_id: UUID
    sheets: list[Type3SheetPreview]


class Type3OutputColumn(BaseModel):
    column_index: int = Field(ge=1)
    header: str
    duplicate: bool


class Type3SheetOutputStructure(BaseModel):
    sheet_name: str
    header_row: int = Field(ge=1)
    max_row: int
    columns: list[Type3OutputColumn]


class Type3ExportField(BaseModel):
    key: str
    label: str


class Type3SheetSelection(Type3SheetPreview):
    nodes: list[Type3Node] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_node_ids(self) -> "Type3SheetSelection":
        if len({node.node_id for node in self.nodes}) != len(self.nodes):
            raise ValueError("node_id must be unique within one sheet")
        if sum(node.node_id.startswith("manual:") for node in self.nodes) > 50:
            raise ValueError("at most 50 manual category nodes are allowed per sheet")
        return self


class Type3SheetSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheets: list[Type3SheetSelection] = Field(max_length=20)

    @model_validator(mode="after")
    def unique_sheets(self) -> "Type3SheetSelectionRequest":
        if len({item.sheet_name for item in self.sheets}) != len(self.sheets):
            raise ValueError("sheet_name must be unique")
        return self


class Type3RemarkAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gross_margin_min: Decimal | None = Field(default=None, ge=0, le=1)
    gross_margin_max: Decimal | None = Field(default=None, ge=0, le=1)
    agreement_price_min: Decimal | None = Field(default=None, ge=0)
    agreement_price_max: Decimal | None = Field(default=None, ge=0)
    jd_price_min: Decimal | None = Field(default=None, ge=0)
    jd_price_max: Decimal | None = Field(default=None, ge=0)
    discount_rate_min: Decimal | None = Field(default=None, ge=0, le=1)
    discount_rate_max: Decimal | None = Field(default=None, ge=0, le=1)
    required_brands: list[str] = Field(default_factory=list, max_length=20)


class Type3CatalogItem(BaseModel):
    category_key: str
    level: Literal["LEVEL1", "LEVEL2", "LEVEL3"]
    level1_name: str | None = None
    level2_name: str | None = None
    level3_name: str | None = None
    candidate_count: int


class Type3CategoryMatch(BaseModel):
    node_id: str
    category_keys: list[str] = Field(default_factory=list)


class Type3CategoryMatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    matches: list[Type3CategoryMatch]


class Type3RunSheetSummary(BaseModel):
    """The exact user-selected Sheet scope frozen into one Type-3 Run."""

    sheet_name: str
    selected_node_count: int = Field(ge=1)


class Type3RunResponse(BaseModel):
    id: UUID
    project_id: UUID
    project_status: str | None = None
    status: str
    raw_remark_snapshot: str
    parsed_remark: Type3RemarkAnalysis | None = None
    error: str | None = None
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    sheet_summaries: list[Type3RunSheetSummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class Type3CandidateResponse(BaseModel):
    id: UUID
    sheet_name: str
    product_id: UUID
    rank: int
    product_snapshot: dict[str, object]
    supplier_snapshot: dict[str, object]
    price_snapshot: dict[str, object]
    confirmed_at: datetime | None


class Type3CandidatePage(BaseModel):
    items: list[Type3CandidateResponse]
    total: int
    page: int
    page_size: int
    confirmed_total: int


class Type3CandidateSheetSummary(BaseModel):
    """Candidate counts for one source worksheet in an independent Type-3 Run."""

    sheet_name: str
    total: int
    confirmed_total: int


class Type3CandidateConfirmationRequest(BaseModel):
    """A Type-3-only confirmation scope; it never uses Type-4 confirmation contracts."""

    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[UUID] = Field(default_factory=list, max_length=500)
    select_all_unconfirmed: bool = False
    excluded_candidate_ids: list[UUID] = Field(default_factory=list, max_length=500)
    sheet_name: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_scope(self) -> "Type3CandidateConfirmationRequest":
        if not self.select_all_unconfirmed and not self.candidate_ids:
            raise ValueError(
                "candidate_ids is required unless selecting all unconfirmed candidates"
            )
        if self.select_all_unconfirmed and self.candidate_ids:
            raise ValueError("candidate_ids cannot be combined with select_all_unconfirmed")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("candidate_ids must be unique")
        if len(set(self.excluded_candidate_ids)) != len(self.excluded_candidate_ids):
            raise ValueError("excluded_candidate_ids must be unique")
        return self


class Type3CandidateUnconfirmationRequest(BaseModel):
    """The explicit Type-3 scope for returning confirmed candidates to pending."""

    model_config = ConfigDict(extra="forbid")

    candidate_ids: list[UUID] = Field(default_factory=list, max_length=500)
    select_all_confirmed: bool = False
    excluded_candidate_ids: list[UUID] = Field(default_factory=list, max_length=500)
    sheet_name: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_scope(self) -> "Type3CandidateUnconfirmationRequest":
        if not self.select_all_confirmed and not self.candidate_ids:
            raise ValueError(
                "candidate_ids is required unless selecting all confirmed candidates"
            )
        if self.select_all_confirmed and self.candidate_ids:
            raise ValueError("candidate_ids cannot be combined with select_all_confirmed")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("candidate_ids must be unique")
        if len(set(self.excluded_candidate_ids)) != len(self.excluded_candidate_ids):
            raise ValueError("excluded_candidate_ids must be unique")
        return self
