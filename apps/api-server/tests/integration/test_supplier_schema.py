import uuid

import pytest
from sqlalchemy import delete, text
from sqlalchemy.exc import DBAPIError

from app.core.database import SessionLocal
from app.modules.supplier.infrastructure.models import Supplier, SupplierCooperationRecord


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
        "supplier:resume",
        "supplier:unblacklist",
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


async def test_supplier_cooperation_history_constraint_allows_only_frozen_pairs() -> None:
    supplier_id = uuid.uuid4()
    async with SessionLocal() as session:
        session.add(
            Supplier(
                id=supplier_id,
                supplier_code=f"TST{str(supplier_id).replace('-', '')[:9]}",
                supplier_name=f"状态约束测试-{supplier_id}",
                main_brands="测试",
                advantage="测试",
            )
        )
        await session.flush()
        for from_status, to_status in [
            ("NORMAL", "STOPPED"),
            ("NORMAL", "BLACKLIST"),
            ("STOPPED", "NORMAL"),
            ("BLACKLIST", "NORMAL"),
        ]:
            session.add(
                SupplierCooperationRecord(
                    supplier_id=supplier_id,
                    from_status=from_status,
                    to_status=to_status,
                    reason="状态约束测试",
                    actor_id=uuid.uuid4(),
                )
            )
        await session.flush()
        for from_status, to_status in [
            ("STOPPED", "BLACKLIST"),
            ("BLACKLIST", "STOPPED"),
            ("NORMAL", "NORMAL"),
            ("STOPPED", "STOPPED"),
            ("BLACKLIST", "BLACKLIST"),
        ]:
            with pytest.raises(DBAPIError):
                async with session.begin_nested():
                    session.add(
                        SupplierCooperationRecord(
                            supplier_id=supplier_id,
                            from_status=from_status,
                            to_status=to_status,
                            reason="非法状态约束测试",
                            actor_id=uuid.uuid4(),
                        )
                    )
                    await session.flush()
        await session.execute(
            delete(SupplierCooperationRecord).where(
                SupplierCooperationRecord.supplier_id == supplier_id
            )
        )
        await session.execute(delete(Supplier).where(Supplier.id == supplier_id))
        await session.commit()
