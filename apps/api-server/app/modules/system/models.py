import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
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
