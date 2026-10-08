"""freeze type-5 configuration on recommendation runs"""

import sqlalchemy as sa

from alembic import op

revision = "20261008_0049"
down_revision = "20261008_0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scm_recommendation_run", sa.Column("ppt_config_snapshot", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("scm_recommendation_run", "ppt_config_snapshot")
