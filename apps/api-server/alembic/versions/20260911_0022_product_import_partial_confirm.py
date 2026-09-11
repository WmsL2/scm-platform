"""support partial confirmation for validated product import rows

Revision ID: 20260911_0022
Revises: 20260911_0021
"""

import sqlalchemy as sa

from alembic import op

revision = "20260911_0022"
down_revision = "20260911_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_product_import_task",
        sa.Column("imported_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "scm_product_import_row",
        sa.Column("is_imported", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("scm_product_import_row", sa.Column("imported_by", sa.CHAR(36), nullable=True))
    op.add_column("scm_product_import_row", sa.Column("imported_at", sa.DateTime(), nullable=True))

    # Existing confirmed batches were atomic in the prior workflow, so every row
    # in those batches is already represented by a formal Product record.
    op.execute(
        sa.text(
            "UPDATE scm_product_import_row AS r "
            "INNER JOIN scm_product_import_task AS t ON t.id = r.import_task_id "
            "SET r.is_imported = true, r.imported_by = t.confirmed_by, "
            "r.imported_at = t.confirmed_at "
            "WHERE t.status = 'CONFIRMED'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE scm_product_import_task SET imported_rows = total_rows "
            "WHERE status = 'CONFIRMED'"
        )
    )

    op.drop_constraint(
        "ck_scm_product_import_task_status", "scm_product_import_task", type_="check"
    )
    op.create_check_constraint(
        "ck_scm_product_import_task_status",
        "scm_product_import_task",
        "status IN ('VALIDATED', 'NEEDS_RESOLUTION', 'READY_TO_CONFIRM', "
        "'PARTIALLY_CONFIRMED', 'CONFIRMED')",
    )


def downgrade() -> None:
    # A pre-0022 application cannot safely resume a partly confirmed batch.
    # Returning it to validation prevents it from treating its already imported
    # rows as a fresh all-or-nothing batch after the row-level state is removed.
    op.execute(
        sa.text(
            "UPDATE scm_product_import_task SET status = 'VALIDATED' "
            "WHERE status = 'PARTIALLY_CONFIRMED'"
        )
    )
    op.drop_constraint(
        "ck_scm_product_import_task_status", "scm_product_import_task", type_="check"
    )
    op.create_check_constraint(
        "ck_scm_product_import_task_status",
        "scm_product_import_task",
        "status IN ('VALIDATED', 'NEEDS_RESOLUTION', 'READY_TO_CONFIRM', 'CONFIRMED')",
    )
    op.drop_column("scm_product_import_row", "imported_at")
    op.drop_column("scm_product_import_row", "imported_by")
    op.drop_column("scm_product_import_row", "is_imported")
    op.drop_column("scm_product_import_task", "imported_rows")
