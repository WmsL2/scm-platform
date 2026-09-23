from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base
from app.common.uuid_type import UUIDChar36
from app.modules.catalog.infrastructure.models import Category, Product
from app.modules.supplier.infrastructure.models import Supplier

# 关联表必须在本模块单独加载时注册到同一份 SQLAlchemy 元数据中。
RELATED_MODEL_TYPES = (Category, Product, Supplier)


class BidTemplate(Base):
    __tablename__ = "scm_bid_template"
    __table_args__ = (
        UniqueConstraint("template_code", "version", name="uq_scm_bid_template_code_version"),
        Index("ix_scm_bid_template_fingerprint", "fingerprint"),
        Index("ix_scm_bid_template_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    template_code: Mapped[str] = mapped_column(String(64), nullable=False)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    header_row: Mapped[int] = mapped_column(Integer, nullable=False)
    data_start_row: Mapped[int] = mapped_column(Integer, nullable=False)
    import_mapping: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    export_mapping: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
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


class BidProject(Base):
    __tablename__ = "scm_bid_project"
    __table_args__ = (
        CheckConstraint(
            "status IN ('IMPORTED', 'MATCHING', 'SELECTING', 'READY', 'EXPORTED', "
            "'SUBMITTED', 'WON', 'LOST')",
            name="ck_scm_bid_project_status",
        ),
        CheckConstraint(
            "import_status IN ('PARSED', 'MAPPING_REQUIRED', 'FAILED', 'NOT_REQUIRED')",
            name="ck_scm_bid_project_import_status",
        ),
        CheckConstraint(
            "project_type IN ('FILTER_RECOMMENDATION', 'FREE_RECOMMENDATION', 'PPT_SOLUTION')",
            name="ck_scm_bid_project_project_type",
        ),
        Index("ix_scm_bid_project_status", "status"),
        Index("ix_scm_bid_project_created_at", "created_at"),
        Index("ix_scm_bid_project_buyer_name", "buyer_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_template.id", ondelete="RESTRICT"), nullable=True
    )
    template_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    project_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="FILTER_RECOMMENDATION"
    )
    import_status: Mapped[str] = mapped_column(String(32), nullable=False)
    import_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    processed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    submitted_file_id: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class BidProjectFile(Base):
    __tablename__ = "scm_bid_project_file"
    __table_args__ = (
        CheckConstraint(
            "file_type IN ('ORIGINAL', 'QUOTED_EXPORT', 'RECOMMENDATION_TEMPLATE', "
            "'RECOMMENDATION_EXPORT')",
            name="ck_scm_bid_project_file_type",
        ),
        UniqueConstraint(
            "project_id", "file_type", "version_no", name="uq_scm_bid_project_file_version"
        ),
        Index("ix_scm_bid_project_file_project_id", "project_id"),
        Index("ix_scm_bid_project_file_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class BidProjectItem(Base):
    __tablename__ = "scm_bid_project_item"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'NO_MATCH', 'UNIQUE_MATCH', 'MULTIPLE_MATCH', "
            "'SELECTED', 'NO_QUOTE')",
            name="ck_scm_bid_project_item_status",
        ),
        UniqueConstraint(
            "project_id",
            "sheet_name",
            "source_row_number",
            name="uq_scm_bid_project_item_source_row",
        ),
        Index("ix_scm_bid_project_item_project_id", "project_id"),
        Index("ix_scm_bid_project_item_status", "status"),
        Index("ix_scm_bid_project_item_category_id", "category_id"),
        Index("ix_scm_bid_project_item_current_selection_id", "current_selection_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_data: Mapped[dict[str, str | int | float | None]] = mapped_column(JSON, nullable=False)
    product_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specification: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDChar36(), ForeignKey("scm_category.id", ondelete="RESTRICT"), nullable=True
    )
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    buyer_item_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="PENDING")
    current_selection_id: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    no_quote_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class BidProjectEvent(Base):
    __tablename__ = "scm_bid_project_event"
    __table_args__ = (
        Index("ix_scm_bid_project_event_project_id", "project_id"),
        Index("ix_scm_bid_project_event_occurred_at", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class MatchTask(Base):
    __tablename__ = "scm_match_task"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_scm_match_task_status",
        ),
        Index("ix_scm_match_task_project_id", "project_id"),
        Index("ix_scm_match_task_status", "status"),
        Index("ix_scm_match_task_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    total_item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    processed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class MatchCandidate(Base):
    __tablename__ = "scm_match_candidate"
    __table_args__ = (
        UniqueConstraint(
            "match_task_id",
            "project_item_id",
            "product_id",
            name="uq_scm_match_candidate_task_item_product",
        ),
        Index("ix_scm_match_candidate_project_item_id", "project_item_id"),
        Index("ix_scm_match_candidate_product_id", "product_id"),
        Index("ix_scm_match_candidate_supplier_id", "supplier_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    match_task_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_match_task.id", ondelete="RESTRICT"), nullable=False
    )
    project_item_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project_item.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_product.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_supplier.id", ondelete="RESTRICT"), nullable=False
    )
    score: Mapped[Decimal] = mapped_column(Numeric(9, 4), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    match_method: Mapped[str] = mapped_column(String(32), nullable=False)
    match_reason: Mapped[dict[str, str | int | float | None]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class BidItemSelection(Base):
    __tablename__ = "scm_bid_item_selection"
    __table_args__ = (
        Index("ix_scm_bid_item_selection_project_item_id", "project_item_id"),
        Index("ix_scm_bid_item_selection_product_id", "product_id"),
        Index("ix_scm_bid_item_selection_supplier_id", "supplier_id"),
        Index("ix_scm_bid_item_selection_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_item_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project_item.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDChar36(), ForeignKey("scm_match_candidate.id", ondelete="RESTRICT"), nullable=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_product.id", ondelete="RESTRICT"), nullable=False
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_supplier.id", ondelete="RESTRICT"), nullable=False
    )
    selected_unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    requirement_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    product_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    supplier_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    price_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
