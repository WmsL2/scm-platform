from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams
from app.core.transaction import transaction_scope
from app.modules.bid.domain.lifecycle import (
    BidProjectStatus,
    BidProjectType,
)
from app.modules.bid.domain.lifecycle import (
    ensure_transition as ensure_bid_project_transition,
)
from app.modules.bid.infrastructure.models import BidProject, BidProjectEvent
from app.modules.bid.schemas import BidProjectStatusResponse
from app.modules.catalog.application.product_export_columns import PRODUCT_EXPORT_COLUMN_KEYS
from app.modules.catalog.infrastructure.models import Product
from app.modules.recommendation.domain.lifecycle import ensure_transition
from app.modules.recommendation.infrastructure.models import (
    PptRecommendationConfig,
    RecommendationCandidate,
    RecommendationCategoryChoice,
    RecommendationConfirmation,
    RecommendationRun,
)
from app.modules.recommendation.infrastructure.repository import RecommendationRepository
from app.modules.recommendation.schemas import (
    BatchConfirmationRequest,
    BatchConfirmationResult,
    CandidateRankInput,
    CategoryCatalogItem,
    CategoryCatalogSnapshot,
    CategoryChoiceInput,
    CategoryPath,
    CategoryPoolItem,
    ConfirmationUpdateRequest,
    FactoryDirectStatus,
    ParsedRequirement,
    PersistCandidatesRequest,
    ProductCandidateRow,
    RecommendationCandidatePageResponse,
    RecommendationCandidateResponse,
    RecommendationConfirmationResponse,
    RecommendationRunResponse,
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


class RecommendationService:
    """B-owned deterministic state and data boundary for free recommendation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = RecommendationRepository(session)

    async def create_run(
        self, project_id: uuid.UUID, actor_id: uuid.UUID
    ) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            project = await self.repository.recommendation_project_for_update(project_id)
            if project is None:
                raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
            requirement = (project.remark or "").strip()
            if len(requirement) < 20:
                raise AppError(
                    "FREE_RECOMMENDATION_REMARK_REQUIRED",
                    "自由推品项目必须填写至少二十字需求说明",
                    409,
                )
            if project.project_type == BidProjectType.FREE_RECOMMENDATION.value:
                mapping_row = await self.repository.latest_template_mapping(project_id)
                if (
                    mapping_row is None
                    or mapping_row[0].confirmed_by is None
                    or mapping_row[0].confirmed_at is None
                ):
                    raise AppError(
                        "RECOMMENDATION_TEMPLATE_MAPPING_NOT_CONFIRMED",
                        "请先确认最新推品模板映射",
                        409,
                    )
            if project.project_type == BidProjectType.PPT_SOLUTION.value:
                config = await self.session.scalar(
                    select(PptRecommendationConfig).where(
                        PptRecommendationConfig.project_id == project.id
                    )
                )
                if config is None:
                    raise AppError(
                        "PPT_RECOMMENDATION_CONFIG_REQUIRED",
                        "请先填写类型 5 的推品方式、价格档和生成数量",
                        409,
                    )
                # Type-5 V8 recall receives exactly the customer requirement, just as Type 4.
                # Its saved price bands are deliberately consumed only by the later plan AI.
            if project.status in {
                BidProjectStatus.READY.value,
                BidProjectStatus.EXPORTED.value,
                BidProjectStatus.SUBMITTED.value,
                BidProjectStatus.WON.value,
                BidProjectStatus.LOST.value,
            }:
                raise AppError(
                    "RECOMMENDATION_PROJECT_SELECTION_COMPLETED",
                    "项目已完成选品，不能重新生成推荐；如需调整请先返回待选品状态",
                    409,
                )
            self._set_project_status(
                project,
                BidProjectStatus.MATCHING,
                actor_id=actor_id,
                event_type="RECOMMENDATION_STARTED",
                allow_selecting_restart=True,
            )
            run = RecommendationRun(
                project_id=project.id,
                status=RecommendationRunStatus.QUEUED.value,
                raw_requirement_snapshot=requirement,
                created_by=actor_id,
            )
            self.session.add(run)
            await self.session.flush()
            await self.session.refresh(run)
        return self._run_response(run)

    async def list_runs(self, project_id: uuid.UUID) -> list[RecommendationRunResponse]:
        project = await self.repository.recommendation_project_for_update(project_id)
        if project is None:
            raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
        return [self._run_response(run) for run in await self.repository.runs(project_id)]

    async def project_type_for_run(self, run_id: uuid.UUID) -> BidProjectType:
        run = await self._run_or_404(run_id)
        project = await self.repository.recommendation_project_for_update(run.project_id)
        if project is None:
            raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
        return BidProjectType(project.project_type)

    async def ppt_recommendation_config_for_run(self, run_id: uuid.UUID) -> PptRecommendationConfig:
        run = await self._run_or_404(run_id)
        config = await self.session.scalar(
            select(PptRecommendationConfig).where(
                PptRecommendationConfig.project_id == run.project_id
            )
        )
        if config is None:
            raise AppError("PPT_RECOMMENDATION_CONFIG_REQUIRED", "类型 5 推品配置不存在", 409)
        return config

    async def get_run(self, run_id: uuid.UUID) -> RecommendationRunResponse:
        run = await self.repository.run_by_id(run_id)
        if run is None:
            raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
        return self._run_response(run)

    # The following methods are C's application-service contract.  C must never access the
    # repository or database directly; all AI output is validated by the DTOs below.
    async def begin_analysis(self, run_id: uuid.UUID) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.ANALYZING)
        return self._run_response(run)

    async def save_parsed_requirement(
        self,
        run_id: uuid.UUID,
        requirement: ParsedRequirement,
        *,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            if run.status == RecommendationRunStatus.QUEUED.value:
                self._transition(run, RecommendationRunStatus.ANALYZING)
            self._transition(run, RecommendationRunStatus.RETRIEVING)
            run.parsed_requirement = requirement.model_dump(mode="json")
            run.provider = provider.strip()[:64] or None
            run.model = model.strip()[:128] or None
            run.prompt_version = prompt_version.strip()[:64] or None
            run.error = None
        return self._run_response(run)

    async def category_pool(self, run_id: uuid.UUID) -> list[CategoryPoolItem]:
        run = await self._run_or_404(run_id)
        requirement = self._parsed_requirement(run)
        return [
            CategoryPoolItem(
                level1_name=path.level1_name,
                level2_name=path.level2_name,
                level3_name=path.level3_name,
                candidate_count=count,
            )
            for path, count in await self.repository.category_pool(
                requirement, requirement.search_keywords or requirement.category_intents
            )
        ]

    async def create_category_catalog_snapshot(self, run_id: uuid.UUID) -> CategoryCatalogSnapshot:
        """Freeze actual selectable category-tree nodes before the model maps request terms."""
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            requirement = self._parsed_requirement(run)
            paths = await self.repository.category_pool(
                requirement,
                include_category_terms=False,
            )
            category_nodes: dict[tuple[str | None, str | None, str | None, str], int] = {}
            for path, count in paths:
                for raw_level, node_path in (
                    ("LEVEL1", (path.level1_name, None, None)),
                    ("LEVEL2", (path.level1_name, path.level2_name, None)),
                    ("LEVEL3", (path.level1_name, path.level2_name, path.level3_name)),
                ):
                    if not any(node_path):
                        continue
                    level = cast(Literal["LEVEL1", "LEVEL2", "LEVEL3"], raw_level)
                    key = (*node_path, level)
                    category_nodes[key] = category_nodes.get(key, 0) + count
            level_order = {"LEVEL1": 1, "LEVEL2": 2, "LEVEL3": 3}
            ordered_nodes = sorted(
                category_nodes.items(),
                key=lambda item: (
                    level_order[item[0][3]],
                    item[0][0] or "",
                    item[0][1] or "",
                    item[0][2] or "",
                ),
            )
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
                    for index, (node, count) in enumerate(ordered_nodes, start=1)
                ],
            )
            run.category_catalog_snapshot = snapshot.model_dump(mode="json")
        return snapshot

    async def record_catalog_category_matches(
        self, run_id: uuid.UUID, category_keys: list[str]
    ) -> None:
        """Persist only category paths selected from this Run's immutable server catalogue."""
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            snapshot = self._category_catalog_snapshot(run)
            items_by_key = {item.category_key: item for item in snapshot.items}
            normalized_keys = list(
                dict.fromkeys(key.strip() for key in category_keys if key.strip())
            )
            unknown_keys = [key for key in normalized_keys if key not in items_by_key]
            if unknown_keys:
                raise AppError(
                    "RECOMMENDATION_CATEGORY_CATALOG_KEY_INVALID",
                    "Agent 返回了本次真实类目清单之外的类目",
                    422,
                )
            existing = await self.repository.category_choices(run_id)
            if existing:
                raise AppError(
                    "RECOMMENDATION_CATEGORY_CHOICES_ALREADY_RECORDED",
                    "本次推品的类目匹配结果已经冻结",
                    409,
                )
            self.session.add_all(
                [
                    RecommendationCategoryChoice(
                        run_id=run.id,
                        level1_name=item.level1_name,
                        level2_name=item.level2_name,
                        level3_name=item.level3_name,
                        source="AI_CATALOG_MATCH",
                        candidate_count=item.candidate_count,
                    )
                    for key in normalized_keys
                    for item in [items_by_key[key]]
                ]
            )

    async def record_category_choices(
        self, run_id: uuid.UUID, choices: list[CategoryChoiceInput]
    ) -> None:
        if not choices or len(choices) > 40:
            raise AppError(
                "RECOMMENDATION_CATEGORY_CHOICES_INVALID", "类目选择数量必须在 1 到 40 之间", 422
            )
        async with transaction_scope(self.session):
            await self._run_or_404_for_update(run_id)
            self.session.add_all(
                [
                    RecommendationCategoryChoice(
                        run_id=run_id,
                        level1_name=choice.level1_name,
                        level2_name=choice.level2_name,
                        level3_name=choice.level3_name,
                        source=choice.source.strip(),
                        reason=choice.reason.strip() if choice.reason else None,
                        candidate_count=choice.candidate_count,
                    )
                    for choice in choices
                ]
            )

    async def search_products(
        self,
        run_id: uuid.UUID,
        category_paths: list[CategoryPath],
        *,
        keywords: list[str] | None = None,
        preferred_brands: list[str] | None = None,
    ) -> list[ProductCandidateRow]:
        if not category_paths or len(category_paths) > 40:
            raise AppError(
                "RECOMMENDATION_CATEGORY_CHOICES_INVALID", "类目选择数量必须在 1 到 40 之间", 422
            )
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            if run.status == RecommendationRunStatus.RETRIEVING.value:
                self._transition(run, RecommendationRunStatus.RANKING)
            elif run.status != RecommendationRunStatus.RANKING.value:
                raise AppError(
                    "RECOMMENDATION_RUN_NOT_RETRIEVING", "当前推品任务不能查询候选商品", 409
                )
            requirement = self._parsed_requirement(run)
            rows = await self.repository.eligible_products(
                requirement,
                category_paths,
                keywords=keywords or requirement.search_keywords,
                preferred_brands=preferred_brands or requirement.preferred_brands,
            )
        return [self._product_candidate_row(product, supplier) for product, supplier in rows]

    async def persist_ranked_candidates(
        self, run_id: uuid.UUID, payload: PersistCandidatesRequest
    ) -> list[RecommendationCandidateResponse]:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            if run.status != RecommendationRunStatus.RANKING.value:
                raise AppError(
                    "RECOMMENDATION_RUN_NOT_RANKING", "当前推品任务不能保存候选商品", 409
                )
            existing = await self.repository.candidates(run_id)
            if existing:
                raise AppError(
                    "RECOMMENDATION_CANDIDATES_ALREADY_PERSISTED", "候选商品已保存，不能覆盖", 409
                )
            requirement = self._parsed_requirement(run)
            ids = [item.product_id for item in payload.candidates]
            eligible = await self.repository.eligible_products_by_ids(requirement, ids)
            product_rows = {product.id: (product, supplier) for product, supplier in eligible}
            rejected = [str(product_id) for product_id in ids if product_id not in product_rows]
            if rejected:
                raise AppError(
                    "RECOMMENDATION_CANDIDATE_INELIGIBLE",
                    "候选商品不存在或已不满足当前筛选条件",
                    409,
                )
            candidates = [
                self._candidate(run.id, item, *product_rows[item.product_id])
                for item in payload.candidates
            ]
            self.session.add_all(candidates)
            self._transition(run, RecommendationRunStatus.CANDIDATES_READY)
            self._transition(run, RecommendationRunStatus.WAITING_CONFIRMATION)
            project = await self.repository.recommendation_project_for_update(run.project_id)
            if project is None:
                raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
            self._set_project_status(
                project,
                BidProjectStatus.SELECTING,
                actor_id=run.created_by,
                event_type="RECOMMENDATION_CANDIDATES_READY",
            )
            await self.session.flush()
            for candidate in candidates:
                await self.session.refresh(candidate)
        return [self._candidate_response(candidate, None) for candidate in candidates]

    async def persist_all_eligible_candidates(self, run_id: uuid.UUID) -> int:
        """Persist every product satisfying the Type-4 hard constraints."""
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            if run.status != RecommendationRunStatus.RETRIEVING.value:
                raise AppError(
                    "RECOMMENDATION_RUN_NOT_RETRIEVING", "当前推品任务不能保存候选商品", 409
                )
            if await self.repository.candidates(run_id):
                raise AppError(
                    "RECOMMENDATION_CANDIDATES_ALREADY_PERSISTED", "候选商品已保存，不能覆盖", 409
                )
            requirement = self._parsed_requirement(run)
            category_paths: list[CategoryPath] = []
            if (
                requirement.requirement_version in {"v7", "v8"}
                and requirement.explicit_category_keywords
            ):
                category_paths = [
                    CategoryPath(
                        level1_name=choice.level1_name,
                        level2_name=choice.level2_name,
                        level3_name=choice.level3_name,
                    )
                    for choice in await self.repository.category_choices(run.id)
                ]
                if not category_paths:
                    self._transition(run, RecommendationRunStatus.NO_CANDIDATES)
                    await self._restore_project_after_terminal_run(
                        run, "RECOMMENDATION_NO_MATCHED_CATEGORY"
                    )
                    return 0
            rows = await self.repository.all_eligible_products(requirement, category_paths)
            if not rows:
                self._transition(run, RecommendationRunStatus.NO_CANDIDATES)
                await self._restore_project_after_terminal_run(run, "RECOMMENDATION_NO_CANDIDATES")
                return 0
            candidates = [
                self._candidate_from_product(run.id, rank, product, supplier)
                for rank, (product, supplier) in enumerate(rows, start=1)
            ]
            self.session.add_all(candidates)
            self._transition(run, RecommendationRunStatus.CANDIDATES_READY)
            self._transition(run, RecommendationRunStatus.WAITING_CONFIRMATION)
            project = await self.repository.recommendation_project_for_update(run.project_id)
            if project is None:
                raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
            self._set_project_status(
                project,
                BidProjectStatus.SELECTING,
                actor_id=run.created_by,
                event_type="RECOMMENDATION_CANDIDATES_READY",
            )
            await self.session.flush()
        return len(candidates)

    async def persist_ppt_eligible_candidates(self, run_id: uuid.UUID) -> int:
        """Freeze the complete Type-5 price-band pool without applying Type-4 limits.

        Type 4 persists its own hard-filter result set.  Type 5 instead keeps every
        formally eligible product in the configured agreement-price bands, so its
        per-plan product quantity never acts as a candidate-pool limit.
        """
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            # Type 5 no longer sends a bounded product list to the model for
            # ranking. Its runner reaches this point directly after controlled
            # category selection, while the Run is still RETRIEVING. This branch
            # belongs only to the Type-5 persistence path; Type 4 is unchanged.
            if run.status == RecommendationRunStatus.RETRIEVING.value:
                self._transition(run, RecommendationRunStatus.RANKING)
            elif run.status != RecommendationRunStatus.RANKING.value:
                raise AppError(
                    "RECOMMENDATION_RUN_NOT_RANKING", "当前推品任务不能保存候选商品", 409
                )
            if await self.repository.candidates(run_id):
                raise AppError(
                    "RECOMMENDATION_CANDIDATES_ALREADY_PERSISTED", "候选商品已保存，不能覆盖", 409
                )
            config = await self.session.scalar(
                select(PptRecommendationConfig).where(
                    PptRecommendationConfig.project_id == run.project_id
                )
            )
            if config is None:
                raise AppError("PPT_RECOMMENDATION_CONFIG_REQUIRED", "类型 5 推品配置不存在", 409)
            category_paths = [
                CategoryPath(
                    level1_name=choice.level1_name,
                    level2_name=choice.level2_name,
                    level3_name=choice.level3_name,
                )
                for choice in await self.repository.category_choices(run.id)
            ]
            if not category_paths:
                self._transition(run, RecommendationRunStatus.NO_CANDIDATES)
                await self._restore_project_after_terminal_run(
                    run, "PPT_RECOMMENDATION_NO_MATCHED_CATEGORY"
                )
                return 0
            requirement = self._parsed_requirement(run)
            rows = [
                (product, supplier)
                for product, supplier in await self.repository.all_eligible_products(
                    requirement, category_paths
                )
                if self._matches_ppt_price_bands(product.agreement_price, config.price_bands)
            ]
            if not rows:
                self._transition(run, RecommendationRunStatus.NO_CANDIDATES)
                await self._restore_project_after_terminal_run(
                    run, "PPT_RECOMMENDATION_NO_CANDIDATES"
                )
                return 0
            candidates = [
                self._candidate_from_product(run.id, rank, product, supplier)
                for rank, (product, supplier) in enumerate(rows, start=1)
            ]
            self.session.add_all(candidates)
            self._transition(run, RecommendationRunStatus.CANDIDATES_READY)
            self._transition(run, RecommendationRunStatus.WAITING_CONFIRMATION)
            project = await self.repository.recommendation_project_for_update(run.project_id)
            if project is None:
                raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
            self._set_project_status(
                project,
                BidProjectStatus.SELECTING,
                actor_id=run.created_by,
                event_type="PPT_RECOMMENDATION_POOL_READY",
            )
            await self.session.flush()
        return len(candidates)

    @staticmethod
    def _matches_ppt_price_bands(
        price: Decimal | None, price_bands: list[dict[str, object]]
    ) -> bool:
        if price is None:
            return False
        for band in price_bands:
            try:
                maximum = Decimal(str(band.get("max_price")))
                minimum_raw = band.get("min_price")
                minimum = Decimal(str(minimum_raw)) if minimum_raw is not None else None
            except (ArithmeticError, ValueError):
                continue
            if price <= maximum and (minimum is None or price >= minimum):
                return True
        return False

    async def mark_no_candidates(self, run_id: uuid.UUID) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.NO_CANDIDATES)
            await self._restore_project_after_terminal_run(run, "RECOMMENDATION_NO_CANDIDATES")
        return self._run_response(run)

    async def mark_needs_input(self, run_id: uuid.UUID, error: str) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.NEEDS_INPUT)
            run.error = error.strip()[:4000] or None
            await self._restore_project_after_terminal_run(run, "RECOMMENDATION_NEEDS_INPUT")
        return self._run_response(run)

    async def mark_failed(self, run_id: uuid.UUID, error: str) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.FAILED)
            run.error = error.strip()[:4000] or None
            await self._restore_project_after_terminal_run(run, "RECOMMENDATION_FAILED")
        return self._run_response(run)

    async def mark_cancelled(self, run_id: uuid.UUID) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.CANCELLED)
            await self._restore_project_after_terminal_run(run, "RECOMMENDATION_CANCELLED")
        return self._run_response(run)

    async def _restore_project_after_terminal_run(
        self, run: RecommendationRun, event_type: str
    ) -> None:
        project = await self.repository.recommendation_project_for_update(run.project_id)
        if project is None:
            raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
        target = (
            BidProjectStatus.SELECTING
            if await self.repository.project_has_candidates(project.id)
            else BidProjectStatus.IMPORTED
        )
        self._set_project_status(
            project,
            target,
            actor_id=run.created_by,
            event_type=event_type,
            note="本次推荐未生成新候选，项目已恢复到可继续处理的状态",
            allow_run_recovery=True,
        )

    async def list_candidates(
        self, run_id: uuid.UUID, page_params: PageParams | None = None
    ) -> list[RecommendationCandidateResponse] | RecommendationCandidatePageResponse:
        await self._run_or_404(run_id)
        if page_params is not None:
            rows, total, confirmed_total = await self.repository.candidate_page(
                run_id, page=page_params.page, page_size=page_params.page_size
            )
            return RecommendationCandidatePageResponse(
                items=[
                    self._candidate_response(candidate, confirmation)
                    for candidate, confirmation in rows
                ],
                total=total,
                page=page_params.page,
                page_size=page_params.page_size,
                confirmed_total=confirmed_total,
                unconfirmed_total=total - confirmed_total,
            )
        return [
            self._candidate_response(candidate, confirmation)
            for candidate, confirmation in await self.repository.candidates(run_id)
        ]

    async def confirm_candidate(
        self,
        candidate_id: uuid.UUID,
        payload: ConfirmationUpdateRequest,
        actor_id: uuid.UUID,
    ) -> RecommendationConfirmationResponse:
        async with transaction_scope(self.session):
            row = await self.repository.candidate_with_run_for_update(candidate_id)
            if row is None:
                raise AppError("RECOMMENDATION_CANDIDATE_NOT_FOUND", "推品候选不存在", 404)
            candidate, run, confirmation = row
            await self._ensure_selection_editable(run)
            if run.status not in {
                RecommendationRunStatus.CANDIDATES_READY.value,
                RecommendationRunStatus.WAITING_CONFIRMATION.value,
                RecommendationRunStatus.CONFIRMED.value,
                RecommendationRunStatus.EXPORTED.value,
            }:
                raise AppError(
                    "RECOMMENDATION_CONFIRMATION_NOT_ALLOWED", "当前推品任务不能人工确认", 409
                )
            requirement = self._parsed_requirement(run)
            eligible = await self.repository.eligible_products_by_ids(
                requirement, [candidate.product_id]
            )
            if len(eligible) != 1:
                raise AppError(
                    "RECOMMENDATION_CANDIDATE_INELIGIBLE", "候选商品或供应商当前不可用", 409
                )
            if confirmation is None:
                confirmation = RecommendationConfirmation(candidate_id=candidate.id)
                self.session.add(confirmation)
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(
                    confirmation,
                    field,
                    value.value if field == "factory_direct" else value,
                )
            confirmation.confirmed_by = actor_id
            confirmation.confirmed_at = datetime.now(UTC).replace(tzinfo=None)
            if run.status in {
                RecommendationRunStatus.CANDIDATES_READY.value,
                RecommendationRunStatus.WAITING_CONFIRMATION.value,
            }:
                self._transition(run, RecommendationRunStatus.CONFIRMED)
            elif run.status == RecommendationRunStatus.EXPORTED.value:
                self._transition(run, RecommendationRunStatus.CONFIRMED)
            await self.session.flush()
            await self.session.refresh(confirmation)
        return self._confirmation_response(confirmation)

    async def remove_confirmation(self, candidate_id: uuid.UUID, actor_id: uuid.UUID) -> bool:
        async with transaction_scope(self.session):
            row = await self.repository.candidate_with_run_for_update(candidate_id)
            if row is None:
                raise AppError("RECOMMENDATION_CANDIDATE_NOT_FOUND", "推荐候选不存在", 404)
            candidate, run, confirmation = row
            if confirmation is None:
                return True
            project = await self.repository.recommendation_project_for_update(run.project_id)
            if project is None:
                raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
            if project.status != BidProjectStatus.SELECTING.value:
                raise AppError(
                    "RECOMMENDATION_SELECTION_LOCKED",
                    "选品已经完成，不能直接移除；请先返回待选品状态",
                    409,
                )
            await self.session.delete(confirmation)
            await self.session.flush()
            remaining = await self.repository.confirmed_candidates_for_export(run.id)
            if not remaining and run.status == RecommendationRunStatus.CONFIRMED.value:
                self._transition(run, RecommendationRunStatus.WAITING_CONFIRMATION)
            project.updated_by = actor_id
        return True

    async def confirm_candidates(
        self,
        run_id: uuid.UUID,
        payload: BatchConfirmationRequest,
        actor_id: uuid.UUID,
    ) -> BatchConfirmationResult:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            await self._ensure_selection_editable(run)
            if run.status not in {
                RecommendationRunStatus.CANDIDATES_READY.value,
                RecommendationRunStatus.WAITING_CONFIRMATION.value,
                RecommendationRunStatus.CONFIRMED.value,
                RecommendationRunStatus.EXPORTED.value,
            }:
                raise AppError(
                    "RECOMMENDATION_CONFIRMATION_NOT_ALLOWED", "当前推品任务不能人工确认", 409
                )
            rows = (
                await self.repository.unconfirmed_candidates_for_update(
                    run_id, payload.excluded_candidate_ids
                )
                if payload.select_all
                else await self.repository.candidates_with_confirmations_for_update(
                    run_id, payload.candidate_ids
                )
            )
            if not payload.select_all and len(rows) != len(payload.candidate_ids):
                raise AppError(
                    "RECOMMENDATION_CANDIDATE_NOT_FOUND",
                    "部分推品候选不存在或不属于当前任务",
                    404,
                )
            requirement = self._parsed_requirement(run)
            product_ids = [candidate.product_id for candidate, _ in rows]
            eligible = await self.repository.eligible_products_by_ids(requirement, product_ids)
            if len(eligible) != len(product_ids):
                raise AppError(
                    "RECOMMENDATION_CANDIDATE_INELIGIBLE",
                    "部分候选商品或供应商当前不可用",
                    409,
                )
            confirmed_at = datetime.now(UTC).replace(tzinfo=None)
            confirmations: list[RecommendationConfirmation] = []
            for candidate, confirmation in rows:
                if confirmation is None:
                    confirmation = RecommendationConfirmation(candidate_id=candidate.id)
                    self.session.add(confirmation)
                confirmation.confirmed_by = actor_id
                confirmation.confirmed_at = confirmed_at
                confirmations.append(confirmation)
            if run.status in {
                RecommendationRunStatus.CANDIDATES_READY.value,
                RecommendationRunStatus.WAITING_CONFIRMATION.value,
            }:
                self._transition(run, RecommendationRunStatus.CONFIRMED)
            elif run.status == RecommendationRunStatus.EXPORTED.value:
                self._transition(run, RecommendationRunStatus.CONFIRMED)
            await self.session.flush()
        return BatchConfirmationResult(confirmed_count=len(confirmations))

    async def _ensure_selection_editable(self, run: RecommendationRun) -> BidProject:
        project = await self.repository.recommendation_project_for_update(run.project_id)
        if project is None:
            raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
        if project.status != BidProjectStatus.SELECTING.value:
            raise AppError(
                "RECOMMENDATION_SELECTION_LOCKED",
                "选品已经完成，不能直接修改；请先返回待选品状态",
                409,
            )
        return project

    async def complete_selection(
        self, project_id: uuid.UUID, run_id: uuid.UUID, actor_id: uuid.UUID
    ) -> BidProjectStatusResponse:
        async with transaction_scope(self.session):
            project = await self.repository.recommendation_project_for_update(project_id)
            if project is None:
                raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
            run = await self._run_or_404_for_update(run_id)
            if run.project_id != project.id:
                raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
            if run.status not in {
                RecommendationRunStatus.CONFIRMED.value,
                RecommendationRunStatus.EXPORTED.value,
            }:
                raise AppError(
                    "RECOMMENDATION_SELECTION_CONFIRMATION_REQUIRED",
                    "至少确认一件候选商品后才能完成选品",
                    409,
                )
            confirmed = await self.repository.confirmed_candidates_for_export(run.id)
            if not confirmed:
                raise AppError(
                    "RECOMMENDATION_SELECTION_CONFIRMATION_REQUIRED",
                    "至少确认一件候选商品后才能完成选品",
                    409,
                )
            self._set_project_status(
                project,
                BidProjectStatus.READY,
                actor_id=actor_id,
                event_type="RECOMMENDATION_SELECTION_COMPLETED",
                note=f"人工完成选品，共确认 {len(confirmed)} 件商品",
            )
            await self.session.flush()
        return BidProjectStatusResponse(
            id=project.id,
            status=BidProjectStatus(project.status),
            submitted_file_id=project.submitted_file_id,
        )

    async def reopen_selection(
        self, project_id: uuid.UUID, run_id: uuid.UUID, actor_id: uuid.UUID
    ) -> BidProjectStatusResponse:
        async with transaction_scope(self.session):
            project = await self.repository.recommendation_project_for_update(project_id)
            if project is None:
                raise AppError("RECOMMENDATION_PROJECT_NOT_FOUND", "推品项目不存在", 404)
            run = await self._run_or_404_for_update(run_id)
            if run.project_id != project.id:
                raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
            if project.status not in {
                BidProjectStatus.READY.value,
                BidProjectStatus.EXPORTED.value,
            }:
                raise AppError(
                    "RECOMMENDATION_SELECTION_REOPEN_NOT_ALLOWED",
                    "当前项目状态不能返回调整选品",
                    409,
                )
            confirmed = await self.repository.confirmed_candidates_for_export(run.id)
            if not confirmed:
                raise AppError(
                    "RECOMMENDATION_SELECTION_CONFIRMATION_REQUIRED",
                    "当前任务没有已选商品，不能返回调整",
                    409,
                )
            if run.status == RecommendationRunStatus.EXPORTED.value:
                self._transition(run, RecommendationRunStatus.CONFIRMED)
            self._set_project_status(
                project,
                BidProjectStatus.SELECTING,
                actor_id=actor_id,
                event_type="RECOMMENDATION_SELECTION_REOPENED",
                note="返回人工选品，后续导出将生成新版本",
                allow_selection_reopen=True,
            )
            await self.session.flush()
        return BidProjectStatusResponse(
            id=project.id,
            status=BidProjectStatus(project.status),
            submitted_file_id=project.submitted_file_id,
        )

    async def _run_or_404_for_update(self, run_id: uuid.UUID) -> RecommendationRun:
        run = await self.repository.run_for_update(run_id)
        if run is None:
            raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
        return run

    async def _run_or_404(self, run_id: uuid.UUID) -> RecommendationRun:
        run = await self.repository.run_by_id(run_id)
        if run is None:
            raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
        return run

    @staticmethod
    def _transition(run: RecommendationRun, target: RecommendationRunStatus) -> None:
        ensure_transition(run.status, target)
        run.status = target.value

    def _set_project_status(
        self,
        project: BidProject,
        target: BidProjectStatus,
        *,
        actor_id: uuid.UUID,
        event_type: str,
        note: str | None = None,
        allow_selecting_restart: bool = False,
        allow_selection_reopen: bool = False,
        allow_run_recovery: bool = False,
    ) -> None:
        if project.status == target.value:
            return
        previous = project.status
        if (
            not (
                allow_selecting_restart
                and previous == BidProjectStatus.SELECTING.value
                and target == BidProjectStatus.MATCHING
            )
            and not (
                allow_selection_reopen
                and previous in {BidProjectStatus.READY.value, BidProjectStatus.EXPORTED.value}
                and target == BidProjectStatus.SELECTING
            )
            and not (
                allow_run_recovery
                and previous == BidProjectStatus.MATCHING.value
                and target in {BidProjectStatus.IMPORTED, BidProjectStatus.SELECTING}
            )
        ):
            ensure_bid_project_transition(previous, target)
        project.status = target.value
        project.updated_by = actor_id
        self.session.add(
            BidProjectEvent(
                project_id=project.id,
                actor_id=actor_id,
                event_type=event_type,
                from_status=previous,
                to_status=target.value,
                note=note,
            )
        )

    @staticmethod
    def _parsed_requirement(run: RecommendationRun) -> ParsedRequirement:
        if run.parsed_requirement is None:
            raise AppError("RECOMMENDATION_REQUIREMENT_NOT_PARSED", "推品需求尚未完成解析", 409)
        return ParsedRequirement.model_validate(run.parsed_requirement)

    @staticmethod
    def _category_catalog_snapshot(run: RecommendationRun) -> CategoryCatalogSnapshot:
        if run.category_catalog_snapshot is None:
            raise AppError(
                "RECOMMENDATION_CATEGORY_CATALOG_NOT_FOUND",
                "本次推品尚未生成真实类目清单",
                409,
            )
        return CategoryCatalogSnapshot.model_validate(run.category_catalog_snapshot)

    @staticmethod
    def _run_response(run: RecommendationRun) -> RecommendationRunResponse:
        return RecommendationRunResponse(
            id=run.id,
            project_id=run.project_id,
            status=RecommendationRunStatus(run.status),
            raw_requirement_snapshot=run.raw_requirement_snapshot,
            parsed_requirement=(
                ParsedRequirement.model_validate(run.parsed_requirement)
                if run.parsed_requirement is not None
                else None
            ),
            category_catalog_snapshot=(
                CategoryCatalogSnapshot.model_validate(run.category_catalog_snapshot)
                if run.category_catalog_snapshot is not None
                else None
            ),
            provider=run.provider,
            model=run.model,
            prompt_version=run.prompt_version,
            error=run.error,
            created_by=run.created_by,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _product_candidate_row(product: Product, supplier: Supplier) -> ProductCandidateRow:
        # Products and suppliers are passed only from the repository's eligible query.
        return ProductCandidateRow(
            product_id=product.id,
            supplier_id=supplier.id,
            sku=product.sku,
            product_name=product.product_name,
            brand=product.brand,
            category_path=" / ".join(
                value
                for value in (
                    product.category_level1_name,
                    product.category_level2_name,
                    product.category_level3_name,
                )
                if value
            ),
            jd_price=product.jd_price,
            agreement_price=product.agreement_price,
            profit=product.profit,
            gross_margin=product.gross_margin,
            discount_rate=product.discount_rate,
            sales_volume=product.sales_volume,
            positive_rating=product.positive_rating,
            selling_points=product.selling_points,
            image_reference=product.image_reference,
            supplier_name=supplier.supplier_name,
            shipping_courier=product.shipping_courier,
        )

    @staticmethod
    def _candidate(
        run_id: uuid.UUID,
        item: CandidateRankInput | None,
        product: Product,
        supplier: Supplier,
        *,
        rank: int | None = None,
    ) -> RecommendationCandidate:
        if item is None and rank is None:
            raise ValueError("rank is required when the candidate has no ranking input")
        candidate_rank = rank if rank is not None else item.rank  # type: ignore[union-attr]
        product_snapshot: dict[str, object | None] = {"id": str(product.id)}
        price_snapshot: dict[str, object | None] = {}
        for field in PRODUCT_EXPORT_COLUMN_KEYS:
            if field == "supplier_name":
                continue
            value = getattr(product, field)
            if field in _DECIMAL_SNAPSHOT_FIELDS:
                price_snapshot[field] = str(value) if value is not None else None
            else:
                product_snapshot[field] = RecommendationService._snapshot_value(value)

        return RecommendationCandidate(
            run_id=run_id,
            product_id=product.id,
            rank=candidate_rank,
            score=item.score if item else None,
            reason=item.reason.strip() if item and item.reason else None,
            manual_flags=item.manual_flags if item else None,
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
    def _candidate_from_product(
        run_id: uuid.UUID, rank: int, product: Product, supplier: Supplier
    ) -> RecommendationCandidate:
        return RecommendationService._candidate(run_id, None, product, supplier, rank=rank)

    @staticmethod
    def _snapshot_value(value: object) -> object:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @staticmethod
    def _candidate_response(
        candidate: RecommendationCandidate, confirmation: RecommendationConfirmation | None
    ) -> RecommendationCandidateResponse:
        return RecommendationCandidateResponse(
            id=candidate.id,
            run_id=candidate.run_id,
            product_id=candidate.product_id,
            rank=candidate.rank,
            score=candidate.score,
            reason=candidate.reason,
            manual_flags=candidate.manual_flags,
            product_snapshot=candidate.product_snapshot,
            supplier_snapshot=candidate.supplier_snapshot,
            price_snapshot=candidate.price_snapshot,
            confirmation_id=confirmation.id if confirmation else None,
            factory_direct=(
                FactoryDirectStatus(confirmation.factory_direct) if confirmation else None
            ),
            confirmation=(
                RecommendationService._confirmation_response(confirmation) if confirmation else None
            ),
            created_at=candidate.created_at,
        )

    @staticmethod
    def _confirmation_response(
        confirmation: RecommendationConfirmation,
    ) -> RecommendationConfirmationResponse:
        return RecommendationConfirmationResponse(
            id=confirmation.id,
            candidate_id=confirmation.candidate_id,
            campaign_price=confirmation.campaign_price,
            delivery_status=confirmation.delivery_status,
            inventory_status=confirmation.inventory_status,
            factory_direct=FactoryDirectStatus(confirmation.factory_direct),
            fulfillment_cycle=confirmation.fulfillment_cycle,
            evidence=confirmation.evidence,
            confirmed_by=confirmation.confirmed_by,
            confirmed_at=confirmation.confirmed_at,
            updated_at=confirmation.updated_at,
        )
