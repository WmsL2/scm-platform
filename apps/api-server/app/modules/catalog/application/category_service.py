# ruff: noqa: E501, E701, E702
from __future__ import annotations

import uuid
from io import BytesIO
from typing import cast

from openpyxl import Workbook, load_workbook
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.transaction import transaction_scope
from app.modules.catalog.infrastructure.models import Category, Product
from app.modules.catalog.schemas import (
    CategoryImportError,
    CategoryImportResponse,
    CategoryWriteRequest,
)

IMPORT_HEADERS = (
    "source_type",
    "level1_external_id",
    "level1_name",
    "level2_external_id",
    "level2_name",
    "level3_external_id",
    "level3_name",
    "deduction_rate",
    "is_active",
    "shelf_flag",
    "business_unit",
)


class CategoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, active_only: bool = False) -> list[Category]:
        statement = select(Category).order_by(
            Category.source_type, Category.level1_name, Category.level2_name, Category.level3_name
        )
        if active_only:
            statement = statement.where(Category.is_active.is_(True))
        return list((await self.session.scalars(statement)).all())

    async def get(self, category_id: uuid.UUID) -> Category:
        category = await self.session.get(Category, category_id)
        if category is None:
            raise AppError("CATEGORY_NOT_FOUND", "Category not found", 404)
        return category

    async def _external_id_conflict(
        self, payload: CategoryWriteRequest, exclude: uuid.UUID | None = None
    ) -> Category | None:
        if payload.level3_external_id is None:
            return None
        statement = select(Category).where(
            Category.source_type == payload.source_type,
            Category.level3_external_id == payload.level3_external_id,
        )
        if exclude:
            statement = statement.where(Category.id != exclude)
        return cast(Category | None, await self.session.scalar(statement))

    async def create(self, payload: CategoryWriteRequest, actor_id: uuid.UUID) -> Category:
        if await self._external_id_conflict(payload):
            raise AppError(
                "CATEGORY_EXTERNAL_ID_EXISTS",
                "This source type and level-3 external ID are already bound to a category",
                409,
            )
        category = Category(**payload.model_dump(), created_by=actor_id, updated_by=actor_id)
        async with transaction_scope(self.session):
            self.session.add(category)
            await self.session.flush()
        return category

    async def update(
        self, category_id: uuid.UUID, payload: CategoryWriteRequest, actor_id: uuid.UUID
    ) -> Category:
        category = await self.get(category_id)
        if await self._external_id_conflict(payload, category_id):
            raise AppError(
                "CATEGORY_EXTERNAL_ID_EXISTS",
                "This source type and level-3 external ID are already bound to a category",
                409,
            )
        async with transaction_scope(self.session):
            for field, value in payload.model_dump().items():
                setattr(category, field, value)
            category.updated_by = actor_id
            await self.session.flush()
        return category

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self.get(category_id)
        used = await self.session.scalar(
            select(func.count()).select_from(Product).where(Product.category_id == category_id)
        )
        if used:
            raise AppError(
                "CATEGORY_IN_USE", "Category is referenced by products and cannot be deleted", 409
            )
        async with transaction_scope(self.session):
            await self.session.delete(category)

    def template(self) -> bytes:
        book = Workbook()
        sheet = book.active
        assert sheet is not None
        sheet.title = "类目导入"
        sheet.append(IMPORT_HEADERS)
        sheet.freeze_panes = "A2"
        output = BytesIO()
        book.save(output)
        return output.getvalue()

    async def import_xlsx(
        self, filename: str, content: bytes, actor_id: uuid.UUID
    ) -> CategoryImportResponse:
        if not filename.lower().endswith(".xlsx"):
            raise AppError(
                "CATEGORY_IMPORT_FILE_TYPE_INVALID", "Only .xlsx files are supported", 422
            )
        if not content:
            raise AppError("CATEGORY_IMPORT_FILE_EMPTY", "The import file is empty", 422)
        try:
            sheet = load_workbook(BytesIO(content), read_only=True, data_only=True).active
            if sheet is None:
                raise ValueError("no worksheet")
            headers = tuple(
                str(cell.value or "").strip() for cell in next(sheet.iter_rows(max_row=1))
            )
        except Exception as exc:
            raise AppError(
                "CATEGORY_IMPORT_FILE_INVALID", "Unable to parse .xlsx file", 422
            ) from exc
        if headers != IMPORT_HEADERS:
            raise AppError(
                "CATEGORY_IMPORT_HEADER_INVALID",
                f"Required headers: {', '.join(IMPORT_HEADERS)}",
                422,
            )
        errors: list[CategoryImportError] = []
        rows: list[tuple[int, CategoryWriteRequest]] = []
        seen_external_ids: set[tuple[str, str]] = set()
        for number, cells in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not any(value is not None and str(value).strip() for value in cells):
                continue
            data: dict[str, object | None] = {
                header: (None if value is None else str(value).strip())
                for header, value in zip(IMPORT_HEADERS, cells, strict=True)
            }
            if data["is_active"] in ("TRUE", "true", "1", "是"):
                data["is_active"] = True
            elif data["is_active"] in ("FALSE", "false", "0", "否"):
                data["is_active"] = False
            try:
                payload = CategoryWriteRequest.model_validate(data)
            except Exception as exc:
                errors.append(CategoryImportError(row_number=number, reason=str(exc)))
                continue
            external_key = (
                (payload.source_type, payload.level3_external_id)
                if payload.level3_external_id is not None
                else None
            )
            if external_key is not None and external_key in seen_external_ids:
                errors.append(
                    CategoryImportError(
                        row_number=number,
                        field="level3_external_id",
                        value=payload.level3_external_id,
                        reason="Duplicate source type and level-3 external ID in Excel",
                    )
                )
                continue
            if external_key is not None:
                seen_external_ids.add(external_key)
            rows.append((number, payload))
        if errors:
            return CategoryImportResponse(
                total=len(rows) + len(errors),
                success=0,
                skipped=0,
                failed=len(errors),
                errors=errors,
            )
        existing = {
            (item.source_type, item.level3_external_id): item
            async for item in await self.session.stream_scalars(select(Category))
            if item.level3_external_id is not None
        }
        inserts: list[Category] = []
        skipped = 0
        for number, payload in rows:
            external_key = (
                (payload.source_type, payload.level3_external_id)
                if payload.level3_external_id is not None
                else None
            )
            prior = existing.get(external_key) if external_key is not None else None
            if prior:
                comparable = payload.model_dump()
                same = all(getattr(prior, name) == value for name, value in comparable.items())
                if same:
                    skipped += 1
                    continue
                errors.append(
                    CategoryImportError(
                        row_number=number,
                        field="level3_external_id",
                        value=payload.level3_external_id,
                        reason="This source type and level-3 external ID are already bound to different data",
                    )
                )
            else:
                inserts.append(
                    Category(**payload.model_dump(), created_by=actor_id, updated_by=actor_id)
                )
        if errors:
            return CategoryImportResponse(
                total=len(rows), success=0, skipped=0, failed=len(errors), errors=errors
            )
        try:
            async with transaction_scope(self.session):
                self.session.add_all(inserts)
                await self.session.flush()
        except IntegrityError as exc:
            raise AppError(
                "CATEGORY_IMPORT_CONFLICT", "Import conflicts with existing category data", 409
            ) from exc
        return CategoryImportResponse(
            total=len(rows), success=len(inserts), skipped=skipped, failed=0, errors=[]
        )
