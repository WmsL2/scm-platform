"""decouple Product Master from Category Master

Revision ID: 20260918_0032
Revises: 20260918_0031
"""

import sqlalchemy as sa

from alembic import op

revision = "20260918_0032"
down_revision = "20260918_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _drop_category_reference("scm_product", "ix_scm_product_category_id")
    _drop_category_reference(
        "scm_product_import_row", "ix_scm_product_import_row_category_id"
    )


def _drop_category_reference(table_name: str, index_name: str) -> None:
    """Drop the FK by its constrained column because prior MySQL migrations left it unnamed."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if "category_id" not in columns:
        return
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key["constrained_columns"] == ["category_id"]:
            name = foreign_key.get("name")
            if name is not None:
                op.drop_constraint(name, table_name, type_="foreignkey")
    indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in indexes:
        op.drop_index(index_name, table_name=table_name)
    op.drop_column(table_name, "category_id")


def downgrade() -> None:
    op.add_column("scm_product_import_row", sa.Column("category_id", sa.CHAR(36), nullable=True))
    op.create_foreign_key(
        "fk_scm_product_import_row_category",
        "scm_product_import_row",
        "scm_category",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_scm_product_import_row_category_id",
        "scm_product_import_row",
        ["category_id"],
    )
    op.add_column("scm_product", sa.Column("category_id", sa.CHAR(36), nullable=True))
    op.create_foreign_key(
        "scm_product_ibfk_1",
        "scm_product",
        "scm_category",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_scm_product_category_id", "scm_product", ["category_id"])
