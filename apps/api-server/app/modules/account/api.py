# ruff: noqa: E501
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, PageParams, PageResult, success
from app.core.database import get_db_session
from app.modules.account.schemas import (
    ChangePasswordRequest,
    PermissionResponse,
    RegisterRequest,
    ReviewRequest,
    RoleCreateRequest,
    RolePermissionsRequest,
    RoleResponse,
    UserResponse,
    UserRolesRequest,
)
from app.modules.account.service import AccountService
from app.modules.auth.dependencies import get_current_user, require_permission
from app.modules.auth.schemas import CurrentUser

auth_router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@auth_router.post("/register", response_model=ApiResponse[UserResponse])
async def register(
    payload: RegisterRequest, session: Annotated[AsyncSession, Depends(get_db_session)]
) -> ApiResponse[UserResponse]:
    return success(await AccountService(session).register(payload.username, payload.password))


@auth_router.post("/change-password", response_model=ApiResponse[dict[str, str]])
async def change_password(
    payload: ChangePasswordRequest,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[dict[str, str]]:
    await AccountService(session).change_password(
        current.user_id, payload.current_password, payload.new_password
    )
    return success({"status": "password_changed"})


@admin_router.get("/users", response_model=ApiResponse[PageResult[UserResponse]])
async def users(
    page: Annotated[PageParams, Depends()],
    _: Annotated[CurrentUser, Depends(require_permission("system:user:list"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageResult[UserResponse]]:
    return success(await AccountService(session).list_users(page))


@admin_router.put("/users/{user_id}/roles", response_model=ApiResponse[UserResponse])
async def user_roles(
    user_id: uuid.UUID,
    payload: UserRolesRequest,
    current: Annotated[CurrentUser, Depends(require_permission("system:user:role:update"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserResponse]:
    return success(
        await AccountService(session).replace_user_roles(user_id, payload.role_ids, current.user_id)
    )


@admin_router.get("/roles", response_model=ApiResponse[list[RoleResponse]])
async def roles(
    _: Annotated[CurrentUser, Depends(require_permission("system:role:list"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[RoleResponse]]:
    return success(await AccountService(session).roles())


@admin_router.post("/roles", response_model=ApiResponse[RoleResponse])
async def create_role(
    payload: RoleCreateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("system:role:create"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RoleResponse]:
    return success(
        await AccountService(session).create_role(payload.role_code, payload.role_name, current.user_id)
    )


@admin_router.put("/roles/{role_id}/permissions", response_model=ApiResponse[RoleResponse])
async def role_permissions(
    role_id: uuid.UUID,
    payload: RolePermissionsRequest,
    current: Annotated[CurrentUser, Depends(require_permission("system:role:permission:update"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[RoleResponse]:
    return success(
        await AccountService(session).replace_role_permissions(
            role_id, payload.permission_ids, current.user_id
        )
    )


@admin_router.get("/permissions", response_model=ApiResponse[list[PermissionResponse]])
async def permissions(
    _: Annotated[CurrentUser, Depends(require_permission("system:permission:list"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[list[PermissionResponse]]:
    return success(await AccountService(session).permissions())


@admin_router.get("/registration-requests", response_model=ApiResponse[PageResult[UserResponse]])
async def registrations(
    page: Annotated[PageParams, Depends()],
    _: Annotated[CurrentUser, Depends(require_permission("system:registration:list"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageResult[UserResponse]]:
    return success(await AccountService(session).list_users(page, pending_only=True))


@admin_router.get("/registration-history", response_model=ApiResponse[PageResult[UserResponse]])
async def registration_history(
    page: Annotated[PageParams, Depends()],
    _: Annotated[CurrentUser, Depends(require_permission("system:registration:list"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[PageResult[UserResponse]]:
    return success(await AccountService(session).list_registration_history(page))


@admin_router.post(
    "/registration-requests/{user_id}/commands/approve", response_model=ApiResponse[UserResponse]
)
async def approve(
    user_id: uuid.UUID,
    payload: ReviewRequest,
    current: Annotated[CurrentUser, Depends(require_permission("system:registration:review"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserResponse]:
    return success(
        await AccountService(session).review(user_id, True, payload.review_note, current.user_id)
    )


@admin_router.post(
    "/registration-requests/{user_id}/commands/reject", response_model=ApiResponse[UserResponse]
)
async def reject(
    user_id: uuid.UUID,
    payload: ReviewRequest,
    current: Annotated[CurrentUser, Depends(require_permission("system:registration:review"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiResponse[UserResponse]:
    return success(
        await AccountService(session).review(user_id, False, payload.review_note, current.user_id)
    )
