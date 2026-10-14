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
_BRAND_SCRIPT_PATTERN = re.compile(r"[\u3400-\u9fff]+|[a-z0-9]+")
_BRAND_SUFFIXES = (
    "官方旗舰店",
    "品牌旗舰店",
    "集团有限公司",
    "有限责任公司",
    "专卖店",
    "旗舰店",
    "有限公司",
    "通用配件",
    "集团",
    "公司",
    "计算机",
    "电脑",
    "数码",
    "品牌",
    "官方",
)
_MATCH_RULES_VERSION = "v2"
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
    cost_price: Decimal | None = None
    agreement_price: Decimal | None = None
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
    canonical_brand: str | None = None

    def match_reason(self) -> dict[str, object]:
        reason: dict[str, object] = {
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
        if self.canonical_brand is not None:
            reason["canonical_brand"] = self.canonical_brand
        return reason


@dataclass(frozen=True)
class MatchDecision:
    status: BidItemMatchStatus
    candidates: tuple[ScoredCandidate, ...]
    reason: str | None = None


@dataclass(frozen=True)
class _BrandCatalogGroup:
    member_keys: frozenset[str]
    aliases: frozenset[str]
    canonical_name: str


@dataclass(frozen=True)
class _BrandModelMatches:
    candidates: tuple[MatchableProduct, ...]
    ambiguous_brand: bool = False
    canonical_brand: str | None = None


BrandCatalog = tuple[_BrandCatalogGroup, ...]


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
    *,
    allow_brand_substitution: bool = False,
    brand_catalog: BrandCatalog | None = None,
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

    brand_model_matches = _brand_model_matches(
        requirement,
        eligible,
        brand_catalog=brand_catalog,
    )
    if brand_model_matches.candidates:
        return _build_decision(
            requirement,
            brand_model_matches.candidates,
            RecallStage.BRAND_MODEL,
            canonical_brand=brand_model_matches.canonical_brand,
        )

    fallback_matches = _fallback_matches(
        requirement,
        eligible,
        allow_brand_substitution=allow_brand_substitution,
    )
    if not fallback_matches:
        return MatchDecision(
            status=BidItemMatchStatus.NO_MATCH,
            candidates=(),
            reason="未找到符合商品状态和供应商资格的候选商品。",
        )
    return _build_decision(requirement, fallback_matches, RecallStage.FALLBACK)


def decide_identified_product_matches(
    requirement: CanonicalRequirement,
    candidates: Sequence[MatchableProduct],
    *,
    brand_catalog: BrandCatalog | None = None,
) -> MatchDecision:
    """Type 2 only accepts an exact SKU/code or exact brand and model match.

    Matching products are ordered by the agreement price (`agreement_price`) so the
    application service can deterministically select the cheapest quotable product.
    """
    eligible = [candidate for candidate in candidates if is_eligible_matching_product(candidate)]
    matches = _identifier_matches(requirement, eligible)
    recall_stage = RecallStage.EXACT_IDENTIFIER
    ambiguous_brand = False
    canonical_brand: str | None = None
    if not matches:
        brand_model_matches = _brand_model_matches(
            requirement,
            eligible,
            brand_catalog=brand_catalog,
        )
        matches = list(brand_model_matches.candidates)
        ambiguous_brand = brand_model_matches.ambiguous_brand
        canonical_brand = brand_model_matches.canonical_brand
        recall_stage = RecallStage.BRAND_MODEL
    if not matches:
        reason = (
            "品牌信息同时命中多个受控品牌，无法安全确定同品。"
            if ambiguous_brand
            else "未找到 SKU 或品牌型号完全一致的可用商品。"
        )
        return MatchDecision(
            status=BidItemMatchStatus.NO_MATCH,
            candidates=(),
            reason=reason,
        )
    return _build_decision(
        requirement,
        matches,
        recall_stage,
        prefer_lowest_price=True,
        canonical_brand=canonical_brand,
    )


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
    *,
    brand_catalog: BrandCatalog | None = None,
) -> _BrandModelMatches:
    model = normalize_match_text(requirement.model)
    requirement_aliases = _brand_aliases(requirement.brand)
    if not requirement_aliases or not model:
        return _BrandModelMatches(())

    normalized_requirement_brand = normalize_match_text(requirement.brand)
    requirement_key = _strip_brand_modifiers(normalized_requirement_brand)
    catalog = brand_catalog if brand_catalog is not None else build_brand_catalog(candidates)
    matched_groups = [
        group
        for group in catalog
        if _brand_group_matches_requirement(
            group,
            requirement_aliases,
            requirement_key,
            allow_embedded=requirement_key != normalized_requirement_brand,
        )
    ]
    if len(matched_groups) != 1:
        return _BrandModelMatches((), ambiguous_brand=len(matched_groups) > 1)

    matched_brand_keys = matched_groups[0].member_keys
    return _BrandModelMatches(
        tuple(
            candidate
            for candidate in candidates
            if normalize_match_text(candidate.brand) in matched_brand_keys
            and normalize_match_text(candidate.model) == model
        ),
        canonical_brand=matched_groups[0].canonical_name,
    )


def build_brand_catalog(
    candidates: Sequence[MatchableProduct],
) -> BrandCatalog:
    """Build one controlled brand-alias catalog for reuse across a matching task."""
    entries: dict[str, frozenset[str]] = {}
    for candidate in candidates:
        if not is_eligible_matching_product(candidate):
            continue
        member_key = normalize_match_text(candidate.brand)
        aliases = _brand_aliases(candidate.brand)
        if member_key and aliases:
            entries[member_key] = aliases

    member_keys = list(entries)
    parents = list(range(len(member_keys)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parents[right_root] = left_root

    alias_owner: dict[str, int] = {}
    for index, member_key in enumerate(member_keys):
        for alias in entries[member_key]:
            owner = alias_owner.setdefault(alias, index)
            union(index, owner)

    grouped_members: dict[int, set[str]] = {}
    grouped_aliases: dict[int, set[str]] = {}
    for index, member_key in enumerate(member_keys):
        root = find(index)
        grouped_members.setdefault(root, set()).add(member_key)
        grouped_aliases.setdefault(root, set()).update(entries[member_key])
    return tuple(
        _BrandCatalogGroup(
            member_keys=frozenset(grouped_members[root]),
            aliases=frozenset(grouped_aliases[root]),
            canonical_name=_canonical_brand_name(grouped_aliases[root]),
        )
        for root in grouped_members
    )


def resolve_controlled_brand_from_text(
    value: str | None, brand_catalog: BrandCatalog
) -> str | None:
    """Resolve an embedded brand only when one controlled catalog group is hit."""
    normalized = normalize_match_text(value)
    if not normalized:
        return None
    matched_groups = [
        group
        for group in brand_catalog
        if any(
            _is_safe_embedded_brand_alias(alias, normalized)
            for alias in group.aliases
        )
    ]
    if len(matched_groups) != 1:
        return None
    return matched_groups[0].canonical_name


def resolve_controlled_model_from_text(
    value: str | None, candidates: Sequence[MatchableProduct]
) -> str | None:
    """Resolve a model embedded in product/parameter text without guessing."""
    if not value:
        return None
    normalized_value = unicodedata.normalize("NFKC", value).casefold()
    labeled = re.search(
        r"(?:型号|model)\s*[:：]?\s*([a-z0-9][a-z0-9._/\-]{1,40})",
        normalized_value,
    )
    models_by_key: dict[str, str] = {}
    for candidate in candidates:
        key = normalize_match_text(candidate.model)
        if key and candidate.model:
            models_by_key.setdefault(key, candidate.model)
    if labeled:
        labeled_key = normalize_match_text(labeled.group(1))
        if labeled_key in models_by_key:
            return models_by_key[labeled_key]

    compact = normalize_match_text(value)
    matched_keys = {
        key
        for key in models_by_key
        if len(key) >= 3 and not key.isdecimal() and key in compact
    }
    if len(matched_keys) == 1:
        return models_by_key[next(iter(matched_keys))]
    if matched_keys:
        longest = max(matched_keys, key=len)
        if all(key in longest for key in matched_keys):
            return models_by_key[longest]
    return None


def _canonical_brand_name(aliases: set[str]) -> str:
    chinese_aliases = [
        alias
        for alias in aliases
        if re.fullmatch(r"[\u3400-\u9fff]+", alias) and len(alias) >= 2
    ]
    if chinese_aliases:
        return min(chinese_aliases, key=lambda alias: (len(alias), alias))
    return min(aliases, key=lambda alias: (len(alias), alias))


def _brand_aliases(value: str | None) -> frozenset[str]:
    normalized = normalize_match_text(value)
    if not normalized:
        return frozenset()
    stripped = _strip_brand_modifiers(normalized)
    aliases = {normalized, stripped}
    aliases.update(
        alias
        for alias in _BRAND_SCRIPT_PATTERN.findall(stripped)
        if _is_meaningful_brand_alias(alias)
    )
    return frozenset(alias for alias in aliases if alias)


def _strip_brand_modifiers(value: str) -> str:
    result = value
    changed = True
    while changed and result:
        changed = False
        for suffix in _BRAND_SUFFIXES:
            if result.endswith(suffix) and len(result) > len(suffix) + 1:
                result = result[: -len(suffix)]
                changed = True
                break
    return result


def _brand_group_matches_requirement(
    group: _BrandCatalogGroup,
    requirement_aliases: frozenset[str],
    requirement_key: str,
    *,
    allow_embedded: bool,
) -> bool:
    if group.aliases & requirement_aliases:
        return True
    if not allow_embedded:
        return False
    return any(
        _is_safe_embedded_brand_alias(alias, requirement_key) for alias in group.aliases
    )


def _is_safe_embedded_brand_alias(alias: str, requirement_key: str) -> bool:
    if alias not in requirement_key:
        return False
    return _is_meaningful_brand_alias(alias, embedded=True)


def _is_meaningful_brand_alias(alias: str, *, embedded: bool = False) -> bool:
    has_cjk = bool(re.search(r"[\u3400-\u9fff]", alias))
    minimum_length = 2 if has_cjk else 3 if embedded else 2
    return len(alias) >= minimum_length


def _fallback_matches(
    requirement: CanonicalRequirement,
    candidates: Sequence[MatchableProduct],
    *,
    allow_brand_substitution: bool = False,
) -> list[MatchableProduct]:
    matches: list[MatchableProduct] = []
    for candidate in candidates:
        if _has_hard_conflict(
            requirement,
            candidate,
            allow_brand_substitution=allow_brand_substitution,
        ):
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


def _has_hard_conflict(
    requirement: CanonicalRequirement,
    candidate: MatchableProduct,
    *,
    allow_brand_substitution: bool = False,
) -> bool:
    requirement_brand = normalize_match_text(requirement.brand)
    candidate_brand = normalize_match_text(candidate.brand)
    if (
        not allow_brand_substitution
        and requirement_brand
        and candidate_brand
        and requirement_brand != candidate_brand
    ):
        return True

    requirement_model = normalize_match_text(requirement.model)
    candidate_model = normalize_match_text(candidate.model)
    return bool(requirement_model and candidate_model and requirement_model != candidate_model)


def _build_decision(
    requirement: CanonicalRequirement,
    matches: Sequence[MatchableProduct],
    recall_stage: RecallStage,
    *,
    prefer_lowest_price: bool = False,
    canonical_brand: str | None = None,
) -> MatchDecision:
    scored = [
        (
            _score_candidate(
                requirement,
                candidate,
                recall_stage,
                canonical_brand=canonical_brand,
            ),
            candidate.agreement_price,
        )
        for candidate in matches
    ]
    if prefer_lowest_price:
        ranked = sorted(
            scored,
            key=lambda item: (
                item[1] is None,
                item[1] if item[1] is not None else Decimal("0"),
                -item[0].score,
                str(item[0].product_id),
            ),
        )
    else:
        ranked = sorted(scored, key=lambda item: (-item[0].score, str(item[0].product_id)))
    top_candidates = tuple(
        ScoredCandidate(
            product_id=candidate.product_id,
            supplier_id=candidate.supplier_id,
            score=candidate.score,
            rank=index,
            recall_stage=candidate.recall_stage,
            signals=candidate.signals,
            canonical_brand=candidate.canonical_brand,
        )
        for index, (candidate, _) in enumerate(ranked[:_MAX_CANDIDATES], start=1)
    )
    if len(top_candidates) == 1 and recall_stage is not RecallStage.FALLBACK:
        return MatchDecision(status=BidItemMatchStatus.UNIQUE_MATCH, candidates=top_candidates)
    return MatchDecision(status=BidItemMatchStatus.MULTIPLE_MATCH, candidates=top_candidates)


def _score_candidate(
    requirement: CanonicalRequirement,
    candidate: MatchableProduct,
    recall_stage: RecallStage,
    *,
    canonical_brand: str | None = None,
) -> ScoredCandidate:
    signals_list = _score_signals(requirement, candidate)
    if (
        recall_stage is RecallStage.BRAND_MODEL
        and not any(signal.field is MatchSignalField.BRAND for signal in signals_list)
    ):
        signals_list.append(MatchSignal(MatchSignalField.BRAND, 20, "CANONICAL_ALIAS"))
    signals = tuple(signals_list)
    return ScoredCandidate(
        product_id=candidate.id,
        supplier_id=candidate.supplier_id,
        score=sum(signal.score for signal in signals),
        rank=0,
        recall_stage=recall_stage,
        signals=signals,
        canonical_brand=canonical_brand,
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
