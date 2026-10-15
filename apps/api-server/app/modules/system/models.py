import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import Base
from app.common.uuid_type import UUIDChar36


class User(Base):
    __tablename__ = "sys_user"
    __table_args__ = (
        CheckConstraint(
            "user_status IN ('PENDING', 'ENABLED', 'DISABLED', 'REJECTED')",
            name="ck_sys_user_status",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="ENABLED")
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class Role(Base):
    __tablename__ = "sys_role"
    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    role_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
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


class Permission(Base):
    __tablename__ = "sys_permission"
    __table_args__ = (CheckConstraint("permission_type IN ('MENU','API','ACTION')"),)
    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    permission_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    permission_name: Mapped[str] = mapped_column(String(128), nullable=False)
    permission_type: Mapped[str] = mapped_column(String(16), nullable=False)
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


class UserRole(Base):
    __tablename__ = "sys_user_role"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("sys_user.id", ondelete="RESTRICT"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("sys_role.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)


class RolePermission(Base):
    __tablename__ = "sys_role_permission"
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("sys_role.id", ondelete="RESTRICT"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(),
        ForeignKey("sys_permission.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)


class BusinessSequence(Base):
    __tablename__ = "sys_biz_sequence"
    __table_args__ = (CheckConstraint("next_value >= 1", name="ck_sys_biz_sequence_next_value"),)

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    sequence_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    next_value: Mapped[int] = mapped_column(BigInteger, nullable=False)
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


class AsyncTask(Base):
    """Durable, cross-process task record for bid-project heavy work.

    This is deliberately independent from the legacy match/PPT task rows.  Those
    tables remain the domain-specific history; this table owns queue delivery,
    leases and operational progress.
    """

    __tablename__ = "scm_async_task"
    __table_args__ = (
        CheckConstraint(
            "task_kind IN ('TYPE1_MATCH','TYPE2_MATCH','TYPE3_CANDIDATE_GENERATION',"
            "'TYPE4_RECOMMENDATION_AGENT','TYPE5_RECOMMENDATION_GENERATION',"
            "'TYPE5_PPT_GENERATION','MAPPING_STRUCTURE_ANALYSIS')",
            name="ck_scm_async_task_kind",
        ),
        CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','CANCELLED')",
            name="ck_scm_async_task_status",
        ),
        Index("ix_scm_async_task_project_status", "project_id", "status"),
        Index("ix_scm_async_task_status_created", "status", "created_at"),
        Index("ix_scm_async_task_lease_expires_at", "lease_expires_at"),
        Index("ix_scm_async_task_run_id", "run_id"),
        Index("ix_scm_async_task_kind_status", "task_kind", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUIDChar36(), nullable=True)
    task_kind: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    progress_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )


class MappingAnalysisCache(Base):
    """Persistent result cache owned by the mapping worker.

    Web requests only look up or enqueue a cache key; synchronous workbook
    parsing is intentionally limited to the dedicated mapping process.
    """

    __tablename__ = "scm_mapping_analysis_cache"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','FAILED')",
            name="ck_scm_mapping_analysis_cache_status",
        ),
        Index(
            "uq_scm_mapping_analysis_cache_lookup",
            "project_id",
            "file_id",
            "analysis_key",
            unique=True,
        ),
        Index("ix_scm_mapping_analysis_cache_task_id", "async_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(UUIDChar36(), nullable=False)
    async_task_id: Mapped[uuid.UUID] = mapped_column(
        UUIDChar36(), ForeignKey("scm_async_task.id", ondelete="RESTRICT"), nullable=False
    )
    analysis_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="PENDING")
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
