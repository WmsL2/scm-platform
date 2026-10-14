from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, AppError, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.bid.infrastructure.models import BidProject
from app.modules.matching.application.service import MatchingService
from app.modules.matching.schemas import (
    BidItemCandidateResponse,
    BidItemSelectionCreateRequest,
    BidItemSelectionResponse,
    NoQuoteCreateRequest,
)
from app.modules.system.task_schemas import AsyncTaskCreate, AsyncTaskKind, AsyncTaskResponse
from app.modules.system.task_service import AsyncTaskService

router = APIRouter(prefix="/bid-projects", tags=["bid-matching"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session, scope="function")]


@router.post(
    "/{project_id}/commands/start-matching",
    response_model=ApiResponse[AsyncTaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_matching(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("bid:match"))],
    session: SessionDep,
) -> ApiResponse[AsyncTaskResponse]:
    # The worker performs the domain validation and starts the legacy MatchTask;
    # creating this row is intentionally the only request-time write for matching.
    project = await session.get(BidProject, project_id)
    if project is None:
        raise AppError("BID_PROJECT_NOT_FOUND", "投标项目不存在", 404)
    kinds = {
        "TYPE_1_SPECIFICATION": AsyncTaskKind.TYPE1_MATCH,
        "TYPE_2_IDENTIFIED_PRODUCT": AsyncTaskKind.TYPE2_MATCH,
    }
    kind = kinds.get(project.recommendation_type or "")
    if kind is None:
        raise AppError("BID_MATCHING_TYPE_INVALID", "该项目不是类型 1 或类型 2 匹配项目", 409)
    await AsyncTaskService(session).ensure_available(project_id, kind)
    if project.import_status != "PARSED":
        raise AppError(
            "BID_PROJECT_NOT_PARSED", "请先人工确认客户需求字段映射，再开始匹配", 409
        )
    if project.status not in {
        "IMPORTED",
        "SELECTING",
        "READY",
    }:
        raise AppError("BID_MATCHING_NOT_ALLOWED", "当前项目状态不能开始匹配", 409)
    if project.output_mapping is not None and project.output_mapping_confirmed_at is None:
        raise AppError("BID_OUTPUT_MAPPING_NOT_CONFIRMED", "请先确认客户原表的回填字段映射", 409)
    task = await AsyncTaskService(session).enqueue(
        AsyncTaskCreate(project_id=project_id, task_kind=kind, created_by=current.user_id)
    )
    return success(task)


@router.get(
    "/{project_id}/items/{item_id}/candidates",
    response_model=ApiResponse[list[BidItemCandidateResponse]],
)
async def list_candidates(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
) -> ApiResponse[list[BidItemCandidateResponse]]:
    return success(await MatchingService(session).candidates(project_id, item_id))


@router.post(
    "/{project_id}/items/{item_id}/selections",
    response_model=ApiResponse[BidItemSelectionResponse],
)
async def select_candidate(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: BidItemSelectionCreateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:select"))],
    session: SessionDep,
) -> ApiResponse[BidItemSelectionResponse]:
    return success(
        await MatchingService(session).select(project_id, item_id, payload, current.user_id)
    )


@router.post(
    "/{project_id}/items/{item_id}/no-quote",
    response_model=ApiResponse[BidItemSelectionResponse],
)
async def mark_no_quote(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: NoQuoteCreateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:select"))],
    session: SessionDep,
) -> ApiResponse[BidItemSelectionResponse]:
    return success(
        await MatchingService(session).no_quote(project_id, item_id, payload, current.user_id)
    )
