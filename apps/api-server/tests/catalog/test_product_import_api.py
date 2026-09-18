import uuid
from datetime import datetime
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from openpyxl.styles import PatternFill
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.catalog.api.router import (
    PRODUCT_IMPORT_UPLOAD_CHUNK_BYTES,
    _stage_product_import_upload,
)
from app.modules.catalog.application.import_service import PRODUCT_IMPORT_HEADERS
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import (
    Category,
    Product,
    ProductImportRow,
    ProductImportSupplierMatch,
    ProductImportTask,
)
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole

IMPORT_PERMISSIONS = ("product:import", "product:import:resolve")


async def test_product_import_upload_is_staged_in_chunks() -> None:
    class ChunkRecordingFile:
        def __init__(self, content: bytes) -> None:
            self.content = content
            self.offset = 0
            self.read_sizes: list[int] = []

        def read(self, size: int = -1) -> bytes:
            self.read_sizes.append(size)
            if self.offset >= len(self.content):
                return b""
            chunk = self.content[self.offset : self.offset + size]
            self.offset += len(chunk)
            return chunk

        def close(self) -> None:
            return None

    content = b"x" * (PRODUCT_IMPORT_UPLOAD_CHUNK_BYTES * 2 + 1)
    source = ChunkRecordingFile(content)
    file = UploadFile(file=source, filename="large-product-import.xlsx")
    staged_path, file_size = await _stage_product_import_upload(file)
    try:
        assert file_size == len(content)
        assert staged_path.read_bytes() == content
        assert source.read_sizes == [PRODUCT_IMPORT_UPLOAD_CHUNK_BYTES] * 4
    finally:
        staged_path.unlink(missing_ok=True)
        await file.close()


class _RecordingStorage:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def save(self, name: str, content: bytes) -> str:
        del content
        return name

    async def read(self, key: str) -> bytes:
        del key
        raise FileNotFoundError

    async def delete(self, key: str) -> None:
        self.deleted.append(key)


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


async def _create_category(
    path: tuple[str, str, str], *, is_active: bool = True
) -> uuid.UUID:
    category_id = uuid.uuid4()
    async with SessionLocal() as session:
        session.add(
            Category(
                id=category_id,
                source_type="MALL_LEVEL3",
                level1_external_id=f"L1-{category_id}",
                level1_name=path[0],
                level2_external_id=f"L2-{category_id}",
                level2_name=path[1],
                level3_external_id=f"L3-{category_id}",
                level3_name=path[2],
                deduction_rate=Decimal("0.0800"),
                is_active=is_active,
            )
        )
        await session.commit()
    return category_id


async def _create_references() -> tuple[uuid.UUID, uuid.UUID]:
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
    category_id = await _create_category(("测试一级", "测试二级", "测试三级"))
    return supplier_id, category_id


def _workbook_bytes(
    *supplier_names: str,
    image_value: str = "https://example.test/image.png",
    category_path: tuple[str, str, str] = ("测试一级", "测试二级", "测试三级"),
    product_name: str = "测试商品",
    cost_price: str = "100",
    sku_override: str | None = None,
    styled_blank_columns_after_template: bool = False,
) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.append(PRODUCT_IMPORT_HEADERS)
    for index, supplier_name in enumerate(supplier_names, start=1):
        values = {
            "所属公司": "测试公司", "上架日期": "2026-09-10", "品牌": "测试品牌",
            "图片": image_value, "型号": "型号", "sku": sku_override or f"SKU-{index}",
            "商品名称": product_name, "一级类目": category_path[0], "二级类目": category_path[1],
            "三级类目": category_path[2], "货号": "货号", "链接": "https://example.test/item",
            "成本价": cost_price, "市场价": "999", "京东价": "201", "协议价": "199.9",
            "协议价采购价": "155.55", "利润": "55.55", "京东价毛利（30-50）": "12.34%",
            "扣点复核": "11.11%", "毛利率": "27.78%", "采销员": "采销员",
            "供应商": supplier_name, "69码": "6900000000000", "3c编码": "3C-TEST",
            "产品规格": "规格", "卖点": "卖点", "包装清单": "包装", "质保期": "一年",
            "限售区域": "限售区域", "京东自营前台价": "180", "自营旗舰店/官方旗舰店": "官方旗舰店",
            "参考链接": "https://example.test/ref", "销量": "10", "好评率": "95%",
            "折扣率": "88.88%", "价格虚高比例": "-11.11%", "税收编码": "TAX-1",
            "开票名称": "测试商品", "税收分类": "测试分类", "发货快递": "京东物流",
            "售后政策": "七天无理由", "备注": "备注",
        }
        worksheet.append([values[header] for header in PRODUCT_IMPORT_HEADERS])
    if styled_blank_columns_after_template:
        worksheet.cell(row=1, column=16_384).fill = PatternFill(
            fill_type="solid", fgColor="FFFFFF"
        )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


async def test_product_import_accepts_blank_styled_columns_after_approved_headers() -> None:
    user_id, headers = await _create_import_user()
    supplier_id, category_id = await _create_references()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            preview = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "styled-blank-columns.xlsx",
                        _workbook_bytes(
                            "导入测试供应商", styled_blank_columns_after_template=True
                        ),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert preview.status_code == 200
            assert preview.json()["data"]["total_rows"] == 1
    finally:
        await _cleanup_import_data(supplier_id, user_id, (category_id,))
        await _cleanup_import_user(user_id)


async def _cleanup_import_data(
    supplier_id: uuid.UUID, user_id: uuid.UUID, category_ids: tuple[uuid.UUID, ...]
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
        await session.execute(delete(Category).where(Category.id.in_(category_ids)))
        await session.commit()


async def test_product_import_binds_unique_active_mall_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = _RecordingStorage()
    monkeypatch.setattr(
        "app.modules.catalog.application.import_service.get_object_storage", lambda: storage
    )
    user_id, headers = await _create_import_user()
    supplier_id, category_id = await _create_references()
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
            assert data["rows"][0]["category_id"] == str(category_id)
            confirmed = await client.post(
                f"/api/v1/products/imports/{data['id']}/confirm", headers=headers
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["data"]["imported_count"] == 1

            async with SessionLocal() as session:
                imported = await session.scalar(
                    select(Product).where(Product.created_by == user_id)
                )
                assert imported is not None
                imported.image_reference = "local-media/product-images/old.png"
                await session.commit()

            duplicate_preview = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "duplicate-products.xlsx",
                        _workbook_bytes(
                            "导入测试供应商", product_name="更新后商品", cost_price="222"
                        ),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert duplicate_preview.status_code == 200
            duplicate_data = duplicate_preview.json()["data"]
            assert duplicate_data["status"] == "READY_TO_CONFIRM"
            assert duplicate_data["valid_rows"] == 0
            assert duplicate_data["update_rows"] == 1
            assert duplicate_data["invalid_rows"] == 0
            assert duplicate_data["rows"][0]["write_action"] == "UPDATE"
            assert {"商品名称", "成本价"}.issubset(duplicate_data["rows"][0]["changed_fields"])
            updated = await client.post(
                f"/api/v1/products/imports/{duplicate_data['id']}/confirm", headers=headers
            )
            assert updated.status_code == 200
            assert updated.json()["data"]["created_count"] == 0
            assert updated.json()["data"]["updated_count"] == 1
            assert "product-images/old.png" in storage.deleted
            updated_preview = await client.get(
                f"/api/v1/products/imports/{duplicate_data['id']}", headers=headers
            )
            assert updated_preview.status_code == 200
            assert updated_preview.json()["data"]["rows"][0]["is_imported"] is True
            assert updated_preview.json()["data"]["rows"][0]["write_action"] == "UPDATE"

            duplicate_rows_preview = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "duplicate-rows-products.xlsx",
                        _workbook_bytes(
                            "导入测试供应商",
                            "导入测试供应商",
                            sku_override="SKU-1",
                        ),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert duplicate_rows_preview.status_code == 200
            duplicate_rows_data = duplicate_rows_preview.json()["data"]
            assert duplicate_rows_data["update_rows"] == 1
            assert duplicate_rows_data["invalid_rows"] == 1
            assert "与Excel第2行的来源供应商与SKU重复" in (
                duplicate_rows_data["rows"][1]["error_message"]
            )

        async with SessionLocal() as session:
            deleted_product = await session.scalar(
                select(Product).where(Product.created_by == user_id)
            )
            assert deleted_product is not None
            disabled_product_id = deleted_product.id
            assert deleted_product.product_name == "更新后商品"
            assert deleted_product.cost_price == Decimal("222.0000")
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
            assert blocked_confirm.json()["code"] == "PRODUCT_IMPORT_NO_VALID_ROWS"

        async with SessionLocal() as session:
            product = await session.get(Product, disabled_product_id)
            assert product is not None
            assert product.status == ProductStatus.DISABLED
            assert product.product_name == "停用前商品名称"
            assert product.cost_price == Decimal("321.0000")
            assert product.source_supplier_id == supplier_id
            assert product.category_id == category_id
            assert product.category_level3_name == "测试三级"
            assert str(product.market_price) == "999.0000"
            assert str(product.agreement_price) == "199.9000"
            assert str(product.jd_margin) == "0.1234"
            assert product.company_name == "测试公司"
            assert product.sales_volume == 10
            assert product.positive_rating == Decimal("0.9500")
    finally:
        await _cleanup_import_data(supplier_id, user_id, (category_id,))
        await _cleanup_import_user(user_id)


async def test_product_import_rejects_missing_ambiguous_and_inactive_categories() -> None:
    user_id, headers = await _create_import_user()
    supplier_id, default_category_id = await _create_references()
    ambiguous_path = ("重复一级", "重复二级", "重复三级")
    inactive_path = ("停用一级", "停用二级", "停用三级")
    ambiguous_category_ids = (
        await _create_category(ambiguous_path),
        await _create_category(ambiguous_path),
    )
    inactive_category_id = await _create_category(inactive_path, is_active=False)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            missing = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "missing-category.xlsx",
                        _workbook_bytes(
                            "导入测试供应商",
                            category_path=("未知一级", "未知二级", "未知三级"),
                        ),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert missing.status_code == 200
            missing_row = missing.json()["data"]["rows"][0]
            assert missing_row["is_valid"] is False
            assert missing_row["category_id"] is None
            assert "未找到有效商城三级类目" in missing_row["error_message"]

            ambiguous = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "ambiguous-category.xlsx",
                        _workbook_bytes("导入测试供应商", category_path=ambiguous_path),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert ambiguous.status_code == 200
            ambiguous_row = ambiguous.json()["data"]["rows"][0]
            assert ambiguous_row["is_valid"] is False
            assert ambiguous_row["category_id"] is None
            assert "商城三级类目匹配不唯一" in ambiguous_row["error_message"]

            inactive = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "inactive-category.xlsx",
                        _workbook_bytes("导入测试供应商", category_path=inactive_path),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert inactive.status_code == 200
            inactive_row = inactive.json()["data"]["rows"][0]
            assert inactive_row["is_valid"] is False
            assert inactive_row["category_id"] is None
            assert "匹配的商城三级类目已停用" in inactive_row["error_message"]
    finally:
        await _cleanup_import_data(
            supplier_id,
            user_id,
            (default_category_id, *ambiguous_category_ids, inactive_category_id),
        )
        await _cleanup_import_user(user_id)


async def test_product_import_confirms_valid_rows_and_retains_failed_rows() -> None:
    user_id, headers = await _create_import_user()
    supplier_id, category_id = await _create_references()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            preview = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "mixed-products.xlsx",
                        _workbook_bytes("导入测试供应商", "未知供应商"),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert preview.status_code == 200
            data = preview.json()["data"]
            assert data["status"] == "NEEDS_RESOLUTION"
            assert data["valid_rows"] == 1
            assert data["invalid_rows"] == 1
            assert data["imported_rows"] == 0

            partial = await client.post(
                f"/api/v1/products/imports/{data['id']}/confirm", headers=headers
            )
            assert partial.status_code == 200
            partial_data = partial.json()["data"]
            assert partial_data == {
                "id": data["id"],
                "status": "PARTIALLY_CONFIRMED",
                "imported_count": 1,
                "created_count": 1,
                "updated_count": 0,
                "imported_rows": 1,
                "valid_rows": 0,
                "update_rows": 0,
                "invalid_rows": 1,
            }

            refreshed = await client.get(f"/api/v1/products/imports/{data['id']}", headers=headers)
            assert refreshed.status_code == 200
            refreshed_data = refreshed.json()["data"]
            assert refreshed_data["rows"][0]["is_imported"] is True
            assert refreshed_data["rows"][1]["is_imported"] is False

            unknown_match = next(
                match
                for match in refreshed_data["supplier_matches"]
                if match["supplier_name_normalized"] == "未知供应商"
            )
            resolved = await client.post(
                f"/api/v1/products/imports/{data['id']}/supplier-matches/{unknown_match['id']}/resolve",
                headers=headers,
                json={"supplier_id": str(supplier_id)},
            )
            assert resolved.status_code == 200
            assert resolved.json()["data"]["status"] == "PARTIALLY_CONFIRMED"
            assert resolved.json()["data"]["valid_rows"] == 1

            confirmed = await client.post(
                f"/api/v1/products/imports/{data['id']}/confirm", headers=headers
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["data"]["status"] == "CONFIRMED"
            assert confirmed.json()["data"]["imported_rows"] == 2

            template = await client.get("/api/v1/products/imports/template", headers=headers)
            assert template.status_code == 200
            assert template.headers["content-type"].startswith(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            assert template.content.startswith(b"PK")

        async with SessionLocal() as session:
            products = list(
                (await session.scalars(select(Product).where(Product.created_by == user_id))).all()
            )
            assert sorted(product.sku for product in products) == ["SKU-1", "SKU-2"]
    finally:
        await _cleanup_import_data(supplier_id, user_id, (category_id,))
        await _cleanup_import_user(user_id)


async def test_product_import_defers_formula_image_storage_until_confirm() -> None:
    user_id, headers = await _create_import_user()
    supplier_id, category_id = await _create_references()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            preview = await client.post(
                "/api/v1/products/imports/preview",
                headers=headers,
                files={
                    "file": (
                        "formula-image-products.xlsx",
                        _workbook_bytes(
                            "导入测试供应商",
                            image_value='=_xlfn.DISPIMG("ID_PRODUCT",1)',
                        ),
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )
            assert preview.status_code == 200
            data = preview.json()["data"]
            assert data["rows"][0]["image_saved"] is False
            assert data["rows"][0]["image_pending_save"] is True

            async with SessionLocal() as session:
                task = await session.get(ProductImportTask, data["id"])
                row = await session.scalar(
                    select(ProductImportRow).where(ProductImportRow.import_task_id == data["id"])
                )
                assert task is not None and task.source_file_storage_key is not None
                assert row is not None and row.image_storage_key is None

            confirmed = await client.post(
                f"/api/v1/products/imports/{data['id']}/confirm", headers=headers
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["data"]["status"] == "CONFIRMED"

            async with SessionLocal() as session:
                task = await session.get(ProductImportTask, data["id"])
                assert task is not None and task.source_file_storage_key is None
    finally:
        await _cleanup_import_data(supplier_id, user_id, (category_id,))
        await _cleanup_import_user(user_id)
