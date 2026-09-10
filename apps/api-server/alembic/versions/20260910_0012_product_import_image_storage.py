"""add staged product import image storage key

Revision ID: 20260910_0012
Revises: 20260910_0011
"""

import sqlalchemy as sa

from alembic import op

revision = "20260910_0012"
down_revision = "20260910_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_product_import_row",
        sa.Column("image_storage_key", sa.String(1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scm_product_import_row", "image_storage_key")
