from __future__ import annotations

import uuid
from io import BytesIO
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, success
from app.core.database import FunctionSessionDep, get_db_session
from app.jobs.recommendation_agent import execute_recommendation_agent_inline
from app.modules.auth.dependencies import require_permission, require_permission_before_response
from app.modules.auth.schemas import CurrentUser
from app.modules.bid.schemas import BidProjectFileResponse
from app.modules.recommendation.application.export_service import RecommendationExportService
from app.modules.recommendation.application.service import RecommendationService
from app.modules.recommendation.schemas import (
    BatchConfirmationRequest,
    ConfirmationUpdateRequest,
    RecommendationCandidateResponse,
    RecommendationConfirmationResponse,
    RecommendationRunResponse,
)

router = APIRouter(prefix="/recommendation-projects", tags=["free-recommendation"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def _attachment_headers(filename: str) -> dict[str, str]:
    """Return an ASCII-safe RFC 5987 attachment header for Chinese filenames."""
    return {
        "Content-Disposition": (
            'attachment; filename="recommendation-export.xlsx"; '
            f"filename*=UTF-8''{quote(filename, safe='')}"
        )
    }


@router.post("/{project_id}/runs", response_model=ApiResponse[RecommendationRunResponse])
async def create_run(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:run"))],
    session: SessionDep,
) -> ApiResponse[RecommendationRunResponse]:
    service = RecommendationService(session)
    run = await service.create_run(project_id, current.user_id)
    await execute_recommendation_agent_inline(run.id, session)
    return success(await service.get_run(run.id))


@router.get("/{project_id}/runs", response_model=ApiResponse[list[RecommendationRunResponse]])
async def list_runs(
    project_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[RecommendationRunResponse]]:
    return success(await RecommendationService(session).list_runs(project_id))


@router.get("/runs/{run_id}", response_model=ApiResponse[RecommendationRunResponse])
async def get_run(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[RecommendationRunResponse]:
    return success(await RecommendationService(session).get_run(run_id))


@router.get(
    "/runs/{run_id}/candidates", response_model=ApiResponse[list[RecommendationCandidateResponse]]
)
async def list_candidates(
    run_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:detail"))],
    session: SessionDep,
) -> ApiResponse[list[RecommendationCandidateResponse]]:
    return success(await RecommendationService(session).list_candidates(run_id))


@router.patch(
    "/candidates/{candidate_id}/confirmation",
    response_model=ApiResponse[RecommendationConfirmationResponse],
)
async def confirm_candidate(
    candidate_id: uuid.UUID,
    payload: ConfirmationUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[RecommendationConfirmationResponse]:
    return success(
        await RecommendationService(session).confirm_candidate(
            candidate_id, payload, current.user_id
        )
    )


@router.post(
    "/runs/{run_id}/confirmations",
    response_model=ApiResponse[list[RecommendationConfirmationResponse]],
)
async def confirm_candidates(
    run_id: uuid.UUID,
    payload: BatchConfirmationRequest,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:review"))],
    session: SessionDep,
) -> ApiResponse[list[RecommendationConfirmationResponse]]:
    return success(
        await RecommendationService(session).confirm_candidates(run_id, payload, current.user_id)
    )


@router.post(
    "/{project_id}/runs/{run_id}/exports", response_model=ApiResponse[BidProjectFileResponse]
)
async def export_confirmed_candidates(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    current: Annotated[
        CurrentUser, Depends(require_permission_before_response("recommendation:export"))
    ],
    session: FunctionSessionDep,
) -> ApiResponse[BidProjectFileResponse]:
    file = await RecommendationExportService(session).export(project_id, run_id, current.user_id)
    return success(file)


@router.get("/runs/{run_id}/exports/{file_id}/download")
async def download_export(
    run_id: uuid.UUID,
    file_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("recommendation:export"))],
    session: SessionDep,
) -> StreamingResponse:
    file, content = await RecommendationExportService(session).download_export(run_id, file_id)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_attachment_headers(file.original_filename),
    )
