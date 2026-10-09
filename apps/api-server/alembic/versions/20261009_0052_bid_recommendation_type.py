"""add explicit recommendation type 1-5

Revision ID: 20261009_0052
Revises: 20261009_0051
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261009_0052"
down_revision: str | Sequence[str] | None = "20261009_0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scm_bid_project",
        sa.Column("recommendation_type", sa.String(length=40), nullable=True),
    )
    op.create_check_constraint(
        "ck_scm_bid_project_recommendation_type",
        "scm_bid_project",
        "recommendation_type IS NULL OR recommendation_type IN "
        "('TYPE_1_SPECIFICATION', 'TYPE_2_IDENTIFIED_PRODUCT', 'TYPE_3_CATEGORY', "
        "'TYPE_4_FREE', 'TYPE_5_PPT')",
    )
    op.execute(
        "UPDATE scm_bid_project SET recommendation_type = 'TYPE_4_FREE' "
        "WHERE project_type = 'FREE_RECOMMENDATION'"
    )
    op.execute(
        "UPDATE scm_bid_project SET recommendation_type = 'TYPE_5_PPT' "
        "WHERE project_type = 'PPT_SOLUTION'"
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_scm_bid_project_recommendation_type",
        "scm_bid_project",
        type_="check",
    )
    op.drop_column("scm_bid_project", "recommendation_type")
