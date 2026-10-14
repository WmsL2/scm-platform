"""add MySQL backed async task queue

Revision ID: 20261014_0057
Revises: 20261013_0056
Create Date: 2026-10-14
"""

import sqlalchemy as sa

from alembic import op

revision = "20261014_0057"
down_revision = "20261013_0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scm_async_task",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("project_id", sa.CHAR(length=36), nullable=False),
        sa.Column("run_id", sa.CHAR(length=36), nullable=True),
        sa.Column("task_kind", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_message", sa.String(length=500), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.CHAR(length=36), nullable=False),
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
            "task_kind IN ('TYPE1_MATCH','TYPE2_MATCH','TYPE3_CANDIDATE_GENERATION',"
            "'TYPE4_RECOMMENDATION_AGENT','TYPE5_RECOMMENDATION_GENERATION',"
            "'TYPE5_PPT_GENERATION','MAPPING_STRUCTURE_ANALYSIS')",
            name="ck_scm_async_task_kind",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','CANCELLED')",
            name="ck_scm_async_task_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scm_async_task_project_status", "scm_async_task", ["project_id", "status"])
    op.create_index("ix_scm_async_task_status_created", "scm_async_task", ["status", "created_at"])
    op.create_index("ix_scm_async_task_lease_expires_at", "scm_async_task", ["lease_expires_at"])
    op.create_index("ix_scm_async_task_run_id", "scm_async_task", ["run_id"])
    op.create_index("ix_scm_async_task_kind_status", "scm_async_task", ["task_kind", "status"])


def downgrade() -> None:
    op.drop_index("ix_scm_async_task_kind_status", table_name="scm_async_task")
    op.drop_index("ix_scm_async_task_run_id", table_name="scm_async_task")
    op.drop_index("ix_scm_async_task_lease_expires_at", table_name="scm_async_task")
    op.drop_index("ix_scm_async_task_status_created", table_name="scm_async_task")
    op.drop_index("ix_scm_async_task_project_status", table_name="scm_async_task")
    op.drop_table("scm_async_task")
