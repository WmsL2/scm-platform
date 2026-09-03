from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, AppError, success
from app.core.config import get_settings
from app.core.database import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import CurrentUser, LoginRequest, TokenResponse
from app.modules.auth.security import create_token, verify_password
from app.modules.system.repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    payload: LoginRequest, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> ApiResponse[TokenResponse]:
    user = await UserRepository(session).active_by_username(payload.username)
    if (
        user is None
        or user.user_status != "ENABLED"
        or not verify_password(payload.password, user.password_hash)
    ):
        raise AppError("AUTH_INVALID_CREDENTIALS", "Invalid credentials", 401)
    settings = get_settings()
    return success(
        TokenResponse(
            access_token=create_token(user.id, user.token_version),
            expires_in=settings.auth_access_token_minutes * 60,
        )
    )


@router.get("/me", response_model=ApiResponse[CurrentUser])
async def me(
    current: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[CurrentUser]:
    return success(current)


@router.post("/logout", response_model=ApiResponse[dict[str, str]])
async def logout(
    current: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[dict[str, str]]:
    del current
    return success({"status": "logged_out"})
