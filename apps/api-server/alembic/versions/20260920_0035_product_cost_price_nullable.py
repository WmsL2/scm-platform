"""allow Product cost price to be null

Revision ID: 20260920_0035
Revises: 20260918_0034
"""

import sqlalchemy as sa

from alembic import op

revision = "20260920_0035"
down_revision = "20260918_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "scm_product",
        "cost_price",
        existing_type=sa.Numeric(65, 30),
        existing_nullable=False,
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM scm_product WHERE cost_price IS NULL")
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "Cannot downgrade scm_product.cost_price to NOT NULL: "
            "existing Products have a NULL cost_price"
        )
    op.alter_column(
        "scm_product",
        "cost_price",
        existing_type=sa.Numeric(65, 30),
        existing_nullable=True,
        nullable=False,
    )
