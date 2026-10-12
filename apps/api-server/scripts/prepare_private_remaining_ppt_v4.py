"""Create private v4 candidates from the already-clean v3 decks.

This preserves the selected slide/master/layout/static media relationships. It
only names dynamic shapes and inserts semantic tokens; output remains ignored.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from shutil import copyfile
from typing import Any

from pptx import Presentation

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / ".codex-assets" / "ppt-template-sources"
OUTPUT = ROOT / ".codex-assets" / "ppt-v4-review"


def copy_text_body(source: Any, target: Any) -> None:
    """Copy the original text body, including its paragraph and run formatting."""
    old_body = target._element.txBody
    old_body.getparent().replace(old_body, deepcopy(source._element.txBody))


def replace_run(paragraph: Any, index: int, text: str, *, clear_after: bool = False) -> None:
    """Change only textual content, retaining the original run properties."""
    while len(paragraph.runs) <= index:
        paragraph.add_run()
    paragraph.runs[index].text = text
    if clear_after:
        for run in paragraph.runs[index + 1 :]:
            run.text = ""


def rename(slide: Any, index: int, name: str) -> Any:
    shape = slide.shapes[index]
    shape.name = name
    return shape


def prepare_festive() -> None:
    source = SOURCE / "JD_FESTIVE_RED_CLEAN_v3.pptx"
    original = SOURCE / "JD_FESTIVE_RED.pptx"
    target = OUTPUT / "JD_FESTIVE_RED_CLEAN_v4.pptx"
    copyfile(source, target)
    deck = Presentation(str(target))
    slide = deck.slides[1]
    original_slide = Presentation(str(original)).slides[1]

    # These three bodies are copied from the approved original solely to retain
    # geometric/paragraph/run styling.  Every original product value is then
    # replaced by a semantic token or cleared before this private candidate is
    # ever rendered.
    selling_points = rename(slide, 2, "SCM_FIELD_SELLING_POINTS")
    copy_text_body(original_slide.shapes[2], selling_points)
    for index in range(1, 4):
        replace_run(
            selling_points.text_frame.paragraphs[index],
            0,
            f"{{{{selling_points:{index - 1}}}}}",
            clear_after=True,
        )

    reference = rename(slide, 3, "SCM_FIELD_REFERENCE")
    copy_text_body(original_slide.shapes[3], reference)
    price_row = reference.text_frame.paragraphs[0]
    replace_run(price_row, 1, "{{market_reference_value}}")
    replace_run(price_row, 2, "")
    replace_run(price_row, 5, "{{jd_customer_price_value}}")
    replace_run(price_row, 6, "")
    replace_run(price_row, 9, "{{discount_rate}}")
    replace_run(price_row, 10, "")
    replace_run(price_row, 12, "：{{sku}}")
    # The source's customer-specific price warning is not a static design
    # element and must never survive in a clean template.
    replace_run(price_row, 14, "")
    fulfilment_row = reference.text_frame.paragraphs[1]
    replace_run(fulfilment_row, 1, "{{fulfillment}}")
    replace_run(fulfilment_row, 5, "：{{delivery}}")
    replace_run(fulfilment_row, 6, "")
    replace_run(fulfilment_row, 7, "")
    replace_run(fulfilment_row, 9, "：{{warranty}}")

    title = rename(slide, 4, "SCM_FIELD_TITLE")
    copy_text_body(original_slide.shapes[4], title)
    replace_run(title.text_frame.paragraphs[0], 0, "{{title}}", clear_after=True)

    project_number = rename(slide, 5, "SCM_STATIC_PROJECT_NUMBER")
    copy_text_body(original_slide.shapes[5], project_number)
    image_caption = rename(slide, 6, "SCM_STATIC_IMAGE_CAPTION")
    copy_text_body(original_slide.shapes[6], image_caption)
    for index in range(8, 13):
        slide.shapes[index].name = f"SCM_SLOT_IMAGE_{index - 7:02d}"
    deck.save(str(target))


def prepare_catalog() -> None:
    source = SOURCE / "CATALOG_MINIMAL_CLEAN_v3.pptx"
    original = SOURCE / "CATALOG_MINIMAL.pptx"
    target = OUTPUT / "CATALOG_MINIMAL_CLEAN_v4.pptx"
    copyfile(source, target)
    deck = Presentation(str(target))
    slide = deck.slides[0]
    original_slide = Presentation(str(original)).slides[0]
    catalog_content = rename(slide, 0, "SCM_FIELD_CATALOG_CONTENT")
    copy_text_body(original_slide.shapes[0], catalog_content)
    paragraphs = catalog_content.text_frame.paragraphs
    replace_run(paragraphs[0], 0, "{{sku}}", clear_after=True)
    replace_run(paragraphs[1], 0, "{{title}}", clear_after=True)
    replace_run(paragraphs[3], 0, "{{category}}", clear_after=True)
    replace_run(paragraphs[4], 0, "{{color}}", clear_after=True)
    replace_run(paragraphs[5], 0, "{{product_specification}}", clear_after=True)
    for index in range(6, 9):
        replace_run(paragraphs[index], 0, "{{unused_catalog_detail}}", clear_after=True)
    replace_run(paragraphs[10], 0, "零售价：{{market_reference_value}}", clear_after=True)
    replace_run(paragraphs[11], 0, "团购价：{{agreement_price_value}}", clear_after=True)
    for index in range(14, 22):
        replace_run(
            paragraphs[index], 0, f"{{{{selling_points:{index - 14}}}}}", clear_after=True
        )
    replace_run(paragraphs[23], 0, "{{evidence}}", clear_after=True)
    category = rename(slide, 1, "SCM_FIELD_CATEGORY")
    copy_text_body(original_slide.shapes[1], category)
    replace_run(category.text_frame.paragraphs[0], 0, "{{category}}", clear_after=True)
    slide.shapes[2].name = "SCM_SLOT_IMAGE_01"
    deck.save(str(target))


def prepare_union() -> None:
    source = SOURCE / "UNION_QUOTE_WHITE_CLEAN_v3.pptx"
    original = SOURCE / "UNION_QUOTE_WHITE.pptx"
    target = OUTPUT / "UNION_QUOTE_WHITE_CLEAN_v4.pptx"
    copyfile(source, target)
    deck = Presentation(str(target))
    slide = deck.slides[0]
    original_slide = Presentation(str(original)).slides[0]
    body = rename(slide, 1, "SCM_FIELD_UNION_BODY")
    copy_text_body(original_slide.shapes[1], body)
    paragraphs = body.text_frame.paragraphs
    replace_run(paragraphs[0], 0, "SKU：{{sku}}", clear_after=True)
    replace_run(paragraphs[1], 0, "商品配置：{{product_specification}}", clear_after=True)
    replace_run(paragraphs[2], 0, "{{material}}", clear_after=True)
    replace_run(paragraphs[9], 0, "前台价：{{market_reference_value}}", clear_after=True)
    replace_run(
        paragraphs[10], 0, "协议价：{{agreement_price_value}}\v{{evidence}}", clear_after=True
    )
    replace_run(paragraphs[11], 0, "{{price_valid_until}}", clear_after=True)
    title = rename(slide, 2, "SCM_FIELD_TITLE")
    copy_text_body(original_slide.shapes[2], title)
    replace_run(title.text_frame.paragraphs[0], 0, "商品名称：{{title}}", clear_after=True)
    slide.shapes[3].name = "SCM_SLOT_IMAGE_01"
    deck.save(str(target))


if __name__ == "__main__":
    OUTPUT.mkdir(exist_ok=True)
    prepare_festive()
    prepare_catalog()
    prepare_union()
