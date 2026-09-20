# ruff: noqa: E501,E701,E702
# mypy: ignore-errors
import asyncio
import logging
from io import BytesIO

from openpyxl import Workbook
from openpyxl.drawing.image import Image as WorkbookImage
from openpyxl.utils import get_column_letter
from PIL import Image as PillowImage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.infrastructure.adapters import get_object_storage
from app.modules.catalog.application.media import local_media_storage_key
from app.modules.catalog.application.product_export_columns import PRODUCT_EXPORT_COLUMNS
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.supplier.domain.rules import CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier

logger = logging.getLogger(__name__)
_MAX_IMAGE_DIMENSION = 80
_IMAGE_ROW_HEIGHT = 60
_IMAGE_COLUMN_WIDTH = 16


class ProductExportService:
    def __init__(self, session: AsyncSession) -> None: self.session = session
    async def export(self, product_ids: list, column_keys: list[str], can_export_disabled: bool) -> bytes:
        rows = []
        for offset in range(0, len(product_ids), 500):
            rows.extend((await self.session.execute(select(Product, Supplier).join(Supplier).where(Product.id.in_(product_ids[offset:offset + 500])))).all())
        by_id = {product.id: (product, supplier) for product, supplier in rows}
        selected = [by_id.get(product_id) for product_id in product_ids]
        if len(by_id) != len(product_ids) or any(item is None for item in selected):
            raise AppError("PRODUCT_EXPORT_SELECTION_STALE", "所选商品已发生变化，请刷新列表后重新选择", 409)
        for product, supplier in selected:
            if (product.status == ProductStatus.DISABLED and not can_export_disabled) or (product.status == ProductStatus.ACTIVE and (supplier.is_deleted or supplier.cooperation_status != CooperationStatus.NORMAL)):
                raise AppError("PRODUCT_EXPORT_SELECTION_STALE", "所选商品已发生变化，请刷新列表后重新选择", 409)
        columns = [column for column in PRODUCT_EXPORT_COLUMNS if column.key in column_keys]
        image_bytes_by_reference = await self._read_export_images(columns, selected)
        return await asyncio.to_thread(self._build, columns, selected, image_bytes_by_reference)

    @staticmethod
    async def _read_export_images(columns, rows) -> dict[str, bytes | None]:
        if not any(column.key == "image_reference" for column in columns):
            return {}
        storage = get_object_storage()
        image_bytes_by_reference: dict[str, bytes | None] = {}
        references = dict.fromkeys(
            product.image_reference for product, _supplier in rows if product.image_reference
        )
        for reference in references:
            key = local_media_storage_key(reference)
            if key is None:
                image_bytes_by_reference[reference] = None
                continue
            try:
                image_bytes_by_reference[reference] = await storage.read(key)
            except Exception:
                logger.warning("Unable to read product export image: %s", reference, exc_info=True)
                image_bytes_by_reference[reference] = None
        return image_bytes_by_reference

    @staticmethod
    def _build(columns, rows, image_bytes_by_reference: dict[str, bytes | None]) -> bytes:
        workbook = Workbook(); sheet = workbook.active; sheet.title = "商品主数据"; sheet.freeze_panes = "A2"
        sheet.append([column.header for column in columns])
        image_column_index = next((index for index, column in enumerate(columns, start=1) if column.key == "image_reference"), None)
        image_sources: list[BytesIO] = []
        for row_number, (product, supplier) in enumerate(rows, start=2):
            sheet.append([None if column.key == "image_reference" else column.value(product, supplier) for column in columns])
            if image_column_index is not None:
                image_source = ProductExportService._workbook_image_source(image_bytes_by_reference.get(product.image_reference))
                if image_source is not None:
                    image = WorkbookImage(image_source)
                    scale = min(_MAX_IMAGE_DIMENSION / image.width, _MAX_IMAGE_DIMENSION / image.height, 1)
                    image.width *= scale; image.height *= scale
                    sheet.add_image(image, f"{get_column_letter(image_column_index)}{row_number}")
                    sheet.row_dimensions[row_number].height = _IMAGE_ROW_HEIGHT
                    image_sources.append(image_source)
        sheet.auto_filter.ref = sheet.dimensions
        for column in sheet.columns: sheet.column_dimensions[column[0].column_letter].width = 18
        if image_column_index is not None:
            sheet.column_dimensions[get_column_letter(image_column_index)].width = _IMAGE_COLUMN_WIDTH
        output = BytesIO(); workbook.save(output); return output.getvalue()

    @staticmethod
    def _workbook_image_source(content: bytes | None) -> BytesIO | None:
        if not content:
            return None
        try:
            with PillowImage.open(BytesIO(content)) as image:
                image.load()
                if image.format in {"PNG", "JPEG", "GIF"}:
                    return BytesIO(content)
                converted = BytesIO()
                image.convert("RGBA" if "A" in image.getbands() else "RGB").save(
                    converted, format="PNG"
                )
                return converted
        except Exception:
            logger.warning("Unable to decode product export image", exc_info=True)
            return None
