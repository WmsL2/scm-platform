"""defer product-import image storage until confirmation

Revision ID: 20260914_0023
Revises: 20260911_0022
"""

import sqlalchemy as sa

from alembic import op

revision = "20260914_0023"
down_revision = "20260911_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_product_import_task",
        sa.Column("source_file_storage_key", sa.String(1024), nullable=True),
    )
    op.drop_constraint(
        "ck_scm_product_import_task_status", "scm_product_import_task", type_="check"
    )
    op.create_check_constraint(
        "ck_scm_product_import_task_status",
        "scm_product_import_task",
        "status IN ('VALIDATED', 'NEEDS_RESOLUTION', 'READY_TO_CONFIRM', "
        "'PARTIALLY_CONFIRMED', 'CONFIRMED', 'EXPIRED')",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE scm_product_import_task SET status = 'VALIDATED' "
            "WHERE status = 'EXPIRED'"
        )
    )
    op.drop_constraint(
        "ck_scm_product_import_task_status", "scm_product_import_task", type_="check"
    )
    op.create_check_constraint(
        "ck_scm_product_import_task_status",
        "status IN ('VALIDATED', 'NEEDS_RESOLUTION', 'READY_TO_CONFIRM', "
        "'PARTIALLY_CONFIRMED', 'CONFIRMED')",
    )
    op.drop_column("scm_product_import_task", "source_file_storage_key")
