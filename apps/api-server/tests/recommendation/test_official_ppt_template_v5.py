from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches

from app.common.contracts import AppError
from app.modules.recommendation.application import ppt_official_template_v5
from app.modules.recommendation.application.ppt_official_template_v5 import (
    render_jd_detail_red_v5,
    standardize_jd_detail_red_v5,
    verify_no_sample_media,
)
from app.modules.recommendation.application.ppt_template_manifest import get_pptx_manifest
from app.modules.recommendation.application.ppt_template_registry import get_ppt_template
from scripts import build_private_official_ppt_template_v5
from scripts.build_private_official_ppt_template_v5 import build_runtime_asset


def _png(color: tuple[int, int, int], size: tuple[int, int] = (160, 80)) -> bytes:
    output = BytesIO()
    Image.new("RGB", size, color).save(output, format="PNG")
    return output.getvalue()


def _source_deck(path: Path) -> None:
    deck = Presentation()
    deck.slide_width = Inches(13.333)
    deck.slide_height = Inches(7.5)
    cover = deck.slides.add_slide(deck.slide_layouts[6])
    cover.shapes.add_textbox(Inches(1), Inches(1), Inches(5), Inches(1)).text = "固定封面"
    page = deck.slides.add_slide(deck.slide_layouts[6])
    # The standardiser deliberately reads audited source indices once only.
    dynamic_geometry = {
        0: (6.379, 3.290, 6.299, 0.503),
        1: (6.379, 3.757, 6.299, 0.503),
        2: (6.389, 4.995, 6.299, 1.715),
        3: (6.389, 4.236, 6.299, 0.301),
        4: (6.465, 0.854, 6.268, 0.335),
        6: (6.379, 2.615, 6.299, 0.301),
        7: (6.360, 1.186, 3.457, 1.688),
        8: (9.757, 1.165, 3.322, 1.816),
    }
    for index in range(15):
        left, top, width, height = dynamic_geometry.get(
            index,
            (0.3 + (index % 5) * 2.5, 0.3 + (index // 5) * 2.2, 2.2, 1.5),
        )
        shape = page.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(left),
            Inches(top),
            Inches(width),
            Inches(height),
        )
        shape.text = f"填写说明 {index}"
    sample = deck.slides.add_slide(deck.slide_layouts[6])
    sample.shapes.add_picture(
        BytesIO(_png((220, 10, 10))), Inches(1), Inches(1), Inches(2), Inches(2)
    )
    deck.save(path)


def _source() -> dict[str, object]:
    return {
        "single_products": [
            {
                "product": {
                    "id": "fictional-1",
                    "product_name": "虚构单品名称",
                    "brand": "虚构品牌",
                    "product_specification": "虚构规格 100mm",
                    "packaging_list": "虚构包装清单",
                    "selling_points": "虚构卖点 A\n虚构卖点 B",
                    "shipping_courier": "虚构快递",
                    "sku": "FICT-001",
                },
                "prices": {"market_price": "199.5", "discount_rate": "0.85"},
                "manual": {"fulfillment_cycle": "3 个工作日"},
            }
        ]
    }


def _runtime(tmp_path: Path) -> Path:
    source = tmp_path / "template1.pptx"
    runtime = tmp_path / "JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx"
    _source_deck(source)
    source_deck = Presentation(source)
    standardize_jd_detail_red_v5(
        source,
        runtime,
        expected_source_fingerprint=ppt_official_template_v5._structure_fingerprint(source_deck),
    )
    verify_no_sample_media(source, runtime)
    return runtime


def test_standardizer_removes_sample_slide_and_media(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    deck = Presentation(runtime)
    assert len(deck.slides) == 2
    assert {shape.name for shape in deck.slides[1].shapes} >= {
        "SCM_FIELD_TITLE",
        "SCM_FIELD_REFERENCE",
        "SCM_SLOT_IMAGE_MAIN",
    }
    assert "填写说明 0" not in "\n".join(
        shape.text for shape in deck.slides[1].shapes if shape.has_text_frame
    )


def test_standardizer_rejects_source_that_does_not_match_formal_contract(tmp_path: Path) -> None:
    source = tmp_path / "template1.pptx"
    _source_deck(source)
    with pytest.raises(AppError) as error:
        standardize_jd_detail_red_v5(source, tmp_path / "runtime.pptx")
    assert error.value.code == "PPT_TEMPLATE_ASSET_STRUCTURE_INVALID"


def test_v5_standardizer_restores_sample_brand_and_supplement_layout(tmp_path: Path) -> None:
    deck = Presentation(_runtime(tmp_path))
    page = deck.slides[1]
    brand = next(shape for shape in page.shapes if shape.name == "SCM_FIELD_BRAND")
    brand_geometry = (brand.left.inches, brand.top.inches, brand.width.inches, brand.height.inches)
    assert brand_geometry == pytest.approx((6.379, 2.615, 6.299, 0.301), abs=0.001)
    slots = [
        next(shape for shape in page.shapes if shape.name == name)
        for name in (
            "SCM_SLOT_IMAGE_SUPPLEMENT_01",
            "SCM_SLOT_IMAGE_SUPPLEMENT_02",
            "SCM_SLOT_IMAGE_SUPPLEMENT_03",
        )
    ]
    expected_geometry = (
        (0.448, 5.404, 1.367, 1.969),
        (2.258, 5.404, 1.354, 1.969),
        (4.069, 5.329, 1.313, 1.969),
    )
    for slot, expected in zip(slots, expected_geometry, strict=True):
        geometry = (slot.left.inches, slot.top.inches, slot.width.inches, slot.height.inches)
        assert geometry == pytest.approx(expected, abs=0.001)
    assert [slot.left for slot in slots] == sorted(slot.left for slot in slots)


def test_v5_standardizer_keeps_customer_price_label_black_and_value_red(tmp_path: Path) -> None:
    deck = Presentation(_runtime(tmp_path))
    prices = next(shape for shape in deck.slides[1].shapes if shape.name == "SCM_FIELD_PRICES")
    label, value = prices.text_frame.paragraphs[0].runs
    assert label.text == "京东大客户价：" and label.font.color.rgb == RGBColor(0, 0, 0)
    assert value.text == "{{jd_customer_price}}" and value.font.color.rgb == RGBColor(255, 0, 0)

    # This is deliberately a renderer-only fictional value; it does not add a
    # product, quotation, API, or frozen business-field source.
    ppt_official_template_v5._replace_token(prices, "{{jd_customer_price}}", "¥ 321.00")
    label, value = prices.text_frame.paragraphs[0].runs
    assert label.text == "京东大客户价：" and label.font.color.rgb == RGBColor(0, 0, 0)
    assert value.text == "¥ 321.00" and value.font.color.rgb == RGBColor(255, 0, 0)


def test_v5_standardizer_uses_single_line_spacing_only_for_requested_fields(
    tmp_path: Path,
) -> None:
    page = Presentation(_runtime(tmp_path)).slides[1]
    for name in (
        "SCM_FIELD_SPECIFICATION",
        "SCM_FIELD_PACKAGING",
        "SCM_FIELD_DELIVERY",
        "SCM_FIELD_SELLING_POINTS",
    ):
        assert all(paragraph.line_spacing == 1.0 for paragraph in next(
            shape for shape in page.shapes if shape.name == name
        ).text_frame.paragraphs)
    assert next(
        shape for shape in page.shapes if shape.name == "SCM_FIELD_BRAND"
    ).text_frame.paragraphs[0].line_spacing == 1.5


def test_v5_renderer_numbers_only_nonempty_selling_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"]["selling_points"] = "1、第一项\n\n第二项\n3.第三项"  # type: ignore[index]
    page = Presentation(
        BytesIO(
            render_jd_detail_red_v5(
                source,
                images={},
                template=get_ppt_template("JD_DETAIL_RED", "5"),
                manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
            )
        )
    ).slides[1]
    selling = next(shape for shape in page.shapes if shape.name == "SCM_FIELD_SELLING_POINTS")
    assert [paragraph.text for paragraph in selling.text_frame.paragraphs] == [
        "产品卖点（介绍详细）",
        "1、第一项",
        "2、第二项",
        "3、第三项",
    ]
    assert all(paragraph.line_spacing == 1.0 for paragraph in selling.text_frame.paragraphs)


def test_v5_renderer_keeps_empty_selling_points_as_header_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"]["selling_points"] = "\n\n"  # type: ignore[index]
    page = Presentation(
        BytesIO(
            render_jd_detail_red_v5(
                source,
                images={},
                template=get_ppt_template("JD_DETAIL_RED", "5"),
                manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
            )
        )
    ).slides[1]
    selling = next(shape for shape in page.shapes if shape.name == "SCM_FIELD_SELLING_POINTS")
    assert [paragraph.text for paragraph in selling.text_frame.paragraphs] == [
        "产品卖点（介绍详细）"
    ]


def test_v5_renderer_rejects_more_than_six_selling_points(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"]["selling_points"] = "\n".join(  # type: ignore[index]
        f"卖点 {index}" for index in range(1, 8)
    )
    with pytest.raises(AppError, match="安全容量") as error:
        render_jd_detail_red_v5(
            source,
            images={},
            template=get_ppt_template("JD_DETAIL_RED", "5"),
            manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
        )
    assert error.value.code == "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED"


def test_v5_renderer_rejects_six_wrapped_selling_points_that_exceed_box_height(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"]["selling_points"] = "\n".join(  # type: ignore[index]
        ["宽" * 40] * 6
    )
    with pytest.raises(AppError, match="自动换行后") as error:
        render_jd_detail_red_v5(
            source,
            images={},
            template=get_ppt_template("JD_DETAIL_RED", "5"),
            manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
        )
    assert error.value.code == "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED"


def test_v5_renderer_keeps_six_safe_selling_points_complete_and_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"]["selling_points"] = "\n".join(  # type: ignore[index]
        f"虚构卖点 {index}" for index in range(1, 7)
    )
    page = Presentation(
        BytesIO(
            render_jd_detail_red_v5(
                source,
                images={},
                template=get_ppt_template("JD_DETAIL_RED", "5"),
                manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
            )
        )
    ).slides[1]
    selling = next(shape for shape in page.shapes if shape.name == "SCM_FIELD_SELLING_POINTS")
    assert [paragraph.text for paragraph in selling.text_frame.paragraphs[1:]] == [
        f"{index}、虚构卖点 {index}" for index in range(1, 7)
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("product_name", "长标题" * 20),
        ("sku", "SKU" * 20),
        ("product_specification", "长规格" * 20),
    ),
)
def test_v5_renderer_rejects_long_title_sku_and_specification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: str
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"][field] = value  # type: ignore[index]
    with pytest.raises(AppError, match="安全容量"):
        render_jd_detail_red_v5(
            source,
            images={},
            template=get_ppt_template("JD_DETAIL_RED", "5"),
            manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("sku", "W" * 18),
        ("brand", "宽" * 34),
        ("shipping_courier", "宽" * 38),
    ),
)
def test_v5_renderer_rejects_rendered_fixed_row_overflow_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: str
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"][field] = value  # type: ignore[index]
    with pytest.raises(AppError, match="自动换行后") as error:
        render_jd_detail_red_v5(
            source,
            images={},
            template=get_ppt_template("JD_DETAIL_RED", "5"),
            manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
        )
    assert error.value.code == "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED"


def test_v5_renderer_accepts_normal_fixed_row_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    product = source["single_products"][0]["product"]  # type: ignore[index]
    product.update({"sku": "SCM-2026", "brand": "虚构品牌", "shipping_courier": "京东物流"})
    result = render_jd_detail_red_v5(
        source,
        images={},
        template=get_ppt_template("JD_DETAIL_RED", "5"),
        manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
    )
    assert len(Presentation(BytesIO(result)).slides) == 2


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        (0, "0%"),
        (1, "100%"),
        ("0.5", "50%"),
        ("0.85", "85%"),
        ("1.0", "100%"),
        (None, ""),
        ("", ""),
        ("not-a-rate", "not-a-rate"),
    ),
)
def test_v5_discount_formatter_preserves_integer_zeros(value: object, expected: str) -> None:
    assert ppt_official_template_v5._format_discount(value) == expected


def test_v5_supplement_slots_accept_distinct_fictional_images_without_stretching(
    tmp_path: Path,
) -> None:
    page = Presentation(_runtime(tmp_path)).slides[1]
    fixtures = (
        ("SCM_SLOT_IMAGE_SUPPLEMENT_01", _png((200, 10, 10), (80, 160))),
        ("SCM_SLOT_IMAGE_SUPPLEMENT_02", _png((10, 200, 10), (160, 80))),
        ("SCM_SLOT_IMAGE_SUPPLEMENT_03", _png((10, 10, 200), (100, 100))),
    )
    hashes: list[str] = []
    for name, image in fixtures:
        slot = next(shape for shape in page.shapes if shape.name == name)
        ppt_official_template_v5._replace_picture(slot, image)
        hashes.append(sha256(slot.image.blob).hexdigest())
        assert slot.crop_left or slot.crop_top
    assert len(set(hashes)) == 3


def test_v5_renderer_centers_horizontal_and_vertical_main_image_crops(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    fixtures = (
        (_png((200, 10, 10), (240, 80)), True),
        (_png((10, 10, 200), (80, 240)), False),
    )
    for image, horizontal in fixtures:
        page = Presentation(
            BytesIO(
                render_jd_detail_red_v5(
                    _source(),
                    images={"fictional-1": image},
                    template=get_ppt_template("JD_DETAIL_RED", "5"),
                    manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
                )
            )
        ).slides[1]
        main = next(shape for shape in page.shapes if shape.name == "SCM_SLOT_IMAGE_MAIN")
        assert main.crop_left == pytest.approx(main.crop_right)
        assert main.crop_top == pytest.approx(main.crop_bottom)
        if horizontal:
            assert main.crop_left > 0 and main.crop_top == 0
        else:
            assert main.crop_top > 0 and main.crop_left == 0


def test_v5_clone_does_not_duplicate_slide_layout_placeholders() -> None:
    deck = Presentation()
    source = deck.slides.add_slide(deck.slide_layouts[1])
    source_count = len(source.shapes)
    clone = ppt_official_template_v5._clone_slide(deck, source)
    assert len(clone.shapes) == source_count


@pytest.mark.parametrize("corruption", ("token", "geometry"))
def test_v5_renderer_rejects_runtime_token_or_geometry_contract_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str
) -> None:
    runtime = _runtime(tmp_path)
    deck = Presentation(runtime)
    page = deck.slides[1]
    title = next(shape for shape in page.shapes if shape.name == "SCM_FIELD_TITLE")
    if corruption == "token":
        title.text_frame.paragraphs[0].runs[0].text = "{{wrong_product_name}}"
    else:
        title.left = Inches(6.2)
    deck.save(runtime)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    with pytest.raises(AppError) as error:
        render_jd_detail_red_v5(
            _source(),
            images={},
            template=get_ppt_template("JD_DETAIL_RED", "5"),
            manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
        )
    assert error.value.code == "PPT_TEMPLATE_ASSET_STRUCTURE_INVALID"


def test_v5_renderer_rejects_missing_runtime_slot_with_controlled_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    deck = Presentation(runtime)
    page = deck.slides[1]
    missing = next(shape for shape in page.shapes if shape.name == "SCM_SLOT_IMAGE_MAIN")
    missing._element.getparent().remove(missing._element)
    deck.save(runtime)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    with pytest.raises(AppError) as error:
        render_jd_detail_red_v5(
            _source(),
            images={},
            template=get_ppt_template("JD_DETAIL_RED", "5"),
            manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
        )
    assert error.value.code == "PPT_TEMPLATE_ASSET_STRUCTURE_INVALID"


def test_private_builder_preserves_existing_runtime_when_candidate_validation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = tmp_path / "source.pptx"
    runtime = tmp_path / "runtime.pptx"
    original.write_bytes(b"private-source")
    runtime.write_bytes(b"approved-runtime")

    def fail_standardization(*_args: object, **_kwargs: object) -> None:
        raise AppError("PPT_TEMPLATE_ASSET_STRUCTURE_INVALID", "invalid", 409)

    monkeypatch.setattr(
        build_private_official_ppt_template_v5, "standardize_jd_detail_red_v5", fail_standardization
    )
    with pytest.raises(AppError, match="invalid"):
        build_runtime_asset(original, runtime)
    assert runtime.read_bytes() == b"approved-runtime"
    assert not list(tmp_path.glob("tmp*.pptx"))


def test_v5_render_preserves_fixed_cover_and_uses_frozen_values(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    result = render_jd_detail_red_v5(
        _source(),
        images={"fictional-1": _png((10, 20, 30))},
        template=get_ppt_template("JD_DETAIL_RED", "5"),
        manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
    )
    deck = Presentation(BytesIO(result))
    assert len(deck.slides) == 2
    assert deck.slides[0].shapes[0].text == "固定封面"
    page = deck.slides[1]
    text = "\n".join(shape.text for shape in page.shapes if shape.has_text_frame)
    assert "商品名称" not in text and "虚构单品名称" in text
    assert "市场参考价：¥ 199.50" in text and "折扣率：85%" in text
    assert "京东大客户价：" in text and "None" not in text
    picture = next(shape for shape in page.shapes if shape.name == "SCM_SLOT_IMAGE_MAIN")
    assert sha256(picture.image.blob).hexdigest() == sha256(_png((10, 20, 30))).hexdigest()
    assert picture.crop_left == picture.crop_right == pytest.approx(
        (1 - (2.2 / 1.5) / 2) / 2, abs=0.00001
    )


def test_v5_missing_values_leave_labels_and_empty_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"] = {"id": "fictional-1"}  # type: ignore[index]
    source["single_products"][0]["prices"] = {}
    source["single_products"][0]["manual"] = {}  # type: ignore[index]
    deck = Presentation(
        BytesIO(
            render_jd_detail_red_v5(
                source,
                images={},
                template=get_ppt_template("JD_DETAIL_RED", "5"),
                manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
            )
        )
    )
    text = "\n".join(shape.text for shape in deck.slides[1].shapes if shape.has_text_frame)
    assert "商品规格：" in text and "SKU：" in text and "None" not in text
    picture = next(shape for shape in deck.slides[1].shapes if shape.name == "SCM_SLOT_IMAGE_MAIN")
    assert Image.open(BytesIO(picture.image.blob)).size == (1, 1)


def test_v5_rejects_unsafe_long_value_before_writing_partial_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    source = _source()
    source["single_products"][0]["product"]["product_name"] = "超长虚构商品名称" * 10  # type: ignore[index]
    with pytest.raises(AppError, match="安全容量") as error:
        render_jd_detail_red_v5(
            source,
            images={},
            template=get_ppt_template("JD_DETAIL_RED", "5"),
            manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
        )
    assert error.value.code == "PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED"


def test_v5_uses_explicit_combination_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = _runtime(tmp_path)
    monkeypatch.setattr(
        ppt_official_template_v5, "resolve_ppt_template_asset", lambda _template: runtime
    )
    with pytest.raises(AppError, match="仅支持单品页"):
        render_jd_detail_red_v5(
            {"packages": [{"items": []}]},
            images={},
            template=get_ppt_template("JD_DETAIL_RED", "5"),
            manifest=get_pptx_manifest("JD_DETAIL_RED", "5"),
        )
