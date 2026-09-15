from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Mapping, Sequence

from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus

_SEPARATOR_PATTERN = re.compile(r"[\s\-_—–/\\|,，.。;；:：()（）\[\]【】{}<>《》]+")
_MATCH_RULES_VERSION = "v1"
_MAX_CANDIDATES = 20


class BidItemMatchStatus(StrEnum):
    PENDING = "PENDING"
    NO_MATCH = "NO_MATCH"
    UNIQUE_MATCH = "UNIQUE_MATCH"
    MULTIPLE_MATCH = "MULTIPLE_MATCH"
    SELECTED = "SELECTED"
    NO_QUOTE = "NO_QUOTE"


class RecallStage(StrEnum):
    EXACT_IDENTIFIER = "EXACT_IDENTIFIER"
    BRAND_MODEL = "BRAND_MODEL"
    FALLBACK = "FALLBACK"


class MatchSignalField(StrEnum):
    BUYER_ITEM_CODE = "BUYER_ITEM_CODE"
    BRAND = "BRAND"
    MODEL = "MODEL"
    CATEGORY = "CATEGORY"
    PRODUCT_NAME = "PRODUCT_NAME"
    SPECIFICATION = "SPECIFICATION"


@dataclass(frozen=True)
class CanonicalRequirement:
    """Canonical bid-project item input, normalized only during comparison."""

    product_name: str | None = None
    brand: str | None = None
    model: str | None = None
    specification: str | None = None
    category_text: str | None = None
    category_id: uuid.UUID | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    max_price: Decimal | None = None
    buyer_item_code: str | None = None
    source_data: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MatchableProduct:
    """Product and source-supplier facts required by deterministic matching."""

    id: uuid.UUID
    supplier_id: uuid.UUID
    product_status: ProductStatus | str
    supplier_archive_status: ArchiveStatus | str
    supplier_cooperation_status: CooperationStatus | str
    supplier_is_deleted: bool
    sku: str | None = None
    item_number: str | None = None
    barcode_text: str | None = None
    brand: str | None = None
    model: str | None = None
    product_name: str | None = None
    category_id: uuid.UUID | None = None
    category_level1_name: str | None = None
    category_level2_name: str | None = None
    category_level3_name: str | None = None
    product_specification: str | None = None


@dataclass(frozen=True)
class MatchSignal:
    field: MatchSignalField
    score: int
    comparison: str


@dataclass(frozen=True)
class ScoredCandidate:
    product_id: uuid.UUID
    supplier_id: uuid.UUID
    score: int
    rank: int
    recall_stage: RecallStage
    signals: tuple[MatchSignal, ...]

    def match_reason(self) -> dict[str, object]:
        return {
            "rules_version": _MATCH_RULES_VERSION,
            "recall_stage": self.recall_stage.value,
            "signals": [
                {
                    "field": signal.field.value,
                    "score": signal.score,
                    "comparison": signal.comparison,
                }
                for signal in self.signals
            ],
        }


@dataclass(frozen=True)
class MatchDecision:
    status: BidItemMatchStatus
    candidates: tuple[ScoredCandidate, ...]
    reason: str | None = None


def normalize_match_text(value: str | None) -> str:
    """Normalize case, width, whitespace, separators, and brackets deterministically."""
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return _SEPARATOR_PATTERN.sub("", normalized)


def is_eligible_matching_product(candidate: MatchableProduct) -> bool:
    """Only live products from available source suppliers can enter recall."""
    return (
        candidate.product_status == ProductStatus.ACTIVE
        and candidate.supplier_archive_status == ArchiveStatus.ARCHIVED
        and candidate.supplier_cooperation_status == CooperationStatus.NORMAL
        and not candidate.supplier_is_deleted
    )


def decide_product_matches(
    requirement: CanonicalRequirement,
    candidates: Sequence[MatchableProduct],
) -> MatchDecision:
    """Recall and rank candidates without selecting or writing any business record."""
    if not _has_match_evidence(requirement):
        return MatchDecision(
            status=BidItemMatchStatus.NO_MATCH,
            candidates=(),
            reason="匹配条件不足：至少需要商品名称、品牌型号、规格、类目或采购方编码之一。",
        )

    eligible = [candidate for candidate in candidates if is_eligible_matching_product(candidate)]
    identifier_matches = _identifier_matches(requirement, eligible)
    if identifier_matches:
        return _build_decision(requirement, identifier_matches, RecallStage.EXACT_IDENTIFIER)

    brand_model_matches = _brand_model_matches(requirement, eligible)
    if brand_model_matches:
        return _build_decision(requirement, brand_model_matches, RecallStage.BRAND_MODEL)

    fallback_matches = _fallback_matches(requirement, eligible)
    if not fallback_matches:
        return MatchDecision(
            status=BidItemMatchStatus.NO_MATCH,
            candidates=(),
            reason="未找到符合商品状态和供应商资格的候选商品。",
        )
    return _build_decision(requirement, fallback_matches, RecallStage.FALLBACK)


def _has_match_evidence(requirement: CanonicalRequirement) -> bool:
    return any(
        (
            normalize_match_text(requirement.buyer_item_code),
            normalize_match_text(requirement.brand),
            normalize_match_text(requirement.model),
            normalize_match_text(requirement.product_name),
            normalize_match_text(requirement.specification),
            normalize_match_text(requirement.category_text),
            requirement.category_id,
        )
    )


def _identifier_matches(
    requirement: CanonicalRequirement,
    candidates: Sequence[MatchableProduct],
) -> list[MatchableProduct]:
    code = normalize_match_text(requirement.buyer_item_code)
    if not code:
        return []
    return [
        candidate for candidate in candidates if _identifier_signal(code, candidate) is not None
    ]


def _brand_model_matches(
    requirement: CanonicalRequirement,
    candidates: Sequence[MatchableProduct],
) -> list[MatchableProduct]:
    brand = normalize_match_text(requirement.brand)
    model = normalize_match_text(requirement.model)
    if not brand or not model:
        return []
    return [
        candidate
        for candidate in candidates
        if normalize_match_text(candidate.brand) == brand
        and normalize_match_text(candidate.model) == model
    ]


def _fallback_matches(
    requirement: CanonicalRequirement,
    candidates: Sequence[MatchableProduct],
) -> list[MatchableProduct]:
    matches: list[MatchableProduct] = []
    for candidate in candidates:
        if _has_hard_conflict(requirement, candidate):
            continue
        signals = _score_signals(requirement, candidate)
        if signals and _is_sufficient_fallback_evidence(signals):
            matches.append(candidate)
    return matches


def _is_sufficient_fallback_evidence(signals: Sequence[MatchSignal]) -> bool:
    fields = {signal.field for signal in signals}
    return (
        MatchSignalField.PRODUCT_NAME in fields
        or MatchSignalField.SPECIFICATION in fields
        or MatchSignalField.CATEGORY in fields
    ) and bool(fields - {MatchSignalField.BRAND})


def _has_hard_conflict(requirement: CanonicalRequirement, candidate: MatchableProduct) -> bool:
    requirement_brand = normalize_match_text(requirement.brand)
    candidate_brand = normalize_match_text(candidate.brand)
    if requirement_brand and candidate_brand and requirement_brand != candidate_brand:
        return True

    requirement_model = normalize_match_text(requirement.model)
    candidate_model = normalize_match_text(candidate.model)
    return bool(requirement_model and candidate_model and requirement_model != candidate_model)


def _build_decision(
    requirement: CanonicalRequirement,
    matches: Sequence[MatchableProduct],
    recall_stage: RecallStage,
) -> MatchDecision:
    scored = [_score_candidate(requirement, candidate, recall_stage) for candidate in matches]
    ranked = sorted(scored, key=lambda candidate: (-candidate.score, str(candidate.product_id)))
    top_candidates = tuple(
        ScoredCandidate(
            product_id=candidate.product_id,
            supplier_id=candidate.supplier_id,
            score=candidate.score,
            rank=index,
            recall_stage=candidate.recall_stage,
            signals=candidate.signals,
        )
        for index, candidate in enumerate(ranked[:_MAX_CANDIDATES], start=1)
    )
    if len(top_candidates) == 1 and recall_stage is not RecallStage.FALLBACK:
        return MatchDecision(status=BidItemMatchStatus.UNIQUE_MATCH, candidates=top_candidates)
    return MatchDecision(status=BidItemMatchStatus.MULTIPLE_MATCH, candidates=top_candidates)


def _score_candidate(
    requirement: CanonicalRequirement,
    candidate: MatchableProduct,
    recall_stage: RecallStage,
) -> ScoredCandidate:
    signals = tuple(_score_signals(requirement, candidate))
    return ScoredCandidate(
        product_id=candidate.id,
        supplier_id=candidate.supplier_id,
        score=sum(signal.score for signal in signals),
        rank=0,
        recall_stage=recall_stage,
        signals=signals,
    )


def _score_signals(
    requirement: CanonicalRequirement,
    candidate: MatchableProduct,
) -> list[MatchSignal]:
    signals: list[MatchSignal] = []
    code = normalize_match_text(requirement.buyer_item_code)
    identifier = _identifier_signal(code, candidate) if code else None
    if identifier is not None:
        signals.append(identifier)

    if _same_text(requirement.brand, candidate.brand):
        signals.append(MatchSignal(MatchSignalField.BRAND, 20, "EXACT"))
    if _same_text(requirement.model, candidate.model):
        signals.append(MatchSignal(MatchSignalField.MODEL, 60, "EXACT"))
    if _category_matches(requirement, candidate):
        signals.append(MatchSignal(MatchSignalField.CATEGORY, 20, "EXACT"))

    product_name_comparison = _text_similarity(requirement.product_name, candidate.product_name)
    if product_name_comparison is not None:
        score = 30 if product_name_comparison == "EXACT" else 20
        signals.append(MatchSignal(MatchSignalField.PRODUCT_NAME, score, product_name_comparison))

    specification_comparison = _text_similarity(
        requirement.specification, candidate.product_specification
    )
    if specification_comparison is not None:
        score = 15 if specification_comparison == "EXACT" else 10
        signals.append(MatchSignal(MatchSignalField.SPECIFICATION, score, specification_comparison))
    return signals


def _identifier_signal(code: str, candidate: MatchableProduct) -> MatchSignal | None:
    for candidate_code in (candidate.sku, candidate.item_number, candidate.barcode_text):
        if normalize_match_text(candidate_code) == code:
            return MatchSignal(MatchSignalField.BUYER_ITEM_CODE, 100, "EXACT")
    return None


def _category_matches(requirement: CanonicalRequirement, candidate: MatchableProduct) -> bool:
    if requirement.category_id is not None and requirement.category_id == candidate.category_id:
        return True
    category_text = normalize_match_text(requirement.category_text)
    if not category_text:
        return False
    category_path = normalize_match_text(
        "/".join(
            value
            for value in (
                candidate.category_level1_name,
                candidate.category_level2_name,
                candidate.category_level3_name,
            )
            if value
        )
    )
    return bool(category_path and category_path == category_text)


def _same_text(left: str | None, right: str | None) -> bool:
    normalized_left = normalize_match_text(left)
    normalized_right = normalize_match_text(right)
    return bool(normalized_left and normalized_left == normalized_right)


def _text_similarity(left: str | None, right: str | None) -> str | None:
    normalized_left = normalize_match_text(left)
    normalized_right = normalize_match_text(right)
    if not normalized_left or not normalized_right:
        return None
    if normalized_left == normalized_right:
        return "EXACT"
    if len(normalized_left) >= 4 and (
        normalized_left in normalized_right or normalized_right in normalized_left
    ):
        return "CONTAINS"
    return None
