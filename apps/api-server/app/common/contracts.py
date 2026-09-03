from collections.abc import Callable, Coroutine
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: str = "OK"
    message: str = "success"
    data: T
    request_id: str | None = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None


def success(data: T, request_id: str | None = None) -> ApiResponse[T]:
    return ApiResponse(data=data, request_id=request_id)


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class AuditRecorder(Protocol):
    async def record(self, action: str, resource_type: str, resource_id: str) -> None: ...


class BusinessSequence(Protocol):
    async def next_value(self, name: str) -> str: ...


class IdempotencyStore(Protocol):
    async def exists(self, key: str) -> bool: ...
    async def record(self, key: str) -> None: ...


def require_permission(permission: str) -> Callable[[], Coroutine[Any, Any, None]]:
    async def dependency() -> None:
        raise RuntimeError(f"Permission not configured: {permission}")

    return dependency
