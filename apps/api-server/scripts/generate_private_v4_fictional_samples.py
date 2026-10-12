"""Render private v4 candidates with entirely fictional product data.

The generated decks remain under the git-ignored review directory.  This helper
does not copy, publish, or otherwise expose any private template asset.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw

from app.modules.recommendation.application import ppt_renderer_v4
from app.modules.recommendation.application.ppt_template_manifest import (
    PPTX_VERSIONED_MANIFESTS,
)

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / ".codex-assets" / "ppt-v4-review"


def fictional_image() -> bytes:
    image = Image.new("RGB", (960, 720), "#dfe8ed")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((180, 130, 780, 590), radius=40, fill="#6e8fa3")
    draw.text((350, 335), "FICTIONAL", fill="white")
    content = BytesIO()
    image.save(content, format="PNG")
    return content.getvalue()


def source() -> dict[str, object]:
    return {
        "project": {"project_name": "虚构 2026 商品展示项目"},
        "single_products": [
            {
                "product": {
                    "id": "fictional-product-01",
                    "product_name": "虚构保温随行杯",
                    "brand": "示例品牌",
                    "model": "F-2026",
                    "sku": "FICT-2026-01",
                    "product_specification": "500ml，食品接触级不锈钢内胆",
                    "packaging_list": "杯体、杯盖、说明卡",
                    "selling_points": "双层真空保温；一键开合；可拆洗杯盖",
                    "shipping_courier": "虚构配送",
                    "warranty_period": "一年",
                    "third_category": "虚构礼品",
                },
                "manual": {"fulfillment_cycle": "7", "delivery_status": "虚构配送"},
                "prices": {
                    "market_price": "199.00",
                    "jd_price": "159.00",
                    "agreement_price": "129.00",
                },
            }
        ],
    }


def render(code: str) -> Path:
    candidate = REVIEW / f"{code}_CLEAN_v4.pptx"
    output = REVIEW / f"{code}-fictional-v4-format.pptx"
    template = SimpleNamespace(code=code, version="4")
    manifest = PPTX_VERSIONED_MANIFESTS[(code, "4")]
    resolver = ppt_renderer_v4.resolve_ppt_template_asset
    try:
        ppt_renderer_v4.resolve_ppt_template_asset = lambda _template: candidate
        rendered = ppt_renderer_v4.render_v4(
            source(),
            images={"fictional-product-01": fictional_image()},
            template=template,
            manifest=manifest,
        )
    finally:
        ppt_renderer_v4.resolve_ppt_template_asset = resolver
    output.write_bytes(rendered)
    return output


if __name__ == "__main__":
    REVIEW.mkdir(exist_ok=True)
    for template_code in ("JD_FESTIVE_RED", "CATALOG_MINIMAL", "UNION_QUOTE_WHITE"):
        print(render(template_code))
