import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.bid.domain.lifecycle import BidImportStatus, BidItemStatus, BidProjectStatus
from app.modules.bid.infrastructure.models import (
    BidItemSelection,
    BidProject,
    BidProjectItem,
    MatchCandidate,
)
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.matching.application.service import MatchingService
from app.modules.matching.domain.rules import normalize_match_text
from app.modules.matching.schemas import (
    BidItemSelectionCreateRequest,
    NoQuoteCreateRequest,
    NoQuoteReason,
)
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


@pytest.mark.asyncio
async def test_matching_persists_candidates_selection_snapshot_and_no_quote() -> None:
    actor_id = uuid.uuid4()
    token = uuid.uuid4().hex
    supplier = Supplier(
        supplier_code=f"M{token[:12]}",
        supplier_name=f"匹配测试供应商-{token}",
        main_brands="Clear",
        advantage="测试",
        archive_status=ArchiveStatus.ARCHIVED.value,
        cooperation_status=CooperationStatus.NORMAL.value,
    )
    project = BidProject(
        project_code=f"BID{token[:12]}",
        project_name="匹配集成测试",
        buyer_name="测试买家",
        status=BidProjectStatus.IMPORTED.value,
        import_status=BidImportStatus.PARSED.value,
        total_item_count=2,
        processed_item_count=0,
        created_by=actor_id,
    )

    async with SessionLocal() as session:
        session.add_all([supplier, project])
        await session.flush()
        product = Product(
            source_supplier_id=supplier.id,
            sku=f"SKU-{token[:8]}",
            brand="Clear",
            model="ARC3",
            product_name="Clear ARC3 蓝牙耳机",
            product_specification="黑色",
            cost_price=Decimal("80.0000"),
            jd_price=Decimal("120.0000"),
            agreement_price=Decimal("100.0000"),
            status=ProductStatus.ACTIVE,
        )
        matched_item = BidProjectItem(
            project_id=project.id,
            sheet_name="需求明细",
            source_row_number=2,
            source_data={"采购项编码": product.sku},
            buyer_item_code=product.sku,
            quantity=Decimal("2"),
            unit="台",
            max_price=Decimal("100.0000"),
            status=BidItemStatus.PENDING.value,
        )
        unmatched_item = BidProjectItem(
            project_id=project.id,
            sheet_name="需求明细",
            source_row_number=3,
            source_data={"商品名称": "不存在的测试商品"},
            product_name="不存在的测试商品",
            quantity=Decimal("1"),
            unit="台",
            status=BidItemStatus.PENDING.value,
        )
        session.add_all([product, matched_item, unmatched_item])
        await session.flush()

        service = MatchingService(session)
        task = await service.start(project.id, actor_id)
        candidates = await service.candidates(project.id, matched_item.id)

        assert task.status == "COMPLETED"
        assert task.processed_item_count == 2
        assert len(candidates) == 1
        assert candidates[0].product_id == product.id
        assert candidates[0].match_reason["recall_stage"] == "EXACT_IDENTIFIER"
        assert matched_item.status == BidItemStatus.UNIQUE_MATCH.value
        assert unmatched_item.status == BidItemStatus.NO_MATCH.value

        selected = await service.select(
            project.id,
            matched_item.id,
            BidItemSelectionCreateRequest(
                candidate_id=candidates[0].candidate_id,
                selected_unit_price=Decimal("99.0000"),
            ),
            actor_id,
        )
        no_quote = await service.no_quote(
            project.id,
            unmatched_item.id,
            NoQuoteCreateRequest(
                reason=NoQuoteReason.NO_PRODUCT_MATCH,
                reason_detail="没有可用正式商品",
            ),
            actor_id,
        )
        await session.flush()

        selection = await session.get(BidItemSelection, selected.selection_id)
        candidate_count = await session.scalar(
            select(MatchCandidate).where(MatchCandidate.project_item_id == matched_item.id)
        )
        refreshed_project = await session.get(BidProject, project.id)

        assert selected.status == BidItemStatus.SELECTED.value
        assert no_quote.status == BidItemStatus.NO_QUOTE.value
        assert selection is not None
        normalized_snapshot = selection.requirement_snapshot["normalized"]
        assert normalized_snapshot["buyer_item_code"] == normalize_match_text(product.sku)
        assert selection.product_snapshot["id"] == str(product.id)
        assert selection.supplier_snapshot["id"] == str(supplier.id)
        assert selection.price_snapshot["selected_unit_price"] == "99.0000"
        assert candidate_count is not None
        assert refreshed_project is not None
        assert refreshed_project.status == BidProjectStatus.READY.value
        assert unmatched_item.current_selection_id is None
        assert unmatched_item.no_quote_reason is not None
        await session.rollback()
