"""新增类目管理增删改查权限。

Revision ID: 20260916_0028
Revises: 20260916_0027
"""

import sqlalchemy as sa

from alembic import op

revision = "20260916_0028"
down_revision = "20260916_0027"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("60000000-0000-0000-0000-000000000001", "category:list", "查看类目列表", "MENU"),
    ("60000000-0000-0000-0000-000000000002", "category:detail", "查看类目详情", "API"),
    ("60000000-0000-0000-0000-000000000003", "category:create", "新增类目", "ACTION"),
    ("60000000-0000-0000-0000-000000000004", "category:update", "编辑类目", "ACTION"),
    ("60000000-0000-0000-0000-000000000005", "category:delete", "删除类目", "ACTION"),
)


def upgrade() -> None:
    for permission_id, code, name, permission_type in PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO sys_permission "
                "(id, permission_code, permission_name, permission_type) "
                "VALUES (:id, :code, :name, :permission_type)"
            ).bindparams(
                id=permission_id,
                code=code,
                name=name,
                permission_type=permission_type,
            )
        )
        op.execute(
            sa.text(
                "INSERT INTO sys_role_permission (role_id, permission_id) "
                "SELECT r.id, :permission_id FROM sys_role r "
                "WHERE r.role_code = 'boss' AND r.is_deleted = false"
            ).bindparams(permission_id=permission_id)
        )


def downgrade() -> None:
    ids = [item[0] for item in PERMISSIONS]
    bind_ids = sa.bindparam("ids", expanding=True, value=ids)
    op.execute(
        sa.text("DELETE FROM sys_role_permission WHERE permission_id IN :ids").bindparams(bind_ids)
    )
    op.execute(sa.text("DELETE FROM sys_permission WHERE id IN :ids").bindparams(bind_ids))
