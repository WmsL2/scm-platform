from sqlalchemy import text

from app.core.database import SessionLocal


async def test_supplier_schema_and_permission_directory() -> None:
    expected_tables = {
        "scm_supplier",
        "scm_supplier_contact",
        "scm_supplier_qualification",
        "scm_supplier_cooperation_record",
        "scm_supplier_import_batch",
        "scm_supplier_import_row",
    }
    expected_permissions = {
        "supplier:list",
        "supplier:detail",
        "supplier:create",
        "supplier:update",
        "supplier:submit",
        "supplier:archive",
        "supplier:stop",
        "supplier:blacklist",
        "supplier:delete",
    }
    async with SessionLocal() as session:
        table_rows = await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name LIKE 'scm_supplier%'"
            )
        )
        assert {row[0] for row in table_rows} == expected_tables

        supplier_columns = {
            row[0]
            for row in (
                await session.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = DATABASE() AND table_name = 'scm_supplier'"
                    )
                )
            )
        }
        assert {
            "id",
            "supplier_code",
            "supplier_name",
            "main_brands",
            "advantage",
            "archive_status",
            "cooperation_status",
            "is_deleted",
            "created_by",
            "updated_by",
            "archived_by",
            "deleted_by",
            "created_at",
            "updated_at",
            "archived_at",
            "deleted_at",
        } == supplier_columns

        unique_index_rows = await session.execute(
            text(
                "SELECT index_name FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = 'scm_supplier' "
                "AND column_name = 'supplier_name' AND non_unique = 0"
            )
        )
        assert {row[0] for row in unique_index_rows} == {"uq_scm_supplier_supplier_name"}

        qualification_columns = {
            row[0]
            for row in (
                await session.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = DATABASE() "
                        "AND table_name = 'scm_supplier_qualification'"
                    )
                )
            )
        }
        assert qualification_columns == {
            "id",
            "supplier_id",
            "is_deleted",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        }

        permission_rows = await session.execute(
            text(
                "SELECT permission_code FROM sys_permission "
                "WHERE permission_code LIKE 'supplier:%'"
            )
        )
        assert {row[0] for row in permission_rows} == expected_permissions
