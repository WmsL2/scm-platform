import uuid

import pytest

from app.modules.supplier.domain.matching import (
    SupplierMatchCandidate,
    SupplierMatchMethod,
    SupplierMatchStatus,
    classify_supplier_name_match,
    is_eligible_source_supplier,
    normalize_supplier_name,
    supplier_name_identity_key,
)
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus


def candidate(
    supplier_name: str,
    *,
    archive_status: ArchiveStatus = ArchiveStatus.ARCHIVED,
    cooperation_status: CooperationStatus = CooperationStatus.NORMAL,
    is_deleted: bool = False,
) -> SupplierMatchCandidate:
    return SupplierMatchCandidate(
        id=uuid.uuid4(),
        supplier_name=supplier_name,
        archive_status=archive_status,
        cooperation_status=cooperation_status,
        is_deleted=is_deleted,
    )


@pytest.mark.parametrize(
    ("raw_name", "expected"),
    [
        ("  广州　XX   科技有限公司  ", "广州 XX 科技有限公司"),
        ("ＡＢＣ　供应商", "ABC 供应商"),
        ("\t广州\n科技有限公司\r", "广州 科技有限公司"),
        ("", ""),
    ],
)
def test_normalize_supplier_name_only_applies_nfkc_and_whitespace(
    raw_name: str, expected: str
) -> None:
    assert normalize_supplier_name(raw_name) == expected


def test_normalize_supplier_name_preserves_region_and_company_suffix() -> None:
    assert normalize_supplier_name("广州科技有限公司") == "广州科技有限公司"


def test_supplier_master_identity_ignores_punctuation_and_spacing_only() -> None:
    expected = supplier_name_identity_key("甜卿品牌管理(深圳)有限公司")
    assert supplier_name_identity_key(" 甜卿 品牌管理（深圳）有限公司。 ") == expected
    assert supplier_name_identity_key("甜卿品牌管理(广州)有限公司") != expected
    assert supplier_name_identity_key("（） 。 - ") == ""
    # Product-source matching deliberately keeps its stricter ADR-0008 rule.
    assert normalize_supplier_name("甜卿品牌管理(深圳)有限公司") != normalize_supplier_name(
        "甜卿品牌管理（深圳）有限公司。"
    )


@pytest.mark.parametrize(
    ("archive_status", "cooperation_status", "is_deleted"),
    [
        (ArchiveStatus.DRAFT, CooperationStatus.NORMAL, False),
        (ArchiveStatus.PENDING, CooperationStatus.NORMAL, False),
        (ArchiveStatus.ARCHIVED, CooperationStatus.STOPPED, False),
        (ArchiveStatus.ARCHIVED, CooperationStatus.BLACKLIST, False),
        (ArchiveStatus.ARCHIVED, CooperationStatus.NORMAL, True),
    ],
)
def test_ineligible_suppliers_cannot_be_source_candidates(
    archive_status: ArchiveStatus,
    cooperation_status: CooperationStatus,
    is_deleted: bool,
) -> None:
    assert not is_eligible_source_supplier(
        candidate(
            "广州 XX 科技有限公司",
            archive_status=archive_status,
            cooperation_status=cooperation_status,
            is_deleted=is_deleted,
        )
    )


def test_unique_eligible_exact_name_candidate_matches() -> None:
    matched_candidate = candidate("广州 XX 科技有限公司")

    result = classify_supplier_name_match("  广州　XX   科技有限公司 ", [matched_candidate])

    assert result.status == SupplierMatchStatus.MATCHED
    assert result.match_method == SupplierMatchMethod.NAME_EXACT
    assert result.matched_supplier_id == matched_candidate.id


def test_no_same_name_candidate_is_unmatched_without_fuzzy_matching() -> None:
    result = classify_supplier_name_match("广州 XX 科技有限公司", [candidate("广州 XX 科技")])

    assert result.status == SupplierMatchStatus.UNMATCHED
    assert result.match_method is None
    assert result.matched_supplier_id is None


@pytest.mark.parametrize(
    "same_name_candidate",
    [
        candidate("广州 XX 科技有限公司", cooperation_status=CooperationStatus.STOPPED),
        candidate("广州 XX 科技有限公司", cooperation_status=CooperationStatus.BLACKLIST),
        candidate("广州 XX 科技有限公司", is_deleted=True),
    ],
)
def test_same_name_but_only_ineligible_candidates_are_ineligible(
    same_name_candidate: SupplierMatchCandidate,
) -> None:
    result = classify_supplier_name_match("广州 XX 科技有限公司", [same_name_candidate])

    assert result.status == SupplierMatchStatus.INELIGIBLE
    assert result.match_method is None
    assert result.matched_supplier_id is None


def test_multiple_eligible_same_name_candidates_are_ambiguous() -> None:
    result = classify_supplier_name_match(
        "广州 XX 科技有限公司",
        [candidate("广州 XX 科技有限公司"), candidate("广州 XX 科技有限公司")],
    )

    assert result.status == SupplierMatchStatus.AMBIGUOUS
    assert result.match_method is None
    assert result.matched_supplier_id is None


def test_one_eligible_and_one_ineligible_same_name_candidate_matches() -> None:
    matched_candidate = candidate("广州 XX 科技有限公司")
    result = classify_supplier_name_match(
        "广州 XX 科技有限公司",
        [
            matched_candidate,
            candidate("广州 XX 科技有限公司", cooperation_status=CooperationStatus.STOPPED),
        ],
    )

    assert result.status == SupplierMatchStatus.MATCHED
    assert result.match_method == SupplierMatchMethod.NAME_EXACT
    assert result.matched_supplier_id == matched_candidate.id
