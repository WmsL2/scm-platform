"""remove aggregate price from type-5 plans

Revision ID: 20260930_0045
Revises: 20260930_0044
"""

import sqlalchemy as sa
from alembic import op

revision = "20260930_0045"
down_revision = "20260930_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("scm_ppt_solution_plan", "total_price")


def downgrade() -> None:
    op.add_column(
        "scm_ppt_solution_plan",
        sa.Column("total_price", sa.Numeric(18, 4), nullable=False, server_default="0"),
    )
