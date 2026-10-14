"""Private, explicitly-versioned QA for the approved two-page festive deck."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from json import dumps
from os import environ
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image
from pptx import Presentation

from app.common.contracts import AppError
from app.core.config import get_settings
from app.modules.recommendation.application.ppt_renderer import PptRenderer
from app.modules.recommendation.application.ppt_template_registry import (
    get_ppt_template,
    resolve_ppt_template_asset,
)


def _png(color: tuple[int, int, int], size: tuple[int, int]) -> bytes:
    """Distinct synthetic image fixtures, not real product photography."""
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


def _item(index: int) -> dict[str, object]:
    return {
        "product": {
            "id": f"fictional-{index}",
            "product_name": f"虚构节庆商品{index}",
            "selling_points": "虚构卖点一\n虚构卖点二\n虚构卖点三\n虚构卖点四",
            "sku": f"F{index:03d}",
            "shipping_courier": "京东",
            "warranty_period": "一年",
        },
        "prices": {
            "market_price": "199.50",
            "agreement_price": "169.50",
            "jd_price": "888.00",
            "discount_rate": "0.85",
        },
        "manual": {"fulfillment_cycle": "3天"},
    }


def _slots(slide: object) -> dict[str, object]:
    return {shape.name: shape for shape in slide.shapes}  # type: ignore[attr-defined]


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    original = root / ".codex-assets/official-ppt/originals/模版2.pptx"
    text = original.with_suffix(".txt")
    runtime_root = root / "assets/ppt-templates"
    destination = root / ".codex-assets/official-ppt/samples/v5/jd-festive-red-two-page"
    destination.mkdir(parents=True, exist_ok=True)
    reference = Presentation(str(original))
    cases: dict[str, tuple[dict[str, object], dict[str, bytes]]] = {
        "complete": (
            {"single_products": [_item(1)]},
            {"fictional-1": _png((190, 40, 30), (160, 100))},
        ),
        "empty-fields": (
            {
                "single_products": [
                    {"product": {"id": "fictional-2", "product_name": "虚构空字段商品"}}
                ]
            },
            {},
        ),
        "no-image": ({"single_products": [_item(3)]}, {}),
        "five-single-products": (
            {"single_products": [_item(i) for i in range(5)]},
            {f"fictional-{i}": _png((30 * i, 100, 20), (120, 100)) for i in range(5)},
        ),
        "four-controlled-images": (
            {
                "single_products": [
                    _item(4) | {"renderer_supplementary_image_ids": ["one", "two", "three"]}
                ]
            },
            {
                "fictional-4": _png((200, 20, 20), (300, 80)),
                "one": _png((20, 200, 20), (80, 300)),
                "two": _png((20, 20, 200), (100, 100)),
                "three": _png((200, 200, 20), (140, 100)),
            },
        ),
        "missing-middle-image": (
            {
                "single_products": [
                    _item(6) | {"renderer_supplementary_image_ids": ["one", "missing", "three"]}
                ]
            },
            {"one": _png((20, 200, 20), (80, 300)), "three": _png((200, 200, 20), (140, 100))},
        ),
    }
    boundary = deepcopy(_item(7))
    boundary["product"].update(
        product_name="虚构" + "宽" * 22, sku="WWWWW", selling_points="\n".join(["宽" * 30] * 4)
    )  # type: ignore[attr-defined]
    cases["boundary-safe"] = ({"single_products": [boundary]}, {})
    price_items = [deepcopy(_item(i)) for i in range(4)]
    for item, prices in zip(
        price_items,
        (
            {"market_price": "199.50", "agreement_price": "169.50"},
            {"market_price": "99.00"},
            {"agreement_price": "89.00"},
            {},
        ),
        strict=True,
    ):
        item["prices"] = prices
    cases["price-mapping"] = ({"single_products": price_items}, {})
    price_spacing = deepcopy(_item(10))
    price_spacing["product"].update(  # type: ignore[index]
        sku="SKU-2026-LONG-001",
        shipping_courier="京东物流（次日达）",
    )
    price_spacing["prices"] = {  # type: ignore[index]
        "market_price": "69.00",
        "agreement_price": "50.00",
        "discount_rate": "0.78",
    }
    cases["price-unit-spacing"] = ({"single_products": [price_spacing]}, {})
    six_points = deepcopy(_item(8))
    six_points["product"]["selling_points"] = "\n".join(  # type: ignore[index]
        f"虚构卖点 {index}" for index in range(1, 7)
    )
    cases["six-selling-points"] = ({"single_products": [six_points]}, {})
    evidence: dict[str, object] = {
        "original_path": str(original),
        "original_sha256": sha256(original.read_bytes()).hexdigest(),
        "txt_sha256": sha256(text.read_bytes()).hexdigest(),
        "original_slides": len(reference.slides),
        "template_code": "JD_FESTIVE_RED",
        "template_version": "5",
        "visual_review": (
            "WPS exports available via render script; "
            "final customer acceptance and approved-font QA pending"
        ),
        "image_fixtures": "distinct fictional color panels; real-product-subject visual QA pending",
    }
    outputs: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    # Exercise normal asset resolution, not a patched resolver or v3 fallback.
    with patch.dict(environ, {"PPT_TEMPLATE_ASSET_DIR": str(runtime_root)}):
        get_settings.cache_clear()
        try:
            runtime = resolve_ppt_template_asset(get_ppt_template("JD_FESTIVE_RED", "5"))
            evidence.update(
                runtime_path=str(runtime), runtime_sha256=sha256(runtime.read_bytes()).hexdigest()
            )
            renderer = PptRenderer()
            for name, (source, images) in cases.items():
                data = renderer.render(
                    source,
                    product_images=images,
                    template_code="JD_FESTIVE_RED",
                    template_version="5",
                )
                output = destination / f"JD_FESTIVE_RED-v5-two-page-{name}.pptx"
                output.write_bytes(data)
                deck = Presentation(BytesIO(data))
                assert deck.slides[0]._element.xml == reference.slides[0]._element.xml
                for slide in list(deck.slides)[1:]:
                    slots = _slots(slide)
                    reference_shape = slots["SCM_FIELD_REFERENCE"]
                    assert not any(name.startswith("SCM_VALUE_") for name in slots)
                    assert all(
                        label in reference_shape.text
                        for label in (
                            "市场参考价：",
                            "京东大客户价：",
                            "折扣率：",
                            "SKU：",
                            "货期：",
                            "发货物流/快递：",
                            "质保：",
                        )
                    )
                    assert all(
                        "{{" not in shape.text and "自动填入" not in shape.text
                        for shape in slide.shapes
                        if shape.has_text_frame
                    )
                    if name == "price-unit-spacing":
                        assert "市场参考价：69.00元" in reference_shape.text
                        assert "京东大客户价：50.00元" in reference_shape.text
                        assert "折扣率：78%" in reference_shape.text
                        assert "69.00元元" not in reference_shape.text
                        assert "50.00元元" not in reference_shape.text
                with ZipFile(BytesIO(data)) as archive:
                    media = {
                        sha256(archive.read(n)).hexdigest()
                        for n in archive.namelist()
                        if n.startswith("ppt/media/")
                    }
                outputs.append(
                    {
                        "path": str(output),
                        "sha256": sha256(data).hexdigest(),
                        "slides": len(deck.slides),
                        "reference_values_filled_in_original_shape": True,
                        "separate_value_layers": False,
                        "cover_unchanged": True,
                        "media_sha256": sorted(media),
                    }
                )
                print(output)
            for field, value in (
                ("product_name", "宽" * 300),
                ("sku", "W" * 100),
                ("selling_points", "\n".join([f"虚构卖点 {i}" for i in range(1, 8)])),
            ):
                item = deepcopy(_item(9))
                item["product"][field] = value  # type: ignore[index]
                try:
                    renderer.render(
                        {"single_products": [item]},
                        template_code="JD_FESTIVE_RED",
                        template_version="5",
                    )
                except AppError as error:
                    assert error.code == "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED"
                    errors.append({"field": field, "error": error.code})
                else:
                    raise AssertionError(f"long {field} was allowed")
        finally:
            get_settings.cache_clear()
    evidence.update(outputs=outputs, rejected_long_fields=errors)
    report = destination / "JD_FESTIVE_RED-v5-two-page-evidence.json"
    report.write_text(dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
