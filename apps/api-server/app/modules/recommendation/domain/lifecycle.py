from __future__ import annotations

from app.common.contracts import AppError
from app.modules.recommendation.template.schemas import RecommendationRunStatus

_TRANSITIONS: dict[RecommendationRunStatus, set[RecommendationRunStatus]] = {
    RecommendationRunStatus.DRAFT: {
        RecommendationRunStatus.QUEUED,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.QUEUED: {
        RecommendationRunStatus.ANALYZING,
        RecommendationRunStatus.FAILED,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.ANALYZING: {
        RecommendationRunStatus.RETRIEVING,
        RecommendationRunStatus.NEEDS_INPUT,
        RecommendationRunStatus.FAILED,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.RETRIEVING: {
        RecommendationRunStatus.RANKING,
        RecommendationRunStatus.NO_CANDIDATES,
        RecommendationRunStatus.FAILED,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.RANKING: {
        RecommendationRunStatus.CANDIDATES_READY,
        RecommendationRunStatus.NO_CANDIDATES,
        RecommendationRunStatus.FAILED,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.CANDIDATES_READY: {
        RecommendationRunStatus.WAITING_CONFIRMATION,
        RecommendationRunStatus.CONFIRMED,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.WAITING_CONFIRMATION: {
        RecommendationRunStatus.CONFIRMED,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.CONFIRMED: {
        RecommendationRunStatus.EXPORTED,
        RecommendationRunStatus.WAITING_CONFIRMATION,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.EXPORTED: {RecommendationRunStatus.WAITING_CONFIRMATION},
    RecommendationRunStatus.FAILED: set(),
    RecommendationRunStatus.NO_CANDIDATES: set(),
    RecommendationRunStatus.NEEDS_INPUT: {
        RecommendationRunStatus.QUEUED,
        RecommendationRunStatus.CANCELLED,
    },
    RecommendationRunStatus.CANCELLED: set(),
}


def ensure_transition(current: str, target: RecommendationRunStatus) -> None:
    try:
        current_status = RecommendationRunStatus(current)
    except ValueError as exc:
        raise AppError("RECOMMENDATION_RUN_STATUS_INVALID", "推品任务状态无效", 409) from exc
    if target not in _TRANSITIONS[current_status]:
        raise AppError("RECOMMENDATION_RUN_TRANSITION_INVALID", "推品任务状态不能这样变更", 409)
