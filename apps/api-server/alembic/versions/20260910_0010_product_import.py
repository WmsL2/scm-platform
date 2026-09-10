"""add product import staging and source supplier matching

Revision ID: 20260910_0010
Revises: 20260909_0009
"""

import sqlalchemy as sa

from alembic import op

revision = "20260910_0010"
down_revision = "20260909_0009"
branch_labels = None
depends_on = None

PRODUCT_IMPORT_PERMISSIONS = (
    ("40000000-0000-0000-0000-000000000004", "product:import", "导入商品", "ACTION"),
    (
        "40000000-0000-0000-0000-000000000005",
        "product:import:resolve",
        "解析商品来源供应商",
        "ACTION",
    ),
)


def upgrade() -> None:
    op.create_table(
        "scm_product_import_task",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("invalid_rows", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.CHAR(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("confirmed_by", sa.CHAR(36), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('VALIDATED', 'NEEDS_RESOLUTION', 'READY_TO_CONFIRM', 'CONFIRMED')",
            name="ck_scm_product_import_task_status",
        ),
        sa.CheckConstraint("total_rows >= 0", name="ck_scm_product_import_task_total_rows"),
        sa.CheckConstraint("valid_rows >= 0", name="ck_scm_product_import_task_valid_rows"),
        sa.CheckConstraint("invalid_rows >= 0", name="ck_scm_product_import_task_invalid_rows"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scm_product_import_supplier_match",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("import_task_id", sa.CHAR(36), nullable=False),
        sa.Column("supplier_name_normalized", sa.String(255), nullable=False),
        sa.Column("match_status", sa.String(16), nullable=False),
        sa.Column("match_method", sa.String(16), nullable=True),
        sa.Column("matched_supplier_id", sa.CHAR(36), nullable=True),
        sa.Column("resolved_by", sa.CHAR(36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "match_status IN ('MATCHED', 'AMBIGUOUS', 'UNMATCHED', 'INELIGIBLE')",
            name="ck_scm_product_import_supplier_match_status",
        ),
        sa.CheckConstraint(
            "match_method IS NULL OR match_method IN ('NAME_EXACT', 'MANUAL')",
            name="ck_scm_product_import_supplier_match_method",
        ),
        sa.ForeignKeyConstraint(
            ["import_task_id"], ["scm_product_import_task.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["matched_supplier_id"], ["scm_supplier.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_task_id",
            "supplier_name_normalized",
            name="uq_scm_product_import_supplier_match_task_name",
        ),
    )
    op.create_index(
        "ix_scm_product_import_supplier_match_task_id",
        "scm_product_import_supplier_match",
        ["import_task_id"],
    )
    op.create_table(
        "scm_product_import_row",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("import_task_id", sa.CHAR(36), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("source_data", sa.JSON(), nullable=False),
        sa.Column("calculated_data", sa.JSON(), nullable=False),
        sa.Column("supplier_name_raw", sa.String(255), nullable=True),
        sa.Column("category_id", sa.CHAR(36), nullable=True),
        sa.Column("supplier_match_id", sa.CHAR(36), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("warning_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["import_task_id"], ["scm_product_import_task.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["category_id"], ["scm_category.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supplier_match_id"], ["scm_product_import_supplier_match.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "import_task_id", "source_row_number", name="uq_scm_product_import_row_task_source_row"
        ),
    )
    op.create_index(
        "ix_scm_product_import_row_task_id", "scm_product_import_row", ["import_task_id"]
    )
    op.create_index(
        "ix_scm_product_import_row_category_id", "scm_product_import_row", ["category_id"]
    )
    op.create_index(
        "ix_scm_product_import_row_supplier_match_id",
        "scm_product_import_row",
        ["supplier_match_id"],
    )
    for permission_id, code, name, permission_type in PRODUCT_IMPORT_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO sys_permission "
                "(id, permission_code, permission_name, permission_type) "
                "VALUES (:id, :code, :name, :permission_type)"
            ).bindparams(id=permission_id, code=code, name=name, permission_type=permission_type)
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
    permission_ids = [row[0] for row in PRODUCT_IMPORT_PERMISSIONS]
    op.execute(
        sa.text(
            "DELETE FROM sys_role_permission WHERE permission_id IN :permission_ids"
        ).bindparams(sa.bindparam("permission_ids", expanding=True, value=permission_ids))
    )
    op.execute(
        sa.text("DELETE FROM sys_permission WHERE id IN :permission_ids").bindparams(
            sa.bindparam("permission_ids", expanding=True, value=permission_ids)
        )
    )
    op.drop_table("scm_product_import_row")
    op.drop_table("scm_product_import_supplier_match")
    op.drop_table("scm_product_import_task")
