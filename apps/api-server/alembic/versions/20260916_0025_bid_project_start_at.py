"""新增投标项目业务开始时间

Revision ID: 20260916_0025
Revises: 20260915_0024
"""

import sqlalchemy as sa

from alembic import op

revision = "20260916_0025"
down_revision = "20260915_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scm_bid_project", sa.Column("start_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("scm_bid_project", "start_at")
