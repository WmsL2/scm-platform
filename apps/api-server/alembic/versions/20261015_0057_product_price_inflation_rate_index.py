"""index product price inflation rate filter

Revision ID: 20261015_0057
Revises: 20261013_0056
Create Date: 2026-10-15
"""

from alembic import op


revision = "20261015_0057"
down_revision = "20261013_0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_scm_product_price_inflation_rate",
        "scm_product",
        ["price_inflation_rate"],
    )


def downgrade() -> None:
    op.drop_index("ix_scm_product_price_inflation_rate", table_name="scm_product")
