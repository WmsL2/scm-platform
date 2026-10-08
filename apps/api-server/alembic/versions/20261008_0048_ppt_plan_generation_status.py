"""persist type-5 per-band plan generation outcomes

Revision ID: 20261008_0048
Revises: 20260930_0046
"""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0048"
down_revision = "20260930_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scm_ppt_plan_generation_status",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("run_id", sa.CHAR(36), nullable=False),
        sa.Column("price_band_index", sa.Integer(), nullable=False),
        sa.Column("requested_plan_count", sa.Integer(), nullable=False),
        sa.Column("generated_plan_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["scm_recommendation_run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "price_band_index", name="uq_scm_ppt_plan_generation_run_band"
        ),
    )
    op.create_index(
        "ix_scm_ppt_plan_generation_status_run_id", "scm_ppt_plan_generation_status", ["run_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scm_ppt_plan_generation_status_run_id", table_name="scm_ppt_plan_generation_status"
    )
    op.drop_table("scm_ppt_plan_generation_status")
