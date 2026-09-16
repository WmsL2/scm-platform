from enum import StrEnum

from app.common.contracts import AppError


class BidProjectStatus(StrEnum):
    IMPORTED = "IMPORTED"
    MATCHING = "MATCHING"
    SELECTING = "SELECTING"
    READY = "READY"
    EXPORTED = "EXPORTED"
    SUBMITTED = "SUBMITTED"
    WON = "WON"
    LOST = "LOST"
    VOIDED = "VOIDED"


class BidImportStatus(StrEnum):
    PARSED = "PARSED"
    MAPPING_REQUIRED = "MAPPING_REQUIRED"
    FAILED = "FAILED"


class BidFileType(StrEnum):
    ORIGINAL = "ORIGINAL"
    QUOTED_EXPORT = "QUOTED_EXPORT"


class BidItemStatus(StrEnum):
    PENDING = "PENDING"
    NO_MATCH = "NO_MATCH"
    UNIQUE_MATCH = "UNIQUE_MATCH"
    MULTIPLE_MATCH = "MULTIPLE_MATCH"
    SELECTED = "SELECTED"
    NO_QUOTE = "NO_QUOTE"


_TRANSITIONS: dict[BidProjectStatus, set[BidProjectStatus]] = {
    BidProjectStatus.IMPORTED: {BidProjectStatus.MATCHING, BidProjectStatus.VOIDED},
    BidProjectStatus.MATCHING: {BidProjectStatus.SELECTING, BidProjectStatus.VOIDED},
    BidProjectStatus.SELECTING: {BidProjectStatus.READY, BidProjectStatus.VOIDED},
    BidProjectStatus.READY: {BidProjectStatus.EXPORTED, BidProjectStatus.VOIDED},
    BidProjectStatus.EXPORTED: {
        BidProjectStatus.READY,
        BidProjectStatus.SUBMITTED,
        BidProjectStatus.VOIDED,
    },
    BidProjectStatus.SUBMITTED: {BidProjectStatus.WON, BidProjectStatus.LOST},
    BidProjectStatus.WON: set(),
    BidProjectStatus.LOST: set(),
    BidProjectStatus.VOIDED: set(),
}


def ensure_transition(current: str, target: BidProjectStatus) -> None:
    try:
        current_status = BidProjectStatus(current)
    except ValueError as exc:
        raise AppError("BID_PROJECT_STATUS_INVALID", "项目状态无效", 409) from exc
    if target not in _TRANSITIONS[current_status]:
        raise AppError("BID_PROJECT_TRANSITION_INVALID", "项目状态不能这样变更", 409)
