"""persist type-5 selected plans

Revision ID: 20261008_0047
Revises: 20260930_0046
"""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0047"
down_revision = "20260930_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_ppt_solution_plan",
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "scm_ppt_solution_plan",
        sa.Column("selected_by", sa.CHAR(length=36), nullable=True),
    )
    op.add_column(
        "scm_ppt_solution_plan",
        sa.Column("selected_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scm_ppt_solution_plan", "selected_at")
    op.drop_column("scm_ppt_solution_plan", "selected_by")
    op.drop_column("scm_ppt_solution_plan", "is_selected")
