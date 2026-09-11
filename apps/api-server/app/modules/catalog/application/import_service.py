"""Fixed-template Product Master import workflow."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.transaction import transaction_scope
from app.infrastructure.adapters import ObjectStorage, get_object_storage
from app.modules.catalog.application.excel_images import (
    ExcelImage,
    dispimg_image_id,
    extract_dispimg_images,
)
from app.modules.catalog.infrastructure.models import (
    Product,
    ProductImportRow,
    ProductImportSupplierMatch,
    ProductImportTask,
)
from app.modules.catalog.infrastructure.repository import ProductRepository
from app.modules.catalog.schemas import (
    ProductImportConfirmResponse,
    ProductImportPreviewResponse,
    ProductImportResolveSupplierRequest,
    ProductImportRowResponse,
    ProductImportSupplierCandidateResponse,
    ProductImportSupplierMatchResponse,
)
from app.modules.supplier.domain.matching import (
    SupplierMatchCandidate,
    SupplierMatchStatus,
    classify_supplier_name_match,
    is_eligible_source_supplier,
    normalize_supplier_name,
)
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.supplier.infrastructure.repository import SupplierRepository

PRODUCT_IMPORT_HEADERS = (
    "上架日期",
    "品牌",
    "图片",
    "型号",
    "sku",
    "商品名称",
    "一级类目",
    "二级类目",
    "三级类目",
    "货号",
    "链接",
    "*成本价",
    "市场价",
    "京东价",
    "协议价",
    "协议价采购价",
    "利润",
    "京东价毛利（30-50）",
    "毛利复核",
    "众诚毛利",
    "采销员",
    "供应商",
    "69码",
    "产品规格",
    "卖点",
    "限售区域",
    "京东自营前台价",
    "参考链接",
    "自营旗舰店/官方旗舰店",
    "折扣率",
    "价格虚高比例（30%)",
    "备注",
)
MAX_IMPORT_FILE_BYTES = 25 * 1024 * 1024
MAX_IMPORT_ROWS = 20_000

_DIRECT_DECIMAL_HEADERS = (
    "*成本价",
    "市场价",
    "京东价",
    "协议价",
    "协议价采购价",
    "利润",
    "京东价毛利（30-50）",
    "毛利复核",
    "众诚毛利",
    "京东自营前台价",
    "折扣率",
    "价格虚高比例（30%)",
)


class ProductImportService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self.session = session
        self.storage = storage or get_object_storage()
        self.repository = ProductRepository(session)
        self.supplier_repository = SupplierRepository(session)

    async def preview(
        self, filename: str, file_bytes: bytes, actor_id: uuid.UUID
    ) -> ProductImportPreviewResponse:
        self._validate_upload(filename, file_bytes)
        rows = self._parse_rows(file_bytes)
        embedded_images = extract_dispimg_images(file_bytes)
        candidates = await self.supplier_repository.eligible_source_suppliers()
        task = ProductImportTask(
            original_filename=filename[:255],
            status="VALIDATED",
            total_rows=len(rows),
            valid_rows=0,
            invalid_rows=0,
            created_by=actor_id,
            rows=rows,
        )
        self._create_supplier_matches(task, candidates)
        self._assign_row_matches(task)
        async with transaction_scope(self.session):
            self.session.add(task)
            await self.session.flush()
            await self._stage_images(task, embedded_images)
            await self._refresh_validation(task)
            response = await self._preview_response(task)
        return response

    async def get_preview(self, task_id: uuid.UUID) -> ProductImportPreviewResponse:
        task = await self.repository.import_task_by_id(task_id)
        if task is None:
            raise AppError("PRODUCT_IMPORT_TASK_NOT_FOUND", "Import task not found", 404)
        return await self._preview_response(task)

    async def supplier_candidates(self) -> list[ProductImportSupplierCandidateResponse]:
        suppliers = await self.supplier_repository.eligible_source_suppliers()
        return [
            ProductImportSupplierCandidateResponse(
                id=supplier.id,
                supplier_code=supplier.supplier_code,
                supplier_name=supplier.supplier_name,
                main_brands=supplier.main_brands,
            )
            for supplier in suppliers
        ]

    async def resolve_supplier(
        self,
        task_id: uuid.UUID,
        match_id: uuid.UUID,
        payload: ProductImportResolveSupplierRequest,
        actor_id: uuid.UUID,
    ) -> ProductImportPreviewResponse:
        async with transaction_scope(self.session):
            task = await self.repository.import_task_by_id_for_update(task_id)
            self._assert_editable_task(task, actor_id)
            assert task is not None
            match = next((item for item in task.supplier_matches if item.id == match_id), None)
            if match is None:
                raise AppError("PRODUCT_IMPORT_MATCH_NOT_FOUND", "Supplier match not found", 404)
            supplier = await self.supplier_repository.active_by_id(payload.supplier_id)
            if supplier is None or not self._supplier_is_eligible(supplier):
                raise AppError(
                    "PRODUCT_IMPORT_SUPPLIER_INELIGIBLE",
                    "Only archived, normal and non-deleted suppliers may be selected",
                    409,
                )
            match.match_status = SupplierMatchStatus.MATCHED
            match.match_method = "MANUAL"
            match.matched_supplier_id = supplier.id
            match.resolved_by = actor_id
            match.resolved_at = datetime.now()
            await self._refresh_validation(task)
            response = await self._preview_response(task)
        return response

    async def confirm(
        self, task_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ProductImportConfirmResponse:
        async with transaction_scope(self.session):
            task = await self.repository.import_task_by_id_for_update(task_id)
            self._assert_editable_task(task, actor_id)
            assert task is not None
            await self._refresh_validation(task)
            if task.status != "READY_TO_CONFIRM":
                raise AppError(
                    "PRODUCT_IMPORT_NOT_READY_TO_CONFIRM",
                    "Resolve all row, category, price and supplier errors before confirmation",
                    409,
                )
            matches = {match.id: match for match in task.supplier_matches}
            try:
                async with self.session.begin_nested():
                    for row in task.rows:
                        match = (
                            matches.get(row.supplier_match_id) if row.supplier_match_id else None
                        )
                        if match is None or match.matched_supplier_id is None:
                            raise RuntimeError(
                                "A ready Product Import row is missing a resolved relation"
                            )
                        supplier = await self.supplier_repository.active_by_id(
                            match.matched_supplier_id
                        )
                        if supplier is None or not self._supplier_is_eligible(supplier):
                            raise AppError(
                                "PRODUCT_IMPORT_REFERENCE_CHANGED",
                                "A source supplier changed after preview; preview the batch again",
                                409,
                            )
                        self.session.add(
                            self._product_from_row(row, match.matched_supplier_id, actor_id)
                        )
                    await self.session.flush()
            except IntegrityError as exc:
                if "uq_scm_product_source_supplier_sku" in str(exc.orig).lower():
                    raise AppError(
                        "PRODUCT_IMPORT_DUPLICATE_PRODUCT",
                        "A product with the same source supplier and SKU already exists",
                        409,
                    ) from exc
                raise
            task.status = "CONFIRMED"
            task.confirmed_by = actor_id
            task.confirmed_at = datetime.now()
            response = ProductImportConfirmResponse(
                id=task.id, status=task.status, imported_count=task.total_rows
            )
        return response

    def _validate_upload(self, filename: str, file_bytes: bytes) -> None:
        if not filename.lower().endswith(".xlsx"):
            raise AppError(
                "PRODUCT_IMPORT_FILE_TYPE_INVALID", "Only .xlsx files are supported", 422
            )
        if not file_bytes:
            raise AppError("PRODUCT_IMPORT_FILE_EMPTY", "The import file is empty", 422)
        if len(file_bytes) > MAX_IMPORT_FILE_BYTES:
            raise AppError("PRODUCT_IMPORT_FILE_TOO_LARGE", "The import file exceeds 25 MB", 422)

    def _parse_rows(self, file_bytes: bytes) -> list[ProductImportRow]:
        try:
            formula_workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=False)
            cached_workbook = load_workbook(BytesIO(file_bytes), read_only=True, data_only=True)
        except Exception as exc:
            raise AppError(
                "PRODUCT_IMPORT_FILE_INVALID", "The file is not a valid .xlsx workbook", 422
            ) from exc
        formula_sheet = formula_workbook.active
        cached_sheet = cached_workbook.active
        assert formula_sheet is not None and cached_sheet is not None
        headers = tuple(
            self._normalized(cell.value) for cell in next(formula_sheet.iter_rows(max_row=1))
        )
        if headers != PRODUCT_IMPORT_HEADERS:
            raise AppError(
                "PRODUCT_IMPORT_TEMPLATE_INVALID",
                "Template headers must exactly match the approved "
                "32-column Product Master template",
                422,
            )
        rows: list[ProductImportRow] = []
        for source_row_number, (formula_cells, cached_cells) in enumerate(
            zip(
                formula_sheet.iter_rows(min_row=2, max_col=len(PRODUCT_IMPORT_HEADERS)),
                cached_sheet.iter_rows(min_row=2, max_col=len(PRODUCT_IMPORT_HEADERS)),
                strict=True,
            ),
            start=2,
        ):
            if not any(cell.value is not None for cell in formula_cells):
                continue
            if len(rows) >= MAX_IMPORT_ROWS:
                raise AppError(
                    "PRODUCT_IMPORT_TOO_MANY_ROWS",
                    f"An import may contain at most {MAX_IMPORT_ROWS} data rows",
                    422,
                )
            source_data = {
                header: self._cell_text(cell.value)
                for header, cell in zip(PRODUCT_IMPORT_HEADERS, formula_cells)
            }
            calculated_data = {
                header: self._cell_text(cell.value)
                for header, cell in zip(PRODUCT_IMPORT_HEADERS, cached_cells)
            }
            rows.append(
                ProductImportRow(
                    source_row_number=source_row_number,
                    source_data=source_data,
                    calculated_data=calculated_data,
                    supplier_name_raw=self._optional(source_data["供应商"]),
                    is_valid=False,
                )
            )
        if not rows:
            raise AppError("PRODUCT_IMPORT_NO_DATA_ROWS", "The workbook has no data rows", 422)
        return rows

    def _create_supplier_matches(self, task: ProductImportTask, candidates: list[Supplier]) -> None:
        candidate_models = [
            SupplierMatchCandidate(
                id=supplier.id,
                supplier_name=supplier.supplier_name,
                archive_status=supplier.archive_status,
                cooperation_status=supplier.cooperation_status,
                is_deleted=supplier.is_deleted,
            )
            for supplier in candidates
        ]
        names = sorted(
            {
                normalize_supplier_name(row.supplier_name_raw)
                for row in task.rows
                if row.supplier_name_raw and normalize_supplier_name(row.supplier_name_raw)
            }
        )
        for normalized_name in names:
            result = classify_supplier_name_match(normalized_name, candidate_models)
            task.supplier_matches.append(
                ProductImportSupplierMatch(
                    supplier_name_normalized=normalized_name,
                    match_status=result.status,
                    match_method=result.match_method,
                    matched_supplier_id=result.matched_supplier_id,
                )
            )

    @staticmethod
    def _assign_row_matches(task: ProductImportTask) -> None:
        matches = {item.supplier_name_normalized: item for item in task.supplier_matches}
        for row in task.rows:
            if row.supplier_name_raw:
                row.supplier_match = matches.get(normalize_supplier_name(row.supplier_name_raw))

    async def _refresh_validation(self, task: ProductImportTask) -> None:
        matches = {match.id: match for match in task.supplier_matches}
        row_supplier_sku_keys: dict[int, tuple[uuid.UUID, str]] = {}
        for row in task.rows:
            match = (
                matches.get(row.supplier_match_id)
                if row.supplier_match_id is not None
                else None
            )
            sku = self._optional(row.source_data["sku"])
            if match is not None and match.matched_supplier_id is not None and sku is not None:
                row_supplier_sku_keys[row.source_row_number] = (match.matched_supplier_id, sku)
        existing_supplier_sku_keys = await self.repository.existing_supplier_sku_keys(
            set(row_supplier_sku_keys.values())
        )
        valid_rows = 0
        unresolved_match = False
        first_excel_row_for_key: dict[tuple[uuid.UUID, str], int] = {}
        for row in task.rows:
            supplier_sku_key = row_supplier_sku_keys.get(row.source_row_number)
            first_excel_row = (
                first_excel_row_for_key.get(supplier_sku_key)
                if supplier_sku_key is not None
                else None
            )
            errors, warnings = await self._row_messages(
                row,
                matches,
                existing_supplier_sku_keys=existing_supplier_sku_keys,
                first_excel_row=first_excel_row,
            )
            row.error_message = "；".join(errors) or None
            row.warning_message = "；".join(warnings) or None
            row.is_valid = not errors
            valid_rows += int(row.is_valid)
            match = (
                matches.get(row.supplier_match_id) if row.supplier_match_id is not None else None
            )
            if match is not None and match.match_status != SupplierMatchStatus.MATCHED:
                unresolved_match = True
            if supplier_sku_key is not None and first_excel_row is None:
                first_excel_row_for_key[supplier_sku_key] = row.source_row_number
        task.valid_rows = valid_rows
        task.invalid_rows = task.total_rows - valid_rows
        task.status = (
            "READY_TO_CONFIRM"
            if valid_rows == task.total_rows
            else "NEEDS_RESOLUTION"
            if unresolved_match
            else "VALIDATED"
        )

    async def _row_messages(
        self,
        row: ProductImportRow,
        matches: dict[uuid.UUID, ProductImportSupplierMatch],
        *,
        existing_supplier_sku_keys: set[tuple[uuid.UUID, str]],
        first_excel_row: int | None,
    ) -> tuple[list[str], list[str]]:
        values = row.source_data
        errors: list[str] = []
        warnings: list[str] = []
        self._required_decimal(row, "*成本价", errors)
        sku = self._optional(values["sku"])
        if sku is None:
            errors.append("SKU不能为空")
        for header in _DIRECT_DECIMAL_HEADERS:
            if header == "*成本价":
                continue
            value = self._import_value(row, header)
            if value and self._decimal_or_none(value) is None:
                warnings.append(f"{header}无可用数值，正式字段暂不写入")
        match = matches.get(row.supplier_match_id) if row.supplier_match_id is not None else None
        if not row.supplier_name_raw:
            errors.append("供应商不能为空")
        elif match is None or match.match_status != SupplierMatchStatus.MATCHED:
            errors.append("来源供应商尚未解析")
        elif sku is not None and match.matched_supplier_id is not None:
            supplier_sku_key = (match.matched_supplier_id, sku)
            if supplier_sku_key in existing_supplier_sku_keys:
                errors.append("该来源供应商与SKU组合已存在")
            elif first_excel_row is not None:
                errors.append(f"与Excel第{first_excel_row}行的来源供应商与SKU重复")
        image_value = values["图片"] or ""
        if image_value.startswith("=") and row.image_storage_key is None:
            warnings.append("图片公式未找到可保存的内嵌图片，正式图片引用暂不写入")
        if values["上架日期"] and self._optional_date(values["上架日期"]) is None:
            warnings.append("上架日期无法确定年份，正式商品将暂不写入上架日期")
        return errors, warnings

    def _product_from_row(
        self,
        row: ProductImportRow,
        source_supplier_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> Product:
        values = row.source_data
        cost_price = self._decimal_or_none(self._import_value(row, "*成本价"))
        if cost_price is None:
            raise RuntimeError("A ready Product Import row is missing a cost price")
        sku = self._optional(values["sku"])
        if sku is None:
            raise RuntimeError("A ready Product Import row is missing an SKU")
        image_reference = self._image_reference(row)
        return Product(
            listed_at=self._optional_date(values["上架日期"]),
            brand=self._optional(values["品牌"]),
            image_reference=self._optional(image_reference),
            model=self._optional(values["型号"]),
            sku=sku,
            product_name=self._optional(values["商品名称"]),
            category_id=None,
            category_level1_name=self._optional(values["一级类目"]),
            category_level2_name=self._optional(values["二级类目"]),
            category_level3_name=self._optional(values["三级类目"]),
            item_number=self._optional(values["货号"]),
            jd_same_product_url=self._optional(values["链接"]),
            cost_price=cost_price,
            market_price=self._decimal_or_none(self._import_value(row, "市场价")),
            jd_price=self._decimal_or_none(self._import_value(row, "京东价")),
            agreement_price=self._decimal_or_none(self._import_value(row, "协议价")),
            agreement_purchase_price=self._decimal_or_none(
                self._import_value(row, "协议价采购价")
            ),
            profit=self._decimal_or_none(self._import_value(row, "利润")),
            jd_margin=self._decimal_or_none(self._import_value(row, "京东价毛利（30-50）")),
            purchasing_agent=self._optional(values["采销员"]),
            source_supplier_id=source_supplier_id,
            barcode_text=self._optional(values["69码"]),
            deduction_review=self._decimal_or_none(self._import_value(row, "毛利复核")),
            product_specification=self._optional(values["产品规格"]),
            selling_points=self._optional(values["卖点"]),
            gross_margin=self._decimal_or_none(self._import_value(row, "众诚毛利")),
            remark=self._optional(values["备注"]),
            discount_rate=self._decimal_or_none(self._import_value(row, "折扣率")),
            restricted_regions=self._optional(values["限售区域"]),
            jd_self_operated_price=self._decimal_or_none(
                self._import_value(row, "京东自营前台价")
            ),
            reference_url=self._optional(values["参考链接"]),
            storefront_type=self._optional(values["自营旗舰店/官方旗舰店"]),
            price_inflation_rate=self._decimal_or_none(
                self._import_value(row, "价格虚高比例（30%)")
            ),
            deduction_rate=None,
            created_by=actor_id,
            updated_by=actor_id,
        )

    async def _stage_images(
        self, task: ProductImportTask, embedded_images: dict[str, ExcelImage]
    ) -> None:
        for row in task.rows:
            image_id = dispimg_image_id(row.source_data.get("图片"))
            image = embedded_images.get(image_id or "")
            if image is None:
                continue
            row.image_storage_key = await self.storage.save(
                f"product-images/{task.id}/{row.id}{image.extension}", image.content
            )

    @staticmethod
    def _image_reference(row: ProductImportRow) -> str | None:
        if row.image_storage_key:
            return f"local-media/{row.image_storage_key}"
        image_value = row.source_data.get("图片") or ""
        return None if image_value.startswith("=") else ProductImportService._optional(image_value)

    @staticmethod
    def _assert_editable_task(task: ProductImportTask | None, actor_id: uuid.UUID) -> None:
        if task is None:
            raise AppError("PRODUCT_IMPORT_TASK_NOT_FOUND", "Import task not found", 404)
        if task.created_by != actor_id:
            raise AppError(
                "PRODUCT_IMPORT_TASK_FORBIDDEN",
                "Only the uploader can resolve or confirm this import batch",
                403,
            )
        if task.status == "CONFIRMED":
            raise AppError(
                "PRODUCT_IMPORT_TASK_ALREADY_CONFIRMED", "Import task is already confirmed", 409
            )

    @staticmethod
    def _supplier_is_eligible(supplier: Supplier) -> bool:
        return is_eligible_source_supplier(
            SupplierMatchCandidate(
                id=supplier.id,
                supplier_name=supplier.supplier_name,
                archive_status=supplier.archive_status,
                cooperation_status=supplier.cooperation_status,
                is_deleted=supplier.is_deleted,
            )
        )

    async def _preview_response(self, task: ProductImportTask) -> ProductImportPreviewResponse:
        supplier_names: dict[uuid.UUID, tuple[str, str]] = {}
        for match in task.supplier_matches:
            if match.matched_supplier_id is None:
                continue
            supplier = await self.supplier_repository.active_by_id(match.matched_supplier_id)
            if supplier is not None:
                supplier_names[match.id] = (supplier.supplier_code, supplier.supplier_name)
        return ProductImportPreviewResponse(
            id=task.id,
            original_filename=task.original_filename,
            status=task.status,
            total_rows=task.total_rows,
            valid_rows=task.valid_rows,
            invalid_rows=task.invalid_rows,
            rows=[
                ProductImportRowResponse(
                    source_row_number=row.source_row_number,
                    product_name=self._optional(row.source_data["商品名称"]),
                    supplier_name_raw=row.supplier_name_raw,
                    image_saved=row.image_storage_key is not None,
                    category_path=" / ".join(
                        self._normalized(row.source_data[name])
                        for name in ("一级类目", "二级类目", "三级类目")
                    ),
                    category_id=row.category_id,
                    supplier_match_id=row.supplier_match_id,
                    is_valid=row.is_valid,
                    error_message=row.error_message,
                    warning_message=row.warning_message,
                )
                for row in task.rows
            ],
            supplier_matches=[
                ProductImportSupplierMatchResponse(
                    id=match.id,
                    supplier_name_normalized=match.supplier_name_normalized,
                    match_status=match.match_status,
                    match_method=match.match_method,
                    matched_supplier_id=match.matched_supplier_id,
                    matched_supplier_code=supplier_names.get(match.id, (None, None))[0],
                    matched_supplier_name=supplier_names.get(match.id, (None, None))[1],
                )
                for match in task.supplier_matches
            ],
        )

    @staticmethod
    def _cell_text(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    @staticmethod
    def _normalized(value: object) -> str:
        return str(value or "").strip()

    @staticmethod
    def _optional(value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return value

    @staticmethod
    def _decimal_or_none(value: str | None) -> Decimal | None:
        if value is None or not value.strip() or value.startswith("="):
            return None
        try:
            return Decimal(value.strip())
        except (InvalidOperation, ValueError):
            return None

    def _required_decimal(
        self, row: ProductImportRow, header: str, errors: list[str]
    ) -> Decimal | None:
        value = self._decimal_or_none(self._import_value(row, header))
        if value is None:
            errors.append(f"{header}必须是数字")
            return None
        return value

    @staticmethod
    def _import_value(row: ProductImportRow, header: str) -> str | None:
        source = row.source_data.get(header)
        if source and source.startswith("="):
            return row.calculated_data.get(header)
        return source

    @staticmethod
    def _optional_date(value: str | None) -> date | None:
        if value is None or not value.strip():
            return None
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
