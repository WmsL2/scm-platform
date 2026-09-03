import uuid

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.common.contracts import AppError
from app.core.config import Settings
from app.infrastructure.adapters import LocalFileStorage
from app.main import app, app_error_handler, unhandled_error_handler, validation_handler


def request_with_id(request_id: str = "test-request") -> Request:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    request.state.request_id = request_id
    return request


def test_settings_parses_comma_separated_cors() -> None:
    settings = Settings(database_url="mysql+asyncmy://user:pass@localhost/db", cors_origins="a,b")
    assert settings.cors_origins == ["a", "b"]


def test_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


async def test_request_id_is_generated() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
    uuid.UUID(response.headers["X-Request-ID"])


async def test_ready_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200


async def test_ready_returns_503_when_database_fails() -> None:
    class FailedSession:
        async def execute(self, statement: object) -> None:
            del statement
            raise OperationalError("SELECT 1", {}, Exception("database unavailable"))

    from app.main import ready

    response = await ready(request_with_id(), FailedSession())  # type: ignore[arg-type]
    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
    assert b"DEPENDENCY_UNAVAILABLE" in response.body


async def test_app_error_response() -> None:
    response = await app_error_handler(request_with_id(), AppError("INVALID", "invalid", 409))
    assert response.status_code == 409
    assert b'"code":"INVALID"' in response.body


async def test_validation_error_response() -> None:
    error = RequestValidationError(
        [{"type": "missing", "loc": ("query", "name"), "msg": "Field required"}]
    )
    response = await validation_handler(request_with_id(), error)
    assert response.status_code == 422
    assert b"VALIDATION_ERROR" in response.body


async def test_unknown_exception_response() -> None:
    response = await unhandled_error_handler(request_with_id(), RuntimeError("secret details"))
    assert response.status_code == 500
    assert b"INTERNAL_SERVER_ERROR" in response.body
    assert b"secret details" not in response.body


async def test_local_storage_rejects_path_escape(tmp_path) -> None:
    with pytest.raises(ValueError, match="inside configured root"):
        await LocalFileStorage(tmp_path).read("../outside.txt")
