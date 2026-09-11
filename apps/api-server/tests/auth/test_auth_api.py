import uuid
from datetime import timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.database import SessionLocal
from app.modules.auth.models import AuthSession
from app.modules.auth.security import create_token, decode_token, hash_password
from app.modules.auth.service import utc_now
from app.modules.system.models import User


async def create_user(status: str = "ENABLED", deleted: bool = False) -> tuple[uuid.UUID, str]:
    user_id, username = uuid.uuid4(), f"auth-test-{uuid.uuid4()}"
    async with SessionLocal() as session:
        session.add(
            User(
                id=user_id,
                username=username,
                password_hash=hash_password("secret"),
                user_status=status,
                is_deleted=deleted,
            )
        )
        await session.commit()
    return user_id, username


async def cleanup(user_id: uuid.UUID) -> None:
    async with SessionLocal() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def test_login_refresh_logout_and_immediate_session_revocation() -> None:
    user_id, username = await create_user()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
            base_url="http://test",
        ) as client:
            login = await client.post(
                "/api/v1/auth/login", json={"username": username, "password": "secret"}
            )
            assert login.status_code == 200
            token = login.json()["data"]["access_token"]
            refresh_token = client.cookies.get("scm_refresh_token")
            assert refresh_token is not None
            assert "HttpOnly" in login.headers["set-cookie"]
            assert "Path=/api/v1/auth" in login.headers["set-cookie"]
            headers = {"Authorization": f"Bearer {token}"}
            me = await client.get("/api/v1/auth/me", headers=headers)
            assert me.status_code == 200 and me.json()["data"]["username"] == username

            refreshed = await client.post("/api/v1/auth/refresh")
            assert refreshed.status_code == 200
            rotated_token = refreshed.json()["data"]["access_token"]
            assert rotated_token != token
            assert client.cookies.get("scm_refresh_token") != refresh_token

            logout = await client.post("/api/v1/auth/logout", headers=headers)
            assert logout.status_code == 200
            assert client.cookies.get("scm_refresh_token") is None
            assert (
                await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {rotated_token}"},
                )
            ).status_code == 401
    finally:
        await cleanup(user_id)


async def test_refresh_token_rotation_rejects_reuse_and_revokes_session() -> None:
    user_id, username = await create_user()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/api/v1/auth/login", json={"username": username, "password": "secret"}
            )
            old_refresh_token = client.cookies.get("scm_refresh_token")
            assert old_refresh_token is not None
            refreshed = await client.post("/api/v1/auth/refresh")
            rotated_access_token = refreshed.json()["data"]["access_token"]

            session_id = decode_token(rotated_access_token)[2]
            assert session_id is not None
            async with SessionLocal() as session:
                auth_session = await session.get(AuthSession, session_id)
                assert auth_session is not None
                auth_session.previous_token_valid_until = utc_now() - timedelta(seconds=1)
                await session.commit()

            async with AsyncClient(
                transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
                base_url="http://test",
            ) as replay_client:
                replay_client.cookies.set(
                    "scm_refresh_token",
                    old_refresh_token,
                    path="/api/v1/auth",
                )
                replay = await replay_client.post("/api/v1/auth/refresh")
                assert replay.status_code == 401
                assert replay.json()["code"] == "AUTH_REFRESH_INVALID"

            me = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {rotated_access_token}"},
            )
            assert me.status_code == 401
    finally:
        await cleanup(user_id)


async def test_refresh_rotation_grace_allows_near_simultaneous_browser_tabs() -> None:
    user_id, username = await create_user()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
            base_url="http://test",
        ) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "secret"},
            )
            original_refresh_token = client.cookies.get("scm_refresh_token")
            assert original_refresh_token is not None
            assert (await client.post("/api/v1/auth/refresh")).status_code == 200

            async with AsyncClient(
                transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
                base_url="http://test",
            ) as second_tab:
                second_tab.cookies.set(
                    "scm_refresh_token",
                    original_refresh_token,
                    path="/api/v1/auth",
                )
                concurrent_refresh = await second_tab.post("/api/v1/auth/refresh")
                assert concurrent_refresh.status_code == 200

            session_id = decode_token(login.json()["data"]["access_token"])[2]
            assert session_id is not None
            async with SessionLocal() as session:
                auth_session = await session.get(AuthSession, session_id)
                assert auth_session is not None
                assert auth_session.revoked_at is None
                assert auth_session.rotation_counter == 2
    finally:
        await cleanup(user_id)


async def test_logout_revokes_bearer_and_cookie_sessions_after_relogin() -> None:
    user_id, username = await create_user()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
            base_url="http://test",
        ) as client:
            first_login = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "secret"},
            )
            first_token = first_login.json()["data"]["access_token"]
            second_login = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "secret"},
            )
            second_token = second_login.json()["data"]["access_token"]

            logout = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {first_token}"},
            )
            assert logout.status_code == 200
            for token in (first_token, second_token):
                me = await client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert me.status_code == 401
    finally:
        await cleanup(user_id)


async def test_refresh_rejects_idle_and_absolute_expiration() -> None:
    for expiry_field in ("idle_expires_at", "absolute_expires_at"):
        user_id, username = await create_user()
        try:
            async with AsyncClient(
                transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
                base_url="http://test",
            ) as client:
                login = await client.post(
                    "/api/v1/auth/login",
                    json={"username": username, "password": "secret"},
                )
                session_id = decode_token(login.json()["data"]["access_token"])[2]
                assert session_id is not None
                async with SessionLocal() as session:
                    auth_session = await session.get(AuthSession, session_id)
                    assert auth_session is not None
                    setattr(auth_session, expiry_field, utc_now() - timedelta(seconds=1))
                    await session.commit()

                refresh = await client.post("/api/v1/auth/refresh")
                assert refresh.status_code == 401
                assert refresh.json()["code"] == "AUTH_REFRESH_INVALID"
        finally:
            await cleanup(user_id)


async def test_password_change_revokes_all_device_sessions() -> None:
    user_id, username = await create_user()
    try:
        async with (
            AsyncClient(
                transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
                base_url="http://test",
            ) as first_device,
            AsyncClient(
                transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
                base_url="http://test",
            ) as second_device,
        ):
            first_login = await first_device.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "secret"},
            )
            second_login = await second_device.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "secret"},
            )
            first_token = first_login.json()["data"]["access_token"]
            second_token = second_login.json()["data"]["access_token"]

            changed = await first_device.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": f"Bearer {first_token}"},
                json={"current_password": "secret", "new_password": "new-secret"},
            )
            assert changed.status_code == 200
            assert first_device.cookies.get("scm_refresh_token") is None
            assert (
                await first_device.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {first_token}"},
                )
            ).status_code == 401
            assert (
                await second_device.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {second_token}"},
                )
            ).status_code == 401
            assert (await second_device.post("/api/v1/auth/refresh")).status_code == 401
    finally:
        await cleanup(user_id)


async def test_disabled_user_loses_access_and_refresh_session() -> None:
    user_id, username = await create_user()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
            base_url="http://test",
        ) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "secret"},
            )
            access_token = login.json()["data"]["access_token"]
            session_id = decode_token(access_token)[2]
            assert session_id is not None
            async with SessionLocal() as session:
                user = await session.get(User, user_id)
                assert user is not None
                user.user_status = "DISABLED"
                await session.commit()

            me = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me.status_code == 401
            assert (await client.post("/api/v1/auth/refresh")).status_code == 401
            async with SessionLocal() as session:
                auth_session = await session.get(AuthSession, session_id)
                assert auth_session is not None
                assert auth_session.revoked_reason == "user_unavailable"
    finally:
        await cleanup(user_id)


async def test_login_failures_do_not_enumerate_users() -> None:
    disabled_id, disabled_username = await create_user(status="DISABLED")
    wrong_password_id, wrong_password_username = await create_user()
    deleted_id, deleted_username = await create_user(deleted=True)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
            base_url="http://test",
        ) as client:
            missing = await client.post(
                "/api/v1/auth/login", json={"username": "missing", "password": "bad"}
            )
            wrong_password = await client.post(
                "/api/v1/auth/login",
                json={"username": wrong_password_username, "password": "bad"},
            )
            disabled = await client.post(
                "/api/v1/auth/login", json={"username": disabled_username, "password": "secret"}
            )
            deleted = await client.post(
                "/api/v1/auth/login", json={"username": deleted_username, "password": "secret"}
            )
            responses = (missing, wrong_password, disabled, deleted)
            assert {response.status_code for response in responses} == {401}
            assert {
                (response.json()["code"], response.json()["message"])
                for response in responses
            } == {("AUTH_INVALID_CREDENTIALS", "Invalid credentials")}
    finally:
        await cleanup(disabled_id)
        await cleanup(wrong_password_id)
        await cleanup(deleted_id)


async def test_token_version_invalidates_token() -> None:
    user_id, username = await create_user()
    try:
        token = create_token(user_id, 1)
        async with SessionLocal() as session:
            user = await session.get(User, user_id)
            assert user is not None
            user.token_version = 2
            await session.commit()
        async with AsyncClient(
            transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
            base_url="http://test",
        ) as client:
            assert (
                await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            ).status_code == 401
    finally:
        await cleanup(user_id)


async def test_disabled_or_deleted_user_invalidates_existing_token() -> None:
    user_id, _ = await create_user()
    headers = {"Authorization": f"Bearer {create_token(user_id, 1)}"}
    try:
        async with AsyncClient(
            transport=ASGITransport(app=__import__("app.main", fromlist=["app"]).app),
            base_url="http://test",
        ) as client:
            async with SessionLocal() as session:
                user = await session.get(User, user_id)
                assert user is not None
                user.user_status = "DISABLED"
                await session.commit()
            disabled = await client.get("/api/v1/auth/me", headers=headers)
            assert disabled.status_code == 401
            assert disabled.json()["code"] == "AUTH_UNAUTHORIZED"

            async with SessionLocal() as session:
                user = await session.get(User, user_id)
                assert user is not None
                user.user_status = "ENABLED"
                user.is_deleted = True
                await session.commit()
            deleted = await client.get("/api/v1/auth/me", headers=headers)
            assert deleted.status_code == 401
            assert deleted.json()["code"] == "AUTH_UNAUTHORIZED"
    finally:
        await cleanup(user_id)
