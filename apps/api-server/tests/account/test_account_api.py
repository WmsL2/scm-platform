# ruff: noqa: E501
import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.common.contracts import AppError
from app.core.database import SessionLocal
from app.main import app
from app.modules.account.service import AccountService
from app.modules.auth.security import create_token, hash_password
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole


async def _admin() -> tuple[uuid.UUID, uuid.UUID]:
    user_id, role_id = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as session:
        permission_ids = list(
            (await session.scalars(select(Permission.id).where(Permission.permission_code.like("system:%")))).all()
        )
        session.add_all([
            User(id=user_id, username=f"account-admin-{user_id}", password_hash=hash_password("secret")),
            Role(id=role_id, role_code=f"account-role-{role_id}", role_name="account test role"),
            UserRole(user_id=user_id, role_id=role_id),
            *[RolePermission(role_id=role_id, permission_id=item) for item in permission_ids],
        ])
        await session.commit()
    return user_id, role_id


async def _cleanup(user_ids: list[uuid.UUID], role_ids: list[uuid.UUID]) -> None:
    async with SessionLocal() as session:
        if role_ids:
            await session.execute(delete(RolePermission).where(RolePermission.role_id.in_(role_ids)))
            await session.execute(delete(UserRole).where(UserRole.role_id.in_(role_ids)))
            await session.execute(delete(Role).where(Role.id.in_(role_ids)))
        if user_ids:
            await session.execute(delete(UserRole).where(UserRole.user_id.in_(user_ids)))
            await session.execute(delete(User).where(User.id.in_(user_ids)))
        await session.commit()


async def test_concurrent_registration_duplicate_username_is_conflict() -> None:
    username = f"concurrent-registration-{uuid.uuid4()}"

    async def register_once() -> str:
        async with SessionLocal() as session:
            try:
                await AccountService(session).register(username, "password")
            except AppError as exc:
                return exc.code
            return "CREATED"

    try:
        results = await asyncio.gather(register_once(), register_once())
        assert sorted(results) == ["ACCOUNT_USERNAME_EXISTS", "CREATED"]
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(User).where(User.username == username))
            await session.commit()


async def test_concurrent_registration_review_allows_only_one_transition() -> None:
    admin_id, admin_role = await _admin()
    username = f"concurrent-review-{uuid.uuid4()}"
    created_id: uuid.UUID | None = None
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            registered = await client.post(
                "/api/v1/auth/register", json={"username": username, "password": "password"}
            )
            created_id = uuid.UUID(registered.json()["data"]["id"])
            path = f"/api/v1/admin/registration-requests/{created_id}/commands/approve"
            first, second = await asyncio.gather(
                client.post(path, headers=headers, json={}), client.post(path, headers=headers, json={})
            )
            assert sorted([first.status_code, second.status_code]) == [200, 409]
    finally:
        await _cleanup([admin_id, *([created_id] if created_id else [])], [admin_role])


async def test_registration_review_and_password_change() -> None:
    admin_id, admin_role = await _admin()
    username = f"registration-{uuid.uuid4()}"
    created_id: uuid.UUID | None = None
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            registered = await client.post("/api/v1/auth/register", json={"username": username, "password": "old"})
            assert registered.status_code == 200
            body = registered.json()["data"]
            created_id = uuid.UUID(body["id"])
            assert body["user_status"] == "PENDING"
            duplicate = await client.post(
                "/api/v1/auth/register", json={"username": f"  {username}  ", "password": "other"}
            )
            assert duplicate.status_code == 409
            assert duplicate.json()["code"] == "ACCOUNT_USERNAME_EXISTS"
            assert (await client.post("/api/v1/auth/login", json={"username": username, "password": "old"})).status_code == 401
            assert (await client.post(f"/api/v1/admin/registration-requests/{created_id}/commands/approve", headers=headers, json={"review_note": "ok"})).status_code == 200
            repeated_review = await client.post(f"/api/v1/admin/registration-requests/{created_id}/commands/reject", headers=headers, json={})
            assert repeated_review.status_code == 409
            login = await client.post("/api/v1/auth/login", json={"username": username, "password": "old"})
            token = login.json()["data"]["access_token"]
            changed = await client.post("/api/v1/auth/change-password", headers={"Authorization": f"Bearer {token}"}, json={"current_password": "old", "new_password": "new"})
            assert changed.status_code == 200
            assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401
            assert (await client.post("/api/v1/auth/login", json={"username": username, "password": "old"})).status_code == 401
            assert (await client.post("/api/v1/auth/login", json={"username": username, "password": "new"})).status_code == 200
    finally:
        await _cleanup([admin_id, *([created_id] if created_id else [])], [admin_role])


async def test_admin_replacement_permissions_and_forbidden() -> None:
    admin_id, admin_role = await _admin()
    target_id, target_role, extra_permission = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with SessionLocal() as session:
            session.add_all([
                User(id=target_id, username=f"account-target-{target_id}", password_hash=hash_password("x")),
                Role(id=target_role, role_code=f"target-role-{target_role}", role_name="target"),
                Permission(id=extra_permission, permission_code=f"dynamic:{extra_permission}", permission_name="dynamic", permission_type="API"),
            ])
            await session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {create_token(target_id, 1)}"})).status_code == 403
            assert (await client.put(f"/api/v1/admin/users/{target_id}/roles", headers=headers, json={"role_ids": [str(target_role)]})).status_code == 200
            assert (await client.put(f"/api/v1/admin/users/{target_id}/roles", headers=headers, json={"role_ids": []})).json()["data"]["role_ids"] == []
            assert (await client.put(f"/api/v1/admin/roles/{target_role}/permissions", headers=headers, json={"permission_ids": [str(extra_permission)]})).status_code == 200
            assert (await client.put(f"/api/v1/admin/roles/{target_role}/permissions", headers=headers, json={"permission_ids": []})).json()["data"]["permission_ids"] == []
            listed = await client.get("/api/v1/admin/permissions", headers=headers)
            assert extra_permission in {uuid.UUID(item["id"]) for item in listed.json()["data"]}
            assert (await client.put(f"/api/v1/admin/users/{target_id}/roles", headers=headers, json={"role_ids": [str(uuid.uuid4())]})).status_code == 404
            assert (
                await client.put(
                    "/api/v1/admin/users/not-a-uuid/roles", headers=headers, json={"role_ids": []}
                )
            ).status_code == 422
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(Permission).where(Permission.id == extra_permission))
            await session.commit()
        await _cleanup([admin_id, target_id], [admin_role, target_role])


async def test_replacement_normalizes_duplicate_ids_and_caller_transaction_can_rollback() -> None:
    admin_id, admin_role = await _admin()
    target_id, target_role, permission_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with SessionLocal() as session:
            session.add_all(
                [
                    User(
                        id=target_id,
                        username=f"hardening-target-{target_id}",
                        password_hash=hash_password("x"),
                    ),
                    Role(
                        id=target_role,
                        role_code=f"hardening-role-{target_role}",
                        role_name="hardening role",
                    ),
                    Permission(
                        id=permission_id,
                        permission_code=f"hardening:{permission_id}",
                        permission_name="hardening permission",
                        permission_type="API",
                    ),
                ]
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            roles = await client.put(
                f"/api/v1/admin/users/{target_id}/roles",
                headers=headers,
                json={"role_ids": [str(target_role), str(target_role)]},
            )
            assert roles.status_code == 200
            assert roles.json()["data"]["role_ids"] == [str(target_role)]
            permissions = await client.put(
                f"/api/v1/admin/roles/{target_role}/permissions",
                headers=headers,
                json={"permission_ids": [str(permission_id), str(permission_id)]},
            )
            assert permissions.status_code == 200
            assert permissions.json()["data"]["permission_ids"] == [str(permission_id)]

        async with SessionLocal() as session:
            assert await session.scalar(
                select(func.count()).select_from(UserRole).where(
                    UserRole.user_id == target_id, UserRole.role_id == target_role
                )
            ) == 1
            assert await session.scalar(
                select(func.count()).select_from(RolePermission).where(
                    RolePermission.role_id == target_role,
                    RolePermission.permission_id == permission_id,
                )
            ) == 1

        rollback_role = uuid.uuid4()
        async with SessionLocal() as session:
            session.add(
                Role(
                    id=rollback_role,
                    role_code=f"rollback-role-{rollback_role}",
                    role_name="rollback role",
                )
            )
            await session.commit()
        try:
            async with SessionLocal() as session:
                try:
                    async with session.begin():
                        await AccountService(session).replace_user_roles(
                            target_id, [rollback_role], admin_id
                        )
                        raise RuntimeError("caller rollback")
                except RuntimeError as exc:
                    assert str(exc) == "caller rollback"
            async with SessionLocal() as session:
                assert await session.scalar(
                    select(func.count()).select_from(UserRole).where(
                        UserRole.user_id == target_id, UserRole.role_id == rollback_role
                    )
                ) == 0
        finally:
            await _cleanup([], [rollback_role])
    finally:
        async with SessionLocal() as session:
            await session.execute(
                delete(RolePermission).where(RolePermission.permission_id == permission_id)
            )
            await session.execute(delete(Permission).where(Permission.id == permission_id))
            await session.commit()
        await _cleanup([admin_id, target_id], [admin_role, target_role])


async def test_registration_unique_conflict_savepoint_preserves_caller_transaction() -> None:
    username = f"savepoint-registration-{uuid.uuid4()}"
    marker_role = uuid.uuid4()
    try:
        async with SessionLocal() as session:
            session.add(User(username=username, password_hash=hash_password("existing")))
            await session.commit()

        async with SessionLocal() as session:
            service = AccountService(session)

            async def skip_precheck(_: str) -> User | None:
                return None

            service.repository.active_user_by_username = skip_precheck  # type: ignore[method-assign]
            async with session.begin():
                try:
                    await service.register(username, "duplicate")
                except AppError as exc:
                    assert exc.code == "ACCOUNT_USERNAME_EXISTS"
                else:
                    raise AssertionError("expected duplicate username conflict")
                session.add(
                    Role(
                        id=marker_role,
                        role_code=f"savepoint-marker-{marker_role}",
                        role_name="savepoint marker",
                    )
                )

        async with SessionLocal() as session:
            assert await session.get(Role, marker_role) is not None
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(Role).where(Role.id == marker_role))
            await session.execute(delete(User).where(User.username == username))
            await session.commit()


async def test_review_standalone_service_does_not_leave_transaction_active() -> None:
    user_id, actor_id = uuid.uuid4(), uuid.uuid4()
    try:
        async with SessionLocal() as session:
            session.add(
                User(
                    id=user_id,
                    username=f"standalone-review-{user_id}",
                    password_hash=hash_password("password"),
                    user_status="PENDING",
                )
            )
            await session.commit()

        async with SessionLocal() as session:
            response = await AccountService(session).review(user_id, True, "approved", actor_id)
            assert response.user_status == "ENABLED"
            assert session.in_transaction() is False

        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            assert user is not None
            assert user.user_status == "ENABLED"
            assert user.reviewed_by == actor_id
            assert user.review_note == "approved"
    finally:
        async with SessionLocal() as session:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
