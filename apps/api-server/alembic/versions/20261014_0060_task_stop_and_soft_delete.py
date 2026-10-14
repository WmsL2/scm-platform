"""add cooperative task stop requests and soft deletion

Revision ID: 20261014_0060
Revises: 20261014_0059
Create Date: 2026-10-14
"""

import sqlalchemy as sa

from alembic import op

revision = "20261014_0060"
down_revision = "20261014_0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scm_async_task", sa.Column("cancel_requested_at", sa.DateTime(), nullable=True))
    op.add_column("scm_async_task", sa.Column("cancel_requested_by", sa.CHAR(36), nullable=True))
    op.add_column("scm_async_task", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("scm_async_task", sa.Column("deleted_by", sa.CHAR(36), nullable=True))


def downgrade() -> None:
    op.drop_column("scm_async_task", "deleted_by")
    op.drop_column("scm_async_task", "deleted_at")
    op.drop_column("scm_async_task", "cancel_requested_by")
    op.drop_column("scm_async_task", "cancel_requested_at")
