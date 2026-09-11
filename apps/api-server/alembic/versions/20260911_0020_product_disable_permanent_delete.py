"""replace product logical delete with disable and permanent delete lifecycle

Revision ID: 20260911_0020
Revises: 20260911_0019
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_0020"
down_revision = "20260911_0019"
branch_labels = None
depends_on = None

PRODUCT_DELETE_PERMISSION_ID = "40000000-0000-0000-0000-000000000007"
PRODUCT_DISABLE_PERMISSION_ID = "40000000-0000-0000-0000-000000000008"
PRODUCT_PURGE_PERMISSION_ID = "40000000-0000-0000-0000-000000000009"


def _grant_system_administrator(permission_id: str) -> None:
    op.execute(
        sa.text(
            "INSERT INTO sys_role_permission (role_id, permission_id) "
            "SELECT r.id, :permission_id FROM sys_role AS r "
            "WHERE r.role_code = 'system_administrator' AND r.is_deleted = false "
            "AND NOT EXISTS (SELECT 1 FROM sys_role_permission AS rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = :permission_id)"
        ).bindparams(permission_id=permission_id)
    )


def upgrade() -> None:
    op.add_column(
        "scm_product",
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
    )
    op.add_column("scm_product", sa.Column("disabled_by", sa.String(36), nullable=True))
    op.add_column("scm_product", sa.Column("disabled_at", sa.DateTime(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE scm_product SET status = 'DISABLED', disabled_by = deleted_by, "
            "disabled_at = deleted_at WHERE is_deleted = true"
        )
    )
    op.create_check_constraint(
        "ck_scm_product_status", "scm_product", "status IN ('ACTIVE', 'DISABLED')"
    )
    op.create_index("ix_scm_product_status", "scm_product", ["status"])
    op.create_table(
        "scm_product_purge_audit",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("product_id", sa.CHAR(36), nullable=False),
        sa.Column("source_supplier_id", sa.CHAR(36), nullable=False),
        sa.Column("sku", sa.String(255), nullable=True),
        sa.Column("product_name", sa.String(512), nullable=True),
        sa.Column("purged_by", sa.CHAR(36), nullable=False),
        sa.Column(
            "purged_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scm_product_purge_audit_product_id", "scm_product_purge_audit", ["product_id"]
    )

    for permission_id, code, name in (
        (PRODUCT_DISABLE_PERMISSION_ID, "product:disable", "停用或启用商品"),
        (PRODUCT_PURGE_PERMISSION_ID, "product:purge", "永久删除商品"),
    ):
        op.execute(
            sa.text(
                "INSERT INTO sys_permission "
                "(id, permission_code, permission_name, permission_type) "
                "VALUES (:id, :code, :name, 'ACTION')"
            ).bindparams(id=permission_id, code=code, name=name)
        )
        _grant_system_administrator(permission_id)

    op.execute(
        sa.text(
            "INSERT INTO sys_role_permission (role_id, permission_id) "
            "SELECT rp.role_id, :disable_permission_id "
            "FROM sys_role_permission AS rp "
            "INNER JOIN sys_permission AS p ON p.id = rp.permission_id "
            "WHERE p.permission_code = 'product:delete' "
            "AND NOT EXISTS (SELECT 1 FROM sys_role_permission AS existing "
            "WHERE existing.role_id = rp.role_id "
            "AND existing.permission_id = :disable_permission_id)"
        ).bindparams(disable_permission_id=PRODUCT_DISABLE_PERMISSION_ID)
    )
    op.execute(
        sa.text(
            "DELETE rp FROM sys_role_permission AS rp "
            "INNER JOIN sys_permission AS p ON p.id = rp.permission_id "
            "WHERE p.permission_code = 'product:delete'"
        )
    )
    op.execute(sa.text("DELETE FROM sys_permission WHERE permission_code = 'product:delete'"))

    op.drop_index("ix_scm_product_is_deleted", table_name="scm_product")
    op.drop_column("scm_product", "deleted_at")
    op.drop_column("scm_product", "deleted_by")
    op.drop_column("scm_product", "is_deleted")


def downgrade() -> None:
    op.add_column(
        "scm_product",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("scm_product", sa.Column("deleted_by", sa.String(36), nullable=True))
    op.add_column("scm_product", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.execute(
        sa.text(
            "UPDATE scm_product SET is_deleted = true, deleted_by = disabled_by, "
            "deleted_at = disabled_at WHERE status = 'DISABLED'"
        )
    )
    op.create_index("ix_scm_product_is_deleted", "scm_product", ["is_deleted"])

    permission_ids = [PRODUCT_DISABLE_PERMISSION_ID, PRODUCT_PURGE_PERMISSION_ID]
    op.execute(
        sa.text(
            "DELETE FROM sys_role_permission WHERE permission_id IN :permission_ids"
        ).bindparams(
            sa.bindparam("permission_ids", expanding=True, value=permission_ids)
        )
    )
    op.execute(
        sa.text("DELETE FROM sys_permission WHERE id IN :permission_ids").bindparams(
            sa.bindparam("permission_ids", expanding=True, value=permission_ids)
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO sys_permission "
            "(id, permission_code, permission_name, permission_type) "
            "VALUES (:id, 'product:delete', '删除商品', 'ACTION')"
        ).bindparams(id=PRODUCT_DELETE_PERMISSION_ID)
    )
    _grant_system_administrator(PRODUCT_DELETE_PERMISSION_ID)

    op.drop_index("ix_scm_product_purge_audit_product_id", table_name="scm_product_purge_audit")
    op.drop_table("scm_product_purge_audit")
    op.drop_index("ix_scm_product_status", table_name="scm_product")
    op.drop_constraint("ck_scm_product_status", "scm_product", type_="check")
    op.drop_column("scm_product", "disabled_at")
    op.drop_column("scm_product", "disabled_by")
    op.drop_column("scm_product", "status")
