"""Private formal-template v5 standardisation and token-safe rendering.

Only named dynamic slots are mutated at runtime.  The source deck is copied
into a private runtime asset by the companion script; customer originals never
enter the repository or public asset directory.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
from json import dumps
from math import ceil, floor
from pathlib import Path
from re import sub
from typing import Any
from xml.etree import ElementTree
from zipfile import ZipFile

from PIL import Image, UnidentifiedImageError
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE
from pptx.util import Inches, Pt

from app.common.contracts import AppError
from app.modules.recommendation.application.ppt_template_manifest import (
    PptxSlotManifest,
    get_pptx_manifest,
)
from app.modules.recommendation.application.ppt_template_registry import (
    PptTemplateDefinition,
    resolve_ppt_template_asset,
)

_TRANSPARENT_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````"
    b"\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82"
)
_JD_FONT = "京东朗正体 玲珑"
_YAHEI = "Microsoft YaHei"
_SELLING_POINT_PREFIX = r"^\s*\d+\s*[、.．)]\s*"
_EMU_PER_POINT = 12_700
_SELLING_POINT_FONT_SIZE_PT = 12.0
_SELLING_POINT_LINE_HEIGHT_FACTOR = 1.2
_SOURCE_SHAPE_TYPES = (
    (14,),
    (1, 1, 1, 1, 1, 9, 1, 1, 17, 1, 1, 1, 1, 1, 1),
    (1, 1, 1, 1, 1, 9, 1, 1, 17, 1, 1, 13, 13, 13, 13),
)
_SOURCE_STRUCTURE_FINGERPRINT = "177ee094d672fbb4311062b5e809c53cf487b90177c4b25f5afbac73940fe011"
_REQUIRED_TEXT_SLOT_NAMES = frozenset(
    {
        "SCM_FIELD_SPECIFICATION",
        "SCM_FIELD_PACKAGING",
        "SCM_FIELD_SELLING_POINTS",
        "SCM_FIELD_DELIVERY",
        "SCM_FIELD_TITLE",
        "SCM_FIELD_BRAND",
        "SCM_FIELD_REFERENCE",
        "SCM_FIELD_PRICES",
    }
)
_REQUIRED_IMAGE_SLOT_NAMES = frozenset(
    {
        "SCM_SLOT_IMAGE_MAIN",
        "SCM_SLOT_IMAGE_SUPPLEMENT_01",
        "SCM_SLOT_IMAGE_SUPPLEMENT_02",
        "SCM_SLOT_IMAGE_SUPPLEMENT_03",
    }
)
_RUNTIME_GEOMETRY_TOLERANCE = Inches(0.01)
_RUNTIME_TEXT_SLOT_GEOMETRY: dict[str, tuple[float, float, float, float]] = {
    "SCM_FIELD_SPECIFICATION": (6.379, 3.290, 6.299, 0.503),
    "SCM_FIELD_PACKAGING": (6.379, 3.757, 6.299, 0.503),
    "SCM_FIELD_SELLING_POINTS": (6.389, 4.995, 6.299, 1.715),
    "SCM_FIELD_DELIVERY": (6.389, 4.236, 6.299, 0.301),
    "SCM_FIELD_TITLE": (6.465, 0.854, 6.268, 0.335),
    "SCM_FIELD_BRAND": (6.379, 2.615, 6.299, 0.301),
    "SCM_FIELD_REFERENCE": (6.360, 1.186, 3.457, 1.688),
    "SCM_FIELD_PRICES": (9.757, 1.165, 3.322, 1.816),
}
_RUNTIME_TEXT_SLOT_TOKENS: dict[str, tuple[str, ...]] = {
    "SCM_FIELD_SPECIFICATION": ("{{specification}}",),
    "SCM_FIELD_PACKAGING": ("{{packaging_list}}",),
    "SCM_FIELD_DELIVERY": ("{{shipping_courier}}",),
    "SCM_FIELD_TITLE": ("{{product_name}}",),
    "SCM_FIELD_BRAND": ("{{brand}}",),
    "SCM_FIELD_REFERENCE": (
        "{{market_price}}",
        "{{sku}}",
        "{{fulfillment_cycle}}",
    ),
    "SCM_FIELD_PRICES": (
        "{{jd_customer_price}}",
        "{{discount_rate}}",
        "{{minimum_order_quantity}}",
    ),
}
_DYNAMIC_FIELD_SLOTS: dict[str, tuple[str, str]] = {
    "product_name": ("SCM_FIELD_TITLE", "{{product_name}}"),
    "specification": ("SCM_FIELD_SPECIFICATION", "{{specification}}"),
    "packaging_list": ("SCM_FIELD_PACKAGING", "{{packaging_list}}"),
    "shipping_courier": ("SCM_FIELD_DELIVERY", "{{shipping_courier}}"),
    "brand": ("SCM_FIELD_BRAND", "{{brand}}"),
    "market_price": ("SCM_FIELD_REFERENCE", "{{market_price}}"),
    "sku": ("SCM_FIELD_REFERENCE", "{{sku}}"),
    "fulfillment_cycle": ("SCM_FIELD_REFERENCE", "{{fulfillment_cycle}}"),
    "jd_customer_price": ("SCM_FIELD_PRICES", "{{jd_customer_price}}"),
    "discount_rate": ("SCM_FIELD_PRICES", "{{discount_rate}}"),
    "minimum_order_quantity": ("SCM_FIELD_PRICES", "{{minimum_order_quantity}}"),
}


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mappings(value: object) -> list[Mapping[str, object]]:
    return [_mapping(item) for item in value] if isinstance(value, list) else []


def _text(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    return str(value).strip() if value is not None and str(value).strip() else ""


def _asset_structure_error(message: str) -> AppError:
    return AppError("PPT_TEMPLATE_ASSET_STRUCTURE_INVALID", message, 409)


def _rgb(red: int, green: int, blue: int) -> RGBColor:
    return RGBColor(red, green, blue)  # type: ignore[no-untyped-call]


def _v5_manifest() -> PptxSlotManifest:
    manifest = get_pptx_manifest("JD_DETAIL_RED", "5")
    if manifest is None:
        raise _asset_structure_error("JD_DETAIL_RED v5 槽位合同不可用")
    return manifest


def _remove_slide(presentation: Any, slide: Any) -> None:
    index = list(presentation.slides).index(slide)
    slide_id = presentation.slides._sldIdLst[index]
    presentation.part.drop_rel(slide_id.rId)
    del presentation.slides._sldIdLst[index]


def _remove_notes_relationship(slide: Any) -> None:
    for relationship in list(slide.part.rels.values()):
        if "notesSlide" in relationship.reltype:
            slide.part.drop_rel(relationship.rId)


def _set_paragraph(
    paragraph: Any,
    label: str,
    token: str,
    *,
    font: str,
    size: int,
    color: RGBColor,
    value_color: RGBColor | None = None,
    line_spacing: float = 1.5,
    bold: bool = False,
) -> None:
    paragraph.clear()
    paragraph.line_spacing = line_spacing
    label_run = paragraph.add_run()
    label_run.text = label
    value_run = paragraph.add_run()
    value_run.text = token
    for run in (label_run, value_run):
        run.font.name = font
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.bold = bold
    if value_color is not None:
        value_run.font.color.rgb = value_color


def _set_single_token(
    shape: Any, token: str, *, font: str, size: int, color: RGBColor, bold: bool = False
) -> None:
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    paragraph = frame.paragraphs[0]
    paragraph.line_spacing = 1.0
    run = paragraph.add_run()
    run.text = token
    run.font.name = font
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold


def _selling_point_items(value: str) -> list[str]:
    """Return at most the six customer-approved non-empty selling-point rows."""
    return [
        sub(_SELLING_POINT_PREFIX, "", item.strip())
        for item in value.splitlines()
        if item.strip()
    ]


def _fill_selling_points(shape: Any, value: str) -> None:
    """Render the page-3 numbered selling-point format without blank rows."""
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    _set_paragraph(
        frame.paragraphs[0],
        "产品卖点（介绍详细）",
        "",
        font=_YAHEI,
        size=12,
        color=_rgb(0, 0, 0),
        line_spacing=1.0,
    )
    for index, item in enumerate(_selling_point_items(value), start=1):
        paragraph = frame.add_paragraph()
        paragraph.line_spacing = 1.0
        number = paragraph.add_run()
        number.text = f"{index}、"
        content = paragraph.add_run()
        content.text = item
        for run in (number, content):
            run.font.name = _YAHEI
            run.font.size = Pt(12)
            run.font.color.rgb = _rgb(0, 0, 0)


def _replace_as_picture(slide: Any, shape: Any, name: str) -> None:
    picture = slide.shapes.add_picture(
        BytesIO(_TRANSPARENT_PNG), shape.left, shape.top, shape.width, shape.height
    )
    picture.name = name
    shape._element.getparent().remove(shape._element)


def _structure_fingerprint(presentation: Any) -> str:
    payload = {
        "slides": len(presentation.slides),
        "shapes": [
            [
                (int(shape.shape_type), shape.left, shape.top, shape.width, shape.height)
                for shape in slide.shapes
            ]
            for slide in presentation.slides
        ],
    }
    return sha256(dumps(payload, separators=(",", ":")).encode("utf-8")).hexdigest()


def _validate_source_structure(presentation: Any, expected_fingerprint: str | None) -> None:
    shape_types = tuple(
        tuple(int(shape.shape_type) for shape in slide.shapes) for slide in presentation.slides
    )
    if expected_fingerprint == _SOURCE_STRUCTURE_FINGERPRINT and shape_types != _SOURCE_SHAPE_TYPES:
        raise _asset_structure_error("JD_DETAIL_RED v5 原始模板页数、形状数量或形状类型不匹配")
    if (
        expected_fingerprint is not None
        and _structure_fingerprint(presentation) != expected_fingerprint
    ):
        raise _asset_structure_error("JD_DETAIL_RED v5 原始模板结构指纹不匹配")


def _validate_runtime_structure(presentation: Any, manifest: PptxSlotManifest) -> None:
    if len(presentation.slides) != 2:
        raise _asset_structure_error("JD_DETAIL_RED v5 运行模板必须只包含封面和商品页")
    if manifest.cover_slide_index != 0 or manifest.product_slide_index != 1:
        raise _asset_structure_error("JD_DETAIL_RED v5 运行模板槽位索引不匹配")
    product = presentation.slides[manifest.product_slide_index]
    if len(product.shapes) != 15:
        raise _asset_structure_error("JD_DETAIL_RED v5 商品页形状数量不匹配")
    slots: dict[str, list[Any]] = {}
    for shape in product.shapes:
        slots.setdefault(shape.name, []).append(shape)
    required_slots = _REQUIRED_TEXT_SLOT_NAMES | _REQUIRED_IMAGE_SLOT_NAMES
    missing = sorted(name for name in required_slots if name not in slots)
    duplicates = sorted(name for name in required_slots if len(slots.get(name, [])) != 1)
    if missing or duplicates:
        raise _asset_structure_error("JD_DETAIL_RED v5 运行模板缺少或重复动态槽位")
    if any(not slots[name][0].has_text_frame for name in _REQUIRED_TEXT_SLOT_NAMES):
        raise _asset_structure_error("JD_DETAIL_RED v5 文本槽位类型不匹配")
    if any(
        slots[name][0].shape_type != MSO_SHAPE_TYPE.PICTURE for name in _REQUIRED_IMAGE_SLOT_NAMES
    ):
        raise _asset_structure_error("JD_DETAIL_RED v5 图片槽位类型不匹配")
    _validate_runtime_text_slot_contract(slots)


def _validate_runtime_text_slot_contract(slots: Mapping[str, list[Any]]) -> None:
    """Verify the standardized coordinates and the one-to-one token contract."""
    for name, expected_geometry in _RUNTIME_TEXT_SLOT_GEOMETRY.items():
        shape = slots[name][0]
        actual_geometry = (shape.left, shape.top, shape.width, shape.height)
        if any(
            abs(actual - Inches(expected)) > _RUNTIME_GEOMETRY_TOLERANCE
            for actual, expected in zip(actual_geometry, expected_geometry, strict=True)
        ):
            raise _asset_structure_error("JD_DETAIL_RED v5 文本槽位几何合同不匹配")
        frame = shape.text_frame
        if shape.width <= frame.margin_left + frame.margin_right or shape.height <= (
            frame.margin_top + frame.margin_bottom
        ):
            raise _asset_structure_error("JD_DETAIL_RED v5 文本槽位可用区域无效")
    for name, tokens in _RUNTIME_TEXT_SLOT_TOKENS.items():
        shape = slots[name][0]
        for token in tokens:
            matches = [
                run
                for paragraph in shape.text_frame.paragraphs
                for run in paragraph.runs
                if run.text == token
            ]
            if len(matches) != 1:
                raise _asset_structure_error("JD_DETAIL_RED v5 文本槽位 Token 合同不匹配")
    selling = slots["SCM_FIELD_SELLING_POINTS"][0]
    if selling.text.strip() != "产品卖点（介绍详细）":
        raise _asset_structure_error("JD_DETAIL_RED v5 卖点槽位固定标题不匹配")


def validate_jd_detail_red_v5_runtime(path: Path, manifest: PptxSlotManifest) -> None:
    try:
        presentation = Presentation(str(path))
    except (OSError, ValueError) as error:
        raise _asset_structure_error("JD_DETAIL_RED v5 运行模板无法读取") from error
    _validate_runtime_structure(presentation, manifest)


def standardize_jd_detail_red_v5(
    source: Path,
    destination: Path,
    *,
    expected_source_fingerprint: str | None = _SOURCE_STRUCTURE_FINGERPRINT,
) -> None:
    """Build the two-page private v5 asset from the authorised formal original."""
    presentation = Presentation(str(source))
    _validate_source_structure(presentation, expected_source_fingerprint)
    product = presentation.slides[1]
    # The third slide carries human sample content. Remove it before saving so its
    # sample media relationships are never brought forward by cloning.
    _remove_slide(presentation, presentation.slides[2])
    _remove_notes_relationship(presentation.slides[0])
    _remove_notes_relationship(product)
    shapes = list(product.shapes)
    fields = {
        "SCM_FIELD_SPECIFICATION": shapes[0],
        "SCM_FIELD_PACKAGING": shapes[1],
        "SCM_FIELD_SELLING_POINTS": shapes[2],
        "SCM_FIELD_DELIVERY": shapes[3],
        "SCM_FIELD_TITLE": shapes[4],
        "SCM_FIELD_BRAND": shapes[6],
        "SCM_FIELD_REFERENCE": shapes[7],
        "SCM_FIELD_PRICES": shapes[8],
    }
    for name, shape in fields.items():
        shape.name = name
    _set_paragraph(
        fields["SCM_FIELD_SPECIFICATION"].text_frame.paragraphs[0],
        "商品规格：",
        "{{specification}}",
        font=_YAHEI,
        size=12,
        color=_rgb(0, 0, 0),
        line_spacing=1.0,
    )
    _set_paragraph(
        fields["SCM_FIELD_PACKAGING"].text_frame.paragraphs[0],
        "包装清单：",
        "{{packaging_list}}",
        font=_YAHEI,
        size=12,
        color=_rgb(0, 0, 0),
        line_spacing=1.0,
    )
    selling = fields["SCM_FIELD_SELLING_POINTS"].text_frame
    selling.clear()
    selling.word_wrap = True
    selling.auto_size = MSO_AUTO_SIZE.NONE
    _fill_selling_points(fields["SCM_FIELD_SELLING_POINTS"], "")
    _set_paragraph(
        fields["SCM_FIELD_DELIVERY"].text_frame.paragraphs[0],
        "发货物流：",
        "{{shipping_courier}}",
        font=_YAHEI,
        size=12,
        color=_rgb(0, 0, 0),
        line_spacing=1.0,
    )
    _set_single_token(
        fields["SCM_FIELD_TITLE"],
        "{{product_name}}",
        font=_JD_FONT,
        size=14,
        color=_rgb(255, 255, 255),
        bold=True,
    )
    _set_paragraph(
        fields["SCM_FIELD_BRAND"].text_frame.paragraphs[0],
        "商品品牌：",
        "{{brand}}",
        font=_YAHEI,
        size=12,
        color=_rgb(0, 0, 0),
    )
    # The instruction page uses a broader brand field, but the customer sample
    # page fixes this row directly above the separator line.  Use that approved
    # geometry so a real brand value can never cross the 3.082-inch separator.
    brand = fields["SCM_FIELD_BRAND"]
    brand.left = Inches(6.379)
    brand.top = Inches(2.615)
    brand.width = Inches(6.299)
    brand.height = Inches(0.301)
    reference = fields["SCM_FIELD_REFERENCE"].text_frame
    reference.clear()
    reference.word_wrap = True
    reference.auto_size = MSO_AUTO_SIZE.NONE
    for index, (label, token) in enumerate(
        (
            ("市场参考价：", "{{market_price}}"),
            ("SKU：", "{{sku}}"),
            ("备货时间：", "{{fulfillment_cycle}}"),
        )
    ):
        paragraph = reference.paragraphs[0] if index == 0 else reference.add_paragraph()
        _set_paragraph(paragraph, label, token, font=_JD_FONT, size=14, color=_rgb(0, 0, 0))
    prices = fields["SCM_FIELD_PRICES"].text_frame
    prices.clear()
    prices.word_wrap = True
    prices.auto_size = MSO_AUTO_SIZE.NONE
    price_specs = (
        # Only the token run is red.  The customer-owned fixed label remains
        # black whether the dynamic amount is present or intentionally blank.
        (
            "京东大客户价：",
            "{{jd_customer_price}}",
            _rgb(0, 0, 0),
            _rgb(255, 0, 0),
        ),
        ("折扣率：", "{{discount_rate}}", _rgb(0, 0, 0), None),
        ("起订量：", "{{minimum_order_quantity}}", _rgb(0, 0, 0), None),
    )
    for index, (label, token, color, value_color) in enumerate(price_specs):
        paragraph = prices.paragraphs[0] if index == 0 else prices.add_paragraph()
        _set_paragraph(
            paragraph,
            label,
            token,
            font=_JD_FONT,
            size=14,
            color=color,
            value_color=value_color,
        )
    image_slots = (
        (shapes[11], "SCM_SLOT_IMAGE_MAIN", None),
        # The instruction page has temporary wide placeholders.  Restore the
        # three portrait slots from page 3 in left-to-right order (1, 2, 3).
        (shapes[12], "SCM_SLOT_IMAGE_SUPPLEMENT_01", (0.448, 5.404, 1.367, 1.969)),
        (shapes[14], "SCM_SLOT_IMAGE_SUPPLEMENT_02", (2.258, 5.404, 1.354, 1.969)),
        (shapes[13], "SCM_SLOT_IMAGE_SUPPLEMENT_03", (4.069, 5.329, 1.313, 1.969)),
    )
    for shape, name, geometry in image_slots:
        if geometry is not None:
            shape.left, shape.top, shape.width, shape.height = (Inches(value) for value in geometry)
        _replace_as_picture(product, shape, name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    presentation.save(str(destination))
    _validate_runtime_structure(Presentation(str(destination)), _v5_manifest())


def verify_no_sample_media(source: Path, runtime: Path) -> None:
    """Ensure no sample-slide media binary is retained in the generated runtime deck."""
    with ZipFile(source) as archive:
        relationships = ElementTree.fromstring(archive.read("ppt/slides/_rels/slide3.xml.rels"))
        targets = [
            relationship.attrib.get("Target", "").replace("../", "ppt/")
            for relationship in relationships
        ]
        sample_hashes = {
            sha256(archive.read(target)).hexdigest()
            for target in targets
            if target.startswith("ppt/media/")
        }
    with ZipFile(runtime) as archive:
        names = set(archive.namelist())
        if "ppt/slides/slide3.xml" in names or "ppt/slides/_rels/slide3.xml.rels" in names:
            raise ValueError("sample slide remains in runtime asset")
        runtime_hashes = {
            sha256(archive.read(name)).hexdigest()
            for name in names
            if name.startswith("ppt/media/")
        }
    if sample_hashes & runtime_hashes:
        raise ValueError("sample slide media remains in runtime asset")


def _clone_slide(presentation: Any, source: Any) -> Any:
    destination = presentation.slides.add_slide(source.slide_layout)
    # add_slide() materialises the layout's 11 placeholders.  The product page
    # is copied in full below, so retaining those extra instances produces
    # invisible but real duplicate layout objects in every generated page.
    for shape in list(destination.shapes):
        shape._element.getparent().remove(shape._element)
    relation_map: dict[str, str] = {}
    for relationship in source.part.rels.values():
        if "notesSlide" in relationship.reltype:
            continue
        target = relationship.target_ref if relationship.is_external else relationship.target_part
        relation_map[relationship.rId] = destination.part.relate_to(
            target, relationship.reltype, is_external=relationship.is_external
        )
    for shape in source.shapes:
        element = deepcopy(shape.element)
        for node in element.iter():
            for key, value in list(node.attrib.items()):
                if value in relation_map:
                    node.set(key, relation_map[value])
        destination.shapes._spTree.insert_element_before(element, "p:extLst")
    return destination


def _replace_token(shape: Any, token: str, value: str) -> None:
    if not getattr(shape, "has_text_frame", False):
        return
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            if token in run.text:
                run.text = run.text.replace(token, value)


def _format_price(value: object) -> str:
    raw = str(value).strip() if value is not None else ""
    if not raw:
        return ""
    try:
        return f"¥ {Decimal(raw):,.2f}"
    except (InvalidOperation, ValueError):
        return raw


def _format_discount(value: object) -> str:
    raw = str(value).strip() if value is not None else ""
    if not raw:
        return ""
    try:
        rate = Decimal(raw)
        if Decimal(0) <= rate <= Decimal(1):
            display = format(rate * 100, "f")
            if "." in display:
                display = display.rstrip("0").rstrip(".")
            return f"{display}%"
        return raw
    except (InvalidOperation, ValueError):
        return raw


def _estimated_text_width_pt(value: str, font_size_pt: float) -> float:
    """Conservatively estimate width using the template's CJK/Latin font size.

    Runtime hosts do not expose the Office text-layout engine.  Full-width CJK
    characters and broad Latin glyphs therefore consume one em; narrow Latin
    glyphs consume a smaller, still conservative share.  The result deliberately
    rejects values before Office could wrap them into a neighbouring fixed row.
    """
    units = 0.0
    for character in value:
        if character.isspace():
            units += 0.35
        elif ord(character) >= 0x2E80 or character in "MW@#%&":
            units += 1.0
        elif character in "ilI.,:;!|'`":
            units += 0.4
        else:
            units += 0.75
    return units * font_size_pt


def _paragraph_line_count(paragraph: Any, token: str, value: str, width_pt: float) -> int:
    token_run = next((run for run in paragraph.runs if run.text == token), None)
    if token_run is None or token_run.font.size is None:
        raise _asset_structure_error("JD_DETAIL_RED v5 动态文本 Token 或字号无效")
    font_size_pt = float(token_run.font.size.pt)
    if font_size_pt <= 0 or width_pt <= 0:
        raise _asset_structure_error("JD_DETAIL_RED v5 动态文本槽位可用宽度无效")
    static_text = paragraph.text.replace(token, "")
    lines = 0
    for line in (static_text + value).splitlines() or [""]:
        lines += max(1, ceil(_estimated_text_width_pt(line, font_size_pt) / width_pt))
    return lines


def _validate_dynamic_text_capacity(shape: Any, token: str, value: str, field: str) -> None:
    frame = shape.text_frame
    paragraphs = [paragraph for paragraph in frame.paragraphs if token in paragraph.text]
    if len(paragraphs) != 1:
        raise _asset_structure_error("JD_DETAIL_RED v5 动态文本 Token 槽位不唯一")
    paragraph = paragraphs[0]
    inner_width_pt = (shape.width - frame.margin_left - frame.margin_right) / _EMU_PER_POINT
    required_lines = _paragraph_line_count(paragraph, token, value, inner_width_pt)
    # Every non-selling field is an approved fixed row.  Its next row, divider,
    # or footer is a safety boundary, so automatic wrapping is never permitted.
    # The height and margins remain checked to catch a malformed runtime asset.
    token_run = next(run for run in paragraph.runs if run.text == token)
    font_size_pt = float(token_run.font.size.pt)
    usable_height_pt = (shape.height - frame.margin_top - frame.margin_bottom) / _EMU_PER_POINT
    if usable_height_pt < font_size_pt:
        raise _asset_structure_error("JD_DETAIL_RED v5 动态文本槽位可用高度无效")
    line_spacing = paragraph.line_spacing
    if not isinstance(line_spacing, (int, float)) or line_spacing <= 0:
        raise _asset_structure_error("JD_DETAIL_RED v5 动态文本槽位行距无效")
    line_advance_pt = max(font_size_pt, font_size_pt * float(line_spacing))
    lines_by_height = 1 + floor((usable_height_pt - font_size_pt) / line_advance_pt)
    allowed_lines = min(lines_by_height, 1)
    if required_lines > allowed_lines:
        raise AppError(
            "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED",
            f"{field} 自动换行后超出 JD_DETAIL_RED v5 固定文本槽安全容量",
            422,
        )


def _validate_fixed_text_capacities(prototype: Any, values: Mapping[str, str]) -> None:
    shapes = {shape.name: shape for shape in prototype.shapes}
    for field, (slot_name, token) in _DYNAMIC_FIELD_SLOTS.items():
        _validate_dynamic_text_capacity(shapes[slot_name], token, values[field], field)


def _selling_point_line_count(shape: Any, value: str) -> tuple[int, int]:
    """Calculate conservative wrapped lines from the actual text-box geometry."""
    frame = shape.text_frame
    inner_width_pt = (shape.width - frame.margin_left - frame.margin_right) / _EMU_PER_POINT
    usable_height_pt = (shape.height - frame.margin_top - frame.margin_bottom) / _EMU_PER_POINT
    characters_per_line = floor(inner_width_pt / _SELLING_POINT_FONT_SIZE_PT)
    line_height_pt = _SELLING_POINT_FONT_SIZE_PT * _SELLING_POINT_LINE_HEIGHT_FACTOR
    maximum_lines = floor(usable_height_pt / line_height_pt)
    if characters_per_line < 1 or maximum_lines < 1:
        raise _asset_structure_error("JD_DETAIL_RED v5 卖点文本框可用空间无效")
    title_lines = ceil(len("产品卖点（介绍详细）") / characters_per_line)
    item_lines = sum(
        ceil((len(f"{index}、") + len(item)) / characters_per_line)
        for index, item in enumerate(_selling_point_items(value), start=1)
    )
    return title_lines + item_lines, maximum_lines


def _validate_selling_point_capacity(shape: Any, value: str) -> None:
    if len(_selling_point_items(value)) > 6:
        raise AppError(
            "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED",
            "selling_points 超出 JD_DETAIL_RED v5 已确认安全容量",
            422,
        )
    required_lines, maximum_lines = _selling_point_line_count(shape, value)
    if required_lines > maximum_lines:
        raise AppError(
            "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED",
            "selling_points 自动换行后超出 JD_DETAIL_RED v5 卖点文本框安全容量",
            422,
        )


def _replace_picture(shape: Any, image_bytes: bytes | None) -> None:
    if image_bytes is None:
        image_bytes = _TRANSPARENT_PNG
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        image_bytes = _TRANSPARENT_PNG
        width = height = 1
    _image_part, relation_id = shape.part.get_or_add_image_part(BytesIO(image_bytes))
    blip = next(node for node in shape._element.iter() if node.tag.endswith("}blip"))
    blip.set(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed", relation_id
    )
    slot_ratio = shape.width / shape.height
    image_ratio = width / height
    shape.crop_left = shape.crop_right = shape.crop_top = shape.crop_bottom = 0
    if image_ratio > slot_ratio:
        crop = (1 - slot_ratio / image_ratio) / 2
        shape.crop_left = shape.crop_right = crop
    elif image_ratio < slot_ratio:
        crop = (1 - image_ratio / slot_ratio) / 2
        shape.crop_top = shape.crop_bottom = crop


def render_jd_detail_red_v5(
    source: Mapping[str, object],
    *,
    images: Mapping[str, bytes],
    template: PptTemplateDefinition,
    manifest: PptxSlotManifest,
) -> bytes:
    try:
        presentation = Presentation(str(resolve_ppt_template_asset(template)))
    except (OSError, ValueError) as error:
        raise _asset_structure_error("JD_DETAIL_RED v5 运行模板无法读取") from error
    _validate_runtime_structure(presentation, manifest)
    prototype = presentation.slides[manifest.product_slide_index]
    cover = (
        presentation.slides[manifest.cover_slide_index]
        if manifest.cover_slide_index is not None
        else None
    )
    for slide in list(presentation.slides):
        if slide is not prototype and slide is not cover:
            _remove_slide(presentation, slide)
    if cover is not None:
        _remove_notes_relationship(cover)
    _remove_notes_relationship(prototype)
    items = _mappings(source.get("single_products"))
    if _mappings(source.get("packages")):
        raise AppError(
            "PPT_TEMPLATE_COMBINATION_UNSUPPORTED", "JD_DETAIL_RED v5 当前仅支持单品页", 422
        )
    for item in items:
        product, manual, prices = (
            _mapping(item.get(key)) for key in ("product", "manual", "prices")
        )
        values = {
            "product_name": _text(product, "product_name"),
            "specification": _text(product, "product_specification"),
            "packaging_list": _text(product, "packaging_list"),
            "selling_points": _text(product, "selling_points"),
            "shipping_courier": _text(product, "shipping_courier"),
            "brand": _text(product, "brand"),
            "market_price": _format_price(prices.get("market_price")),
            "sku": _text(product, "sku"),
            "fulfillment_cycle": _text(manual, "fulfillment_cycle"),
            "jd_customer_price": "",
            "discount_rate": _format_discount(prices.get("discount_rate")),
            "minimum_order_quantity": "",
        }
        _validate_fixed_text_capacities(prototype, values)
        _validate_selling_point_capacity(
            next(shape for shape in prototype.shapes if shape.name == "SCM_FIELD_SELLING_POINTS"),
            values["selling_points"],
        )
        slide = _clone_slide(presentation, prototype)
        shapes = {shape.name: shape for shape in slide.shapes}
        for key, value in values.items():
            if key == "selling_points":
                continue
            for shape in shapes.values():
                _replace_token(shape, "{{" + key + "}}", value)
        _fill_selling_points(shapes["SCM_FIELD_SELLING_POINTS"], values["selling_points"])
        product_id = _text(product, "id")
        _replace_picture(shapes["SCM_SLOT_IMAGE_MAIN"], images.get(product_id))
        for name in (
            "SCM_SLOT_IMAGE_SUPPLEMENT_01",
            "SCM_SLOT_IMAGE_SUPPLEMENT_02",
            "SCM_SLOT_IMAGE_SUPPLEMENT_03",
        ):
            _replace_picture(shapes[name], None)
    _remove_slide(presentation, prototype)
    output = BytesIO()
    presentation.save(output)
    return output.getvalue()
