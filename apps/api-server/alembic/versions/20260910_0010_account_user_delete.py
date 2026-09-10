"""add account user logical delete audit and permission

Revision ID: 20260910_0010
Revises: 20260909_0009
"""

import sqlalchemy as sa

from alembic import op

revision = "20260910_0010"
down_revision = "20260909_0009"
branch_labels = None
depends_on = None

PERMISSION_ID = "30000000-0000-0000-0000-000000000009"


def upgrade() -> None:
    op.add_column("sys_user", sa.Column("deleted_by", sa.CHAR(36), nullable=True))
    op.add_column("sys_user", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.execute(
        sa.text(
            "INSERT INTO sys_permission (id, permission_code, permission_name, permission_type) "
            "VALUES (:id, 'system:user:delete', '删除用户', 'ACTION')"
        ).bindparams(id=PERMISSION_ID)
    )
    op.execute(
        sa.text(
            "INSERT INTO sys_role_permission (role_id, permission_id) "
            "SELECT r.id, :permission_id FROM sys_role AS r "
            "WHERE r.role_code = 'system_administrator' AND r.is_deleted = false "
            "AND NOT EXISTS (SELECT 1 FROM sys_role_permission AS rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = :permission_id)"
        ).bindparams(permission_id=PERMISSION_ID)
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM sys_role_permission WHERE permission_id = :permission_id").bindparams(
            permission_id=PERMISSION_ID
        )
    )
    op.execute(sa.text("DELETE FROM sys_permission WHERE permission_code = 'system:user:delete'"))
    op.drop_column("sys_user", "deleted_at")
    op.drop_column("sys_user", "deleted_by")
