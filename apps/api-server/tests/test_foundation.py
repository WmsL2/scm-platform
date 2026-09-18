import pytest
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
    key = await storage.save("product-images/task/sample.png", b"content")
    assert key.startswith("product-images/task/")
    assert key.endswith(".png")
    assert await storage.read(key) == b"content"
    await storage.delete(key)
    with pytest.raises(FileNotFoundError):
        await storage.read(key)
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"workbook")
    workbook_key = await storage.save_file("product-import-sources/task.xlsx", source)
    copied = tmp_path / "copied.xlsx"
    await storage.copy_to(workbook_key, copied)
    assert copied.read_bytes() == b"workbook"


def test_response() -> None:
    assert success({"value": 1}).data == {"value": 1}
