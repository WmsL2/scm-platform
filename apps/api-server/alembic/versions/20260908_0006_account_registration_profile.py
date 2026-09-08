"""account registration and profile administration

Revision ID: 20260908_0006
Revises: 20260908_0005
"""

import sqlalchemy as sa

from alembic import op

revision = "20260908_0006"
down_revision = "20260908_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_sys_user_status", "sys_user", type_="check")
    op.create_check_constraint(
        "ck_sys_user_status",
        "sys_user",
        "user_status IN ('PENDING', 'ENABLED', 'DISABLED', 'REJECTED')",
    )
    op.add_column("sys_user", sa.Column("reviewed_by", sa.CHAR(36), nullable=True))
    op.add_column("sys_user", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("sys_user", sa.Column("review_note", sa.Text(), nullable=True))
    permissions = (
        (
            "30000000-0000-0000-0000-000000000001",
            "system:user:list",
            "用户列表",
            "API",
        ),
        (
            "30000000-0000-0000-0000-000000000002",
            "system:user:role:update",
            "更新用户角色",
            "ACTION",
        ),
        (
            "30000000-0000-0000-0000-000000000003",
            "system:role:list",
            "角色列表",
            "API",
        ),
        (
            "30000000-0000-0000-0000-000000000004",
            "system:role:permission:update",
            "更新角色权限",
            "ACTION",
        ),
        (
            "30000000-0000-0000-0000-000000000005",
            "system:permission:list",
            "权限列表",
            "API",
        ),
        (
            "30000000-0000-0000-0000-000000000006",
            "system:registration:list",
            "注册申请列表",
            "API",
        ),
        (
            "30000000-0000-0000-0000-000000000007",
            "system:registration:review",
            "注册申请审批",
            "ACTION",
        ),
    )
    for permission_id, code, name, permission_type in permissions:
        op.execute(sa.text(
            "INSERT INTO sys_permission (id, permission_code, permission_name, permission_type) "
            "VALUES (:id, :code, :name, :permission_type)"
        ).bindparams(id=permission_id, code=code, name=name, permission_type=permission_type))


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM sys_permission WHERE permission_code IN "
        "('system:user:list', 'system:user:role:update', 'system:role:list', "
        "'system:role:permission:update', 'system:permission:list', "
        "'system:registration:list', 'system:registration:review')"))
    op.drop_column("sys_user", "review_note")
    op.drop_column("sys_user", "reviewed_at")
    op.drop_column("sys_user", "reviewed_by")
    op.drop_constraint("ck_sys_user_status", "sys_user", type_="check")
    op.create_check_constraint(
        "ck_sys_user_status", "sys_user", "user_status IN ('ENABLED', 'DISABLED')"
    )
