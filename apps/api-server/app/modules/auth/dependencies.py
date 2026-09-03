from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.core.database import get_db_session
from app.modules.auth.schemas import CurrentUser
from app.modules.auth.security import decode_token
from app.modules.system.repository import UserRepository

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUser:
    if credentials is None:
        raise AppError("AUTH_UNAUTHORIZED", "Authentication required", 401)
    try:
        user_id, version = decode_token(credentials.credentials)
    except Exception as exc:
        raise AppError("AUTH_UNAUTHORIZED", "Invalid access token", 401) from exc
    repo = UserRepository(session)
    user = await repo.active_by_id(user_id)
    if user is None or user.user_status != "ENABLED" or user.token_version != version:
        raise AppError("AUTH_UNAUTHORIZED", "Invalid access token", 401)
    roles, permissions = await repo.codes(user.id)
    return CurrentUser(
        user_id=user.id, username=user.username, roles=roles, permissions=permissions
    )


def require_permission(permission_code: str) -> Callable[..., object]:
    async def dependency(current: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if permission_code not in current.permissions:
            raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)
        return current

    return dependency
