"""add free recommendation project and persistence foundation

Revision ID: 20260923_0039
Revises: 20260922_0038
"""

import sqlalchemy as sa

from alembic import op

revision = "20260923_0039"
down_revision = "20260922_0038"
branch_labels = None
depends_on = None

RECOMMENDATION_PERMISSIONS = (
    (
        "70000000-0000-0000-0000-000000000001",
        "recommendation:create",
        "创建自由推品项目与模板",
        "ACTION",
    ),
    ("70000000-0000-0000-0000-000000000002", "recommendation:run", "运行自由推品", "ACTION"),
    ("70000000-0000-0000-0000-000000000003", "recommendation:detail", "查看自由推品详情", "API"),
    ("70000000-0000-0000-0000-000000000004", "recommendation:review", "审核自由推品候选", "ACTION"),
    ("70000000-0000-0000-0000-000000000005", "recommendation:export", "导出自由推品结果", "ACTION"),
)


def _uuid() -> sa.CHAR:
    return sa.CHAR(36)


def _replace_check(table: str, old: str, new: sa.CheckConstraint) -> None:
    op.drop_constraint(old, table, type_="check")
    op.create_check_constraint(new.name, table, new.sqltext)


def upgrade() -> None:
    op.add_column(
        "scm_bid_project",
        sa.Column(
            "project_type", sa.String(32), nullable=False, server_default="FILTER_RECOMMENDATION"
        ),
    )
    _replace_check(
        "scm_bid_project",
        "ck_scm_bid_project_import_status",
        sa.CheckConstraint(
            "import_status IN ('PARSED', 'MAPPING_REQUIRED', 'FAILED', 'NOT_REQUIRED')",
            name="ck_scm_bid_project_import_status",
        ),
    )
    op.create_check_constraint(
        "ck_scm_bid_project_project_type",
        "scm_bid_project",
        "project_type IN ('FILTER_RECOMMENDATION', 'FREE_RECOMMENDATION', 'PPT_SOLUTION')",
    )
    op.alter_column("scm_bid_project", "project_type", server_default=None)
    _replace_check(
        "scm_bid_project_file",
        "ck_scm_bid_project_file_type",
        sa.CheckConstraint(
            "file_type IN ('ORIGINAL', 'QUOTED_EXPORT', 'RECOMMENDATION_TEMPLATE')",
            name="ck_scm_bid_project_file_type",
        ),
    )

    op.create_table(
        "scm_recommendation_template_mapping",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_id", _uuid(), nullable=False),
        sa.Column("template_file_id", _uuid(), nullable=False),
        sa.Column("template_sha256", sa.String(64), nullable=False),
        sa.Column("sheet_name", sa.String(128), nullable=False),
        sa.Column("header_row", sa.Integer(), nullable=False),
        sa.Column("data_start_row", sa.Integer(), nullable=False),
        sa.Column("mapping_json", sa.JSON(), nullable=False),
        sa.Column("confirmed_by", _uuid(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["template_file_id"], ["scm_bid_project_file.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_file_id", name="uq_scm_recommendation_template_mapping_file"),
    )
    op.create_index(
        "ix_scm_recommendation_template_mapping_project_id",
        "scm_recommendation_template_mapping",
        ["project_id"],
    )
    op.create_index(
        "ix_scm_recommendation_template_mapping_template_file_id",
        "scm_recommendation_template_mapping",
        ["template_file_id"],
    )
    op.create_table(
        "scm_recommendation_run",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_id", _uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("raw_requirement_snapshot", sa.Text(), nullable=False),
        sa.Column("parsed_requirement", sa.JSON(), nullable=True),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", _uuid(), nullable=False),
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
            "status IN ('DRAFT', 'QUEUED', 'ANALYZING', 'RETRIEVING', 'RANKING', "
            "'CANDIDATES_READY', 'WAITING_CONFIRMATION', 'CONFIRMED', 'EXPORTED', "
            "'FAILED', 'NO_CANDIDATES', 'NEEDS_INPUT', 'CANCELLED')",
            name="ck_scm_recommendation_run_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_scm_recommendation_run_project_id", ["project_id"]),
        ("ix_scm_recommendation_run_status", ["status"]),
        ("ix_scm_recommendation_run_created_at", ["created_at"]),
    ):
        op.create_index(name, "scm_recommendation_run", columns)
    op.create_table(
        "scm_recommendation_category_choice",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("run_id", _uuid(), nullable=False),
        sa.Column("level1_name", sa.String(255)),
        sa.Column("level2_name", sa.String(255)),
        sa.Column("level3_name", sa.String(255)),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["run_id"], ["scm_recommendation_run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scm_recommendation_category_choice_run_id",
        "scm_recommendation_category_choice",
        ["run_id"],
    )
    op.create_table(
        "scm_recommendation_candidate",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("run_id", _uuid(), nullable=False),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(9, 4)),
        sa.Column("reason", sa.Text()),
        sa.Column("manual_flags", sa.JSON()),
        sa.Column("product_snapshot", sa.JSON(), nullable=False),
        sa.Column("supplier_snapshot", sa.JSON(), nullable=False),
        sa.Column("price_snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["run_id"], ["scm_recommendation_run.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["scm_product.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "product_id", name="uq_scm_recommendation_candidate_run_product"
        ),
    )
    for name, columns in (
        ("ix_scm_recommendation_candidate_run_id", ["run_id"]),
        ("ix_scm_recommendation_candidate_product_id", ["product_id"]),
        ("ix_scm_recommendation_candidate_run_rank", ["run_id", "rank"]),
    ):
        op.create_index(name, "scm_recommendation_candidate", columns)
    op.create_table(
        "scm_recommendation_confirmation",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("candidate_id", _uuid(), nullable=False),
        sa.Column("campaign_price", sa.Numeric(65, 30)),
        sa.Column("delivery_status", sa.String(32)),
        sa.Column("inventory_status", sa.String(32)),
        sa.Column("fulfillment_cycle", sa.String(255)),
        sa.Column("evidence", sa.Text()),
        sa.Column("confirmed_by", _uuid()),
        sa.Column("confirmed_at", sa.DateTime()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["scm_recommendation_candidate.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_id", name="uq_scm_recommendation_confirmation_candidate"),
    )
    for permission_id, code, name, permission_type in RECOMMENDATION_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO sys_permission "
                "(id, permission_code, permission_name, permission_type) "
                "VALUES (:id, :code, :name, :kind)"
            ).bindparams(id=permission_id, code=code, name=name, kind=permission_type)
        )
        op.execute(
            sa.text(
                "INSERT INTO sys_role_permission (role_id, permission_id) "
                "SELECT r.id, :permission_id FROM sys_role r "
                "WHERE r.role_code = 'boss' AND r.is_deleted = false "
                "AND NOT EXISTS (SELECT 1 FROM sys_role_permission rp "
                "WHERE rp.role_id = r.id AND rp.permission_id = :permission_id)"
            ).bindparams(permission_id=permission_id)
        )


def downgrade() -> None:
    bind = op.get_bind()
    checks = (
        "SELECT COUNT(*) FROM scm_bid_project "
        "WHERE project_type <> 'FILTER_RECOMMENDATION' OR import_status = 'NOT_REQUIRED'",
        "SELECT COUNT(*) FROM scm_bid_project_file WHERE file_type = 'RECOMMENDATION_TEMPLATE'",
        "SELECT COUNT(*) FROM scm_recommendation_template_mapping",
        "SELECT COUNT(*) FROM scm_recommendation_run",
        "SELECT COUNT(*) FROM scm_recommendation_category_choice",
        "SELECT COUNT(*) FROM scm_recommendation_candidate",
        "SELECT COUNT(*) FROM scm_recommendation_confirmation",
    )
    if any(int(bind.scalar(sa.text(statement)) or 0) > 0 for statement in checks):
        raise RuntimeError(
            "Cannot downgrade 20260923_0039 while free-recommendation data exists. "
            "Remove or migrate FREE_RECOMMENDATION data explicitly before downgrading."
        )
    ids = [row[0] for row in RECOMMENDATION_PERMISSIONS]
    op.execute(
        sa.text("DELETE FROM sys_role_permission WHERE permission_id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True, value=ids)
        )
    )
    op.execute(
        sa.text("DELETE FROM sys_permission WHERE id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True, value=ids)
        )
    )
    op.drop_table("scm_recommendation_confirmation")
    op.drop_table("scm_recommendation_candidate")
    op.drop_table("scm_recommendation_category_choice")
    op.drop_table("scm_recommendation_run")
    op.drop_table("scm_recommendation_template_mapping")
    op.drop_constraint("ck_scm_bid_project_file_type", "scm_bid_project_file", type_="check")
    op.create_check_constraint(
        "ck_scm_bid_project_file_type",
        "scm_bid_project_file",
        "file_type IN ('ORIGINAL', 'QUOTED_EXPORT')",
    )
    op.drop_constraint("ck_scm_bid_project_project_type", "scm_bid_project", type_="check")
    op.drop_constraint("ck_scm_bid_project_import_status", "scm_bid_project", type_="check")
    op.create_check_constraint(
        "ck_scm_bid_project_import_status",
        "scm_bid_project",
        "import_status IN ('PARSED', 'MAPPING_REQUIRED', 'FAILED')",
    )
    op.drop_column("scm_bid_project", "project_type")
