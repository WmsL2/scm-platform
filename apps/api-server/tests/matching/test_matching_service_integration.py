import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, select, update

from app.core.database import SessionLocal
from app.modules.bid.domain.lifecycle import (
    BidImportStatus,
    BidItemStatus,
    BidProjectStatus,
    BidRecommendationType,
)
from app.modules.bid.infrastructure.models import (
    BidItemSelection,
    BidProject,
    BidProjectEvent,
    BidProjectItem,
    MatchCandidate,
    MatchTask,
)
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.matching.application.service import MatchingService
from app.modules.matching.application.type2_agent import (
    Type2BatchMatchResult,
    Type2RequirementContext,
)
from app.modules.matching.domain.rules import normalize_match_text
from app.modules.matching.schemas import (
    BidItemSelectionCreateRequest,
    NoQuoteCreateRequest,
    NoQuoteReason,
)
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


class Type2DecisionStub:
    def __init__(self, marker: str) -> None:
        self.marker = marker
        self.received: list[Type2RequirementContext] = []
        self.project_remark: str | None = None

    async def match_batch(
        self,
        requirements: list[Type2RequirementContext],
        *,
        project_remark: str | None,
    ) -> Type2BatchMatchResult:
        self.received.extend(requirements)
        self.project_remark = project_remark
        items: list[dict[str, object]] = []
        for requirement in requirements:
            if requirement.source_row["场景"] == "有原品":
                exact = next(
                    candidate.candidate_key
                    for candidate in requirement.candidates
                    if candidate.product_remark == f"{self.marker}-EXACT"
                )
                substitute = next(
                    candidate.candidate_key
                    for candidate in requirement.candidates
                    if candidate.product_remark == f"{self.marker}-CHEAP-ALT"
                )
                items.append(
                    {
                        "requirement_key": requirement.requirement_key,
                        "exact_candidate_keys": [exact],
                        "substitute_candidates": [
                            {
                                "candidate_key": substitute,
                                "differences": ["型号不同"],
                                "note": "同类型商品替代：型号由 LT1821 改为 LT1821-ALT",
                            }
                        ],
                    }
                )
            else:
                substitute = next(
                    candidate.candidate_key
                    for candidate in requirement.candidates
                    if candidate.product_remark == f"{self.marker}-ONLY-ALT"
                )
                items.append(
                    {
                        "requirement_key": requirement.requirement_key,
                        "exact_candidate_keys": [],
                        "substitute_candidates": [
                            {
                                "candidate_key": substitute,
                                "differences": ["型号不同", "客户要求原型号无货"],
                                "note": (
                                    "同类型商品替代：原型号 TN9999 无货，"
                                    "推荐兼容型号 TN9999-ALT"
                                ),
                            }
                        ],
                    }
                )
        return Type2BatchMatchResult.model_validate({"items": items})


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


@pytest.mark.asyncio
async def test_type2_automatically_selects_lowest_cost_and_finishes_with_unmatched_rows() -> None:
    actor_id = uuid.uuid4()
    token = uuid.uuid4().hex
    suppliers = [
        Supplier(
            supplier_code=f"L{token[:10]}{index}",
            supplier_name=f"类型2最低价供应商-{index}-{token}",
            main_brands="Clear",
            advantage="测试",
            archive_status=ArchiveStatus.ARCHIVED.value,
            cooperation_status=CooperationStatus.NORMAL.value,
        )
        for index in range(2)
    ]
    project = BidProject(
        project_code=f"BID{token[:12]}",
        project_name="类型2自动最低价测试",
        buyer_name="测试买家",
        status=BidProjectStatus.IMPORTED.value,
        import_status=BidImportStatus.PARSED.value,
        recommendation_type=BidRecommendationType.TYPE_2_IDENTIFIED_PRODUCT.value,
        total_item_count=3,
        processed_item_count=0,
        created_by=actor_id,
    )

    async with SessionLocal() as session:
        session.add_all([*suppliers, project])
        await session.flush()
        expensive = Product(
            source_supplier_id=suppliers[0].id,
            sku=f"EXP-{token[:8]}",
            brand="联想",
            model="LT-1821",
            product_name="联想 LT-1821",
            cost_price=Decimal("90.0000"),
            status=ProductStatus.ACTIVE,
        )
        cheapest = Product(
            source_supplier_id=suppliers[1].id,
            sku=f"LOW-{token[:8]}",
            brand="联想Lenovo",
            model="LT/1821",
            product_name="联想 Lenovo LT1821",
            cost_price=Decimal("80.0000"),
            status=ProductStatus.ACTIVE,
        )
        matched_item = BidProjectItem(
            project_id=project.id,
            sheet_name="Sheet1",
            source_row_number=2,
            source_data={"品牌": "中国联想电脑", "型号": "LT 1821"},
            brand="中国联想电脑",
            model="LT 1821",
            max_price=Decimal("85.0000"),
            status=BidItemStatus.PENDING.value,
        )
        unmatched_item = BidProjectItem(
            project_id=project.id,
            sheet_name="Sheet1",
            source_row_number=3,
            source_data={"品牌": "Missing", "型号": "NONE"},
            brand="Missing",
            model="NONE",
            status=BidItemStatus.PENDING.value,
        )
        session.add_all([expensive, cheapest, matched_item, unmatched_item])
        await session.flush()

        await MatchingService(session).start(project.id, actor_id)
        await session.flush()
        selection = await session.get(BidItemSelection, matched_item.current_selection_id)
        refreshed_project = await session.get(BidProject, project.id)

        assert selection is not None
        assert selection.product_id == cheapest.id
        assert selection.selected_unit_price == Decimal("80.0000")
        assert matched_item.status == BidItemStatus.SELECTED.value
        assert unmatched_item.status == BidItemStatus.NO_MATCH.value
        assert refreshed_project is not None
        assert refreshed_project.status == BidProjectStatus.READY.value
        assert refreshed_project.processed_item_count == 2
        await session.rollback()


@pytest.mark.asyncio
async def test_type2_ai_prefers_exact_product_and_marks_substitute_with_note() -> None:
    actor_id = uuid.uuid4()
    token = uuid.uuid4().hex
    supplier = Supplier(
        supplier_code=f"A{token[:11]}",
        supplier_name=f"类型2AI供应商-{token}",
        main_brands="联想",
        advantage="打印耗材",
        archive_status=ArchiveStatus.ARCHIVED.value,
        cooperation_status=CooperationStatus.NORMAL.value,
    )
    project = BidProject(
        project_code=f"BID{token[:12]}",
        project_name="类型2 AI 原品优先测试",
        buyer_name="北京烟草",
        remark="原品优先；没有原品时才允许同类型替代，并在备注说明差异",
        status=BidProjectStatus.IMPORTED.value,
        import_status=BidImportStatus.PARSED.value,
        recommendation_type=BidRecommendationType.TYPE_2_IDENTIFIED_PRODUCT.value,
        total_item_count=2,
        processed_item_count=0,
        created_by=actor_id,
    )

    async with SessionLocal() as session:
        session.add_all([supplier, project])
        await session.flush()
        exact = Product(
            source_supplier_id=supplier.id,
            sku=f"EXACT-{token[:8]}",
            brand="联想Lenovo",
            model="LT1821",
            product_name="联想 LT1821 黑色原装粉盒",
            product_specification="黑色，适用 CS1821W，1500页",
            packaging_list="单支装",
            category_level3_name="原装粉盒",
            cost_price=Decimal("90.0000"),
            discount_rate=Decimal("0.8800"),
            remark=f"{token}-EXACT",
            status=ProductStatus.ACTIVE,
        )
        cheaper_substitute = Product(
            source_supplier_id=supplier.id,
            sku=f"ALT1-{token[:8]}",
            brand="联想",
            model="LT1821-ALT",
            product_name="联想 LT1821 兼容黑色粉盒",
            product_specification="黑色，适用 CS1821W，1500页",
            packaging_list="单支装",
            category_level3_name="粉盒",
            cost_price=Decimal("50.0000"),
            discount_rate=Decimal("0.8000"),
            remark=f"{token}-CHEAP-ALT",
            status=ProductStatus.ACTIVE,
        )
        only_substitute = Product(
            source_supplier_id=supplier.id,
            sku=f"ALT2-{token[:8]}",
            brand="通用",
            model="TN9999-ALT",
            product_name="TN9999 兼容黑色粉盒",
            product_specification="黑色，打印量 2000 页",
            packaging_list="单支装",
            category_level3_name="粉盒",
            cost_price=Decimal("70.0000"),
            discount_rate=Decimal("0.8500"),
            remark=f"{token}-ONLY-ALT",
            status=ProductStatus.ACTIVE,
        )
        exact_item = BidProjectItem(
            project_id=project.id,
            sheet_name="报价明细",
            source_row_number=2,
            source_data={
                "场景": "有原品",
                "品牌": "联想",
                "型号": "LT1821",
                "适用机型": "CS1821W",
                "颜色": "黑",
                "包装规格": "单支装",
                "备注": "必须原装",
            },
            product_name="联想 LT1821 粉盒",
            brand="联想",
            model="LT1821",
            specification="黑色 1500页 单支装 适用 CS1821W",
            category_text="粉盒",
            max_price=Decimal("100.0000"),
            status=BidItemStatus.PENDING.value,
        )
        substitute_item = BidProjectItem(
            project_id=project.id,
            sheet_name="报价明细",
            source_row_number=3,
            source_data={
                "场景": "无原品",
                "品牌": "指定品牌",
                "型号": "TN9999",
                "颜色": "黑",
                "打印量": "2000页",
                "备注": "无对应商品时可同类型替代",
            },
            product_name="TN9999 粉盒",
            brand="指定品牌",
            model="TN9999",
            specification="黑色 2000页",
            category_text="粉盒",
            max_price=Decimal("80.0000"),
            status=BidItemStatus.PENDING.value,
        )
        simple_item = BidProjectItem(
            project_id=project.id,
            sheet_name="报价明细",
            source_row_number=4,
            source_data={"品牌": "联想", "型号": "LT1821"},
            brand="联想",
            model="LT1821",
            max_price=Decimal("100.0000"),
            status=BidItemStatus.PENDING.value,
        )
        session.add_all(
            [
                exact,
                cheaper_substitute,
                only_substitute,
                exact_item,
                substitute_item,
                simple_item,
            ]
        )
        await session.flush()
        assert MatchingService._type2_required_discount_rate(
            exact_item, "需满足 88 折对比大客户实时价"
        ) == Decimal("0.88")
        assert MatchingService._type2_required_discount_rate(
            exact_item, "原品优先，无原品才允许替代"
        ) is None

        project_id = project.id
        supplier_id = supplier.id
        product_ids = [exact.id, cheaper_substitute.id, only_substitute.id]
        exact_item_id = exact_item.id
        substitute_item_id = substitute_item.id
        simple_item_id = simple_item.id
        exact_product_id = exact.id
        substitute_product_id = only_substitute.id
        project_remark = project.remark
        await session.commit()

        agent = Type2DecisionStub(token)
        async with session.begin():
            await MatchingService(session, type2_agent=agent).start(  # type: ignore[arg-type]
                project_id, actor_id
            )
        session.expire_all()
        exact_item = await session.get(BidProjectItem, exact_item_id)
        substitute_item = await session.get(BidProjectItem, substitute_item_id)
        simple_item = await session.get(BidProjectItem, simple_item_id)
        assert exact_item is not None
        assert substitute_item is not None
        assert simple_item is not None
        exact_selection = await session.get(
            BidItemSelection, exact_item.current_selection_id
        )
        substitute_selection = await session.get(
            BidItemSelection, substitute_item.current_selection_id
        )
        simple_selection = await session.get(
            BidItemSelection, simple_item.current_selection_id
        )

        assert exact_selection is not None
        assert exact_selection.product_id == exact_product_id
        assert exact_selection.selected_unit_price == Decimal("90.0000")
        assert exact_selection.product_snapshot["type2_match_type"] == "TYPE2_AI_EXACT"
        assert substitute_selection is not None
        assert substitute_selection.product_id == substitute_product_id
        assert substitute_selection.note is not None
        assert substitute_selection.note.startswith("同类型商品替代：")
        assert agent.project_remark == project_remark
        assert agent.received[0].source_row["备注"] == "必须原装"
        assert agent.received[0].important_fields["color"] == "黑"
        assert len(agent.received) == 2
        assert simple_selection is not None
        assert simple_selection.product_id == exact_product_id
        await session.commit()

        item_ids = [exact_item_id, substitute_item_id, simple_item_id]
        await session.execute(
            update(BidProjectItem)
            .where(BidProjectItem.id.in_(item_ids))
            .values(current_selection_id=None)
        )
        await session.execute(
            delete(BidItemSelection).where(BidItemSelection.project_item_id.in_(item_ids))
        )
        await session.execute(
            delete(MatchCandidate).where(MatchCandidate.project_item_id.in_(item_ids))
        )
        await session.execute(delete(MatchTask).where(MatchTask.project_id == project_id))
        await session.execute(
            delete(BidProjectEvent).where(BidProjectEvent.project_id == project_id)
        )
        await session.execute(
            delete(BidProjectItem).where(BidProjectItem.id.in_(item_ids))
        )
        await session.execute(delete(BidProject).where(BidProject.id == project_id))
        await session.execute(delete(Product).where(Product.id.in_(product_ids)))
        await session.execute(delete(Supplier).where(Supplier.id == supplier_id))
        await session.commit()
