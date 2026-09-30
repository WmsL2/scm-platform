from __future__ import annotations

import hashlib
import logging
import tempfile
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.config import get_settings
from app.core.transaction import transaction_scope
from app.infrastructure.adapters import ObjectStorage, get_object_storage
from app.modules.bid.domain.lifecycle import BidFileType, BidProjectStatus, ensure_transition
from app.modules.bid.infrastructure.models import BidProjectEvent, BidProjectFile
from app.modules.catalog.application.media import local_media_storage_key
from app.modules.recommendation.application.agent_runner import StructuredProvider
from app.modules.recommendation.application.ppt_plan_runner import PptPlanAgentRunner
from app.modules.recommendation.application.ppt_renderer import PptRenderer
from app.modules.recommendation.infrastructure.models import (
    PptGenerationTask,
    PptRecommendationConfig,
    PptSolutionPackage,
    PptSolutionPackageItem,
    PptSolutionPlan,
    RecommendationCandidate,
    RecommendationConfirmation,
)
from app.modules.recommendation.infrastructure.ppt_repository import PptSolutionRepository
from app.modules.recommendation.ppt_schemas import (
    PptGenerationStatus,
    PptGenerationTaskResponse,
    PptPackageCreateRequest,
    PptPackageItemResponse,
    PptPackageResponse,
    PptPriceBandAvailabilityResponse,
    PptRecommendationConfigResponse,
    PptRecommendationConfigUpdateRequest,
    PptSolutionPlanItemResponse,
    PptSolutionPlanResponse,
)
from app.modules.recommendation.template.schemas import RecommendationRunStatus

logger = logging.getLogger(__name__)


class PptSolutionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: ObjectStorage | None = None,
        renderer: PptRenderer | None = None,
    ) -> None:
        self.session = session
        self.storage = storage or get_object_storage()
        self.renderer = renderer or PptRenderer()
        self.repository = PptSolutionRepository(session)

    async def config(self, project_id: uuid.UUID) -> PptRecommendationConfigResponse | None:
        config = await self.repository.config(project_id)
        return self._config_response(config) if config else None

    async def save_config(
        self,
        project_id: uuid.UUID,
        payload: PptRecommendationConfigUpdateRequest,
        actor_id: uuid.UUID,
    ) -> PptRecommendationConfigResponse:
        async with transaction_scope(self.session):
            project = await self.repository.project_for_update(project_id)
            if project is None:
                raise AppError("PPT_SOLUTION_PROJECT_NOT_FOUND", "PPT 方案项目不存在", 404)
            if project.status not in {
                BidProjectStatus.IMPORTED.value,
                BidProjectStatus.SELECTING.value,
            }:
                raise AppError("PPT_CONFIG_NOT_EDITABLE", "当前项目状态不能调整推品配置", 409)
            config = await self.repository.config(project_id, lock=True)
            values = [item.model_dump(mode="json") for item in payload.price_bands]
            if config is None:
                config = PptRecommendationConfig(
                    project_id=project_id,
                    recommendation_mode=payload.recommendation_mode.value,
                    price_bands=values,
                    candidate_count_per_band=payload.candidate_count_per_band,
                    plan_count_per_band=payload.plan_count_per_band,
                    fulfillment_deadline=payload.fulfillment_deadline,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                self.session.add(config)
            else:
                config.recommendation_mode = payload.recommendation_mode.value
                config.price_bands = values
                config.candidate_count_per_band = payload.candidate_count_per_band
                config.plan_count_per_band = payload.plan_count_per_band
                config.fulfillment_deadline = payload.fulfillment_deadline
                config.updated_by = actor_id
            await self.session.flush()
            await self.session.refresh(config)
        return self._config_response(config)

    async def list_plans(self, run_id: uuid.UUID) -> list[PptSolutionPlanResponse]:
        candidates = {
            candidate.id: candidate for candidate in await self.repository.candidates(run_id)
        }
        return [
            self._plan_response(item, candidates) for item in await self.repository.plans(run_id)
        ]

    async def plan_availability(
        self, run_id: uuid.UUID
    ) -> list[PptPriceBandAvailabilityResponse]:
        run = await self.repository.run(run_id)
        if run is None:
            raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
        config = await self.repository.config(run.project_id)
        if config is None:
            raise AppError("PPT_RECOMMENDATION_CONFIG_REQUIRED", "类型 5 推品配置不存在", 409)
        return self._plan_availability(config, await self.repository.candidates(run_id))

    async def create_generated_plans(self, run_id: uuid.UUID) -> list[PptSolutionPlanResponse]:
        """Persist distinct Type-5 proposals from the complete frozen product pool."""
        async with transaction_scope(self.session):
            run = await self.repository.run_for_update(run_id)
            if run is None:
                raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
            project = await self.repository.project_for_update(run.project_id)
            config = await self.repository.config(run.project_id, lock=True)
            if project is None or config is None:
                raise AppError("PPT_RECOMMENDATION_CONFIG_REQUIRED", "类型 5 推品配置不存在", 409)
            existing = await self.repository.plans(run_id)
            if existing:
                return await self.list_plans(run_id)
            candidates = await self.repository.candidates(run_id)
            for plan in self._build_plans(config, candidates):
                self.session.add(
                    PptSolutionPlan(
                        run_id=run_id,
                        price_band_index=plan["price_band_index"],
                        plan_no=plan["plan_no"],
                        plan_type=plan["plan_type"],
                        name=plan["name"],
                        summary=plan["summary"],
                        candidate_ids=plan["candidate_ids"],
                        selection_source="DETERMINISTIC",
                        selection_provider=None,
                        selection_model=None,
                        selection_prompt_version=None,
                    )
                )
            await self.session.flush()
        return await self.list_plans(run_id)

    async def create_ai_generated_plans(
        self, run_id: uuid.UUID, provider: StructuredProvider
    ) -> list[PptSolutionPlanResponse]:
        """Persist Type-5 AI proposals after the complete candidate pool is frozen."""
        # Do not hold a Run row lock while waiting for the external structured provider.
        run = await self.repository.run(run_id)
        if run is None:
            raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
        config = await self.repository.config(run.project_id)
        if config is None:
            raise AppError("PPT_RECOMMENDATION_CONFIG_REQUIRED", "类型 5 推品配置不存在", 409)
        candidates = await self.repository.candidates(run_id)
        proposals = await PptPlanAgentRunner(provider).run(config, candidates)
        expected = self._expected_plan_slots(config, candidates)
        by_slot = {(item.price_band_index, item.plan_no): item for item in proposals.plans}
        if set(by_slot) != expected or len(by_slot) != len(proposals.plans):
            raise AppError(
                "PPT_PLAN_AI_CONTRACT_INVALID", "方案 AI 未按每个价格档返回完整且唯一的方案", 422
            )
        async with transaction_scope(self.session):
            locked_run = await self.repository.run_for_update(run_id)
            if locked_run is None:
                raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
            if await self.repository.plans(run_id):
                raise AppError("PPT_PLAN_ALREADY_CREATED", "类型 5 方案已经生成", 409)
            for slot in sorted(expected):
                proposal = by_slot[slot]
                maximum = self._decimal_value(config.price_bands[slot[0] - 1].get("max_price"))
                if maximum is None:
                    raise AppError("PPT_PLAN_AI_CONTRACT_INVALID", "价格档配置无效", 422)
                permitted = self._band_candidates(
                    candidates,
                    self._decimal_value(config.price_bands[slot[0] - 1].get("min_price")),
                    maximum,
                )
                allowed_ids = {item.id for item in permitted}
                ids = list(proposal.candidate_ids)
                if len(ids) != config.candidate_count_per_band or any(
                    item not in allowed_ids for item in ids
                ):
                    raise AppError(
                        "PPT_PLAN_AI_CANDIDATE_INVALID",
                        "方案 AI 返回了价格档外或数量不符的商品",
                        422,
                    )
                mode = config.recommendation_mode
                plan_type = (
                    "SINGLE"
                    if mode == "SINGLE" or (mode == "MIXED" and slot[1] % 2 == 1)
                    else "COMBINATION"
                )
                self.session.add(
                    PptSolutionPlan(
                        run_id=run_id,
                        price_band_index=slot[0],
                        plan_no=slot[1],
                        plan_type=plan_type,
                        name=proposal.name.strip(),
                        summary=proposal.summary.strip() if proposal.summary else None,
                        candidate_ids=[str(item) for item in ids],
                        selection_source="AI",
                        selection_provider=provider.provider,
                        selection_model=provider.model,
                        selection_prompt_version=f"{provider.prompt_version}:ppt-plan-v1",
                    )
                )
        return await self.list_plans(run_id)

    async def create_package(
        self, run_id: uuid.UUID, payload: PptPackageCreateRequest, actor_id: uuid.UUID
    ) -> PptPackageResponse:
        async with transaction_scope(self.session):
            run = await self.repository.run_for_update(run_id)
            if run is None:
                raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
            project = await self.repository.project_for_update(run.project_id)
            if project is None:
                raise AppError("PPT_SOLUTION_PROJECT_NOT_FOUND", "PPT 方案项目不存在", 404)
            if project.status != BidProjectStatus.SELECTING.value:
                raise AppError("PPT_PACKAGE_NOT_EDITABLE", "当前项目状态不能调整套装", 409)
            ids = [item.candidate_id for item in payload.items]
            rows = await self.repository.confirmed_candidates(run_id, ids)
            if len(rows) != len(ids):
                raise AppError("PPT_PACKAGE_CANDIDATE_INVALID", "套装只能使用已人工确认的商品", 409)
            by_id = {candidate.id: (candidate, confirmation) for candidate, confirmation in rows}
            package = PptSolutionPackage(
                run_id=run_id,
                name=payload.name.strip(),
                price_tier=payload.price_tier,
                total_price=Decimal(0),
                reason=payload.reason.strip() if payload.reason else None,
                is_selected=True,
                created_by=actor_id,
                selected_by=actor_id,
                selected_at=datetime.now(UTC).replace(tzinfo=None),
            )
            self.session.add(package)
            await self.session.flush()
            total = Decimal(0)
            for index, input_item in enumerate(payload.items, start=1):
                candidate, confirmation = by_id[input_item.candidate_id]
                unit_price = self._candidate_price(
                    candidate.price_snapshot, confirmation.campaign_price
                )
                line_total = unit_price * input_item.quantity
                total += line_total
                self.session.add(
                    PptSolutionPackageItem(
                        package_id=package.id,
                        candidate_id=candidate.id,
                        quantity=input_item.quantity,
                        unit_price=unit_price,
                        line_total=line_total,
                        sort_order=index,
                    )
                )
            if payload.price_tier is not None and total > payload.price_tier:
                raise AppError("PPT_PACKAGE_OVER_BUDGET", "套装总价超过所选价格档位", 422)
            package.total_price = total
            await self.session.flush()
            await self.session.refresh(package)
        return next(item for item in await self.list_packages(run_id) if item.id == package.id)

    async def list_packages(self, run_id: uuid.UUID) -> list[PptPackageResponse]:
        packages = await self.repository.packages(run_id)
        items = await self.repository.package_items([item.id for item in packages])
        grouped: dict[uuid.UUID, list[PptPackageItemResponse]] = {}
        for item, candidate in items:
            grouped.setdefault(item.package_id, []).append(
                PptPackageItemResponse(
                    id=item.id,
                    candidate_id=item.candidate_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                    sort_order=item.sort_order,
                    product_snapshot=candidate.product_snapshot,
                    price_snapshot=candidate.price_snapshot,
                )
            )
        return [
            PptPackageResponse(
                id=package.id,
                run_id=package.run_id,
                name=package.name,
                price_tier=package.price_tier,
                total_price=package.total_price,
                reason=package.reason,
                is_selected=package.is_selected,
                items=grouped.get(package.id, []),
                created_at=package.created_at,
                updated_at=package.updated_at,
            )
            for package in packages
        ]

    async def delete_package(self, package_id: uuid.UUID, actor_id: uuid.UUID) -> bool:
        del actor_id
        async with transaction_scope(self.session):
            package = await self.repository.package_for_update(package_id)
            if package is None:
                raise AppError("PPT_PACKAGE_NOT_FOUND", "套装不存在", 404)
            run = await self.repository.run_for_update(package.run_id)
            if run is None:
                raise AppError("RECOMMENDATION_RUN_NOT_FOUND", "推品任务不存在", 404)
            project = await self.repository.project_for_update(run.project_id)
            if project is None or project.status != BidProjectStatus.SELECTING.value:
                raise AppError("PPT_PACKAGE_NOT_EDITABLE", "当前项目状态不能调整套装", 409)
            for item in await self.repository.package_items_for_update(package_id):
                await self.session.delete(item)
            await self.session.delete(package)
        return True

    async def create_generation(
        self,
        project_id: uuid.UUID,
        run_id: uuid.UUID,
        actor_id: uuid.UUID,
        *,
        use_default_template: bool,
    ) -> PptGenerationTaskResponse:
        settings = get_settings()
        async with transaction_scope(self.session):
            project = await self.repository.project_for_update(project_id)
            run = await self.repository.run_for_update(run_id)
            if project is None or run is None or run.project_id != project.id:
                raise AppError("PPT_SOLUTION_PROJECT_NOT_FOUND", "PPT 方案项目不存在", 404)
            if project.status not in {
                BidProjectStatus.READY.value,
                BidProjectStatus.EXPORTED.value,
            }:
                raise AppError("PPT_SOLUTION_NOT_READY", "请先完成商品选择", 409)
            if run.status not in {
                RecommendationRunStatus.CONFIRMED.value,
                RecommendationRunStatus.EXPORTED.value,
            }:
                raise AppError("PPT_SOLUTION_RUN_NOT_CONFIRMED", "请先确认本次选品", 409)
            if not await self.repository.confirmed_candidates(run_id):
                raise AppError("PPT_SOLUTION_SELECTION_REQUIRED", "至少选择一个商品", 409)
            # Type 5 deliberately has one controlled system template. Keep the
            # request field for wire compatibility, but do not bind project files.
            del use_default_template
            template = None
            task = PptGenerationTask(
                project_id=project_id,
                run_id=run_id,
                template_file_id=template.id if template else None,
                status=PptGenerationStatus.QUEUED.value,
                provider="deepseek-python-pptx",
                model=settings.deepseek_model,
                prompt_version="ppt-local-v2",
                created_by=actor_id,
            )
            self.session.add(task)
            await self.session.flush()
            await self.session.refresh(task)
        return self._task_response(task)

    async def execute_generation(self, task_id: uuid.UUID) -> None:
        saved_key: str | None = None
        try:
            task = await self._start_task(task_id)
            project = await self.repository.project(task.project_id)
            if project is None:
                raise AppError("PPT_SOLUTION_PROJECT_NOT_FOUND", "PPT 方案项目不存在", 404)
            candidates = await self.repository.confirmed_candidates(task.run_id)
            packages = await self.list_packages(task.run_id)
            packaged_candidate_ids = {
                item.candidate_id for package in packages for item in package.items
            }
            template = (
                await self.session.get(BidProjectFile, task.template_file_id)
                if task.template_file_id
                else None
            )
            source = {
                "project": {
                    "project_code": project.project_code,
                    "project_name": project.project_name,
                    "buyer_name": project.buyer_name,
                    "requirement": project.remark,
                },
                "single_products": [
                    {
                        "candidate_id": str(candidate.id),
                        "product": candidate.product_snapshot,
                        "supplier": candidate.supplier_snapshot,
                        "prices": candidate.price_snapshot,
                        "manual": {
                            "campaign_price": (
                                str(confirmation.campaign_price)
                                if confirmation.campaign_price is not None
                                else None
                            ),
                            "delivery_status": confirmation.delivery_status,
                            "inventory_status": confirmation.inventory_status,
                            "fulfillment_cycle": confirmation.fulfillment_cycle,
                            "evidence": confirmation.evidence,
                        },
                    }
                    for candidate, confirmation in candidates
                    if candidate.id not in packaged_candidate_ids
                ],
                "packages": [item.model_dump(mode="json") for item in packages],
            }
            product_images = await self._load_product_images(candidates)
            # Rendering can load a customer template. Close the read transaction before
            # copying that file and creating the local PPTX so no database lock is held.
            await self.session.commit()
            with tempfile.TemporaryDirectory(prefix="scm-ppt-") as directory:
                workdir = Path(directory)
                template_path = None
                if template is not None:
                    template_path = workdir / "customer-template.pptx"
                    await self.storage.copy_to(template.storage_key, template_path)
                content = self.renderer.render(
                    source,
                    template_path=template_path,
                    product_images=product_images,
                )
            version = await self.repository.next_output_version(project.id)
            saved_key = await self.storage.save(
                f"bid-projects/{project.id}/ppt-exports/v{version}.pptx", content
            )
            async with transaction_scope(self.session):
                locked_task = await self.repository.generation_for_update(task_id)
                project = await self.repository.project_for_update(project.id)
                if locked_task is None or project is None:
                    raise AppError("PPT_GENERATION_TASK_NOT_FOUND", "PPT 生成任务不存在", 404)
                output = BidProjectFile(
                    project_id=project.id,
                    file_type=BidFileType.PPT_EXPORT.value,
                    version_no=version,
                    original_filename=f"{project.project_code}-PPT方案-V{version}.pptx",
                    storage_key=saved_key,
                    file_size=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    created_by=locked_task.created_by,
                )
                self.session.add(output)
                await self.session.flush()
                locked_task.status = PptGenerationStatus.SUCCEEDED.value
                locked_task.output_file_id = output.id
                locked_task.provider_session_id = None
                locked_task.provider_artifact_id = "local-python-pptx"
                locked_task.completed_at = datetime.now(UTC).replace(tzinfo=None)
                if project.status == BidProjectStatus.READY.value:
                    ensure_transition(project.status, BidProjectStatus.EXPORTED)
                    before = project.status
                    project.status = BidProjectStatus.EXPORTED.value
                    project.updated_by = locked_task.created_by
                    self.session.add(
                        BidProjectEvent(
                            project_id=project.id,
                            from_status=before,
                            to_status=project.status,
                            event_type="PPT_GENERATED",
                            actor_id=locked_task.created_by,
                            note=f"生成 PPT 方案第 {version} 版",
                        )
                    )
            # `next_output_version()` above is a read that starts SQLAlchemy's
            # implicit transaction. In this standalone worker that means
            # transaction_scope participates instead of owning the commit; without
            # an explicit commit the output record is rolled back on session close
            # while the PPTX file has already been written to local storage.
            await self.session.commit()
        except AppError as exc:
            if saved_key:
                await self.storage.delete(saved_key)
            await self._fail_task(task_id, exc.message if isinstance(exc, AppError) else str(exc))
        except Exception as exc:
            logger.exception("PPT generation failed: task_id=%s", task_id)
            if saved_key:
                await self.storage.delete(saved_key)
            await self._fail_task(
                task_id,
                f"PPT 生成失败（{type(exc).__name__}），请检查服务端日志。",
            )

    async def list_generations(self, project_id: uuid.UUID) -> list[PptGenerationTaskResponse]:
        return [self._task_response(task) for task in await self.repository.generations(project_id)]

    async def download(
        self, task_id: uuid.UUID, file_id: uuid.UUID
    ) -> tuple[BidProjectFile, bytes]:
        file = await self.repository.generation_output(task_id, file_id)
        if file is None:
            raise AppError("PPT_EXPORT_NOT_FOUND", "PPT 文件不存在", 404)
        return file, await self.storage.read(file.storage_key)

    async def _start_task(self, task_id: uuid.UUID) -> PptGenerationTask:
        async with transaction_scope(self.session):
            task = await self.repository.generation_for_update(task_id)
            if task is None:
                raise AppError("PPT_GENERATION_TASK_NOT_FOUND", "PPT 生成任务不存在", 404)
            if task.status != PptGenerationStatus.QUEUED.value:
                raise AppError("PPT_GENERATION_TASK_STATE_INVALID", "PPT 任务状态无效", 409)
            task.status = PptGenerationStatus.RUNNING.value
            task.started_at = datetime.now(UTC).replace(tzinfo=None)
        return task

    async def _fail_task(self, task_id: uuid.UUID, error: str) -> None:
        async with transaction_scope(self.session):
            task = await self.repository.generation_for_update(task_id)
            if task is None:
                return
            task.status = PptGenerationStatus.FAILED.value
            task.error = error.strip()[:4000]
            task.completed_at = datetime.now(UTC).replace(tzinfo=None)
        # See execute_generation(): this method is also called by the standalone
        # worker after a read has opened an implicit transaction.
        await self.session.commit()

    async def mark_generation_failed(self, task_id: uuid.UUID, error: str) -> None:
        """Persist a dispatch failure so the UI never waits on a stuck queued task."""
        await self._fail_task(task_id, error)

    @classmethod
    def _expected_plan_slots(
        cls, config: PptRecommendationConfig, candidates: Sequence[RecommendationCandidate]
    ) -> set[tuple[int, int]]:
        slots: set[tuple[int, int]] = set()
        for band_index, raw_band in enumerate(config.price_bands, start=1):
            minimum = cls._decimal_value(raw_band.get("min_price"))
            maximum = cls._decimal_value(raw_band.get("max_price"))
            if maximum is None:
                continue
            if (
                len(cls._band_candidates(candidates, minimum, maximum))
                < config.candidate_count_per_band
            ):
                continue
            slots.update(
                (band_index, plan_no) for plan_no in range(1, config.plan_count_per_band + 1)
            )
        return slots

    @classmethod
    def _plan_availability(
        cls, config: PptRecommendationConfig, candidates: Sequence[RecommendationCandidate]
    ) -> list[PptPriceBandAvailabilityResponse]:
        values: list[PptPriceBandAvailabilityResponse] = []
        for band_index, raw_band in enumerate(config.price_bands, start=1):
            minimum = cls._decimal_value(raw_band.get("min_price"))
            maximum = cls._decimal_value(raw_band.get("max_price"))
            if maximum is None:
                continue
            count = len(cls._band_candidates(candidates, minimum, maximum))
            required = config.candidate_count_per_band
            label = cls._price_band_label(minimum, maximum)
            can_generate = count >= required
            values.append(
                PptPriceBandAvailabilityResponse(
                    price_band_index=band_index,
                    min_price=minimum,
                    max_price=maximum,
                    candidate_count=count,
                    required_count=required,
                    can_generate=can_generate,
                    message=(
                        f"{label}：有 {count} 件，满足每方案 {required} 件的要求"
                        if can_generate
                        else f"{label}：只有 {count} 件，还差 {required - count} 件才能组成每个方案"
                    ),
                )
            )
        return values

    @classmethod
    def _build_plans(
        cls,
        config: PptRecommendationConfig,
        candidates: Sequence[RecommendationCandidate],
    ) -> list[dict[str, object]]:
        """Turn the complete frozen Type-5 product pool into distinct proposals.

        The configured quantity is the number of products in *each* proposal, not a
        cap on the candidate pool.  Proposals intentionally use overlapping windows
        when needed, while rotating their starting positions so they are not copies.
        """
        plans: list[dict[str, object]] = []
        mode = config.recommendation_mode
        for band_index, raw_band in enumerate(config.price_bands, start=1):
            minimum = cls._decimal_value(raw_band.get("min_price"))
            maximum = cls._decimal_value(raw_band.get("max_price"))
            if maximum is None:
                continue
            available = cls._band_candidates(candidates, minimum, maximum)
            quantity = config.candidate_count_per_band
            if len(available) < quantity:
                continue
            for plan_no in range(1, config.plan_count_per_band + 1):
                plan_type = (
                    "SINGLE"
                    if mode == "SINGLE" or (mode == "MIXED" and plan_no % 2 == 1)
                    else "COMBINATION"
                )
                step = max(1, quantity // 2)
                start = ((plan_no - 1) * step) % len(available)
                selected = [
                    available[(start + index) % len(available)] for index in range(quantity)
                ]
                band_label = cls._price_band_label(minimum, maximum)
                plan_type_label = "单品" if plan_type == "SINGLE" else "组合"
                plans.append(
                    {
                        "price_band_index": band_index,
                        "plan_no": plan_no,
                        "plan_type": plan_type,
                        "name": f"{band_label} · {plan_type_label}方案 {plan_no}",
                        "summary": (
                            f"包含 {len(selected)} 件商品；每件商品的协议价均在 {band_label} 内。"
                        ),
                        "candidate_ids": [str(candidate.id) for candidate in selected],
                    }
                )
        return plans

    @classmethod
    def _band_candidates(
        cls,
        candidates: Sequence[RecommendationCandidate],
        minimum: Decimal | None,
        maximum: Decimal,
    ) -> list[RecommendationCandidate]:
        return [
            candidate
            for candidate in candidates
            if cls._candidate_agreement_price(candidate) <= maximum
            and (minimum is None or cls._candidate_agreement_price(candidate) >= minimum)
        ]

    @staticmethod
    def _decimal_value(value: object) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            return None

    @classmethod
    def _candidate_agreement_price(cls, candidate: RecommendationCandidate) -> Decimal:
        value = cls._decimal_value(candidate.price_snapshot.get("agreement_price"))
        return value if value is not None and value >= 0 else Decimal(0)

    @staticmethod
    def _price_band_label(minimum: Decimal | None, maximum: Decimal) -> str:
        return f"{minimum if minimum is not None else 0}–{maximum} 元"

    @staticmethod
    def _candidate_price(snapshot: dict[str, object], campaign_price: Decimal | None) -> Decimal:
        if campaign_price is not None:
            return campaign_price
        raw = snapshot.get("agreement_price")
        try:
            value = Decimal(str(raw))
        except (InvalidOperation, TypeError):
            raise AppError("PPT_PACKAGE_PRICE_REQUIRED", "套装商品缺少可计算价格", 422) from None
        if value < 0:
            raise AppError("PPT_PACKAGE_PRICE_REQUIRED", "套装商品价格不能小于零", 422)
        return value

    async def _load_product_images(
        self,
        candidates: Sequence[tuple[RecommendationCandidate, RecommendationConfirmation]],
    ) -> dict[str, bytes]:
        """Read locally managed image references without making network requests."""
        images: dict[str, bytes] = {}
        for candidate, _confirmation in candidates:
            product_snapshot = getattr(candidate, "product_snapshot", {})
            if not isinstance(product_snapshot, dict):
                continue
            image_key = local_media_storage_key(product_snapshot.get("image_reference"))
            product_id = str(product_snapshot.get("id") or getattr(candidate, "product_id", ""))
            if image_key is None or not product_id:
                continue
            try:
                images[product_id] = await self.storage.read(image_key)
            except (OSError, ValueError):
                continue
        return images

    @staticmethod
    def _plan_response(
        plan: PptSolutionPlan, candidates: dict[uuid.UUID, RecommendationCandidate]
    ) -> PptSolutionPlanResponse:
        return PptSolutionPlanResponse(
            id=plan.id,
            run_id=plan.run_id,
            price_band_index=plan.price_band_index,
            plan_no=plan.plan_no,
            plan_type=plan.plan_type,  # type: ignore[arg-type]
            name=plan.name,
            summary=plan.summary,
            candidate_ids=[uuid.UUID(value) for value in plan.candidate_ids],
            selection_source=plan.selection_source,
            selection_provider=plan.selection_provider,
            selection_model=plan.selection_model,
            selection_prompt_version=plan.selection_prompt_version,
            items=[
                PptSolutionPlanItemResponse(
                    candidate_id=candidate.id,
                    rank=candidate.rank,
                    product_snapshot=candidate.product_snapshot,
                    price_snapshot=candidate.price_snapshot,
                )
                for candidate_id in plan.candidate_ids
                if (candidate := candidates.get(uuid.UUID(candidate_id))) is not None
            ],
            created_at=plan.created_at,
        )

    @staticmethod
    def _task_response(task: PptGenerationTask) -> PptGenerationTaskResponse:
        return PptGenerationTaskResponse(
            id=task.id,
            project_id=task.project_id,
            run_id=task.run_id,
            template_file_id=task.template_file_id,
            output_file_id=task.output_file_id,
            status=PptGenerationStatus(task.status),
            provider=task.provider,
            model=task.model,
            prompt_version=task.prompt_version,
            error=task.error,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    def _config_response(config: PptRecommendationConfig) -> PptRecommendationConfigResponse:
        return PptRecommendationConfigResponse.model_validate(
            {
                "project_id": config.project_id,
                "recommendation_mode": config.recommendation_mode,
                "price_bands": config.price_bands,
                "candidate_count_per_band": config.candidate_count_per_band,
                "plan_count_per_band": config.plan_count_per_band,
                "fulfillment_deadline": config.fulfillment_deadline,
                "created_at": config.created_at,
                "updated_at": config.updated_at,
            }
        )
