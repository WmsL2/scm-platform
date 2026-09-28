from __future__ import annotations

import hashlib
import json
import tempfile
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.config import get_settings
from app.core.transaction import transaction_scope
from app.infrastructure.adapters import ObjectStorage, get_object_storage
from app.integrations.kimi.client import KimiClient, KimiConfigurationError, KimiProviderError
from app.modules.bid.domain.lifecycle import BidFileType, BidProjectStatus, ensure_transition
from app.modules.bid.infrastructure.models import BidProjectEvent, BidProjectFile
from app.modules.recommendation.infrastructure.models import (
    PptGenerationTask,
    PptSolutionPackage,
    PptSolutionPackageItem,
)
from app.modules.recommendation.infrastructure.ppt_repository import PptSolutionRepository
from app.modules.recommendation.ppt_schemas import (
    PptGenerationStatus,
    PptGenerationTaskResponse,
    PptPackageCreateRequest,
    PptPackageItemResponse,
    PptPackageResponse,
)
from app.modules.recommendation.template.schemas import RecommendationRunStatus


class PptSolutionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: ObjectStorage | None = None,
        kimi: KimiClient | None = None,
    ) -> None:
        self.session = session
        self.storage = storage or get_object_storage()
        self.kimi = kimi or KimiClient()
        self.repository = PptSolutionRepository(session)

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
            template = (
                None
                if use_default_template
                else await self.repository.latest_template(project_id)
            )
            task = PptGenerationTask(
                project_id=project_id,
                run_id=run_id,
                template_file_id=template.id if template else None,
                status=PptGenerationStatus.QUEUED.value,
                provider="kimi-hosted-agent",
                model=settings.kimi_model,
                prompt_version=settings.kimi_prompt_version,
                created_by=actor_id,
            )
            self.session.add(task)
            await self.session.flush()
            await self.session.refresh(task)
        return self._task_response(task)

    async def execute_generation(self, task_id: uuid.UUID) -> None:
        task = await self._start_task(task_id)
        saved_key: str | None = None
        try:
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
            # Provider execution can take minutes. Close the read transaction before
            # uploading resources and polling Kimi so no database lock/connection is held.
            await self.session.commit()
            with tempfile.TemporaryDirectory(prefix="scm-ppt-") as directory:
                workdir = Path(directory)
                source_path = workdir / "selected-products.json"
                source_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
                template_path = None
                if template is not None:
                    template_path = workdir / "customer-template.pptx"
                    await self.storage.copy_to(template.storage_key, template_path)
                artifact = await self.kimi.generate_ppt(
                    title=f"{project.project_name} PPT 方案",
                    instruction=self._generation_instruction(template is not None),
                    source_path=source_path,
                    template_path=template_path,
                )
            version = await self.repository.next_output_version(project.id)
            saved_key = await self.storage.save(
                f"bid-projects/{project.id}/ppt-exports/v{version}.pptx", artifact.content
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
                    file_size=len(artifact.content),
                    sha256=hashlib.sha256(artifact.content).hexdigest(),
                    created_by=locked_task.created_by,
                )
                self.session.add(output)
                await self.session.flush()
                locked_task.status = PptGenerationStatus.SUCCEEDED.value
                locked_task.output_file_id = output.id
                locked_task.provider_session_id = artifact.session_id[:255]
                locked_task.provider_artifact_id = artifact.artifact_id[:255]
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
        except (KimiConfigurationError, KimiProviderError, AppError) as exc:
            if saved_key:
                await self.storage.delete(saved_key)
            await self._fail_task(task_id, exc.message if isinstance(exc, AppError) else str(exc))
        except Exception:
            if saved_key:
                await self.storage.delete(saved_key)
            await self._fail_task(task_id, "PPT 生成失败，请稍后重试")

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

    @staticmethod
    def _generation_instruction(has_template: bool) -> str:
        template_rule = (
            "严格参考绑定的 customer-template.pptx 的整体布局、颜色和品牌元素。"
            if has_template
            else "未提供甲方模板，请使用系统默认的简洁商务商品方案版式。"
        )
        return (
            "读取 selected-products.json，生成中文、原生可编辑的 .pptx。"
            f"{template_rule}只使用文件中的真实商品、价格、参数和人工说明，不得补造事实。"
            "packages 是人工确认的套装，按套装整体展示并列明组成、数量和总价；"
            "未进入套装的 single_products 按单品方案展示。价格保留两位小数。"
            "所有元素必须可编辑，不要把整页做成图片，最终文件写入 output 目录。"
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
