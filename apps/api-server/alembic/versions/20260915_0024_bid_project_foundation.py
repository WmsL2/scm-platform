"""新增投标项目基础设施

Revision ID: 20260915_0024
Revises: 20260914_0023
"""

import sqlalchemy as sa

from alembic import op

revision = "20260915_0024"
down_revision = "20260914_0023"
branch_labels = None
depends_on = None

BID_PERMISSIONS = (
    ("50000000-0000-0000-0000-000000000001", "bid:list", "查看投标项目", "MENU"),
    ("50000000-0000-0000-0000-000000000002", "bid:detail", "查看投标项目详情", "API"),
    ("50000000-0000-0000-0000-000000000003", "bid:create", "新建投标项目", "ACTION"),
    ("50000000-0000-0000-0000-000000000004", "bid:match", "执行商品匹配", "ACTION"),
    ("50000000-0000-0000-0000-000000000005", "bid:select", "人工选品与无法报价", "ACTION"),
    ("50000000-0000-0000-0000-000000000006", "bid:export", "生成投标报价文件", "ACTION"),
    ("50000000-0000-0000-0000-000000000007", "bid:file:download", "下载投标文件", "API"),
    ("50000000-0000-0000-0000-000000000008", "bid:submit", "标记已投标", "ACTION"),
    ("50000000-0000-0000-0000-000000000009", "bid:result", "维护投标结果", "ACTION"),
)


def _uuid() -> sa.CHAR:
    return sa.CHAR(36)


def _grant_default_administrator(permission_id: str) -> None:
    op.execute(
        sa.text(
            "INSERT INTO sys_role_permission (role_id, permission_id) "
            "SELECT r.id, :permission_id FROM sys_role AS r "
            "WHERE r.role_code = 'boss' AND r.is_deleted = false "
            "AND NOT EXISTS (SELECT 1 FROM sys_role_permission AS rp "
            "WHERE rp.role_id = r.id AND rp.permission_id = :permission_id)"
        ).bindparams(permission_id=permission_id)
    )


def upgrade() -> None:
    op.create_table(
        "scm_bid_template",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("template_code", sa.String(64), nullable=False),
        sa.Column("template_name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("sheet_name", sa.String(128), nullable=False),
        sa.Column("header_row", sa.Integer(), nullable=False),
        sa.Column("data_start_row", sa.Integer(), nullable=False),
        sa.Column("import_mapping", sa.JSON(), nullable=False),
        sa.Column("export_mapping", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", _uuid(), nullable=True),
        sa.Column("updated_by", _uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_code", "version", name="uq_scm_bid_template_code_version"),
    )
    op.create_index("ix_scm_bid_template_fingerprint", "scm_bid_template", ["fingerprint"])
    op.create_index("ix_scm_bid_template_active", "scm_bid_template", ["is_active"])

    op.create_table(
        "scm_bid_project",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_code", sa.String(32), nullable=False),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column("buyer_name", sa.String(255), nullable=False),
        sa.Column("deadline_at", sa.DateTime(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("template_id", _uuid(), nullable=True),
        sa.Column("template_version", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("import_status", sa.String(32), nullable=False),
        sa.Column("import_error", sa.Text(), nullable=True),
        sa.Column("total_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("submitted_file_id", _uuid(), nullable=True),
        sa.Column("created_by", _uuid(), nullable=False),
        sa.Column("updated_by", _uuid(), nullable=True),
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
            "status IN ('IMPORTED', 'MATCHING', 'SELECTING', 'READY', 'EXPORTED', "
            "'SUBMITTED', 'WON', 'LOST')",
            name="ck_scm_bid_project_status",
        ),
        sa.CheckConstraint(
            "import_status IN ('PARSED', 'MAPPING_REQUIRED', 'FAILED')",
            name="ck_scm_bid_project_import_status",
        ),
        sa.ForeignKeyConstraint(["template_id"], ["scm_bid_template.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_code"),
    )
    op.create_index("ix_scm_bid_project_status", "scm_bid_project", ["status"])
    op.create_index("ix_scm_bid_project_created_at", "scm_bid_project", ["created_at"])
    op.create_index("ix_scm_bid_project_buyer_name", "scm_bid_project", ["buyer_name"])

    op.create_table(
        "scm_bid_project_file",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_id", _uuid(), nullable=False),
        sa.Column("file_type", sa.String(32), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_by", _uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.CheckConstraint(
            "file_type IN ('ORIGINAL', 'QUOTED_EXPORT')", name="ck_scm_bid_project_file_type"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "file_type",
            "version_no",
            name="uq_scm_bid_project_file_version",
        ),
    )
    op.create_index("ix_scm_bid_project_file_project_id", "scm_bid_project_file", ["project_id"])
    op.create_index("ix_scm_bid_project_file_created_at", "scm_bid_project_file", ["created_at"])
    op.create_foreign_key(
        "fk_scm_bid_project_submitted_file",
        "scm_bid_project",
        "scm_bid_project_file",
        ["submitted_file_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "scm_bid_project_item",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_id", _uuid(), nullable=False),
        sa.Column("sheet_name", sa.String(128), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("source_data", sa.JSON(), nullable=False),
        sa.Column("product_name", sa.String(512), nullable=True),
        sa.Column("brand", sa.String(128), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("specification", sa.Text(), nullable=True),
        sa.Column("category_text", sa.String(512), nullable=True),
        sa.Column("category_id", _uuid(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("max_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("buyer_item_code", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("current_selection_id", _uuid(), nullable=True),
        sa.Column("no_quote_reason", sa.Text(), nullable=True),
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
            "status IN ('PENDING', 'NO_MATCH', 'UNIQUE_MATCH', 'MULTIPLE_MATCH', "
            "'SELECTED', 'NO_QUOTE')",
            name="ck_scm_bid_project_item_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["scm_category.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "sheet_name",
            "source_row_number",
            name="uq_scm_bid_project_item_source_row",
        ),
    )
    for name, columns in (
        ("ix_scm_bid_project_item_project_id", ["project_id"]),
        ("ix_scm_bid_project_item_status", ["status"]),
        ("ix_scm_bid_project_item_category_id", ["category_id"]),
        ("ix_scm_bid_project_item_current_selection_id", ["current_selection_id"]),
    ):
        op.create_index(name, "scm_bid_project_item", columns)

    op.create_table(
        "scm_bid_project_event",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_id", _uuid(), nullable=False),
        sa.Column("from_status", sa.String(16), nullable=True),
        sa.Column("to_status", sa.String(16), nullable=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor_id", _uuid(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scm_bid_project_event_project_id", "scm_bid_project_event", ["project_id"]
    )
    op.create_index(
        "ix_scm_bid_project_event_occurred_at", "scm_bid_project_event", ["occurred_at"]
    )

    op.create_table(
        "scm_match_task",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_id", _uuid(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("total_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", _uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_scm_match_task_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["scm_bid_project.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_scm_match_task_project_id", ["project_id"]),
        ("ix_scm_match_task_status", ["status"]),
        ("ix_scm_match_task_created_at", ["created_at"]),
    ):
        op.create_index(name, "scm_match_task", columns)

    op.create_table(
        "scm_match_candidate",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("match_task_id", _uuid(), nullable=False),
        sa.Column("project_item_id", _uuid(), nullable=False),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("supplier_id", _uuid(), nullable=False),
        sa.Column("score", sa.Numeric(9, 4), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("match_method", sa.String(32), nullable=False),
        sa.Column("match_reason", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(["match_task_id"], ["scm_match_task.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["project_item_id"],
            ["scm_bid_project_item.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["scm_product.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["scm_supplier.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "match_task_id",
            "project_item_id",
            "product_id",
            name="uq_scm_match_candidate_task_item_product",
        ),
    )
    for name, columns in (
        ("ix_scm_match_candidate_project_item_id", ["project_item_id"]),
        ("ix_scm_match_candidate_product_id", ["product_id"]),
        ("ix_scm_match_candidate_supplier_id", ["supplier_id"]),
    ):
        op.create_index(name, "scm_match_candidate", columns)

    op.create_table(
        "scm_bid_item_selection",
        sa.Column("id", _uuid(), nullable=False),
        sa.Column("project_item_id", _uuid(), nullable=False),
        sa.Column("candidate_id", _uuid(), nullable=True),
        sa.Column("product_id", _uuid(), nullable=False),
        sa.Column("supplier_id", _uuid(), nullable=False),
        sa.Column("selected_unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("requirement_snapshot", sa.JSON(), nullable=False),
        sa.Column("product_snapshot", sa.JSON(), nullable=False),
        sa.Column("supplier_snapshot", sa.JSON(), nullable=False),
        sa.Column("price_snapshot", sa.JSON(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", _uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.ForeignKeyConstraint(
            ["project_item_id"],
            ["scm_bid_project_item.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["scm_match_candidate.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["scm_product.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["scm_supplier.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_scm_bid_item_selection_project_item_id", ["project_item_id"]),
        ("ix_scm_bid_item_selection_product_id", ["product_id"]),
        ("ix_scm_bid_item_selection_supplier_id", ["supplier_id"]),
        ("ix_scm_bid_item_selection_created_at", ["created_at"]),
    ):
        op.create_index(name, "scm_bid_item_selection", columns)
    op.create_foreign_key(
        "fk_scm_bid_project_item_current_selection",
        "scm_bid_project_item",
        "scm_bid_item_selection",
        ["current_selection_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        sa.text(
            "INSERT INTO sys_biz_sequence (id, sequence_key, prefix, next_value) "
            "VALUES (:id, 'BID_PROJECT', 'BID', 1)"
        ).bindparams(id="00000000-0000-0000-0000-000000000002")
    )
    for permission_id, code, name, permission_type in BID_PERMISSIONS:
        op.execute(
            sa.text(
                "INSERT INTO sys_permission "
                "(id, permission_code, permission_name, permission_type) "
                "VALUES (:id, :code, :name, :permission_type)"
            ).bindparams(id=permission_id, code=code, name=name, permission_type=permission_type)
        )
        _grant_default_administrator(permission_id)


def downgrade() -> None:
    permission_ids = [row[0] for row in BID_PERMISSIONS]
    op.execute(
        sa.text(
            "DELETE FROM sys_role_permission WHERE permission_id IN :permission_ids"
        ).bindparams(
            sa.bindparam("permission_ids", expanding=True, value=permission_ids)
        )
    )
    op.execute(
        sa.text("DELETE FROM sys_permission WHERE id IN :permission_ids").bindparams(
            sa.bindparam("permission_ids", expanding=True, value=permission_ids)
        )
    )
    op.execute(sa.text("DELETE FROM sys_biz_sequence WHERE sequence_key = 'BID_PROJECT'"))
    op.drop_constraint(
        "fk_scm_bid_project_item_current_selection", "scm_bid_project_item", type_="foreignkey"
    )
    for name in (
        "ix_scm_bid_item_selection_created_at",
        "ix_scm_bid_item_selection_supplier_id",
        "ix_scm_bid_item_selection_product_id",
        "ix_scm_bid_item_selection_project_item_id",
    ):
        op.drop_index(name, table_name="scm_bid_item_selection")
    op.drop_table("scm_bid_item_selection")
    for name in (
        "ix_scm_match_candidate_supplier_id",
        "ix_scm_match_candidate_product_id",
        "ix_scm_match_candidate_project_item_id",
    ):
        op.drop_index(name, table_name="scm_match_candidate")
    op.drop_table("scm_match_candidate")
    for name in (
        "ix_scm_match_task_created_at",
        "ix_scm_match_task_status",
        "ix_scm_match_task_project_id",
    ):
        op.drop_index(name, table_name="scm_match_task")
    op.drop_table("scm_match_task")
    op.drop_index("ix_scm_bid_project_event_occurred_at", table_name="scm_bid_project_event")
    op.drop_index("ix_scm_bid_project_event_project_id", table_name="scm_bid_project_event")
    op.drop_table("scm_bid_project_event")
    for name in (
        "ix_scm_bid_project_item_current_selection_id",
        "ix_scm_bid_project_item_category_id",
        "ix_scm_bid_project_item_status",
        "ix_scm_bid_project_item_project_id",
    ):
        op.drop_index(name, table_name="scm_bid_project_item")
    op.drop_table("scm_bid_project_item")
    op.drop_constraint("fk_scm_bid_project_submitted_file", "scm_bid_project", type_="foreignkey")
    op.drop_index("ix_scm_bid_project_file_created_at", table_name="scm_bid_project_file")
    op.drop_index("ix_scm_bid_project_file_project_id", table_name="scm_bid_project_file")
    op.drop_table("scm_bid_project_file")
    op.drop_index("ix_scm_bid_project_buyer_name", table_name="scm_bid_project")
    op.drop_index("ix_scm_bid_project_created_at", table_name="scm_bid_project")
    op.drop_index("ix_scm_bid_project_status", table_name="scm_bid_project")
    op.drop_table("scm_bid_project")
    op.drop_index("ix_scm_bid_template_active", table_name="scm_bid_template")
    op.drop_index("ix_scm_bid_template_fingerprint", table_name="scm_bid_template")
    op.drop_table("scm_bid_template")
