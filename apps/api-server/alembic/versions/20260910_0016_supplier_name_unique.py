"""enforce globally unique supplier names

Revision ID: 20260910_0016
Revises: 20260910_0015
"""

from alembic import op

revision = "20260910_0016"
down_revision = "20260910_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_scm_supplier_supplier_name", "scm_supplier", ["supplier_name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_scm_supplier_supplier_name", "scm_supplier", type_="unique")
