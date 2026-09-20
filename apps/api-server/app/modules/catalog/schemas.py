# ruff: noqa: E501
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.modules.catalog.domain.lifecycle import ProductStatus


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_type: str
    level1_external_id: str | None
    level1_name: str
    level2_external_id: str | None
    level2_name: str
    level3_external_id: str | None
    level3_name: str
    deduction_rate: Decimal
    is_active: bool
    shelf_flag: str | None
    business_unit: str | None


class CategoryFilterOptionResponse(BaseModel):
    selection_key: str
    label: str
    level: Literal["LEVEL1", "LEVEL2", "LEVEL3"]
    level1_selection_key: str
    level2_selection_key: str
    level1_label: str
    level2_label: str


class CategoryFilterOptionPageResponse(BaseModel):
    items: list[CategoryFilterOptionResponse]
    has_more: bool


class ProductCategoryFilterOptionResponse(BaseModel):
    selection_key: str
    label: str
    level: Literal["LEVEL1", "LEVEL2", "LEVEL3"]
    level1_selection_key: str
    level2_selection_key: str
    level1_label: str
    level2_label: str


class ProductCategoryFilterOptionPageResponse(BaseModel):
    items: list[ProductCategoryFilterOptionResponse]
    has_more: bool


class CategoryWriteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: Literal["MALL_LEVEL3", "INDUSTRIAL_LINE"]
    level1_external_id: str | None = Field(default=None, max_length=128)
    level1_name: str = Field(min_length=1, max_length=255)
    level2_external_id: str | None = Field(default=None, max_length=128)
    level2_name: str = Field(min_length=1, max_length=255)
    level3_external_id: str | None = Field(default=None, max_length=128)
    level3_name: str = Field(min_length=1, max_length=255)
    deduction_rate: Decimal = Field(
        default=Decimal("0.0800"), ge=0, le=1, max_digits=9, decimal_places=4
    )
    is_active: bool = True
    shelf_flag: str | None = Field(default=None, max_length=32)
    business_unit: str | None = Field(default=None, max_length=128)

    @field_validator(
        "level1_name",
        "level2_name",
        "level3_name",
        "level1_external_id",
        "level2_external_id",
        "level3_external_id",
        "shelf_flag",
        "business_unit",
    )
    @classmethod
    def normalize_category_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class CategoryImportError(BaseModel):
    row_number: int
    field: str | None = None
    value: str | None = None
    reason: str


class CategoryImportResponse(BaseModel):
    total: int
    success: int
    skipped: int
    failed: int
    errors: list[CategoryImportError]


_PRODUCT_PRICE_FIELDS = (
    "cost_price",
    "market_price",
    "jd_price",
    "agreement_price",
    "agreement_purchase_price",
    "jd_self_operated_price",
)


def _serialize_product_price(value: Decimal | None) -> str | None:
    """Keep all significant price digits while retaining the legacy 4-place minimum."""
    if value is None:
        return None
    integer, _, fraction = format(value, "f").partition(".")
    fraction = fraction.rstrip("0")
    return f"{integer}.{fraction.ljust(4, '0')}"


class _ProductPriceResponseMixin(BaseModel):
    @field_serializer(
        *_PRODUCT_PRICE_FIELDS,
        when_used="json",
        check_fields=False,
    )
    def serialize_product_price(self, value: Decimal | None) -> str | None:
        return _serialize_product_price(value)


class ProductListItem(_ProductPriceResponseMixin):
    id: uuid.UUID
    company_name: str | None
    listed_at: date | None
    brand: str | None
    image_reference: str | None
    model: str | None
    sku: str | None
    product_name: str | None
    item_number: str | None
    jd_same_product_url: str | None
    category_path: str
    source_supplier_id: uuid.UUID
    source_supplier_name: str | None
    cost_price: Decimal | None
    agreement_price: Decimal | None
    jd_price: Decimal | None
    market_price: Decimal | None
    agreement_purchase_price: Decimal | None
    profit: Decimal | None
    jd_margin: Decimal | None
    deduction_review: Decimal | None
    gross_margin: Decimal | None
    purchasing_agent: str | None
    barcode_text: str | None
    certification_3c_code: str | None
    product_specification: str | None
    selling_points: str | None
    packaging_list: str | None
    warranty_period: str | None
    restricted_regions: str | None
    jd_self_operated_price: Decimal | None
    storefront_type: str | None
    reference_url: str | None
    sales_volume: int | None
    positive_rating: Decimal | None
    discount_rate: Decimal | None
    price_inflation_rate: Decimal | None
    tax_code: str | None
    invoice_name: str | None
    tax_category: str | None
    shipping_courier: str | None
    after_sales_policy: str | None
    remark: str | None
    status: ProductStatus
    created_by: uuid.UUID | None
    created_by_username: str | None
    created_at: datetime
    updated_by: uuid.UUID | None
    updated_by_username: str | None
    updated_at: datetime


class ProductDetailResponse(_ProductPriceResponseMixin):
    id: uuid.UUID
    company_name: str | None
    listed_at: date | None
    brand: str | None
    image_reference: str | None
    model: str | None
    sku: str | None
    product_name: str | None
    category_level1_name: str | None
    category_level2_name: str | None
    category_level3_name: str | None
    item_number: str | None
    jd_same_product_url: str | None
    cost_price: Decimal | None
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
    certification_3c_code: str | None
    deduction_review: Decimal | None
    product_specification: str | None
    selling_points: str | None
    packaging_list: str | None
    warranty_period: str | None
    gross_margin: Decimal | None
    remark: str | None
    discount_rate: Decimal | None
    restricted_regions: str | None
    jd_self_operated_price: Decimal | None
    reference_url: str | None
    storefront_type: str | None
    sales_volume: int | None
    positive_rating: Decimal | None
    price_inflation_rate: Decimal | None
    deduction_rate: Decimal | None
    tax_code: str | None
    invoice_name: str | None
    tax_category: str | None
    shipping_courier: str | None
    after_sales_policy: str | None
    status: ProductStatus
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
    cost_price: Decimal = Field(gt=0, max_digits=65, decimal_places=30)


class ProductUpdateRequest(BaseModel):
    """Editable Product Master fields; supplier, SKU and image reference are immutable here."""

    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, max_length=255)
    listed_at: date | None = None
    brand: str | None = Field(default=None, max_length=128)
    model: str | None = Field(default=None, max_length=255)
    product_name: str | None = Field(default=None, max_length=512)
    category_level1_name: str | None = Field(default=None, max_length=255)
    category_level2_name: str | None = Field(default=None, max_length=255)
    category_level3_name: str | None = Field(default=None, max_length=255)
    item_number: str | None = Field(default=None, max_length=255)
    jd_same_product_url: str | None = Field(default=None, max_length=2048)
    cost_price: Decimal | None = Field(default=None, gt=0, max_digits=65, decimal_places=30)
    market_price: Decimal | None = Field(default=None, max_digits=65, decimal_places=30)
    jd_price: Decimal | None = Field(default=None, max_digits=65, decimal_places=30)
    agreement_price: Decimal | None = Field(default=None, max_digits=65, decimal_places=30)
    agreement_purchase_price: Decimal | None = Field(
        default=None, max_digits=65, decimal_places=30
    )
    profit: Decimal | None = Field(default=None, max_digits=18, decimal_places=4)
    jd_margin: Decimal | None = Field(default=None, max_digits=9, decimal_places=4)
    deduction_review: Decimal | None = Field(default=None, max_digits=9, decimal_places=4)
    gross_margin: Decimal | None = Field(default=None, max_digits=9, decimal_places=4)
    purchasing_agent: str | None = Field(default=None, max_length=128)
    barcode_text: str | None = Field(default=None, max_length=255)
    certification_3c_code: str | None = Field(default=None, max_length=255)
    product_specification: str | None = None
    selling_points: str | None = None
    packaging_list: str | None = None
    warranty_period: str | None = Field(default=None, max_length=255)
    remark: str | None = None
    discount_rate: Decimal | None = Field(default=None, max_digits=9, decimal_places=4)
    restricted_regions: str | None = None
    jd_self_operated_price: Decimal | None = Field(
        default=None, max_digits=65, decimal_places=30
    )
    reference_url: str | None = Field(default=None, max_length=2048)
    storefront_type: str | None = Field(default=None, max_length=64)
    sales_volume: int | None = Field(default=None, ge=0)
    positive_rating: Decimal | None = Field(default=None, ge=0, le=1, max_digits=9, decimal_places=4)
    price_inflation_rate: Decimal | None = Field(default=None, max_digits=9, decimal_places=4)
    tax_code: str | None = Field(default=None, max_length=255)
    invoice_name: str | None = Field(default=None, max_length=512)
    tax_category: str | None = Field(default=None, max_length=255)
    shipping_courier: str | None = Field(default=None, max_length=255)
    after_sales_policy: str | None = None

    @field_validator(
        "company_name",
        "brand",
        "model",
        "product_name",
        "item_number",
        "jd_same_product_url",
        "purchasing_agent",
        "barcode_text",
        "certification_3c_code",
        "product_specification",
        "selling_points",
        "packaging_list",
        "warranty_period",
        "remark",
        "restricted_regions",
        "reference_url",
        "storefront_type",
        "tax_code",
        "invoice_name",
        "tax_category",
        "shipping_courier",
        "after_sales_policy",
        "category_level1_name",
        "category_level2_name",
        "category_level3_name",
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
    image_pending_save: bool
    category_path: str
    supplier_match_id: uuid.UUID | None
    is_valid: bool
    write_action: Literal["CREATE", "UPDATE"]
    changed_fields: list[str] | None
    is_imported: bool
    error_message: str | None
    warning_message: str | None


class ProductImportPreviewResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    status: str
    total_rows: int
    valid_rows: int
    update_rows: int
    invalid_rows: int
    imported_rows: int
    row_total: int
    page: int
    page_size: int
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
    created_count: int
    updated_count: int
    imported_rows: int
    valid_rows: int
    update_rows: int
    invalid_rows: int


class ProductImportDiscardResponse(BaseModel):
    id: uuid.UUID
    status: Literal["EXPIRED"]
