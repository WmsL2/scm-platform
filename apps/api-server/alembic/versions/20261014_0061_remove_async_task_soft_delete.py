"""remove unused async-task record soft-delete fields

Revision ID: 20261014_0061
Revises: 20261014_0060
"""

import sqlalchemy as sa

from alembic import op

revision = "20261014_0061"
down_revision = "20261014_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("scm_async_task", "deleted_by")
    op.drop_column("scm_async_task", "deleted_at")


def downgrade() -> None:
    op.add_column("scm_async_task", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("scm_async_task", sa.Column("deleted_by", sa.String(36), nullable=True))
