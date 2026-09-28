"""add type-5 ppt solution workflow

Revision ID: 20260928_0041
Revises: 20260923_0040
"""

import sqlalchemy as sa

from alembic import op

revision = "20260928_0041"
down_revision = "20260923_0040"
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
        "'RECOMMENDATION_EXPORT', 'PPT_TEMPLATE', 'PPT_EXPORT')",
    )
    op.create_table(
        "scm_ppt_solution_package",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("run_id", _uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("price_tier", sa.Numeric(18, 4), nullable=True),
        sa.Column("total_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", _uuid(), nullable=False),
        sa.Column("selected_by", _uuid(), nullable=True),
        sa.Column("selected_at", sa.DateTime(), nullable=True),
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
    )
    op.create_index(
        "ix_scm_ppt_solution_package_run_id", "scm_ppt_solution_package", ["run_id"]
    )
    op.create_index(
        "ix_scm_ppt_solution_package_selected",
        "scm_ppt_solution_package",
        ["run_id", "is_selected"],
    )
    op.create_table(
        "scm_ppt_solution_package_item",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("package_id", _uuid(), nullable=False),
        sa.Column("candidate_id", _uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("line_total", sa.Numeric(18, 4), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["package_id"], ["scm_ppt_solution_package.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["scm_recommendation_candidate.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "package_id", "candidate_id", name="uq_scm_ppt_solution_package_item_candidate"
        ),
    )
    op.create_index(
        "ix_scm_ppt_solution_package_item_package_id",
        "scm_ppt_solution_package_item",
        ["package_id"],
    )
    op.create_index(
        "ix_scm_ppt_solution_package_item_candidate_id",
        "scm_ppt_solution_package_item",
        ["candidate_id"],
    )
    op.create_table(
        "scm_ppt_generation_task",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_id", _uuid(), nullable=False),
        sa.Column("run_id", _uuid(), nullable=False),
        sa.Column("template_file_id", _uuid(), nullable=True),
        sa.Column("output_file_id", _uuid(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("provider_session_id", sa.String(255), nullable=True),
        sa.Column("provider_artifact_id", sa.String(255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", _uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
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
            "status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_scm_ppt_generation_task_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["run_id"], ["scm_recommendation_run.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_file_id"], ["scm_bid_project_file.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["output_file_id"], ["scm_bid_project_file.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scm_ppt_generation_task_project_id", "scm_ppt_generation_task", ["project_id"]
    )
    op.create_index("ix_scm_ppt_generation_task_run_id", "scm_ppt_generation_task", ["run_id"])
    op.create_index("ix_scm_ppt_generation_task_status", "scm_ppt_generation_task", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "scm_ppt_generation_task",
        "scm_ppt_solution_package_item",
        "scm_ppt_solution_package",
    ):
        if int(bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table}")) or 0) > 0:
            raise RuntimeError(f"Cannot downgrade 20260928_0041 while {table} contains data.")
    if int(
        bind.scalar(
            sa.text(
                "SELECT COUNT(*) FROM scm_bid_project_file "
                "WHERE file_type IN ('PPT_TEMPLATE', 'PPT_EXPORT')"
            )
        )
        or 0
    ) > 0:
        raise RuntimeError("Cannot downgrade while PPT template or export files exist.")
    op.drop_index("ix_scm_ppt_generation_task_status", table_name="scm_ppt_generation_task")
    op.drop_index("ix_scm_ppt_generation_task_run_id", table_name="scm_ppt_generation_task")
    op.drop_index("ix_scm_ppt_generation_task_project_id", table_name="scm_ppt_generation_task")
    op.drop_table("scm_ppt_generation_task")
    op.drop_index(
        "ix_scm_ppt_solution_package_item_candidate_id",
        table_name="scm_ppt_solution_package_item",
    )
    op.drop_index(
        "ix_scm_ppt_solution_package_item_package_id",
        table_name="scm_ppt_solution_package_item",
    )
    op.drop_table("scm_ppt_solution_package_item")
    op.drop_index("ix_scm_ppt_solution_package_selected", table_name="scm_ppt_solution_package")
    op.drop_index("ix_scm_ppt_solution_package_run_id", table_name="scm_ppt_solution_package")
    op.drop_table("scm_ppt_solution_package")
    op.drop_constraint("ck_scm_bid_project_file_type", "scm_bid_project_file", type_="check")
    op.create_check_constraint(
        "ck_scm_bid_project_file_type",
        "scm_bid_project_file",
        "file_type IN ('ORIGINAL', 'QUOTED_EXPORT', 'RECOMMENDATION_TEMPLATE', "
        "'RECOMMENDATION_EXPORT')",
    )
