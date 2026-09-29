"""freeze Type-4 category catalog snapshots

Revision ID: 20260929_0042
Revises: 20260928_0041
"""

import sqlalchemy as sa

from alembic import op

revision = "20260929_0042"
down_revision = "20260928_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_recommendation_run",
        sa.Column("category_catalog_snapshot", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    count = int(
        bind.scalar(
            sa.text(
                "SELECT COUNT(*) FROM scm_recommendation_run "
                "WHERE category_catalog_snapshot IS NOT NULL"
            )
        )
        or 0
    )
    if count:
        raise RuntimeError(
            "Cannot downgrade 20260929_0042 while category catalogue snapshots exist."
        )
    op.drop_column("scm_recommendation_run", "category_catalog_snapshot")
