"""Inspect and stream WPS/Excel cell images referenced by DISPIMG formulas."""

from __future__ import annotations

import posixpath
import re
import shutil
import warnings
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from types import TracebackType
from xml.etree import ElementTree

from PIL import Image, UnidentifiedImageError

_DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
_MAIN_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_DISPIMG_PATTERN = re.compile(r'DISPIMG\s*\(\s*"(?P<image_id>[^"]+)"', re.IGNORECASE)
_BROWSER_IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
_CONVERT_TO_PNG_EXTENSIONS = {".bmp", ".emf", ".tif", ".tiff", ".wmf"}
_SUPPORTED_IMAGE_EXTENSIONS = _BROWSER_IMAGE_EXTENSIONS | _CONVERT_TO_PNG_EXTENSIONS
_MAX_IN_MEMORY_IMAGE_BYTES = 10 * 1024 * 1024
_MAX_IN_MEMORY_TOTAL_BYTES = 50 * 1024 * 1024


class DispimgImageError(ValueError):
    """Raised when a DISPIMG reference cannot become a safe browser image."""


@dataclass(frozen=True)
class ExcelImage:
    extension: str
    content: bytes


@dataclass(frozen=True)
class ExcelImageEntry:
    image_id: str
    extension: str
    media_path: str
    file_size: int


@dataclass(frozen=True)
class ExcelImageFile:
    extension: str
    path: Path


def dispimg_image_id(value: str | None) -> str | None:
    if not value:
        return None
    match = _DISPIMG_PATTERN.search(value)
    return match.group("image_id") if match else None


class DispimgImageArchive:
    """Keep one workbook ZIP open and extract one requested image at a time."""

    def __init__(self, source: Path) -> None:
        try:
            self._archive = zipfile.ZipFile(source)
        except zipfile.BadZipFile as exc:
            raise DispimgImageError("The workbook ZIP package is invalid") from exc
        try:
            self.entries = _image_entries(self._archive)
        except Exception:
            self._archive.close()
            raise

    def __enter__(self) -> DispimgImageArchive:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        self.close()

    def close(self) -> None:
        self._archive.close()

    def validate_reference(self, image_id: str, *, max_image_bytes: int) -> ExcelImageEntry:
        entry = self.entries.get(image_id)
        if entry is None:
            raise DispimgImageError("The embedded image referenced by the formula is missing")
        if entry.extension not in _SUPPORTED_IMAGE_EXTENSIONS:
            raise DispimgImageError(
                f"Embedded image type {entry.extension or '(none)'} is not supported"
            )
        if entry.file_size > max_image_bytes:
            max_image_mb = max_image_bytes // (1024 * 1024)
            raise DispimgImageError(f"The embedded image exceeds {max_image_mb} MB")
        return entry

    def extract_to(
        self, image_id: str, destination_base: Path, *, max_image_bytes: int
    ) -> ExcelImageFile:
        entry = self.validate_reference(image_id, max_image_bytes=max_image_bytes)
        raw_path = destination_base.with_suffix(entry.extension)
        try:
            with self._archive.open(entry.media_path) as source, raw_path.open("wb") as target:
                shutil.copyfileobj(source, target, length=1024 * 1024)
            return _browser_image_file(raw_path, source_extension=entry.extension)
        except (
            OSError,
            UnidentifiedImageError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raw_path.unlink(missing_ok=True)
            raise DispimgImageError("The embedded image cannot be decoded safely") from exc


def inspect_dispimg_references(
    source: Path, image_ids: set[str], *, max_image_bytes: int
) -> dict[str, str]:
    """Return validation errors without reading every image payload into memory."""
    errors: dict[str, str] = {}
    with DispimgImageArchive(source) as archive:
        for image_id in image_ids:
            try:
                archive.validate_reference(image_id, max_image_bytes=max_image_bytes)
            except DispimgImageError as exc:
                errors[image_id] = str(exc)
    return errors


def extract_dispimg_images(file_bytes: bytes) -> dict[str, ExcelImage]:
    """Small-workbook compatibility helper; raises instead of silently truncating."""
    try:
        archive = zipfile.ZipFile(BytesIO(file_bytes))
    except zipfile.BadZipFile:
        return {}
    with archive:
        return _extract_dispimg_images_in_memory(archive)


def extract_dispimg_images_from_path(source: Path) -> dict[str, ExcelImage]:
    """Small-workbook compatibility helper; large imports must use DispimgImageArchive."""
    try:
        archive = zipfile.ZipFile(source)
    except zipfile.BadZipFile:
        return {}
    with archive:
        return _extract_dispimg_images_in_memory(archive)


def _image_entries(archive: zipfile.ZipFile) -> dict[str, ExcelImageEntry]:
    try:
        cell_images = ElementTree.fromstring(archive.read("xl/cellimages.xml"))
        relationships = ElementTree.fromstring(archive.read("xl/_rels/cellimages.xml.rels"))
    except KeyError:
        return {}
    except ElementTree.ParseError as exc:
        raise DispimgImageError("The workbook embedded-image metadata is invalid") from exc
    relationship_targets = {
        item.attrib["Id"]: item.attrib["Target"]
        for item in relationships.findall(f"{{{_PACKAGE_REL_NS}}}Relationship")
        if item.attrib.get("Type", "").endswith("/image")
        and item.attrib.get("TargetMode") != "External"
    }
    result: dict[str, ExcelImageEntry] = {}
    for picture in cell_images.findall(f".//{{{_DRAWING_NS}}}pic"):
        properties = picture.find(f".//{{{_DRAWING_NS}}}cNvPr")
        blip = picture.find(f".//{{{_MAIN_NS}}}blip")
        if properties is None or blip is None:
            continue
        image_id = properties.attrib.get("name")
        relationship_id = blip.attrib.get(f"{{{_REL_NS}}}embed")
        target = relationship_targets.get(relationship_id or "")
        media_path = _media_path(target)
        if not image_id or media_path is None:
            continue
        try:
            image_info = archive.getinfo(media_path)
        except KeyError:
            continue
        result[image_id] = ExcelImageEntry(
            image_id=image_id,
            extension=PurePosixPath(media_path).suffix.lower(),
            media_path=media_path,
            file_size=image_info.file_size,
        )
    return result


def _media_path(target: str | None) -> str | None:
    if not target:
        return None
    candidate = target.replace("\\", "/")
    candidate = candidate[1:] if candidate.startswith("/") else candidate
    if not candidate.startswith("xl/"):
        candidate = f"xl/{candidate}"
    normalized = posixpath.normpath(candidate)
    if not normalized.startswith("xl/media/") or ".." in PurePosixPath(normalized).parts:
        return None
    return normalized


def _browser_image_file(source: Path, *, source_extension: str) -> ExcelImageFile:
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(source) as image:
            if source_extension in _BROWSER_IMAGE_EXTENSIONS:
                image.verify()
                return ExcelImageFile(extension=source_extension, path=source)
            image.load()
            converted = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            output = source.with_name(f"{source.stem}-browser.png")
            converted.save(output, format="PNG", optimize=True)
    source.unlink(missing_ok=True)
    return ExcelImageFile(extension=".png", path=output)


def _extract_dispimg_images_in_memory(
    archive: zipfile.ZipFile,
) -> dict[str, ExcelImage]:
    result: dict[str, ExcelImage] = {}
    total_bytes = 0
    for image_id, entry in _image_entries(archive).items():
        if entry.extension not in _BROWSER_IMAGE_EXTENSIONS:
            continue
        if entry.file_size > _MAX_IN_MEMORY_IMAGE_BYTES:
            raise DispimgImageError("An embedded image is too large for in-memory extraction")
        total_bytes += entry.file_size
        if total_bytes > _MAX_IN_MEMORY_TOTAL_BYTES:
            raise DispimgImageError(
                "Embedded images exceed the safe in-memory extraction limit"
            )
        result[image_id] = ExcelImage(
            extension=entry.extension,
            content=archive.read(entry.media_path),
        )
    return result
