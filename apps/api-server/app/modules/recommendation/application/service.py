from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.transaction import transaction_scope
from app.modules.catalog.infrastructure.models import Product
from app.modules.recommendation.domain.lifecycle import ensure_transition
from app.modules.recommendation.infrastructure.models import (
    RecommendationCandidate,
    RecommendationCategoryChoice,
    RecommendationConfirmation,
    RecommendationRun,
)
from app.modules.recommendation.infrastructure.repository import RecommendationRepository
from app.modules.recommendation.schemas import (
    BatchConfirmationRequest,
    CandidateRankInput,
    CategoryChoiceInput,
    CategoryPath,
    CategoryPoolItem,
    ConfirmationUpdateRequest,
    ParsedRequirement,
    PersistCandidatesRequest,
    ProductCandidateRow,
    RecommendationCandidateResponse,
    RecommendationConfirmationResponse,
    RecommendationRunResponse,
)
from app.modules.recommendation.template.schemas import RecommendationRunStatus
from app.modules.supplier.infrastructure.models import Supplier


class RecommendationService:
    """B-owned deterministic state and data boundary for free recommendation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = RecommendationRepository(session)

    async def create_run(
        self, project_id: uuid.UUID, actor_id: uuid.UUID
    ) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            project = await self.repository.free_project_for_update(project_id)
            if project is None:
                raise AppError("FREE_RECOMMENDATION_PROJECT_NOT_FOUND", "自由推品项目不存在", 404)
            requirement = (project.remark or "").strip()
            if len(requirement) < 20:
                raise AppError(
                    "FREE_RECOMMENDATION_REMARK_REQUIRED",
                    "自由推品项目必须填写至少二十字需求说明",
                    409,
                )
            mapping_row = await self.repository.latest_template_mapping(project_id)
            if (
                mapping_row is None
                or mapping_row[0].confirmed_by is None
                or mapping_row[0].confirmed_at is None
            ):
                raise AppError(
                    "RECOMMENDATION_TEMPLATE_MAPPING_NOT_CONFIRMED", "请先确认最新推品模板映射", 409
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
        project = await self.repository.free_project_for_update(project_id)
        if project is None:
            raise AppError("FREE_RECOMMENDATION_PROJECT_NOT_FOUND", "自由推品项目不存在", 404)
        return [self._run_response(run) for run in await self.repository.runs(project_id)]

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
            for path, count in await self.repository.category_pool(requirement)
        ]

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
        self, run_id: uuid.UUID, category_paths: list[CategoryPath]
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
            rows = await self.repository.eligible_products(requirement, category_paths)
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
            await self.session.flush()
            for candidate in candidates:
                await self.session.refresh(candidate)
        return [self._candidate_response(candidate, None) for candidate in candidates]

    async def mark_no_candidates(self, run_id: uuid.UUID) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.NO_CANDIDATES)
        return self._run_response(run)

    async def mark_needs_input(self, run_id: uuid.UUID, error: str) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.NEEDS_INPUT)
            run.error = error.strip()[:4000] or None
        return self._run_response(run)

    async def mark_failed(self, run_id: uuid.UUID, error: str) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.FAILED)
            run.error = error.strip()[:4000] or None
        return self._run_response(run)

    async def mark_cancelled(self, run_id: uuid.UUID) -> RecommendationRunResponse:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            self._transition(run, RecommendationRunStatus.CANCELLED)
        return self._run_response(run)

    async def list_candidates(self, run_id: uuid.UUID) -> list[RecommendationCandidateResponse]:
        await self._run_or_404(run_id)
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
            confirmation.campaign_price = payload.campaign_price
            confirmation.delivery_status = payload.delivery_status
            confirmation.inventory_status = payload.inventory_status
            confirmation.fulfillment_cycle = payload.fulfillment_cycle
            confirmation.evidence = payload.evidence
            confirmation.confirmed_by = actor_id
            confirmation.confirmed_at = datetime.now(UTC).replace(tzinfo=None)
            if run.status in {
                RecommendationRunStatus.CANDIDATES_READY.value,
                RecommendationRunStatus.WAITING_CONFIRMATION.value,
            }:
                self._transition(run, RecommendationRunStatus.CONFIRMED)
            await self.session.flush()
            await self.session.refresh(confirmation)
        return self._confirmation_response(confirmation)

    async def confirm_candidates(
        self,
        run_id: uuid.UUID,
        payload: BatchConfirmationRequest,
        actor_id: uuid.UUID,
    ) -> list[RecommendationConfirmationResponse]:
        async with transaction_scope(self.session):
            run = await self._run_or_404_for_update(run_id)
            if run.status not in {
                RecommendationRunStatus.CANDIDATES_READY.value,
                RecommendationRunStatus.WAITING_CONFIRMATION.value,
                RecommendationRunStatus.CONFIRMED.value,
                RecommendationRunStatus.EXPORTED.value,
            }:
                raise AppError(
                    "RECOMMENDATION_CONFIRMATION_NOT_ALLOWED", "当前推品任务不能人工确认", 409
                )
            rows = await self.repository.candidates_with_confirmations_for_update(
                run_id, payload.candidate_ids
            )
            if len(rows) != len(payload.candidate_ids):
                raise AppError(
                    "RECOMMENDATION_CANDIDATE_NOT_FOUND",
                    "部分推品候选不存在或不属于当前任务",
                    404,
                )
            requirement = self._parsed_requirement(run)
            product_ids = [candidate.product_id for candidate, _ in rows]
            eligible = await self.repository.eligible_products_by_ids(
                requirement, product_ids
            )
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
            await self.session.flush()
            for confirmation in confirmations:
                await self.session.refresh(confirmation)
        return [self._confirmation_response(item) for item in confirmations]

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

    @staticmethod
    def _parsed_requirement(run: RecommendationRun) -> ParsedRequirement:
        if run.parsed_requirement is None:
            raise AppError("RECOMMENDATION_REQUIREMENT_NOT_PARSED", "推品需求尚未完成解析", 409)
        return ParsedRequirement.model_validate(run.parsed_requirement)

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
            image_reference=product.image_reference,
            supplier_name=supplier.supplier_name,
            shipping_courier=product.shipping_courier,
        )

    @staticmethod
    def _candidate(
        run_id: uuid.UUID,
        item: CandidateRankInput,
        product: Product,
        supplier: Supplier,
    ) -> RecommendationCandidate:
        return RecommendationCandidate(
            run_id=run_id,
            product_id=product.id,
            rank=item.rank,
            score=item.score,
            reason=item.reason.strip() if item.reason else None,
            manual_flags=item.manual_flags,
            product_snapshot={
                "id": str(product.id),
                "sku": product.sku,
                "product_name": product.product_name,
                "brand": product.brand,
                "model": product.model,
                "category_level1_name": product.category_level1_name,
                "category_level2_name": product.category_level2_name,
                "category_level3_name": product.category_level3_name,
                "image_reference": product.image_reference,
                "shipping_courier": product.shipping_courier,
            },
            supplier_snapshot={
                "id": str(supplier.id),
                "supplier_code": supplier.supplier_code,
                "supplier_name": supplier.supplier_name,
                "archive_status": supplier.archive_status,
                "cooperation_status": supplier.cooperation_status,
            },
            price_snapshot={
                "cost_price": str(product.cost_price) if product.cost_price is not None else None,
                "jd_price": str(product.jd_price) if product.jd_price is not None else None,
                "agreement_price": str(product.agreement_price)
                if product.agreement_price is not None
                else None,
                "profit": str(product.profit) if product.profit is not None else None,
                "gross_margin": str(product.gross_margin)
                if product.gross_margin is not None
                else None,
                "discount_rate": str(product.discount_rate)
                if product.discount_rate is not None
                else None,
                "purchasing_agent": product.purchasing_agent,
            },
        )

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
            fulfillment_cycle=confirmation.fulfillment_cycle,
            evidence=confirmation.evidence,
            confirmed_by=confirmation.confirmed_by,
            confirmed_at=confirmation.confirmed_at,
            updated_at=confirmation.updated_at,
        )
