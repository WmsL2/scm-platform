"""add Product Master category filter indexes

Revision ID: 20260918_0031
Revises: 20260917_0030
"""

from alembic import op

revision = "20260918_0031"
down_revision = "20260917_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_scm_product_status_category_path",
        "scm_product",
        ["status", "category_level1_name", "category_level2_name", "category_level3_name"],
        mysql_length={
            "category_level1_name": 128,
            "category_level2_name": 128,
            "category_level3_name": 128,
        },
    )


def downgrade() -> None:
    op.drop_index("ix_scm_product_status_category_path", table_name="scm_product")
