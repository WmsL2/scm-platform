"""add project output mapping review

Revision ID: 20261013_0055
Revises: 20261012_0054
Create Date: 2026-10-13
"""

import sqlalchemy as sa

from alembic import op

revision = "20261013_0055"
down_revision = "20261012_0054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scm_bid_project", sa.Column("output_mapping", sa.JSON(), nullable=True))
    op.add_column(
        "scm_bid_project",
        sa.Column("output_mapping_confirmed_by", sa.CHAR(length=36), nullable=True),
    )
    op.add_column(
        "scm_bid_project",
        sa.Column("output_mapping_confirmed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scm_bid_project", "output_mapping_confirmed_at")
    op.drop_column("scm_bid_project", "output_mapping_confirmed_by")
    op.drop_column("scm_bid_project", "output_mapping")
