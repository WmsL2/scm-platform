"""freeze company and purchaser scopes for recommendation runs

Revision ID: 20261016_0058
Revises: 20261015_0057
Create Date: 2026-10-16
"""

import sqlalchemy as sa

from alembic import op

revision = "20261016_0058"
down_revision = "20261015_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_bid_project", sa.Column("recommendation_company_names", sa.JSON(), nullable=True)
    )
    op.add_column(
        "scm_bid_project",
        sa.Column("recommendation_purchasing_agents", sa.JSON(), nullable=True),
    )
    op.add_column(
        "scm_match_task", sa.Column("product_scope_snapshot", sa.JSON(), nullable=True)
    )
    op.add_column(
        "scm_recommendation_run", sa.Column("product_scope_snapshot", sa.JSON(), nullable=True)
    )
    op.add_column(
        "scm_type3_recommendation_run",
        sa.Column("product_scope_snapshot", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_scm_product_status_purchasing_agent",
        "scm_product",
        ["status", "purchasing_agent"],
    )


def downgrade() -> None:
    op.drop_index("ix_scm_product_status_purchasing_agent", table_name="scm_product")
    op.drop_column("scm_type3_recommendation_run", "product_scope_snapshot")
    op.drop_column("scm_recommendation_run", "product_scope_snapshot")
    op.drop_column("scm_match_task", "product_scope_snapshot")
    op.drop_column("scm_bid_project", "recommendation_purchasing_agents")
    op.drop_column("scm_bid_project", "recommendation_company_names")
