import uuid
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.common.contracts import AppError, PageParams
from app.core.database import SessionLocal
from app.infrastructure.adapters import LocalFileStorage
from app.modules.bid.application.service import BidProjectService
from app.modules.bid.domain.lifecycle import (
    BidImportStatus,
    BidProjectStatus,
    ensure_transition,
)
from app.modules.bid.infrastructure.models import BidTemplate


def _workbook_bytes() -> tuple[bytes, list[str]]:
    headers = [
        "采购项编码",
        "商品名称",
        "品牌",
        "型号",
        "规格",
        "类目",
        "数量",
        "单位",
        "限价",
        "报价",
    ]
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "需求明细"
    sheet.append(headers)
    sheet.append(["BUY-1", "测试商品", "测试品牌", "M-1", "规格A", "数码", 2, "台", 100, None])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue(), headers


@pytest.mark.asyncio
async def test_project_creation_parses_frozen_template(tmp_path: Path) -> None:
    file_bytes, headers = _workbook_bytes()
    actor_id = uuid.uuid4()
    storage = LocalFileStorage(tmp_path)
    async with SessionLocal() as session:
        service = BidProjectService(session, storage)
        template = BidTemplate(
            template_code=f"test-{uuid.uuid4()}",
            template_name="测试模板",
            version=1,
            sheet_name="需求明细",
            header_row=1,
            data_start_row=2,
            import_mapping={
                "buyer_item_code": "采购项编码",
                "product_name": "商品名称",
                "brand": "品牌",
                "model": "型号",
                "specification": "规格",
                "category_text": "类目",
                "quantity": "数量",
                "unit": "单位",
                "max_price": "限价",
            },
            export_mapping={"selected_unit_price": "报价"},
            fingerprint=service._fingerprint("需求明细", 1, headers),
        )
        session.add(template)
        await session.flush()
        response = await service.create(
            project_name="测试投标项目",
            buyer_name="测试需求商",
            deadline_at=None,
            remark=None,
            filename="需求.xlsx",
            file_bytes=file_bytes,
            actor_id=actor_id,
        )
        assert response.import_status == BidImportStatus.PARSED
        assert response.total_item_count == 1
        rows = await service.items(response.id, page_params=PageParams(), status=None)
        assert rows.total == 1
        assert rows.items[0].product_name == "测试商品"
        await session.rollback()


def test_project_lifecycle_rejects_illegal_transition() -> None:
    with pytest.raises(AppError) as exc_info:
        ensure_transition(BidProjectStatus.IMPORTED.value, BidProjectStatus.SUBMITTED)
    assert exc_info.value.status_code == 409
