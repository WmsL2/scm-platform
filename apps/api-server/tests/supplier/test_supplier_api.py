import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.supplier.infrastructure.models import (
    Supplier,
    SupplierContact,
    SupplierCooperationRecord,
    SupplierQualification,
)
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole

SUPPLIER_PERMISSIONS = (
    "supplier:list",
    "supplier:detail",
    "supplier:create",
    "supplier:update",
    "supplier:submit",
    "supplier:archive",
    "supplier:stop",
    "supplier:blacklist",
)


async def create_user_with_permissions(
    permission_codes: tuple[str, ...]
) -> tuple[uuid.UUID, dict[str, str]]:
    user_id, role_id = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as session:
        permissions = list(
            (
                await session.scalars(
                    select(Permission).where(Permission.permission_code.in_(permission_codes))
                )
            ).all()
        )
        assert len(permissions) == len(permission_codes)
        session.add_all(
            [
                User(
                    id=user_id,
                    username=f"supplier-test-{user_id}",
                    password_hash=hash_password("secret"),
                ),
                Role(id=role_id, role_code=f"supplier-test-{role_id}", role_name="supplier test"),
                UserRole(user_id=user_id, role_id=role_id),
                *[
                    RolePermission(role_id=role_id, permission_id=permission.id)
                    for permission in permissions
                ],
            ]
        )
        await session.commit()
    return user_id, {"Authorization": f"Bearer {create_token(user_id, 1)}"}


async def cleanup_user(user_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        role_ids = list(
            (
                await session.scalars(select(UserRole.role_id).where(UserRole.user_id == user_id))
            ).all()
        )
        await session.execute(delete(RolePermission).where(RolePermission.role_id.in_(role_ids)))
        await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await session.execute(delete(Role).where(Role.id.in_(role_ids)))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def cleanup_suppliers(supplier_ids: list[str]) -> None:
    if not supplier_ids:
        return
    async with SessionLocal() as session:
        await session.execute(
            delete(SupplierContact).where(SupplierContact.supplier_id.in_(supplier_ids))
        )
        await session.execute(
            delete(SupplierQualification).where(SupplierQualification.supplier_id.in_(supplier_ids))
        )
        await session.execute(
            delete(SupplierCooperationRecord).where(
                SupplierCooperationRecord.supplier_id.in_(supplier_ids)
            )
        )
        await session.execute(delete(Supplier).where(Supplier.id.in_(supplier_ids)))
        await session.commit()


async def test_supplier_api_enforces_permissions_and_lifecycle() -> None:
    user_id, headers = await create_user_with_permissions(SUPPLIER_PERMISSIONS)
    supplier_ids: list[str] = []
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            unauthorized = await client.get("/api/v1/suppliers")
            assert unauthorized.status_code == 401

            create = await client.post(
                "/api/v1/suppliers",
                headers=headers,
                json={
                    "supplier_name": "众诚测试供应商",
                    "main_brands": "品牌 A、品牌 B",
                    "advantage": "本地测试数据",
                    "contacts": [{"contact_name": "李四", "contact_phone": "13800000000"}],
                },
            )
            assert create.status_code == 201
            supplier = create.json()["data"]
            supplier_id = supplier["id"]
            supplier_ids.append(supplier_id)
            assert supplier["supplier_code"].startswith("SUP")
            assert supplier["archive_status"] == "DRAFT"
            assert supplier["cooperation_status"] == "NORMAL"
            assert supplier["contacts"][0]["contact_name"] == "李四"

            supplied_code = await client.post(
                "/api/v1/suppliers",
                headers=headers,
                json={
                    "supplier_code": "SUP00000001",
                    "supplier_name": "不能指定编码",
                    "main_brands": "品牌",
                    "advantage": "优势",
                },
            )
            assert supplied_code.status_code == 422

            update = await client.patch(
                f"/api/v1/suppliers/{supplier_id}",
                headers=headers,
                json={"supplier_name": "更新后的供应商", "contacts": []},
            )
            assert update.status_code == 200
            assert update.json()["data"]["supplier_name"] == "更新后的供应商"
            assert update.json()["data"]["contacts"] == []

            bypass_state = await client.patch(
                f"/api/v1/suppliers/{supplier_id}",
                headers=headers,
                json={"archive_status": "ARCHIVED"},
            )
            assert bypass_state.status_code == 422

            archive_before_submit = await client.post(
                f"/api/v1/suppliers/{supplier_id}/commands/archive", headers=headers
            )
            assert archive_before_submit.status_code == 409

            submit = await client.post(
                f"/api/v1/suppliers/{supplier_id}/commands/submit", headers=headers
            )
            assert submit.status_code == 200
            assert submit.json()["data"]["archive_status"] == "PENDING"

            archive = await client.post(
                f"/api/v1/suppliers/{supplier_id}/commands/archive", headers=headers
            )
            assert archive.status_code == 200
            assert archive.json()["data"]["archive_status"] == "ARCHIVED"
            assert archive.json()["data"]["archived_by"] == str(user_id)
            assert archive.json()["data"]["archived_at"] is not None

            stop = await client.post(
                f"/api/v1/suppliers/{supplier_id}/commands/stop",
                headers=headers,
                json={"reason": "合作终止"},
            )
            assert stop.status_code == 200
            assert stop.json()["data"]["cooperation_status"] == "STOPPED"

            blacklist_after_stop = await client.post(
                f"/api/v1/suppliers/{supplier_id}/commands/blacklist",
                headers=headers,
                json={"reason": "不能跳过状态机"},
            )
            assert blacklist_after_stop.status_code == 409

            listing = await client.get("/api/v1/suppliers", headers=headers)
            assert listing.status_code == 200
            assert any(item["id"] == supplier_id for item in listing.json()["data"]["items"])

        async with SessionLocal() as session:
            record = await session.scalar(
                select(SupplierCooperationRecord).where(
                    SupplierCooperationRecord.supplier_id == supplier_id
                )
            )
            assert record is not None
            assert record.from_status == "NORMAL"
            assert record.to_status == "STOPPED"
            assert record.reason == "合作终止"
            assert record.actor_id == user_id
    finally:
        await cleanup_suppliers(supplier_ids)
        await cleanup_user(user_id)


async def test_supplier_api_returns_403_for_authenticated_user_without_supplier_permissions(
) -> None:
    user_id, headers = await create_user_with_permissions(())
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/suppliers", headers=headers)
            assert response.status_code == 403
            assert response.json()["code"] == "AUTH_FORBIDDEN"
    finally:
        await cleanup_user(user_id)
