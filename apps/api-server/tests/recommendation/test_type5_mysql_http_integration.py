"""Real-MySQL HTTP acceptance coverage for the Type-5 short-session workflow.

These tests create records with a per-test UUID prefix and delete only those exact
records in ``finally`` blocks. They intentionally run against the configured local
development database; they never issue schema or whole-table destructive commands.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.integrations.deepseek.client import DeepSeekProviderError
from app.jobs import recommendation_agent
from app.main import app
from app.modules.auth.security import create_token, hash_password
from app.modules.bid.domain.lifecycle import BidImportStatus, BidProjectStatus, BidProjectType
from app.modules.bid.infrastructure.models import BidProject, BidProjectEvent
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.recommendation.application.agent_schemas import RequirementAnalysis
from app.modules.recommendation.application.ppt_plan_runner import PptPlanAgentRunner
from app.modules.recommendation.infrastructure.models import (
    PptPlanGenerationStatus,
    PptRecommendationConfig,
    PptSolutionPlan,
    RecommendationCandidate,
    RecommendationCategoryChoice,
    RecommendationConfirmation,
    RecommendationRun,
)
from app.modules.recommendation.ppt_schemas import (
    PptFrozenRecommendationConfig,
    PptPlanProposal,
    PptPlanProposalList,
)
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole


class MockProvider:
    """Structured provider returned in place of DeepSeek for HTTP acceptance tests."""

    fail_bands: set[int] = set()
    plan_payloads: list[dict[str, object]] = []
    gate_band: int | None = None
    gate_entered = asyncio.Event()
    gate_release = asyncio.Event()
    gate_calls = 0

    @classmethod
    def reset(cls) -> None:
        cls.fail_bands = set()
        cls.plan_payloads = []
        cls.gate_band = None
        cls.gate_entered = asyncio.Event()
        cls.gate_release = asyncio.Event()
        cls.gate_calls = 0

    @property
    def provider(self) -> str:
        return "type5-mysql-test"

    @property
    def model(self) -> str:
        return "mock"

    @property
    def prompt_version(self) -> str:
        return "type5-mysql-test"

    async def structured_completion(self, **kwargs: object) -> object:
        response_model = kwargs["response_model"]
        if response_model is RequirementAnalysis:
            return RequirementAnalysis(summary="本地集成验收", keywords=["验收"])
        payload = json.loads(str(kwargs["user_prompt"]))
        assert isinstance(payload, dict)
        self.plan_payloads.append(payload)
        band = int(payload["price_band_index"])
        if self.gate_band == band:
            type(self).gate_calls += 1
            if type(self).gate_calls == 2:
                type(self).gate_entered.set()
            await asyncio.wait_for(type(self).gate_release.wait(), timeout=5)
        if band in self.fail_bands:
            raise DeepSeekProviderError("模拟价格档失败", retryable=False)
        return PptPlanProposalList(
            plans=[
                PptPlanProposal(
                    price_band_index=band,
                    plan_no=1,
                    name=f"测试方案-{band}",
                    candidate_keys=["c1"],
                )
            ]
        )


async def _user() -> tuple[uuid.UUID, uuid.UUID, dict[str, str]]:
    user_id, role_id = uuid.uuid4(), uuid.uuid4()
    async with SessionLocal() as session:
        permissions = list(
            (
                await session.scalars(
                    select(Permission).where(
                        Permission.permission_code.in_(
                            ("recommendation:run", "recommendation:detail", "recommendation:review")
                        )
                    )
                )
            ).all()
        )
        assert len(permissions) == 3
        session.add_all(
            [
                User(
                    id=user_id, username=f"type5-mysql-{user_id}", password_hash=hash_password("x")
                ),
                Role(role_code=f"type5-mysql-{role_id}", role_name="type5 mysql test"),
            ]
        )
        await session.flush()
        role = await session.scalar(select(Role).where(Role.role_code == f"type5-mysql-{role_id}"))
        assert role is not None
        session.add_all(
            [
                UserRole(user_id=user_id, role_id=role.id),
                *[RolePermission(role_id=role.id, permission_id=item.id) for item in permissions],
            ]
        )
        await session.commit()
        return user_id, role.id, {"Authorization": f"Bearer {create_token(user_id, 1)}"}


async def _fixture(
    actor_id: uuid.UUID, *, quantities: int, bands: list[dict[str, str]]
) -> tuple[uuid.UUID, uuid.UUID, list[uuid.UUID]]:
    token = uuid.uuid4().hex
    project_id, supplier_id = uuid.uuid4(), uuid.uuid4()
    product_ids = [uuid.uuid4() for _ in range(quantities)]
    async with SessionLocal() as session:
        session.add(
            Supplier(
                id=supplier_id,
                supplier_code=f"T5{token[:12]}",
                supplier_name=f"T5 MySQL 验收供应商 {token}",
                main_brands="测试品牌",
                advantage="集成验收",
                archive_status=ArchiveStatus.ARCHIVED.value,
                cooperation_status=CooperationStatus.NORMAL.value,
            )
        )
        await session.flush()
        session.add(
            BidProject(
                id=project_id,
                project_code=f"T5{token[:12]}",
                project_name=f"T5 MySQL HTTP {token}",
                buyer_name="验收客户",
                status=BidProjectStatus.IMPORTED.value,
                import_status=BidImportStatus.NOT_REQUIRED.value,
                project_type=BidProjectType.PPT_SOLUTION.value,
                remark="这是类型五本地 MySQL HTTP 集成验收用的足够长需求说明。",
                created_by=actor_id,
            )
        )
        await session.flush()
        session.add(
            PptRecommendationConfig(
                project_id=project_id,
                recommendation_mode="SINGLE",
                price_bands=bands,
                candidate_count_per_band=quantities if quantities == 500 else 2,
                plan_count_per_band=1,
                fulfillment_deadline=None,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )
        prices = [
            Decimal("900110"),
            Decimal("900120"),
            Decimal("900210"),
            Decimal("900220"),
            Decimal("900310"),
            Decimal("900320"),
        ]
        session.add_all(
            [
                Product(
                    id=product_id,
                    source_supplier_id=supplier_id,
                    sku=f"T5-{token[:10]}-{index}",
                    product_name=f"T5 测试商品 {index}",
                    category_level1_name="测试类目",
                    category_level2_name="测试二级",
                    category_level3_name="测试三级",
                    agreement_price=(
                        prices[index] if quantities != 500 else Decimal("910000") + Decimal(index)
                    ),
                    jd_price=Decimal("150"),
                    gross_margin=Decimal("0.20"),
                    status=ProductStatus.ACTIVE.value,
                )
                for index, product_id in enumerate(product_ids)
            ]
        )
        await session.commit()
    return project_id, supplier_id, product_ids


async def _cleanup(
    *,
    project_id: uuid.UUID,
    supplier_id: uuid.UUID,
    product_ids: list[uuid.UUID],
    user_id: uuid.UUID,
    role_id: uuid.UUID,
) -> None:
    async with SessionLocal() as session:
        run_ids = list(
            (
                await session.scalars(
                    select(RecommendationRun.id).where(RecommendationRun.project_id == project_id)
                )
            ).all()
        )
        if run_ids:
            candidate_ids = list(
                (
                    await session.scalars(
                        select(RecommendationCandidate.id).where(
                            RecommendationCandidate.run_id.in_(run_ids)
                        )
                    )
                ).all()
            )
            if candidate_ids:
                await session.execute(
                    delete(RecommendationConfirmation).where(
                        RecommendationConfirmation.candidate_id.in_(candidate_ids)
                    )
                )
            await session.execute(
                delete(PptPlanGenerationStatus).where(PptPlanGenerationStatus.run_id.in_(run_ids))
            )
            await session.execute(
                delete(PptSolutionPlan).where(PptSolutionPlan.run_id.in_(run_ids))
            )
            await session.execute(
                delete(RecommendationCategoryChoice).where(
                    RecommendationCategoryChoice.run_id.in_(run_ids)
                )
            )
            await session.execute(
                delete(RecommendationCandidate).where(RecommendationCandidate.run_id.in_(run_ids))
            )
            await session.execute(
                delete(RecommendationRun).where(RecommendationRun.id.in_(run_ids))
            )
        await session.execute(
            delete(PptRecommendationConfig).where(PptRecommendationConfig.project_id == project_id)
        )
        await session.execute(
            delete(BidProjectEvent).where(BidProjectEvent.project_id == project_id)
        )
        await session.execute(delete(BidProject).where(BidProject.id == project_id))
        await session.execute(delete(Product).where(Product.id.in_(product_ids)))
        await session.execute(delete(Supplier).where(Supplier.id == supplier_id))
        await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
        await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        await session.execute(delete(Role).where(Role.id == role_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_type5_http_partial_failure_retry_snapshot_and_concurrency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recommendation_agent, "DeepSeekClient", MockProvider)
    from app.modules.recommendation.api import ppt_router

    monkeypatch.setattr(ppt_router, "DeepSeekClient", MockProvider)
    MockProvider.reset()
    MockProvider.fail_bands = {2}
    user_id, role_id, headers = await _user()
    project_id, supplier_id, product_ids = await _fixture(
        user_id,
        quantities=6,
        bands=[
            {"min_price": "900100", "max_price": "900150"},
            {"min_price": "900200", "max_price": "900250"},
            {"min_price": "900300", "max_price": "900350"},
        ],
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.post(
                f"/api/v1/recommendation-projects/{project_id}/runs", headers=headers
            )
            assert created.status_code == 200, created.text
            run_id = uuid.UUID(created.json()["data"]["id"])
            availability = await client.get(
                f"/api/v1/ppt-solution-projects/runs/{run_id}/plan-availability", headers=headers
            )
            assert availability.status_code == 200
            generated = await client.get(
                f"/api/v1/ppt-solution-projects/runs/{run_id}/plans", headers=headers
            )
            assert generated.status_code == 200
            selected_plan_id = uuid.UUID(generated.json()["data"][0]["id"])
            selected = await client.post(
                f"/api/v1/ppt-solution-projects/plans/{selected_plan_id}/select",
                headers=headers,
            )
            assert selected.status_code == 200, selected.text
            assert selected.json()["data"]["is_selected"] is True
        async with SessionLocal() as session:
            run = await session.get(RecommendationRun, run_id)
            assert run is not None and run.ppt_config_snapshot is not None
            assert (
                len(
                    (
                        await session.scalars(
                            select(RecommendationCandidate).where(
                                RecommendationCandidate.run_id == run_id
                            )
                        )
                    ).all()
                )
                >= 6
            )
            plans = list(
                (
                    await session.scalars(
                        select(PptSolutionPlan).where(PptSolutionPlan.run_id == run_id)
                    )
                ).all()
            )
            assert {item.price_band_index for item in plans} == {1, 3}
            original_ids = {item.price_band_index: item.id for item in plans}
            selected_plan = next(item for item in plans if item.id == selected_plan_id)
            assert selected_plan.is_selected is True
            assert selected_plan.selected_by == user_id
            assert selected_plan.selected_at is not None
            statuses = list(
                (
                    await session.scalars(
                        select(PptPlanGenerationStatus).where(
                            PptPlanGenerationStatus.run_id == run_id
                        )
                    )
                ).all()
            )
            assert (
                next(item for item in statuses if item.price_band_index == 2).error
                == "方案生成失败"
            )
            config = await session.scalar(
                select(PptRecommendationConfig).where(
                    PptRecommendationConfig.project_id == project_id
                )
            )
            assert config is not None
            config.recommendation_mode, config.price_bands, config.candidate_count_per_band = (
                "COMBINATION",
                [{"max_price": "999"}],
                1,
            )
            await session.commit()
        MockProvider.fail_bands = set()
        MockProvider.gate_band = 2
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            retry_one = asyncio.create_task(
                client.post(
                    f"/api/v1/ppt-solution-projects/runs/{run_id}/commands/retry-plans",
                    headers=headers,
                )
            )
            retry_two = asyncio.create_task(
                client.post(
                    f"/api/v1/ppt-solution-projects/runs/{run_id}/commands/retry-plans",
                    headers=headers,
                )
            )
            await asyncio.wait_for(MockProvider.gate_entered.wait(), timeout=5)
            MockProvider.gate_release.set()
            responses = await asyncio.wait_for(asyncio.gather(retry_one, retry_two), timeout=10)
            assert all(response.status_code == 200 for response in responses)
            repeated = await client.post(
                f"/api/v1/ppt-solution-projects/runs/{run_id}/commands/retry-plans", headers=headers
            )
            assert repeated.status_code == 200
        async with SessionLocal() as session:
            plans = list(
                (
                    await session.scalars(
                        select(PptSolutionPlan).where(PptSolutionPlan.run_id == run_id)
                    )
                ).all()
            )
            assert len(plans) == 3
            assert {item.price_band_index for item in plans} == {1, 2, 3}
            assert {
                item.price_band_index: item.id
                for item in plans
                if item.price_band_index in original_ids
            } == original_ids
            statuses = list(
                (
                    await session.scalars(
                        select(PptPlanGenerationStatus).where(
                            PptPlanGenerationStatus.run_id == run_id
                        )
                    )
                ).all()
            )
            assert {
                (item.price_band_index, item.generated_plan_count, item.error) for item in statuses
            } == {(1, 1, None), (2, 1, None), (3, 1, None)}
            assert all(len(item.candidate_ids) == 2 for item in plans)
            selected_plan = next(item for item in plans if item.id == selected_plan_id)
            assert selected_plan.is_selected is True
            assert selected_plan.selected_by == user_id
            assert selected_plan.selected_at is not None
    finally:
        await _cleanup(
            project_id=project_id,
            supplier_id=supplier_id,
            product_ids=product_ids,
            user_id=user_id,
            role_id=role_id,
        )


@pytest.mark.asyncio
async def test_type5_http_five_hundred_item_plan_uses_real_frozen_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recommendation_agent, "DeepSeekClient", MockProvider)
    MockProvider.reset()
    user_id, role_id, headers = await _user()
    project_id, supplier_id, product_ids = await _fixture(
        user_id, quantities=500, bands=[{"min_price": "910000", "max_price": "911000"}]
    )
    try:
        extra_ids = [uuid.uuid4(), uuid.uuid4()]
        async with SessionLocal() as session:
            session.add_all(
                [
                    Product(
                        id=extra_ids[0],
                        source_supplier_id=supplier_id,
                        sku=f"T5-low-{uuid.uuid4().hex}",
                        product_name="价格档以下",
                        agreement_price=Decimal("909999"),
                        jd_price=Decimal("150"),
                        gross_margin=Decimal("0.20"),
                        status=ProductStatus.ACTIVE.value,
                    ),
                    Product(
                        id=extra_ids[1],
                        source_supplier_id=supplier_id,
                        sku=f"T5-high-{uuid.uuid4().hex}",
                        product_name="价格档以上",
                        agreement_price=Decimal("911001"),
                        jd_price=Decimal("150"),
                        gross_margin=Decimal("0.20"),
                        status=ProductStatus.ACTIVE.value,
                    ),
                ]
            )
            await session.commit()
        product_ids.extend(extra_ids)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/recommendation-projects/{project_id}/runs", headers=headers
            )
            assert response.status_code == 200, response.text
            run_id = uuid.UUID(response.json()["data"]["id"])
        async with SessionLocal() as session:
            plan = await session.scalar(
                select(PptSolutionPlan).where(PptSolutionPlan.run_id == run_id)
            )
            assert plan is not None and len(plan.candidate_ids) == 500
            assert len(set(plan.candidate_ids)) == 500
            candidates = list(
                (
                    await session.scalars(
                        select(RecommendationCandidate).where(
                            RecommendationCandidate.run_id == run_id
                        )
                    )
                ).all()
            )
            by_id = {item.id: item for item in candidates}
            assert {uuid.UUID(value) for value in plan.candidate_ids}.issubset(set(by_id))
            assert all(
                Decimal("910000")
                <= Decimal(str(by_id[uuid.UUID(item)].price_snapshot["agreement_price"]))
                <= Decimal("911000")
                for item in plan.candidate_ids
            )
            frozen_config = (
                run.ppt_config_snapshot
                if (run := await session.get(RecommendationRun, run_id))
                else None
            )
            assert frozen_config is not None
            config = PptFrozenRecommendationConfig.model_validate(frozen_config)
            permitted = PptPlanAgentRunner(MockProvider()).band_candidates(
                config.price_bands[0], candidates
            )
            core_id = PptPlanAgentRunner(MockProvider()).window_key_map(permitted)["c1"].id
            assert any(
                payload["candidates"][0]["id"] == "c1" for payload in MockProvider.plan_payloads
            )
            assert plan.candidate_ids[0] == str(core_id)
            assert str(core_id) in plan.candidate_ids
            assert str(extra_ids[0]) not in plan.candidate_ids
            assert str(extra_ids[1]) not in plan.candidate_ids
    finally:
        await _cleanup(
            project_id=project_id,
            supplier_id=supplier_id,
            product_ids=product_ids,
            user_id=user_id,
            role_id=role_id,
        )
