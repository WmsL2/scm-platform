from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.bid.domain.product_scope import ProductSelectionScope
from app.modules.matching.infrastructure.repository import MatchingRepository


class _Rows:
    def all(self) -> list[object]:
        return []


@pytest.mark.asyncio
async def test_eligible_products_applies_company_and_purchaser_scope() -> None:
    session = MagicMock()
    session.execute = AsyncMock(return_value=_Rows())
    repository = MatchingRepository(session)

    await repository.eligible_products(
        ProductSelectionScope.from_values(["上海公司"], ["张三", "李四"])
    )

    statement = session.execute.call_args.args[0]
    params = statement.compile().params

    assert "scm_product.company_name IN" in str(statement)
    assert "scm_product.purchasing_agent IN" in str(statement)
    assert tuple(params.values())[-2:] == (["上海公司"], ["张三", "李四"])
