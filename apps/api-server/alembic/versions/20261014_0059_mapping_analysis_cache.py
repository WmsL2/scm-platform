"""add mapping analysis cache

Revision ID: 20261014_0059
Revises: 20261014_0058
Create Date: 2026-10-14
"""

import sqlalchemy as sa

from alembic import op

revision = "20261014_0059"
down_revision = "20261014_0058"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scm_mapping_analysis_cache",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("project_id", sa.CHAR(length=36), nullable=False),
        sa.Column("file_id", sa.CHAR(length=36), nullable=False),
        sa.Column("async_task_id", sa.CHAR(length=36), nullable=False),
        sa.Column("analysis_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','FAILED')",
            name="ck_scm_mapping_analysis_cache_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["async_task_id"], ["scm_async_task.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_scm_mapping_analysis_cache_lookup",
        "scm_mapping_analysis_cache",
        ["project_id", "file_id", "analysis_key"],
        unique=True,
    )
    op.create_index(
        "ix_scm_mapping_analysis_cache_task_id", "scm_mapping_analysis_cache", ["async_task_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_scm_mapping_analysis_cache_task_id", table_name="scm_mapping_analysis_cache")
    op.drop_index("uq_scm_mapping_analysis_cache_lookup", table_name="scm_mapping_analysis_cache")
    op.drop_table("scm_mapping_analysis_cache")
