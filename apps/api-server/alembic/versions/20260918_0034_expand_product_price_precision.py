"""expand Product price precision without rounding source values

Revision ID: 20260918_0034
Revises: 20260918_0033
"""

import sqlalchemy as sa

from alembic import op

revision = "20260918_0034"
down_revision = "20260918_0033"
branch_labels = None
depends_on = None

_PRICE_COLUMNS = (
    ("cost_price", False),
    ("market_price", True),
    ("jd_price", True),
    ("agreement_price", True),
    ("agreement_purchase_price", True),
    ("jd_self_operated_price", True),
)


def upgrade() -> None:
    for column_name, nullable in _PRICE_COLUMNS:
        op.alter_column(
            "scm_product",
            column_name,
            existing_type=sa.Numeric(18, 4),
            type_=sa.Numeric(65, 30),
            existing_nullable=nullable,
        )


def downgrade() -> None:
    bind = op.get_bind()
    unsafe_conditions = " OR ".join(
        f"(`{column_name}` IS NOT NULL AND "
        f"(`{column_name}` <> ROUND(`{column_name}`, 4) "
        f"OR ABS(`{column_name}`) >= 100000000000000))"
        for column_name, _ in _PRICE_COLUMNS
    )
    unsafe_count = bind.execute(
        sa.text(f"SELECT COUNT(*) FROM `scm_product` WHERE {unsafe_conditions}")
    ).scalar_one()
    if unsafe_count:
        raise RuntimeError(
            "Cannot downgrade Product prices to DECIMAL(18,4): "
            "existing values would lose precision or exceed the integer range"
        )

    for column_name, nullable in reversed(_PRICE_COLUMNS):
        op.alter_column(
            "scm_product",
            column_name,
            existing_type=sa.Numeric(65, 30),
            type_=sa.Numeric(18, 4),
            existing_nullable=nullable,
        )
