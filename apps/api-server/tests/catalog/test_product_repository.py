from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.infrastructure.repository import (
    PRODUCT_IMPORT_PRODUCT_LOOKUP_BATCH_SIZE,
    PRODUCT_IMPORT_TEMP_MEDIA_CLEANUP_BATCH_SIZE,
    ProductRepository,
)


async def test_product_key_lookup_batches_large_composite_in_query() -> None:
    class ScalarRows:
        def all(self) -> list[object]:
            return []

    class Session:
        def __init__(self) -> None:
            self.statements: list[object] = []

        async def scalars(self, statement: object) -> ScalarRows:
            self.statements.append(statement)
            return ScalarRows()

    keys = {
        (UUID(int=index), f"SKU-{index:04d}")
        for index in range(PRODUCT_IMPORT_PRODUCT_LOOKUP_BATCH_SIZE * 2 + 1)
    }
    session = Session()
    repository = ProductRepository(cast(AsyncSession, session))

    products = await repository.products_by_supplier_sku(keys, for_update=True)

    assert products == {}
    assert len(session.statements) == 3
    assert all(
        getattr(statement, "_for_update_arg") is not None for statement in session.statements
    )


async def test_temporary_media_cleanup_locks_small_batches_without_waiting() -> None:
    class ScalarRows:
        def all(self) -> list[object]:
            return []

    class Session:
        def __init__(self) -> None:
            self.statements: list[object] = []

        async def scalars(self, statement: object) -> ScalarRows:
            self.statements.append(statement)
            return ScalarRows()

    session = Session()
    repository = ProductRepository(cast(AsyncSession, session))

    tasks = await repository.temporary_media_cleanup_tasks_for_update(
        stale_before=datetime(2026, 9, 22)
    )

    assert tasks == []
    assert len(session.statements) == 3
    assert all(
        getattr(statement, "_for_update_arg").skip_locked is True
        for statement in session.statements
    )
    assert all(
        getattr(statement, "_limit_clause").value == PRODUCT_IMPORT_TEMP_MEDIA_CLEANUP_BATCH_SIZE
        for statement in session.statements
    )
