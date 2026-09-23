from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.recommendation.application.service import RecommendationService
from app.modules.recommendation.schemas import (
    ConfirmationUpdateRequest,
    RecommendationCandidateResponse,
    RecommendationConfirmationResponse,
    RecommendationRunResponse,
)

router = APIRouter(prefix="/recommendation-projects", tags=["free-recommendation"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("/{project_id}/runs", response_model=ApiResponse[RecommendationRunResponse])
async def create_run(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("recommendation:run"))],
    session: SessionDep,
) -> ApiResponse[RecommendationRunResponse]:
    """Create a queued run only; C's AgentRunner starts AI processing separately."""
    return success(await RecommendationService(session).create_run(project_id, current.user_id))


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
