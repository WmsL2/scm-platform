from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base
from app.common.uuid_type import UUIDChar36


class Category(Base):
    __tablename__ = "scm_category"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('MALL_LEVEL3', 'INDUSTRIAL_LINE')",
            name="ck_scm_category_source_type",
        ),
        UniqueConstraint(
            "source_type",
            "level3_external_id",
            name="uq_scm_category_source_level3_external",
        ),
        Index("ix_scm_category_source_type", "source_type"),
        Index("ix_scm_category_level3_name", "level3_name"),
        Index("ix_scm_category_is_active", "is_active"),
        Index("ix_scm_category_business_unit", "business_unit"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    level1_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    level1_name: Mapped[str] = mapped_column(String(255), nullable=False)
    level2_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    level2_name: Mapped[str] = mapped_column(String(255), nullable=False)
    level3_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    level3_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deduction_rate: Mapped[Decimal] = mapped_column(
        Numeric(9, 4), nullable=False, server_default="0.0800"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    shelf_flag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class Product(Base):
    __tablename__ = "scm_product"
    __table_args__ = (
        Index("ix_scm_product_category_id", "category_id"),
        Index("ix_scm_product_source_supplier_id", "source_supplier_id"),
        Index("ix_scm_product_listed_at", "listed_at"),
        Index("ix_scm_product_brand", "brand"),
        Index("ix_scm_product_model", "model"),
        Index("ix_scm_product_sku", "sku"),
        Index("ix_scm_product_product_name", "product_name"),
        Index("ix_scm_product_item_number", "item_number"),
        Index("ix_scm_product_barcode_text", "barcode_text"),
        Index("ix_scm_product_updated_at", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    listed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    image_reference: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(255), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_category.id", ondelete="RESTRICT"), nullable=False
    )
    item_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jd_same_product_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    market_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    jd_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    agreement_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    agreement_purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    jd_margin: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    purchasing_agent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_supplier.id", ondelete="RESTRICT"), nullable=False
    )
    barcode_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deduction_review: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    product_specification: Mapped[str | None] = mapped_column(Text, nullable=True)
    selling_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    gross_margin: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    restricted_regions: Mapped[str | None] = mapped_column(Text, nullable=True)
    jd_self_operated_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    storefront_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price_inflation_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    deduction_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
