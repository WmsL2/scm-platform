"""add Product Import normalized values and optimistic snapshots

Revision ID: 20260918_0031
Revises: 20260917_0030
"""

import sqlalchemy as sa

from alembic import op

revision = "20260918_0031"
down_revision = "20260917_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scm_product_import_row", sa.Column("normalized_data", sa.JSON(), nullable=True))
    op.add_column(
        "scm_product_import_row",
        sa.Column("target_product_id", sa.CHAR(length=36), nullable=True),
    )
    op.add_column(
        "scm_product_import_row",
        sa.Column("target_product_updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_scm_product_import_row_target_product_id",
        "scm_product_import_row",
        ["target_product_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scm_product_import_row_target_product_id",
        table_name="scm_product_import_row",
    )
    op.drop_column("scm_product_import_row", "target_product_updated_at")
    op.drop_column("scm_product_import_row", "target_product_id")
    op.drop_column("scm_product_import_row", "normalized_data")
