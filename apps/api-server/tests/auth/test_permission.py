import uuid
from typing import Annotated

from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.database import SessionLocal
from app.main import app
from app.modules.auth.dependencies import require_permission
from app.modules.auth.security import create_token, hash_password
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole


@app.get("/__test/permission")
async def protected(
    _: Annotated[object, Depends(require_permission("test:resource:read"))],
) -> dict[str, bool]:
    return {"ok": True}


async def test_dynamic_permission_revoke_and_missing_token() -> None:
    user, role, permission = (uuid.uuid4() for _ in range(3))
    async with SessionLocal() as session:
        session.add_all(
            [
                User(id=user, username=f"perm-{user}", password_hash=hash_password("x")),
                Role(id=role, role_code=f"r-{role}", role_name="r"),
                Permission(
                    id=permission,
                    permission_code="test:resource:read",
                    permission_name="p",
                    permission_type="API",
                ),
                UserRole(user_id=user, role_id=role),
                RolePermission(role_id=role, permission_id=permission),
            ]
        )
        await session.commit()
    headers = {"Authorization": f"Bearer {create_token(user, 1)}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/__test/permission", headers=headers)).status_code == 200
            async with SessionLocal() as session:
                await session.execute(delete(RolePermission).where(RolePermission.role_id == role))
                await session.commit()
            assert (await client.get("/__test/permission", headers=headers)).status_code == 403
            assert (await client.get("/__test/permission")).status_code == 401
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(UserRole).where(UserRole.user_id == user))
            await session.execute(delete(Permission).where(Permission.id == permission))
            await session.execute(delete(Role).where(Role.id == role))
            await session.execute(delete(User).where(User.id == user))
            await session.commit()


async def test_dynamic_permission_grant() -> None:
    user, role, permission = (uuid.uuid4() for _ in range(3))
    async with SessionLocal() as session:
        session.add_all(
            [
                User(id=user, username=f"grant-{user}", password_hash=hash_password("x")),
                Role(id=role, role_code=f"g-{role}", role_name="g"),
                Permission(
                    id=permission,
                    permission_code="test:resource:read",
                    permission_name="p",
                    permission_type="API",
                ),
                UserRole(user_id=user, role_id=role),
            ]
        )
        await session.commit()
    headers = {"Authorization": f"Bearer {create_token(user, 1)}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/__test/permission", headers=headers)).status_code == 403
            async with SessionLocal() as session:
                session.add(RolePermission(role_id=role, permission_id=permission))
                await session.commit()
            assert (await client.get("/__test/permission", headers=headers)).status_code == 200
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(RolePermission).where(RolePermission.role_id == role))
            await session.execute(delete(UserRole).where(UserRole.user_id == user))
            await session.execute(delete(Permission).where(Permission.id == permission))
            await session.execute(delete(Role).where(Role.id == role))
            await session.execute(delete(User).where(User.id == user))
            await session.commit()


async def test_deleted_role_immediately_loses_permissions() -> None:
    user, role, permission = (uuid.uuid4() for _ in range(3))
    async with SessionLocal() as session:
        session.add_all(
            [
                User(id=user, username=f"deleted-role-{user}", password_hash=hash_password("x")),
                Role(id=role, role_code=f"deleted-role-{role}", role_name="deleted role"),
                Permission(
                    id=permission,
                    permission_code="test:resource:read",
                    permission_name="p",
                    permission_type="API",
                ),
                UserRole(user_id=user, role_id=role),
                RolePermission(role_id=role, permission_id=permission),
            ]
        )
        await session.commit()
    headers = {"Authorization": f"Bearer {create_token(user, 1)}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/__test/permission", headers=headers)).status_code == 200
            async with SessionLocal() as session:
                stored_role = await session.get(Role, role)
                assert stored_role is not None
                stored_role.is_deleted = True
                await session.commit()
            assert (await client.get("/__test/permission", headers=headers)).status_code == 403
            me = await client.get("/api/v1/auth/me", headers=headers)
            assert me.status_code == 200
            assert me.json()["data"]["roles"] == []
            assert me.json()["data"]["permissions"] == []
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(RolePermission).where(RolePermission.role_id == role))
            await session.execute(delete(UserRole).where(UserRole.user_id == user))
            await session.execute(delete(Permission).where(Permission.id == permission))
            await session.execute(delete(Role).where(Role.id == role))
            await session.execute(delete(User).where(User.id == user))
            await session.commit()
