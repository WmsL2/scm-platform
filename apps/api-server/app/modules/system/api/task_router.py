from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, AppError, PageParams, PageResult, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import CurrentUser
from app.modules.bid.infrastructure.models import BidProject
from app.modules.system.task_schemas import AsyncTaskResponse
from app.modules.system.task_service import AsyncTaskService

router = APIRouter(prefix="/bid-projects", tags=["async-tasks"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session, scope="function")]


def _can_read(current: CurrentUser) -> None:
    if not (
        {"bid:detail", "recommendation:detail", "recommendation:create"} & set(current.permissions)
    ):
        raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)


async def _can_operate(
    current: CurrentUser, task: AsyncTaskResponse, session: AsyncSession
) -> None:
    if task.task_kind.value == "MAPPING_STRUCTURE_ANALYSIS":
        project = await session.get(BidProject, task.project_id)
        permission = (
            "bid:update"
            if project and project.project_type == "FILTER_RECOMMENDATION"
            else "recommendation:create"
        )
        if permission not in current.permissions:
            raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)
        return
    permission = (
        "bid:match"
        if task.task_kind.value in {"TYPE1_MATCH", "TYPE2_MATCH"}
        else "recommendation:export"
        if task.task_kind.value == "TYPE5_PPT_GENERATION"
        else "recommendation:run"
    )
    if permission not in current.permissions:
        raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)


@router.get("/{project_id}/async-tasks", response_model=ApiResponse[PageResult[AsyncTaskResponse]])
async def list_tasks(
    project_id: uuid.UUID,
    page: Annotated[PageParams, Depends()],
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: SessionDep,
) -> ApiResponse[PageResult[AsyncTaskResponse]]:
    _can_read(current)
    items, total = await AsyncTaskService(session).list_for_project(project_id, page)
    return success(PageResult(items=items, total=total, page=page.page, page_size=page.page_size))


@router.get("/async-tasks/{task_id}", response_model=ApiResponse[AsyncTaskResponse])
async def get_task(
    task_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: SessionDep,
) -> ApiResponse[AsyncTaskResponse]:
    _can_read(current)
    return success(await AsyncTaskService(session).get(task_id))


@router.post(
    "/async-tasks/{task_id}/commands/cancel", response_model=ApiResponse[AsyncTaskResponse]
)
async def cancel_task(
    task_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: SessionDep,
) -> ApiResponse[AsyncTaskResponse]:
    service = AsyncTaskService(session)
    await _can_operate(current, await service.get(task_id), session)
    return success(await service.cancel(task_id))


@router.post("/async-tasks/{task_id}/commands/retry", response_model=ApiResponse[AsyncTaskResponse])
async def retry_task(
    task_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: SessionDep,
) -> ApiResponse[AsyncTaskResponse]:
    service = AsyncTaskService(session)
    await _can_operate(current, await service.get(task_id), session)
    return success(await service.retry(task_id))
