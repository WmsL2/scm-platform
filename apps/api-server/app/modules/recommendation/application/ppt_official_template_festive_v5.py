"""In-place filling of the reviewed two-page private JD_FESTIVE_RED v5 deck.

The reference shape is never cleared or rebuilt. Dynamic values replace the
customer-owned gap Runs in that original text box, while native paragraph tabs
keep adjacent fields separated without floating text layers or space padding.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
from json import dumps
from math import ceil, floor
from pathlib import Path
from re import split
from typing import Any
from zipfile import BadZipFile, ZipFile

from PIL import Image, UnidentifiedImageError
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.exc import PackageNotFoundError
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches

from app.common.contracts import AppError
from app.modules.recommendation.application.ppt_layout_preview import (
    LayoutPreviewIssue,
    add_layout_preview_pages,
)
from app.modules.recommendation.application.ppt_template_manifest import (
    PptxSlotManifest,
    get_pptx_manifest,
)
from app.modules.recommendation.application.ppt_template_registry import (
    PptTemplateDefinition,
    resolve_ppt_template_asset,
)

logger = logging.getLogger(__name__)

_SOURCE_SHA256 = "4c1c4922d63f7932a37e51308a25ea3b426cf4ca7f126dcb43aaf208447f1657"
_SOURCE_TXT_SHA256 = "afb9154ee68f5de9907ea85ce33953a64dd4ea124c445523bcb1bf54f2014201"
_SOURCE_STRUCTURE_FINGERPRINT = "4f203800d937e32a423d3d3732fa4bf5b2b5020076b915ee82fb0cc13da61198"
_JD_FONT = "京东朗正体 玲珑"
_EMU_PER_POINT = 12_700
_TRANSPARENT_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````"
    b"\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82"
)
_TEXT_SLOT_GEOMETRY = {
    "SCM_FIELD_TITLE": (5.820, 0.587, 7.161, 1.110),
    "SCM_FIELD_REFERENCE": (5.863, 1.620, 7.028, 1.160),
    "SCM_FIELD_SELLING_POINTS": (5.863, 2.702, 7.029, 1.816),
}
_IMAGE_SLOT_GEOMETRY = {
    "SCM_SLOT_IMAGE_MAIN": (0.357, 0.995, 5.343, 5.320),
    "SCM_SLOT_IMAGE_SUPPLEMENT_01": (6.053, 5.010, 1.811, 1.733),
    "SCM_SLOT_IMAGE_SUPPLEMENT_02": (7.983, 5.010, 1.811, 1.733),
    "SCM_SLOT_IMAGE_SUPPLEMENT_03": (9.912, 5.010, 1.811, 1.733),
}
_SUPPLEMENT_IMAGE_SLOT_NAMES = tuple(
    name for name in _IMAGE_SLOT_GEOMETRY if name != "SCM_SLOT_IMAGE_MAIN"
)
# The reviewed template gives each supplementary image 124.8pt of height.  A
# small, bounded reduction can absorb an otherwise harmless final text line;
# pictures are still rendered with ``contain`` and therefore never stretched
# or cropped.  Do not use this as a general text-overflow escape hatch.
_MIN_SUPPLEMENT_IMAGE_HEIGHT_PT = 100.0
_REFERENCE_TEXT = (
    "市场参考价：             京东大客户价：           折扣率：   \v"
    "SKU：                    市场参考价不要虚高，客户会查！",
    "货期：                   发货物流/快递：          质保： ",
)
# paragraph, target run, reserved width in points. The original value positions
# are the whitespace Runs between fixed labels. In the customer CJK font those
# spaces render at approximately half an em, not the 0.25 em estimate formerly
# used here. Prefixes remain copied from the original Run, so the value width
# never double-counts a fixed label or moves a later fixed element.
_REFERENCE_GAP_SPACE_EM = 0.50
_VALUE_RUNS: dict[str, tuple[int, int, float]] = {
    "market_price": (0, 1, 13 * 14 * _REFERENCE_GAP_SPACE_EM),
    "jd_customer_price": (0, 3, 11 * 14 * _REFERENCE_GAP_SPACE_EM),
    "discount_rate": (0, 5, 75),
    "sku": (0, 9, 20 * 14 * _REFERENCE_GAP_SPACE_EM),
    "fulfillment_cycle": (1, 1, 15 * 14 * _REFERENCE_GAP_SPACE_EM),
    "shipping_courier": (1, 6, 10 * 14 * _REFERENCE_GAP_SPACE_EM),
    "warranty_period": (1, 10, 120),
}
# Positions are relative to the original reference text frame's left inset.  They
# retain the customer's two-row layout while adding 8--12pt of visible space
# between adjacent attributes without depending on a run of ASCII spaces.
_REFERENCE_TAB_STOPS_PT = {
    0: (90.0, 157.0, 333.0),
    1: (118.0, 311.0),
}
_TAB_SEPARATED_FIELDS = frozenset(
    {"market_price", "jd_customer_price", "sku", "fulfillment_cycle", "shipping_courier"}
)
_ASSET_MARKER = "JD_FESTIVE_RED:5:two-page:" + _SOURCE_SHA256


def _error(message: str) -> AppError:
    return AppError("PPT_TEMPLATE_ASSET_STRUCTURE_INVALID", message, 409)


def _capacity_error(
    field: str,
    product_identifier: str,
    *,
    required_width_pt: float | None = None,
    available_width_pt: float | None = None,
    required_lines: int | None = None,
    allowed_lines: int | None = None,
    overflow_height_pt: float | None = None,
    remaining_height_pt: float | None = None,
    layout_diagnostic: str | None = None,
) -> AppError:
    detail = f"商品标识 {product_identifier or '未知'}"
    if required_width_pt is not None and available_width_pt is not None:
        detail += f"；预计需 {required_width_pt:.1f}pt，可用 {available_width_pt:.1f}pt"
    if required_lines is not None and allowed_lines is not None:
        detail += f"；预计 {required_lines} 行，可用 {allowed_lines} 行"
    if overflow_height_pt is not None and remaining_height_pt is not None:
        detail += f"；还需 {overflow_height_pt:.1f}pt，页面剩余 {remaining_height_pt:.1f}pt"
    if layout_diagnostic:
        detail += f"；{layout_diagnostic}"
    return AppError(
        "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED",
        f"JD_FESTIVE_RED v5 {field}超出客户固定槽位安全容量（{detail}）",
        422,
    )


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mappings(value: object) -> list[Mapping[str, object]]:
    return [_mapping(item) for item in value] if isinstance(value, list) else []


def _text(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    return str(value).strip() if value is not None else ""


def _load(path: Path) -> Any:
    try:
        return Presentation(str(path))
    except (OSError, ValueError, KeyError, BadZipFile, PackageNotFoundError, SyntaxError) as error:
        raise _error("运行模板无法读取") from error


def _structure_fingerprint(presentation: Any) -> str:
    payload = {
        "slides": len(presentation.slides),
        "shapes": [
            [(int(s.shape_type), s.left, s.top, s.width, s.height) for s in slide.shapes]
            for slide in presentation.slides
        ],
    }
    return sha256(dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


def _contract_digest(presentation: Any) -> str:
    def node_contract(node: Any) -> object:
        return (
            node.tag,
            sorted(node.attrib.items()),
            (node.text or "") if node.tag.endswith("}t") else None,
            [node_contract(child) for child in node],
        )

    payload = {
        "slides": [node_contract(slide._element) for slide in presentation.slides],
        "static_parts": sorted(
            (
                str(part.partname),
                dumps(node_contract(part._element))
                if hasattr(part, "_element")
                else sha256(part.blob).hexdigest(),
            )
            for part in presentation.part.package.iter_parts()
            if str(part.partname).startswith(
                (
                    "/ppt/media/",
                    "/ppt/theme/",
                    "/ppt/slideMasters/",
                    "/ppt/slideLayouts/",
                )
            )
        ),
    }
    return sha256(dumps(payload, ensure_ascii=False).encode("utf-8")).hexdigest()


def _remove_notes(slide: Any) -> None:
    for rel in list(slide.part.rels.values()):
        if "notesSlide" in rel.reltype:
            slide.part.drop_rel(rel.rId)


def _remove_slide(presentation: Any, slide: Any) -> None:
    slide_id = presentation.slides._sldIdLst[list(presentation.slides).index(slide)]
    presentation.part.drop_rel(slide_id.rId)
    presentation.slides._sldIdLst.remove(slide_id)


def _set_paragraph_value(paragraph: Any, value: str) -> None:
    # Keep every original Run, rPr, paragraph property and bullet. Only t changes.
    if not paragraph.runs:
        raise _error("动态段落缺少预留 Run")
    for index, run in enumerate(paragraph.runs):
        run.text = value if index == 0 else ""


def _set_reference_tab_stops(reference: Any) -> None:
    """Use native paragraph tabs for value-to-label spacing in the source box."""
    frame = reference.text_frame
    if len(frame.paragraphs) != 2:
        raise _error("运行模板原位属性段落合同无效")
    for paragraph_index, stops in _REFERENCE_TAB_STOPS_PT.items():
        paragraph = frame.paragraphs[paragraph_index]
        properties = paragraph._p.get_or_add_pPr()
        for existing in list(properties):
            if existing.tag.endswith("}tabLst"):
                properties.remove(existing)
        tab_list = OxmlElement("a:tabLst")
        for stop in stops:
            tab = OxmlElement("a:tab")
            tab.set("pos", str(int(stop * _EMU_PER_POINT)))
            tab_list.append(tab)
        properties.insert(0, tab_list)

    # These are only pre-label layout gaps in the customer paragraph, not label
    # content. Tabs now provide their positioning, so clearing them prevents a
    # tab-plus-spaces double gap while preserving the visible fixed labels.
    frame.paragraphs[1].runs[2].text = frame.paragraphs[1].runs[2].text.lstrip()
    frame.paragraphs[1].runs[7].text = ""


def _price_with_yuan(value: str) -> str:
    """Apply template 2's display-only currency unit after a real amount."""
    return value if not value or value.endswith("元") else value + "元"


def _fill_reference_values(reference: Any, values: Mapping[str, str]) -> None:
    """Fill customer-owned gap Runs in place; fixed label Runs remain untouched."""
    frame = reference.text_frame
    if len(frame.paragraphs) != 2:
        raise _error("运行模板原位属性段落合同无效")
    _set_reference_tab_stops(reference)
    for field, (paragraph_index, run_index, _width) in _VALUE_RUNS.items():
        paragraph = frame.paragraphs[paragraph_index]
        if run_index >= len(paragraph.runs):
            raise _error("运行模板原位属性 Run 合同无效")
        value = values[field]
        paragraph.runs[run_index].text = value + ("\t" if field in _TAB_SEPARATED_FIELDS else "")


def _remove_value_layers(slide: Any) -> None:
    """Remove obsolete renderer-only value layers from the cloned output page."""
    for shape in list(slide.shapes):
        if shape.name.startswith("SCM_VALUE_"):
            shape._element.getparent().remove(shape._element)


def _invisible_run(run: Any) -> None:
    properties = run._r.get_or_add_rPr()
    fill = properties.find("{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
    if fill is None or len(fill) != 1:
        raise _error("属性 Run 缺少原件颜色合同")
    alpha = OxmlElement("a:alpha")
    alpha.set("val", "0")
    fill[0].append(alpha)


def _add_value_layer(slide: Any, reference: Any, field: str) -> None:
    paragraph_index, run_index, _width = _VALUE_RUNS[field]
    layer = slide.shapes.add_textbox(
        reference.left, reference.top, reference.width, reference.height
    )
    layer.name = "SCM_VALUE_" + field
    body = deepcopy(
        reference._element.find(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}txBody"
        )
    )
    old_body = layer._element.find(
        "{http://schemas.openxmlformats.org/presentationml/2006/main}txBody"
    )
    layer._element.replace(old_body, body)
    frame = layer.text_frame
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.word_wrap = False
    target_paragraph = frame.paragraphs[paragraph_index]
    target = target_paragraph.runs[run_index]
    target.text = "{{" + field + "}}"
    # Remove following content only in this value layer; the reference is intact.
    node = target._r.getnext()
    while node is not None:
        following = node.getnext()
        target_paragraph._p.remove(node)
        node = following
    for paragraph in list(frame.paragraphs)[paragraph_index + 1 :]:
        frame._txBody.remove(paragraph._p)
    for paragraph in frame.paragraphs:
        for run in paragraph.runs:
            if run._r is not target._r:
                _invisible_run(run)


def _picture_slot(slide: Any, source: Any, name: str) -> None:
    picture = slide.shapes.add_picture(
        BytesIO(_TRANSPARENT_PNG), source.left, source.top, source.width, source.height
    )
    picture.name = name
    # Retain z-order. In particular, the main image stays above its white region.
    parent = source._element.getparent()
    parent.remove(picture._element)
    parent.replace(source._element, picture._element)


def standardize_jd_festive_red_v5(
    source: Path,
    destination: Path,
    *,
    expected_source_fingerprint: str = _SOURCE_STRUCTURE_FINGERPRINT,
    expected_source_sha256: str | None = _SOURCE_SHA256,
) -> None:
    """Build from the explicitly approved two-page original; never edit it."""
    if (
        expected_source_sha256 is not None
        and sha256(source.read_bytes()).hexdigest() != expected_source_sha256
    ):
        raise _error("原件 SHA-256 与已确认两页正式版本不匹配")
    if expected_source_sha256 is not None:
        description = source.with_suffix(".txt")
        if (
            not description.is_file()
            or sha256(description.read_bytes()).hexdigest() != _SOURCE_TXT_SHA256
        ):
            raise _error("字体/回填说明 TXT 与已确认版本不匹配")
    deck = _load(source)
    if len(deck.slides) != 2 or _structure_fingerprint(deck) != expected_source_fingerprint:
        raise _error("原件页面、形状类型/数量或几何指纹不匹配")
    page = deck.slides[1]
    shapes = list(page.shapes)
    if (
        len(shapes) != 11
        or tuple(p.text for p in shapes[3].text_frame.paragraphs) != _REFERENCE_TEXT
    ):
        raise _error("原件属性标签及换行合同不匹配")
    selling = shapes[2]
    if (
        len(selling.text_frame.paragraphs) != 5
        or selling.text_frame.paragraphs[0].text != "商品卖点："
    ):
        raise _error("原件卖点必须有标题和四条项目符号行")
    for paragraph in selling.text_frame.paragraphs[1:]:
        if not paragraph._p.xpath("./a:pPr/a:buChar[@char='u']"):
            raise _error("原件卖点菱形项目符号不匹配")
    for name, index in _manifest().source_text_slots.items():
        shapes[index].name = name
    _set_paragraph_value(shapes[4].text_frame.paragraphs[0], "{{product_name}}")
    shapes[4].text_frame.auto_size = MSO_AUTO_SIZE.NONE
    selling.text_frame.auto_size = MSO_AUTO_SIZE.NONE
    for index, paragraph in enumerate(selling.text_frame.paragraphs[1:], 1):
        _set_paragraph_value(paragraph, "{{selling_point_" + str(index) + "}}")
    for field in _VALUE_RUNS:
        _add_value_layer(page, shapes[3], field)
    for index, name in zip((1, 8, 10, 9), _IMAGE_SLOT_GEOMETRY, strict=True):
        if index == 1:
            # Preserve the white main-area shape, removing only its instruction.
            for paragraph in shapes[index].text_frame.paragraphs:
                _set_paragraph_value(paragraph, "")
            shapes[index].name = "SCM_STATIC_MAIN_BACKGROUND"
            picture = page.shapes.add_picture(
                BytesIO(_TRANSPARENT_PNG),
                shapes[index].left,
                shapes[index].top,
                shapes[index].width,
                shapes[index].height,
            )
            picture.name = name
        else:
            _picture_slot(page, shapes[index], name)
    for slide in deck.slides:
        _remove_notes(slide)
    deck.core_properties.identifier = _ASSET_MARKER
    deck.core_properties.keywords = _contract_digest(deck)
    destination.parent.mkdir(parents=True, exist_ok=True)
    deck.save(str(destination))
    validate_jd_festive_red_v5_runtime(destination, _manifest())


def _manifest() -> PptxSlotManifest:
    manifest = get_pptx_manifest("JD_FESTIVE_RED", "5")
    if manifest is None:
        raise _error("v5 manifest 不可用")
    return manifest


def _validate_runtime_structure(deck: Any, manifest: PptxSlotManifest) -> None:
    if (
        manifest != _manifest()
        or len(deck.slides) != 2
        or deck.core_properties.identifier != _ASSET_MARKER
        or deck.core_properties.keywords != _contract_digest(deck)
    ):
        raise _error("运行模板版本、页数或结构/Run 样式合同不匹配")
    page = deck.slides[1]
    if len(page.shapes) != 19:
        raise _error("运行模板必须保留原固定形状与七个独立值层")
    names: dict[str, list[Any]] = {}
    for shape in page.shapes:
        names.setdefault(shape.name, []).append(shape)
    required = (
        set(_TEXT_SLOT_GEOMETRY)
        | set(_IMAGE_SLOT_GEOMETRY)
        | {
            "SCM_STATIC_PROJECT_NUMBER",
            "SCM_STATIC_IMAGE_CAPTION",
            "SCM_STATIC_MAIN_BACKGROUND",
        }
        | {"SCM_VALUE_" + field for field in _VALUE_RUNS}
    )
    if any(len(names.get(name, [])) != 1 for name in required):
        raise _error("缺少或重复文本/图片槽位")
    for name, geometry in (_TEXT_SLOT_GEOMETRY | _IMAGE_SLOT_GEOMETRY).items():
        shape = names[name][0]
        if any(
            abs(actual - Inches(expected)) > Inches(0.01)
            for actual, expected in zip(
                (shape.left, shape.top, shape.width, shape.height), geometry, strict=True
            )
        ):
            raise _error("槽位几何不匹配")
    if (
        tuple(p.text for p in names["SCM_FIELD_REFERENCE"][0].text_frame.paragraphs)
        != _REFERENCE_TEXT
    ):
        raise _error("固定属性标签、空格或软换行被改变")
    for name in _IMAGE_SLOT_GEOMETRY:
        if names[name][0].shape_type != MSO_SHAPE_TYPE.PICTURE:
            raise _error("图片槽位类型不匹配")
    tokens = ["{{product_name}}"] + ["{{selling_point_" + str(i) + "}}" for i in range(1, 5)]
    tokens += ["{{" + field + "}}" for field in _VALUE_RUNS]
    for token in tokens:
        if (
            sum(
                run.text == token
                for shape in page.shapes
                if shape.has_text_frame
                for paragraph in shape.text_frame.paragraphs
                for run in paragraph.runs
            )
            != 1
        ):
            raise _error("Token 缺失、错配或重复")


def validate_jd_festive_red_v5_runtime(path: Path, manifest: PptxSlotManifest) -> None:
    _validate_runtime_structure(_load(path), manifest)


def verify_no_sample_media(source: Path, runtime: Path) -> None:
    """The approved source has no example pages or product pictures.

    Retain its static media only; the sole additional media is the transparent
    slot pixel. No media from the obsolete four-page asset is permitted.
    """
    with ZipFile(source) as original, ZipFile(runtime) as cleaned:
        allowed = {
            sha256(original.read(n)).digest()
            for n in original.namelist()
            if n.startswith("ppt/media/")
        }
        allowed.add(sha256(_TRANSPARENT_PNG).digest())
        actual = {
            sha256(cleaned.read(n)).digest()
            for n in cleaned.namelist()
            if n.startswith("ppt/media/")
        }
        if not actual <= allowed or any(
            n.startswith("ppt/slides/slide3.") for n in cleaned.namelist()
        ):
            raise _error("运行模板携带非正式原件静态媒体或多余页面")


def _clone_slide(deck: Any, source: Any) -> Any:
    slide = deck.slides.add_slide(source.slide_layout)
    for shape in list(slide.shapes):
        shape._element.getparent().remove(shape._element)
    rels: dict[str, str] = {}
    for rel in source.part.rels.values():
        if "notesSlide" not in rel.reltype:
            rels[rel.rId] = slide.part.relate_to(
                rel.target_ref if rel.is_external else rel.target_part,
                rel.reltype,
                is_external=rel.is_external,
            )
    # Copy all slide-level properties (background, transition, color override),
    # not only shapes. Layout and master relationship IDs remain remapped.
    copied = deepcopy(source._element)
    for node in copied.iter():
        for key, value in list(node.attrib.items()):
            if (
                key.startswith(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
                )
                and value in rels
            ):
                node.set(key, rels[value])
    slide._element.attrib.clear()
    slide._element.attrib.update(copied.attrib)
    for child in list(slide._element):
        slide._element.remove(child)
    for child in copied:
        slide._element.append(child)
    slide.__dict__.pop("shapes", None)
    return slide


def _format_price(value: object) -> str:
    if value is None or not str(value).strip():
        return ""
    try:
        number = Decimal(str(value))
        return format(number, ".2f") if number.is_finite() and number >= 0 else ""
    except (InvalidOperation, ValueError):
        return ""


def _format_discount(value: object) -> str:
    if value is None or not str(value).strip():
        return ""
    try:
        rate = Decimal(str(value))
        if rate.is_finite() and 0 <= rate <= 1:
            display = format(rate * 100, "f")
            return (display.rstrip("0").rstrip(".") if "." in display else display) + "%"
    except (InvalidOperation, ValueError):
        pass
    return ""


def _estimated_text_width_pt(value: str, size: float) -> float:
    return size * sum(
        0.30
        if c.isspace() or c in ".,:;!ilI|'"
        else 1.0
        if ord(c) >= 0x2E80
        else 0.90
        if c in "MW@#%&"
        else 0.68
        if c.isupper()
        else 0.56
        if c.isdigit()
        else 0.35
        if c in "-_()/[]{}"
        else 0.56
        for c in value
    )


def _selling_point_items(value: str) -> list[str]:
    """Return logical selling points without confusing wrapping with item count.

    Newlines are the authoritative separator when the source has more than one
    non-empty line.  In that form semicolons remain ordinary punctuation inside
    each item.  A single-line source may use Chinese or ASCII semicolons as its
    list separator.  Empty fragments never create bullets.
    """
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) != 1:
        return lines
    return [item.strip() for item in split(r"[;；]", lines[0]) if item.strip()]


def _wrapped_line_count(value: str, width_pt: float, font_size_pt: float) -> int:
    return sum(
        max(1, ceil(_estimated_text_width_pt(line, font_size_pt) / width_pt))
        for line in value.splitlines() or [""]
    )


def _line_advance(paragraph: Any) -> float:
    if not paragraph.runs or paragraph.runs[0].font.size is None:
        raise _error("运行模板动态文本字号合同无效")
    spacing = paragraph.line_spacing
    if spacing is None:
        # The customer title uses Office's automatic paragraph spacing.
        return float(paragraph.runs[0].font.size.pt) * 1.2
    if not isinstance(spacing, (int, float)) or spacing <= 0:
        raise _error("运行模板动态文本行距合同无效")
    size = float(paragraph.runs[0].font.size.pt)
    return max(size, size * float(spacing))


def _move_shapes_after(
    slots: Mapping[str, Any],
    original_tops: Mapping[str, int],
    threshold: int,
    delta: int,
    offsets: dict[str, int] | None = None,
) -> None:
    if not delta:
        return
    for name, shape in slots.items():
        if original_tops[name] >= threshold:
            shape.top += delta
            if offsets is not None:
                offsets[name] = offsets.get(name, 0) + delta


def _compact_supplement_image_area(slots: Mapping[str, Any], required_delta: int) -> int:
    """Recover only the approved spare height in the supplementary-image row.

    The row stays in its original order and at its already-linked top position.
    Reducing all three containers equally retains their alignment; ``_fill_image``
    subsequently uses contain sizing, so the actual image aspect ratios remain
    unchanged.  Returning the applied reduction makes residual overflow remain
    a controlled capacity error.
    """
    if required_delta <= 0:
        return 0
    minimum_height = int(_MIN_SUPPLEMENT_IMAGE_HEIGHT_PT * _EMU_PER_POINT)
    image_slots = [slots[name] for name in _SUPPLEMENT_IMAGE_SLOT_NAMES]
    image_left = min(slot.left for slot in image_slots)
    image_right = max(slot.left + slot.width for slot in image_slots)
    image_top = min(slot.top for slot in image_slots)
    image_bottom = max(slot.top + slot.height for slot in image_slots)
    # The approved asset's unnamed coloured panel is the visual background for
    # the three supplementary slots.  It deliberately remains an original
    # customer shape (and therefore has no new public-asset name).  Locate it
    # from its enclosing geometry rather than changing the frozen PPTX.
    backgrounds = [
        shape
        for name, shape in slots.items()
        if name not in _SUPPLEMENT_IMAGE_SLOT_NAMES
        and shape.shape_type != MSO_SHAPE_TYPE.PICTURE
        and shape.left <= image_left
        and shape.left + shape.width >= image_right
        and shape.top <= image_top
        and shape.top + shape.height >= image_bottom
    ]
    background = max(backgrounds, key=lambda shape: shape.top, default=None)
    available_delta = min(max(0, slot.height - minimum_height) for slot in image_slots)
    applied_delta = min(required_delta, available_delta)
    if not applied_delta:
        return 0
    for slot in image_slots:
        slot.height -= applied_delta
    if background is not None:
        background.height -= applied_delta
    return int(applied_delta)


def _append_selling_points(shape: Any, items: list[str]) -> None:
    """Extend the customer bullet sequence while preserving its exact style."""
    if len(items) <= 4:
        return
    frame = shape.text_frame
    if len(frame.paragraphs) < 5:
        raise _error("运行模板卖点段落合同无效")
    paragraph_template = frame.paragraphs[4]._p
    for item in items[4:]:
        frame._txBody.append(deepcopy(paragraph_template))
        _set_paragraph_value(frame.paragraphs[-1], item)


def _selling_line_advance(paragraph: Any) -> float:
    """Use WPS-observed CJK line boxes for the 12pt diamond bullet rows."""
    advance = _line_advance(paragraph)
    if not paragraph._p.xpath("./a:pPr/a:buChar"):
        return advance
    if not paragraph.runs or paragraph.runs[0].font.size is None:
        raise _error("运行模板卖点字号合同无效")
    spacing = paragraph.line_spacing
    if not isinstance(spacing, (int, float)) or spacing <= 0:
        raise _error("运行模板卖点行距合同无效")
    return max(advance, float(paragraph.runs[0].font.size.pt) * 1.2 * float(spacing))


def _layout_diagnostic(
    slots: Mapping[str, Any],
    original_tops: Mapping[str, int],
    original_heights: Mapping[str, int],
    offsets: Mapping[str, int],
    *,
    slide_height: int,
    required_bottom: int,
    title_lines: int,
    line_counts: Mapping[str, int],
    selling_lines: int,
    supplement_compaction_pt: float,
) -> str:
    geometry_names = (
        "SCM_FIELD_TITLE",
        "SCM_FIELD_REFERENCE",
        "SCM_FIELD_SELLING_POINTS",
        "SCM_STATIC_IMAGE_CAPTION",
        "SCM_SLOT_IMAGE_SUPPLEMENT_01",
        "SCM_SLOT_IMAGE_SUPPLEMENT_02",
        "SCM_SLOT_IMAGE_SUPPLEMENT_03",
    )
    initial_bottom = max(
        original_tops[name] + original_heights[name]
        for name in slots
        if original_tops[name] >= original_tops["SCM_FIELD_TITLE"]
    )
    geometry = "；".join(
        f"{name}:Y {original_tops[name] / _EMU_PER_POINT:.1f}→"
        f"{slots[name].top / _EMU_PER_POINT:.1f}pt，高 "
        f"{original_heights[name] / _EMU_PER_POINT:.1f}→"
        f"{slots[name].height / _EMU_PER_POINT:.1f}pt，累计下移 "
        f"{offsets.get(name, 0) / _EMU_PER_POINT:.1f}pt"
        for name in geometry_names
    )
    field_lines = "，".join(f"{field}={count}" for field, count in line_counts.items())
    return (
        f"页高 {slide_height / _EMU_PER_POINT:.1f}pt，内容底部 "
        f"{required_bottom / _EMU_PER_POINT:.1f}pt，初始余量 "
        f"{(slide_height - initial_bottom) / _EMU_PER_POINT:.1f}pt；"
        f"商品名称={title_lines}行，属性值行数[{field_lines}]，卖点总行数={selling_lines}；"
        f"补图区安全自适应收回 {supplement_compaction_pt:.1f}pt；"
        f"{geometry}"
    )


def _layout_dynamic_text(
    slots: Mapping[str, Any],
    values: Mapping[str, str],
    product_identifier: str,
    slide_height: int,
    *,
    allow_overflow: bool = False,
) -> list[tuple[str, str]]:
    """Expand only cloned content blocks, then move every linked lower shape once."""
    preview_issues: list[tuple[str, str]] = []
    original_tops = {name: shape.top for name, shape in slots.items()}
    original_heights = {name: shape.height for name, shape in slots.items()}
    offsets = {name: 0 for name in slots}
    title = slots["SCM_FIELD_TITLE"]
    title_frame = title.text_frame
    title_advance = _line_advance(title_frame.paragraphs[0])
    title_width = (
        title.width - title_frame.margin_left - title_frame.margin_right
    ) / _EMU_PER_POINT
    title_lines = _wrapped_line_count(values["product_name"], title_width, 20)
    title_capacity = floor(
        (title.height - title_frame.margin_top - title_frame.margin_bottom)
        / _EMU_PER_POINT
        / title_advance
    )
    title_delta = max(0, title_lines - title_capacity) * int(title_advance * _EMU_PER_POINT)
    expanded_fields = ["product_name"] if title_delta else []
    title.height += title_delta
    _move_shapes_after(
        slots, original_tops, original_tops["SCM_FIELD_REFERENCE"], title_delta, offsets
    )

    reference = slots["SCM_FIELD_REFERENCE"]
    reference_frame = reference.text_frame
    reference_width = (
        reference.width - reference_frame.margin_left - reference_frame.margin_right
    ) / _EMU_PER_POINT
    reference_rows = [
        row
        for paragraph in reference_frame.paragraphs
        for row in paragraph.text.splitlines()
    ]
    reference_line_counts = {
        f"row_{index + 1}": _wrapped_line_count(row, reference_width, 14)
        for index, row in enumerate(reference_rows)
    }
    reference_extra_lines = max(0, sum(reference_line_counts.values()) - 3)
    if reference_extra_lines:
        expanded_fields.append("reference_fields")
    reference_delta = int(
        reference_extra_lines
        * max(_line_advance(paragraph) for paragraph in reference_frame.paragraphs)
        * _EMU_PER_POINT
    )
    reference.height += reference_delta
    _move_shapes_after(
        slots,
        original_tops,
        original_tops["SCM_FIELD_SELLING_POINTS"],
        reference_delta,
        offsets,
    )

    selling = slots["SCM_FIELD_SELLING_POINTS"]
    selling_frame = selling.text_frame
    selling_width = (
        selling.width - selling_frame.margin_left - selling_frame.margin_right - 342900
    ) / _EMU_PER_POINT
    items = _selling_point_items(values["selling_points"])
    baseline_selling_height = sum(
        _selling_line_advance(paragraph) for paragraph in selling_frame.paragraphs[:5]
    )
    required_selling_height = 0.0
    selling_lines = 0
    for index, paragraph in enumerate(selling_frame.paragraphs[: len(items) + 1]):
        advance = _selling_line_advance(paragraph)
        content = paragraph.text if index == 0 else items[index - 1]
        paragraph_lines = _wrapped_line_count(
            content, selling_width, float(paragraph.runs[0].font.size.pt)
        )
        selling_lines += paragraph_lines
        required_selling_height += paragraph_lines * advance
    selling_delta = max(
        0,
        int((required_selling_height - baseline_selling_height) * _EMU_PER_POINT),
    )
    if selling_delta:
        expanded_fields.append("selling_points")
    selling.height += selling_delta
    _move_shapes_after(
        slots,
        original_tops,
        original_tops["SCM_STATIC_IMAGE_CAPTION"],
        selling_delta,
        offsets,
    )

    managed = [
        shape
        for name, shape in slots.items()
        if original_tops[name] >= original_tops["SCM_FIELD_TITLE"]
    ]
    required_bottom = max(shape.top + shape.height for shape in managed)
    supplement_compaction = 0
    if required_bottom > slide_height:
        supplement_compaction = _compact_supplement_image_area(
            slots, required_bottom - slide_height
        )
        if supplement_compaction:
            required_bottom = max(shape.top + shape.height for shape in managed)
    if required_bottom > slide_height:
        field = ", ".join(dict.fromkeys(expanded_fields)) or "dynamic_fields"
        diagnostic = _layout_diagnostic(
            slots,
            original_tops,
            original_heights,
            offsets,
            slide_height=slide_height,
            required_bottom=required_bottom,
            title_lines=title_lines,
            line_counts=reference_line_counts,
            selling_lines=selling_lines,
            supplement_compaction_pt=supplement_compaction / _EMU_PER_POINT,
        )
        if not allow_overflow:
            raise _capacity_error(
                field,
                product_identifier,
                overflow_height_pt=(required_bottom - slide_height) / _EMU_PER_POINT,
                remaining_height_pt=0,
                layout_diagnostic=diagnostic,
            )
        preview_issues.append(
            (
                field,
                f"页面超出 {(required_bottom - slide_height) / _EMU_PER_POINT:.1f}pt。"
                + diagnostic,
            )
        )
    return preview_issues


def _item_values(item: Mapping[str, object]) -> dict[str, str]:
    product, prices, manual = (_mapping(item.get(k)) for k in ("product", "prices", "manual"))
    return {
        "product_name": _text(product, "product_name"),
        "selling_points": _text(product, "selling_points"),
        "market_price": _price_with_yuan(_format_price(prices.get("market_price"))),
        "jd_customer_price": _price_with_yuan(_format_price(prices.get("agreement_price"))),
        "discount_rate": _format_discount(prices.get("discount_rate")),
        "sku": _text(product, "sku"),
        "fulfillment_cycle": _text(manual, "fulfillment_cycle"),
        "shipping_courier": _text(product, "shipping_courier"),
        "warranty_period": _text(product, "warranty_period"),
    }


def _image_bytes(item: Mapping[str, object], images: Mapping[str, bytes]) -> list[bytes | None]:
    product = _mapping(item.get("product"))
    # Only main product media is available in the business snapshot today.
    # Renderer-only supplementary IDs are explicitly supplied by fictional QA;
    # no API, database or snapshot field is added and no image is duplicated.
    identifiers = [_text(product, "id")]
    supplementary = item.get("renderer_supplementary_image_ids")
    if isinstance(supplementary, list):
        identifiers.extend(str(value) if value is not None else "" for value in supplementary)
    if len(identifiers) > 4:
        raise AppError("PPT_TEMPLATE_IMAGE_CAPACITY_EXCEEDED", "仅有四个原件图片槽", 422)
    return [images.get(identifier) if identifier else None for identifier in identifiers]


def _fill_image(slide: Any, slot: Any, image_bytes: bytes | None) -> None:
    if image_bytes is None:
        return
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            width, height = image.size
    except (OSError, UnidentifiedImageError) as error:
        raise AppError("PPT_TEMPLATE_IMAGE_INVALID", "商品图片无法读取", 422) from error
    scale = min(slot.width / width, slot.height / height)
    rendered_width, rendered_height = int(width * scale), int(height * scale)
    picture = slide.shapes.add_picture(
        BytesIO(image_bytes),
        slot.left + (slot.width - rendered_width) // 2,
        slot.top + (slot.height - rendered_height) // 2,
        width=rendered_width,
        height=rendered_height,
    )
    picture.name = slot.name
    parent = slot._element.getparent()
    parent.remove(picture._element)
    parent.replace(slot._element, picture._element)


def render_jd_festive_red_v5(
    source: Mapping[str, object],
    *,
    images: Mapping[str, bytes],
    template: PptTemplateDefinition,
    manifest: PptxSlotManifest,
    layout_preview: bool = False,
) -> bytes:
    if (template.code, template.version) != ("JD_FESTIVE_RED", "5"):
        raise _error("渲染入口必须明确为 JD_FESTIVE_RED + 5")
    deck = _load(resolve_ppt_template_asset(template))
    _validate_runtime_structure(deck, manifest)
    if _mappings(source.get("packages")):
        raise AppError(
            "PPT_TEMPLATE_COMBINATION_UNSUPPORTED",
            "模板2组合价格/属性展示合同待确认，不能混用逐件协议价与组合总价",
            422,
        )
    prototype = deck.slides[1]
    preview_issues: list[LayoutPreviewIssue] = []
    for product_number, item in enumerate(_mappings(source.get("single_products")), start=1):
        values = _item_values(item)
        product_identifier = _text(_mapping(item.get("product")), "id")
        slide = _clone_slide(deck, prototype)
        selling = _selling_point_items(values["selling_points"])
        token_values = {"product_name": values["product_name"]}
        token_values.update(
            {
                "selling_point_" + str(i + 1): selling[i] if i < len(selling) else ""
                for i in range(4)
            }
        )
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        for field, value in token_values.items():
                            if run.text == "{{" + field + "}}":
                                run.text = value
        slots = {s.name: s for s in slide.shapes}
        _fill_reference_values(slots["SCM_FIELD_REFERENCE"], values)
        _remove_value_layers(slide)
        slots = {s.name: s for s in slide.shapes}
        _append_selling_points(slots["SCM_FIELD_SELLING_POINTS"], selling)
        overflows = _layout_dynamic_text(
            slots,
            values,
            product_identifier,
            deck.slide_height,
            allow_overflow=layout_preview,
        )
        if overflows:
            for field, _summary in overflows:
                logger.warning(
                    "PPT v5 layout preview bypassed capacity: template=%s product=%s field=%s",
                    template.code,
                    product_identifier or "unknown",
                    field,
                )
            preview_issues.append(
                LayoutPreviewIssue(
                    product_number=product_number,
                    product_name=values["product_name"],
                    summary="；".join(summary for _field, summary in overflows),
                    values={key: value for key, value in values.items() if value},
                )
            )
        image_list = _image_bytes(item, images)
        for index, name in enumerate(_IMAGE_SLOT_GEOMETRY):
            _fill_image(slide, slots[name], image_list[index] if index < len(image_list) else None)
    if layout_preview and preview_issues:
        add_layout_preview_pages(deck, template.code, preview_issues)
    _remove_slide(deck, prototype)
    # Candidate integrity signature describes the runtime prototype, not output.
    deck.core_properties.keywords = ""
    output = BytesIO()
    deck.save(output)
    return output.getvalue()
