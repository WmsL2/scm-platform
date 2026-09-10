from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

TaskHandler = Callable[..., Awaitable[None]]


class TaskQueue(Protocol):
    async def enqueue(self, handler: TaskHandler, *args: Any, **kwargs: Any) -> None: ...


class InlineTaskQueue:
    async def enqueue(self, handler: TaskHandler, *args: Any, **kwargs: Any) -> None:
        await handler(*args, **kwargs)


class ArqTaskQueue:
    async def enqueue(self, handler: TaskHandler, *args: Any, **kwargs: Any) -> None:
        del handler, args, kwargs
        raise RuntimeError("ARQ task queue is not configured")


class ObjectStorage(Protocol):
    async def save(self, name: str, content: bytes) -> str: ...
    async def read(self, key: str) -> bytes: ...


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _target(self, key: str) -> Path:
        relative = Path(key)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Storage key must stay inside configured root")
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("Storage key must stay inside configured root")
        return target

    async def save(self, name: str, content: bytes) -> str:
        requested = Path(name.replace("\\", "/"))
        if requested.is_absolute() or ".." in requested.parts:
            raise ValueError("Storage key must stay inside configured root")
        suffix = requested.suffix.lower()
        key = (requested.parent / f"{uuid4()}{suffix}").as_posix()
        target = self._target(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key

    async def read(self, key: str) -> bytes:
        return self._target(key).read_bytes()


class MinioStorage:
    async def healthcheck(self) -> None:
        raise RuntimeError("MinIO storage is not configured")

    async def save(self, name: str, content: bytes) -> str:
        del name, content
        raise RuntimeError("MinIO storage is not configured")

    async def read(self, key: str) -> bytes:
        del key
        raise RuntimeError("MinIO storage is not configured")


def get_object_storage() -> ObjectStorage:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.storage_mode == "local":
        return LocalFileStorage(settings.local_storage_path)
    if settings.storage_mode == "minio":
        return MinioStorage()
    raise RuntimeError(f"Unsupported storage mode: {settings.storage_mode}")


class Cache(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...


class NoopCache:
    async def get(self, key: str) -> str | None:
        del key
        return None

    async def set(self, key: str, value: str) -> None:
        del key, value


class RedisCache:
    async def healthcheck(self) -> None:
        raise RuntimeError("Redis cache is not configured")

    async def get(self, key: str) -> str | None:
        del key
        raise RuntimeError("Redis cache is not configured")

    async def set(self, key: str, value: str) -> None:
        del key, value
        raise RuntimeError("Redis cache is not configured")
