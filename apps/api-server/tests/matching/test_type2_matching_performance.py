import uuid
from decimal import Decimal

from app.modules.bid.infrastructure.models import BidProjectItem
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.matching.application.service import (
    TYPE2_AI_CANDIDATE_LIMIT,
    MatchingService,
)
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


def test_type2_candidate_documents_are_built_once_and_prompt_pool_is_bounded(
    monkeypatch,
) -> None:
    supplier = Supplier(
        id=uuid.uuid4(),
        supplier_code="TYPE2PERF",
        supplier_name="类型2性能测试供应商",
        main_brands="联想",
        advantage="打印耗材",
        archive_status=ArchiveStatus.ARCHIVED.value,
        cooperation_status=CooperationStatus.NORMAL.value,
        is_deleted=False,
    )
    products = [
        Product(
            id=uuid.uuid4(),
            source_supplier_id=supplier.id,
            sku=f"PERF-{index:03d}",
            brand="联想" if index == 0 else "兼容品牌",
            model="LT1821" if index == 0 else f"LT1821-ALT-{index:03d}",
            product_name=f"测试粉盒 黑色 1500页 候选{index:03d}",
            product_specification="适用 CS1821W",
            packaging_list="单支装",
            cost_price=Decimal(100 + index),
            status=ProductStatus.ACTIVE,
        )
        for index in range(30)
    ]
    items = [
        BidProjectItem(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            sheet_name="报价明细",
            source_row_number=index + 2,
            source_data={
                "品牌": "联想",
                "型号": "LT1821",
                "颜色": "黑色",
                "备注": "无原品时可同类型替代",
            },
            product_name="测试粉盒",
            brand="联想",
            model="LT1821",
            max_price=Decimal("999"),
        )
        for index in range(5)
    ]
    calls = 0
    original = MatchingService._type2_product_search_document

    def counted(product: Product):
        nonlocal calls
        calls += 1
        return original(product)

    monkeypatch.setattr(
        MatchingService,
        "_type2_product_search_document",
        staticmethod(counted),
    )

    service = MatchingService(None)  # type: ignore[arg-type]
    contexts, pools, _decisions = service._type2_agent_contexts(
        items,
        [(product, supplier) for product in products],
        project_remark="无原品时可同类型替代",
    )

    assert calls == len(products)
    assert len(contexts) == len(items)
    assert all(len(context.candidates) <= TYPE2_AI_CANDIDATE_LIMIT for context in contexts)
    assert all(len(pool) <= TYPE2_AI_CANDIDATE_LIMIT for pool in pools.values())
    assert all(context.candidates[0].model == "LT1821" for context in contexts)


def test_type2_discount_rate_is_dynamic_and_ignores_blank_result_headers() -> None:
    item = BidProjectItem(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        sheet_name="报价明细",
        source_row_number=2,
        source_data={
            "计量单位": "支",
            "需求单位": "北京烟草",
            "是否满足平台承诺折扣率（88折）": None,
        },
        brand="联想",
        model="LT1821",
    )

    assert MatchingService._type2_required_discount_rate(item, "最低价报价") is None
    assert MatchingService._type2_required_discount_rate(item, "报价需要满足9折") == Decimal(
        "0.9"
    )
    assert MatchingService._type2_required_discount_rate(item, "报价需要满足95折") == Decimal(
        "0.95"
    )
    assert MatchingService._type2_required_discount_rate(item, "折扣率不超过85%") == Decimal(
        "0.85"
    )

    item.source_data["是否满足平台承诺折扣率（88折）"] = "是"
    assert MatchingService._type2_required_discount_rate(item, None) == Decimal("0.88")


def test_type2_does_not_treat_buyer_organization_as_measurement_unit() -> None:
    item = BidProjectItem(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        sheet_name="报价明细",
        source_row_number=2,
        source_data={"计量单位": "支", "需求单位": "北京烟草"},
        brand="联想",
        model="LT1821",
    )

    assert MatchingService._type2_important_fields(item)["unit"] == "支"


def test_type2_extracts_brand_model_from_parameter_text_and_excludes_quantity() -> None:
    supplier = Supplier(
        id=uuid.uuid4(),
        supplier_code="TYPE2EMBEDDED",
        supplier_name="类型2组合参数测试供应商",
        main_brands="乐扣",
        advantage="日用百货",
        archive_status=ArchiveStatus.ARCHIVED.value,
        cooperation_status=CooperationStatus.NORMAL.value,
        is_deleted=False,
    )
    product = Product(
        id=uuid.uuid4(),
        source_supplier_id=supplier.id,
        sku="EMBEDDED-001",
        brand="LocknLock乐扣乐扣",
        model="EJC3425WHT",
        product_name="乐扣乐扣保温杯",
        cost_price=Decimal("89"),
        status=ProductStatus.ACTIVE,
    )
    item = BidProjectItem(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        sheet_name="报价明细",
        source_row_number=2,
        source_data={
            "规格型号/参数": "品牌：LocknLock乐扣乐扣 型号:EJC3425WHT",
            "预计数量": 200,
            "备注": "必须原品",
        },
        specification="品牌：LocknLock乐扣乐扣 型号:EJC3425WHT",
    )

    contexts, pools, decisions = MatchingService(None)._type2_agent_contexts(  # type: ignore[arg-type]
        [item], [(product, supplier)], project_remark=None
    )

    assert len(contexts) == 1
    assert pools[item.id] == [product.id]
    assert not decisions
    assert contexts[0].normalized_fields["brand"] == "乐扣乐扣"
    assert contexts[0].normalized_fields["model"] == "EJC3425WHT"
    assert "预计数量" not in contexts[0].source_row
    assert contexts[0].source_row["备注"] == "必须原品"


def test_type2_identifier_match_is_rejected_when_explicit_model_conflicts() -> None:
    supplier = Supplier(
        id=uuid.uuid4(),
        supplier_code="TYPE2CONFLICT",
        supplier_name="类型2冲突测试供应商",
        main_brands="联想",
        advantage="打印耗材",
        archive_status=ArchiveStatus.ARCHIVED.value,
        cooperation_status=CooperationStatus.NORMAL.value,
        is_deleted=False,
    )
    product = Product(
        id=uuid.uuid4(),
        source_supplier_id=supplier.id,
        sku="CUSTOMER-CODE-001",
        brand="联想",
        model="LT1821C",
        product_name="联想 LT1821C 粉盒",
        cost_price=Decimal("80"),
        status=ProductStatus.ACTIVE,
    )
    item = BidProjectItem(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        sheet_name="报价明细",
        source_row_number=2,
        source_data={"商品编码": "CUSTOMER-CODE-001", "品牌": "联想", "型号": "LT1821"},
        buyer_item_code="CUSTOMER-CODE-001",
        brand="联想",
        model="LT1821",
    )

    contexts, pools, decisions = MatchingService(None)._type2_agent_contexts(  # type: ignore[arg-type]
        [item], [(product, supplier)], project_remark=None
    )

    assert contexts == []
    assert pools[item.id] == []
    assert next(iter(decisions.values())).exact_candidate_keys == []
