"""supplier master backend

Revision ID: 20260907_0004
Revises: 20260907_0003
"""

import sqlalchemy as sa

from alembic import op

revision = "20260907_0004"
down_revision = "20260907_0003"
branch_labels = None
depends_on = None

uuid = sa.CHAR(36)
audit = [
    sa.Column("created_by", uuid, nullable=True),
    sa.Column("updated_by", uuid, nullable=True),
    sa.Column(
        "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    ),
]


def upgrade() -> None:
    op.create_table(
        "scm_supplier",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("supplier_code", sa.String(16), nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("main_brands", sa.Text(), nullable=False),
        sa.Column("advantage", sa.Text(), nullable=False),
        sa.Column("archive_status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("cooperation_status", sa.String(16), nullable=False, server_default="NORMAL"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("archived_by", uuid, nullable=True),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        *audit,
        sa.CheckConstraint(
            "archive_status IN ('DRAFT', 'PENDING', 'ARCHIVED')",
            name="ck_scm_supplier_archive_status",
        ),
        sa.CheckConstraint(
            "cooperation_status IN ('NORMAL', 'STOPPED', 'BLACKLIST')",
            name="ck_scm_supplier_cooperation_status",
        ),
        sa.UniqueConstraint("supplier_code", name="uq_scm_supplier_supplier_code"),
    )
    op.create_index(
        "ix_scm_supplier_archive_cooperation",
        "scm_supplier",
        ["archive_status", "cooperation_status"],
    )
    op.create_table(
        "scm_supplier_contact",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "supplier_id",
            uuid,
            sa.ForeignKey("scm_supplier.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(64), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *audit,
        sa.CheckConstraint(
            "contact_name IS NOT NULL OR contact_phone IS NOT NULL",
            name="ck_scm_supplier_contact_has_value",
        ),
    )
    op.create_index("ix_scm_supplier_contact_supplier_id", "scm_supplier_contact", ["supplier_id"])
    op.create_table(
        "scm_supplier_qualification",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "supplier_id",
            uuid,
            sa.ForeignKey("scm_supplier.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *audit,
    )
    op.create_index(
        "ix_scm_supplier_qualification_supplier_id", "scm_supplier_qualification", ["supplier_id"]
    )
    op.create_table(
        "scm_supplier_cooperation_record",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "supplier_id",
            uuid,
            sa.ForeignKey("scm_supplier.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(16), nullable=False),
        sa.Column("to_status", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_id", uuid, nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "from_status = 'NORMAL' AND to_status IN ('STOPPED', 'BLACKLIST')",
            name="ck_scm_supplier_cooperation_record_transition",
        ),
        sa.CheckConstraint(
            "CHAR_LENGTH(TRIM(reason)) > 0", name="ck_scm_supplier_cooperation_record_reason"
        ),
    )
    op.create_index(
        "ix_scm_supplier_cooperation_record_supplier_occurred",
        "scm_supplier_cooperation_record",
        ["supplier_id", "occurred_at"],
    )

    permissions = (
        ("20000000-0000-0000-0000-000000000001", "supplier:list", "供应商列表", "API"),
        ("20000000-0000-0000-0000-000000000002", "supplier:detail", "供应商详情", "API"),
        ("20000000-0000-0000-0000-000000000003", "supplier:create", "创建供应商", "ACTION"),
        ("20000000-0000-0000-0000-000000000004", "supplier:update", "编辑供应商", "ACTION"),
        ("20000000-0000-0000-0000-000000000005", "supplier:submit", "提交供应商", "ACTION"),
        ("20000000-0000-0000-0000-000000000006", "supplier:archive", "归档供应商", "ACTION"),
        ("20000000-0000-0000-0000-000000000007", "supplier:stop", "停用供应商", "ACTION"),
        ("20000000-0000-0000-0000-000000000008", "supplier:blacklist", "拉黑供应商", "ACTION"),
    )
    for permission_id, code, name, permission_type in permissions:
        op.execute(
            sa.text(
                "INSERT INTO sys_permission "
                "(id, permission_code, permission_name, permission_type) "
                "VALUES (:id, :code, :name, :permission_type)"
            ).bindparams(
                id=permission_id, code=code, name=name, permission_type=permission_type
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM sys_permission WHERE permission_code IN "
            "('supplier:list', 'supplier:detail', 'supplier:create', 'supplier:update', "
            "'supplier:submit', 'supplier:archive', 'supplier:stop', 'supplier:blacklist')"
        )
    )
    op.drop_index(
        "ix_scm_supplier_cooperation_record_supplier_occurred",
        table_name="scm_supplier_cooperation_record",
    )
    op.drop_table("scm_supplier_cooperation_record")
    op.drop_index(
        "ix_scm_supplier_qualification_supplier_id", table_name="scm_supplier_qualification"
    )
    op.drop_table("scm_supplier_qualification")
    op.drop_index("ix_scm_supplier_contact_supplier_id", table_name="scm_supplier_contact")
    op.drop_table("scm_supplier_contact")
    op.drop_index("ix_scm_supplier_archive_cooperation", table_name="scm_supplier")
    op.drop_table("scm_supplier")
