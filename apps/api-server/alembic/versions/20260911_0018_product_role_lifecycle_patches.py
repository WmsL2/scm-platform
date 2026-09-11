"""protect product business keys and add product-edit / role-delete permissions

Revision ID: 20260911_0018
Revises: 20260910_0017
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_0018"
down_revision = "20260910_0017"
branch_labels = None
depends_on = None

PRODUCT_UPDATE_PERMISSION_ID = "40000000-0000-0000-0000-000000000006"
ROLE_DELETE_PERMISSION_ID = "30000000-0000-0000-0000-000000000010"


def upgrade() -> None:
    duplicate = op.get_bind().execute(
        sa.text(
            "SELECT source_supplier_id, sku, COUNT(*) AS duplicate_count "
            "FROM scm_product WHERE sku IS NOT NULL "
            "GROUP BY source_supplier_id, sku HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicate is not None:
        raise RuntimeError(
            "Cannot add uq_scm_product_source_supplier_sku because existing duplicate "
            "products were found. Reconcile the duplicate source supplier + SKU records first."
        )
    op.create_unique_constraint(
        "uq_scm_product_source_supplier_sku",
        "scm_product",
        ["source_supplier_id", "sku"],
    )

    permissions = (
        (PRODUCT_UPDATE_PERMISSION_ID, "product:update", "编辑商品基础资料", "ACTION"),
        (ROLE_DELETE_PERMISSION_ID, "system:role:delete", "删除自定义角色", "ACTION"),
    )
    for permission_id, code, name, permission_type in permissions:
        op.execute(
            sa.text(
                "INSERT INTO sys_permission (id, permission_code, permission_name, permission_type) "
                "VALUES (:id, :code, :name, :permission_type)"
            ).bindparams(
                id=permission_id, code=code, name=name, permission_type=permission_type
            )
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
    permission_ids = [PRODUCT_UPDATE_PERMISSION_ID, ROLE_DELETE_PERMISSION_ID]
    op.execute(
        sa.text("DELETE FROM sys_role_permission WHERE permission_id IN :permission_ids").bindparams(
            sa.bindparam("permission_ids", expanding=True, value=permission_ids)
        )
    )
    op.execute(
        sa.text("DELETE FROM sys_permission WHERE id IN :permission_ids").bindparams(
            sa.bindparam("permission_ids", expanding=True, value=permission_ids)
        )
    )
    op.drop_constraint("uq_scm_product_source_supplier_sku", "scm_product", type_="unique")
