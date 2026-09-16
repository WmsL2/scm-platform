"""允许投标项目使用已作废状态。

Revision ID: 20260916_0027
Revises: 20260916_0026
"""

from alembic import op

revision = "20260916_0027"
down_revision = "20260916_0026"
branch_labels = None
depends_on = None

_WITHOUT_VOIDED = (
    "status IN ('IMPORTED', 'MATCHING', 'SELECTING', 'READY', 'EXPORTED', "
    "'SUBMITTED', 'WON', 'LOST')"
)
_WITH_VOIDED = (
    "status IN ('IMPORTED', 'MATCHING', 'SELECTING', 'READY', 'EXPORTED', "
    "'SUBMITTED', 'WON', 'LOST', 'VOIDED')"
)


def upgrade() -> None:
    op.drop_constraint("ck_scm_bid_project_status", "scm_bid_project", type_="check")
    op.create_check_constraint("ck_scm_bid_project_status", "scm_bid_project", _WITH_VOIDED)


def downgrade() -> None:
    op.drop_constraint("ck_scm_bid_project_status", "scm_bid_project", type_="check")
    op.create_check_constraint("ck_scm_bid_project_status", "scm_bid_project", _WITHOUT_VOIDED)
