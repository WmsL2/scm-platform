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


def fictional_image(
    color: str,
    *,
    size: tuple[int, int] = (960, 720),
    label: str = "FICTIONAL",
) -> bytes:
    """Create a private-only, clearly fictional raster fixture.

    The pixels act only as deterministic image-replacement test data. They are
    never copied to source control and deliberately do not depict a product,
    person, logo, or customer material.
    """
    image = Image.new("RGB", size, "#dfe8ed")
    draw = ImageDraw.Draw(image)
    inset_x, inset_y = size[0] // 5, size[1] // 5
    draw.rounded_rectangle(
        (inset_x, inset_y, size[0] - inset_x, size[1] - inset_y),
        radius=max(20, min(size) // 18),
        fill=color,
    )
    draw.text((size[0] // 3, size[1] // 2), label, fill="white")
    content = BytesIO()
    image.save(content, format="PNG")
    return content.getvalue()


def source(package_size: int | None = None) -> dict[str, object]:
    products = [
        {
            "id": f"fictional-package-{index}",
            "product_name": f"虚构组合商品 {index}",
            "brand": "示例品牌",
            "model": f"PK-{index:02d}",
            "sku": f"FICT-PK-{index:02d}",
        }
        for index in range(1, 5)
    ]
    if package_size is not None:
        return {
            "project": {"project_name": "虚构 2026 组合展示项目"},
            "single_products": [],
            "packages": [
                {
                    "name": f"虚构 {package_size} 件组合方案",
                    "total_price": "399.00",
                    "reason": "完全虚构的组合方案验证数据。",
                    "items": [
                        {"quantity": 1, "product_snapshot": product}
                        for product in products[:package_size]
                    ],
                }
            ],
        }
    return {
        "project": {"project_name": "虚构 2026 商品展示项目"},
        "packages": [],
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


def _package(
    name: str, products: list[dict[str, object]], *, total_price: str
) -> dict[str, object]:
    return {
        "name": name,
        "total_price": total_price,
        "reason": "完全虚构的组合方案验证数据。",
        "items": [
            {"quantity": index, "product_snapshot": product}
            for index, product in enumerate(products, start=1)
        ],
    }


def multi_package_source() -> tuple[dict[str, object], dict[str, bytes]]:
    """Return five combinations with unique page markers and product images."""
    packages: list[dict[str, object]] = []
    images: dict[str, bytes] = {}
    colors = ("#a36e6e", "#6ea37b", "#866ea3", "#a38f6e", "#6e8fa3")
    for package_index in range(1, 6):
        products: list[dict[str, object]] = []
        for product_index in range(1, 3):
            product_id = f"fictional-multi-{package_index}-{product_index}"
            products.append(
                {
                    "id": product_id,
                    "product_name": f"虚构连续组合 {package_index} 商品 {product_index}",
                    "brand": "示例品牌",
                    "model": f"MULTI-{package_index:02d}-{product_index:02d}",
                    "sku": f"FICT-MULTI-{package_index:02d}-{product_index:02d}",
                }
            )
            images[product_id] = fictional_image(
                colors[(package_index + product_index) % len(colors)],
                label=f"M{package_index}-{product_index}",
            )
        packages.append(
            _package(
                f"虚构连续组合方案 {package_index}",
                products,
                total_price=f"{package_index}99.00",
            )
        )
    return (
        {
            "project": {"project_name": "虚构连续五组合验收项目"},
            "single_products": [],
            "packages": packages,
        },
        images,
    )


def boundary_source() -> tuple[dict[str, object], dict[str, bytes]]:
    """Exercise long text, missing media, and landscape/portrait media privately."""
    # This is deliberately near (but inside) the strict one-line title-bar
    # capacity.  A separate automated regression asserts that a two-line title
    # returns a capacity error instead of generating invisible text.
    long_name = "虚构长标题边界验证商品甲乙丙丁戊己庚辛壬癸"
    long_specification = (
        "虚构超长规格字段，用于验证规格区域不会被渲染器截断；包含多段参数、"
        "材质、尺寸、颜色、包装要求和完全虚构的验收标识。"
    )
    long_points = "；".join(
        f"虚构超长卖点 {index}：用于边界验收的说明文字，验证模板文本框在长内容下的"
        "换行、行距和可读性。"
        for index in range(1, 7)
    )
    long_product = {
        "id": "fictional-boundary-long",
        "product_name": long_name,
        "brand": "虚构超长品牌名称用于参考字段续页验证",
        "model": "BOUNDARY-LONG-MODEL-REFERENCE-01",
        "sku": "FICT-BOUNDARY-LONG-REFERENCE-01",
        "product_specification": long_specification,
        "packaging_list": "完全虚构包装清单",
        "selling_points": long_points,
        "shipping_courier": "虚构配送",
        "warranty_period": "一年",
        "third_category": "虚构礼品",
    }
    portrait_product = {
        "id": "fictional-boundary-portrait",
        "product_name": "虚构竖版图片商品",
        "brand": "虚构超长竖图品牌名称用于参考字段验证",
        "model": "BOUNDARY-PORTRAIT-MODEL-REFERENCE-01",
        "sku": "FICT-BOUNDARY-PORTRAIT-REFERENCE-01",
        "product_specification": "竖版图片比例验收",
        "selling_points": "完全虚构竖版图片测试",
    }
    missing_product = {
        "id": "fictional-boundary-missing",
        "product_name": "虚构缺失图片商品",
        "brand": "虚构超长缺图品牌名称用于参考字段验证",
        "model": "BOUNDARY-MISSING-MODEL-REFERENCE-01",
        "sku": "FICT-BOUNDARY-MISSING-REFERENCE-01",
        "product_specification": "缺失图片不应复用上一页图片",
        "selling_points": "完全虚构缺图测试",
    }
    combo_products = [
        {
            "id": f"fictional-boundary-combo-{index}",
            "product_name": f"虚构横竖混合组合商品 {index}",
            "brand": "示例品牌",
            "model": f"BOUNDARY-COMBO-{index:02d}",
            "sku": f"FICT-BOUNDARY-COMBO-{index:02d}",
        }
        for index in range(1, 5)
    ]
    return (
        {
            "project": {"project_name": "虚构边界验收项目"},
            "packages": [_package("虚构横竖混合四件组合", combo_products, total_price="899.00")],
            "single_products": [
                {
                    "product": long_product,
                    "manual": {
                        "fulfillment_cycle": "预计三十个工作日内分批交付并签收回传",
                        "delivery_status": "虚构配送",
                    },
                    "prices": {
                        "market_price": "999.00",
                        "jd_price": "899.00",
                        "agreement_price": "799.00",
                    },
                },
                {
                    "product": portrait_product,
                    "manual": {
                        "fulfillment_cycle": "预计三十个工作日内分批交付并签收回传",
                        "delivery_status": "虚构配送",
                    },
                    "prices": {
                        "market_price": "299.00",
                        "jd_price": "259.00",
                        "agreement_price": "229.00",
                    },
                },
                {
                    "product": missing_product,
                    "manual": {
                        "fulfillment_cycle": "预计三十个工作日内分批交付并签收回传",
                        "delivery_status": "虚构配送",
                    },
                    "prices": {
                        "market_price": "199.00",
                        "jd_price": "169.00",
                        "agreement_price": "149.00",
                    },
                },
            ],
        },
        {
            "fictional-boundary-long": fictional_image(
                "#a36e6e", size=(1200, 720), label="LONG-H"
            ),
            "fictional-boundary-portrait": fictional_image(
                "#6ea37b", size=(720, 1200), label="PORTRAIT"
            ),
            **{
                product["id"]: fictional_image(
                    ("#866ea3", "#a38f6e", "#6e8fa3", "#a36e6e")[index - 1],
                    size=(1200, 720) if index % 2 else (720, 1200),
                    label=f"C{index}",
                )
                for index, product in enumerate(combo_products, start=1)
            },
        },
    )


def _candidate(code: str) -> Path:
    if code == "JD_DETAIL_RED":
        candidate = REVIEW / "JD_DETAIL_RED_CLEAN_v4-text-fix.pptx"
    else:
        candidate = REVIEW / f"{code}_CLEAN_v4.pptx"
    if not candidate.is_file():
        raise RuntimeError(f"missing final private v4 candidate: {candidate}")
    return candidate


def _render_source(
    code: str, suffix: str, payload: dict[str, object], images: dict[str, bytes]
) -> Path:
    candidate = _candidate(code)
    output = REVIEW / f"{code}-{suffix}-fictional-v4-format.pptx"
    template = SimpleNamespace(code=code, version="4")
    manifest = PPTX_VERSIONED_MANIFESTS[(code, "4")]
    resolver = ppt_renderer_v4.resolve_ppt_template_asset
    try:
        ppt_renderer_v4.resolve_ppt_template_asset = lambda _template: candidate
        rendered = ppt_renderer_v4.render_v4(
            payload,
            images=images,
            template=template,
            manifest=manifest,
        )
    finally:
        ppt_renderer_v4.resolve_ppt_template_asset = resolver
    output.write_bytes(rendered)
    return output


def render(code: str, package_size: int | None = None, *, artifact_suffix: str = "") -> Path:
    package_colors = ("#a36e6e", "#6ea37b", "#866ea3", "#a38f6e")
    suffix = "single" if package_size is None else f"combination-{package_size}"
    return _render_source(
        code,
        suffix + artifact_suffix,
        source(package_size),
        {
            "fictional-product-01": fictional_image("#6e8fa3", label="SINGLE"),
            **{
                f"fictional-package-{index}": fictional_image(color, label=f"P{index}")
                for index, color in enumerate(package_colors, start=1)
            },
        },
    )


def render_multi_packages(code: str, *, artifact_suffix: str = "") -> Path:
    payload, images = multi_package_source()
    return _render_source(code, "multi-combination-5" + artifact_suffix, payload, images)


def render_boundary(code: str, *, artifact_suffix: str = "") -> Path:
    payload, images = boundary_source()
    return _render_source(code, "boundary" + artifact_suffix, payload, images)


if __name__ == "__main__":
    REVIEW.mkdir(exist_ok=True)
    for package_size in (None, 2, 3, 4):
        print(render("JD_DETAIL_RED", package_size, artifact_suffix="-round2"))
    print(render_multi_packages("JD_DETAIL_RED", artifact_suffix="-round2"))
    print(render_boundary("JD_DETAIL_RED", artifact_suffix="-round2"))
