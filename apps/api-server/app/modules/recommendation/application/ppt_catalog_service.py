"""Type-5-owned V8 catalogue and candidate-freezing workflow.

This deliberately mirrors the Type-4 V8 business contract without importing its
service or repository.  Type 5 can therefore evolve its PPT selection policy
without changing the free-recommendation path.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.transaction import transaction_scope
from app.modules.bid.domain.lifecycle import (
    BidProjectStatus,
)
from app.modules.bid.domain.lifecycle import (
    ensure_transition as ensure_bid_transition,
)
from app.modules.bid.infrastructure.models import BidProject, BidProjectEvent
from app.modules.catalog.application.product_export_columns import PRODUCT_EXPORT_COLUMN_KEYS
from app.modules.catalog.infrastructure.models import Product
from app.modules.recommendation.domain.lifecycle import ensure_transition
from app.modules.recommendation.infrastructure.models import (
    RecommendationCandidate,
    RecommendationCategoryChoice,
    RecommendationRun,
)
from app.modules.recommendation.infrastructure.ppt_repository import PptSolutionRepository
from app.modules.recommendation.ppt_schemas import (
    PptFrozenPoolPriceBandStatistics,
    PptFrozenPoolStatistics,
    PptFrozenRecommendationConfig,
)
from app.modules.recommendation.schemas import (
    CategoryCatalogItem,
    CategoryCatalogSnapshot,
    CategoryPath,
    ParsedRequirement,
)
from app.modules.recommendation.template.schemas import RecommendationRunStatus
from app.modules.supplier.infrastructure.models import Supplier

_DECIMAL_SNAPSHOT_FIELDS = frozenset(
    {
        "cost_price",
        "market_price",
        "jd_price",
        "agreement_price",
        "agreement_purchase_price",
        "profit",
        "jd_margin",
        "deduction_review",
        "gross_margin",
        "jd_self_operated_price",
        "positive_rating",
        "discount_rate",
        "price_inflation_rate",
    }
)


class PptCatalogService:
    """Independent Type-5 implementation of controlled V8 recall."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PptSolutionRepository(session)

    async def requirement_for(self, run_id: uuid.UUID) -> str:
        return (await self._run_or_404(run_id)).raw_requirement_snapshot

    async def is_cancelled(self, run_id: uuid.UUID) -> bool:
        return (await self._run_or_404(run_id)).status == RecommendationRunStatus.CANCELLED.value

    async def begin_analysis(self, run_id: uuid.UUID) -> None:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._ensure_ppt_project(await self.repository.project_for_update(run.project_id))
            self._transition(run, RecommendationRunStatus.ANALYZING)

    async def save_parsed_requirement(
        self,
        run_id: uuid.UUID,
        requirement: ParsedRequirement,
        *,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> None:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._ensure_ppt_project(await self.repository.project_for_update(run.project_id))
            if run.status == RecommendationRunStatus.QUEUED.value:
                self._transition(run, RecommendationRunStatus.ANALYZING)
            self._transition(run, RecommendationRunStatus.RETRIEVING)
            run.parsed_requirement = requirement.model_dump(mode="json")
            run.provider = provider.strip()[:64] or None
            run.model = model.strip()[:128] or None
            run.prompt_version = prompt_version.strip()[:64] or None
            run.error = None

    async def config_for_run(self, run_id: uuid.UUID) -> PptFrozenRecommendationConfig:
        run = await self._run_or_404(run_id)
        if run.ppt_config_snapshot is None:
            raise AppError(
                "PPT_RECOMMENDATION_CONFIG_SNAPSHOT_MISSING",
                "历史类型 5 任务缺少冻结配置，不能继续推品",
                409,
            )
        try:
            return PptFrozenRecommendationConfig.model_validate(run.ppt_config_snapshot)
        except ValueError as exc:
            raise AppError(
                "PPT_RECOMMENDATION_CONFIG_SNAPSHOT_INVALID", "类型 5 冻结配置无效", 409
            ) from exc

    async def create_category_catalog_snapshot(self, run_id: uuid.UUID) -> CategoryCatalogSnapshot:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            requirement = self._parsed_requirement(run)
            paths = await self.repository.category_pool(requirement)
            nodes: dict[tuple[str | None, str | None, str | None, str], int] = {}
            for path, count in paths:
                for raw_level, node_path in (
                    ("LEVEL1", (path.level1_name, None, None)),
                    ("LEVEL2", (path.level1_name, path.level2_name, None)),
                    ("LEVEL3", (path.level1_name, path.level2_name, path.level3_name)),
                ):
                    if any(node_path):
                        key = (*node_path, raw_level)
                        nodes[key] = nodes.get(key, 0) + count
            order = {"LEVEL1": 1, "LEVEL2": 2, "LEVEL3": 3}
            snapshot = CategoryCatalogSnapshot(
                generated_at=datetime.now(UTC),
                items=[
                    CategoryCatalogItem(
                        category_key=f"c{index}",
                        level1_name=node[0],
                        level2_name=node[1],
                        level3_name=node[2],
                        level=cast(Literal["LEVEL1", "LEVEL2", "LEVEL3"], node[3]),
                        candidate_count=count,
                    )
                    for index, (node, count) in enumerate(
                        sorted(
                            nodes.items(),
                            key=lambda item: (
                                order[item[0][3]],
                                item[0][0] or "",
                                item[0][1] or "",
                                item[0][2] or "",
                            ),
                        ),
                        start=1,
                    )
                ],
            )
            run.category_catalog_snapshot = snapshot.model_dump(mode="json")
        return snapshot

    async def record_catalog_category_matches(
        self, run_id: uuid.UUID, category_keys: list[str]
    ) -> None:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            snapshot = self._catalog_snapshot(run)
            by_key = {item.category_key: item for item in snapshot.items}
            keys = list(dict.fromkeys(value.strip() for value in category_keys if value.strip()))
            if unknown := [key for key in keys if key not in by_key]:
                del unknown
                raise AppError(
                    "PPT_RECOMMENDATION_CATEGORY_CATALOG_KEY_INVALID",
                    "类型 5 Agent 返回了本次真实类目清单之外的类目",
                    422,
                )
            if await self.repository.category_choices(run.id):
                raise AppError(
                    "PPT_RECOMMENDATION_CATEGORY_CHOICES_FROZEN", "类型 5 类目已冻结", 409
                )
            self.session.add_all(
                [
                    RecommendationCategoryChoice(
                        run_id=run.id,
                        level1_name=item.level1_name,
                        level2_name=item.level2_name,
                        level3_name=item.level3_name,
                        source="PPT_AI_CATALOG_MATCH",
                        candidate_count=item.candidate_count,
                    )
                    for key in keys
                    for item in [by_key[key]]
                ]
            )

    async def persist_eligible_candidates(self, run_id: uuid.UUID) -> int:
        """Freeze every Type-5 candidate after the same V8 controlled recall."""
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            if run.status != RecommendationRunStatus.RETRIEVING.value:
                raise AppError(
                    "PPT_RECOMMENDATION_RUN_NOT_RETRIEVING", "当前类型 5 任务不能保存候选", 409
                )
            if await self.repository.candidates(run.id):
                raise AppError(
                    "PPT_RECOMMENDATION_CANDIDATES_ALREADY_PERSISTED", "类型 5 候选已冻结", 409
                )
            config = await self.config_for_run(run.id)
            choices = await self.repository.category_choices(run.id)
            requirement = self._parsed_requirement(run)
            if requirement.explicit_category_keywords and not choices:
                self._transition(run, RecommendationRunStatus.NO_CANDIDATES)
                await self._restore_project(run, "PPT_RECOMMENDATION_NO_MATCHED_CATEGORY")
                return 0
            paths = [
                CategoryPath(
                    level1_name=item.level1_name,
                    level2_name=item.level2_name,
                    level3_name=item.level3_name,
                )
                for item in choices
            ]
            rows = await self.repository.all_eligible_products(requirement, paths)
            if not rows:
                self._transition(run, RecommendationRunStatus.NO_CANDIDATES)
                await self._restore_project(run, "PPT_RECOMMENDATION_NO_CANDIDATES")
                return 0
            self.session.add_all(
                [
                    self._candidate(run.id, rank, product, supplier)
                    for rank, (product, supplier) in enumerate(rows, 1)
                ]
            )
            pool_statistics = PptFrozenPoolStatistics(
                frozen_candidate_count=len(rows),
                price_bands=[
                    PptFrozenPoolPriceBandStatistics(
                        price_band_index=index,
                        min_price=band.min_price,
                        max_price=band.max_price,
                        frozen_candidate_count=sum(
                            1
                            for product, _supplier in rows
                            if (
                                self._matches_combination_source(
                                    product.agreement_price, band.max_price
                                )
                                if config.recommendation_mode == "COMBINATION"
                                else self._matches_price_band(
                                    product.agreement_price, band.min_price, band.max_price
                                )
                            )
                        ),
                        requested_item_count=band.item_count,
                    )
                    for index, band in enumerate(config.price_bands, start=1)
                ],
            )
            run.ppt_config_snapshot = config.model_copy(
                update={"frozen_pool_statistics": pool_statistics}
            ).model_dump(mode="json")
            direct_selection = (
                isinstance(run.ppt_config_snapshot, dict)
                and run.ppt_config_snapshot.get("selection_mode") in {"DIRECT", "COMBINATIONS"}
            )
            project = self._ensure_ppt_project(
                await self.repository.project_for_update(run.project_id)
            )
            self._set_project_status(
                project, BidProjectStatus.SELECTING, run.created_by, "PPT_RECOMMENDATION_POOL_READY"
            )
            # Direct selection must not expose the frozen pool as a human-selectable
            # result while the AI is still scoring it. Historical multi-plan Runs
            # retain their original ready-for-selection timing.
            if direct_selection:
                self._transition(run, RecommendationRunStatus.RANKING)
            else:
                self._transition(run, RecommendationRunStatus.CANDIDATES_READY)
                self._transition(run, RecommendationRunStatus.WAITING_CONFIRMATION)
        return len(rows)

    @staticmethod
    def _matches_price_band(
        price: Decimal | None, minimum: Decimal | None, maximum: Decimal
    ) -> bool:
        return price is not None and price <= maximum and (minimum is None or price >= minimum)

    @staticmethod
    def _matches_combination_source(price: Decimal | None, maximum: Decimal) -> bool:
        return price is not None and price > 0 and price <= maximum

    async def mark_needs_input(self, run_id: uuid.UUID, error: str) -> None:
        await self._mark_terminal(
            run_id, RecommendationRunStatus.NEEDS_INPUT, error, "PPT_RECOMMENDATION_NEEDS_INPUT"
        )

    async def mark_failed(self, run_id: uuid.UUID, error: str) -> None:
        await self._mark_terminal(
            run_id, RecommendationRunStatus.FAILED, error, "PPT_RECOMMENDATION_FAILED"
        )

    async def mark_cancelled(self, run_id: uuid.UUID) -> None:
        await self._mark_terminal(
            run_id, RecommendationRunStatus.CANCELLED, None, "PPT_RECOMMENDATION_CANCELLED"
        )

    async def record_plan_failure(self, run_id: uuid.UUID, error: str) -> None:
        """Record a safe Type-5 composition failure without exposing direct pool rows."""
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            if run.status == RecommendationRunStatus.RANKING.value:
                self._transition(run, RecommendationRunStatus.FAILED)
                run.error = error.strip()[:4000] or "类型 5 AI 商品匹配失败"
                await self._restore_project(run, "PPT_DIRECT_SELECTION_FAILED")
                return
            if run.status not in {
                RecommendationRunStatus.CANDIDATES_READY.value,
                RecommendationRunStatus.WAITING_CONFIRMATION.value,
            }:
                raise AppError(
                    "PPT_PLAN_FAILURE_STATE_INVALID", "当前类型 5 任务不能记录方案失败", 409
                )
            run.error = error.strip()[:4000] or "类型 5 方案生成失败"

    async def _mark_terminal(
        self, run_id: uuid.UUID, status: RecommendationRunStatus, error: str | None, event: str
    ) -> None:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, status)
            run.error = error.strip()[:4000] if error else None
            await self._restore_project(run, event)

    async def _restore_project(self, run: RecommendationRun, event: str) -> None:
        project = self._ensure_ppt_project(await self.repository.project_for_update(run.project_id))
        target = (
            BidProjectStatus.SELECTING
            if await self.repository.project_has_candidates(project.id)
            else BidProjectStatus.IMPORTED
        )
        self._set_project_status(project, target, run.created_by, event, allow_recovery=True)

    @staticmethod
    def _candidate(
        run_id: uuid.UUID, rank: int, product: Product, supplier: Supplier
    ) -> RecommendationCandidate:
        product_snapshot: dict[str, object | None] = {"id": str(product.id)}
        price_snapshot: dict[str, object | None] = {}
        for field in PRODUCT_EXPORT_COLUMN_KEYS:
            if field == "supplier_name":
                continue
            value = getattr(product, field)
            if field in _DECIMAL_SNAPSHOT_FIELDS:
                price_snapshot[field] = str(value) if value is not None else None
            else:
                product_snapshot[field] = PptCatalogService._snapshot_value(value)
        return RecommendationCandidate(
            run_id=run_id,
            product_id=product.id,
            rank=rank,
            product_snapshot=product_snapshot,
            supplier_snapshot={
                "id": str(supplier.id),
                "supplier_code": supplier.supplier_code,
                "supplier_name": supplier.supplier_name,
                "archive_status": supplier.archive_status,
                "cooperation_status": supplier.cooperation_status,
            },
            price_snapshot=price_snapshot,
        )

    @staticmethod
    def _snapshot_value(value: object) -> object:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @staticmethod
    def _transition(run: RecommendationRun, target: RecommendationRunStatus) -> None:
        ensure_transition(run.status, target)
        run.status = target.value

    @staticmethod
    def _parsed_requirement(run: RecommendationRun) -> ParsedRequirement:
        if run.parsed_requirement is None:
            raise AppError("PPT_RECOMMENDATION_REQUIREMENT_NOT_PARSED", "类型 5 需求尚未解析", 409)
        return ParsedRequirement.model_validate(run.parsed_requirement)

    @staticmethod
    def _catalog_snapshot(run: RecommendationRun) -> CategoryCatalogSnapshot:
        if run.category_catalog_snapshot is None:
            raise AppError(
                "PPT_RECOMMENDATION_CATEGORY_CATALOG_NOT_FOUND", "类型 5 真实类目清单不存在", 409
            )
        return CategoryCatalogSnapshot.model_validate(run.category_catalog_snapshot)

    async def _run_or_404_for_update(self, run_id: uuid.UUID) -> RecommendationRun:
        run = await self.repository.run_for_update(run_id)
        if run is None:
            raise AppError("PPT_RECOMMENDATION_RUN_NOT_FOUND", "类型 5 推品任务不存在", 404)
        return run

    async def _run_or_404(self, run_id: uuid.UUID) -> RecommendationRun:
        run = await self.repository.run(run_id)
        if run is None:
            raise AppError("PPT_RECOMMENDATION_RUN_NOT_FOUND", "类型 5 推品任务不存在", 404)
        return run

    @staticmethod
    def _ensure_ppt_project(project: BidProject | None) -> BidProject:
        if project is None:
            raise AppError("PPT_SOLUTION_PROJECT_NOT_FOUND", "PPT 方案项目不存在", 404)
        return project

    def _set_project_status(
        self,
        project: BidProject,
        target: BidProjectStatus,
        actor_id: uuid.UUID,
        event: str,
        *,
        allow_recovery: bool = False,
    ) -> None:
        if project.status == target.value:
            return
        before = project.status
        if not (
            allow_recovery
            and before == BidProjectStatus.MATCHING.value
            and target in {BidProjectStatus.IMPORTED, BidProjectStatus.SELECTING}
        ):
            ensure_bid_transition(before, target)
        project.status = target.value
        project.updated_by = actor_id
        self.session.add(
            BidProjectEvent(
                project_id=project.id,
                actor_id=actor_id,
                event_type=event,
                from_status=before,
                to_status=target.value,
                note="类型 5 独立受控选品链路",
            )
        )
