from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams, PageResult
from app.core.transaction import transaction_scope
from app.infrastructure.adapters import ObjectStorage, get_object_storage
from app.modules.bid.domain.lifecycle import (
    BidFileType,
    BidImportStatus,
    BidItemStatus,
    BidProjectStatus,
    BidProjectType,
    ensure_transition,
)
from app.modules.bid.infrastructure.models import (
    BidProject,
    BidProjectEvent,
    BidProjectFile,
    BidProjectItem,
    BidTemplate,
)
from app.modules.bid.infrastructure.repository import BidProjectRepository
from app.modules.bid.schemas import (
    BidCurrentSelectionResponse,
    BidProjectCreateResponse,
    BidProjectDetailResponse,
    BidProjectEventResponse,
    BidProjectFileResponse,
    BidProjectItemResponse,
    BidProjectListItem,
    BidProjectStatusResponse,
)
from app.modules.recommendation.template.models import RecommendationTemplateMapping
from app.modules.recommendation.template.schemas import (
    RecommendationTemplateFileResponse,
    RecommendationTemplateMappingResponse,
    RecommendationTemplateMappingUpdateRequest,
    RecommendationTemplateStructureResponse,
)
from app.modules.system.service import BusinessSequenceService

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_PROJECT_ITEMS = 100_000


class BidProjectService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self.session = session
        self.storage = storage or get_object_storage()
        self.repository = BidProjectRepository(session)

    async def create(
        self,
        *,
        project_name: str,
        buyer_name: str,
        start_at: datetime | None,
        deadline_at: datetime | None,
        remark: str | None,
        filename: str | None,
        file_bytes: bytes | None,
        recommendation_template_filename: str | None = None,
        recommendation_template_bytes: bytes | None = None,
        project_type: BidProjectType = BidProjectType.FILTER_RECOMMENDATION,
        actor_id: uuid.UUID,
    ) -> BidProjectCreateResponse:
        if start_at is not None and deadline_at is not None and start_at > deadline_at:
            raise AppError("BID_PROJECT_INVALID_TIME_RANGE", "项目开始时间不能晚于截止时间", 422)
        if project_type == BidProjectType.PPT_SOLUTION:
            raise AppError("BID_PROJECT_TYPE_NOT_AVAILABLE", "PPT 方案项目暂未开放", 409)
        if project_type == BidProjectType.FILTER_RECOMMENDATION:
            if (
                recommendation_template_filename is not None
                or recommendation_template_bytes is not None
            ):
                raise AppError(
                    "RECOMMENDATION_TEMPLATE_NOT_ALLOWED",
                    "筛选推品项目不接受自由推品模板",
                    422,
                )
            if filename is None or file_bytes is None:
                raise AppError("BID_EXCEL_REQUIRED", "筛选推品必须上传客户需求 Excel", 422)
            self._validate_upload(filename, file_bytes)
        else:
            if not remark or len(remark.strip()) < 20:
                raise AppError(
                    "FREE_RECOMMENDATION_REMARK_REQUIRED",
                    "自由推品需求说明至少需要 20 个有效字符",
                    422,
                )
            if recommendation_template_filename is None or recommendation_template_bytes is None:
                raise AppError("RECOMMENDATION_TEMPLATE_REQUIRED", "自由推品必须上传推荐模板", 422)
            self._validate_recommendation_template(
                recommendation_template_filename, recommendation_template_bytes
            )
        project_id = uuid.uuid4()
        template: BidTemplate | None = None
        parsed_rows: list[dict[str, Any]] = []
        import_status = BidImportStatus.MAPPING_REQUIRED.value
        import_error: str | None = "未识别到已启用模板，需要完成字段映射后再解析"
        if project_type == BidProjectType.FILTER_RECOMMENDATION:
            assert file_bytes is not None
            try:
                template = await self._recognize_template(file_bytes)
                if template is not None:
                    parsed_rows = self._parse_rows(file_bytes, template)
                    import_status = BidImportStatus.PARSED.value
                    import_error = None
            except AppError as exc:
                import_status = BidImportStatus.FAILED.value
                import_error = exc.message
        else:
            import_status = BidImportStatus.NOT_REQUIRED.value
            import_error = None

        analysis = None
        if project_type == BidProjectType.FREE_RECOMMENDATION:
            from app.modules.recommendation.template.analyzer import analyze_template

            assert recommendation_template_bytes is not None
            analysis = analyze_template(recommendation_template_bytes)

        saved_keys: list[str] = []
        try:
            storage_key: str | None = None
            template_storage_key: str | None = None
            if project_type == BidProjectType.FILTER_RECOMMENDATION:
                assert file_bytes is not None
                storage_key = await self.storage.save(
                    f"bid-projects/{project_id}/original/source.xlsx", file_bytes
                )
                saved_keys.append(storage_key)
            else:
                assert recommendation_template_bytes is not None
                template_storage_key = await self.storage.save(
                    f"bid-projects/{project_id}/recommendation-templates/v1.xlsx",
                    recommendation_template_bytes,
                )
                saved_keys.append(template_storage_key)
            async with transaction_scope(self.session):
                project_code = await BusinessSequenceService(self.session).issue_code("BID_PROJECT")
                project = BidProject(
                    id=project_id,
                    project_code=project_code,
                    project_name=project_name.strip(),
                    buyer_name=buyer_name.strip(),
                    start_at=start_at,
                    deadline_at=deadline_at,
                    remark=remark.strip() if remark else None,
                    template_id=template.id if template else None,
                    template_version=template.version if template else None,
                    status=BidProjectStatus.IMPORTED.value,
                    project_type=project_type.value,
                    import_status=import_status,
                    import_error=import_error,
                    total_item_count=len(parsed_rows),
                    processed_item_count=0,
                    created_by=actor_id,
                )
                self.session.add(project)
                if file_bytes is not None and filename is not None and storage_key is not None:
                    self.session.add(
                        BidProjectFile(
                            project_id=project_id,
                            file_type=BidFileType.ORIGINAL.value,
                            version_no=1,
                            original_filename=Path(filename).name[:255],
                            storage_key=storage_key,
                            file_size=len(file_bytes),
                            sha256=hashlib.sha256(file_bytes).hexdigest(),
                            created_by=actor_id,
                        )
                    )
                if template_storage_key is not None:
                    assert recommendation_template_bytes is not None
                    assert recommendation_template_filename is not None
                    assert analysis is not None
                    template_file = BidProjectFile(
                        project_id=project_id,
                        file_type=BidFileType.RECOMMENDATION_TEMPLATE.value,
                        version_no=1,
                        original_filename=Path(recommendation_template_filename).name[:255],
                        storage_key=template_storage_key,
                        file_size=len(recommendation_template_bytes),
                        sha256=hashlib.sha256(recommendation_template_bytes).hexdigest(),
                        created_by=actor_id,
                    )
                    self.session.add(template_file)
                    await self.session.flush()
                    self.session.add(
                        RecommendationTemplateMapping(
                            project_id=project_id,
                            template_file_id=template_file.id,
                            template_sha256=template_file.sha256,
                            sheet_name=analysis.sheet_name,
                            header_row=analysis.header_row,
                            data_start_row=analysis.data_start_row,
                            mapping_json=analysis.mapping_json,
                        )
                    )
                for row in parsed_rows:
                    self.session.add(BidProjectItem(project_id=project_id, **row))
                self._add_event(
                    project_id,
                    actor_id,
                    "PROJECT_CREATED",
                    None,
                    BidProjectStatus.IMPORTED.value,
                    import_error,
                )
                await self.session.flush()
        except Exception:
            for saved_key in saved_keys:
                await self.storage.delete(saved_key)
            raise
        return BidProjectCreateResponse(
            id=project_id,
            project_code=project_code,
            status=BidProjectStatus.IMPORTED,
            import_status=BidImportStatus(import_status),
            project_type=project_type,
            import_error=import_error,
            template_id=template.id if template else None,
            template_version=template.version if template else None,
            total_item_count=len(parsed_rows),
        )

    async def list_projects(
        self, page_params: PageParams, *, keyword: str | None, status: BidProjectStatus | None
    ) -> PageResult[BidProjectListItem]:
        rows, total = await self.repository.project_page(
            page=page_params.page,
            page_size=page_params.page_size,
            keyword=keyword.strip() if keyword else None,
            status=status.value if status else None,
        )
        return PageResult(
            items=[self._list_item(row) for row in rows],
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def add_recommendation_template(
        self, project_id: uuid.UUID, filename: str, file_bytes: bytes, actor_id: uuid.UUID
    ) -> RecommendationTemplateFileResponse:
        self._validate_recommendation_template(filename, file_bytes)
        project = await self._project_or_404(project_id)
        self._ensure_free_project(project)
        from app.modules.recommendation.template.analyzer import analyze_template

        analysis = analyze_template(file_bytes)
        storage_key: str | None = None
        try:
            async with transaction_scope(self.session):
                project = await self._project_or_404(project_id, lock=True)
                self._ensure_free_project(project)
                version = await self._next_template_version(project_id)
                storage_key = await self.storage.save(
                    f"bid-projects/{project_id}/recommendation-templates/v{version}.xlsx",
                    file_bytes,
                )
                file = BidProjectFile(
                    project_id=project_id,
                    file_type=BidFileType.RECOMMENDATION_TEMPLATE.value,
                    version_no=version,
                    original_filename=Path(filename).name[:255],
                    storage_key=storage_key,
                    file_size=len(file_bytes),
                    sha256=hashlib.sha256(file_bytes).hexdigest(),
                    created_by=actor_id,
                )
                self.session.add(file)
                await self.session.flush()
                self.session.add(
                    RecommendationTemplateMapping(
                        project_id=project_id,
                        template_file_id=file.id,
                        template_sha256=file.sha256,
                        sheet_name=analysis.sheet_name,
                        header_row=analysis.header_row,
                        data_start_row=analysis.data_start_row,
                        mapping_json=analysis.mapping_json,
                    )
                )
                await self.session.flush()
                await self.session.refresh(file)
                response = RecommendationTemplateFileResponse(
                    **self._file_response(file).model_dump(), mapping_confirmed=False
                )
        except Exception:
            if storage_key is not None:
                await self.storage.delete(storage_key)
            raise
        return response

    async def recommendation_templates(
        self, project_id: uuid.UUID
    ) -> list[RecommendationTemplateFileResponse]:
        project = await self._project_or_404(project_id)
        self._ensure_free_project(project)
        rows = await self.session.execute(
            select(BidProjectFile, RecommendationTemplateMapping)
            .outerjoin(
                RecommendationTemplateMapping,
                RecommendationTemplateMapping.template_file_id == BidProjectFile.id,
            )
            .where(
                BidProjectFile.project_id == project_id,
                BidProjectFile.file_type == BidFileType.RECOMMENDATION_TEMPLATE.value,
            )
            .order_by(BidProjectFile.version_no.asc())
        )
        return [
            RecommendationTemplateFileResponse(
                **self._file_response(file).model_dump(),
                mapping_confirmed=mapping is not None and mapping.confirmed_at is not None,
            )
            for file, mapping in rows.all()
        ]

    async def recommendation_template_mapping(
        self, project_id: uuid.UUID, file_id: uuid.UUID
    ) -> RecommendationTemplateMappingResponse:
        file, mapping = await self._recommendation_mapping_or_error(project_id, file_id)
        return self._mapping_response(file, mapping)

    async def recommendation_template_structure(
        self,
        project_id: uuid.UUID,
        file_id: uuid.UUID,
        *,
        sheet_name: str | None,
        header_row: int,
    ) -> RecommendationTemplateStructureResponse:
        file, _mapping = await self._recommendation_mapping_or_error(project_id, file_id)
        content = await self.storage.read(file.storage_key)
        if hashlib.sha256(content).hexdigest() != file.sha256:
            raise AppError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板摘要校验失败", 422)
        from app.modules.recommendation.template.analyzer import inspect_template_structure

        structure = inspect_template_structure(
            content,
            sheet_name=sheet_name.strip() if sheet_name else None,
            header_row=header_row,
        )
        return RecommendationTemplateStructureResponse.model_validate(
            structure, from_attributes=True
        )

    async def update_recommendation_template_mapping(
        self,
        project_id: uuid.UUID,
        file_id: uuid.UUID,
        payload: RecommendationTemplateMappingUpdateRequest,
        actor_id: uuid.UUID,
    ) -> RecommendationTemplateMappingResponse:
        async with transaction_scope(self.session):
            file, mapping = await self._recommendation_mapping_or_error(
                project_id, file_id, lock=True
            )
            mapping.sheet_name = payload.sheet_name.strip()
            mapping.header_row = payload.header_row
            mapping.data_start_row = payload.data_start_row
            mapping.mapping_json = payload.mapping_json
            content = await self.storage.read(file.storage_key)
            if (
                hashlib.sha256(content).hexdigest() != file.sha256
                or file.sha256 != mapping.template_sha256
            ):
                raise AppError("RECOMMENDATION_TEMPLATE_MAPPING_INVALID", "模板摘要校验失败", 422)
            from app.modules.recommendation.template.analyzer import validate_mapping_contract

            validate_mapping_contract(
                content,
                sheet_name=mapping.sheet_name,
                header_row=mapping.header_row,
                data_start_row=mapping.data_start_row,
                mapping_json=mapping.mapping_json,
            )
            mapping.confirmed_by = actor_id
            mapping.confirmed_at = datetime.now()
        return self._mapping_response(file, mapping)

    async def get(self, project_id: uuid.UUID) -> BidProjectDetailResponse:
        project = await self._project_or_404(project_id)
        files = await self.repository.files(project_id)
        events = await self.repository.events(project_id)
        return BidProjectDetailResponse(
            **self._list_item(project).model_dump(),
            remark=project.remark,
            template_id=project.template_id,
            template_version=project.template_version,
            import_error=project.import_error,
            submitted_file_id=project.submitted_file_id,
            files=[self._file_response(item) for item in files],
            events=[BidProjectEventResponse.model_validate(item) for item in events],
        )

    async def items(
        self,
        project_id: uuid.UUID,
        page_params: PageParams,
        *,
        status: BidItemStatus | None,
        keyword: str | None = None,
    ) -> PageResult[BidProjectItemResponse]:
        await self._project_or_404(project_id)
        rows, total = await self.repository.item_page(
            project_id,
            page=page_params.page,
            page_size=page_params.page_size,
            status=status.value if status else None,
            keyword=keyword.strip() or None if keyword else None,
        )
        return PageResult(
            items=[
                BidProjectItemResponse(
                    **BidProjectItemResponse.model_validate(item, from_attributes=True).model_dump(
                        exclude={"current_selection"}
                    ),
                    current_selection=(
                        BidCurrentSelectionResponse(
                            selection_id=selection.id,
                            product_id=selection.product_id,
                            supplier_id=selection.supplier_id,
                            selected_unit_price=selection.selected_unit_price,
                            requirement_snapshot=selection.requirement_snapshot,
                            product_snapshot=selection.product_snapshot,
                            supplier_snapshot=selection.supplier_snapshot,
                            price_snapshot=selection.price_snapshot,
                            note=selection.note,
                            created_at=selection.created_at,
                        )
                        if selection is not None
                        else None
                    ),
                )
                for item, selection in rows
            ],
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def files(self, project_id: uuid.UUID) -> list[BidProjectFileResponse]:
        await self._project_or_404(project_id)
        return [self._file_response(item) for item in await self.repository.files(project_id)]

    async def download(
        self, project_id: uuid.UUID, file_id: uuid.UUID
    ) -> tuple[BidProjectFile, bytes]:
        file = await self.repository.file_by_id(project_id, file_id)
        if file is None:
            raise AppError("BID_PROJECT_FILE_NOT_FOUND", "投标文件不存在", 404)
        return file, await self.storage.read(file.storage_key)

    async def export(self, project_id: uuid.UUID, actor_id: uuid.UUID) -> BidProjectFileResponse:
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id, lock=True)
            if project.status not in {
                BidProjectStatus.READY.value,
                BidProjectStatus.EXPORTED.value,
            }:
                raise AppError("BID_PROJECT_NOT_READY", "项目尚未完成选品，不能生成报价文件", 409)
            if project.template_id is None:
                raise AppError("BID_TEMPLATE_REQUIRED", "项目尚未绑定可导出模板", 409)
            template = await self.session.get(BidTemplate, project.template_id)
            if template is None:
                raise AppError("BID_TEMPLATE_NOT_FOUND", "项目模板不存在", 409)
            unresolved_count = await self.session.scalar(
                select(func.count())
                .select_from(BidProjectItem)
                .where(
                    BidProjectItem.project_id == project_id,
                    BidProjectItem.status.not_in(
                        [BidItemStatus.SELECTED.value, BidItemStatus.NO_QUOTE.value]
                    ),
                )
            )
            if unresolved_count:
                raise AppError("BID_PROJECT_ITEMS_UNRESOLVED", "仍有需求行未完成选品", 409)
            original = await self.repository.original_file(project_id)
            if original is None:
                raise AppError("BID_PROJECT_ORIGINAL_NOT_FOUND", "项目原始文件不存在", 409)
            selections = await self.repository.export_rows(project_id)
            content = self._build_export(
                await self.storage.read(original.storage_key), template, selections
            )
            version = await self.repository.next_export_version(project_id)
            filename = f"{project.project_code}-报价文件-V{version}.xlsx"
            storage_key = await self.storage.save(
                f"bid-projects/{project_id}/exports/quote-v{version}.xlsx", content
            )
            file = BidProjectFile(
                project_id=project_id,
                file_type=BidFileType.QUOTED_EXPORT.value,
                version_no=version,
                original_filename=filename,
                storage_key=storage_key,
                file_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                created_by=actor_id,
            )
            self.session.add(file)
            if project.status == BidProjectStatus.READY.value:
                self._transition(
                    project, actor_id, BidProjectStatus.EXPORTED, "QUOTE_EXPORTED", None
                )
            else:
                self._add_event(
                    project_id,
                    actor_id,
                    "QUOTE_EXPORTED",
                    BidProjectStatus.EXPORTED.value,
                    BidProjectStatus.EXPORTED.value,
                    f"生成报价文件第{version}版",
                )
            await self.session.flush()
        return self._file_response(file)

    async def submit(
        self, project_id: uuid.UUID, file_id: uuid.UUID, note: str | None, actor_id: uuid.UUID
    ) -> BidProjectStatusResponse:
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id, lock=True)
            file = await self.repository.file_by_id(project_id, file_id)
            if file is None or file.file_type != BidFileType.QUOTED_EXPORT.value:
                raise AppError(
                    "BID_SUBMITTED_FILE_INVALID", "实际投标文件必须是当前项目的报价导出文件", 409
                )
            self._transition(
                project, actor_id, BidProjectStatus.SUBMITTED, "PROJECT_SUBMITTED", note
            )
            project.submitted_file_id = file.id
            project.updated_by = actor_id
        return BidProjectStatusResponse(
            id=project.id,
            status=BidProjectStatus(project.status),
            submitted_file_id=project.submitted_file_id,
        )

    async def result(
        self,
        project_id: uuid.UUID,
        target: BidProjectStatus,
        note: str | None,
        actor_id: uuid.UUID,
    ) -> BidProjectStatusResponse:
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id, lock=True)
            event_type = "PROJECT_WON" if target == BidProjectStatus.WON else "PROJECT_LOST"
            self._transition(project, actor_id, target, event_type, note)
        return BidProjectStatusResponse(
            id=project.id,
            status=BidProjectStatus(project.status),
            submitted_file_id=project.submitted_file_id,
        )

    async def update(
        self, project_id: uuid.UUID, payload: object, actor_id: uuid.UUID
    ) -> BidProjectDetailResponse:
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id, lock=True)
            if project.status in {
                BidProjectStatus.SUBMITTED.value,
                BidProjectStatus.WON.value,
                BidProjectStatus.LOST.value,
                BidProjectStatus.VOIDED.value,
            }:
                raise AppError(
                    "BID_PROJECT_UPDATE_FORBIDDEN", "当前项目状态不允许修改基本信息", 409
                )
            start_at = getattr(payload, "start_at")
            deadline_at = getattr(payload, "deadline_at")
            if start_at is not None and deadline_at is not None and start_at > deadline_at:
                raise AppError(
                    "BID_PROJECT_INVALID_TIME_RANGE", "项目开始时间不能晚于投标截止时间", 422
                )
            project.project_name = getattr(payload, "project_name").strip()
            project.buyer_name = getattr(payload, "buyer_name").strip()
            project.start_at, project.deadline_at = start_at, deadline_at
            project.remark = (
                getattr(payload, "remark").strip() if getattr(payload, "remark") else None
            )
            project.updated_by = actor_id
            self._add_event(
                project_id,
                actor_id,
                "PROJECT_UPDATED",
                project.status,
                project.status,
                "更新项目基本信息",
            )
        return await self.get(project_id)

    async def void(
        self, project_id: uuid.UUID, reason: str, actor_id: uuid.UUID
    ) -> BidProjectStatusResponse:
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id, lock=True)
            self._transition(project, actor_id, BidProjectStatus.VOIDED, "PROJECT_VOIDED", reason)
        return BidProjectStatusResponse(
            id=project.id,
            status=BidProjectStatus(project.status),
            submitted_file_id=project.submitted_file_id,
        )

    async def advance_lifecycle(
        self,
        project_id: uuid.UUID,
        target: BidProjectStatus,
        actor_id: uuid.UUID,
        event_type: str,
        note: str | None = None,
    ) -> BidProjectStatusResponse:
        """供匹配服务调用的受控项目状态推进入口。"""
        async with transaction_scope(self.session):
            project = await self._project_or_404(project_id, lock=True)
            if target == BidProjectStatus.READY:
                unfinished_count = await self.session.scalar(
                    select(func.count())
                    .select_from(BidProjectItem)
                    .where(
                        BidProjectItem.project_id == project_id,
                        BidProjectItem.status.not_in(
                            [BidItemStatus.SELECTED.value, BidItemStatus.NO_QUOTE.value]
                        ),
                    )
                )
                if unfinished_count:
                    raise AppError("BID_PROJECT_ITEMS_UNRESOLVED", "仍有需求行未完成选品", 409)
            self._transition(project, actor_id, target, event_type, note)
        return BidProjectStatusResponse(
            id=project.id,
            status=BidProjectStatus(project.status),
            submitted_file_id=project.submitted_file_id,
        )

    async def _recognize_template(self, file_bytes: bytes) -> BidTemplate | None:
        try:
            workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=False)
        except Exception as exc:
            raise AppError("BID_EXCEL_PARSE_FAILED", "Excel 文件无法读取", 422) from exc
        try:
            templates = list(
                (
                    await self.session.scalars(
                        select(BidTemplate).where(BidTemplate.is_active.is_(True))
                    )
                ).all()
            )
            for template in templates:
                if template.sheet_name not in workbook.sheetnames:
                    continue
                sheet = workbook[template.sheet_name]
                headers = [self._text(cell.value) for cell in sheet[template.header_row]]
                if (
                    self._fingerprint(template.sheet_name, template.header_row, headers)
                    == template.fingerprint
                ):
                    return template
        finally:
            workbook.close()
        return None

    def _parse_rows(self, file_bytes: bytes, template: BidTemplate) -> list[dict[str, Any]]:
        try:
            workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=False)
        except Exception as exc:
            raise AppError("BID_EXCEL_PARSE_FAILED", "Excel 文件无法读取", 422) from exc
        try:
            if template.sheet_name not in workbook.sheetnames:
                raise AppError("BID_TEMPLATE_SHEET_MISSING", "模板工作表不存在", 422)
            sheet = workbook[template.sheet_name]
            headers = [self._text(cell.value) for cell in sheet[template.header_row]]
            header_columns = {header: index for index, header in enumerate(headers) if header}
            missing = [
                header
                for header in template.import_mapping.values()
                if header not in header_columns
            ]
            if missing:
                raise AppError("BID_TEMPLATE_HEADER_MISSING", "模板表头不完整", 422)
            rows: list[dict[str, Any]] = []
            for row_number, cells in enumerate(
                sheet.iter_rows(min_row=template.data_start_row), template.data_start_row
            ):
                values = [cell.value for cell in cells]
                if not any(value is not None and str(value).strip() for value in values):
                    continue
                source_data = {
                    header: self._json_value(values[index])
                    for header, index in header_columns.items()
                    if index < len(values)
                }
                parsed = {
                    key: self._text(source_data.get(header))
                    for key, header in template.import_mapping.items()
                }
                rows.append(
                    {
                        "sheet_name": template.sheet_name,
                        "source_row_number": row_number,
                        "source_data": source_data,
                        "product_name": parsed.get("product_name"),
                        "brand": parsed.get("brand"),
                        "model": parsed.get("model"),
                        "specification": parsed.get("specification"),
                        "category_text": parsed.get("category_text"),
                        "quantity": self._decimal(parsed.get("quantity")),
                        "unit": parsed.get("unit"),
                        "max_price": self._decimal(parsed.get("max_price")),
                        "buyer_item_code": parsed.get("buyer_item_code"),
                        "status": BidItemStatus.PENDING.value,
                    }
                )
                if len(rows) > MAX_PROJECT_ITEMS:
                    raise AppError("BID_EXCEL_ROWS_TOO_MANY", "Excel 需求行超过允许上限", 422)
            return rows
        finally:
            workbook.close()

    def _build_export(
        self,
        original_bytes: bytes,
        template: BidTemplate,
        selections: list[tuple[BidProjectItem, Any]],
    ) -> bytes:
        price_header = template.export_mapping.get("selected_unit_price")
        if not price_header:
            raise AppError("BID_EXPORT_PRICE_COLUMN_MISSING", "模板未配置报价写入列", 409)
        workbook = load_workbook(BytesIO(original_bytes), data_only=False)
        try:
            sheet = workbook[template.sheet_name]
            header_columns = {
                self._text(cell.value): cell.column
                for cell in sheet[template.header_row]
                if self._text(cell.value)
            }
            price_column = header_columns.get(price_header)
            if price_column is None:
                raise AppError("BID_EXPORT_PRICE_COLUMN_MISSING", "原始文件缺少报价写入列", 409)
            for item, selection in selections:
                sheet.cell(item.source_row_number, price_column).value = str(
                    selection.selected_unit_price
                )
            output = BytesIO()
            workbook.save(output)
            return output.getvalue()
        finally:
            workbook.close()

    async def _project_or_404(self, project_id: uuid.UUID, *, lock: bool = False) -> BidProject:
        project = await self.repository.project_by_id(project_id, lock=lock)
        if project is None:
            raise AppError("BID_PROJECT_NOT_FOUND", "投标项目不存在", 404)
        return project

    @staticmethod
    def _ensure_free_project(project: BidProject) -> None:
        if project.project_type != BidProjectType.FREE_RECOMMENDATION.value:
            raise AppError("PROJECT_TYPE_NOT_SUPPORTED", "该项目类型不支持推荐模板", 409)

    async def _next_template_version(self, project_id: uuid.UUID) -> int:
        latest = await self.session.scalar(
            select(func.max(BidProjectFile.version_no)).where(
                BidProjectFile.project_id == project_id,
                BidProjectFile.file_type == BidFileType.RECOMMENDATION_TEMPLATE.value,
            )
        )
        return (latest or 0) + 1

    async def _recommendation_mapping_or_error(
        self, project_id: uuid.UUID, file_id: uuid.UUID, *, lock: bool = False
    ) -> tuple[BidProjectFile, RecommendationTemplateMapping]:
        project = await self._project_or_404(project_id, lock=lock)
        self._ensure_free_project(project)
        statement = (
            select(BidProjectFile, RecommendationTemplateMapping)
            .join(
                RecommendationTemplateMapping,
                RecommendationTemplateMapping.template_file_id == BidProjectFile.id,
            )
            .where(BidProjectFile.id == file_id, BidProjectFile.project_id == project_id)
        )
        if lock:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).first()
        if row is None:
            raise AppError("RECOMMENDATION_TEMPLATE_NOT_FOUND", "推荐模板或映射不存在", 404)
        file, mapping = row
        if file.file_type != BidFileType.RECOMMENDATION_TEMPLATE.value:
            raise AppError(
                "RECOMMENDATION_TEMPLATE_PROJECT_MISMATCH", "文件不是该项目的推荐模板", 409
            )
        return file, mapping

    def _mapping_response(
        self, file: BidProjectFile, mapping: RecommendationTemplateMapping
    ) -> RecommendationTemplateMappingResponse:
        return RecommendationTemplateMappingResponse(
            template_file=self._file_response(file),
            sheet_name=mapping.sheet_name,
            header_row=mapping.header_row,
            data_start_row=mapping.data_start_row,
            mapping_json=mapping.mapping_json,
            confirmed_by=mapping.confirmed_by,
            confirmed_at=mapping.confirmed_at,
        )

    def _transition(
        self,
        project: BidProject,
        actor_id: uuid.UUID,
        target: BidProjectStatus,
        event_type: str,
        note: str | None,
    ) -> None:
        ensure_transition(project.status, target)
        before = project.status
        project.status = target.value
        project.updated_by = actor_id
        self._add_event(project.id, actor_id, event_type, before, target.value, note)

    def _add_event(
        self,
        project_id: uuid.UUID,
        actor_id: uuid.UUID,
        event_type: str,
        from_status: str | None,
        to_status: str | None,
        note: str | None,
    ) -> None:
        self.session.add(
            BidProjectEvent(
                project_id=project_id,
                actor_id=actor_id,
                event_type=event_type,
                from_status=from_status,
                to_status=to_status,
                note=note,
            )
        )

    @staticmethod
    def _validate_upload(filename: str, file_bytes: bytes) -> None:
        if Path(filename).suffix.lower() != ".xlsx":
            raise AppError("BID_EXCEL_EXTENSION_UNSUPPORTED", "仅支持 .xlsx 文件", 422)
        if not file_bytes:
            raise AppError("BID_EXCEL_EMPTY", "上传文件不能为空", 422)
        if len(file_bytes) > MAX_FILE_BYTES:
            raise AppError("BID_EXCEL_TOO_LARGE", "上传文件超过大小限制", 422)

    @staticmethod
    def _validate_recommendation_template(filename: str, file_bytes: bytes) -> None:
        if Path(filename).suffix.lower() != ".xlsx" or not file_bytes:
            raise AppError("RECOMMENDATION_TEMPLATE_INVALID", "推荐模板必须是非空 .xlsx 文件", 422)
        if len(file_bytes) > MAX_FILE_BYTES:
            raise AppError("RECOMMENDATION_TEMPLATE_INVALID", "推荐模板超过大小限制", 422)

    @staticmethod
    def _fingerprint(sheet_name: str, header_row: int, headers: list[str | None]) -> str:
        value = json.dumps(
            {"sheet_name": sheet_name, "header_row": header_row, "headers": headers},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _text(value: object) -> str | None:
        if value is None:
            return None
        result = str(value).strip()
        return result or None

    @staticmethod
    def _json_value(value: object) -> str | int | float | None:
        if value is None:
            return None
        if isinstance(value, (str, int, float)):
            return value
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _decimal(value: str | None) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(value.replace(",", ""))
        except InvalidOperation as exc:
            raise AppError("BID_EXCEL_NUMBER_INVALID", "Excel 数量或限价格式不正确", 422) from exc

    @staticmethod
    def _list_item(project: BidProject) -> BidProjectListItem:
        return BidProjectListItem.model_validate(project, from_attributes=True)

    @staticmethod
    def _file_response(file: BidProjectFile) -> BidProjectFileResponse:
        return BidProjectFileResponse.model_validate(file, from_attributes=True)
