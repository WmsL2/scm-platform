import uuid
from datetime import datetime
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, PageParams, PageResult, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.bid.application.service import BidProjectService
from app.modules.bid.domain.lifecycle import BidItemStatus, BidProjectStatus
from app.modules.bid.schemas import (
    BidProjectCreateResponse,
    BidProjectDetailResponse,
    BidProjectFileResponse,
    BidProjectItemResponse,
    BidProjectListItem,
    BidProjectStatusResponse,
    BidResultRequest,
    BidSubmitRequest,
)

router = APIRouter(prefix="/bid-projects", tags=["bid-projects"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=ApiResponse[BidProjectCreateResponse])
async def create_bid_project(
    file: Annotated[UploadFile, File(...)],
    project_name: Annotated[str, Form(min_length=1, max_length=255)],
    buyer_name: Annotated[str, Form(min_length=1, max_length=255)],
    current: Annotated[CurrentUser, Depends(require_permission("bid:create"))],
    session: SessionDep,
    deadline_at: Annotated[datetime | None, Form()] = None,
    remark: Annotated[str | None, Form(max_length=5000)] = None,
) -> ApiResponse[BidProjectCreateResponse]:
    return success(
        await BidProjectService(session).create(
            project_name=project_name,
            buyer_name=buyer_name,
            deadline_at=deadline_at,
            remark=remark,
            filename=file.filename or "投标文件.xlsx",
            file_bytes=await file.read(),
            actor_id=current.user_id,
        )
    )


@router.get("", response_model=ApiResponse[PageResult[BidProjectListItem]])
async def list_bid_projects(
    _: Annotated[CurrentUser, Depends(require_permission("bid:list"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    status: BidProjectStatus | None = None,
) -> ApiResponse[PageResult[BidProjectListItem]]:
    return success(
        await BidProjectService(session).list_projects(
            page_params,
            keyword=keyword,
            status=status,
        )
    )


@router.get("/{project_id}", response_model=ApiResponse[BidProjectDetailResponse])
async def get_bid_project(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
) -> ApiResponse[BidProjectDetailResponse]:
    return success(await BidProjectService(session).get(project_id))


@router.get("/{project_id}/items", response_model=ApiResponse[PageResult[BidProjectItemResponse]])
async def list_bid_project_items(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    status: BidItemStatus | None = None,
) -> ApiResponse[PageResult[BidProjectItemResponse]]:
    return success(await BidProjectService(session).items(project_id, page_params, status=status))


@router.get("/{project_id}/files", response_model=ApiResponse[list[BidProjectFileResponse]])
async def list_bid_project_files(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:detail"))],
    session: SessionDep,
) -> ApiResponse[list[BidProjectFileResponse]]:
    return success(await BidProjectService(session).files(project_id))


@router.get("/{project_id}/files/{file_id}/download")
async def download_bid_project_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("bid:file:download"))],
    session: SessionDep,
) -> StreamingResponse:
    file, content = await BidProjectService(session).download(project_id, file_id)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{file.original_filename}"'},
    )


@router.post("/{project_id}/exports", response_model=ApiResponse[BidProjectFileResponse])
async def export_bid_project(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("bid:export"))],
    session: SessionDep,
) -> ApiResponse[BidProjectFileResponse]:
    return success(await BidProjectService(session).export(project_id, current.user_id))


@router.post("/{project_id}/commands/submit", response_model=ApiResponse[BidProjectStatusResponse])
async def submit_bid_project(
    project_id: uuid.UUID,
    payload: BidSubmitRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:submit"))],
    session: SessionDep,
) -> ApiResponse[BidProjectStatusResponse]:
    return success(
        await BidProjectService(session).submit(
            project_id, payload.submitted_file_id, payload.note, current.user_id
        )
    )


@router.post("/{project_id}/commands/win", response_model=ApiResponse[BidProjectStatusResponse])
async def win_bid_project(
    project_id: uuid.UUID,
    payload: BidResultRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:result"))],
    session: SessionDep,
) -> ApiResponse[BidProjectStatusResponse]:
    return success(
        await BidProjectService(session).result(
            project_id, BidProjectStatus.WON, payload.note, current.user_id
        )
    )


@router.post("/{project_id}/commands/lose", response_model=ApiResponse[BidProjectStatusResponse])
async def lose_bid_project(
    project_id: uuid.UUID,
    payload: BidResultRequest,
    current: Annotated[CurrentUser, Depends(require_permission("bid:result"))],
    session: SessionDep,
) -> ApiResponse[BidProjectStatusResponse]:
    return success(
        await BidProjectService(session).result(
            project_id, BidProjectStatus.LOST, payload.note, current.user_id
        )
    )
