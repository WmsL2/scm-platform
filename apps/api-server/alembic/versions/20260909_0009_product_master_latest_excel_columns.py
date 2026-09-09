"""align product master with latest Excel columns

Revision ID: 20260909_0009
Revises: 20260909_0008
"""

import sqlalchemy as sa

from alembic import op

revision = "20260909_0009"
down_revision = "20260909_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scm_product", sa.Column("selling_points", sa.Text(), nullable=True))
    op.add_column("scm_product", sa.Column("storefront_type", sa.String(64), nullable=True))
    op.drop_column("scm_product", "remote_area_freight_note")


def downgrade() -> None:
    op.add_column("scm_product", sa.Column("remote_area_freight_note", sa.Text(), nullable=True))
    op.drop_column("scm_product", "storefront_type")
    op.drop_column("scm_product", "selling_points")
