from sqlalchemy import text

from app.core.database import SessionLocal


async def test_supplier_schema_and_permission_directory() -> None:
    expected_tables = {
        "scm_supplier",
        "scm_supplier_contact",
        "scm_supplier_qualification",
        "scm_supplier_cooperation_record",
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
            "created_at",
            "updated_at",
            "archived_at",
        } == supplier_columns

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
