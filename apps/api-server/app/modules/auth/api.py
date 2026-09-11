from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, AppError, ErrorResponse, success
from app.core.config import get_settings
from app.core.database import get_db_session
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import CurrentUser, LoginRequest, TokenResponse
from app.modules.auth.security import decode_token, verify_password
from app.modules.auth.service import AuthSessionService
from app.modules.system.repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_NAME = "scm_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.auth_session_absolute_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.use_secure_refresh_cookie,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=get_settings().use_secure_refresh_cookie,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[TokenResponse]:
    user = await UserRepository(session).active_by_username(payload.username)
    if (
        user is None
        or user.user_status != "ENABLED"
        or not verify_password(payload.password, user.password_hash)
    ):
        raise AppError("AUTH_INVALID_CREDENTIALS", "Invalid credentials", 401)
    issued = await AuthSessionService(session).create(user)
    set_refresh_cookie(response, issued.refresh_token)
    settings = get_settings()
    return success(
        TokenResponse(
            access_token=issued.access_token,
            expires_in=settings.auth_access_token_minutes * 60,
        )
    )


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    responses={401: {"model": ErrorResponse}},
)
async def refresh(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[TokenResponse] | JSONResponse:
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    issued = (
        await AuthSessionService(session).rotate(refresh_token)
        if refresh_token is not None
        else None
    )
    if issued is None:
        error_response = JSONResponse(
            status_code=401,
            content=ErrorResponse(
                code="AUTH_REFRESH_INVALID",
                message="Login session has expired",
                request_id=getattr(request.state, "request_id", None),
            ).model_dump(),
        )
        clear_refresh_cookie(error_response)
        return error_response
    set_refresh_cookie(response, issued.refresh_token)
    settings = get_settings()
    return success(
        TokenResponse(
            access_token=issued.access_token,
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
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, str]]:
    authorization = request.headers.get("Authorization", "")
    scheme, _, access_token = authorization.partition(" ")
    if scheme.lower() == "bearer" and access_token:
        try:
            _, _, access_session_id = decode_token(access_token)
        except Exception:
            access_session_id = None
        if access_session_id is not None:
            await AuthSessionService(session).revoke_by_session_id(
                access_session_id, "logout"
            )
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh_token is not None:
        await AuthSessionService(session).revoke_by_refresh_token(
            refresh_token, "logout"
        )
    clear_refresh_cookie(response)
    return success({"status": "logged_out"})
