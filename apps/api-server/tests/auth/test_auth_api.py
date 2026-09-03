import uuid

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.core.database import SessionLocal
from app.modules.auth.security import create_token, hash_password
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


async def test_login_me_logout_and_stateless_behavior() -> None:
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
            headers = {"Authorization": f"Bearer {token}"}
            me = await client.get("/api/v1/auth/me", headers=headers)
            assert me.status_code == 200 and me.json()["data"]["username"] == username
            logout = await client.post("/api/v1/auth/logout", headers=headers)
            assert logout.status_code == 200
            assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200
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
