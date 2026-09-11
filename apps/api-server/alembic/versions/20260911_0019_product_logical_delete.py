"""add product logical delete

Revision ID: 20260911_0019
Revises: 20260911_0018
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_0019"
down_revision = "20260911_0018"
branch_labels = None
depends_on = None

PRODUCT_DELETE_PERMISSION_ID = "40000000-0000-0000-0000-000000000007"


def upgrade() -> None:
    op.add_column(
        "scm_product",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("scm_product", sa.Column("deleted_by", sa.String(36), nullable=True))
    op.add_column("scm_product", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_scm_product_is_deleted", "scm_product", ["is_deleted"])
    op.execute(
        sa.text(
            "INSERT INTO sys_permission "
            "(id, permission_code, permission_name, permission_type) "
            "VALUES (:id, 'product:delete', '删除商品', 'ACTION')"
        ).bindparams(id=PRODUCT_DELETE_PERMISSION_ID)
    )
    op.execute(
        sa.text(
            "INSERT INTO sys_role_permission (role_id, permission_id) "
            "SELECT r.id, :permission_id FROM sys_role AS r "
            "WHERE r.role_code = 'system_administrator' AND r.is_deleted = false "
            "AND NOT EXISTS (SELECT 1 FROM sys_role_permission AS rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = :permission_id)"
        ).bindparams(permission_id=PRODUCT_DELETE_PERMISSION_ID)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM sys_role_permission WHERE permission_id = :permission_id").bindparams(
            permission_id=PRODUCT_DELETE_PERMISSION_ID
        )
    )
    op.execute(
        sa.text("DELETE FROM sys_permission WHERE id = :permission_id").bindparams(
            permission_id=PRODUCT_DELETE_PERMISSION_ID
        )
    )
    op.drop_index("ix_scm_product_is_deleted", table_name="scm_product")
    op.drop_column("scm_product", "deleted_at")
    op.drop_column("scm_product", "deleted_by")
    op.drop_column("scm_product", "is_deleted")
