from base64 import b64decode
from io import BytesIO
from pathlib import Path

from pptx import Presentation

from app.modules.recommendation.application.ppt_renderer import PptRenderer
from app.modules.recommendation.application.ppt_template_registry import list_ppt_templates

_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9J7VIAAAAASUVORK5CYII="
)


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


def test_each_builtin_template_creates_an_editable_valid_pptx_with_three_package_images() -> None:
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
        expected_slide_count = 2 if template.code == "SYSTEM_DEFAULT" else 3
        assert len(deck.slides) == expected_slide_count
        text = _all_text(deck)
        assert "不锈钢保温杯" in text
        assert "89.00" in text
        assert "109.00" in text
        assert "虚构测试卖点" in text
        package_slide = deck.slides[-2]
        assert sum(shape.shape_type == 13 for shape in package_slide.shapes) == 3
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
