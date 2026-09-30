"""add type-5 plan AI selection audit

Revision ID: 20260930_0046
Revises: 20260930_0045
"""

import sqlalchemy as sa

from alembic import op

revision = "20260930_0046"
down_revision = "20260930_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_ppt_solution_plan",
        sa.Column(
            "selection_source", sa.String(16), nullable=False, server_default="DETERMINISTIC"
        ),
    )
    op.add_column(
        "scm_ppt_solution_plan",
        sa.Column("selection_provider", sa.String(64), nullable=True),
    )
    op.add_column(
        "scm_ppt_solution_plan",
        sa.Column("selection_model", sa.String(128), nullable=True),
    )
    op.add_column(
        "scm_ppt_solution_plan",
        sa.Column("selection_prompt_version", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scm_ppt_solution_plan", "selection_prompt_version")
    op.drop_column("scm_ppt_solution_plan", "selection_model")
    op.drop_column("scm_ppt_solution_plan", "selection_provider")
    op.drop_column("scm_ppt_solution_plan", "selection_source")
