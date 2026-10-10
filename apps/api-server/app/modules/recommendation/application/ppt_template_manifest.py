"""Private Type-5 clean-template contract.

Indices are used only once while sanitising source decks. Runtime rendering uses
the stable semantic shape names and never reads a filled business deck.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PptxSlotManifest:
    source_filename: str
    clean_filename: str
    asset_version: str
    cover_slide_index: int | None
    product_slide_index: int
    source_text_slots: dict[str, int]
    source_image_slots: tuple[int, ...]
    source_clear_text: tuple[int, ...] = ()
    source_remove_images: tuple[int, ...] = ()


SLOT_TITLE = "SCM_SLOT_TITLE"
SLOT_BODY = "SCM_SLOT_BODY"
SLOT_PRICE = "SCM_SLOT_PRICE"
SLOT_IMAGE_PREFIX = "SCM_SLOT_IMAGE_"


PPTX_SLOT_MANIFESTS: dict[str, PptxSlotManifest] = {
    "JD_DETAIL_RED": PptxSlotManifest(
        "JD_DETAIL_RED.pptx",
        "JD_DETAIL_RED_CLEAN_v3.pptx",
        "3",
        0,
        1,
        {SLOT_TITLE: 4, SLOT_BODY: 0, SLOT_PRICE: 7},
        (11, 12, 13, 14),
        (1, 2, 3, 6, 8, 9, 10),
    ),
    "JD_FESTIVE_RED": PptxSlotManifest(
        "JD_FESTIVE_RED.pptx",
        "JD_FESTIVE_RED_CLEAN_v3.pptx",
        "3",
        0,
        1,
        {SLOT_TITLE: 4, SLOT_BODY: 2, SLOT_PRICE: 3},
        (8, 9, 10, 11, 12),
        (5, 6),
    ),
    "CATALOG_MINIMAL": PptxSlotManifest(
        "CATALOG_MINIMAL.pptx",
        "CATALOG_MINIMAL_CLEAN_v3.pptx",
        "3",
        None,
        0,
        {SLOT_TITLE: 0, SLOT_BODY: 0},
        (4,),
        (1,),
        (2, 3),
    ),
    "UNION_QUOTE_WHITE": PptxSlotManifest(
        "UNION_QUOTE_WHITE.pptx",
        "UNION_QUOTE_WHITE_CLEAN_v3.pptx",
        "3",
        None,
        0,
        {SLOT_TITLE: 2, SLOT_BODY: 1},
        (3,),
    ),
}
