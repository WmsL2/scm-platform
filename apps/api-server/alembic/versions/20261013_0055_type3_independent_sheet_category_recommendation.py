"""add independent type3 sheet category recommendation tables

Revision ID: 20261013_0055
Revises: 20261012_0054
Create Date: 2026-10-13
"""

import sqlalchemy as sa
from alembic import op

revision = "20261013_0055"
down_revision = "20261012_0054"
branch_labels = None
depends_on = None


def _uuid() -> sa.String:
    return sa.String(length=36)


def upgrade() -> None:
    op.create_table("scm_type3_sheet_config", sa.Column("id", _uuid(), primary_key=True), sa.Column("project_id", _uuid(), sa.ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False), sa.Column("template_file_id", _uuid(), sa.ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"), nullable=False), sa.Column("sheet_name", sa.String(128), nullable=False), sa.Column("header_row", sa.Integer(), nullable=False), sa.Column("data_start_row", sa.Integer(), nullable=False), sa.Column("mapping_json", sa.JSON(), nullable=False), sa.Column("selected_nodes", sa.JSON(), nullable=False), sa.Column("created_by", _uuid(), nullable=False), sa.Column("updated_by", _uuid(), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("project_id", "sheet_name", name="uq_scm_type3_sheet_config_project_sheet"))
    op.create_index("ix_scm_type3_sheet_config_project_id", "scm_type3_sheet_config", ["project_id"])
    op.create_table("scm_type3_recommendation_run", sa.Column("id", _uuid(), primary_key=True), sa.Column("project_id", _uuid(), sa.ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False), sa.Column("raw_remark_snapshot", sa.Text(), nullable=False), sa.Column("parsed_remark", sa.JSON()), sa.Column("category_catalog_snapshot", sa.JSON()), sa.Column("sheet_snapshot", sa.JSON(), nullable=False), sa.Column("provider", sa.String(64)), sa.Column("model", sa.String(128)), sa.Column("prompt_version", sa.String(64)), sa.Column("status", sa.String(32), nullable=False), sa.Column("error", sa.Text()), sa.Column("created_by", _uuid(), nullable=False), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False), sa.CheckConstraint("status IN ('QUEUED','ANALYZING','RETRIEVING','WAITING_CONFIRMATION','CONFIRMED','EXPORTED','FAILED','NO_CANDIDATES')", name="ck_scm_type3_run_status"))
    op.create_index("ix_scm_type3_run_project_created", "scm_type3_recommendation_run", ["project_id", "created_at"])
    op.create_table("scm_type3_recommendation_candidate", sa.Column("id", _uuid(), primary_key=True), sa.Column("run_id", _uuid(), sa.ForeignKey("scm_type3_recommendation_run.id", ondelete="RESTRICT"), nullable=False), sa.Column("sheet_name", sa.String(128), nullable=False), sa.Column("product_id", _uuid(), sa.ForeignKey("scm_product.id", ondelete="RESTRICT"), nullable=False), sa.Column("rank", sa.Integer(), nullable=False), sa.Column("product_snapshot", sa.JSON(), nullable=False), sa.Column("supplier_snapshot", sa.JSON(), nullable=False), sa.Column("price_snapshot", sa.JSON(), nullable=False), sa.Column("confirmed_by", _uuid()), sa.Column("confirmed_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("run_id", "sheet_name", "product_id", name="uq_scm_type3_candidate_run_sheet_product"))
    op.create_index("ix_scm_type3_candidate_run_sheet_rank", "scm_type3_recommendation_candidate", ["run_id", "sheet_name", "rank"])
    op.create_table("scm_type3_recommendation_export", sa.Column("id", _uuid(), primary_key=True), sa.Column("project_id", _uuid(), sa.ForeignKey("scm_bid_project.id", ondelete="RESTRICT"), nullable=False), sa.Column("run_id", _uuid(), sa.ForeignKey("scm_type3_recommendation_run.id", ondelete="RESTRICT"), nullable=False), sa.Column("export_file_id", _uuid(), sa.ForeignKey("scm_bid_project_file.id", ondelete="RESTRICT"), nullable=False), sa.Column("version_no", sa.Integer(), nullable=False), sa.Column("exported_by", _uuid(), nullable=False), sa.Column("exported_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.UniqueConstraint("project_id", "run_id", "version_no", name="uq_scm_type3_export_version"))


def downgrade() -> None:
    op.drop_table("scm_type3_recommendation_export")
    op.drop_index("ix_scm_type3_candidate_run_sheet_rank", table_name="scm_type3_recommendation_candidate")
    op.drop_table("scm_type3_recommendation_candidate")
    op.drop_index("ix_scm_type3_run_project_created", table_name="scm_type3_recommendation_run")
    op.drop_table("scm_type3_recommendation_run")
    op.drop_index("ix_scm_type3_sheet_config_project_id", table_name="scm_type3_sheet_config")
    op.drop_table("scm_type3_sheet_config")
