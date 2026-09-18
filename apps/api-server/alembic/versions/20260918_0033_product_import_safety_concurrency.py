"""add Product Import normalized values and optimistic snapshots

Revision ID: 20260918_0033
Revises: 20260918_0032
"""

import sqlalchemy as sa

from alembic import op

revision = "20260918_0033"
down_revision = "20260918_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {
        column["name"] for column in inspector.get_columns("scm_product_import_row")
    }
    if "normalized_data" not in columns:
        op.add_column(
            "scm_product_import_row",
            sa.Column("normalized_data", sa.JSON(), nullable=True),
        )
    if "target_product_id" not in columns:
        op.add_column(
            "scm_product_import_row",
            sa.Column("target_product_id", sa.CHAR(length=36), nullable=True),
        )
    if "target_product_updated_at" not in columns:
        op.add_column(
            "scm_product_import_row",
            sa.Column("target_product_updated_at", sa.DateTime(), nullable=True),
        )
    indexes = {
        index["name"] for index in sa.inspect(bind).get_indexes("scm_product_import_row")
    }
    if "ix_scm_product_import_row_target_product_id" not in indexes:
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
