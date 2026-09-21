"""add Product List company filter index

Revision ID: 20260921_0037
Revises: 20260921_0036
"""

from alembic import op

revision = "20260921_0037"
down_revision = "20260921_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_scm_product_status_company_name", "scm_product", ["status", "company_name"]
    )


def downgrade() -> None:
    op.drop_index("ix_scm_product_status_company_name", table_name="scm_product")
