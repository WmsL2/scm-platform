"""add project output mapping review

Revision ID: 20261013_0056
Revises: 20261013_0055
Create Date: 2026-10-13
"""

import sqlalchemy as sa

from alembic import op

revision = "20261013_0056"
down_revision = "20261013_0055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This branch originally used the same 0055 revision id as the Type 3
    # migration. Keep an already-upgraded developer database recoverable when
    # the branches are integrated, without overwriting its project mappings.
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("scm_bid_project")
    }
    if "output_mapping" not in columns:
        op.add_column("scm_bid_project", sa.Column("output_mapping", sa.JSON(), nullable=True))
    if "output_mapping_confirmed_by" not in columns:
        op.add_column(
            "scm_bid_project",
            sa.Column("output_mapping_confirmed_by", sa.CHAR(length=36), nullable=True),
        )
    if "output_mapping_confirmed_at" not in columns:
        op.add_column(
            "scm_bid_project",
            sa.Column("output_mapping_confirmed_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("scm_bid_project")
    }
    if "output_mapping_confirmed_at" in columns:
        op.drop_column("scm_bid_project", "output_mapping_confirmed_at")
    if "output_mapping_confirmed_by" in columns:
        op.drop_column("scm_bid_project", "output_mapping_confirmed_by")
    if "output_mapping" in columns:
        op.drop_column("scm_bid_project", "output_mapping")
