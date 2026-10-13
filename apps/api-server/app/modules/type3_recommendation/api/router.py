# ruff: noqa: E501
from __future__ import annotations

import uuid
from io import BytesIO
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, PageParams, success
from app.core.database import FunctionSessionDep, SessionLocal, get_db_session
from app.modules.auth.dependencies import require_permission, require_permission_before_response
from app.modules.auth.schemas import CurrentUser
from app.modules.bid.schemas import BidProjectFileResponse
from app.modules.type3_recommendation.application.agent import execute_type3_agent_inline
from app.modules.type3_recommendation.application.service import Type3RecommendationService
from app.modules.type3_recommendation.schemas import (
    Type3CandidatePage,
    Type3RunResponse,
    Type3SheetPreview,
    Type3SheetSelectionRequest,
    Type3TemplatePreview,
)

router = APIRouter(prefix="/type3-recommendation-projects", tags=["type3-recommendation"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/{project_id}/template-preview", response_model=ApiResponse[Type3TemplatePreview])
async def template_preview(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[Type3TemplatePreview]:
    return success(await Type3RecommendationService(session).preview(project_id))


@router.get(
    "/{project_id}/sheet-selections", response_model=ApiResponse[list[Type3SheetPreview]]
)
async def saved_sheet_selections(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[Type3SheetPreview]]:
    return success(await Type3RecommendationService(session).saved_sheet_selections(project_id))


@router.put(
    "/{project_id}/sheet-selections", response_model=ApiResponse[list[Type3SheetPreview]]
)
async def save_sheet_selections(
    project_id: uuid.UUID,
    payload: Type3SheetSelectionRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:create"))],
    session: SessionDep,
) -> ApiResponse[list[Type3SheetPreview]]:
    return success(
        await Type3RecommendationService(session).save_sheet_selection(
            project_id, payload, current.user_id
        )
    )


@router.post("/{project_id}/runs", response_model=ApiResponse[Type3RunResponse])
async def start(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:run"))],
) -> ApiResponse[Type3RunResponse]:
    # The run must commit before the inline AI work starts.  The executor then owns a
    # separate transaction so a candidate-persistence failure can safely mark this Run FAILED.
    async with SessionLocal() as create_session:
        run = await Type3RecommendationService(create_session).start(project_id, current.user_id)
    async with SessionLocal() as execution_session:
        await execute_type3_agent_inline(
            run.id, Type3RecommendationService(execution_session)
        )
    async with SessionLocal() as result_session:
        return success(await Type3RecommendationService(result_session).get_run(run.id))


@router.get("/{project_id}/runs", response_model=ApiResponse[list[Type3RunResponse]])
async def runs(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[Type3RunResponse]]:
    return success(await Type3RecommendationService(session).list_runs(project_id))


@router.get("/runs/{run_id}", response_model=ApiResponse[Type3RunResponse])
async def run(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[Type3RunResponse]:
    return success(await Type3RecommendationService(session).get_run(run_id))


@router.get("/runs/{run_id}/candidates", response_model=ApiResponse[Type3CandidatePage])
async def candidates(
    run_id: uuid.UUID,
    page: Annotated[PageParams, Depends()],
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
    sheet_name: str | None = None,
) -> ApiResponse[Type3CandidatePage]:
    return success(await Type3RecommendationService(session).candidates(run_id, sheet_name, page))


@router.post("/candidates/confirm", response_model=ApiResponse[bool])
async def confirm(
    candidate_ids: list[uuid.UUID],
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[bool]:
    await Type3RecommendationService(session).confirm(candidate_ids, current.user_id)
    return success(True)


@router.post(
    "/{project_id}/runs/{run_id}/commands/complete-selection",
    response_model=ApiResponse[bool],
)
async def complete_selection(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[bool]:
    await Type3RecommendationService(session).complete_selection(project_id, run_id, current.user_id)
    return success(True)


@router.post(
    "/{project_id}/runs/{run_id}/exports", response_model=ApiResponse[BidProjectFileResponse]
)
async def export(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    current: Annotated[
        CurrentUser, Depends(require_permission_before_response("recommendation:export"))
    ],
    session: FunctionSessionDep,
) -> ApiResponse[BidProjectFileResponse]:
    return success(
        await Type3RecommendationService(session).export(project_id, run_id, current.user_id)
    )


@router.get("/runs/{run_id}/exports/{file_id}/download")
async def download(
    run_id: uuid.UUID,
    file_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:export"))],
    session: SessionDep,
) -> StreamingResponse:
    file, content = await Type3RecommendationService(session).download(run_id, file_id)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"type3-export.xlsx\"; filename*=UTF-8''{quote(file.original_filename, safe='')}"
        },
    )
