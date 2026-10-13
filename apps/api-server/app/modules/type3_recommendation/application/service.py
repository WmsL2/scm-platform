# ruff: noqa: E501, E701, E702
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any, cast

from openpyxl import load_workbook
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams
from app.core.transaction import transaction_scope
from app.infrastructure.adapters import ObjectStorage, get_object_storage
from app.modules.bid.domain.lifecycle import (
    BidFileType,
    BidProjectStatus,
    BidRecommendationType,
    ensure_transition,
)
from app.modules.bid.infrastructure.models import BidProject, BidProjectEvent, BidProjectFile
from app.modules.bid.schemas import BidProjectFileResponse
from app.modules.catalog.application.product_export_columns import (
    PRODUCT_EXPORT_COLUMN_KEYS,
    PRODUCT_EXPORT_COLUMNS,
)
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.type3_recommendation.infrastructure.models import (
    Type3Candidate,
    Type3Export,
    Type3Run,
    Type3SheetConfig,
)
from app.modules.type3_recommendation.schemas import (
    Type3CandidateConfirmationRequest,
    Type3CandidatePage,
    Type3CandidateResponse,
    Type3CandidateSheetSummary,
    Type3ExportField,
    Type3Node,
    Type3OutputColumn,
    Type3RemarkAnalysis,
    Type3RunResponse,
    Type3RunSheetSummary,
    Type3SheetOutputStructure,
    Type3SheetPreview,
    Type3SheetSelectionRequest,
    Type3TemplatePreview,
)

_NODE = re.compile(r"^\s*(?P<code>\d+(?:\.\d+){0,2})\s*[、.．\-]?\s*(?P<label>\S.{0,250})$")
_ALIASES = {
    "sku": "sku",
    "一级类目": "category_level1_name",
    "二级类目": "category_level2_name",
    "三级类目": "category_level3_name",
    "商品名称": "product_name",
    "品牌": "brand",
    "规格型号": "model",
    "VIP价格": "agreement_price",
    "京东价": "jd_price",
    "折扣率": "discount_rate",
    "毛利率": "gross_margin",
}
_DECIMALS = frozenset(
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


class Type3RecommendationService:
    """Dedicated Type-3 persistence and deterministic retrieval boundary."""

    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self.session, self.storage = session, storage or get_object_storage()

    async def preview(self, project_id: uuid.UUID) -> Type3TemplatePreview:
        project, file = await self._project_and_template(project_id)
        del project
        workbook_bytes = await self.storage.read(file.storage_key)
        return Type3TemplatePreview(template_file_id=file.id, sheets=self._inspect(workbook_bytes))

    async def sheet_output_structure(
        self, project_id: uuid.UUID, sheet_name: str, header_row: int
    ) -> Type3SheetOutputStructure:
        """Read one Type-3 workbook Sheet's actual output headers for manual mapping."""
        _project, file = await self._project_and_template(project_id)
        try:
            workbook = load_workbook(BytesIO(await self.storage.read(file.storage_key)), read_only=True)
        except Exception as exc:
            raise AppError("TYPE3_WORKBOOK_INVALID", "类型 3 工作簿无法读取", 422) from exc
        try:
            if sheet_name not in workbook.sheetnames:
                raise AppError("TYPE3_SHEET_NOT_FOUND", "所选工作表已不存在", 422)
            sheet = workbook[sheet_name]
            if header_row > sheet.max_row:
                raise AppError("TYPE3_HEADER_ROW_INVALID", "表头行超出工作表范围", 422)
            return Type3SheetOutputStructure(
                sheet_name=sheet.title,
                header_row=header_row,
                max_row=sheet.max_row,
                columns=self._output_columns(sheet, header_row),
            )
        finally:
            workbook.close()

    @staticmethod
    def export_fields() -> list[Type3ExportField]:
        """Type-3's own field catalogue for mapping its independently exported workbook."""
        return [Type3ExportField(key=item.key, label=item.header) for item in PRODUCT_EXPORT_COLUMNS]

    async def available_export_fields(self, project_id: uuid.UUID) -> list[Type3ExportField]:
        await self._project(project_id)
        return self.export_fields()

    async def save_sheet_selection(
        self, project_id: uuid.UUID, payload: Type3SheetSelectionRequest, actor_id: uuid.UUID
    ) -> list[Type3SheetPreview]:
        project, template = await self._project_and_template(project_id, for_update=True)
        preview = {
            item.sheet_name: item
            for item in self._inspect(await self.storage.read(template.storage_key))
        }
        async with transaction_scope(self.session):
            existing = list(
                (
                    await self.session.scalars(
                        select(Type3SheetConfig)
                        .where(Type3SheetConfig.project_id == project.id)
                        .with_for_update()
                    )
                ).all()
            )
            for row in existing:
                await self.session.delete(row)
            # The replacement payload can contain the same (project_id, sheet_name)
            # as a deleted row.  MySQL enforces that unique key immediately, so flush
            # deletes before staging replacement inserts in this transaction.
            await self.session.flush()
            saved: list[Type3SheetPreview] = []
            for sheet in payload.sheets:
                actual = preview.get(sheet.sheet_name)
                if actual is None:
                    raise AppError("TYPE3_SHEET_NOT_FOUND", "所选工作表已不存在", 422)
                nodes_by_id = {item.node_id: item for item in actual.nodes}
                manual_nodes = [
                    item for item in sheet.nodes if item.node_id.startswith("manual:")
                ]
                if any(
                    item.node_id not in nodes_by_id and item not in manual_nodes
                    for item in sheet.nodes
                ):
                    raise AppError(
                        "TYPE3_CATEGORY_NODE_INVALID", "所选类目节点不属于当前工作簿", 422
                    )
                if sheet.data_start_row <= sheet.header_row:
                    raise AppError(
                        "TYPE3_OUTPUT_REGION_INVALID", "数据起始行必须位于表头行之后", 422
                    )
                self._validate_output_mapping(sheet.mapping_json, actual.max_column)
                self.session.add(
                    Type3SheetConfig(
                        project_id=project.id,
                        template_file_id=template.id,
                        sheet_name=sheet.sheet_name,
                        header_row=sheet.header_row,
                        data_start_row=sheet.data_start_row,
                        mapping_json=sheet.mapping_json,
                        # Cell identity comes from the saved workbook preview; manually
                        # added nodes are intentionally preserved as a user-owned input.
                        selected_nodes=[
                            (
                                nodes_by_id[item.node_id].model_dump()
                                if item.node_id in nodes_by_id
                                else item.model_dump()
                            )
                            for item in sheet.nodes
                        ],
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )
                saved.append(sheet)
            project.updated_by = actor_id
        return saved

    async def saved_sheet_selections(self, project_id: uuid.UUID) -> list[Type3SheetPreview]:
        """Return the user-owned selection that belongs to the current workbook version."""
        project, template = await self._project_and_template(project_id)
        del project
        rows = list(
            (
                await self.session.scalars(
                    select(Type3SheetConfig)
                    .where(
                        Type3SheetConfig.project_id == project_id,
                        Type3SheetConfig.template_file_id == template.id,
                    )
                    .order_by(Type3SheetConfig.sheet_name)
                )
            ).all()
        )
        return [
            Type3SheetPreview(
                sheet_name=row.sheet_name,
                header_row=row.header_row,
                data_start_row=row.data_start_row,
                max_row=0,
                max_column=0,
                mapping_json=row.mapping_json,
                nodes=[Type3Node.model_validate(node) for node in row.selected_nodes],
            )
            for row in rows
        ]

    async def start(self, project_id: uuid.UUID, actor_id: uuid.UUID) -> Type3RunResponse:
        async with transaction_scope(self.session):
            project = await self._project(project_id, for_update=True)
            configs = await self._configs(project.id)
            if not configs:
                raise AppError(
                    "TYPE3_SHEET_SELECTION_REQUIRED",
                    "请先选择需要推品的 Sheet 及一级、二级或三级类目",
                    409,
                )
            if project.status in {
                BidProjectStatus.READY.value,
                BidProjectStatus.EXPORTED.value,
                BidProjectStatus.SUBMITTED.value,
                BidProjectStatus.WON.value,
                BidProjectStatus.LOST.value,
            }:
                raise AppError(
                    "TYPE3_SELECTION_COMPLETED", "项目已完成选品，如需调整请先返回待选品状态", 409
                )
            if project.status not in {
                BidProjectStatus.IMPORTED.value,
                BidProjectStatus.MATCHING.value,
                BidProjectStatus.SELECTING.value,
            }:
                raise AppError("TYPE3_RUN_NOT_ALLOWED", "当前项目状态不能生成候选", 409)

            before_status = project.status
            if project.status == BidProjectStatus.IMPORTED.value:
                ensure_transition(project.status, BidProjectStatus.MATCHING)
                project.status = BidProjectStatus.MATCHING.value
            project.updated_by = actor_id
            self.session.add(
                BidProjectEvent(
                    project_id=project.id,
                    actor_id=actor_id,
                    event_type="TYPE3_RECOMMENDATION_STARTED",
                    from_status=before_status,
                    to_status=project.status,
                    note=(
                        "类型 3 独立 Sheet/类目推品重新生成候选，项目保持待选品状态"
                        if before_status == BidProjectStatus.SELECTING.value
                        else "类型 3 独立 Sheet/类目推品开始"
                    ),
                )
            )
            run = Type3Run(
                project_id=project.id,
                raw_remark_snapshot=(project.remark or "").strip(),
                sheet_snapshot=[self._sheet_snapshot(item) for item in configs],
                status="QUEUED",
                created_by=actor_id,
            )
            self.session.add(run)
            await self.session.flush()
            await self.session.refresh(run)
        return self._run_response(run, project_status=project.status)

    async def save_and_start(
        self,
        project_id: uuid.UUID,
        payload: Type3SheetSelectionRequest,
        actor_id: uuid.UUID,
    ) -> Type3RunResponse:
        """Persist exactly the submitted multi-Sheet selection, then freeze that same state."""
        await self.save_sheet_selection(project_id, payload, actor_id)
        return await self.start(project_id, actor_id)

    async def list_runs(self, project_id: uuid.UUID) -> list[Type3RunResponse]:
        project = await self._project(project_id)
        rows = list(
            (
                await self.session.scalars(
                    select(Type3Run)
                    .where(Type3Run.project_id == project_id)
                    .order_by(Type3Run.created_at.desc())
                )
            ).all()
        )
        return [self._run_response(row, project_status=project.status) for row in rows]

    async def get_run(self, run_id: uuid.UUID) -> Type3RunResponse:
        run = await self._run(run_id)
        project = await self._project(run.project_id)
        return self._run_response(run, project_status=project.status)

    async def prepare_for_category_mapping(
        self,
        run_id: uuid.UUID,
        analysis: Type3RemarkAnalysis,
        *,
        provider: str,
        model: str,
        prompt_version: str,
    ) -> dict[str, object]:
        """Persist the parsed remark and server-issued catalogue before AI mapping."""
        async with transaction_scope(self.session):
            run = await self._run(run_id, for_update=True)
            run.status = "ANALYZING"
            run.parsed_remark = analysis.model_dump(mode="json")
            run.provider, run.model, run.prompt_version = provider, model, prompt_version
            catalog = await self._catalog(analysis)
            run.category_catalog_snapshot = {
                "generated_at": datetime.now(UTC).isoformat(),
                "items": catalog,
            }
            return {"catalog": catalog, "sheets": run.sheet_snapshot}

    async def execute(
        self,
        run_id: uuid.UUID,
        analysis: Type3RemarkAnalysis,
        *,
        provider: str,
        model: str,
        prompt_version: str,
        category_matches: dict[str, list[str]],
    ) -> None:
        async with transaction_scope(self.session):
            run = await self._run(run_id, for_update=True)
            run.status = "RETRIEVING"
            run.parsed_remark = analysis.model_dump(mode="json")
            run.provider, run.model, run.prompt_version = provider, model, prompt_version
            catalog_raw = (run.category_catalog_snapshot or {}).get("items")
            if not isinstance(catalog_raw, list):
                catalog_raw = await self._catalog(analysis)
                run.category_catalog_snapshot = {
                    "generated_at": datetime.now(UTC).isoformat(),
                    "items": catalog_raw,
                }
            catalog = cast(list[dict[str, object]], catalog_raw)
            issued = {item["category_key"]: item for item in catalog}
            sheets = run.sheet_snapshot
            requested = {
                str(node["node_id"])
                for sheet in sheets
                for node in cast(list[dict[str, object]], sheet["selected_nodes"])
            }
            if set(category_matches) != requested or any(
                key not in issued for keys in category_matches.values() for key in keys
            ):
                raise AppError(
                    "TYPE3_CATEGORY_CATALOG_KEY_INVALID",
                    "AI 返回了未签发类目或遗漏了用户所选类目",
                    422,
                )
            # Keep the issued-key mapping with this run.  It lets us audit a broad Excel
            # node that intentionally expands to multiple real terminal categories without
            # ever letting AI return an arbitrary database category.
            catalog_snapshot = dict(run.category_catalog_snapshot or {})
            catalog_snapshot["matches"] = [
                {"node_id": node_id, "category_keys": category_matches[node_id]}
                for node_id in sorted(category_matches)
            ]
            run.category_catalog_snapshot = catalog_snapshot
            for sheet in sheets:
                paths = [
                    issued[key]
                    for node in cast(list[dict[str, object]], sheet["selected_nodes"])
                    for key in category_matches[str(node["node_id"])]
                ]
                rows = await self._eligible(analysis, paths)
                for rank, (product, supplier) in enumerate(rows, start=1):
                    self.session.add(
                        self._candidate(run.id, str(sheet["sheet_name"]), rank, product, supplier)
                    )
            await self.session.flush()
            count = int(
                await self.session.scalar(
                    select(func.count(Type3Candidate.id)).where(Type3Candidate.run_id == run.id)
                )
                or 0
            )
            run.status = "WAITING_CONFIRMATION" if count else "NO_CANDIDATES"

    async def fail(self, run_id: uuid.UUID, message: str) -> None:
        async with transaction_scope(self.session):
            run = await self._run(run_id, for_update=True)
            run.status, run.error = "FAILED", message[:4000]

    async def candidates(
        self, run_id: uuid.UUID, sheet_name: str | None, page: PageParams
    ) -> Type3CandidatePage:
        await self._run(run_id)
        condition = [Type3Candidate.run_id == run_id]
        if sheet_name:
            condition.append(Type3Candidate.sheet_name == sheet_name)
        total = int(
            await self.session.scalar(select(func.count(Type3Candidate.id)).where(*condition)) or 0
        )
        confirmed = int(
            await self.session.scalar(
                select(func.count(Type3Candidate.id)).where(
                    *condition, Type3Candidate.confirmed_at.is_not(None)
                )
            )
            or 0
        )
        rows = list(
            (
                await self.session.scalars(
                    select(Type3Candidate)
                    .where(*condition)
                    .order_by(Type3Candidate.sheet_name, Type3Candidate.rank)
                    .offset((page.page - 1) * page.page_size)
                    .limit(page.page_size)
                )
            ).all()
        )
        return Type3CandidatePage(
            items=[self._candidate_response(row) for row in rows],
            total=total,
            page=page.page,
            page_size=page.page_size,
            confirmed_total=confirmed,
        )

    async def candidate_sheets(self, run_id: uuid.UUID) -> list[Type3CandidateSheetSummary]:
        """Return source-Sheet counters without loading all candidates into the browser."""
        await self._run(run_id)
        rows = (
            await self.session.execute(
                select(
                    Type3Candidate.sheet_name,
                    func.count(Type3Candidate.id),
                    func.sum(Type3Candidate.confirmed_at.is_not(None)),
                )
                .where(Type3Candidate.run_id == run_id)
                .group_by(Type3Candidate.sheet_name)
                .order_by(Type3Candidate.sheet_name)
            )
        ).all()
        return [
            Type3CandidateSheetSummary(
                sheet_name=sheet_name,
                total=int(total),
                confirmed_total=int(confirmed_total or 0),
            )
            for sheet_name, total, confirmed_total in rows
        ]

    async def confirm(self, candidate_ids: list[uuid.UUID], actor_id: uuid.UUID) -> None:
        async with transaction_scope(self.session):
            rows = list(
                (
                    await self.session.scalars(
                        select(Type3Candidate)
                        .where(Type3Candidate.id.in_(candidate_ids))
                        .with_for_update()
                    )
                ).all()
            )
            if len(rows) != len(set(candidate_ids)):
                raise AppError("TYPE3_CANDIDATE_NOT_FOUND", "存在不存在的类型 3 候选商品", 404)
            now = datetime.now(UTC).replace(tzinfo=None)
            for row in rows:
                row.confirmed_by, row.confirmed_at = actor_id, now

    async def confirm_candidates(
        self,
        run_id: uuid.UUID,
        payload: Type3CandidateConfirmationRequest,
        actor_id: uuid.UUID,
    ) -> int:
        """Confirm selected candidates, or all pending candidates within the current Sheet."""
        async with transaction_scope(self.session):
            await self._run(run_id, for_update=True)
            condition = [
                Type3Candidate.run_id == run_id,
                Type3Candidate.confirmed_at.is_(None),
            ]
            if payload.select_all_unconfirmed:
                if payload.sheet_name:
                    condition.append(Type3Candidate.sheet_name == payload.sheet_name)
                if payload.excluded_candidate_ids:
                    condition.append(Type3Candidate.id.not_in(payload.excluded_candidate_ids))
            else:
                condition.append(Type3Candidate.id.in_(payload.candidate_ids))
            rows = list(
                (
                    await self.session.scalars(
                        select(Type3Candidate).where(*condition).with_for_update()
                    )
                ).all()
            )
            if not payload.select_all_unconfirmed and len(rows) != len(payload.candidate_ids):
                raise AppError("TYPE3_CANDIDATE_NOT_FOUND", "存在不存在或已确认的类型 3 候选商品", 404)
            now = datetime.now(UTC).replace(tzinfo=None)
            for row in rows:
                row.confirmed_by, row.confirmed_at = actor_id, now
            return len(rows)

    async def complete_selection(
        self, project_id: uuid.UUID, run_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        async with transaction_scope(self.session):
            project = await self._project(project_id, for_update=True)
            run = await self._run(run_id, for_update=True)
            if run.project_id != project.id:
                raise AppError("TYPE3_RUN_NOT_FOUND", "类型 3 推品任务不存在", 404)
            confirmed = int(
                await self.session.scalar(
                    select(func.count(Type3Candidate.id)).where(
                        Type3Candidate.run_id == run.id,
                        Type3Candidate.confirmed_at.is_not(None),
                    )
                )
                or 0
            )
            if not confirmed:
                raise AppError("TYPE3_CONFIRMATION_REQUIRED", "请先确认至少一件商品", 409)
            if project.status == BidProjectStatus.MATCHING.value:
                ensure_transition(project.status, BidProjectStatus.SELECTING)
                project.status = BidProjectStatus.SELECTING.value
            if project.status == BidProjectStatus.SELECTING.value:
                ensure_transition(project.status, BidProjectStatus.READY)
                project.status = BidProjectStatus.READY.value
            if project.status not in {BidProjectStatus.READY.value, BidProjectStatus.EXPORTED.value}:
                raise AppError("TYPE3_SELECTION_NOT_ALLOWED", "当前项目状态不能完成选品", 409)
            project.updated_by = actor_id
            run.status = "CONFIRMED"

    async def reopen_selection(
        self, project_id: uuid.UUID, run_id: uuid.UUID, actor_id: uuid.UUID
    ) -> None:
        """Return a completed Type-3 project to manual selection without losing history."""
        async with transaction_scope(self.session):
            project = await self._project(project_id, for_update=True)
            run = await self._run(run_id, for_update=True)
            if run.project_id != project.id:
                raise AppError("TYPE3_RUN_NOT_FOUND", "类型 3 推品任务不存在", 404)
            if project.status not in {
                BidProjectStatus.READY.value,
                BidProjectStatus.EXPORTED.value,
            }:
                raise AppError(
                    "TYPE3_SELECTION_REOPEN_NOT_ALLOWED", "当前项目状态不能返回调整选品", 409
                )
            confirmed = int(
                await self.session.scalar(
                    select(func.count(Type3Candidate.id)).where(
                        Type3Candidate.run_id == run.id,
                        Type3Candidate.confirmed_at.is_not(None),
                    )
                )
                or 0
            )
            if not confirmed:
                raise AppError(
                    "TYPE3_SELECTION_CONFIRMATION_REQUIRED",
                    "当前任务没有已选商品，不能返回调整",
                    409,
                )

            previous_status = project.status
            project.status = BidProjectStatus.SELECTING.value
            project.updated_by = actor_id
            if run.status == "EXPORTED":
                run.status = "CONFIRMED"
            self.session.add(
                BidProjectEvent(
                    project_id=project.id,
                    actor_id=actor_id,
                    event_type="TYPE3_SELECTION_REOPENED",
                    from_status=previous_status,
                    to_status=project.status,
                    note="返回人工选品，后续按 Sheet 导出将生成新版本",
                )
            )

    async def export(
        self, project_id: uuid.UUID, run_id: uuid.UUID, actor_id: uuid.UUID
    ) -> BidProjectFileResponse:
        saved_key: str | None = None
        try:
            async with transaction_scope(self.session):
                project, template = await self._project_and_template(project_id, for_update=True)
                run = await self._run(run_id, for_update=True)
                if run.project_id != project.id:
                    raise AppError("TYPE3_RUN_NOT_FOUND", "类型 3 推品任务不存在", 404)
                groups = list(
                    (
                        await self.session.execute(
                            select(Type3Candidate.sheet_name, Type3Candidate)
                            .where(
                                Type3Candidate.run_id == run.id,
                                Type3Candidate.confirmed_at.is_not(None),
                            )
                            .order_by(Type3Candidate.sheet_name, Type3Candidate.rank)
                        )
                    ).all()
                )
                if not groups:
                    raise AppError(
                        "TYPE3_CONFIRMATION_REQUIRED",
                        "每个导出 Sheet 至少确认一条候选商品后才能导出",
                        409,
                    )
                content = self._build_export(
                    await self.storage.read(template.storage_key),
                    run.sheet_snapshot,
                    [(str(row[0]), row[1]) for row in groups],
                )
                version = (
                    int(
                        await self.session.scalar(
                            select(func.max(Type3Export.version_no)).where(
                                Type3Export.project_id == project.id
                            )
                        )
                        or 0
                    )
                    + 1
                )
                saved_key = await self.storage.save(
                    f"bid-projects/{project.id}/type3-exports/run-{run.id}-v{version}.xlsx", content
                )
                exported = BidProjectFile(
                    project_id=project.id,
                    file_type=BidFileType.RECOMMENDATION_EXPORT.value,
                    version_no=version,
                    original_filename=f"{project.project_code}-类型3按Sheet推品-R{str(run.id)[:8]}-V{version}.xlsx",
                    storage_key=saved_key,
                    file_size=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    created_by=actor_id,
                )
                self.session.add(exported)
                await self.session.flush()
                self.session.add(
                    Type3Export(
                        project_id=project.id,
                        run_id=run.id,
                        export_file_id=exported.id,
                        version_no=version,
                        exported_by=actor_id,
                    )
                )
                if project.status == BidProjectStatus.READY.value:
                    ensure_transition(project.status, BidProjectStatus.EXPORTED)
                project.status, project.updated_by, run.status = (
                    BidProjectStatus.EXPORTED.value,
                    actor_id,
                    "EXPORTED",
                )
                self.session.add(
                    BidProjectEvent(
                        project_id=project.id,
                        actor_id=actor_id,
                        event_type="TYPE3_RECOMMENDATION_EXPORTED",
                        from_status=BidProjectStatus.READY.value,
                        to_status=project.status,
                        note="类型 3 按 Sheet 导出",
                    )
                )
                await self.session.refresh(exported)
        except Exception:
            if saved_key:
                await self.storage.delete(saved_key)
            raise
        return BidProjectFileResponse.model_validate(exported, from_attributes=True)

    async def download(self, run_id: uuid.UUID, file_id: uuid.UUID) -> tuple[BidProjectFile, bytes]:
        row = await self.session.scalar(
            select(BidProjectFile)
            .join(Type3Export, Type3Export.export_file_id == BidProjectFile.id)
            .where(Type3Export.run_id == run_id, BidProjectFile.id == file_id)
        )
        if row is None:
            raise AppError("TYPE3_EXPORT_NOT_FOUND", "类型 3 导出文件不存在", 404)
        return row, await self.storage.read(row.storage_key)

    async def _project(self, project_id: uuid.UUID, *, for_update: bool = False) -> BidProject:
        statement = select(BidProject).where(
            BidProject.id == project_id,
            BidProject.recommendation_type == BidRecommendationType.TYPE_3_CATEGORY.value,
        )
        if for_update:
            statement = statement.with_for_update()
        project = await self.session.scalar(statement)
        if project is None:
            raise AppError("TYPE3_PROJECT_NOT_FOUND", "类型 3 项目不存在", 404)
        return project

    async def _project_and_template(
        self, project_id: uuid.UUID, *, for_update: bool = False
    ) -> tuple[BidProject, BidProjectFile]:
        project = await self._project(project_id, for_update=for_update)
        statement = (
            select(BidProjectFile)
            .where(
                BidProjectFile.project_id == project.id,
                BidProjectFile.file_type == BidFileType.RECOMMENDATION_TEMPLATE.value,
            )
            .order_by(BidProjectFile.version_no.desc())
            .limit(1)
        )
        if for_update:
            statement = statement.with_for_update()
        file = await self.session.scalar(statement)
        if file is None:
            raise AppError("TYPE3_WORKBOOK_NOT_FOUND", "类型 3 客户工作簿不存在", 409)
        return project, file

    async def _configs(self, project_id: uuid.UUID) -> list[Type3SheetConfig]:
        return list(
            (
                await self.session.scalars(
                    select(Type3SheetConfig)
                    .where(Type3SheetConfig.project_id == project_id)
                    .order_by(Type3SheetConfig.sheet_name)
                )
            ).all()
        )

    async def _run(self, run_id: uuid.UUID, *, for_update: bool = False) -> Type3Run:
        statement = select(Type3Run).where(Type3Run.id == run_id)
        if for_update:
            statement = statement.with_for_update()
        run = await self.session.scalar(statement)
        if run is None:
            raise AppError("TYPE3_RUN_NOT_FOUND", "类型 3 推品任务不存在", 404)
        return run

    @staticmethod
    def _inspect(content: bytes) -> list[Type3SheetPreview]:
        try:
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=False)
        except Exception as exc:
            raise AppError("TYPE3_WORKBOOK_INVALID", "类型 3 工作簿无法读取", 422) from exc
        try:
            result = []
            for sheet in workbook.worksheets:
                nodes: list[Type3Node] = []
                for row in sheet.iter_rows(
                    max_row=min(sheet.max_row, 120), max_col=min(sheet.max_column, 40)
                ):
                    for cell in row:
                        text = str(cell.value).strip() if cell.value is not None else ""
                        match = _NODE.match(text)
                        if not match:
                            continue
                        depth = match.group("code").count(".") + 1
                        nodes.append(
                            Type3Node(
                                node_id=f"{sheet.title}!{cell.coordinate}",
                                coordinate=cell.coordinate,
                                level=(
                                    "LEVEL1" if depth == 1 else "LEVEL2" if depth == 2 else "LEVEL3"
                                ),
                                code=match.group("code"),
                                label=match.group("label").strip(),
                            )
                        )
                header_row, mapping = Type3RecommendationService._output_mapping(sheet)
                result.append(
                    Type3SheetPreview(
                        sheet_name=sheet.title,
                        header_row=header_row,
                        data_start_row=header_row + 1,
                        max_row=sheet.max_row,
                        max_column=sheet.max_column,
                        mapping_json=mapping,
                        nodes=nodes,
                    )
                )
            return result
        finally:
            workbook.close()

    @staticmethod
    def _output_mapping(sheet: Any) -> tuple[int, dict[str, object]]:
        for number, row in enumerate(sheet.iter_rows(max_row=min(sheet.max_row, 80)), 1):
            columns = [
                {"column_index": index, "field_key": _ALIASES[str(cell.value).strip()]}
                for index, cell in enumerate(row, 1)
                if cell.value is not None and str(cell.value).strip() in _ALIASES
            ]
            if columns:
                return number, {"version": 2, "columns": columns}
        return 1, {"version": 2, "columns": []}

    @staticmethod
    def _output_columns(sheet: Any, header_row: int) -> list[Type3OutputColumn]:
        cells = next(
            sheet.iter_rows(min_row=header_row, max_row=header_row, max_col=sheet.max_column),
            (),
        )
        headers = [str(cell.value).strip() if cell.value is not None else "" for cell in cells]
        counts = {header: headers.count(header) for header in set(headers) if header}
        return [
            Type3OutputColumn(
                column_index=index,
                header=header,
                duplicate=counts[header] > 1,
            )
            for index, header in enumerate(headers, start=1)
            if header
        ]

    @staticmethod
    def _validate_output_mapping(mapping_json: dict[str, object], max_column: int) -> None:
        columns = mapping_json.get("columns") if isinstance(mapping_json, dict) else None
        if not isinstance(columns, list):
            raise AppError("TYPE3_EXPORT_MAPPING_INVALID", "导出字段映射格式不正确", 422)
        indexes: set[int] = set()
        for mapping in columns:
            if not isinstance(mapping, dict):
                raise AppError("TYPE3_EXPORT_MAPPING_INVALID", "导出字段映射格式不正确", 422)
            column, field = mapping.get("column_index"), mapping.get("field_key")
            if (
                not isinstance(column, int)
                or column < 1
                or column > max_column
                or column in indexes
                or not isinstance(field, str)
                or field not in PRODUCT_EXPORT_COLUMN_KEYS
            ):
                raise AppError("TYPE3_EXPORT_MAPPING_INVALID", "导出字段映射包含无效列或字段", 422)
            indexes.add(column)

    async def _catalog(self, analysis: Type3RemarkAnalysis) -> list[dict[str, object]]:
        rows = await self._eligible(analysis, [])
        nodes: dict[tuple[str | None, str | None, str | None, str], int] = {}
        for product, _supplier in rows:
            for level, path in (
                ("LEVEL1", (product.category_level1_name, None, None)),
                ("LEVEL2", (product.category_level1_name, product.category_level2_name, None)),
                (
                    "LEVEL3",
                    (
                        product.category_level1_name,
                        product.category_level2_name,
                        product.category_level3_name,
                    ),
                ),
            ):
                if any(path):
                    nodes[(*path, level)] = nodes.get((*path, level), 0) + 1
        return [
            {
                "category_key": f"t3c{index}",
                "level1_name": item[0][0],
                "level2_name": item[0][1],
                "level3_name": item[0][2],
                "level": item[0][3],
                "candidate_count": item[1],
            }
            for index, item in enumerate(
                sorted(
                    nodes.items(),
                    key=lambda value: (
                        value[0][3],
                        value[0][0] or "",
                        value[0][1] or "",
                        value[0][2] or "",
                    ),
                ),
                1,
            )
        ]

    async def _eligible(
        self, analysis: Type3RemarkAnalysis, paths: list[dict[str, object]]
    ) -> list[tuple[Product, Supplier]]:
        filters: list[Any] = [
            Product.status == ProductStatus.ACTIVE,
            Supplier.archive_status == ArchiveStatus.ARCHIVED,
            Supplier.cooperation_status == CooperationStatus.NORMAL,
            Supplier.is_deleted.is_(False),
        ]
        for field in ("gross_margin", "agreement_price", "jd_price", "discount_rate"):
            lower, upper = getattr(analysis, f"{field}_min"), getattr(analysis, f"{field}_max")
            if lower is not None:
                filters.append(getattr(Product, field) >= lower)
            if upper is not None:
                filters.append(getattr(Product, field) <= upper)
        if analysis.required_brands:
            filters.append(
                or_(
                    *[
                        func.lower(Product.brand).contains(brand.casefold())
                        for brand in analysis.required_brands
                    ]
                )
            )
        if paths:
            filters.append(
                or_(
                    *[
                        and_(
                            *[
                                getattr(Product, field) == value
                                for field, value in (
                                    ("category_level1_name", path.get("level1_name")),
                                    ("category_level2_name", path.get("level2_name")),
                                    ("category_level3_name", path.get("level3_name")),
                                )
                                if value
                            ]
                        )
                        for path in paths
                    ]
                )
            )
        return list(
            (
                await self.session.execute(
                    select(Product, Supplier)
                    .join(Supplier, Product.source_supplier_id == Supplier.id)
                    .where(*filters)
                    .order_by(Product.id)
                )
            )
            .tuples()
            .all()
        )

    @staticmethod
    def _sheet_snapshot(row: Type3SheetConfig) -> dict[str, object]:
        return {
            "sheet_name": row.sheet_name,
            "header_row": row.header_row,
            "data_start_row": row.data_start_row,
            "mapping_json": row.mapping_json,
            "selected_nodes": row.selected_nodes,
        }

    @staticmethod
    def _candidate(
        run_id: uuid.UUID, sheet_name: str, rank: int, product: Product, supplier: Supplier
    ) -> Type3Candidate:
        product_snapshot: dict[str, object] = {"id": str(product.id)}
        price_snapshot: dict[str, object] = {}
        for field in PRODUCT_EXPORT_COLUMN_KEYS:
            if field == "supplier_name":
                continue
            value = getattr(product, field)
            (price_snapshot if field in _DECIMALS else product_snapshot)[field] = (
                str(value)
                if isinstance(value, Decimal)
                else value.isoformat()
                if isinstance(value, (date, datetime))
                else value
            )
        return Type3Candidate(
            run_id=run_id,
            sheet_name=sheet_name,
            product_id=product.id,
            rank=rank,
            product_snapshot=product_snapshot,
            supplier_snapshot={
                "id": str(supplier.id),
                "supplier_name": supplier.supplier_name,
                "supplier_code": supplier.supplier_code,
            },
            price_snapshot=price_snapshot,
        )

    @staticmethod
    def _candidate_response(row: Type3Candidate) -> Type3CandidateResponse:
        return Type3CandidateResponse(
            id=row.id,
            sheet_name=row.sheet_name,
            product_id=row.product_id,
            rank=row.rank,
            product_snapshot=row.product_snapshot,
            supplier_snapshot=row.supplier_snapshot,
            price_snapshot=row.price_snapshot,
            confirmed_at=row.confirmed_at,
        )

    @staticmethod
    def _run_response(run: Type3Run, *, project_status: str | None = None) -> Type3RunResponse:
        sheet_summaries: list[Type3RunSheetSummary] = []
        for sheet in run.sheet_snapshot:
            if not isinstance(sheet, dict):
                continue
            sheet_name, selected_nodes = sheet.get("sheet_name"), sheet.get("selected_nodes")
            if not isinstance(sheet_name, str) or not isinstance(selected_nodes, list):
                continue
            if selected_nodes:
                sheet_summaries.append(
                    Type3RunSheetSummary(
                        sheet_name=sheet_name, selected_node_count=len(selected_nodes)
                    )
                )
        return Type3RunResponse(
            id=run.id,
            project_id=run.project_id,
            project_status=project_status,
            status=run.status,
            raw_remark_snapshot=run.raw_remark_snapshot,
            parsed_remark=Type3RemarkAnalysis.model_validate(run.parsed_remark)
            if run.parsed_remark
            else None,
            error=run.error,
            provider=run.provider,
            model=run.model,
            prompt_version=run.prompt_version,
            sheet_summaries=sheet_summaries,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    @staticmethod
    def _build_export(
        source: bytes, sheets: list[dict[str, object]], grouped: list[tuple[str, Type3Candidate]]
    ) -> bytes:
        workbook = load_workbook(BytesIO(source), data_only=False)
        try:
            by_sheet: dict[str, list[Type3Candidate]] = {}
            for name, candidate in grouped:
                by_sheet.setdefault(name, []).append(candidate)
            for config in sheets:
                name = str(config["sheet_name"])
                if name not in by_sheet:
                    continue
                if name not in workbook.sheetnames:
                    raise AppError("TYPE3_EXPORT_SHEET_CHANGED", "导出 Sheet 已变更", 409)
                mapping_json = config.get("mapping_json")
                columns = mapping_json.get("columns", []) if isinstance(mapping_json, dict) else []
                if not columns:
                    raise AppError("TYPE3_EXPORT_MAPPING_REQUIRED", f"{name} 未配置导出列", 409)
                sheet, start = workbook[name], int(cast(int, config["data_start_row"]))
                for offset, candidate in enumerate(by_sheet[name]):
                    for mapping in columns:
                        if not isinstance(mapping, dict):
                            continue
                        column, field = mapping.get("column_index"), mapping.get("field_key")
                        if isinstance(column, int) and isinstance(field, str):
                            value = candidate.supplier_snapshot.get(
                                field,
                                candidate.product_snapshot.get(
                                    field, candidate.price_snapshot.get(field)
                                ),
                            )
                            sheet.cell(start + offset, column).value = cast(Any, value)
            output = BytesIO()
            workbook.save(output)
            return output.getvalue()
        finally:
            workbook.close()
