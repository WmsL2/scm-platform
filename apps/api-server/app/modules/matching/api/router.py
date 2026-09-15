from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.matching.application.service import MatchingService
from app.modules.matching.schemas import (
    BidItemCandidateResponse,
    BidItemSelectionCreateRequest,
    BidItemSelectionResponse,
    NoQuoteCreateRequest,
    StartMatchingResponse,
)

router = APIRouter(prefix="/bid-projects", tags=["bid-matching"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "/{project_id}/commands/start-matching", response_model=ApiResponse[StartMatchingResponse]
)
async def start_matching(
    project_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("bid:match"))],
    session: SessionDep,
) -> ApiResponse[StartMatchingResponse]:
    return success(await MatchingService(session).start(project_id, current.user_id))


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
