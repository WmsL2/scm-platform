"""High-fidelity, versioned business-template rendering.

This module intentionally handles only an audited v4 contract.  It replaces text
inside named runs and image relationship targets in place; it never redraws a
business template's static design.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from io import BytesIO
from typing import Any

from PIL import Image, UnidentifiedImageError
from pptx import Presentation

from app.common.contracts import AppError
from app.modules.recommendation.application.ppt_template_manifest import PptxSlotManifest
from app.modules.recommendation.application.ppt_template_registry import resolve_ppt_template_asset

_TRANSPARENT_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc````"
    b"\x00\x00\x00\x05\x00\x01\xa5\xf6E@\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _text(values: Mapping[str, object], name: str) -> str:
    value = values.get(name)
    return str(value).strip() if value is not None and str(value).strip() else ""


def _money(value: object) -> str:
    text = str(value or "").strip()
    return f"¥ {text}" if text else ""


def _plain_amount(value: object) -> str:
    """Return a value for a template that owns its currency unit in a static run."""
    return str(value or "").strip()


def _fields(item: Mapping[str, object]) -> dict[str, str]:
    product, manual, prices = (_mapping(item.get(key)) for key in ("product", "manual", "prices"))
    title = _text(product, "product_name")
    brand_model = " / ".join(
        value for value in (_text(product, "brand"), _text(product, "model")) if value
    )
    price_lines = [
        ("市场参考价", _money(prices.get("market_price"))),
        ("京东价格", _money(prices.get("jd_price"))),
        ("协议价格", _money(prices.get("agreement_price"))),
        ("活动价格", _money(manual.get("campaign_price"))),
    ]
    specification = _text(product, "product_specification")
    packaging = _text(product, "packaging_list")
    selling_points = _text(product, "selling_points")
    delivery = _text(manual, "delivery_status") or _text(product, "shipping_courier")
    warranty = _text(product, "warranty_period")
    evidence = _text(manual, "evidence")
    market_price = _money(prices.get("market_price"))
    jd_price = _money(prices.get("jd_price"))
    agreement_price = _money(prices.get("agreement_price"))
    campaign_price = _money(manual.get("campaign_price"))
    jd_customer_price = _money(manual.get("jd_customer_price"))
    return {
        "title": title,
        "brand_model": brand_model,
        "product_specification": specification,
        "packaging_list": packaging,
        "selling_points": selling_points,
        "delivery": delivery,
        "warranty": warranty,
        "evidence": evidence,
        "market_price": market_price,
        "jd_price": jd_price,
        "jd_customer_price": jd_customer_price,
        # These slots retain the original festive price typography and units.
        # There is currently no confirmed `manual.jd_customer_price` input in
        # the persisted task contract, so this intentionally stays empty rather
        # than falling back to a differently-scoped ordinary JD price.
        "market_reference_value": _plain_amount(prices.get("market_price")),
        "jd_customer_price_value": _plain_amount(manual.get("jd_customer_price")),
        "agreement_price_value": _plain_amount(prices.get("agreement_price")),
        "discount_rate": _plain_amount(manual.get("discount_rate")),
        "agreement_price": agreement_price,
        "campaign_price": campaign_price,
        "offer_label": "活动价格：" if campaign_price else "",
        "sku": _text(product, "sku"),
        "fulfillment": _text(manual, "fulfillment_cycle"),
        "specification": specification,
        "packaging": packaging,
        "service": warranty,
        "reference": evidence,
        "prices": "\n".join(f"{label}：{value}" for label, value in price_lines if value),
        "image_notice": "",
        "category": _text(product, "third_category") or _text(product, "category"),
        "catalog_content": "\n".join(
            value
            for value in (title, specification, selling_points, _text(manual, "evidence"))
            if value
        ),
        "union_body": "\n".join(
            value
            for value in (
                f"SKU：{_text(product, 'sku')}" if _text(product, "sku") else "",
                f"商品配置：{specification}" if specification else "",
                f"市场参考价：{market_price}" if market_price else "",
                f"协议价：{agreement_price}" if agreement_price else "",
                f"发货物流：{delivery}" if delivery else "",
            )
            if value
        ),
    }


def _replace_tokenized_runs(shape: Any, values: Mapping[str, str]) -> None:
    """Replace only token-bearing runs, retaining pPr/rPr and static labels."""
    if not getattr(shape, "has_text_frame", False):
        return
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            for token in list(_tokens(run.text)):
                value = _token_value(token, values)
                run.text = run.text.replace("{{" + token + "}}", value)


def _tokens(value: str) -> list[str]:
    import re

    return re.findall(r"\{\{([^{}]+)\}\}", value)


def _token_value(token: str, values: Mapping[str, str]) -> str:
    name, separator, index = token.partition(":")
    value = values.get(name, "")
    if not separator:
        return value
    lines = [line.strip() for line in value.replace("；", "\n").splitlines() if line.strip()]
    return lines[int(index)] if index.isdigit() and int(index) < len(lines) else ""


def _remove_empty_dynamic_paragraphs(shape: Any, values: Mapping[str, str]) -> None:
    """Remove a whole optional information row when all of its values are absent."""
    if not getattr(shape, "has_text_frame", False):
        return
    for paragraph in list(shape.text_frame.paragraphs):
        tokens = _tokens(paragraph.text)
        if tokens and all(not _token_value(token, values) for token in tokens):
            paragraph._element.getparent().remove(paragraph._element)


def _clone_slide(presentation: Any, source: Any) -> Any:
    destination = presentation.slides.add_slide(source.slide_layout)
    rels: dict[str, str] = {}
    for relationship in source.part.rels.values():
        if "notesSlide" in relationship.reltype:
            continue
        target = relationship.target_ref if relationship.is_external else relationship.target_part
        rels[relationship.rId] = destination.part.relate_to(
            target, relationship.reltype, is_external=relationship.is_external
        )
    # A blank layout can inject placeholders.  Replacing the content tree makes
    # cloned pages have exactly the reference shape order and geometry.
    source_c_sld = deepcopy(source._element.cSld)
    old_c_sld = destination._element.cSld
    old_c_sld.getparent().replace(old_c_sld, source_c_sld)
    for node in destination._element.cSld.iter():
        for key, value in list(node.attrib.items()):
            if value in rels:
                node.set(key, rels[value])
    destination.__dict__.pop("shapes", None)
    return destination


def _is_image(content: bytes) -> bool:
    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def _replace_picture(shape: Any, content: bytes | None) -> None:
    """Swap the existing image relationship, preserving shape/z-order/crop."""
    if content is None:
        # A transparent pixel removes old product media without adding any text.
        content = _TRANSPARENT_PNG
    _image_part, rel_id = shape.part.get_or_add_image_part(BytesIO(content))
    blip = next(node for node in shape._element.iter() if node.tag.endswith("}blip"))
    blip.set("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed", rel_id)


def _remove_slide(presentation: Any, slide: Any) -> None:
    index = list(presentation.slides).index(slide)
    slide_id = presentation.slides._sldIdLst[index]
    presentation.part.drop_rel(slide_id.rId)
    del presentation.slides._sldIdLst[index]


def render_v4(
    source: Mapping[str, object],
    *,
    images: Mapping[str, bytes],
    template: Any,
    manifest: PptxSlotManifest,
) -> bytes:
    presentation = Presentation(str(resolve_ppt_template_asset(template)))
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
        project = _mapping(source.get("project"))
        for shape in cover.shapes:
            project_name = _text(project, "project_name")
            _replace_tokenized_runs(
                shape,
                {"project_name": project_name, "project_title": project_name},
            )
    items = source.get("single_products")
    for item in items if isinstance(items, list) else []:
        product_item = _mapping(item)
        values = _fields(product_item)
        if template.code == "JD_FESTIVE_RED":
            selling_point_lines = [
                line
                for line in values["selling_points"].replace("；", "\n").splitlines()
                if line.strip()
            ]
            if len(selling_point_lines) > 3:
                raise AppError(
                    "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED",
                    "节庆模板卖点区域无法容纳全部商品卖点",
                    409,
                )
        slide = _clone_slide(presentation, prototype)
        shapes = {shape.name: shape for shape in slide.shapes}
        required = set(manifest.source_text_slots)
        if not required.issubset(shapes):
            raise AppError("PPT_TEMPLATE_SLOT_MISMATCH", "PPT 模板槽位不匹配", 409)
        for shape in shapes.values():
            _remove_empty_dynamic_paragraphs(shape, values)
            _replace_tokenized_runs(shape, values)
        product = _mapping(product_item.get("product"))
        product_id = _text(product, "id")
        image = images.get(product_id)
        image = image if image is not None and _is_image(image) else None
        image_slots = sorted(
            (shape for name, shape in shapes.items() if name.startswith("SCM_SLOT_IMAGE_")),
            key=lambda shape: shape.name,
        )
        if not image_slots:
            raise AppError("PPT_TEMPLATE_SLOT_MISMATCH", "PPT 模板图片槽位不匹配", 409)
        for index, shape in enumerate(image_slots):
            _replace_picture(shape, image if index == 0 else None)
    _remove_slide(presentation, prototype)
    output = BytesIO()
    presentation.save(output)
    return output.getvalue()
