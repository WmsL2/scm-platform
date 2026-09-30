from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
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
from app.modules.bid.infrastructure.models import BidProject, BidProjectFile
from app.modules.catalog.infrastructure.models import Product

# Explicit imports ensure the referenced tables are registered when this module is loaded alone.
RELATED_MODEL_TYPES = (BidProject, BidProjectFile, Product)


class RecommendationRun(Base):
    __tablename__ = "scm_recommendation_run"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'QUEUED', 'ANALYZING', 'RETRIEVING', 'RANKING', "
            "'CANDIDATES_READY', 'WAITING_CONFIRMATION', 'CONFIRMED', 'EXPORTED', "
            "'FAILED', 'NO_CANDIDATES', 'NEEDS_INPUT', 'CANCELLED')",
            name="ck_scm_recommendation_run_status",
        ),
        Index("ix_scm_recommendation_run_project_id", "project_id"),
        Index("ix_scm_recommendation_run_status", "status"),
        Index("ix_scm_recommendation_run_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_requirement_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_requirement: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    category_catalog_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
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


class RecommendationCategoryChoice(Base):
    __tablename__ = "scm_recommendation_category_choice"
    __table_args__ = (Index("ix_scm_recommendation_category_choice_run_id", "run_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_recommendation_run.id", ondelete="RESTRICT"), nullable=False
    )
    level1_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level2_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level3_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class RecommendationCandidate(Base):
    __tablename__ = "scm_recommendation_candidate"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "product_id", name="uq_scm_recommendation_candidate_run_product"
        ),
        Index("ix_scm_recommendation_candidate_run_id", "run_id"),
        Index("ix_scm_recommendation_candidate_product_id", "product_id"),
        Index("ix_scm_recommendation_candidate_run_rank", "run_id", "rank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_recommendation_run.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_product.id", ondelete="RESTRICT"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    manual_flags: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    product_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    supplier_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    price_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class RecommendationConfirmation(Base):
    __tablename__ = "scm_recommendation_confirmation"
    __table_args__ = (
        UniqueConstraint("candidate_id", name="uq_scm_recommendation_confirmation_candidate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(),
        ForeignKey("scm_recommendation_candidate.id", ondelete="RESTRICT"),
        nullable=False,
    )
    campaign_price: Mapped[Decimal | None] = mapped_column(Numeric(65, 30), nullable=True)
    delivery_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    inventory_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    factory_direct: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="PENDING"
    )
    fulfillment_cycle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class RecommendationExport(Base):
    __tablename__ = "scm_recommendation_export"
    __table_args__ = (
        UniqueConstraint("export_file_id", name="uq_scm_recommendation_export_file"),
        UniqueConstraint(
            "project_id", "run_id", "version_no", name="uq_scm_recommendation_export_version"
        ),
        Index("ix_scm_recommendation_export_project_id", "project_id"),
        Index("ix_scm_recommendation_export_run_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_recommendation_run.id", ondelete="RESTRICT"), nullable=False
    )
    template_file_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"), nullable=False
    )
    template_mapping_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(),
        ForeignKey("scm_recommendation_template_mapping.id", ondelete="RESTRICT"),
        nullable=False,
    )
    export_file_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"), nullable=False
    )
    mapping_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    exported_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    exported_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class PptSolutionPackage(Base):
    __tablename__ = "scm_ppt_solution_package"
    __table_args__ = (
        Index("ix_scm_ppt_solution_package_run_id", "run_id"),
        Index("ix_scm_ppt_solution_package_selected", "run_id", "is_selected"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_recommendation_run.id", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price_tier: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    selected_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    selected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class PptRecommendationConfig(Base):
    __tablename__ = "scm_ppt_recommendation_config"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_scm_ppt_recommendation_config_project"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    recommendation_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    price_bands: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    candidate_count_per_band: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_count_per_band: Mapped[int] = mapped_column(Integer, nullable=False)
    fulfillment_deadline: Mapped[date | None] = mapped_column(nullable=True)
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


class PptSolutionPlan(Base):
    __tablename__ = "scm_ppt_solution_plan"
    __table_args__ = (
        CheckConstraint(
            "plan_type IN ('SINGLE', 'COMBINATION')",
            name="ck_scm_ppt_solution_plan_type",
        ),
        UniqueConstraint(
            "run_id", "price_band_index", "plan_no", name="uq_scm_ppt_solution_plan_run_band_no"
        ),
        Index("ix_scm_ppt_solution_plan_run_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_recommendation_run.id", ondelete="RESTRICT"), nullable=False
    )
    price_band_index: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_no: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_type: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    selection_source: Mapped[str] = mapped_column(String(16), nullable=False)
    selection_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    selection_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selection_prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class PptSolutionPackageItem(Base):
    __tablename__ = "scm_ppt_solution_package_item"
    __table_args__ = (
        UniqueConstraint(
            "package_id", "candidate_id", name="uq_scm_ppt_solution_package_item_candidate"
        ),
        Index("ix_scm_ppt_solution_package_item_package_id", "package_id"),
        Index("ix_scm_ppt_solution_package_item_candidate_id", "candidate_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_ppt_solution_package.id", ondelete="RESTRICT"), nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(),
        ForeignKey("scm_recommendation_candidate.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )


class PptGenerationTask(Base):
    __tablename__ = "scm_ppt_generation_task"
    __table_args__ = (
        CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_scm_ppt_generation_task_status",
        ),
        Index("ix_scm_ppt_generation_task_project_id", "project_id"),
        Index("ix_scm_ppt_generation_task_run_id", "run_id"),
        Index("ix_scm_ppt_generation_task_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_recommendation_run.id", ondelete="RESTRICT"), nullable=False
    )
    template_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"), nullable=True
    )
    output_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_artifact_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
