"""supplier logical deletion and Excel import staging

Revision ID: 20260908_0005
Revises: 20260907_0004
"""

import sqlalchemy as sa

from alembic import op

revision = "20260908_0005"
down_revision = "20260907_0004"
branch_labels = None
depends_on = None

uuid = sa.CHAR(36)


def upgrade() -> None:
    op.add_column("scm_supplier", sa.Column("deleted_by", uuid, nullable=True))
    op.add_column("scm_supplier", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_table(
        "scm_supplier_import_batch",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="VALIDATED"),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("valid_rows", sa.Integer(), nullable=False),
        sa.Column("invalid_rows", sa.Integer(), nullable=False),
        sa.Column("created_by", uuid, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("confirmed_by", uuid, nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('VALIDATED', 'CONFIRMED')", name="ck_scm_supplier_import_batch_status"
        ),
        sa.CheckConstraint("total_rows >= 0", name="ck_scm_supplier_import_batch_total_rows"),
        sa.CheckConstraint("valid_rows >= 0", name="ck_scm_supplier_import_batch_valid_rows"),
        sa.CheckConstraint("invalid_rows >= 0", name="ck_scm_supplier_import_batch_invalid_rows"),
    )
    op.create_table(
        "scm_supplier_import_row",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "batch_id",
            uuid,
            sa.ForeignKey("scm_supplier_import_batch.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=True),
        sa.Column("main_brands", sa.Text(), nullable=True),
        sa.Column("advantage", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(64), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "batch_id", "source_row_number", name="uq_scm_supplier_import_row_batch_source_row"
        ),
    )
    op.create_index("ix_scm_supplier_import_row_batch_id", "scm_supplier_import_row", ["batch_id"])
    op.execute(
        sa.text(
            "INSERT INTO sys_permission (id, permission_code, permission_name, permission_type) "
            "VALUES ('20000000-0000-0000-0000-000000000009', 'supplier:delete', "
            "'删除供应商', 'ACTION')"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM sys_permission WHERE permission_code = 'supplier:delete'")
    )
    op.drop_index("ix_scm_supplier_import_row_batch_id", table_name="scm_supplier_import_row")
    op.drop_table("scm_supplier_import_row")
    op.drop_table("scm_supplier_import_batch")
    op.drop_column("scm_supplier", "deleted_at")
    op.drop_column("scm_supplier", "deleted_by")
