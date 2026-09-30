from base64 import b64decode
from io import BytesIO
from pathlib import Path

from pptx import Presentation

from app.modules.recommendation.application.ppt_renderer import PptRenderer

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
                },
                "prices": {"agreement_price": "99.00"},
                "manual": {"delivery_status": "一件代发", "evidence": "人工确认可供货"},
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
