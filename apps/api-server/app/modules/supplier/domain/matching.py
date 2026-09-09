from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence

from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus

_WHITESPACE_PATTERN = re.compile(r"\s+")


class SupplierMatchStatus(StrEnum):
    MATCHED = "MATCHED"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"
    INELIGIBLE = "INELIGIBLE"


class SupplierMatchMethod(StrEnum):
    NAME_EXACT = "NAME_EXACT"


@dataclass(frozen=True)
class SupplierMatchCandidate:
    id: uuid.UUID
    supplier_name: str
    archive_status: ArchiveStatus | str
    cooperation_status: CooperationStatus | str
    is_deleted: bool


@dataclass(frozen=True)
class SupplierMatchResult:
    status: SupplierMatchStatus
    match_method: SupplierMatchMethod | None = None
    matched_supplier_id: uuid.UUID | None = None


def normalize_supplier_name(value: str) -> str:
    """Normalize a supplier name for deterministic exact matching only."""
    normalized = unicodedata.normalize("NFKC", value).strip()
    return _WHITESPACE_PATTERN.sub(" ", normalized)


def is_eligible_source_supplier(candidate: SupplierMatchCandidate) -> bool:
    """Return whether a supplier may be selected as a product source supplier."""
    return (
        candidate.archive_status == ArchiveStatus.ARCHIVED
        and candidate.cooperation_status == CooperationStatus.NORMAL
        and not candidate.is_deleted
    )


def classify_supplier_name_match(
    excel_supplier_name: str,
    candidates: Sequence[SupplierMatchCandidate],
) -> SupplierMatchResult:
    """Classify an Excel supplier name against current supplier candidates."""
    normalized_excel_name = normalize_supplier_name(excel_supplier_name)
    if not normalized_excel_name:
        return SupplierMatchResult(status=SupplierMatchStatus.UNMATCHED)

    same_name_candidates = [
        candidate
        for candidate in candidates
        if normalize_supplier_name(candidate.supplier_name) == normalized_excel_name
    ]
    if not same_name_candidates:
        return SupplierMatchResult(status=SupplierMatchStatus.UNMATCHED)

    eligible_candidates = [
        candidate for candidate in same_name_candidates if is_eligible_source_supplier(candidate)
    ]
    if not eligible_candidates:
        return SupplierMatchResult(status=SupplierMatchStatus.INELIGIBLE)
    if len(eligible_candidates) > 1:
        return SupplierMatchResult(status=SupplierMatchStatus.AMBIGUOUS)

    return SupplierMatchResult(
        status=SupplierMatchStatus.MATCHED,
        match_method=SupplierMatchMethod.NAME_EXACT,
        matched_supplier_id=eligible_candidates[0].id,
    )
