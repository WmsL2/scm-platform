"""add Product Import task cleanup index

Revision ID: 20260922_0038
Revises: 20260921_0037
"""

import sqlalchemy as sa

from alembic import op

revision = "20260922_0038"
down_revision = "20260921_0037"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_scm_product_import_task_status_created_at"


def upgrade() -> None:
    indexes = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("scm_product_import_task")
    }
    if _INDEX_NAME not in indexes:
        op.create_index(_INDEX_NAME, "scm_product_import_task", ["status", "created_at"])


def downgrade() -> None:
    indexes = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("scm_product_import_task")
    }
    if _INDEX_NAME in indexes:
        op.drop_index(_INDEX_NAME, table_name="scm_product_import_task")
