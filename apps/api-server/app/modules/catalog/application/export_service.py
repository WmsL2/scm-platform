# ruff: noqa: E501,E701,E702
# mypy: ignore-errors
import asyncio
import logging
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import xlsxwriter
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
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("商品主数据")
        sheet.freeze_panes(1, 0)
        sheet.write_row(0, 0, [column.header for column in columns])
        image_column_index = next(
            (index for index, column in enumerate(columns) if column.key == "image_reference"),
            None,
        )
        image_format = workbook.add_format({"align": "center", "valign": "vcenter"})
        date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
        image_sources: list[BytesIO] = []
        for row_index, (product, supplier) in enumerate(rows, start=1):
            for column_index, column in enumerate(columns):
                if column.key == "image_reference":
                    continue
                value = column.value(product, supplier)
                if column.key == "listed_at" and value is not None:
                    sheet.write_datetime(row_index, column_index, value, date_format)
                elif value is not None:
                    sheet.write(row_index, column_index, value)
            if image_column_index is not None:
                image_source = ProductExportService._prepare_embedded_image(
                    image_bytes_by_reference.get(product.image_reference)
                )
                if image_source is not None:
                    sheet.embed_image(
                        row_index,
                        image_column_index,
                        "product-image.png",
                        {"image_data": image_source, "cell_format": image_format},
                    )
                    image_sources.append(image_source)
                    sheet.set_row(row_index, _IMAGE_ROW_HEIGHT)
        sheet.autofilter(0, 0, len(rows), max(len(columns) - 1, 0))
        sheet.set_column(0, max(len(columns) - 1, 0), 18)
        if image_column_index is not None:
            sheet.set_column_pixels(image_column_index, image_column_index, 90)
        workbook.close()
        return ProductExportService._normalize_rich_data_relationship_path(output.getvalue())

    @staticmethod
    def _normalize_rich_data_relationship_path(content: bytes) -> bytes:
        bad_path = "/xl/richData/_rels/richValueRel.xml.rels"
        good_path = "xl/richData/_rels/richValueRel.xml.rels"
        with ZipFile(BytesIO(content)) as source:
            names = source.namelist()
            if bad_path not in names or good_path in names:
                return content
            output = BytesIO()
            with ZipFile(output, "w", ZIP_DEFLATED) as target:
                for info in source.infolist():
                    target_info = ZipInfo(good_path if info.filename == bad_path else info.filename)
                    target_info.date_time = info.date_time
                    target_info.external_attr = info.external_attr
                    target_info.extra = info.extra
                    target_info.comment = info.comment
                    target_info.compress_type = info.compress_type
                    target.writestr(target_info, source.read(info.filename))
        return output.getvalue()

    @staticmethod
    def _prepare_embedded_image(content: bytes | None) -> BytesIO | None:
        if not content:
            return None
        try:
            with PillowImage.open(BytesIO(content)) as image:
                image.load()
                if image.format in {"PNG", "JPEG"} and (
                    image.width >= _MAX_IMAGE_DIMENSION or image.height >= _MAX_IMAGE_DIMENSION
                ):
                    return BytesIO(content)
                prepared = image.convert("RGBA")
                if image.width >= _MAX_IMAGE_DIMENSION or image.height >= _MAX_IMAGE_DIMENSION:
                    prepared.thumbnail(
                        (_MAX_IMAGE_DIMENSION, _MAX_IMAGE_DIMENSION),
                        PillowImage.Resampling.LANCZOS,
                    )
                canvas = PillowImage.new("RGBA", (_MAX_IMAGE_DIMENSION, _MAX_IMAGE_DIMENSION))
                canvas.alpha_composite(
                    prepared,
                    ((canvas.width - prepared.width) // 2, (canvas.height - prepared.height) // 2),
                )
                output = BytesIO()
                canvas.save(output, format="PNG")
                output.seek(0)
                return output
        except Exception:
            logger.warning("Unable to decode product export image", exc_info=True)
            return None
