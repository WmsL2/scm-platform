"""Freeze the built-in template identity on Type-5 generation tasks.

Revision ID: 20261009_0051
Revises: 20261008_0050
"""

from alembic import op
import sqlalchemy as sa


revision = "20261009_0051"
down_revision = "20261008_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_ppt_generation_task",
        sa.Column("template_code", sa.String(length=64), nullable=False, server_default="SYSTEM_DEFAULT"),
    )
    op.add_column(
        "scm_ppt_generation_task",
        sa.Column("template_version", sa.String(length=32), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("scm_ppt_generation_task", "template_version")
    op.drop_column("scm_ppt_generation_task", "template_code")
