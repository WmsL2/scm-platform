"""add type-5 recommendation configuration

Revision ID: 20260930_0043
Revises: 20260929_0042
"""

import sqlalchemy as sa

from alembic import op

revision = "20260930_0043"
down_revision = "20260929_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scm_ppt_recommendation_config",
        sa.Column("id", sa.CHAR(36), nullable=False),
        sa.Column("project_id", sa.CHAR(36), nullable=False),
        sa.Column("recommendation_mode", sa.String(16), nullable=False),
        sa.Column("price_bands", sa.JSON(), nullable=False),
        sa.Column("candidate_count_per_band", sa.Integer(), nullable=False),
        sa.Column("plan_count_per_band", sa.Integer(), nullable=False),
        sa.Column("fulfillment_deadline", sa.Date(), nullable=True),
        sa.Column("created_by", sa.CHAR(36), nullable=False),
        sa.Column("updated_by", sa.CHAR(36), nullable=False),
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
            "recommendation_mode IN ('SINGLE', 'COMBINATION', 'MIXED')",
            name="ck_scm_ppt_recommendation_config_mode",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_scm_ppt_recommendation_config_project"),
    )


def downgrade() -> None:
    if int(
        op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM scm_ppt_recommendation_config")) or 0
    ):
        raise RuntimeError(
            "Cannot downgrade 20260930_0043 while Type-5 recommendation configurations exist."
        )
    op.drop_table("scm_ppt_recommendation_config")
