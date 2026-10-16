# ruff: noqa: E501
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base
from app.common.uuid_type import UUIDChar36


class Type3SheetConfig(Base):
    __tablename__ = "scm_type3_sheet_config"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "sheet_name", name="uq_scm_type3_sheet_config_project_sheet"
        ),
        Index("ix_scm_type3_sheet_config_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    template_file_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"), nullable=False
    )
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    header_row: Mapped[int] = mapped_column(Integer, nullable=False)
    data_start_row: Mapped[int] = mapped_column(Integer, nullable=False)
    mapping_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    selected_nodes: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    updated_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class Type3Run(Base):
    __tablename__ = "scm_type3_recommendation_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED','ANALYZING','RETRIEVING','WAITING_CONFIRMATION','CONFIRMED','EXPORTED','FAILED','NO_CANDIDATES')",
            name="ck_scm_type3_run_status",
        ),
        Index("ix_scm_type3_run_project_created", "project_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    raw_remark_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    product_scope_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    parsed_remark: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    category_catalog_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    sheet_snapshot: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class Type3Candidate(Base):
    __tablename__ = "scm_type3_recommendation_candidate"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "sheet_name", "product_id", name="uq_scm_type3_candidate_run_sheet_product"
        ),
        Index("ix_scm_type3_candidate_run_sheet_rank", "run_id", "sheet_name", "rank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(),
        ForeignKey("scm_type3_recommendation_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sheet_name: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_product.id", ondelete="RESTRICT"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    product_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    supplier_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    price_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class Type3Export(Base):
    __tablename__ = "scm_type3_recommendation_export"
    __table_args__ = (
        UniqueConstraint("project_id", "run_id", "version_no", name="uq_scm_type3_export_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(),
        ForeignKey("scm_type3_recommendation_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    export_file_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    exported_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    exported_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
