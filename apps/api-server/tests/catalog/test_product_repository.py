from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.infrastructure.repository import (
    PRODUCT_IMPORT_PRODUCT_LOOKUP_BATCH_SIZE,
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


async def test_import_task_staging_deletion_uses_foreign_key_safe_order() -> None:
    class Session:
        def __init__(self) -> None:
            self.statements: list[object] = []

        async def execute(self, statement: object) -> None:
            self.statements.append(statement)

    session = Session()
    repository = ProductRepository(cast(AsyncSession, session))
    task_id = UUID(int=1)

    await repository.delete_import_task_staging(task_id)

    assert len(session.statements) == 3
    statements = [str(statement) for statement in session.statements]
    assert "scm_product_import_row" in statements[0]
    assert "scm_product_import_supplier_match" in statements[1]
    assert "scm_product_import_task" in statements[2]
