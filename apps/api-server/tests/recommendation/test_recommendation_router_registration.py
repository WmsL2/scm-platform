from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_recommendation_router_is_registered_in_api_v1() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/recommendation-projects/{uuid4()}/runs")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_UNAUTHORIZED"
