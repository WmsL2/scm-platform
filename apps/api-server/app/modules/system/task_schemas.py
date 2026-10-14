from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AsyncTaskKind(StrEnum):
    TYPE1_MATCH = "TYPE1_MATCH"
    TYPE2_MATCH = "TYPE2_MATCH"
    TYPE3_CANDIDATE_GENERATION = "TYPE3_CANDIDATE_GENERATION"
    TYPE4_RECOMMENDATION_AGENT = "TYPE4_RECOMMENDATION_AGENT"
    TYPE5_RECOMMENDATION_GENERATION = "TYPE5_RECOMMENDATION_GENERATION"
    TYPE5_PPT_GENERATION = "TYPE5_PPT_GENERATION"
    MAPPING_STRUCTURE_ANALYSIS = "MAPPING_STRUCTURE_ANALYSIS"


class AsyncTaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AsyncTaskResponse(BaseModel):
    id: UUID
    project_id: UUID
    run_id: UUID | None
    task_kind: AsyncTaskKind
    status: AsyncTaskStatus
    progress_percent: int = Field(ge=0, le=100)
    progress_message: str | None
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1)
    error_code: str | None
    error_message: str | None
    lease_expires_at: datetime | None
    heartbeat_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class AsyncTaskCreate(BaseModel):
    """Internal request, not accepted directly from an untrusted browser payload."""

    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    task_kind: AsyncTaskKind
    created_by: UUID
    run_id: UUID | None = None
    payload_json: dict[str, object] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=3)
