"""seed custom role creation permission

Revision ID: 20260908_0007
Revises: 20260908_0006
"""

import sqlalchemy as sa

from alembic import op

revision = "20260908_0007"
down_revision = "20260908_0006"
branch_labels = None
depends_on = None

ROLE_CREATE_PERMISSION_ID = "30000000-0000-0000-0000-000000000008"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO sys_permission (id, permission_code, permission_name, permission_type) "
            "VALUES (:id, 'system:role:create', '新增角色', 'ACTION')"
        ).bindparams(id=ROLE_CREATE_PERMISSION_ID)
    )
    op.execute(
        sa.text(
            "INSERT INTO sys_role_permission (role_id, permission_id) "
            "SELECT r.id, :permission_id FROM sys_role AS r "
            "WHERE r.role_code = 'system_administrator' AND r.is_deleted = false "
            "AND NOT EXISTS (SELECT 1 FROM sys_role_permission AS rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = :permission_id)"
        ).bindparams(permission_id=ROLE_CREATE_PERMISSION_ID)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM sys_role_permission WHERE permission_id = :permission_id").bindparams(
            permission_id=ROLE_CREATE_PERMISSION_ID
        )
    )
    op.execute(
        sa.text("DELETE FROM sys_permission WHERE permission_code = 'system:role:create'")
    )
