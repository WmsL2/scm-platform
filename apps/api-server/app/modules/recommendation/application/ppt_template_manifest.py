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
    image_fit_modes: tuple[str, ...] = ()


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


# Frozen v3 contracts above deliberately remain untouched.  A v4 contract is
# keyed by both code and version so a historical task can never silently pick up
# a later template asset.
PPTX_VERSIONED_MANIFESTS: dict[tuple[str, str], PptxSlotManifest] = {
    ("UNION_QUOTE_WHITE", "5"): PptxSlotManifest(
        "模板4.pptx",
        "UNION_QUOTE_WHITE_OFFICIAL_CLEAN_v5.pptx",
        "5",
        None,
        0,
        {"SCM_FIELD_UNION_BODY": 1, "SCM_FIELD_TITLE": 2},
        (3,),
        image_fit_modes=("contain",),
    ),
    ("JD_DETAIL_RED", "5"): PptxSlotManifest(
        "模版1.pptx",
        "JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx",
        "5",
        0,
        1,
        {
            "SCM_FIELD_SPECIFICATION": 0,
            "SCM_FIELD_PACKAGING": 1,
            "SCM_FIELD_SELLING_POINTS": 2,
            "SCM_FIELD_DELIVERY": 3,
            "SCM_FIELD_TITLE": 4,
            "SCM_FIELD_BRAND": 6,
            "SCM_FIELD_REFERENCE": 7,
            "SCM_FIELD_PRICES": 8,
        },
        (11, 12, 13, 14),
        image_fit_modes=("cover", "cover", "cover", "cover"),
    ),
    ("JD_FESTIVE_RED", "5"): PptxSlotManifest(
        "模版2.pptx",
        "JD_FESTIVE_RED_OFFICIAL_CLEAN_v5.pptx",
        "5",
        0,
        1,
        {
            "SCM_SLOT_IMAGE_MAIN": 1,
            "SCM_FIELD_SELLING_POINTS": 2,
            "SCM_FIELD_REFERENCE": 3,
            "SCM_FIELD_TITLE": 4,
            "SCM_STATIC_PROJECT_NUMBER": 5,
            "SCM_STATIC_IMAGE_CAPTION": 6,
        },
        (1, 8, 10, 9),
        image_fit_modes=("contain",) * 4,
    ),
    ("JD_DETAIL_RED", "4"): PptxSlotManifest(
        "JD_DETAIL_RED.pptx",
        "JD_DETAIL_RED_CLEAN_v4-text-fix.pptx",
        "4",
        0,
        1,
        {
            "SCM_FIELD_SPECIFICATION": 0,
            "SCM_FIELD_PACKAGING": 1,
            "SCM_FIELD_SELLING_POINTS": 2,
            "SCM_FIELD_DELIVERY": 3,
            "SCM_FIELD_TITLE": 4,
            "SCM_FIELD_BRAND_MODEL": 6,
            "SCM_FIELD_REFERENCE": 7,
            "SCM_FIELD_PRICES": 8,
            "SCM_FIELD_IMAGE_NOTICE": 9,
            "SCM_FIELD_SERVICE": 10,
        },
        (11, 12, 13, 14),
        image_fit_modes=("contain", "contain", "contain", "contain"),
    ),
    ("JD_FESTIVE_RED", "4"): PptxSlotManifest(
        "JD_FESTIVE_RED.pptx", "JD_FESTIVE_RED_CLEAN_v4.pptx", "4", 0, 1,
        {"SCM_FIELD_SELLING_POINTS": 2, "SCM_FIELD_REFERENCE": 3,
         "SCM_FIELD_TITLE": 4, "SCM_STATIC_PROJECT_NUMBER": 5,
         "SCM_STATIC_IMAGE_CAPTION": 6},
        (8, 9, 10, 11, 12), image_fit_modes=("contain",) * 5,
    ),
    ("CATALOG_MINIMAL", "4"): PptxSlotManifest(
        "CATALOG_MINIMAL.pptx", "CATALOG_MINIMAL_CLEAN_v4.pptx", "4", None, 0,
        {"SCM_FIELD_CATALOG_CONTENT": 0, "SCM_FIELD_CATEGORY": 1}, (2,),
        image_fit_modes=("contain",),
    ),
    ("UNION_QUOTE_WHITE", "4"): PptxSlotManifest(
        "UNION_QUOTE_WHITE.pptx", "UNION_QUOTE_WHITE_CLEAN_v4.pptx", "4", None, 0,
        {"SCM_FIELD_UNION_BODY": 1, "SCM_FIELD_TITLE": 2}, (3,),
        image_fit_modes=("contain",),
    ),
}


def get_pptx_manifest(code: str, version: str) -> PptxSlotManifest | None:
    if version == "3":
        return PPTX_SLOT_MANIFESTS.get(code)
    return PPTX_VERSIONED_MANIFESTS.get((code, version))
