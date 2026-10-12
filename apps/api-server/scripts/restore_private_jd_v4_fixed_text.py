"""Restore two audited fixed labels in the private JD v4 candidate.

Only the original static label paragraph is copied. No original product data,
dynamic text, media, metadata, or slide geometry is imported.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from pptx import Presentation

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = ROOT / ".codex-assets" / "ppt-template-sources" / "JD_DETAIL_RED.pptx"
SOURCE = ROOT / ".codex-assets" / "ppt-v4-review" / "JD_DETAIL_RED_CLEAN_v4-static-media.pptx"
OUTPUT = ROOT / ".codex-assets" / "ppt-v4-review" / "JD_DETAIL_RED_CLEAN_v4-text-fix.pptx"


def _shape_by_name(slide: Any, name: str) -> Any:
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    raise RuntimeError(f"missing expected shape: {name}")


def _replace_paragraph(destination: Any, source: Any) -> None:
    old = destination.text_frame.paragraphs[0]._element
    old.getparent().replace(old, deepcopy(source.text_frame.paragraphs[0]._element))


def main() -> None:
    if not REFERENCE.is_file() or not SOURCE.is_file():
        raise SystemExit("private reference or candidate is unavailable")
    reference = Presentation(str(REFERENCE))
    candidate = Presentation(str(SOURCE))
    reference_product = reference.slides[1]
    candidate_product = candidate.slides[1]

    # Original shape 38 is the fixed lower-left image caption. Original shape 24
    # owns the fixed selling-point heading; only its heading paragraph is static.
    _replace_paragraph(
        _shape_by_name(candidate_product, "SCM_FIELD_IMAGE_NOTICE"),
        reference_product.shapes[9],
    )
    _replace_paragraph(
        _shape_by_name(candidate_product, "SCM_FIELD_SELLING_POINTS"),
        reference_product.shapes[2],
    )
    # The reference label denotes a JD enterprise/customer quotation. It is not
    # interchangeable with the generic product `jd_price` field.
    for paragraph in _shape_by_name(candidate_product, "SCM_FIELD_PRICES").text_frame.paragraphs:
        for run in paragraph.runs:
            run.text = run.text.replace("{{jd_price}}", "{{jd_customer_price}}")
    candidate.save(str(OUTPUT))


if __name__ == "__main__":
    main()
