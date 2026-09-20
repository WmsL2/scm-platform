from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.adapters import ObjectStorage
from app.modules.catalog.application import excel_images
from app.modules.catalog.application.excel_images import (
    DispimgImageArchive,
    DispimgImageError,
    ExcelImage,
    dispimg_image_id,
    extract_dispimg_images,
    extract_dispimg_images_from_path,
    inspect_dispimg_references,
)
from app.modules.catalog.application.import_service import ProductImportService
from app.modules.catalog.infrastructure.models import ProductImportRow, ProductImportTask


def _image_content(image_format: str = "PNG") -> bytes:
    output = BytesIO()
    Image.new("RGB", (2, 2), color=(120, 80, 40)).save(output, format=image_format)
    return output.getvalue()


def _workbook_with_wps_cell_image(
    *, extension: str = ".png", content: bytes | None = None
) -> bytes:
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
            f"""Target=\"media/image1{extension}\"/></Relationships>""",
        )
        archive.writestr(f"xl/media/image1{extension}", content or _image_content())
    return output.getvalue()


def test_extracts_wps_dispimg_image_by_formula_identifier() -> None:
    images = extract_dispimg_images(_workbook_with_wps_cell_image())

    assert dispimg_image_id('=DISPIMG("ID_PRODUCT",1)') == "ID_PRODUCT"
    assert images["ID_PRODUCT"].extension == ".png"
    assert images["ID_PRODUCT"].content == _image_content()


def test_extracts_wps_dispimg_images_from_workbook_path(tmp_path: Path) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(_workbook_with_wps_cell_image())

    images = extract_dispimg_images_from_path(source)

    assert images["ID_PRODUCT"].content == _image_content()


def test_streams_and_converts_tiff_to_browser_png(tmp_path: Path) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(
        _workbook_with_wps_cell_image(
            extension=".tiff",
            content=_image_content("TIFF"),
        )
    )

    with DispimgImageArchive(source) as archive:
        extracted = archive.extract_to(
            "ID_PRODUCT",
            tmp_path / "image",
            max_image_bytes=64 * 1024 * 1024,
        )

    assert extracted.extension == ".png"
    with Image.open(extracted.path) as image:
        assert image.format == "PNG"
        assert image.size == (2, 2)


def test_reports_missing_dispimg_reference_without_silent_truncation(tmp_path: Path) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(_workbook_with_wps_cell_image())

    errors = inspect_dispimg_references(
        source,
        {"ID_PRODUCT", "ID_MISSING"},
        max_image_bytes=64 * 1024 * 1024,
    )

    assert "ID_PRODUCT" not in errors
    assert "missing" in errors["ID_MISSING"]


def test_streaming_extraction_is_not_limited_by_legacy_aggregate_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(_workbook_with_wps_cell_image())
    monkeypatch.setattr(excel_images, "_MAX_IN_MEMORY_TOTAL_BYTES", 1)

    with pytest.raises(DispimgImageError, match="in-memory extraction limit"):
        extract_dispimg_images_from_path(source)

    with DispimgImageArchive(source) as archive:
        extracted = archive.extract_to(
            "ID_PRODUCT",
            tmp_path / "streamed-image",
            max_image_bytes=64 * 1024 * 1024,
        )

    assert extracted.path.read_bytes() == _image_content()


async def test_staged_dispimg_image_becomes_relative_product_reference() -> None:
    class MemoryStorage:
        async def save(self, name: str, content: bytes) -> str:
            assert name.startswith("product-images/")
            assert content == _image_content()
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
    service = ProductImportService(
        cast(AsyncSession, None), storage=cast(ObjectStorage, MemoryStorage())
    )

    await service._stage_images(
        cast(ProductImportTask, task),
        {"ID_PRODUCT": ExcelImage(extension=".png", content=_image_content())},
    )

    assert row.image_storage_key == "product-images/task/image.png"
    assert service._image_reference(row) == "local-media/product-images/task/image.png"


async def test_confirm_reads_temporary_workbook_before_staging_embedded_image() -> None:
    class MemoryStorage:
        def __init__(self) -> None:
            self.saved: list[tuple[str, bytes]] = []

        async def copy_to(self, key: str, destination: Path) -> None:
            assert key == "product-import-sources/task.xlsx"
            destination.write_bytes(_workbook_with_wps_cell_image())

        async def save(self, name: str, content: bytes) -> str:
            self.saved.append((name, content))
            return "product-images/task/image.png"

        async def save_file(self, name: str, source: Path) -> str:
            self.saved.append((name, source.read_bytes()))
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
