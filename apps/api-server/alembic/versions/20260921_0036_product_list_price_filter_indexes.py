"""add Product List JD price and profit filter indexes

Revision ID: 20260921_0036
Revises: 20260920_0035
"""

from alembic import op

revision = "20260921_0036"
down_revision = "20260920_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_scm_product_status_jd_price", "scm_product", ["status", "jd_price"])
    op.create_index("ix_scm_product_status_profit", "scm_product", ["status", "profit"])


def downgrade() -> None:
    op.drop_index("ix_scm_product_status_profit", table_name="scm_product")
    op.drop_index("ix_scm_product_status_jd_price", table_name="scm_product")
