from __future__ import annotations

import asyncio
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.database import SessionLocal
from app.core.transaction import transaction_scope
from app.infrastructure.adapters import InlineTaskQueue, TaskQueue
from app.integrations.deepseek.client import (
    DeepSeekConfigurationError,
    DeepSeekProviderError,
    DeepSeekStructuredOutputError,
)
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
from app.modules.catalog.infrastructure.models import Product
from app.modules.matching.application.type1_agent import (
    TYPE1_PROMPT_VERSION,
    Type1Agent,
    Type1AgentContractError,
    Type1CandidateContext,
    Type1RequirementContext,
    Type1RequirementDecision,
)
from app.modules.matching.application.type2_agent import (
    TYPE2_PROMPT_VERSION,
    Type2Agent,
    Type2AgentContractError,
    Type2CandidateContext,
    Type2RequirementContext,
    Type2RequirementDecision,
    normalized_search_tokens,
)
from app.modules.matching.domain.rules import (
    CanonicalRequirement,
    MatchableProduct,
    build_brand_catalog,
    decide_identified_product_matches,
    decide_product_matches,
    is_eligible_matching_product,
    normalize_match_text,
    resolve_controlled_brand_from_text,
    resolve_controlled_model_from_text,
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

TYPE2_AI_MAX_CONCURRENCY = 4
TYPE2_AI_CANDIDATE_LIMIT = 8
TYPE1_AI_MAX_CONCURRENCY = 4
TYPE1_AI_CANDIDATE_CHUNK_SIZE = 20
TYPE1_AI_BATCH_SIZE = 5
TYPE1_FALLBACK_MIN_SCORE = 50


@dataclass(frozen=True)
class _Type2SearchDocument:
    tokens: frozenset[str]
    normalized_text: str
    normalized_model: str


class MatchingService:
    def __init__(
        self,
        session: AsyncSession,
        task_queue: TaskQueue | None = None,
        type1_agent: Type1Agent | None = None,
        type2_agent: Type2Agent | None = None,
    ) -> None:
        self.session = session
        self.repository = MatchingRepository(session)
        self.task_queue = task_queue or InlineTaskQueue()
        self.type1_agent = type1_agent
        self.type2_agent = type2_agent

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
        project = await self.session.get(BidProject, project_id)
        if (
            project is not None
            and project.recommendation_type
            == BidRecommendationType.TYPE_1_SPECIFICATION.value
            and self.type1_agent is not None
        ):
            async with SessionLocal() as orchestration_session:
                return await MatchingService(
                    orchestration_session,
                    type1_agent=self.type1_agent,
                )._run_type1_ai_matching(project_id, actor_id)
        if (
            project is not None
            and project.recommendation_type
            == BidRecommendationType.TYPE_2_IDENTIFIED_PRODUCT.value
            and self.type2_agent is not None
        ):
            # The request dependency owns an outer transaction. Type 2 needs three
            # committed phases around the remote AI call, so it must not rollback or
            # reopen that request transaction. Run the orchestration in its own session.
            async with SessionLocal() as orchestration_session:
                return await MatchingService(
                    orchestration_session,
                    type2_agent=self.type2_agent,
                )._run_type2_ai_matching(project_id, actor_id)
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id)
            if project.import_status != BidImportStatus.PARSED.value:
                raise AppError("BID_PROJECT_NOT_PARSED", "项目尚未完成需求行解析", 409)
            is_type2 = (
                project.recommendation_type
                == BidRecommendationType.TYPE_2_IDENTIFIED_PRODUCT.value
            )
            is_type1 = (
                project.recommendation_type
                == BidRecommendationType.TYPE_1_SPECIFICATION.value
            )
            allowed_statuses = {BidProjectStatus.IMPORTED.value}
            if is_type1 or is_type2:
                # Allows projects created before automatic selection to be upgraded by
                # running matching once more from their old review state.
                allowed_statuses.update(
                    {
                        BidProjectStatus.SELECTING.value,
                        BidProjectStatus.READY.value,
                    }
                )
            if project.status not in allowed_statuses:
                raise AppError("BID_MATCHING_NOT_ALLOWED", "当前项目状态不能开始匹配", 409)
            previous_status = project.status
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
            self._event(
                project_id,
                actor_id,
                "MATCH_STARTED",
                previous_status,
                "MATCHING",
                None,
            )
            await self.session.flush()

            items = await self.repository.items(project_id)
            product_rows = await self.repository.eligible_products()
            candidates = [self._matchable(product, supplier) for product, supplier in product_rows]
            brand_catalog = build_brand_catalog(candidates)
            allow_brand_substitution = (
                project.recommendation_type
                == BidRecommendationType.TYPE_1_SPECIFICATION.value
            )
            product_rows_by_id = {
                product.id: (product, supplier) for product, supplier in product_rows
            }
            auto_selected_count = 0
            auto_selection_plans: list[
                tuple[BidProjectItem, MatchCandidate, Product, Supplier]
            ] = []
            for item in items:
                requirement = self._requirement(item)
                decision = (
                    decide_identified_product_matches(
                        requirement,
                        candidates,
                        brand_catalog=brand_catalog,
                    )
                    if is_type2
                    else decide_product_matches(
                        requirement,
                        candidates,
                        allow_brand_substitution=allow_brand_substitution,
                        brand_catalog=brand_catalog,
                    )
                )
                item.status = decision.status.value
                item.current_selection_id = None
                item.no_quote_reason = None
                candidate_models: dict[uuid.UUID, MatchCandidate] = {}
                for candidate in decision.candidates:
                    candidate_model = MatchCandidate(
                        id=uuid.uuid4(),
                        match_task_id=task.id,
                        project_item_id=item.id,
                        product_id=candidate.product_id,
                        supplier_id=candidate.supplier_id,
                        score=Decimal(candidate.score),
                        rank=candidate.rank,
                        match_method=candidate.recall_stage.value,
                        match_reason=candidate.match_reason(),
                    )
                    candidate_models[candidate.product_id] = candidate_model
                    self.session.add(candidate_model)
                if is_type1 or is_type2:
                    chosen = next(
                        (
                            candidate
                            for candidate in decision.candidates
                            if (
                                self._is_quotable_type2_product(
                                    product_rows_by_id[candidate.product_id][0],
                                    item.max_price,
                                )
                                if is_type2
                                else self._is_quotable_type1_product(
                                    product_rows_by_id[candidate.product_id][0],
                                    item.max_price,
                                )
                            )
                        ),
                        None,
                    )
                    if chosen is None:
                        item.status = BidItemStatus.NO_MATCH.value
                        continue
                    product, supplier = product_rows_by_id[chosen.product_id]
                    assert product.cost_price is not None
                    auto_selection_plans.append(
                        (item, candidate_models[chosen.product_id], product, supplier)
                    )
                    item.status = BidItemStatus.SELECTED.value
                    auto_selected_count += 1
            if is_type1 or is_type2:
                # Candidate rows must exist before their selection FK rows are inserted.
                await self.session.flush()
                for item, candidate_model, product, supplier in auto_selection_plans:
                    selection_id = uuid.uuid4()
                    assert product.cost_price is not None
                    selection = BidItemSelection(
                        id=selection_id,
                        project_item_id=item.id,
                        candidate_id=candidate_model.id,
                        product_id=product.id,
                        supplier_id=supplier.id,
                        selected_unit_price=product.cost_price,
                        requirement_snapshot=self._requirement_snapshot(item),
                        product_snapshot=self._product_snapshot(product),
                        supplier_snapshot=self._supplier_snapshot(supplier),
                        price_snapshot=self._price_snapshot(product, product.cost_price),
                        note=(
                            "类型2按当前成本价自动选择最低报价"
                            if is_type2
                            else "类型1已自动选择规格适配度最高的合规商品"
                        ),
                        created_by=actor_id,
                    )
                    self.session.add(selection)
                    item.current_selection_id = selection_id
            task.status = "COMPLETED"
            task.processed_item_count = len(items)
            project.processed_item_count = len(items)
            project.status = BidProjectStatus.SELECTING.value
            self._event(project_id, actor_id, "MATCH_COMPLETED", "MATCHING", "SELECTING", None)
            if is_type1 or is_type2 or not items:
                project.status = BidProjectStatus.READY.value
                self._event(
                    project_id,
                    actor_id,
                    "PROJECT_READY",
                    "SELECTING",
                    "READY",
                    (
                        (
                            f"类型2自动选择最低报价 {auto_selected_count} 条，"
                            if is_type2
                            else f"类型1自动选择规格合规商品 {auto_selected_count} 条，"
                        )
                        + f"未匹配 {len(items) - auto_selected_count} 条"
                        if is_type1 or is_type2
                        else None
                    ),
                )
            await self.session.flush()
        return StartMatchingResponse(
            task_id=task.id,
            status=task.status,
            total_item_count=task.total_item_count,
            processed_item_count=task.processed_item_count,
        )

    async def _run_type1_ai_matching(
        self, project_id: uuid.UUID, actor_id: uuid.UUID
    ) -> StartMatchingResponse:
        assert self.type1_agent is not None
        type1_agent = self.type1_agent
        task_id = uuid.uuid4()
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id)
            if project.import_status != BidImportStatus.PARSED.value:
                raise AppError("BID_PROJECT_NOT_PARSED", "项目尚未完成需求行解析", 409)
            if project.status not in {
                BidProjectStatus.IMPORTED.value,
                BidProjectStatus.SELECTING.value,
                BidProjectStatus.READY.value,
            }:
                raise AppError("BID_MATCHING_NOT_ALLOWED", "当前项目状态不能开始匹配", 409)
            previous_status = project.status
            task = MatchTask(
                id=task_id,
                project_id=project_id,
                status="RUNNING",
                total_item_count=project.total_item_count,
                processed_item_count=0,
                created_by=actor_id,
            )
            project.status = BidProjectStatus.MATCHING.value
            project.updated_by = actor_id
            self.session.add(task)
            self._event(
                project_id,
                actor_id,
                "TYPE1_AI_MATCH_STARTED",
                previous_status,
                BidProjectStatus.MATCHING.value,
                TYPE1_PROMPT_VERSION,
            )

        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id)
            items = await self.repository.items(project_id)
            product_rows = await self.repository.eligible_products()
            project_remark = project.remark
            context_rounds, candidate_pools, deterministic_decisions = self._type1_agent_contexts(
                items, product_rows
            )

        try:
            approved_keys: dict[str, list[str]] = {
                key: list(decision.candidate_keys)
                for key, decision in deterministic_decisions.items()
            }
            no_match_reasons: dict[str, str | None] = {
                key: decision.no_match_reason
                for key, decision in deterministic_decisions.items()
            }
            batches = [
                context_round[start : start + TYPE1_AI_BATCH_SIZE]
                for context_round in context_rounds
                for start in range(0, len(context_round), TYPE1_AI_BATCH_SIZE)
            ]
            semaphore = asyncio.Semaphore(TYPE1_AI_MAX_CONCURRENCY)

            async def match_batch(
                batch: list[Type1RequirementContext],
            ) -> list[Type1RequirementDecision]:
                async with semaphore:
                    result = await type1_agent.match_batch(
                        batch, project_remark=project_remark
                    )
                    return result.items

            tasks = [asyncio.create_task(match_batch(batch)) for batch in batches]
            try:
                batch_results = await asyncio.gather(*tasks)
            except BaseException:
                for ai_task in tasks:
                    if not ai_task.done():
                        ai_task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
            for result_items in batch_results:
                for result_item in result_items:
                    approved_keys.setdefault(result_item.requirement_key, []).extend(
                        result_item.candidate_keys
                    )
                    if result_item.no_match_reason:
                        no_match_reasons[result_item.requirement_key] = (
                            result_item.no_match_reason
                        )
        except DeepSeekConfigurationError as exc:
            await self._fail_type1_ai_matching(
                task_id, project_id, actor_id, str(exc), previous_status
            )
            raise AppError("TYPE1_AI_NOT_CONFIGURED", str(exc), 409) from exc
        except DeepSeekStructuredOutputError as exc:
            message = "类型1 AI 规格复核结果不符合业务约束，请重新执行"
            diagnostic = (
                f"{message}；{exc.error_kind}；{exc.safe_validation_summary}"
            )
            await self._fail_type1_ai_matching(
                task_id, project_id, actor_id, diagnostic, previous_status
            )
            raise AppError("TYPE1_AI_RESULT_INVALID", message, 502) from exc
        except Type1AgentContractError as exc:
            message = "类型1 AI 规格复核结果不符合业务约束，请重新执行"
            await self._fail_type1_ai_matching(
                task_id,
                project_id,
                actor_id,
                f"{message}；CONTRACT；{exc}",
                previous_status,
            )
            raise AppError("TYPE1_AI_RESULT_INVALID", message, 502) from exc
        except DeepSeekProviderError as exc:
            await self._fail_type1_ai_matching(
                task_id, project_id, actor_id, str(exc), previous_status
            )
            raise AppError("TYPE1_AI_PROVIDER_FAILED", str(exc), 502) from exc

        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id)
            if project.status != BidProjectStatus.MATCHING.value:
                raise AppError("TYPE1_AI_TASK_STALE", "类型1 AI 任务状态已变化", 409)
            loaded_task = await self.session.get(MatchTask, task_id)
            if loaded_task is None or loaded_task.status != "RUNNING":
                raise AppError("TYPE1_AI_TASK_STALE", "类型1 AI 任务不存在或已结束", 409)
            task = loaded_task
            current_items = {item.id: item for item in await self.repository.items(project_id)}
            products_by_id = {
                product.id: (product, supplier)
                for product, supplier in await self.repository.eligible_products()
            }
            matched_count = 0
            auto_selected_count = 0
            selection_plans: list[
                tuple[BidProjectItem, MatchCandidate, Product, Supplier, int]
            ] = []
            for original_item in items:
                item = current_items[original_item.id]
                requirement_key = self._type1_requirement_key(item.id)
                pool = candidate_pools.get(item.id, [])
                candidate_ids_by_key = {
                    f"P{index:05d}": product_id
                    for index, product_id in enumerate(pool, start=1)
                }
                unique_keys = list(dict.fromkeys(approved_keys.get(requirement_key, [])))
                selected_ids = [
                    candidate_ids_by_key[key]
                    for key in unique_keys
                    if key in candidate_ids_by_key
                    and candidate_ids_by_key[key] in products_by_id
                ]
                item.current_selection_id = None
                item.no_quote_reason = None
                if not selected_ids:
                    item.status = BidItemStatus.NO_MATCH.value
                    item.no_quote_reason = json.dumps(
                        {
                            "reason": (
                                no_match_reasons.get(requirement_key)
                                if no_match_reasons.get(requirement_key)
                                else "未找到与类目、名称、规格参数、技术要求及备注相符的商品"
                            )
                        },
                        ensure_ascii=False,
                    )
                    continue
                candidate_models: dict[uuid.UUID, MatchCandidate] = {}
                for rank, product_id in enumerate(selected_ids, start=1):
                    product, supplier = products_by_id[product_id]
                    candidate_model = MatchCandidate(
                        id=uuid.uuid4(),
                        match_task_id=task.id,
                        project_item_id=item.id,
                        product_id=product.id,
                        supplier_id=supplier.id,
                        score=Decimal(max(1, 101 - rank)),
                        rank=rank,
                        match_method="TYPE1_AI_SPECIFICATION",
                        match_reason={
                            "rules_version": TYPE1_PROMPT_VERSION,
                            "recall_stage": "TYPE1_AI_SPECIFICATION",
                            "comparison": "AI_STRUCTURED",
                        },
                    )
                    candidate_models[product_id] = candidate_model
                    self.session.add(candidate_model)
                quotable_ids = [
                    product_id
                    for product_id in selected_ids
                    if self._is_quotable_type1_product(
                        products_by_id[product_id][0], item.max_price
                    )
                ]
                if not quotable_ids:
                    item.status = BidItemStatus.NO_MATCH.value
                    item.no_quote_reason = json.dumps(
                        {"reason": "AI 规格候选缺少有效当前成本价或报价超过客户限价"},
                        ensure_ascii=False,
                    )
                    continue
                matched_count += 1
                item.status = BidItemStatus.SELECTED.value
                for output_rank, product_id in enumerate(quotable_ids, start=1):
                    product, supplier = products_by_id[product_id]
                    selection_plans.append(
                        (
                            item,
                            candidate_models[product_id],
                            product,
                            supplier,
                            output_rank,
                        )
                    )
                    auto_selected_count += 1

            await self.session.flush()
            for item, candidate_model, product, supplier, output_rank in selection_plans:
                assert product.cost_price is not None
                selection_id = uuid.uuid4()
                self.session.add(
                    BidItemSelection(
                        id=selection_id,
                        project_item_id=item.id,
                        candidate_id=candidate_model.id,
                        product_id=product.id,
                        supplier_id=supplier.id,
                        selected_unit_price=product.cost_price,
                        requirement_snapshot=self._requirement_snapshot(item),
                        product_snapshot=self._product_snapshot(product),
                        supplier_snapshot=self._supplier_snapshot(supplier),
                        price_snapshot=self._price_snapshot(product, product.cost_price),
                        note=f"类型1 AI 规格匹配商品（适配顺序 {output_rank}）",
                        created_by=actor_id,
                    )
                )
                if item.current_selection_id is None:
                    item.current_selection_id = selection_id

            task.status = "COMPLETED"
            task.processed_item_count = len(items)
            project.processed_item_count = len(items)
            project.status = BidProjectStatus.READY.value
            project.updated_by = actor_id
            self._event(
                project_id,
                actor_id,
                "TYPE1_AI_MATCH_COMPLETED",
                BidProjectStatus.MATCHING.value,
                BidProjectStatus.READY.value,
                (
                    f"类型1 AI 规格复核匹配 {matched_count} 个需求行，输出 "
                    f"{auto_selected_count} 个商品，未匹配 {len(items) - matched_count} 行"
                ),
            )

        return StartMatchingResponse(
            task_id=task_id,
            status="COMPLETED",
            total_item_count=len(items),
            processed_item_count=len(items),
        )

    async def _fail_type1_ai_matching(
        self,
        task_id: uuid.UUID,
        project_id: uuid.UUID,
        actor_id: uuid.UUID,
        message: str,
        restore_status: str,
    ) -> None:
        async with transaction_scope(self.session):
            task = await self.session.get(MatchTask, task_id)
            project = await self.session.get(BidProject, project_id)
            if task is not None and task.status == "RUNNING":
                task.status = "FAILED"
                task.error_message = message[:2000]
            if project is not None and project.status == BidProjectStatus.MATCHING.value:
                project.status = restore_status
                project.updated_by = actor_id
                self._event(
                    project_id,
                    actor_id,
                    "TYPE1_AI_MATCH_FAILED",
                    BidProjectStatus.MATCHING.value,
                    restore_status,
                    message[:2000],
                )

    async def _run_type2_ai_matching(
        self, project_id: uuid.UUID, actor_id: uuid.UUID
    ) -> StartMatchingResponse:
        assert self.type2_agent is not None
        type2_agent = self.type2_agent
        task_id = uuid.uuid4()
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id)
            if project.import_status != BidImportStatus.PARSED.value:
                raise AppError("BID_PROJECT_NOT_PARSED", "项目尚未完成需求行解析", 409)
            if project.status not in {
                BidProjectStatus.IMPORTED.value,
                BidProjectStatus.SELECTING.value,
                BidProjectStatus.READY.value,
            }:
                raise AppError("BID_MATCHING_NOT_ALLOWED", "当前项目状态不能开始匹配", 409)
            previous_status = project.status
            task = MatchTask(
                id=task_id,
                project_id=project_id,
                status="RUNNING",
                total_item_count=project.total_item_count,
                processed_item_count=0,
                created_by=actor_id,
            )
            project.status = BidProjectStatus.MATCHING.value
            project.updated_by = actor_id
            self.session.add(task)
            self._event(
                project_id,
                actor_id,
                "TYPE2_AI_MATCH_STARTED",
                previous_status,
                BidProjectStatus.MATCHING.value,
                TYPE2_PROMPT_VERSION,
            )

        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id)
            items = await self.repository.items(project_id)
            product_rows = await self.repository.eligible_products()
            project_remark = project.remark
            contexts, candidate_pools, deterministic_decisions = self._type2_agent_contexts(
                items, product_rows, project_remark=project_remark
            )

        try:
            decisions: dict[str, Type2RequirementDecision] = dict(
                deterministic_decisions
            )
            batches = [contexts[start : start + 10] for start in range(0, len(contexts), 10)]
            semaphore = asyncio.Semaphore(TYPE2_AI_MAX_CONCURRENCY)

            async def match_batch(
                batch: list[Type2RequirementContext],
            ) -> list[Type2RequirementDecision]:
                async with semaphore:
                    result = await type2_agent.match_batch(
                        batch, project_remark=project_remark
                    )
                    return result.items

            tasks = [asyncio.create_task(match_batch(batch)) for batch in batches]
            try:
                batch_results = await asyncio.gather(*tasks)
            except BaseException:
                # asyncio.gather propagates the first exception but otherwise lets sibling
                # requests keep running. Cancel them explicitly so a failed batch cannot
                # continue consuming provider time and tokens after the API has returned.
                for ai_task in tasks:
                    if not ai_task.done():
                        ai_task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                raise
            for result_items in batch_results:
                decisions.update({item.requirement_key: item for item in result_items})
        except DeepSeekConfigurationError as exc:
            await self._fail_type2_ai_matching(task_id, project_id, actor_id, str(exc))
            raise AppError("TYPE2_AI_NOT_CONFIGURED", str(exc), 409) from exc
        except (DeepSeekStructuredOutputError, Type2AgentContractError) as exc:
            message = "类型2 AI 同品判断结果不符合业务约束，请重新执行"
            await self._fail_type2_ai_matching(task_id, project_id, actor_id, message)
            raise AppError("TYPE2_AI_RESULT_INVALID", message, 502) from exc
        except DeepSeekProviderError as exc:
            await self._fail_type2_ai_matching(task_id, project_id, actor_id, str(exc))
            raise AppError("TYPE2_AI_PROVIDER_FAILED", str(exc), 502) from exc

        auto_selected_count = 0
        substitute_count = 0
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id)
            if project.status != BidProjectStatus.MATCHING.value:
                raise AppError("TYPE2_AI_TASK_STALE", "类型2 AI 任务状态已变化", 409)
            loaded_task = await self.session.get(MatchTask, task_id)
            if loaded_task is None or loaded_task.status != "RUNNING":
                raise AppError("TYPE2_AI_TASK_STALE", "类型2 AI 任务不存在或已结束", 409)
            task = loaded_task

            current_items = {item.id: item for item in await self.repository.items(project_id)}
            current_product_rows = await self.repository.eligible_products()
            products_by_id = {
                product.id: (product, supplier)
                for product, supplier in current_product_rows
            }
            selection_plans: list[
                tuple[BidProjectItem, MatchCandidate, Product, Supplier, str, str]
            ] = []
            for original_item in items:
                item = current_items[original_item.id]
                requirement_key = self._type2_requirement_key(item.id)
                decision = decisions.get(requirement_key)
                pool = candidate_pools.get(item.id, [])
                candidate_ids_by_key = {
                    f"P{index:02d}": product_id
                    for index, product_id in enumerate(pool, start=1)
                }
                item.current_selection_id = None
                item.no_quote_reason = None
                if decision is None:
                    item.status = BidItemStatus.NO_MATCH.value
                    item.no_quote_reason = json.dumps(
                        {"reason": "TYPE2_AI_RESULT_MISSING"}, ensure_ascii=False
                    )
                    continue

                exact_keys = list(getattr(decision, "exact_candidate_keys"))
                substitute_decisions = {
                    entry.candidate_key: entry
                    for entry in getattr(decision, "substitute_candidates")
                }
                exact_products = self._type2_products_for_keys(
                    exact_keys, candidate_ids_by_key, products_by_id
                )
                substitute_rows_by_key = {
                    key: products_by_id[product_id]
                    for key, product_id in candidate_ids_by_key.items()
                    if key in substitute_decisions and product_id in products_by_id
                }
                substitute_products = list(substitute_rows_by_key.values())
                ranked_candidates: list[
                    tuple[str, Product, Supplier, str | None, list[str]]
                ] = []
                for product, supplier in exact_products:
                    ranked_candidates.append(("TYPE2_AI_EXACT", product, supplier, None, []))
                for key, (product, supplier) in substitute_rows_by_key.items():
                    entry = substitute_decisions[key]
                    ranked_candidates.append(
                        (
                            "TYPE2_AI_SUBSTITUTE",
                            product,
                            supplier,
                            entry.note,
                            entry.differences,
                        )
                    )

                candidate_models: dict[uuid.UUID, MatchCandidate] = {}
                for rank, (method, product, supplier, note, differences) in enumerate(
                    ranked_candidates, start=1
                ):
                    candidate_model = MatchCandidate(
                        id=uuid.uuid4(),
                        match_task_id=task.id,
                        project_item_id=item.id,
                        product_id=product.id,
                        supplier_id=supplier.id,
                        score=Decimal("100" if method == "TYPE2_AI_EXACT" else "60"),
                        rank=rank,
                        match_method=method,
                        match_reason={
                            "rules_version": TYPE2_PROMPT_VERSION,
                            "recall_stage": method,
                            "comparison": "AI_STRUCTURED",
                            "differences": differences,
                            "required_note": note,
                        },
                    )
                    candidate_models[product.id] = candidate_model
                    self.session.add(candidate_model)

                chosen_method = "TYPE2_AI_EXACT"
                chosen_note = "类型2 AI 判定完全同品，按当前成本价自动选择最低报价"
                required_discount_rate = self._type2_required_discount_rate(
                    item, project_remark
                )
                chosen_rows = [
                    row
                    for row in exact_products
                    if self._is_quotable_type2_product(
                        row[0],
                        item.max_price,
                        required_discount_rate=required_discount_rate,
                    )
                ]
                if not chosen_rows:
                    chosen_method = "TYPE2_AI_SUBSTITUTE"
                    chosen_rows = [
                        row
                        for row in substitute_products
                        if self._is_quotable_type2_product(
                            row[0],
                            item.max_price,
                            required_discount_rate=required_discount_rate,
                        )
                    ]
                chosen_rows.sort(
                    key=lambda row: (
                        row[0].cost_price is None,
                        row[0].cost_price or Decimal("0"),
                        str(row[0].id),
                    )
                )
                if not chosen_rows:
                    item.status = BidItemStatus.NO_MATCH.value
                    item.no_quote_reason = json.dumps(
                        {
                            "reason": getattr(decision, "no_match_reason")
                            or "没有价格与限价均合规的完全同品或同类型替代品",
                        },
                        ensure_ascii=False,
                    )
                    continue

                product, supplier = chosen_rows[0]
                if chosen_method == "TYPE2_AI_SUBSTITUTE":
                    selected_key = next(
                        key
                        for key, product_id in candidate_ids_by_key.items()
                        if product_id == product.id
                    )
                    chosen_note = substitute_decisions[selected_key].note
                    substitute_count += 1
                candidate_model = candidate_models[product.id]
                selection_plans.append(
                    (
                        item,
                        candidate_model,
                        product,
                        supplier,
                        chosen_note,
                        chosen_method,
                    )
                )
                item.status = BidItemStatus.SELECTED.value
                auto_selected_count += 1

            await self.session.flush()
            for item, candidate_model, product, supplier, note, match_method in selection_plans:
                assert product.cost_price is not None
                selection_id = uuid.uuid4()
                product_snapshot = self._product_snapshot(product)
                product_snapshot["type2_match_type"] = match_method
                self.session.add(
                    BidItemSelection(
                        id=selection_id,
                        project_item_id=item.id,
                        candidate_id=candidate_model.id,
                        product_id=product.id,
                        supplier_id=supplier.id,
                        selected_unit_price=product.cost_price,
                        requirement_snapshot=self._requirement_snapshot(item),
                        product_snapshot=product_snapshot,
                        supplier_snapshot=self._supplier_snapshot(supplier),
                        price_snapshot=self._price_snapshot(product, product.cost_price),
                        note=note,
                        created_by=actor_id,
                    )
                )
                item.current_selection_id = selection_id

            task.status = "COMPLETED"
            task.processed_item_count = len(items)
            project.processed_item_count = len(items)
            project.status = BidProjectStatus.READY.value
            project.updated_by = actor_id
            self._event(
                project_id,
                actor_id,
                "TYPE2_AI_MATCH_COMPLETED",
                BidProjectStatus.MATCHING.value,
                BidProjectStatus.READY.value,
                (
                    f"类型2 AI 完全同品优先匹配，自动报价 {auto_selected_count} 条，"
                    f"其中同类型替代 {substitute_count} 条，未匹配 "
                    f"{len(items) - auto_selected_count} 条"
                ),
            )

        return StartMatchingResponse(
            task_id=task_id,
            status="COMPLETED",
            total_item_count=len(items),
            processed_item_count=len(items),
        )

    async def _fail_type2_ai_matching(
        self,
        task_id: uuid.UUID,
        project_id: uuid.UUID,
        actor_id: uuid.UUID,
        message: str,
    ) -> None:
        async with transaction_scope(self.session):
            task = await self.session.get(MatchTask, task_id)
            project = await self.session.get(BidProject, project_id)
            if task is not None and task.status == "RUNNING":
                task.status = "FAILED"
                task.error_message = message[:2000]
            if project is not None and project.status == BidProjectStatus.MATCHING.value:
                project.status = BidProjectStatus.IMPORTED.value
                project.updated_by = actor_id
                self._event(
                    project_id,
                    actor_id,
                    "TYPE2_AI_MATCH_FAILED",
                    BidProjectStatus.MATCHING.value,
                    BidProjectStatus.IMPORTED.value,
                    message[:2000],
                )

    def _type1_agent_contexts(
        self,
        items: list[BidProjectItem],
        product_rows: list[tuple[Product, Supplier]],
    ) -> tuple[
        list[list[Type1RequirementContext]],
        dict[uuid.UUID, list[uuid.UUID]],
        dict[str, Type1RequirementDecision],
    ]:
        matchables = [self._matchable(product, supplier) for product, supplier in product_rows]
        brand_catalog = build_brand_catalog(matchables)
        product_documents = {
            product.id: self._type2_product_search_document(product)
            for product, _supplier in product_rows
        }
        rows_by_id = {product.id: product for product, _supplier in product_rows}
        context_rounds: list[list[Type1RequirementContext]] = []
        pools: dict[uuid.UUID, list[uuid.UUID]] = {}
        decisions: dict[str, Type1RequirementDecision] = {}
        for item in items:
            requirement_key = self._type1_requirement_key(item.id)
            important_fields = self._type1_important_fields(item)
            if not important_fields:
                pools[item.id] = []
                decisions[requirement_key] = Type1RequirementDecision(
                    requirement_key=requirement_key,
                    no_match_reason="类型1需求缺少类目、商品名称、规格参数或主要技术要求",
                )
                continue

            rule_decision = decide_product_matches(
                self._requirement(item),
                matchables,
                allow_brand_substitution=True,
                brand_catalog=brand_catalog,
            )
            deterministic_ids = [
                candidate.product_id for candidate in rule_decision.candidates
            ]
            requirement_text = " ".join(important_fields.values())
            requirement_tokens = normalized_search_tokens(requirement_text)
            normalized_requirement = normalize_match_text(requirement_text)
            normalized_product_name = normalize_match_text(item.product_name)
            normalized_category = normalize_match_text(item.category_text)
            fallback_scores: list[tuple[int, uuid.UUID]] = []
            for product, _supplier in product_rows:
                if product.id in deterministic_ids:
                    continue
                document = product_documents[product.id]
                shared_tokens = requirement_tokens & document.tokens
                score = (
                    len(shared_tokens) * 10
                    + (
                        40
                        if normalized_product_name
                        and normalized_product_name in document.normalized_text
                        else 0
                    )
                    + (
                        30
                        if normalized_category
                        and normalized_category in document.normalized_text
                        else 0
                    )
                    + (
                        20
                        if normalized_requirement
                        and document.normalized_text
                        and (
                            normalized_requirement in document.normalized_text
                            or document.normalized_text in normalized_requirement
                        )
                        else 0
                    )
                    + (40 if any(len(token) >= 6 for token in shared_tokens) else 0)
                )
                if score >= TYPE1_FALLBACK_MIN_SCORE:
                    fallback_scores.append((score, product.id))
            ranked_fallback = sorted(
                fallback_scores, key=lambda row: (-row[0], str(row[1]))
            )
            fallback_ids = [product_id for _score, product_id in ranked_fallback]
            pool = list(dict.fromkeys(deterministic_ids + fallback_ids))
            pools[item.id] = pool
            if not pool:
                decisions[requirement_key] = Type1RequirementDecision(
                    requirement_key=requirement_key,
                    no_match_reason="未召回可供类型1 AI复核的规格候选",
                )
                continue
            for chunk_start in range(0, len(pool), TYPE1_AI_CANDIDATE_CHUNK_SIZE):
                round_index = chunk_start // TYPE1_AI_CANDIDATE_CHUNK_SIZE
                while len(context_rounds) <= round_index:
                    context_rounds.append([])
                chunk = pool[
                    chunk_start : chunk_start + TYPE1_AI_CANDIDATE_CHUNK_SIZE
                ]
                context_rounds[round_index].append(
                    Type1RequirementContext(
                        requirement_key=requirement_key,
                        source_row=self._matching_source_row(item),
                        normalized_fields={
                            "category_text": item.category_text,
                            "product_name": item.product_name,
                            "specification": item.specification,
                            "brand": item.brand,
                            "model": item.model,
                        },
                        important_fields=important_fields,
                        candidates=[
                            self._type1_candidate_context(
                                index, rows_by_id[product_id]
                            )
                            for index, product_id in enumerate(
                                chunk, start=chunk_start + 1
                            )
                        ],
                    )
                )
        return context_rounds, pools, decisions

    @staticmethod
    def _type1_important_fields(item: BidProjectItem) -> dict[str, str]:
        fields: dict[str, str] = {}
        for key, value in (
            ("category_text", item.category_text),
            ("product_name", item.product_name),
            ("model_or_specification", item.model),
            ("specification", item.specification),
        ):
            if value and str(value).strip():
                fields[key] = str(value).strip()
        for header, raw_value in item.source_data.items():
            if raw_value is None or not str(raw_value).strip():
                continue
            normalized_header = normalize_match_text(header)
            if any(
                normalize_match_text(keyword) in normalized_header
                for keyword in ("备注", "特殊要求", "技术要求", "技术参数", "说明")
            ):
                fields.setdefault(f"row_note:{header}", str(raw_value).strip())
        return fields

    @staticmethod
    def _type1_candidate_context(index: int, product: Product) -> Type1CandidateContext:
        return Type1CandidateContext(
            candidate_key=f"P{index:05d}",
            product_name=product.product_name,
            brand=product.brand,
            model=product.model,
            specification=product.product_specification,
            packaging=product.packaging_list,
            category_path=" / ".join(
                value
                for value in (
                    product.category_level1_name,
                    product.category_level2_name,
                    product.category_level3_name,
                )
                if value
            )
            or None,
            selling_points=product.selling_points,
            product_remark=product.remark,
        )

    def _type2_agent_contexts(
        self,
        items: list[BidProjectItem],
        product_rows: list[tuple[Product, Supplier]],
        *,
        project_remark: str | None,
    ) -> tuple[
        list[Type2RequirementContext],
        dict[uuid.UUID, list[uuid.UUID]],
        dict[str, Type2RequirementDecision],
    ]:
        matchables = [self._matchable(product, supplier) for product, supplier in product_rows]
        brand_catalog = build_brand_catalog(matchables)
        search_documents = {
            product.id: self._type2_product_search_document(product)
            for product, _supplier in product_rows
        }
        contexts: list[Type2RequirementContext] = []
        pools: dict[uuid.UUID, list[uuid.UUID]] = {}
        decisions: dict[str, Type2RequirementDecision] = {}
        rows_by_id = {product.id: product for product, _supplier in product_rows}
        for item in items:
            requirement_key = self._type2_requirement_key(item.id)
            embedded_identity_text = " ".join(
                str(value)
                for value in (
                    item.product_name,
                    item.specification,
                    *item.source_data.values(),
                )
                if value is not None and str(value).strip()
            )
            resolved_brand = item.brand or resolve_controlled_brand_from_text(
                embedded_identity_text, brand_catalog
            )
            resolved_model = item.model or resolve_controlled_model_from_text(
                embedded_identity_text, matchables
            )
            has_primary_identity = bool(item.buyer_item_code) or bool(
                resolved_brand and resolved_model
            )
            if not has_primary_identity:
                pools[item.id] = []
                decisions[requirement_key] = Type2RequirementDecision(
                    requirement_key=requirement_key,
                    no_match_reason="类型2必须提供客户商品编码，或同时提供品牌和型号",
                )
                continue

            required_discount_rate = self._type2_required_discount_rate(
                item, project_remark
            )
            quotable_rows = [
                (product, supplier)
                for product, supplier in product_rows
                if self._is_quotable_type2_product(
                    product,
                    item.max_price,
                    required_discount_rate=required_discount_rate,
                )
            ]
            quotable_ids = {product.id for product, _supplier in quotable_rows}
            quotable_matchables = [
                product for product in matchables if product.id in quotable_ids
            ]
            requirement = CanonicalRequirement(
                product_name=item.product_name,
                brand=resolved_brand,
                model=resolved_model,
                specification=item.specification,
                category_text=item.category_text,
                category_id=item.category_id,
                quantity=item.quantity,
                unit=item.unit,
                max_price=item.max_price,
                buyer_item_code=item.buyer_item_code,
                source_data=item.source_data,
            )
            exact = decide_identified_product_matches(
                requirement, quotable_matchables, brand_catalog=brand_catalog
            )
            exact_ids = [candidate.product_id for candidate in exact.candidates]
            if item.buyer_item_code and resolved_brand and resolved_model:
                identity_only = decide_identified_product_matches(
                    CanonicalRequirement(brand=resolved_brand, model=resolved_model),
                    quotable_matchables,
                    brand_catalog=brand_catalog,
                )
                identity_ids = {
                    candidate.product_id for candidate in identity_only.candidates
                }
                exact_ids = [product_id for product_id in exact_ids if product_id in identity_ids]
            important_fields = self._type2_important_fields(
                item, brand=resolved_brand, model=resolved_model
            )
            has_secondary_conditions = any(
                key not in {"buyer_item_code", "brand", "model"}
                for key in important_fields
            )
            allow_substitution = self._type2_allows_substitution(item, project_remark)

            if exact_ids and not has_secondary_conditions:
                pool = list(dict.fromkeys(exact_ids))[:TYPE2_AI_CANDIDATE_LIMIT]
                pools[item.id] = pool
                decisions[requirement_key] = Type2RequirementDecision(
                    requirement_key=requirement_key,
                    exact_candidate_keys=[
                        f"P{index:02d}" for index in range(1, len(pool) + 1)
                    ],
                )
                continue

            requirement_document = self._type2_requirement_search_document(
                item, brand=resolved_brand, model=resolved_model
            )
            ranked = sorted(
                (
                    (
                        self._type2_recall_score_documents(
                            item,
                            product,
                            requirement_document,
                            search_documents[product.id],
                        ),
                        product.id,
                    )
                    for product, _supplier in quotable_rows
                    if product.id not in exact_ids
                ),
                key=lambda row: (-row[0], str(row[1])),
            )
            substitute_ids = [product_id for score, product_id in ranked if score > 0]
            pool = exact_ids + (substitute_ids if allow_substitution else [])
            pool = list(dict.fromkeys(pool))[:TYPE2_AI_CANDIDATE_LIMIT]
            pools[item.id] = pool
            if not pool:
                decisions[requirement_key] = Type2RequirementDecision(
                    requirement_key=requirement_key,
                    no_match_reason=(
                        "品牌和型号未匹配到合规正式商品"
                        if not allow_substitution
                        else "未召回可供AI复核的同品或同类型候选"
                    ),
                )
                continue
            contexts.append(
                Type2RequirementContext(
                    requirement_key=requirement_key,
                    source_row=self._matching_source_row(item),
                    normalized_fields={
                        "product_name": item.product_name,
                        "brand": resolved_brand,
                        "model": resolved_model,
                        "specification": item.specification,
                        "category_text": item.category_text,
                        "unit": item.unit,
                    },
                    important_fields=important_fields,
                    allow_substitution=allow_substitution,
                    candidates=[
                        self._type2_candidate_context(index, rows_by_id[product_id])
                        for index, product_id in enumerate(pool, start=1)
                    ],
                )
            )
        return contexts, pools, decisions

    @staticmethod
    def _type2_important_fields(
        item: BidProjectItem,
        *,
        brand: str | None = None,
        model: str | None = None,
    ) -> dict[str, str]:
        fields: dict[str, str] = {}
        for key, value in (
            ("buyer_item_code", item.buyer_item_code),
            ("brand", brand or item.brand),
            ("model", model or item.model),
        ):
            if value and str(value).strip():
                fields[key] = str(value).strip()

        semantic_headers = (
            ("color", ("颜色", "色别")),
            ("compatible_model", ("适用", "兼容机型", "设备型号")),
            ("capacity", ("打印量", "容量", "页数", "支数")),
            ("packaging", ("包装", "装箱")),
            ("specification", ("规格", "参数")),
            ("unit", ("计量单位", "单位")),
            ("material", ("材质",)),
            ("size", ("尺寸", "大小")),
            ("row_note", ("备注", "特殊要求", "说明")),
        )
        for header, raw_value in item.source_data.items():
            if raw_value is None or not str(raw_value).strip():
                continue
            normalized_header = normalize_match_text(header)
            for field, keywords in semantic_headers:
                if any(normalize_match_text(keyword) in normalized_header for keyword in keywords):
                    if field == "unit" and normalized_header not in {
                        normalize_match_text("计量单位"),
                        normalize_match_text("单位"),
                        normalize_match_text("销售单位"),
                    }:
                        continue
                    fields.setdefault(field, str(raw_value).strip())
                    break
        return fields

    @staticmethod
    def _type2_allows_substitution(
        item: BidProjectItem, project_remark: str | None
    ) -> bool:
        requirement_text = " ".join(
            str(value)
            for value in (project_remark, *item.source_data.values())
            if value is not None
        )
        compact = re.sub(r"\s+", "", requirement_text)
        return any(
            marker in compact
            for marker in (
                "允许替代",
                "可以替代",
                "可替代",
                "同类型替代",
                "同质同类",
                "同类商品",
            )
        )

    @staticmethod
    def _matching_source_row(item: BidProjectItem) -> dict[str, object]:
        quantity_headers = {
            normalize_match_text(value)
            for value in ("数量", "预计数量", "采购数量", "需求数量", "报价数量")
        }
        return {
            header: value
            for header, value in item.source_data.items()
            if value is not None
            and str(value).strip()
            and normalize_match_text(header) not in quantity_headers
        }

    @staticmethod
    def _type2_candidate_context(index: int, product: Product) -> Type2CandidateContext:
        return Type2CandidateContext(
            candidate_key=f"P{index:02d}",
            product_name=product.product_name,
            brand=product.brand,
            model=product.model,
            specification=product.product_specification,
            packaging=product.packaging_list,
            category_path=" / ".join(
                value
                for value in (
                    product.category_level1_name,
                    product.category_level2_name,
                    product.category_level3_name,
                )
                if value
            )
            or None,
            selling_points=product.selling_points,
            product_remark=product.remark,
        )

    @staticmethod
    def _type2_requirement_search_document(
        item: BidProjectItem,
        *,
        brand: str | None = None,
        model: str | None = None,
    ) -> _Type2SearchDocument:
        requirement_text = " ".join(
            str(value)
            for value in (
                item.product_name,
                brand or item.brand,
                model or item.model,
                item.specification,
                item.category_text,
                *item.source_data.values(),
            )
            if value is not None
        )
        return _Type2SearchDocument(
            tokens=frozenset(normalized_search_tokens(requirement_text)),
            normalized_text=normalize_match_text(requirement_text),
            normalized_model=normalize_match_text(model or item.model),
        )

    @staticmethod
    def _type2_product_search_document(product: Product) -> _Type2SearchDocument:
        product_text = " ".join(
            value
            for value in (
                product.product_name,
                product.brand,
                product.model,
                product.product_specification,
                product.packaging_list,
                product.category_level1_name,
                product.category_level2_name,
                product.category_level3_name,
                product.selling_points,
                product.remark,
            )
            if value
        )
        return _Type2SearchDocument(
            tokens=frozenset(normalized_search_tokens(product_text)),
            normalized_text=normalize_match_text(product_text),
            normalized_model=normalize_match_text(product.model),
        )

    @staticmethod
    def _type2_recall_score_documents(
        item: BidProjectItem,
        product: Product,
        requirement: _Type2SearchDocument,
        candidate: _Type2SearchDocument,
    ) -> int:
        overlap = requirement.tokens & candidate.tokens
        score = len(overlap) * 10
        if (
            requirement.normalized_model
            and requirement.normalized_model in candidate.normalized_text
        ):
            score += 60
        normalized_product_name = normalize_match_text(item.product_name)
        if normalized_product_name and normalized_product_name in candidate.normalized_text:
            score += 40
        if candidate.normalized_model and candidate.normalized_model in requirement.normalized_text:
            score += 30
        return score

    @staticmethod
    def _type2_products_for_keys(
        keys: list[str],
        candidate_ids_by_key: dict[str, uuid.UUID],
        products_by_id: dict[uuid.UUID, tuple[Product, Supplier]],
    ) -> list[tuple[Product, Supplier]]:
        rows: list[tuple[Product, Supplier]] = []
        for key in keys:
            product_id = candidate_ids_by_key.get(key)
            if product_id is not None and product_id in products_by_id:
                rows.append(products_by_id[product_id])
        return rows

    @staticmethod
    def _type2_required_discount_rate(
        item: BidProjectItem, project_remark: str | None
    ) -> Decimal | None:
        # A blank result column such as “是否满足平台承诺折扣率（88折）” is not
        # itself a customer constraint. Include a header only when its cell has an
        # actual value, while free-text project remarks are always considered.
        requirement_parts = [project_remark] if project_remark else []
        requirement_parts.extend(
            f"{header} {value}"
            for header, value in item.source_data.items()
            if value is not None and str(value).strip()
        )
        rates: list[Decimal] = []
        for requirement_text in requirement_parts:
            normalized = unicodedata.normalize("NFKC", str(requirement_text)).casefold()
            for raw_rate in re.findall(r"(?<!\d)(0\.\d+)(?!\d)", normalized):
                rates.append(Decimal(raw_rate))
            for raw_rate in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*%(?!\d)", normalized):
                rates.append(Decimal(raw_rate) / Decimal("100"))
            for raw_rate in re.findall(r"(?<!\d)(\d+(?:\.\d+)?)\s*折", normalized):
                value = Decimal(raw_rate)
                rates.append(value / (Decimal("10") if value <= 10 else Decimal("100")))
        valid_rates = [rate for rate in rates if Decimal("0") < rate <= Decimal("1")]
        return min(valid_rates) if valid_rates else None

    @staticmethod
    def _type1_requirement_key(item_id: uuid.UUID) -> str:
        return f"R{item_id.hex[:12]}"

    @staticmethod
    def _type2_requirement_key(item_id: uuid.UUID) -> str:
        return f"R{item_id.hex[:12]}"

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
            cost_price=product.cost_price,
            sku=product.sku,
            item_number=product.item_number,
            barcode_text=product.barcode_text,
            brand=product.brand,
            model=product.model,
            product_name=product.product_name,
            category_id=None,
            category_level1_name=product.category_level1_name,
            category_level2_name=product.category_level2_name,
            category_level3_name=product.category_level3_name,
            product_specification=product.product_specification,
        )

    @staticmethod
    def _is_quotable_type2_product(
        product: Product,
        max_price: Decimal | None,
        *,
        required_discount_rate: Decimal | None = None,
    ) -> bool:
        price = product.cost_price
        price_is_valid = price is not None and price > 0 and (
            max_price is None or price <= max_price
        )
        if not price_is_valid:
            return False
        return required_discount_rate is None or (
            product.discount_rate is not None
            and product.discount_rate <= required_discount_rate
        )

    @staticmethod
    def _is_quotable_type1_product(
        product: Product, max_price: Decimal | None
    ) -> bool:
        price = product.cost_price
        return price is not None and price > 0 and (
            max_price is None or price <= max_price
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
            "category_id": None,
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
            "packaging_list": product.packaging_list,
            "discount_rate": (
                str(product.discount_rate) if product.discount_rate is not None else None
            ),
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
        discount_compliance = None
        if product.discount_rate is not None:
            discount_compliance = "是" if product.discount_rate <= Decimal("0.88") else "否"
        return {
            "cost_price": str(product.cost_price) if product.cost_price is not None else None,
            "jd_price": str(product.jd_price) if product.jd_price is not None else None,
            "agreement_price": str(product.agreement_price)
            if product.agreement_price is not None
            else None,
            "selected_unit_price": str(selected_unit_price),
            "discount_rate": (
                str(product.discount_rate) if product.discount_rate is not None else None
            ),
            "discount_compliance": discount_compliance,
            "price_valid_until": None,
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
