"""新增投标项目编辑与作废权限

Revision ID: 20260916_0026
Revises: 20260916_0025
"""

import sqlalchemy as sa

from alembic import op

revision = "20260916_0026"
down_revision = "20260916_0025"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("50000000-0000-0000-0000-000000000010", "bid:update", "编辑投标项目", "ACTION"),
    ("50000000-0000-0000-0000-000000000011", "bid:void", "作废投标项目", "ACTION"),
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
        sa.text(
            "DELETE FROM sys_role_permission "
            "WHERE permission_id IN :ids"
        ).bindparams(bind_ids)
    )
    op.execute(sa.text("DELETE FROM sys_permission WHERE id IN :ids").bindparams(bind_ids))
