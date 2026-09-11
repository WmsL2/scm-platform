import uuid
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.catalog.application.import_service import PRODUCT_IMPORT_HEADERS
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import (
    Product,
    ProductImportRow,
    ProductImportSupplierMatch,
    ProductImportTask,
)
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole

IMPORT_PERMISSIONS = ("product:import", "product:import:resolve")


async def _create_import_user() -> tuple[uuid.UUID, dict[str, str]]:
    user_id, role_id = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as session:
        permissions = list(
            (
                await session.scalars(
                    select(Permission).where(Permission.permission_code.in_(IMPORT_PERMISSIONS))
                )
            ).all()
        )
        assert len(permissions) == len(IMPORT_PERMISSIONS)
        session.add_all(
            [
                User(
                    id=user_id,
                    username=f"product-import-test-{user_id}",
                    password_hash=hash_password("secret"),
                ),
                Role(id=role_id, role_code=f"product-import-{role_id}", role_name="product import"),
                UserRole(user_id=user_id, role_id=role_id),
                *[
                    RolePermission(role_id=role_id, permission_id=permission.id)
                    for permission in permissions
                ],
            ]
        )
        await session.commit()
    return user_id, {"Authorization": f"Bearer {create_token(user_id, 1)}"}


async def _cleanup_import_user(user_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        role_ids = list(
            (
                await session.scalars(
                    select(UserRole.role_id).where(UserRole.user_id == user_id)
                )
            ).all()
        )
        await session.execute(delete(RolePermission).where(RolePermission.role_id.in_(role_ids)))
        await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await session.execute(delete(Role).where(Role.id.in_(role_ids)))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def _create_references() -> uuid.UUID:
    supplier_id = uuid.uuid4()
    async with SessionLocal() as session:
        session.add(
            Supplier(
                id=supplier_id,
                supplier_code=f"IMP{str(supplier_id)[:8]}",
                supplier_name="导入测试供应商",
                main_brands="测试品牌",
                advantage="测试优势",
                archive_status="ARCHIVED",
                cooperation_status="NORMAL",
            )
        )
        await session.commit()
    return supplier_id


def _workbook_bytes(supplier_name: str) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(PRODUCT_IMPORT_HEADERS)
    worksheet.append(
        [
            "2026-09-10", "测试品牌", "https://example.test/image.png", "型号", "SKU-1", "测试商品",
            "测试一级", "测试二级", "测试三级", "货号", "https://example.test/item", "100",
            "999", "201", "199.9", "155.55", "55.55", "0.1234", "0.1111", "0.2778", "采销员",
            supplier_name, "6900000000000", "规格", "卖点", "限售区域", "180", "https://example.test/ref",
            "官方旗舰店", "0.8888", "-0.1111", "备注",
        ]
    )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


async def _cleanup_import_data(
    supplier_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    async with SessionLocal() as session:
        task_ids = list(
            (
                await session.scalars(
                    select(ProductImportTask.id).where(ProductImportTask.created_by == user_id)
                )
            ).all()
        )
        await session.execute(delete(Product).where(Product.created_by == user_id))
        if task_ids:
            await session.execute(
                delete(ProductImportRow).where(
                    ProductImportRow.import_task_id.in_(task_ids)
                )
            )
            await session.execute(
                delete(ProductImportSupplierMatch).where(
                    ProductImportSupplierMatch.import_task_id.in_(task_ids)
                )
            )
            await session.execute(
                delete(ProductImportTask).where(ProductImportTask.id.in_(task_ids))
            )
        await session.execute(delete(Supplier).where(Supplier.id == supplier_id))
        await session.commit()


async def test_product_import_direct_values_do_not_require_category_or_recalculation() -> None:
    user_id, headers = await _create_import_user()
    supplier_id = await _create_references()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            unresolved = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "products.xlsx",
                        _workbook_bytes("未知供应商"),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert unresolved.status_code == 200
            assert unresolved.json()["data"]["status"] == "NEEDS_RESOLUTION"
            assert unresolved.json()["data"]["invalid_rows"] == 1

            preview = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "products.xlsx",
                        _workbook_bytes("导入测试供应商"),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert preview.status_code == 200
            data = preview.json()["data"]
            assert data["status"] == "READY_TO_CONFIRM"
            assert data["valid_rows"] == 1
            confirmed = await client.post(
                f"/api/v1/products/imports/{data['id']}/confirm", headers=headers
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["data"]["imported_count"] == 1

            duplicate_preview = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "duplicate-products.xlsx",
                        _workbook_bytes("导入测试供应商"),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert duplicate_preview.status_code == 200
            duplicate_data = duplicate_preview.json()["data"]
            assert duplicate_data["status"] == "VALIDATED"
            assert duplicate_data["invalid_rows"] == 1
            assert "来源供应商与SKU组合已存在" in duplicate_data["rows"][0]["error_message"]

        async with SessionLocal() as session:
            deleted_product = await session.scalar(
                select(Product).where(Product.created_by == user_id)
            )
            assert deleted_product is not None
            disabled_product_id = deleted_product.id
            deleted_product.product_name = "停用前商品名称"
            deleted_product.cost_price = Decimal("321.0000")
            deleted_product.status = ProductStatus.DISABLED
            deleted_product.disabled_by = user_id
            deleted_product.disabled_at = datetime.now()
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            disabled_preview = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "disabled-product.xlsx",
                        _workbook_bytes("导入测试供应商"),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert disabled_preview.status_code == 200
            disabled_data = disabled_preview.json()["data"]
            assert disabled_data["status"] == "VALIDATED"
            assert disabled_data["valid_rows"] == 0
            assert "商品已停用，请启用或永久删除后再导入" in (
                disabled_data["rows"][0]["error_message"]
            )
            blocked_confirm = await client.post(
                f"/api/v1/products/imports/{disabled_data['id']}/confirm", headers=headers
            )
            assert blocked_confirm.status_code == 409
            assert blocked_confirm.json()["code"] == "PRODUCT_IMPORT_NOT_READY_TO_CONFIRM"

        async with SessionLocal() as session:
            product = await session.get(Product, disabled_product_id)
            assert product is not None
            assert product.status == ProductStatus.DISABLED
            assert product.product_name == "停用前商品名称"
            assert product.cost_price == Decimal("321.0000")
            assert product.source_supplier_id == supplier_id
            assert product.category_id is None
            assert product.category_level3_name == "测试三级"
            assert str(product.market_price) == "999.0000"
            assert str(product.agreement_price) == "199.9000"
            assert str(product.jd_margin) == "0.1234"
    finally:
        await _cleanup_import_data(supplier_id, user_id)
        await _cleanup_import_user(user_id)
