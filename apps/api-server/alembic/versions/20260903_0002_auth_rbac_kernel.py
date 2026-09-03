"""auth rbac kernel

Revision ID: 20260903_0002
Revises: 20260902_0001
"""

import sqlalchemy as sa

from alembic import op

revision = "20260903_0002"
down_revision = "20260902_0001"
branch_labels = None
depends_on = None

uuid = sa.CHAR(36)
audit = [
    sa.Column("created_by", sa.CHAR(36), nullable=True),
    sa.Column("updated_by", sa.CHAR(36), nullable=True),
    sa.Column(
        "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    ),
]


def upgrade() -> None:
    op.create_table(
        "sys_user",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("user_status", sa.String(16), nullable=False, server_default="ENABLED"),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "active_username",
            sa.String(64),
            sa.Computed("CASE WHEN is_deleted = 0 THEN username ELSE NULL END"),
        ),
        sa.CheckConstraint("user_status IN ('ENABLED', 'DISABLED')", name="ck_sys_user_status"),
        *audit,
    )
    op.create_index("uq_sys_user_active_username", "sys_user", ["active_username"], unique=True)
    op.create_table(
        "sys_role",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("role_code", sa.String(64), nullable=False, unique=True),
        sa.Column("role_name", sa.String(128), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *audit,
    )
    op.create_table(
        "sys_permission",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("permission_code", sa.String(128), nullable=False, unique=True),
        sa.Column("permission_name", sa.String(128), nullable=False),
        sa.Column("permission_type", sa.String(16), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("permission_type IN ('MENU', 'API', 'ACTION')"),
        *audit,
    )
    op.create_table(
        "sys_user_role",
        sa.Column(
            "user_id", uuid, sa.ForeignKey("sys_user.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column(
            "role_id", uuid, sa.ForeignKey("sys_role.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("created_by", sa.CHAR(36), nullable=True),
    )
    op.create_index("ix_sys_user_role_role_id", "sys_user_role", ["role_id"])
    op.create_table(
        "sys_role_permission",
        sa.Column(
            "role_id", uuid, sa.ForeignKey("sys_role.id", ondelete="RESTRICT"), primary_key=True
        ),
        sa.Column(
            "permission_id",
            uuid,
            sa.ForeignKey("sys_permission.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("created_by", sa.CHAR(36), nullable=True),
    )
    op.create_index(
        "ix_sys_role_permission_permission_id", "sys_role_permission", ["permission_id"]
    )


def downgrade() -> None:
    op.drop_table("sys_role_permission")
    op.drop_table("sys_user_role")
    op.drop_table("sys_permission")
    op.drop_table("sys_role")
    op.drop_table("sys_user")
