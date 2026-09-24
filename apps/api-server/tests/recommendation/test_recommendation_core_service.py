from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.database import SessionLocal
from app.modules.bid.domain.lifecycle import (
    BidFileType,
    BidImportStatus,
    BidProjectStatus,
    BidProjectType,
)
from app.modules.bid.infrastructure.models import BidProject, BidProjectFile
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.recommendation.application.service import RecommendationService
from app.modules.recommendation.infrastructure.models import RecommendationCandidate
from app.modules.recommendation.schemas import (
    BatchConfirmationRequest,
    CategoryChoiceInput,
    CategoryPath,
    ConfirmationUpdateRequest,
    ParsedRequirement,
    PersistCandidatesRequest,
)
from app.modules.recommendation.template.models import RecommendationTemplateMapping
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


@pytest.mark.asyncio
async def test_free_recommendation_run_filters_candidates_and_confirms_snapshot() -> None:
    actor_id = uuid.uuid4()
    token = uuid.uuid4().hex
    supplier = Supplier(
        supplier_code=f"RC{token[:12]}",
        supplier_name=f"自由推品供应商-{token}",
        main_brands="测试品牌",
        advantage="测试",
        archive_status=ArchiveStatus.ARCHIVED.value,
        cooperation_status=CooperationStatus.NORMAL.value,
    )
    project = BidProject(
        project_code=f"FREE{token[:10]}",
        project_name="自由推品集成测试",
        buyer_name="测试客户",
        status=BidProjectStatus.IMPORTED.value,
        import_status=BidImportStatus.NOT_REQUIRED.value,
        project_type=BidProjectType.FREE_RECOMMENDATION.value,
        remark="中秋国庆需要活动特价商品，要求毛利率百分之六以上并支持一件代发。",
        created_by=actor_id,
    )

    async with SessionLocal() as session:
        session.add_all([supplier, project])
        await session.flush()
        template_file = BidProjectFile(
            project_id=project.id,
            file_type=BidFileType.RECOMMENDATION_TEMPLATE.value,
            version_no=1,
            original_filename="推荐模板.xlsx",
            storage_key=f"test/{token}.xlsx",
            file_size=1,
            sha256="a" * 64,
            created_by=actor_id,
        )
        session.add(template_file)
        await session.flush()
        session.add(
            RecommendationTemplateMapping(
                project_id=project.id,
                template_file_id=template_file.id,
                template_sha256=template_file.sha256,
                sheet_name="推荐清单",
                header_row=1,
                data_start_row=2,
                mapping_json={"product_name": "商品名称", "gross_margin": "毛利率"},
                confirmed_by=actor_id,
                confirmed_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        eligible = Product(
            source_supplier_id=supplier.id,
            sku=f"SKU-{token[:8]}",
            product_name="中秋活动测试商品",
            company_name="测试所属公司",
            brand="测试品牌",
            category_level1_name="食品饮料",
            category_level2_name="休闲食品",
            category_level3_name="坚果",
            jd_price=Decimal("100"),
            agreement_price=Decimal("90"),
            profit=Decimal("8"),
            gross_margin=Decimal("0.08"),
            status=ProductStatus.ACTIVE.value,
        )
        low_margin = Product(
            source_supplier_id=supplier.id,
            sku=f"LOW-{token[:8]}",
            product_name="低毛利测试商品",
            category_level1_name="食品饮料",
            category_level2_name="休闲食品",
            category_level3_name="坚果",
            jd_price=Decimal("80"),
            gross_margin=Decimal("0.05"),
            status=ProductStatus.ACTIVE.value,
        )
        eligible_second = Product(
            source_supplier_id=supplier.id,
            sku=f"SKU2-{token[:8]}",
            product_name="国庆活动测试商品",
            brand="测试品牌",
            category_level1_name="食品饮料",
            category_level2_name="休闲食品",
            category_level3_name="坚果",
            jd_price=Decimal("120"),
            agreement_price=Decimal("108"),
            profit=Decimal("10"),
            gross_margin=Decimal("0.09"),
            status=ProductStatus.ACTIVE.value,
        )
        session.add_all([eligible, eligible_second, low_margin])
        await session.flush()

        service = RecommendationService(session)
        run = await service.create_run(project.id, actor_id)
        assert run.status == "QUEUED"
        assert run.raw_requirement_snapshot == project.remark

        parsed = ParsedRequirement(gross_margin_min=Decimal("0.06"), category_keywords=["食品饮料"])
        await service.save_parsed_requirement(
            run.id,
            parsed,
            provider="deepseek",
            model="deepseek-chat",
            prompt_version="free-v1",
        )
        pool = await service.category_pool(run.id)
        assert [(item.level1_name, item.level3_name, item.candidate_count) for item in pool] == [
            ("食品饮料", "坚果", 2)
        ]
        path = CategoryPath(level1_name="食品饮料", level2_name="休闲食品", level3_name="坚果")
        await service.record_category_choices(
            run.id,
            [
                CategoryChoiceInput(
                    level1_name=path.level1_name,
                    level2_name=path.level2_name,
                    level3_name=path.level3_name,
                    source="AI",
                    reason="符合节日活动场景",
                    candidate_count=1,
                )
            ],
        )
        rows = await service.search_products(run.id, [path])
        assert {row.product_id for row in rows} == {eligible.id, eligible_second.id}

        saved = await service.persist_ranked_candidates(
            run.id,
            PersistCandidatesRequest(
                candidates=[
                    {"product_id": eligible.id, "rank": 1, "score": "98.5", "reason": "毛利达标"},
                    {
                        "product_id": eligible_second.id,
                        "rank": 2,
                        "score": "96.5",
                        "reason": "节日场景匹配",
                    },
                ]
            ),
        )
        assert saved[0].price_snapshot["gross_margin"] == "0.08"
        assert saved[0].product_snapshot["company_name"] == "测试所属公司"
        assert saved[0].supplier_snapshot["supplier_name"] == supplier.supplier_name
        assert (await service.get_run(run.id)).status == "WAITING_CONFIRMATION"

        confirmed = await service.confirm_candidate(
            saved[0].id,
            ConfirmationUpdateRequest(
                campaign_price=Decimal("88"),
                delivery_status="JD_OR_SF_SUPPORTED",
                inventory_status="IN_STOCK",
                fulfillment_cycle="48小时",
            ),
            actor_id,
        )
        assert confirmed.candidate_id == saved[0].id
        assert confirmed.campaign_price == Decimal("88")
        assert (await service.get_run(run.id)).status == "CONFIRMED"
        batch_confirmed = await service.confirm_candidates(
            run.id,
            BatchConfirmationRequest(candidate_ids=[saved[1].id]),
            actor_id,
        )
        assert [item.candidate_id for item in batch_confirmed] == [saved[1].id]
        assert (await session.get(RecommendationCandidate, saved[0].id)) is not None
        await session.rollback()


@pytest.mark.asyncio
async def test_unconfirmed_latest_template_blocks_run_creation() -> None:
    actor_id = uuid.uuid4()
    token = uuid.uuid4().hex
    project = BidProject(
        project_code=f"BLOCK{token[:9]}",
        project_name="未确认模板测试",
        buyer_name="测试客户",
        status=BidProjectStatus.IMPORTED.value,
        import_status=BidImportStatus.NOT_REQUIRED.value,
        project_type=BidProjectType.FREE_RECOMMENDATION.value,
        remark="这是一段足够长但映射尚未确认的自由推品需求说明内容。",
        created_by=actor_id,
    )
    async with SessionLocal() as session:
        session.add(project)
        await session.flush()
        template_file = BidProjectFile(
            project_id=project.id,
            file_type=BidFileType.RECOMMENDATION_TEMPLATE.value,
            version_no=1,
            original_filename="未确认.xlsx",
            storage_key=f"test/{token}.xlsx",
            file_size=1,
            sha256="b" * 64,
            created_by=actor_id,
        )
        session.add(template_file)
        await session.flush()
        session.add(
            RecommendationTemplateMapping(
                project_id=project.id,
                template_file_id=template_file.id,
                template_sha256=template_file.sha256,
                sheet_name="推荐清单",
                header_row=1,
                data_start_row=2,
                mapping_json={},
            )
        )
        await session.flush()
        with pytest.raises(Exception, match="请先确认最新推品模板映射"):
            await RecommendationService(session).create_run(project.id, actor_id)
        await session.rollback()
