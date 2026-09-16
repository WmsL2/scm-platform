from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import CurrentUser
from app.modules.dashboard.application.service import DashboardService
from app.modules.dashboard.schemas import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/summary", response_model=ApiResponse[DashboardSummaryResponse])
async def dashboard_summary(
    _: Annotated[CurrentUser, Depends(get_current_user)], session: SessionDep
) -> ApiResponse[DashboardSummaryResponse]:
    return success(await DashboardService(session).summary())
