import uuid

import pytest

from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.matching.domain.rules import (
    BidItemMatchStatus,
    CanonicalRequirement,
    MatchableProduct,
    RecallStage,
    decide_product_matches,
    is_eligible_matching_product,
    normalize_match_text,
)
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus


def product(
    *,
    sku: str | None = "SKU-001",
    item_number: str | None = "ITEM-001",
    barcode_text: str | None = "690000000001",
    brand: str | None = "Clear",
    model: str | None = "ARC3",
    product_name: str | None = "Clear ARC3 蓝牙耳机",
    product_specification: str | None = "黑色 / 运动版",
    category_id: uuid.UUID | None = None,
    category_level1_name: str | None = "数码",
    category_level2_name: str | None = "影音娱乐",
    category_level3_name: str | None = "蓝牙/无线耳机",
    product_status: ProductStatus = ProductStatus.ACTIVE,
    archive_status: ArchiveStatus = ArchiveStatus.ARCHIVED,
    cooperation_status: CooperationStatus = CooperationStatus.NORMAL,
    supplier_is_deleted: bool = False,
) -> MatchableProduct:
    return MatchableProduct(
        id=uuid.uuid4(),
        supplier_id=uuid.uuid4(),
        product_status=product_status,
        supplier_archive_status=archive_status,
        supplier_cooperation_status=cooperation_status,
        supplier_is_deleted=supplier_is_deleted,
        sku=sku,
        item_number=item_number,
        barcode_text=barcode_text,
        brand=brand,
        model=model,
        product_name=product_name,
        category_id=category_id,
        category_level1_name=category_level1_name,
        category_level2_name=category_level2_name,
        category_level3_name=category_level3_name,
        product_specification=product_specification,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" Ｃｌｅａｒ　ARC-3 ", "cleararc3"),
        ("蓝牙/无线耳机", "蓝牙无线耳机"),
        (None, ""),
    ],
)
def test_normalize_match_text(value: str | None, expected: str) -> None:
    assert normalize_match_text(value) == expected


@pytest.mark.parametrize(
    ("product_status", "archive_status", "cooperation_status", "supplier_is_deleted"),
    [
        (ProductStatus.DISABLED, ArchiveStatus.ARCHIVED, CooperationStatus.NORMAL, False),
        (ProductStatus.ACTIVE, ArchiveStatus.DRAFT, CooperationStatus.NORMAL, False),
        (ProductStatus.ACTIVE, ArchiveStatus.PENDING, CooperationStatus.NORMAL, False),
        (ProductStatus.ACTIVE, ArchiveStatus.ARCHIVED, CooperationStatus.STOPPED, False),
        (ProductStatus.ACTIVE, ArchiveStatus.ARCHIVED, CooperationStatus.BLACKLIST, False),
        (ProductStatus.ACTIVE, ArchiveStatus.ARCHIVED, CooperationStatus.NORMAL, True),
    ],
)
def test_ineligible_product_or_supplier_is_excluded(
    product_status: ProductStatus,
    archive_status: ArchiveStatus,
    cooperation_status: CooperationStatus,
    supplier_is_deleted: bool,
) -> None:
    assert not is_eligible_matching_product(
        product(
            product_status=product_status,
            archive_status=archive_status,
            cooperation_status=cooperation_status,
            supplier_is_deleted=supplier_is_deleted,
        )
    )


def test_exact_buyer_item_code_returns_a_unique_candidate_with_explanation() -> None:
    candidate = product(sku="SKU-100")

    result = decide_product_matches(CanonicalRequirement(buyer_item_code=" sku 100 "), [candidate])

    assert result.status == BidItemMatchStatus.UNIQUE_MATCH
    assert result.candidates[0].product_id == candidate.id
    assert result.candidates[0].recall_stage == RecallStage.EXACT_IDENTIFIER
    assert result.candidates[0].match_reason()["rules_version"] == "v1"
    assert result.candidates[0].match_reason()["signals"][0] == {
        "field": "BUYER_ITEM_CODE",
        "score": 100,
        "comparison": "EXACT",
    }


def test_exact_brand_and_model_returns_a_unique_candidate_after_normalization() -> None:
    candidate = product(brand="Ｃｌｅａｒ", model="ARC-3")

    result = decide_product_matches(
        CanonicalRequirement(brand=" clear ", model="arc 3"), [candidate]
    )

    assert result.status == BidItemMatchStatus.UNIQUE_MATCH
    assert result.candidates[0].recall_stage == RecallStage.BRAND_MODEL
    assert result.candidates[0].score == 80


def test_multiple_exact_candidates_are_ranked_stably_and_require_manual_selection() -> None:
    first = product(sku="SAME", product_name="A 商品")
    second = product(sku="SAME", product_name="B 商品")

    result = decide_product_matches(CanonicalRequirement(buyer_item_code="SAME"), [second, first])

    assert result.status == BidItemMatchStatus.MULTIPLE_MATCH
    assert [candidate.rank for candidate in result.candidates] == [1, 2]
    assert [candidate.product_id for candidate in result.candidates] == sorted(
        (first.id, second.id), key=str
    )


def test_model_or_brand_conflict_cannot_be_rescued_by_a_similar_name() -> None:
    candidate = product(brand="Other", model="ARC4", product_name="Clear ARC3 蓝牙耳机")

    result = decide_product_matches(
        CanonicalRequirement(brand="Clear", model="ARC3", product_name="Clear ARC3 蓝牙耳机"),
        [candidate],
    )

    assert result.status == BidItemMatchStatus.NO_MATCH


def test_name_and_category_fallback_is_kept_for_manual_selection() -> None:
    candidate = product(product_name="Clear ARC3 蓝牙耳机", model=None)

    result = decide_product_matches(
        CanonicalRequirement(
            product_name="Clear ARC3 蓝牙耳机",
            category_text="数码 / 影音娱乐 / 蓝牙/无线耳机",
        ),
        [candidate],
    )

    assert result.status == BidItemMatchStatus.MULTIPLE_MATCH
    assert result.candidates[0].recall_stage == RecallStage.FALLBACK
    assert result.candidates[0].score == 50


def test_insufficient_condition_and_ineligible_candidates_do_not_force_a_match() -> None:
    candidate = product(product_status=ProductStatus.DISABLED)

    insufficient = decide_product_matches(CanonicalRequirement(), [candidate])
    ineligible = decide_product_matches(
        CanonicalRequirement(buyer_item_code="SKU-001"), [candidate]
    )

    assert insufficient.status == BidItemMatchStatus.NO_MATCH
    assert "匹配条件不足" in (insufficient.reason or "")
    assert ineligible.status == BidItemMatchStatus.NO_MATCH
    assert ineligible.candidates == ()
