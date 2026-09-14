from io import BytesIO
from types import SimpleNamespace
from typing import cast
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.application.excel_images import (
    ExcelImage,
    dispimg_image_id,
    extract_dispimg_images,
)
from app.modules.catalog.application.import_service import ProductImportService
from app.modules.catalog.infrastructure.models import ProductImportRow, ProductImportTask


def _workbook_with_wps_cell_image() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "xl/cellimages.xml",
            """<etc:cellImages xmlns:etc=\"http://www.wps.cn/officeDocument/2017/etCustomData\" """
            """xmlns:xdr=\"http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing\" """
            """xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" """
            """xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"""
            """<etc:cellImage><xdr:pic><xdr:nvPicPr><xdr:cNvPr name=\"ID_PRODUCT\"/>"""
            """</xdr:nvPicPr><xdr:blipFill><a:blip r:embed=\"rId1\"/>"""
            """</xdr:blipFill></xdr:pic></etc:cellImage></etc:cellImages>""",
        )
        archive.writestr(
            "xl/_rels/cellimages.xml.rels",
            """<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"""
            """<Relationship Id=\"rId1\" """
            """Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/"""
            """image\" """
            """Target=\"media/image1.png\"/></Relationships>""",
        )
        archive.writestr("xl/media/image1.png", b"png-content")
    return output.getvalue()


def test_extracts_wps_dispimg_image_by_formula_identifier() -> None:
    images = extract_dispimg_images(_workbook_with_wps_cell_image())

    assert dispimg_image_id('=DISPIMG("ID_PRODUCT",1)') == "ID_PRODUCT"
    assert images["ID_PRODUCT"].extension == ".png"
    assert images["ID_PRODUCT"].content == b"png-content"


async def test_staged_dispimg_image_becomes_relative_product_reference() -> None:
    class MemoryStorage:
        async def save(self, name: str, content: bytes) -> str:
            assert name.startswith("product-images/")
            assert content == b"png-content"
            return "product-images/task/image.png"

        async def read(self, key: str) -> bytes:
            raise AssertionError(f"unexpected read: {key}")

        async def delete(self, key: str) -> None:
            raise AssertionError(f"unexpected delete: {key}")

    row = ProductImportRow(
        id=uuid4(),
        source_row_number=2,
        source_data={"图片": '=DISPIMG("ID_PRODUCT",1)'},
        calculated_data={},
        is_valid=False,
    )
    task = SimpleNamespace(id=uuid4(), rows=[row])
    service = ProductImportService(cast(AsyncSession, None), storage=MemoryStorage())

    await service._stage_images(
        cast(ProductImportTask, task),
        {"ID_PRODUCT": ExcelImage(extension=".png", content=b"png-content")},
    )

    assert row.image_storage_key == "product-images/task/image.png"
    assert service._image_reference(row) == "local-media/product-images/task/image.png"


async def test_confirm_reads_temporary_workbook_before_staging_embedded_image() -> None:
    class MemoryStorage:
        def __init__(self) -> None:
            self.saved: list[tuple[str, bytes]] = []

        async def read(self, key: str) -> bytes:
            assert key == "product-import-sources/task.xlsx"
            return _workbook_with_wps_cell_image()

        async def save(self, name: str, content: bytes) -> str:
            self.saved.append((name, content))
            return "product-images/task/image.png"

        async def delete(self, key: str) -> None:
            raise AssertionError(f"unexpected delete: {key}")

    row = ProductImportRow(
        id=uuid4(),
        source_row_number=2,
        source_data={"图片": '=DISPIMG("ID_PRODUCT",1)'},
        calculated_data={},
        is_valid=False,
    )
    task = SimpleNamespace(
        id=uuid4(), rows=[row], source_file_storage_key="product-import-sources/task.xlsx"
    )
    storage = MemoryStorage()
    service = ProductImportService(cast(AsyncSession, None), storage=storage)

    assert row.image_storage_key is None
    saved_keys = await service._stage_confirmed_row_images(cast(ProductImportTask, task), [row])

    assert saved_keys == ["product-images/task/image.png"]
    assert storage.saved[0][0].startswith("product-images/")
    assert row.image_storage_key == "product-images/task/image.png"
