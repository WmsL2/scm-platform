"""add rotating refresh-token sessions

Revision ID: 20260911_0021
Revises: 20260911_0020
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_0021"
down_revision = "20260911_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sys_auth_session",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("user_id", sa.CHAR(36), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False),
        sa.Column("previous_refresh_token_hash", sa.String(64), nullable=True),
        sa.Column("previous_token_valid_until", sa.DateTime(), nullable=True),
        sa.Column("rotation_counter", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_activity_at", sa.DateTime(), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_reason", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["sys_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sys_auth_session_user_id", "sys_auth_session", ["user_id"])
    op.create_index(
        "ix_sys_auth_session_idle_expires_at",
        "sys_auth_session",
        ["idle_expires_at"],
    )
    op.create_index(
        "ix_sys_auth_session_absolute_expires_at",
        "sys_auth_session",
        ["absolute_expires_at"],
    )


def downgrade() -> None:
    op.drop_table("sys_auth_session")
