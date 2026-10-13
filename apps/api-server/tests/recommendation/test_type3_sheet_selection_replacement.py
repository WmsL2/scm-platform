from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.type3_recommendation.application.service import Type3RecommendationService
from app.modules.type3_recommendation.schemas import (
    Type3Node,
    Type3SheetPreview,
    Type3SheetSelection,
    Type3SheetSelectionRequest,
)


@pytest.mark.asyncio
async def test_type3_replacement_flushes_deleted_sheet_before_insert() -> None:
    events: list[str] = []
    session = MagicMock()
    session.in_transaction.return_value = True
    session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: [SimpleNamespace()]))
    session.delete = AsyncMock(side_effect=lambda _row: events.append("delete"))
    session.flush = AsyncMock(side_effect=lambda: events.append("flush"))
    session.add = MagicMock(side_effect=lambda _row: events.append("add"))
    service = Type3RecommendationService(session)
    project = SimpleNamespace(id=uuid4())
    template = SimpleNamespace(id=uuid4(), storage_key="test")
    actor_id = uuid4()
    node = Type3Node(
        node_id="家用电器!C3",
        coordinate="C3",
        level="LEVEL3",
        label="炊具电器",
        code="6.1.1",
    )
    sheet = Type3SheetPreview(
        sheet_name="家用电器", header_row=1, data_start_row=2, max_row=20, max_column=20,
        mapping_json={"version": 2, "columns": []}, nodes=[node],
    )
    service._project_and_template = AsyncMock(return_value=(project, template))  # type: ignore[method-assign]
    service._inspect = MagicMock(return_value=[sheet])  # type: ignore[method-assign]
    service.storage.read = AsyncMock(return_value=b"workbook")  # type: ignore[method-assign]

    await service.save_sheet_selection(
        project.id,
        Type3SheetSelectionRequest(sheets=[Type3SheetSelection(**sheet.model_dump())]),
        actor_id,
    )

    assert events == ["delete", "flush", "add"]
