"""add Product Master 2026 business fields and filter indexes

Revision ID: 20260917_0030
Revises: 20260917_0029
"""

import sqlalchemy as sa

from alembic import op

revision = "20260917_0030"
down_revision = "20260917_0029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scm_product", sa.Column("company_name", sa.String(255), nullable=True))
    op.add_column(
        "scm_product", sa.Column("certification_3c_code", sa.String(255), nullable=True)
    )
    op.add_column("scm_product", sa.Column("packaging_list", sa.Text(), nullable=True))
    op.add_column("scm_product", sa.Column("warranty_period", sa.String(255), nullable=True))
    op.add_column("scm_product", sa.Column("sales_volume", sa.BigInteger(), nullable=True))
    op.add_column("scm_product", sa.Column("positive_rating", sa.Numeric(9, 4), nullable=True))
    op.add_column("scm_product", sa.Column("tax_code", sa.String(255), nullable=True))
    op.add_column("scm_product", sa.Column("invoice_name", sa.String(512), nullable=True))
    op.add_column("scm_product", sa.Column("tax_category", sa.String(255), nullable=True))
    op.add_column("scm_product", sa.Column("shipping_courier", sa.String(255), nullable=True))
    op.add_column("scm_product", sa.Column("after_sales_policy", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_scm_product_sales_volume_nonnegative",
        "scm_product",
        "sales_volume IS NULL OR sales_volume >= 0",
    )
    op.create_check_constraint(
        "ck_scm_product_positive_rating_range",
        "scm_product",
        "positive_rating IS NULL OR (positive_rating >= 0 AND positive_rating <= 1)",
    )
    op.create_index("ix_scm_product_cost_price", "scm_product", ["cost_price"])
    op.create_index("ix_scm_product_agreement_price", "scm_product", ["agreement_price"])
    op.create_index("ix_scm_product_discount_rate", "scm_product", ["discount_rate"])
    op.create_index("ix_scm_product_sales_volume", "scm_product", ["sales_volume"])


def downgrade() -> None:
    op.drop_index("ix_scm_product_sales_volume", table_name="scm_product")
    op.drop_index("ix_scm_product_discount_rate", table_name="scm_product")
    op.drop_index("ix_scm_product_agreement_price", table_name="scm_product")
    op.drop_index("ix_scm_product_cost_price", table_name="scm_product")
    op.drop_constraint("ck_scm_product_positive_rating_range", "scm_product", type_="check")
    op.drop_constraint("ck_scm_product_sales_volume_nonnegative", "scm_product", type_="check")
    for column in (
        "after_sales_policy",
        "shipping_courier",
        "tax_category",
        "invoice_name",
        "tax_code",
        "positive_rating",
        "sales_volume",
        "warranty_period",
        "packaging_list",
        "certification_3c_code",
        "company_name",
    ):
        op.drop_column("scm_product", column)
