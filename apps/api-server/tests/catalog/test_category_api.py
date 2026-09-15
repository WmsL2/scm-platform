# ruff: noqa: E501, E701, E702
import uuid
from io import BytesIO

from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import delete, event, select

from app.common.contracts import AppError
from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.catalog.application.category_service import CategoryService
from app.modules.catalog.infrastructure.models import Category, Product
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole


async def category_user() -> tuple[uuid.UUID, dict[str, str]]:
    user_id, role_id = uuid.uuid4(), uuid.uuid4()
    codes = ("product:list", "product:update", "product:import")
    async with SessionLocal() as session:
        permissions = list((await session.scalars(select(Permission).where(Permission.permission_code.in_(codes)))).all())
        session.add_all([User(id=user_id, username=f"category-{user_id}", password_hash=hash_password("secret")), Role(id=role_id, role_code=f"category-{role_id}", role_name="category"), UserRole(user_id=user_id, role_id=role_id), *[RolePermission(role_id=role_id, permission_id=item.id) for item in permissions]])
        await session.commit()
    return user_id, {"Authorization": f"Bearer {create_token(user_id, 1)}"}


async def cleanup(user_id: uuid.UUID, category_ids: list[uuid.UUID]) -> None:
    async with SessionLocal() as session:
        await session.execute(delete(Product).where(Product.category_id.in_(category_ids)))
        await session.execute(delete(Category).where(Category.id.in_(category_ids)))
        role_ids = list((await session.scalars(select(UserRole.role_id).where(UserRole.user_id == user_id))).all())
        await session.execute(delete(RolePermission).where(RolePermission.role_id.in_(role_ids)))
        await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await session.execute(delete(Role).where(Role.id.in_(role_ids)))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


def payload(external_id: str, name: str = "三级") -> dict[str, object]:
    return {"source_type": "MALL_LEVEL3", "level1_external_id": "1", "level1_name": "一级", "level2_external_id": "2", "level2_name": "二级", "level3_external_id": external_id, "level3_name": name, "deduction_rate": "0.0800", "is_active": True, "shelf_flag": None, "business_unit": None}


def workbook(rows: list[dict[str, object]]) -> bytes:
    headers = tuple(payload("x").keys()); book = Workbook(); sheet = book.active; assert sheet is not None
    sheet.append(headers)
    for row in rows: sheet.append([row[key] for key in headers])
    output = BytesIO(); book.save(output); return output.getvalue()


async def test_category_crud_selection_and_external_id_conflicts() -> None:
    user_id, headers = await category_user(); ids: list[uuid.UUID] = []
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post("/api/v1/categories", headers=headers, json=payload("300"))
            assert created.status_code == 200; category_id = uuid.UUID(created.json()["data"]["id"]); ids.append(category_id)
            assert (await client.get("/api/v1/categories/selection", headers=headers)).status_code == 200
            assert (await client.get(f"/api/v1/categories/{category_id}", headers=headers)).status_code == 200
            duplicate = await client.post("/api/v1/categories", headers=headers, json=payload("300", "另一三级"))
            assert duplicate.status_code == 409 and duplicate.json()["code"] == "CATEGORY_EXTERNAL_ID_EXISTS"
            edited = await client.put(f"/api/v1/categories/{category_id}", headers=headers, json=payload("301", "已编辑"))
            assert edited.status_code == 200 and edited.json()["data"]["level3_name"] == "已编辑"
            assert (await client.delete(f"/api/v1/categories/{category_id}", headers=headers)).status_code == 200
            assert (await client.get(f"/api/v1/categories/{category_id}", headers=headers)).status_code == 404
    finally:
        await cleanup(user_id, ids)


async def test_category_import_valid_skip_and_external_id_conflict() -> None:
    user_id, headers = await category_user(); ids: list[uuid.UUID] = []
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            content = workbook([payload("401", "甲"), payload("402", "乙")])
            first = await client.post("/api/v1/categories/imports", headers=headers, files={"file": ("categories.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            assert first.status_code == 200 and first.json()["data"]["success"] == 2
            async with SessionLocal() as session:
                ids.extend([item.id for item in (await session.scalars(select(Category).where(Category.level3_external_id.in_(("401", "402"))))).all()])
            skipped = await client.post("/api/v1/categories/imports", headers=headers, files={"file": ("categories.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            assert skipped.json()["data"]["skipped"] == 2
            conflict = await client.post("/api/v1/categories/imports", headers=headers, files={"file": ("categories.xlsx", workbook([payload("401", "不同路径")]), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            data = conflict.json()["data"]; assert data["failed"] == 1; assert data["errors"][0]["field"] == "level3_external_id"
    finally:
        await cleanup(user_id, ids)


async def test_category_import_rejects_structure_duplicates_and_field_values() -> None:
    user_id, headers = await category_user()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            empty = await client.post("/api/v1/categories/imports", headers=headers, files={"file": ("empty.xlsx", workbook([]), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            assert empty.status_code == 200 and empty.json()["data"]["total"] == 0
            bad_headers = await client.post("/api/v1/categories/imports", headers=headers, files={"file": ("bad.xlsx", b"not an xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            assert bad_headers.status_code == 422
            invalid = payload("501"); invalid["level1_name"] = ""; invalid["is_active"] = "maybe"
            rejected = await client.post("/api/v1/categories/imports", headers=headers, files={"file": ("invalid.xlsx", workbook([invalid]), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            error = rejected.json()["data"]["errors"][0]
            assert error["row_number"] == 2 and error["reason"]
            repeated = await client.post("/api/v1/categories/imports", headers=headers, files={"file": ("repeat.xlsx", workbook([payload("502"), payload("502", "不同")]), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
            duplicate_error = repeated.json()["data"]["errors"][0]
            assert duplicate_error["row_number"] == 3
            assert duplicate_error["field"] == "level3_external_id"
            assert duplicate_error["value"] == "502"
    finally:
        await cleanup(user_id, [])


async def test_category_import_write_failure_rolls_back_all_rows() -> None:
    user_id, _ = await category_user(); inserted_ids: list[uuid.UUID] = []
    try:
        content = workbook([payload("601", "第一条"), payload("602", "第二条")])
        async with SessionLocal() as session:
            service = CategoryService(session)
            injected = False
            def inject_conflict(sync_session: object, *_: object) -> None:
                nonlocal injected
                if not injected:
                    injected = True
                    sync_session.add(Category(**payload("602", "冲突"), created_by=user_id, updated_by=user_id))  # type: ignore[attr-defined]
            event.listen(session.sync_session, "before_flush", inject_conflict)
            try:
                try:
                    await service.import_xlsx("rollback.xlsx", content, user_id)
                except AppError as exc:
                    assert exc.code == "CATEGORY_IMPORT_CONFLICT"
            finally:
                event.remove(session.sync_session, "before_flush", inject_conflict)
        async with SessionLocal() as check:
            remaining = list((await check.scalars(select(Category.id).where(Category.level3_external_id.in_(("601", "602"))))).all())
            assert remaining == []
    finally:
        await cleanup(user_id, inserted_ids)
