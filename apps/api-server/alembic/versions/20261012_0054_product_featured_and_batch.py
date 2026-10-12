"""add product featured marker

Revision ID: 20261012_0054
Revises: 20261012_0053
Create Date: 2026-10-12
"""

from alembic import op
import sqlalchemy as sa

revision = "20261012_0054"
down_revision = "20261012_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_product",
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_scm_product_status_is_featured",
        "scm_product",
        ["status", "is_featured"],
    )


def downgrade() -> None:
    op.drop_index("ix_scm_product_status_is_featured", table_name="scm_product")
    op.drop_column("scm_product", "is_featured")
