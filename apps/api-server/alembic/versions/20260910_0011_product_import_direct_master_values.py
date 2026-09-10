"""store direct category and price values from product imports

Revision ID: 20260910_0011
Revises: 20260910_0010
"""

import sqlalchemy as sa

from alembic import op

revision = "20260910_0011"
down_revision = "20260910_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "scm_product",
        "category_id",
        existing_type=sa.CHAR(36),
        nullable=True,
    )
    op.add_column("scm_product", sa.Column("category_level1_name", sa.String(255), nullable=True))
    op.add_column("scm_product", sa.Column("category_level2_name", sa.String(255), nullable=True))
    op.add_column("scm_product", sa.Column("category_level3_name", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("scm_product", "category_level3_name")
    op.drop_column("scm_product", "category_level2_name")
    op.drop_column("scm_product", "category_level1_name")
    op.alter_column(
        "scm_product",
        "category_id",
        existing_type=sa.CHAR(36),
        nullable=False,
    )
