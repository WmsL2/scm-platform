"""business sequence infrastructure

Revision ID: 20260907_0003
Revises: 20260903_0002
"""

import sqlalchemy as sa

from alembic import op

revision = "20260907_0003"
down_revision = "20260903_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sys_biz_sequence",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("sequence_key", sa.String(64), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("next_value", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.CHAR(36), nullable=True),
        sa.Column("updated_by", sa.CHAR(36), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("next_value >= 1", name="ck_sys_biz_sequence_next_value"),
        sa.UniqueConstraint("sequence_key", name="uq_sys_biz_sequence_sequence_key"),
    )
    op.execute(
        sa.text(
            "INSERT INTO sys_biz_sequence (id, sequence_key, prefix, next_value) "
            "VALUES ('00000000-0000-0000-0000-000000000001', 'SUPPLIER', 'SUP', 1)"
        )
    )


def downgrade() -> None:
    op.drop_table("sys_biz_sequence")
