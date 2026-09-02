from httpx import ASGITransport, AsyncClient

from app.common.contracts import success
from app.infrastructure.adapters import InlineTaskQueue, LocalFileStorage
from app.main import app


async def test_live_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.json()["data"] == {"status": "alive"}
    assert response.headers["X-Request-ID"] == "test-request"


async def test_inline_queue() -> None:
    values: list[str] = []

    async def handler(value: str) -> None:
        values.append(value)

    await InlineTaskQueue().enqueue(handler, "done")
    assert values == ["done"]


async def test_local_storage(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path)
    key = await storage.save("sample.txt", b"content")
    assert await storage.read(key) == b"content"


def test_response() -> None:
    assert success({"value": 1}).data == {"value": 1}
