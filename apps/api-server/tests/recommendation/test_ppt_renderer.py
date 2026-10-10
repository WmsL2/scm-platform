from base64 import b64decode
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches

from app.common.contracts import AppError
from app.modules.recommendation.application import ppt_renderer, ppt_template_registry
from app.modules.recommendation.application.ppt_renderer import PptRenderer
from app.modules.recommendation.application.ppt_template_manifest import (
    PPTX_SLOT_MANIFESTS,
    SLOT_BODY,
    SLOT_IMAGE_PREFIX,
    SLOT_PRICE,
    SLOT_TITLE,
)
from app.modules.recommendation.application.ppt_template_registry import (
    get_ppt_template,
    list_ppt_templates,
)

_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9J7VIAAAAASUVORK5CYII="
)


def _add_static_shape(
    slide: object, *, left: float, top: float, width: float, height: float
) -> None:
    shape = slide.shapes.add_shape(  # type: ignore[attr-defined]
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor(230, 230, 230)
    shape.line.fill.background()


def _add_text_slot(
    slide: object, name: str, *, left: float, top: float, width: float, height: float
) -> None:
    slot = slide.shapes.add_textbox(  # type: ignore[attr-defined]
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    slot.name = name
    slot.text = "虚构模板槽位"


def _write_business_template_fixture(path: Path, template_code: str) -> None:
    """Create the minimum fictional clean deck required by the runtime slot contract."""
    manifest = PPTX_SLOT_MANIFESTS[template_code]
    deck = Presentation()
    deck.slide_width = Inches(13.333333)
    deck.slide_height = Inches(7.5)

    if manifest.cover_slide_index is not None:
        cover = deck.slides.add_slide(deck.slide_layouts[6])
        _add_static_shape(cover, left=0, top=0, width=13.333333, height=7.5)
        _add_text_slot(cover, "SCM_FIXTURE_COVER", left=1, top=3, width=11, height=0.8)

    product = deck.slides.add_slide(deck.slide_layouts[6])
    _add_static_shape(product, left=0, top=0, width=13.333333, height=0.2)
    _add_text_slot(product, SLOT_TITLE, left=6, top=0.5, width=6, height=0.7)
    _add_text_slot(product, SLOT_BODY, left=6, top=1.4, width=6, height=3.8)
    if SLOT_PRICE in manifest.source_text_slots:
        _add_text_slot(product, SLOT_PRICE, left=6, top=5.4, width=6, height=1.1)
    if template_code == "JD_FESTIVE_RED":
        # A fictional static background image must survive cloning while product
        # images are replaced in the named dynamic slots.
        product.shapes.add_picture(BytesIO(_PNG), 0, 0, deck.slide_width, deck.slide_height)
    image_count = len(manifest.source_image_slots)
    for index in range(image_count):
        _add_text_slot(
            product,
            f"{SLOT_IMAGE_PREFIX}{index + 1}",
            left=0.6 + (index % 2) * 2.5,
            top=1.0 + (index // 2) * 2.2,
            width=2.2,
            height=2.0,
        )
    deck.save(path)


@pytest.fixture
def business_template_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Path]:
    """Point the renderer's directly imported resolver at fictional tmp assets."""
    paths: dict[str, Path] = {}
    for template in list_ppt_templates():
        if template.code == "SYSTEM_DEFAULT":
            continue
        path = tmp_path / f"{template.code.lower()}-fixture.pptx"
        _write_business_template_fixture(path, template.code)
        paths[template.code] = path

    # ppt_renderer imports this function directly, so patching the registry alone
    # would leave the actual render call bound to the production resolver.
    monkeypatch.setattr(
        ppt_renderer,
        "resolve_ppt_template_asset",
        lambda template: paths[template.code],
    )
    return paths


def _source() -> dict[str, object]:
    return {
        "project": {
            "project_code": "PPT-20260930-001",
            "project_name": "工会中秋福利方案",
            "buyer_name": "示例工会",
            "requirement": "中秋福利，预算 500 元，适用于职工慰问，支持一件代发。",
        },
        "packages": [
            {
                "name": "500 元节日套装",
                "total_price": "488.00",
                "reason": "人工确认的节日慰问组合。",
                "items": [
                    {
                        "quantity": 2,
                        "unit_price": "88.00",
                        "line_total": "176.00",
                        "product_snapshot": {
                            "id": "package-product-1",
                            "product_name": "玻璃保鲜盒",
                            "brand": "示例品牌",
                            "model": "B-100",
                        },
                    },
                    {
                        "quantity": 1,
                        "unit_price": "312.00",
                        "line_total": "312.00",
                        "product_snapshot": {
                            "id": "package-product-2",
                            "product_name": "家用小家电",
                        },
                    },
                    {
                        "quantity": 1,
                        "unit_price": "0.00",
                        "line_total": "0.00",
                        "product_snapshot": {
                            "id": "package-product-3",
                            "product_name": "第三件虚构商品",
                        },
                    },
                ],
            }
        ],
        "single_products": [
            {
                "product": {
                    "id": "single-product",
                    "product_name": "不锈钢保温杯",
                    "brand": "示例品牌",
                    "model": "C-200",
                    "product_specification": "450ml，食品级不锈钢",
                    "selling_points": "虚构测试卖点",
                    "shipping_courier": "测试快递",
                    "warranty_period": "一年",
                },
                "prices": {
                    "market_price": "129.00",
                    "jd_price": "109.00",
                    "agreement_price": "99.00",
                },
                "manual": {
                    "campaign_price": "89.00",
                    "delivery_status": "一件代发",
                    "evidence": "人工确认可供货",
                },
            }
        ],
    }


def _all_text(deck: Presentation) -> str:
    return "\n".join(
        shape.text for slide in deck.slides for shape in slide.shapes if hasattr(shape, "text")
    )


def _slide_text(slide: object) -> str:
    return "\n".join(shape.text for shape in slide.shapes if hasattr(shape, "text"))  # type: ignore[attr-defined]


def test_renderer_creates_editable_default_pptx(tmp_path: Path) -> None:
    output = tmp_path / "default.pptx"
    output.write_bytes(PptRenderer().render(_source(), product_images={"single-product": _PNG}))

    deck = Presentation(output)
    assert len(deck.slides) == 2
    text = _all_text(deck)
    assert "商品名称：500 元节日套装" in text
    assert "500 元节日套装" in text
    assert "不锈钢保温杯" in text
    assert any(shape.shape_type == 13 for slide in deck.slides for shape in slide.shapes)


def test_renderer_preserves_customer_template_and_appends_editable_pages(tmp_path: Path) -> None:
    template = Presentation()
    template.slides.add_slide(template.slide_layouts[6]).shapes.add_textbox(
        0, 0, 1000000, 1000000
    ).text = "甲方模板封面"
    template_path = tmp_path / "customer-template.pptx"
    template.save(template_path)

    deck = Presentation(BytesIO(PptRenderer().render(_source(), template_path=template_path)))
    assert len(deck.slides) == 3
    assert "甲方模板封面" in _all_text(deck)
    assert "商品名称：500 元节日套装" in _all_text(deck)


def test_each_builtin_template_creates_an_editable_valid_pptx_with_three_package_images(
    business_template_assets: dict[str, Path],
) -> None:
    renderer = PptRenderer()
    images = {
        "single-product": _PNG,
        "package-product-1": _PNG,
        "package-product-2": _PNG,
        "package-product-3": _PNG,
    }
    for template in list_ppt_templates():
        deck = Presentation(
            BytesIO(renderer.render(_source(), template_code=template.code, product_images=images))
        )
        expected_slide_count = 3 if template.code in {"JD_DETAIL_RED", "JD_FESTIVE_RED"} else 2
        assert len(deck.slides) == expected_slide_count
        text = _all_text(deck)
        assert "不锈钢保温杯" in text
        assert "89.00" in text
        assert "109.00" in text
        assert "虚构测试卖点" in text
        package_slide = deck.slides[-2]
        # Festive has one retained full-slide background image in addition to the
        # three dynamic package images; the other source templates do not.
        expected_pictures = 4 if template.code == "JD_FESTIVE_RED" else 3
        assert sum(shape.shape_type == 13 for shape in package_slide.shapes) == expected_pictures
        assert "500 元节日套装" in _slide_text(package_slide)
        assert "不锈钢保温杯" not in _slide_text(package_slide)
        for slide in deck.slides:
            for shape in slide.shapes:
                assert shape.left >= 0 and shape.top >= 0
                assert shape.left + shape.width <= deck.slide_width
                assert shape.top + shape.height <= deck.slide_height


def test_long_details_use_continuation_pages_without_dropping_prices_or_name() -> None:
    source = _source()
    product = source["single_products"][0]["product"]  # type: ignore[index]
    product["product_name"] = "超长虚构商品名称" * 16  # type: ignore[index]
    product["product_specification"] = "长规格" * 220  # type: ignore[index]
    product["selling_points"] = "长卖点" * 220  # type: ignore[index]

    rendered = PptRenderer().render(source, product_images={"single-product": _PNG})
    deck = Presentation(BytesIO(rendered))
    text = _all_text(deck)
    assert "详情续页" in text
    assert "¥ 89.00" in text
    assert "¥ 109.00" in text
    assert "长规格" * 20 in text


def test_business_price_slot_avoids_body_price_and_missing_images_show_one_notice(
    business_template_assets: dict[str, Path],
) -> None:
    source = _source()
    source["packages"] = []  # type: ignore[index]
    for template in list_ppt_templates():
        if template.code == "SYSTEM_DEFAULT":
            continue
        deck = Presentation(BytesIO(PptRenderer().render(source, template_code=template.code)))
        text = _all_text(deck)
        assert text.count("协议价：¥ 99.00") == 1
        assert text.count("人工确认活动价：¥ 89.00") == 1
        assert text.count("商品图片待补充") == 1
        assert "快递：待确认" not in text
        assert "质保：待确认" not in text


def test_business_templates_retain_source_canvas_without_source_business_text(
    business_template_assets: dict[str, Path],
) -> None:
    renderer = PptRenderer()
    for template in list_ppt_templates():
        if template.code == "SYSTEM_DEFAULT":
            continue
        source_deck = Presentation(business_template_assets[template.code])
        source_strings = {
            shape.text.strip()
            for slide in source_deck.slides
            for shape in slide.shapes
            if getattr(shape, "has_text_frame", False) and shape.text.strip()
        }
        rendered = renderer.render(_source(), template_code=template.code)
        output = Presentation(BytesIO(rendered))
        assert (output.slide_width, output.slide_height) == (
            source_deck.slide_width,
            source_deck.slide_height,
        )
        rendered_text = _all_text(output)
        assert not source_strings.intersection({rendered_text})
        assert template.code in PPTX_SLOT_MANIFESTS
        with ZipFile(BytesIO(rendered)) as archive:
            assert not any("notesSlides" in name for name in archive.namelist())


def test_real_business_asset_missing_still_fails_explicitly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ppt_template_registry,
        "get_settings",
        lambda: SimpleNamespace(ppt_template_asset_dir=tmp_path, app_env="production"),
    )

    with pytest.raises(AppError) as raised:
        ppt_template_registry.resolve_ppt_template_asset(get_ppt_template("JD_DETAIL_RED"))

    assert getattr(raised.value, "code", None) == "PPT_TEMPLATE_ASSET_UNAVAILABLE"


def test_real_business_asset_version_mismatch_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = get_ppt_template("JD_DETAIL_RED")
    manifest = PPTX_SLOT_MANIFESTS[template.code]
    monkeypatch.setitem(
        PPTX_SLOT_MANIFESTS,
        template.code,
        replace(manifest, asset_version="fixture-version-mismatch"),
    )

    with pytest.raises(AppError) as raised:
        PptRenderer().render(
            _source(), template_code=template.code, template_version=template.version
        )

    assert getattr(raised.value, "code", None) == "PPT_TEMPLATE_ASSET_VERSION_MISMATCH"


def test_invalid_builtin_template_is_rejected() -> None:
    try:
        PptRenderer().render(_source(), template_code="../../not-a-template")
    except Exception as exc:
        assert getattr(exc, "code", None) == "PPT_TEMPLATE_INVALID"
    else:
        raise AssertionError("an unknown template code must be rejected")


def test_renderer_rejects_a_task_with_a_frozen_unavailable_template_version() -> None:
    try:
        PptRenderer().render(_source(), template_code="SYSTEM_DEFAULT", template_version="2")
    except Exception as exc:
        assert getattr(exc, "code", None) == "PPT_TEMPLATE_VERSION_UNAVAILABLE"
    else:
        raise AssertionError("an unavailable frozen version must be rejected")
