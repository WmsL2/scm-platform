"""add recommendation run history index

Revision ID: 20261012_0053
Revises: 20261009_0052
Create Date: 2026-10-12
"""

from alembic import op

revision = "20261012_0053"
down_revision = "20261009_0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_scm_recommendation_run_project_created_at",
        "scm_recommendation_run",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scm_recommendation_run_project_created_at",
        table_name="scm_recommendation_run",
    )
