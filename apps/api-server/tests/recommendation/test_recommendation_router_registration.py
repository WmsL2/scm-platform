from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.responses import StreamingResponse

from app.main import app
from app.modules.recommendation.api.recommendation_router import _attachment_headers


def test_recommendation_download_header_supports_chinese_filename() -> None:
    filename = "BID-TEST-自由推品结果-V1.xlsx"
    response = StreamingResponse(iter([b"xlsx"]), headers=_attachment_headers(filename))

    assert response.headers["content-disposition"] == (
        'attachment; filename="recommendation-export.xlsx"; '
        "filename*=UTF-8''BID-TEST-%E8%87%AA%E7%94%B1%E6%8E%A8%E5%93%81%E7%BB%93%E6%9E%9C-V1.xlsx"
    )


@pytest.mark.asyncio
async def test_recommendation_router_is_registered_in_api_v1() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/api/v1/recommendation-projects/{uuid4()}/runs")
        export_response = await client.post(
            f"/api/v1/recommendation-projects/{uuid4()}/runs/{uuid4()}/exports"
        )
        download_response = await client.get(
            f"/api/v1/recommendation-projects/runs/{uuid4()}/exports/{uuid4()}/download"
        )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_UNAUTHORIZED"
    assert export_response.status_code == 401
    assert download_response.status_code == 401
