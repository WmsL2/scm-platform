from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
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
