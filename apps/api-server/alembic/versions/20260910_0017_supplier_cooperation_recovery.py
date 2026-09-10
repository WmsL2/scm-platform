"""allow supplier cooperation recovery history

Revision ID: 20260910_0017
Revises: 20260910_0016
"""

import sqlalchemy as sa

from alembic import op

revision = "20260910_0017"
down_revision = "20260910_0016"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_scm_supplier_cooperation_record_transition"
REVERSE_HISTORY_SQL = """
    SELECT 1 FROM scm_supplier_cooperation_record
    WHERE from_status IN ('STOPPED', 'BLACKLIST') AND to_status = 'NORMAL'
    LIMIT 1
"""


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "scm_supplier_cooperation_record", type_="check")
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "scm_supplier_cooperation_record",
        "(from_status = 'NORMAL' AND to_status IN ('STOPPED', 'BLACKLIST')) "
        "OR (from_status IN ('STOPPED', 'BLACKLIST') AND to_status = 'NORMAL')",
    )
    op.get_bind().execute(
        sa.text(
            "INSERT INTO sys_permission (id, permission_code, permission_name, permission_type) "
            "VALUES (:id, :code, :name, 'ACTION')"
        ),
        [
            {
                "id": "20000000-0000-0000-0000-000000000010",
                "code": "supplier:resume",
                "name": "恢复供应商合作",
            },
            {
                "id": "20000000-0000-0000-0000-000000000011",
                "code": "supplier:unblacklist",
                "name": "移出供应商黑名单",
            },
        ],
    )


def downgrade() -> None:
    if op.get_bind().execute(sa.text(REVERSE_HISTORY_SQL)).first() is not None:
        raise RuntimeError("Cannot downgrade: supplier cooperation recovery history exists")
    op.execute(
        sa.text(
            "DELETE rp FROM sys_role_permission AS rp "
            "JOIN sys_permission AS p ON p.id = rp.permission_id "
            "WHERE p.permission_code IN ('supplier:resume', 'supplier:unblacklist')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM sys_permission "
            "WHERE permission_code IN ('supplier:resume', 'supplier:unblacklist')"
        )
    )
    op.drop_constraint(CONSTRAINT_NAME, "scm_supplier_cooperation_record", type_="check")
    op.create_check_constraint(
        CONSTRAINT_NAME,
        "scm_supplier_cooperation_record",
        "from_status = 'NORMAL' AND to_status IN ('STOPPED', 'BLACKLIST')",
    )
