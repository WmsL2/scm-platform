"""allow product import rows to update normal duplicate products

Revision ID: 20260917_0028
Revises: 20260916_0027
"""

import sqlalchemy as sa

from alembic import op

revision = "20260917_0028"
down_revision = "20260916_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_product_import_task",
        sa.Column("update_rows", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "scm_product_import_row",
        sa.Column("write_action", sa.String(length=16), nullable=False, server_default="CREATE"),
    )
    op.add_column(
        "scm_product_import_row",
        sa.Column("changed_fields", sa.JSON(), nullable=True),
    )
    op.create_check_constraint(
        "ck_scm_product_import_row_write_action",
        "scm_product_import_row",
        "write_action IN ('CREATE', 'UPDATE')",
    )
    op.alter_column("scm_product_import_task", "update_rows", server_default=None)
    op.alter_column("scm_product_import_row", "write_action", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "ck_scm_product_import_row_write_action", "scm_product_import_row", type_="check"
    )
    op.drop_column("scm_product_import_row", "changed_fields")
    op.drop_column("scm_product_import_row", "write_action")
    op.drop_column("scm_product_import_task", "update_rows")
