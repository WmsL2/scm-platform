"""add type-5 generated solution plans

Revision ID: 20260930_0044
Revises: 20260930_0043
"""

import sqlalchemy as sa
from alembic import op

revision = "20260930_0044"
down_revision = "20260930_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scm_ppt_solution_plan",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("run_id", sa.CHAR(36), nullable=False),
        sa.Column("price_band_index", sa.Integer(), nullable=False),
        sa.Column("plan_no", sa.Integer(), nullable=False),
        sa.Column("plan_type", sa.String(16), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("total_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("candidate_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.CheckConstraint(
            "plan_type IN ('SINGLE', 'COMBINATION')", name="ck_scm_ppt_solution_plan_type"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["scm_recommendation_run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "price_band_index", "plan_no", name="uq_scm_ppt_solution_plan_run_band_no"
        ),
    )
    op.create_index("ix_scm_ppt_solution_plan_run_id", "scm_ppt_solution_plan", ["run_id"])


def downgrade() -> None:
    if int(op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM scm_ppt_solution_plan")) or 0):
        raise RuntimeError("Cannot downgrade 20260930_0044 while Type-5 solution plans exist.")
    op.drop_index("ix_scm_ppt_solution_plan_run_id", table_name="scm_ppt_solution_plan")
    op.drop_table("scm_ppt_solution_plan")
