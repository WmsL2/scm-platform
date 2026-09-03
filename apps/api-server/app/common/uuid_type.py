import uuid
from typing import Any

from sqlalchemy import CHAR, TypeDecorator


class UUIDChar36(TypeDecorator[uuid.UUID]):
    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value: uuid.UUID | str | None, dialect: Any) -> str | None:
        del dialect
        return None if value is None else str(uuid.UUID(str(value)))

    def process_result_value(self, value: str | None, dialect: Any) -> uuid.UUID | None:
        del dialect
        return None if value is None else uuid.UUID(value)
