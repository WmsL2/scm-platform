from __future__ import annotations

import json
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.transaction import transaction_scope
from app.infrastructure.adapters import InlineTaskQueue, TaskQueue
from app.modules.bid.domain.lifecycle import BidImportStatus, BidItemStatus, BidProjectStatus
from app.modules.bid.infrastructure.models import (
    BidItemSelection,
    BidProject,
    BidProjectEvent,
    BidProjectItem,
    MatchCandidate,
    MatchTask,
)
from app.modules.catalog.infrastructure.models import Product
from app.modules.matching.domain.rules import (
    CanonicalRequirement,
    MatchableProduct,
    decide_product_matches,
    is_eligible_matching_product,
    normalize_match_text,
)
from app.modules.matching.infrastructure.repository import MatchingRepository
from app.modules.matching.schemas import (
    BidItemCandidateResponse,
    BidItemSelectionCreateRequest,
    BidItemSelectionResponse,
    NoQuoteCreateRequest,
    StartMatchingResponse,
)
from app.modules.supplier.infrastructure.models import Supplier


class MatchingService:
    def __init__(self, session: AsyncSession, task_queue: TaskQueue | None = None) -> None:
        self.session = session
        self.repository = MatchingRepository(session)
        self.task_queue = task_queue or InlineTaskQueue()

    async def start(self, project_id: uuid.UUID, actor_id: uuid.UUID) -> StartMatchingResponse:
        result: StartMatchingResponse | None = None

        async def run() -> None:
            nonlocal result
            result = await self._run_matching(project_id, actor_id)

        await self.task_queue.enqueue(run)
        if result is None:
            raise RuntimeError("Matching task queue returned without executing the task")
        return result

    async def _run_matching(
        self, project_id: uuid.UUID, actor_id: uuid.UUID
    ) -> StartMatchingResponse:
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id)
            if project.import_status != BidImportStatus.PARSED.value:
                raise AppError("BID_PROJECT_NOT_PARSED", "项目尚未完成需求行解析", 409)
            if project.status != BidProjectStatus.IMPORTED.value:
                raise AppError("BID_MATCHING_NOT_ALLOWED", "当前项目状态不能开始匹配", 409)
            task = MatchTask(
                project_id=project_id,
                status="RUNNING",
                total_item_count=project.total_item_count,
                processed_item_count=0,
                created_by=actor_id,
            )
            project.status = BidProjectStatus.MATCHING.value
            project.updated_by = actor_id
            self.session.add(task)
            self._event(project_id, actor_id, "MATCH_STARTED", "IMPORTED", "MATCHING", None)
            await self.session.flush()

            items = await self.repository.items(project_id)
            product_rows = await self.repository.eligible_products()
            candidates = [self._matchable(product, supplier) for product, supplier in product_rows]
            for item in items:
                decision = decide_product_matches(self._requirement(item), candidates)
                item.status = decision.status.value
                for candidate in decision.candidates:
                    self.session.add(
                        MatchCandidate(
                            match_task_id=task.id,
                            project_item_id=item.id,
                            product_id=candidate.product_id,
                            supplier_id=candidate.supplier_id,
                            score=Decimal(candidate.score),
                            rank=candidate.rank,
                            match_method=candidate.recall_stage.value,
                            match_reason=candidate.match_reason(),
                        )
                    )
            task.status = "COMPLETED"
            task.processed_item_count = len(items)
            project.processed_item_count = len(items)
            project.status = BidProjectStatus.SELECTING.value
            self._event(project_id, actor_id, "MATCH_COMPLETED", "MATCHING", "SELECTING", None)
            if not items:
                project.status = BidProjectStatus.READY.value
                self._event(project_id, actor_id, "PROJECT_READY", "SELECTING", "READY", None)
            await self.session.flush()
        return StartMatchingResponse(
            task_id=task.id,
            status=task.status,
            total_item_count=task.total_item_count,
            processed_item_count=task.processed_item_count,
        )

    async def candidates(
        self, project_id: uuid.UUID, item_id: uuid.UUID
    ) -> list[BidItemCandidateResponse]:
        await self._project_or_404(project_id)
        rows = await self.repository.latest_candidates(project_id, item_id)
        return [
            self._candidate_response(candidate, product, supplier)
            for candidate, product, supplier in rows
        ]

    async def select(
        self,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: BidItemSelectionCreateRequest,
        actor_id: uuid.UUID,
    ) -> BidItemSelectionResponse:
        async with transaction_scope(self.session):
            project = await self._editable_project(project_id)
            item = await self._item_or_404(project_id, item_id)
            row = await self.repository.candidate_for_update(
                project_id, item_id, payload.candidate_id
            )
            if row is None:
                raise AppError(
                    "BID_MATCH_CANDIDATE_NOT_FOUND", "候选商品不存在或不属于该需求行", 404
                )
            candidate, product, supplier = row
            if not is_eligible_matching_product(self._matchable(product, supplier)):
                raise AppError("BID_MATCH_CANDIDATE_INELIGIBLE", "候选商品或供应商当前不可用", 409)
            if item.max_price is not None and payload.selected_unit_price > item.max_price:
                raise AppError("BID_SELECTED_PRICE_EXCEEDS_MAX", "选品单价不能高于需求限价", 422)
            selection = BidItemSelection(
                project_item_id=item.id,
                candidate_id=candidate.id,
                product_id=product.id,
                supplier_id=supplier.id,
                selected_unit_price=payload.selected_unit_price,
                requirement_snapshot=self._requirement_snapshot(item),
                product_snapshot=self._product_snapshot(product),
                supplier_snapshot=self._supplier_snapshot(supplier),
                price_snapshot=self._price_snapshot(product, payload.selected_unit_price),
                note=payload.note.strip() if payload.note else None,
                created_by=actor_id,
            )
            self.session.add(selection)
            await self.session.flush()
            item.current_selection_id = selection.id
            item.status = BidItemStatus.SELECTED.value
            item.no_quote_reason = None
            project.updated_by = actor_id
            self._event(project_id, actor_id, "ITEM_SELECTED", project.status, project.status, None)
            await self._refresh_project_status(project, actor_id)
        return BidItemSelectionResponse(
            selection_id=selection.id,
            project_item_id=item_id,
            status=item.status,
            current_selection_id=selection.id,
        )

    async def no_quote(
        self,
        project_id: uuid.UUID,
        item_id: uuid.UUID,
        payload: NoQuoteCreateRequest,
        actor_id: uuid.UUID,
    ) -> BidItemSelectionResponse:
        async with transaction_scope(self.session):
            project = await self._editable_project(project_id)
            item = await self._item_or_404(project_id, item_id)
            item.status = BidItemStatus.NO_QUOTE.value
            item.current_selection_id = None
            project.updated_by = actor_id
            item.no_quote_reason = json.dumps(
                {"reason": payload.reason.value, "detail": payload.reason_detail},
                ensure_ascii=False,
            )
            self._event(
                project_id,
                actor_id,
                "ITEM_NO_QUOTE",
                project.status,
                project.status,
                item.no_quote_reason,
            )
            await self._refresh_project_status(project, actor_id)
        return BidItemSelectionResponse(
            selection_id=None,
            project_item_id=item_id,
            status=item.status,
            current_selection_id=None,
        )

    async def _project_or_404(self, project_id: uuid.UUID) -> BidProject:
        project = await self.repository.project_for_update(project_id)
        if project is None:
            raise AppError("BID_PROJECT_NOT_FOUND", "投标项目不存在", 404)
        return project

    async def _item_or_404(self, project_id: uuid.UUID, item_id: uuid.UUID) -> BidProjectItem:
        item = await self.repository.item_for_update(project_id, item_id)
        if item is None:
            raise AppError("BID_PROJECT_ITEM_NOT_FOUND", "投标需求行不存在", 404)
        return item

    async def _editable_project(self, project_id: uuid.UUID) -> BidProject:
        project = await self._project_or_404(project_id)
        if project.status not in {
            BidProjectStatus.SELECTING.value,
            BidProjectStatus.READY.value,
            BidProjectStatus.EXPORTED.value,
        }:
            raise AppError("BID_SELECTION_NOT_ALLOWED", "当前项目状态不能选品", 409)
        return project

    async def _refresh_project_status(self, project: BidProject, actor_id: uuid.UUID) -> None:
        unresolved = await self.repository.unresolved_count(project.id)
        if unresolved == 0 and project.status == BidProjectStatus.SELECTING.value:
            project.status = BidProjectStatus.READY.value
            project.updated_by = actor_id
            self._event(project.id, actor_id, "PROJECT_READY", "SELECTING", "READY", None)
        elif project.status == BidProjectStatus.EXPORTED.value:
            project.status = BidProjectStatus.READY.value
            project.updated_by = actor_id
            self._event(project.id, actor_id, "SELECTION_CHANGED", "EXPORTED", "READY", None)

    @staticmethod
    def _requirement(item: BidProjectItem) -> CanonicalRequirement:
        return CanonicalRequirement(
            product_name=item.product_name,
            brand=item.brand,
            model=item.model,
            specification=item.specification,
            category_text=item.category_text,
            category_id=item.category_id,
            quantity=item.quantity,
            unit=item.unit,
            max_price=item.max_price,
            buyer_item_code=item.buyer_item_code,
            source_data=item.source_data,
        )

    @staticmethod
    def _matchable(product: Product, supplier: Supplier) -> MatchableProduct:
        return MatchableProduct(
            id=product.id,
            supplier_id=supplier.id,
            product_status=product.status,
            supplier_archive_status=supplier.archive_status,
            supplier_cooperation_status=supplier.cooperation_status,
            supplier_is_deleted=supplier.is_deleted,
            sku=product.sku,
            item_number=product.item_number,
            barcode_text=product.barcode_text,
            brand=product.brand,
            model=product.model,
            product_name=product.product_name,
            category_id=product.category_id,
            category_level1_name=product.category_level1_name,
            category_level2_name=product.category_level2_name,
            category_level3_name=product.category_level3_name,
            product_specification=product.product_specification,
        )

    def _event(
        self,
        project_id: uuid.UUID,
        actor_id: uuid.UUID,
        event_type: str,
        before: str | None,
        after: str | None,
        note: str | None,
    ) -> None:
        self.session.add(
            BidProjectEvent(
                project_id=project_id,
                actor_id=actor_id,
                event_type=event_type,
                from_status=before,
                to_status=after,
                note=note,
            )
        )

    @staticmethod
    def _requirement_snapshot(item: BidProjectItem) -> dict[str, object]:
        return {
            "original": {
                "product_name": item.product_name,
                "brand": item.brand,
                "model": item.model,
                "specification": item.specification,
                "category_text": item.category_text,
                "category_id": str(item.category_id) if item.category_id else None,
                "quantity": str(item.quantity) if item.quantity is not None else None,
                "unit": item.unit,
                "max_price": str(item.max_price) if item.max_price is not None else None,
                "buyer_item_code": item.buyer_item_code,
                "source_data": item.source_data,
            },
            "normalized": {
                "product_name": normalize_match_text(item.product_name),
                "brand": normalize_match_text(item.brand),
                "model": normalize_match_text(item.model),
                "specification": normalize_match_text(item.specification),
                "category_text": normalize_match_text(item.category_text),
                "buyer_item_code": normalize_match_text(item.buyer_item_code),
            },
        }

    @staticmethod
    def _product_snapshot(product: Product) -> dict[str, object]:
        return {
            "id": str(product.id),
            "sku": product.sku,
            "brand": product.brand,
            "model": product.model,
            "product_name": product.product_name,
            "category_id": str(product.category_id) if product.category_id else None,
            "category_path": " / ".join(
                value
                for value in (
                    product.category_level1_name,
                    product.category_level2_name,
                    product.category_level3_name,
                )
                if value
            ),
            "product_specification": product.product_specification,
            "status": product.status,
        }

    @staticmethod
    def _supplier_snapshot(supplier: Supplier) -> dict[str, object]:
        return {
            "id": str(supplier.id),
            "supplier_code": supplier.supplier_code,
            "supplier_name": supplier.supplier_name,
            "archive_status": supplier.archive_status,
            "cooperation_status": supplier.cooperation_status,
        }

    @staticmethod
    def _price_snapshot(product: Product, selected_unit_price: Decimal) -> dict[str, object]:
        return {
            "cost_price": str(product.cost_price),
            "jd_price": str(product.jd_price) if product.jd_price is not None else None,
            "agreement_price": str(product.agreement_price)
            if product.agreement_price is not None
            else None,
            "selected_unit_price": str(selected_unit_price),
        }

    @staticmethod
    def _candidate_response(
        candidate: MatchCandidate, product: Product, supplier: Supplier
    ) -> BidItemCandidateResponse:
        return BidItemCandidateResponse(
            candidate_id=candidate.id,
            product_id=product.id,
            supplier_id=supplier.id,
            product_name=product.product_name,
            brand=product.brand,
            model=product.model,
            category_path=" / ".join(
                value
                for value in (
                    product.category_level1_name,
                    product.category_level2_name,
                    product.category_level3_name,
                )
                if value
            ),
            product_specification=product.product_specification,
            supplier_code=supplier.supplier_code,
            supplier_name=supplier.supplier_name,
            cost_price=product.cost_price,
            jd_price=product.jd_price,
            agreement_price=product.agreement_price,
            score=candidate.score,
            rank=candidate.rank,
            method=candidate.match_method,
            match_reason=candidate.match_reason,
        )
