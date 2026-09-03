import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app


@pytest.mark.parametrize(
    "invalid_claim",
    ["expired", "missing_sub", "missing_ver", "missing_exp", "missing_iat"],
)
async def test_me_rejects_invalid_jwt_claims_at_api_level(invalid_claim: str) -> None:
    now = datetime.now(timezone.utc)
    payload: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "ver": 1,
        "iat": now,
        "exp": now + timedelta(minutes=1),
    }
    if invalid_claim == "expired":
        payload["exp"] = now - timedelta(minutes=1)
    elif invalid_claim == "missing_sub":
        del payload["sub"]
    elif invalid_claim == "missing_ver":
        del payload["ver"]
    elif invalid_claim == "missing_exp":
        del payload["exp"]
    else:
        del payload["iat"]

    token = jwt.encode(
        payload,
        get_settings().auth_jwt_secret.get_secret_value(),
        algorithm="HS256",
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_UNAUTHORIZED"
