"""create category and product master

Revision ID: 20260909_0008
Revises: 20260908_0007
"""

import sqlalchemy as sa

from alembic import op

revision = "20260909_0008"
down_revision = "20260908_0007"
branch_labels = None
depends_on = None

PRODUCT_PERMISSIONS = (
    ("40000000-0000-0000-0000-000000000001", "product:list", "商品列表", "MENU"),
    ("40000000-0000-0000-0000-000000000002", "product:detail", "商品详情", "API"),
    ("40000000-0000-0000-0000-000000000003", "product:cost:update", "更新商品成本价", "ACTION"),
)


def upgrade() -> None:
    op.create_table(
        "scm_category",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("level1_external_id", sa.String(128), nullable=True),
        sa.Column("level1_name", sa.String(255), nullable=False),
        sa.Column("level2_external_id", sa.String(128), nullable=True),
        sa.Column("level2_name", sa.String(255), nullable=False),
        sa.Column("level3_external_id", sa.String(128), nullable=True),
        sa.Column("level3_name", sa.String(255), nullable=False),
        sa.Column("deduction_rate", sa.Numeric(9, 4), nullable=False, server_default="0.0800"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("shelf_flag", sa.String(32), nullable=True),
        sa.Column("business_unit", sa.String(128), nullable=True),
        sa.Column("created_by", sa.CHAR(36), nullable=True),
        sa.Column("updated_by", sa.CHAR(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "source_type IN ('MALL_LEVEL3', 'INDUSTRIAL_LINE')",
            name="ck_scm_category_source_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type",
            "level3_external_id",
            name="uq_scm_category_source_level3_external",
        ),
    )
    op.create_index("ix_scm_category_source_type", "scm_category", ["source_type"])
    op.create_index("ix_scm_category_level3_name", "scm_category", ["level3_name"])
    op.create_index("ix_scm_category_is_active", "scm_category", ["is_active"])
    op.create_index("ix_scm_category_business_unit", "scm_category", ["business_unit"])

    op.create_table(
        "scm_product",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("listed_at", sa.Date(), nullable=True),
        sa.Column("brand", sa.String(128), nullable=True),
        sa.Column("image_reference", sa.String(2048), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("sku", sa.String(255), nullable=True),
        sa.Column("product_name", sa.String(512), nullable=True),
        sa.Column("category_id", sa.CHAR(36), nullable=False),
        sa.Column("item_number", sa.String(255), nullable=True),
        sa.Column("jd_same_product_url", sa.String(2048), nullable=True),
        sa.Column("cost_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("market_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("jd_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("agreement_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("agreement_purchase_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("profit", sa.Numeric(18, 4), nullable=True),
        sa.Column("jd_margin", sa.Numeric(9, 4), nullable=True),
        sa.Column("purchasing_agent", sa.String(128), nullable=True),
        sa.Column("source_supplier_id", sa.CHAR(36), nullable=False),
        sa.Column("barcode_text", sa.String(255), nullable=True),
        sa.Column("deduction_review", sa.Numeric(9, 4), nullable=True),
        sa.Column("product_specification", sa.Text(), nullable=True),
        sa.Column("gross_margin", sa.Numeric(9, 4), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("discount_rate", sa.Numeric(9, 4), nullable=True),
        sa.Column("restricted_regions", sa.Text(), nullable=True),
        sa.Column("jd_self_operated_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("reference_url", sa.String(2048), nullable=True),
        sa.Column("remote_area_freight_note", sa.Text(), nullable=True),
        sa.Column("price_inflation_rate", sa.Numeric(9, 4), nullable=True),
        sa.Column("deduction_rate", sa.Numeric(9, 4), nullable=True),
        sa.Column("created_by", sa.CHAR(36), nullable=True),
        sa.Column("updated_by", sa.CHAR(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["category_id"], ["scm_category.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_supplier_id"], ["scm_supplier.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, column in (
        ("ix_scm_product_category_id", "category_id"),
        ("ix_scm_product_source_supplier_id", "source_supplier_id"),
        ("ix_scm_product_listed_at", "listed_at"),
        ("ix_scm_product_brand", "brand"),
        ("ix_scm_product_model", "model"),
        ("ix_scm_product_sku", "sku"),
        ("ix_scm_product_product_name", "product_name"),
        ("ix_scm_product_item_number", "item_number"),
        ("ix_scm_product_barcode_text", "barcode_text"),
        ("ix_scm_product_updated_at", "updated_at"),
    ):
        op.create_index(index_name, "scm_product", [column])

    for permission_id, code, name, permission_type in PRODUCT_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO sys_permission "
                "(id, permission_code, permission_name, permission_type) "
                "VALUES (:id, :code, :name, :permission_type)"
            ).bindparams(id=permission_id, code=code, name=name, permission_type=permission_type)
        )
        op.execute(
            sa.text(
                "INSERT INTO sys_role_permission (role_id, permission_id) "
                "SELECT r.id, :permission_id FROM sys_role AS r "
                "WHERE r.role_code = 'system_administrator' AND r.is_deleted = false "
                "AND NOT EXISTS (SELECT 1 FROM sys_role_permission AS rp "
                "WHERE rp.role_id = r.id AND rp.permission_id = :permission_id)"
            ).bindparams(permission_id=permission_id)
        )


def downgrade() -> None:
    permission_ids = [row[0] for row in PRODUCT_PERMISSIONS]
    statement = sa.text(
        "DELETE FROM sys_role_permission WHERE permission_id IN :permission_ids"
    ).bindparams(sa.bindparam("permission_ids", expanding=True, value=permission_ids))
    op.execute(statement)
    statement = sa.text("DELETE FROM sys_permission WHERE id IN :permission_ids").bindparams(
        sa.bindparam("permission_ids", expanding=True, value=permission_ids)
    )
    op.execute(statement)
    # MySQL uses the FK-supporting indexes while the table exists; dropping the
    # table removes every product index safely after the constraints are gone.
    op.drop_table("scm_product")
    op.drop_table("scm_category")
