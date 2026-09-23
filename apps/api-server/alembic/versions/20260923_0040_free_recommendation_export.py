"""add free recommendation export records

Revision ID: 20260923_0040
Revises: 20260923_0039
"""

import sqlalchemy as sa

from alembic import op

revision = "20260923_0040"
down_revision = "20260923_0039"
branch_labels = None
depends_on = None


def _uuid() -> sa.CHAR:
    return sa.CHAR(36)


def upgrade() -> None:
    op.drop_constraint("ck_scm_bid_project_file_type", "scm_bid_project_file", type_="check")
    op.create_check_constraint(
        "ck_scm_bid_project_file_type",
        "scm_bid_project_file",
        "file_type IN ('ORIGINAL', 'QUOTED_EXPORT', 'RECOMMENDATION_TEMPLATE', "
        "'RECOMMENDATION_EXPORT')",
    )
    op.add_column(
        "scm_recommendation_confirmation",
        sa.Column("factory_direct", sa.String(16), nullable=False, server_default="PENDING"),
    )
    op.create_check_constraint(
        "ck_scm_recommendation_confirmation_factory_direct",
        "scm_recommendation_confirmation",
        "factory_direct IN ('PENDING', 'YES', 'NO')",
    )
    op.create_table(
        "scm_recommendation_export",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_id", _uuid(), nullable=False),
        sa.Column("run_id", _uuid(), nullable=False),
        sa.Column("template_file_id", _uuid(), nullable=False),
        sa.Column("template_mapping_id", _uuid(), nullable=False),
        sa.Column("export_file_id", _uuid(), nullable=False),
        sa.Column("mapping_snapshot", sa.JSON(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("exported_by", _uuid(), nullable=False),
        sa.Column(
            "exported_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["scm_recommendation_run.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_file_id"], ["scm_bid_project_file.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["template_mapping_id"], ["scm_recommendation_template_mapping.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["export_file_id"], ["scm_bid_project_file.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("export_file_id", name="uq_scm_recommendation_export_file"),
        sa.UniqueConstraint(
            "project_id", "run_id", "version_no", name="uq_scm_recommendation_export_version"
        ),
    )
    op.create_index(
        "ix_scm_recommendation_export_project_id", "scm_recommendation_export", ["project_id"]
    )
    op.create_index(
        "ix_scm_recommendation_export_run_id", "scm_recommendation_export", ["run_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()
    if int(bind.scalar(sa.text("SELECT COUNT(*) FROM scm_recommendation_export")) or 0) > 0:
        raise RuntimeError(
            "Cannot downgrade 20260923_0040 while recommendation export records exist."
        )
    if (
        int(
            bind.scalar(
                sa.text(
                    "SELECT COUNT(*) FROM scm_recommendation_confirmation "
                    "WHERE factory_direct <> 'PENDING'"
                )
            )
            or 0
        )
        > 0
    ):
        raise RuntimeError(
            "Cannot downgrade 20260923_0040 while non-default factory-direct confirmations exist."
        )
    op.drop_index("ix_scm_recommendation_export_run_id", table_name="scm_recommendation_export")
    op.drop_index("ix_scm_recommendation_export_project_id", table_name="scm_recommendation_export")
    op.drop_table("scm_recommendation_export")
    op.drop_constraint(
        "ck_scm_recommendation_confirmation_factory_direct",
        "scm_recommendation_confirmation",
        type_="check",
    )
    op.drop_column("scm_recommendation_confirmation", "factory_direct")
    op.drop_constraint("ck_scm_bid_project_file_type", "scm_bid_project_file", type_="check")
    op.create_check_constraint(
        "ck_scm_bid_project_file_type",
        "scm_bid_project_file",
        "file_type IN ('ORIGINAL', 'QUOTED_EXPORT', 'RECOMMENDATION_TEMPLATE')",
    )
