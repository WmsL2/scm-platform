"""Extract WPS/Excel cell images referenced by DISPIMG formulas."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree

_DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
_MAIN_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_DISPIMG_PATTERN = re.compile(r'DISPIMG\s*\(\s*"(?P<image_id>[^"]+)"', re.IGNORECASE)
_ALLOWED_EXTENSIONS = {".jpeg", ".jpg", ".png", ".webp"}
_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_MAX_TOTAL_IMAGE_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class ExcelImage:
    extension: str
    content: bytes


def dispimg_image_id(value: str | None) -> str | None:
    if not value:
        return None
    match = _DISPIMG_PATTERN.search(value)
    return match.group("image_id") if match else None


def extract_dispimg_images(file_bytes: bytes) -> dict[str, ExcelImage]:
    """Return DISPIMG identifiers mapped to safely extracted embedded image bytes."""
    try:
        archive = zipfile.ZipFile(BytesIO(file_bytes))
    except zipfile.BadZipFile:
        return {}
    with archive:
        try:
            cell_images = ElementTree.fromstring(archive.read("xl/cellimages.xml"))
            relationships = ElementTree.fromstring(archive.read("xl/_rels/cellimages.xml.rels"))
        except (KeyError, ElementTree.ParseError):
            return {}
        relationship_targets = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships.findall(f"{{{_PACKAGE_REL_NS}}}Relationship")
            if item.attrib.get("Type", "").endswith("/image")
            and item.attrib.get("TargetMode") != "External"
        }
        result: dict[str, ExcelImage] = {}
        total_bytes = 0
        for picture in cell_images.findall(f".//{{{_DRAWING_NS}}}pic"):
            properties = picture.find(f".//{{{_DRAWING_NS}}}cNvPr")
            blip = picture.find(f".//{{{_MAIN_NS}}}blip")
            if properties is None or blip is None:
                continue
            image_id = properties.attrib.get("name")
            relationship_id = blip.attrib.get(f"{{{_REL_NS}}}embed")
            target = relationship_targets.get(relationship_id or "")
            if not image_id or not target:
                continue
            media_path = PurePosixPath("xl") / PurePosixPath(target)
            if ".." in media_path.parts or not str(media_path).startswith("xl/media/"):
                continue
            extension = media_path.suffix.lower()
            if extension not in _ALLOWED_EXTENSIONS:
                continue
            try:
                image_info = archive.getinfo(str(media_path))
            except KeyError:
                continue
            if image_info.file_size > _MAX_IMAGE_BYTES:
                continue
            total_bytes += image_info.file_size
            if total_bytes > _MAX_TOTAL_IMAGE_BYTES:
                break
            result[image_id] = ExcelImage(extension=extension, content=archive.read(image_info))
        return result
