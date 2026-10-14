"""allow controlled async task retries by default

Revision ID: 20261014_0058
Revises: 20261014_0057
Create Date: 2026-10-14
"""

import sqlalchemy as sa

from alembic import op

revision = "20261014_0058"
down_revision = "20261014_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("scm_async_task", "max_attempts", server_default=sa.text("3"))


def downgrade() -> None:
    op.alter_column("scm_async_task", "max_attempts", server_default=sa.text("1"))
