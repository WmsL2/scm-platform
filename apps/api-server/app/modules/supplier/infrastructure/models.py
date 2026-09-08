from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.models import Base
from app.common.uuid_type import UUIDChar36


class Supplier(Base):
    __tablename__ = "scm_supplier"
    __table_args__ = (
        CheckConstraint(
            "archive_status IN ('DRAFT', 'PENDING', 'ARCHIVED')",
            name="ck_scm_supplier_archive_status",
        ),
        CheckConstraint(
            "cooperation_status IN ('NORMAL', 'STOPPED', 'BLACKLIST')",
            name="ck_scm_supplier_cooperation_status",
        ),
        Index("ix_scm_supplier_archive_cooperation", "archive_status", "cooperation_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    supplier_code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    main_brands: Mapped[str] = mapped_column(Text, nullable=False)
    advantage: Mapped[str] = mapped_column(Text, nullable=False)
    archive_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="DRAFT")
    cooperation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="NORMAL"
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    archived_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    contacts: Mapped[list[SupplierContact]] = relationship(
        back_populates="supplier", lazy="selectin"
    )


class SupplierContact(Base):
    __tablename__ = "scm_supplier_contact"
    __table_args__ = (
        CheckConstraint(
            "contact_name IS NOT NULL OR contact_phone IS NOT NULL",
            name="ck_scm_supplier_contact_has_value",
        ),
        Index("ix_scm_supplier_contact_supplier_id", "supplier_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_supplier.id", ondelete="RESTRICT"), nullable=False
    )
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
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
    supplier: Mapped[Supplier] = relationship(back_populates="contacts")


class SupplierQualification(Base):
    __tablename__ = "scm_supplier_qualification"
    __table_args__ = (Index("ix_scm_supplier_qualification_supplier_id", "supplier_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_supplier.id", ondelete="RESTRICT"), nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
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


class SupplierCooperationRecord(Base):
    __tablename__ = "scm_supplier_cooperation_record"
    __table_args__ = (
        CheckConstraint(
            "from_status = 'NORMAL' AND to_status IN ('STOPPED', 'BLACKLIST')",
            name="ck_scm_supplier_cooperation_record_transition",
        ),
        CheckConstraint(
            "CHAR_LENGTH(TRIM(reason)) > 0", name="ck_scm_supplier_cooperation_record_reason"
        ),
        Index("ix_scm_supplier_cooperation_record_supplier_occurred", "supplier_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_supplier.id", ondelete="RESTRICT"), nullable=False
    )
    from_status: Mapped[str] = mapped_column(String(16), nullable=False)
    to_status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class SupplierImportBatch(Base):
    __tablename__ = "scm_supplier_import_batch"
    __table_args__ = (
        CheckConstraint(
            "status IN ('VALIDATED', 'CONFIRMED')", name="ck_scm_supplier_import_batch_status"
        ),
        CheckConstraint("total_rows >= 0", name="ck_scm_supplier_import_batch_total_rows"),
        CheckConstraint("valid_rows >= 0", name="ck_scm_supplier_import_batch_valid_rows"),
        CheckConstraint("invalid_rows >= 0", name="ck_scm_supplier_import_batch_invalid_rows"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="VALIDATED")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rows: Mapped[list[SupplierImportRow]] = relationship(back_populates="batch", lazy="selectin")


class SupplierImportRow(Base):
    __tablename__ = "scm_supplier_import_row"
    __table_args__ = (
        UniqueConstraint(
            "batch_id", "source_row_number", name="uq_scm_supplier_import_row_batch_source_row"
        ),
        Index("ix_scm_supplier_import_row_batch_id", "batch_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(),
        ForeignKey("scm_supplier_import_batch.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    main_brands: Mapped[str | None] = mapped_column(Text, nullable=True)
    advantage: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch: Mapped[SupplierImportBatch] = relationship(back_populates="rows")
