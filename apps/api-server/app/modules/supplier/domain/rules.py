from enum import StrEnum

from app.common.contracts import AppError


class ArchiveStatus(StrEnum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ARCHIVED = "ARCHIVED"


class CooperationStatus(StrEnum):
    NORMAL = "NORMAL"
    STOPPED = "STOPPED"
    BLACKLIST = "BLACKLIST"


def assert_archive_transition(current: str, target: ArchiveStatus) -> None:
    if (current, target) not in {
        (ArchiveStatus.DRAFT, ArchiveStatus.PENDING),
        (ArchiveStatus.PENDING, ArchiveStatus.ARCHIVED),
    }:
        raise AppError(
            "SUPPLIER_ARCHIVE_TRANSITION_NOT_ALLOWED",
            f"Cannot change archive status from {current} to {target}",
            409,
        )


def assert_cooperation_transition(current: str, target: CooperationStatus) -> None:
    if current != CooperationStatus.NORMAL or target not in {
        CooperationStatus.STOPPED,
        CooperationStatus.BLACKLIST,
    }:
        raise AppError(
            "SUPPLIER_COOPERATION_TRANSITION_NOT_ALLOWED",
            f"Cannot change cooperation status from {current} to {target}",
            409,
        )


def normalize_reason(reason: str) -> str:
    normalized = reason.strip()
    if not normalized:
        raise AppError("SUPPLIER_REASON_REQUIRED", "A non-blank reason is required", 422)
    return normalized
