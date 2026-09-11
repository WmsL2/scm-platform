# ruff: noqa: E501
import asyncio
import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.common.contracts import AppError
from app.core.database import SessionLocal
from app.main import app
from app.modules.account.service import ROLE_MANAGEMENT_PERMISSION_CODES, AccountService
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


async def test_registration_history_lists_reviewed_records_only() -> None:
    admin_id, admin_role = await _admin()
    approved_username = f"history-approved-{uuid.uuid4()}"
    pending_username = f"history-pending-{uuid.uuid4()}"
    approved_id: uuid.UUID | None = None
    pending_id: uuid.UUID | None = None
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            approved = await client.post(
                "/api/v1/auth/register", json={"username": approved_username, "password": "password"}
            )
            pending = await client.post(
                "/api/v1/auth/register", json={"username": pending_username, "password": "password"}
            )
            approved_id = uuid.UUID(approved.json()["data"]["id"])
            pending_id = uuid.UUID(pending.json()["data"]["id"])
            reviewed = await client.post(
                f"/api/v1/admin/registration-requests/{approved_id}/commands/approve",
                headers=headers,
                json={"review_note": "history note"},
            )
            assert reviewed.status_code == 200

            history = await client.get("/api/v1/admin/registration-history", headers=headers)
            assert history.status_code == 200
            items = history.json()["data"]["items"]
            approved_item = next(item for item in items if item["id"] == str(approved_id))
            assert approved_item["user_status"] == "ENABLED"
            assert approved_item["review_note"] == "history note"
            assert approved_item["reviewed_at"] is not None
            assert str(pending_id) not in {item["id"] for item in items}
    finally:
        await _cleanup(
            [admin_id, *([approved_id] if approved_id else []), *([pending_id] if pending_id else [])],
            [admin_role],
        )


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
            assigned = await client.put(f"/api/v1/admin/users/{target_id}/roles", headers=headers, json={"role_ids": [str(target_role)]})
            assert assigned.status_code == 200
            assert assigned.json()["data"]["role_names"] == ["target"]
            cleared = await client.put(f"/api/v1/admin/users/{target_id}/roles", headers=headers, json={"role_ids": []})
            assert cleared.json()["data"]["role_ids"] == []
            assert cleared.json()["data"]["role_names"] == []
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


async def test_admin_creates_custom_role_with_unique_code_and_name() -> None:
    admin_id, admin_role = await _admin()
    unprivileged_id = uuid.uuid4()
    role_id: uuid.UUID | None = None
    role_code = f"pricing_operator_{uuid.uuid4().hex}"
    role_name = f"报价管理员-{uuid.uuid4()}"
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with SessionLocal() as session:
            session.add(
                User(
                    id=unprivileged_id,
                    username=f"unprivileged-role-create-{unprivileged_id}",
                    password_hash=hash_password("secret"),
                )
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            forbidden = await client.post(
                "/api/v1/admin/roles",
                headers={"Authorization": f"Bearer {create_token(unprivileged_id, 1)}"},
                json={"role_code": f"forbidden_{uuid.uuid4().hex}", "role_name": "无权限角色"},
            )
            assert forbidden.status_code == 403
            created = await client.post(
                "/api/v1/admin/roles",
                headers=headers,
                json={"role_code": f"  {role_code}  ", "role_name": f"  {role_name}  "},
            )
            assert created.status_code == 200
            body = created.json()["data"]
            role_id = uuid.UUID(body["id"])
            assert body == {
                "id": str(role_id),
                "role_code": role_code,
                "role_name": role_name,
                "is_builtin": False,
                "permission_ids": [],
            }
            duplicate_code = await client.post(
                "/api/v1/admin/roles",
                headers=headers,
                json={"role_code": role_code, "role_name": f"另一个角色-{uuid.uuid4()}"},
            )
            assert duplicate_code.status_code == 409
            assert duplicate_code.json()["code"] == "ACCOUNT_ROLE_CODE_EXISTS"
            duplicate_name = await client.post(
                "/api/v1/admin/roles",
                headers=headers,
                json={"role_code": f"catalog_operator_{uuid.uuid4().hex}", "role_name": role_name},
            )
            assert duplicate_name.status_code == 409
            assert duplicate_name.json()["code"] == "ACCOUNT_ROLE_NAME_EXISTS"
            invalid_code = await client.post(
                "/api/v1/admin/roles",
                headers=headers,
                json={"role_code": "Pricing Operator", "role_name": "无效角色"},
            )
            assert invalid_code.status_code == 422

        async with SessionLocal() as session:
            role = await session.get(Role, role_id)
            assert role is not None
            assert role.is_builtin is False
            assert role.created_by == admin_id
            assert role.updated_by == admin_id
    finally:
        await _cleanup(
            [admin_id, unprivileged_id], [admin_role, *([role_id] if role_id else [])]
        )


async def test_admin_deletes_only_unassigned_custom_roles() -> None:
    admin_id, admin_role = await _admin()
    custom_role, assigned_role, builtin_role, assigned_user = (
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
        uuid.uuid4(),
    )
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with SessionLocal() as session:
            session.add_all(
                [
                    Role(id=custom_role, role_code=f"deletable-{custom_role}", role_name="deletable"),
                    Role(id=assigned_role, role_code=f"assigned-{assigned_role}", role_name="assigned"),
                    Role(
                        id=builtin_role,
                        role_code=f"builtin-{builtin_role}",
                        role_name="builtin",
                        is_builtin=True,
                    ),
                    User(
                        id=assigned_user,
                        username=f"role-assignee-{assigned_user}",
                        password_hash=hash_password("secret"),
                    ),
                    UserRole(user_id=assigned_user, role_id=assigned_role),
                ]
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            deleted = await client.delete(f"/api/v1/admin/roles/{custom_role}", headers=headers)
            assert deleted.status_code == 200
            assert deleted.json()["data"] == {"status": "deleted"}

            assigned = await client.delete(f"/api/v1/admin/roles/{assigned_role}", headers=headers)
            assert assigned.status_code == 409
            assert assigned.json()["code"] == "ACCOUNT_ROLE_ASSIGNED_DELETE_FORBIDDEN"

            builtin = await client.delete(f"/api/v1/admin/roles/{builtin_role}", headers=headers)
            assert builtin.status_code == 409
            assert builtin.json()["code"] == "ACCOUNT_BUILTIN_ROLE_DELETE_FORBIDDEN"

        async with SessionLocal() as session:
            assignee = await session.get(User, assigned_user)
            assert assignee is not None
            assignee.is_deleted = True
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            deleted_assignee_role = await client.delete(
                f"/api/v1/admin/roles/{assigned_role}", headers=headers
            )
            assert deleted_assignee_role.status_code == 200

        async with SessionLocal() as session:
            role = await session.get(Role, custom_role)
            assert role is not None and role.is_deleted is True and role.updated_by == admin_id
            role = await session.get(Role, assigned_role)
            assert role is not None and role.is_deleted is True and role.updated_by == admin_id
    finally:
        await _cleanup(
            [admin_id, assigned_user], [admin_role, custom_role, assigned_role, builtin_role]
        )


async def test_admin_cannot_remove_own_role_management_access() -> None:
    admin_id, admin_role = await _admin()
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with SessionLocal() as session:
            required_permission_ids = list(
                (
                    await session.scalars(
                        select(Permission.id).where(
                            Permission.permission_code.in_(ROLE_MANAGEMENT_PERMISSION_CODES)
                        )
                    )
                ).all()
            )

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            retained = await client.put(
                f"/api/v1/admin/roles/{admin_role}/permissions",
                headers=headers,
                json={"permission_ids": [str(item) for item in required_permission_ids]},
            )
            assert retained.status_code == 200
            locked_out = await client.put(
                f"/api/v1/admin/roles/{admin_role}/permissions",
                headers=headers,
                json={"permission_ids": []},
            )
            assert locked_out.status_code == 409
            assert locked_out.json()["code"] == "ACCOUNT_ROLE_MANAGEMENT_SELF_LOCKOUT"
    finally:
        await _cleanup([admin_id], [admin_role])


async def test_admin_role_assignment_requires_enabled_user() -> None:
    admin_id, admin_role = await _admin()
    target_role = uuid.uuid4()
    target_ids = [uuid.uuid4() for _ in range(3)]
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    statuses = ["PENDING", "REJECTED", "DISABLED"]
    try:
        async with SessionLocal() as session:
            session.add(
                Role(
                    id=target_role,
                    role_code=f"enabled-only-role-{target_role}",
                    role_name="enabled only role",
                )
            )
            session.add_all(
                [
                    User(
                        id=user_id,
                        username=f"enabled-only-{status.lower()}-{user_id}",
                        password_hash=hash_password("x"),
                        user_status=status,
                    )
                    for user_id, status in zip(target_ids, statuses, strict=True)
                ]
            )
            await session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for user_id in target_ids:
                response = await client.put(
                    f"/api/v1/admin/users/{user_id}/roles",
                    headers=headers,
                    json={"role_ids": [str(target_role)]},
                )
                assert response.status_code == 409
                assert response.json()["code"] == "ACCOUNT_USER_NOT_ENABLED"
    finally:
        await _cleanup([admin_id, *target_ids], [admin_role, target_role])


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
            assert roles.json()["data"]["role_names"] == ["hardening role"]
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


async def test_user_logical_delete_contract() -> None:
    admin_id, admin_role = await _admin()
    target_id, target_role = uuid.uuid4(), uuid.uuid4()
    target_username = f"delete-target-{target_id}"
    headers = {"Authorization": f"Bearer {create_token(admin_id, 1)}"}
    try:
        async with SessionLocal() as session:
            session.add_all(
                [
                    User(id=target_id, username=target_username, password_hash=hash_password("secret")),
                    Role(id=target_role, role_code=f"delete-role-{target_role}", role_name="delete role"),
                    UserRole(user_id=target_id, role_id=target_role),
                ]
            )
            await session.commit()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            forbidden = await client.delete(
                f"/api/v1/admin/users/{target_id}",
                headers={"Authorization": f"Bearer {create_token(target_id, 1)}"},
            )
            assert forbidden.status_code == 403
            assert forbidden.json()["code"] == "AUTH_FORBIDDEN"
            deleted = await client.delete(f"/api/v1/admin/users/{target_id}", headers=headers)
            assert deleted.status_code == 200
            assert deleted.json()["data"] == {"status": "deleted"}
            assert str(target_id) not in {
                item["id"] for item in (await client.get("/api/v1/admin/users", headers=headers)).json()["data"]["items"]
            }
            assert (await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {create_token(target_id, 1)}"})).status_code == 401
            assert (await client.post("/api/v1/auth/login", json={"username": target_username, "password": "secret"})).status_code == 401
            assert (await client.delete(f"/api/v1/admin/users/{target_id}", headers=headers)).json()["code"] == "ACCOUNT_USER_NOT_FOUND"
            self_delete = await client.delete(f"/api/v1/admin/users/{admin_id}", headers=headers)
            assert self_delete.status_code == 409
            assert self_delete.json()["code"] == "ACCOUNT_USER_SELF_DELETE_FORBIDDEN"
            assert (await client.delete(f"/api/v1/admin/users/{uuid.uuid4()}", headers=headers)).json()["code"] == "ACCOUNT_USER_NOT_FOUND"
        async with SessionLocal() as session:
            target = await session.get(User, target_id)
            assert target is not None and target.is_deleted
            assert target.deleted_by == admin_id and target.deleted_at is not None
            assert target.updated_by == admin_id and target.token_version == 2
            assert await session.get(UserRole, {"user_id": target_id, "role_id": target_role}) is not None
            admin = await session.get(User, admin_id)
            assert admin is not None and admin.is_deleted is False
    finally:
        await _cleanup([admin_id, target_id], [admin_role, target_role])
