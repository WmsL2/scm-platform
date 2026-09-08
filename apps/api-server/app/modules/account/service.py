# ruff: noqa: E501
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncIterator

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams, PageResult
from app.modules.account.repository import AccountRepository
from app.modules.account.schemas import PermissionResponse, RoleResponse, UserResponse
from app.modules.auth.security import hash_password, verify_password
from app.modules.system.models import Role, User


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AccountRepository(session)

    async def register(self, username: str, password: str) -> UserResponse:
        normalized = username.strip()
        if not normalized or len(normalized) > 64:
            raise AppError("ACCOUNT_VALIDATION_ERROR", "username must be 1 to 64 characters", 422)
        try:
            async with self._transaction():
                if await self.repository.active_user_by_username(normalized):
                    raise AppError("ACCOUNT_USERNAME_EXISTS", "Username already exists", 409)
                user = User(
                    username=normalized,
                    password_hash=hash_password(password),
                    user_status="PENDING",
                )
                self.session.add(user)
                await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            if self._is_active_username_conflict(exc):
                raise AppError("ACCOUNT_USERNAME_EXISTS", "Username already exists", 409) from exc
            raise
        return self._user(user, [])

    async def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> None:
        async with self._transaction():
            user = await self.repository.active_user_for_update(user_id)
            if user is None:
                raise AppError("AUTH_UNAUTHORIZED", "Invalid access token", 401)
            if not verify_password(current_password, user.password_hash):
                raise AppError("AUTH_INVALID_CREDENTIALS", "Invalid credentials", 401)
            user.password_hash = hash_password(new_password)
            user.token_version += 1
            user.updated_by = user_id

    async def list_users(
        self, page: PageParams, pending_only: bool = False
    ) -> PageResult[UserResponse]:
        users, total = await self.repository.users(page, pending_only)
        items = [
            self._user(user, await self.repository.role_ids_for_user(user.id)) for user in users
        ]
        return PageResult(items=items, total=total, page=page.page, page_size=page.page_size)

    async def replace_user_roles(
        self, user_id: uuid.UUID, role_ids: list[uuid.UUID], actor: uuid.UUID
    ) -> UserResponse:
        async with self._transaction():
            user = await self.repository.active_user_for_update(user_id)
            if user is None:
                raise AppError("ACCOUNT_USER_NOT_FOUND", "User not found", 404)
            roles = await self.repository.active_roles(list(set(role_ids)))
            if len(roles) != len(set(role_ids)):
                raise AppError("ACCOUNT_ROLE_NOT_FOUND", "One or more roles do not exist", 404)
            await self.repository.replace_user_roles(user_id, role_ids, actor)
        return self._user(user, role_ids)

    async def roles(self) -> list[RoleResponse]:
        roles = await self.repository.roles()
        return [
            self._role(role, await self.repository.permission_ids_for_role(role.id))
            for role in roles
        ]

    async def replace_role_permissions(
        self, role_id: uuid.UUID, permission_ids: list[uuid.UUID], actor: uuid.UUID
    ) -> RoleResponse:
        async with self._transaction():
            role = await self.repository.active_role_for_update(role_id)
            if role is None:
                raise AppError("ACCOUNT_ROLE_NOT_FOUND", "Role not found", 404)
            permissions = await self.repository.active_permissions(list(set(permission_ids)))
            if len(permissions) != len(set(permission_ids)):
                raise AppError(
                    "ACCOUNT_PERMISSION_NOT_FOUND", "One or more permissions do not exist", 404
                )
            await self.repository.replace_role_permissions(role_id, permission_ids, actor)
        return self._role(role, permission_ids)

    async def permissions(self) -> list[PermissionResponse]:
        return [
            PermissionResponse(
                id=item.id,
                permission_code=item.permission_code,
                permission_name=item.permission_name,
                permission_type=item.permission_type,
            )
            for item in await self.repository.permissions()
        ]

    async def review(
        self, user_id: uuid.UUID, approve: bool, note: str | None, actor: uuid.UUID
    ) -> UserResponse:
        async with self._transaction():
            user = await self.repository.active_user_for_update(user_id)
            if user is None:
                raise AppError("ACCOUNT_USER_NOT_FOUND", "User not found", 404)
            if user.user_status != "PENDING":
                raise AppError("REGISTRATION_INVALID_STATE", "Registration is not pending", 409)
            user.user_status = "ENABLED" if approve else "REJECTED"
            user.reviewed_by = actor
            user.reviewed_at = datetime.now()
            user.review_note = note.strip() if note and note.strip() else None
            user.updated_by = actor
        return self._user(user, await self.repository.role_ids_for_user(user.id))

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[None]:
        if self.session.in_transaction():
            try:
                yield
            except Exception:
                await self.session.rollback()
                raise
            else:
                await self.session.commit()
        else:
            async with self.session.begin():
                yield

    @staticmethod
    def _user(user: User, role_ids: list[uuid.UUID]) -> UserResponse:
        return UserResponse(
            id=user.id,
            username=user.username,
            user_status=user.user_status,
            role_ids=role_ids,
            reviewed_by=user.reviewed_by,
            reviewed_at=user.reviewed_at,
            review_note=user.review_note,
        )

    @staticmethod
    def _role(role: Role, permission_ids: list[uuid.UUID]) -> RoleResponse:
        return RoleResponse(
            id=role.id,
            role_code=role.role_code,
            role_name=role.role_name,
            permission_ids=permission_ids,
        )

    @staticmethod
    def _is_active_username_conflict(exc: IntegrityError) -> bool:
        detail = str(exc.orig).lower()
        return "uq_sys_user_active_username" in detail or "active_username" in detail
