import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.catalog.domain.lifecycle import ProductStatus


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_type: str
    level1_name: str
    level2_name: str
    level3_name: str
    deduction_rate: Decimal
    is_active: bool


class ProductListItem(BaseModel):
    id: uuid.UUID
    listed_at: date | None
    brand: str | None
    image_reference: str | None
    model: str | None
    sku: str | None
    product_name: str | None
    item_number: str | None
    category_id: uuid.UUID | None
    category_path: str
    source_supplier_id: uuid.UUID
    source_supplier_name: str | None
    cost_price: Decimal
    agreement_price: Decimal | None
    jd_price: Decimal | None
    status: ProductStatus
    updated_at: datetime


class ProductDetailResponse(BaseModel):
    id: uuid.UUID
    listed_at: date | None
    brand: str | None
    image_reference: str | None
    model: str | None
    sku: str | None
    product_name: str | None
    category: CategoryResponse | None
    category_level1_name: str | None
    category_level2_name: str | None
    category_level3_name: str | None
    item_number: str | None
    jd_same_product_url: str | None
    cost_price: Decimal
    market_price: Decimal | None
    jd_price: Decimal | None
    agreement_price: Decimal | None
    agreement_purchase_price: Decimal | None
    profit: Decimal | None
    jd_margin: Decimal | None
    purchasing_agent: str | None
    source_supplier_id: uuid.UUID
    source_supplier_name: str | None
    barcode_text: str | None
    deduction_review: Decimal | None
    product_specification: str | None
    selling_points: str | None
    gross_margin: Decimal | None
    remark: str | None
    discount_rate: Decimal | None
    restricted_regions: str | None
    jd_self_operated_price: Decimal | None
    reference_url: str | None
    storefront_type: str | None
    price_inflation_rate: Decimal | None
    deduction_rate: Decimal | None
    created_at: datetime
    updated_at: datetime


class ProductLifecycleResponse(BaseModel):
    id: uuid.UUID
    status: ProductStatus


class ProductPurgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: Literal[True]


class ProductPurgeResponse(BaseModel):
    id: uuid.UUID
    status: str = "PURGED"


class ProductCostUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cost_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)


class ProductUpdateRequest(BaseModel):
    """Editable source-business fields; pricing and category controls stay out of this contract."""

    model_config = ConfigDict(extra="forbid")

    listed_at: date | None = None
    brand: str | None = Field(default=None, max_length=128)
    image_reference: str | None = Field(default=None, max_length=2048)
    model: str | None = Field(default=None, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=255)
    product_name: str | None = Field(default=None, max_length=512)
    item_number: str | None = Field(default=None, max_length=255)
    jd_same_product_url: str | None = Field(default=None, max_length=2048)
    purchasing_agent: str | None = Field(default=None, max_length=128)
    source_supplier_id: uuid.UUID | None = None
    barcode_text: str | None = Field(default=None, max_length=255)
    product_specification: str | None = None
    selling_points: str | None = None
    remark: str | None = None
    restricted_regions: str | None = None
    reference_url: str | None = Field(default=None, max_length=2048)
    storefront_type: str | None = Field(default=None, max_length=64)

    @field_validator(
        "brand",
        "image_reference",
        "model",
        "sku",
        "product_name",
        "item_number",
        "jd_same_product_url",
        "purchasing_agent",
        "barcode_text",
        "product_specification",
        "selling_points",
        "remark",
        "restricted_regions",
        "reference_url",
        "storefront_type",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class ProductSourceSupplierCandidateResponse(BaseModel):
    id: uuid.UUID
    supplier_code: str
    supplier_name: str
    main_brands: str


class ProductImportSupplierMatchResponse(BaseModel):
    id: uuid.UUID
    supplier_name_normalized: str
    match_status: str
    match_method: str | None
    matched_supplier_id: uuid.UUID | None
    matched_supplier_code: str | None
    matched_supplier_name: str | None


class ProductImportRowResponse(BaseModel):
    source_row_number: int
    product_name: str | None
    supplier_name_raw: str | None
    image_saved: bool
    category_path: str
    category_id: uuid.UUID | None
    supplier_match_id: uuid.UUID | None
    is_valid: bool
    is_imported: bool
    error_message: str | None
    warning_message: str | None


class ProductImportPreviewResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    imported_rows: int
    rows: list[ProductImportRowResponse]
    supplier_matches: list[ProductImportSupplierMatchResponse]


class ProductImportResolveSupplierRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    supplier_id: uuid.UUID


class ProductImportSupplierCandidateResponse(BaseModel):
    id: uuid.UUID
    supplier_code: str
    supplier_name: str
    main_brands: str


class ProductImportConfirmResponse(BaseModel):
    id: uuid.UUID
    status: str
    imported_count: int
    imported_rows: int
    valid_rows: int
    invalid_rows: int
