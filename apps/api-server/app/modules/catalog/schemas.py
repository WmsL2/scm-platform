import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


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
    model: str | None
    sku: str | None
    product_name: str | None
    item_number: str | None
    category_id: uuid.UUID
    category_path: str
    source_supplier_id: uuid.UUID
    source_supplier_name: str | None
    cost_price: Decimal
    agreement_price: Decimal | None
    jd_price: Decimal | None
    updated_at: datetime


class ProductDetailResponse(BaseModel):
    id: uuid.UUID
    listed_at: date | None
    brand: str | None
    image_reference: str | None
    model: str | None
    sku: str | None
    product_name: str | None
    category: CategoryResponse
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


class ProductCostUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cost_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
