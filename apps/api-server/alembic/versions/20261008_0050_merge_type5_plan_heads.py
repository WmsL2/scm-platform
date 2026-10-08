"""merge Type-5 plan selection and token-safety migration branches

Revision ID: 20261008_0050
Revises: 20261008_0047, 20261008_0049
"""

revision = "20261008_0050"
down_revision = ("20261008_0047", "20261008_0049")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Graph-only merge: each parent owns its existing, independently applied DDL.
    pass


def downgrade() -> None:
    # The parent migrations retain their own reversible DDL.
    pass
