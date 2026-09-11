# ruff: noqa: E501
import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams, PageResult
from app.core.transaction import transaction_scope
from app.modules.account.repository import AccountRepository
from app.modules.account.schemas import PermissionResponse, RoleResponse, UserResponse
from app.modules.auth.security import hash_password, verify_password
from app.modules.auth.service import AuthSessionService
from app.modules.system.models import Role, User

ROLE_MANAGEMENT_PERMISSION_CODES = {
    "system:role:list",
    "system:permission:list",
    "system:role:permission:update",
}


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AccountRepository(session)

    async def register(self, username: str, password: str) -> UserResponse:
        normalized = username.strip()
        if not normalized or len(normalized) > 64:
            raise AppError("ACCOUNT_VALIDATION_ERROR", "username must be 1 to 64 characters", 422)
        async with transaction_scope(self.session):
            if await self.repository.active_user_by_username(normalized):
                raise AppError("ACCOUNT_USERNAME_EXISTS", "Username already exists", 409)
            try:
                async with self.session.begin_nested():
                    user = User(
                        username=normalized,
                        password_hash=hash_password(password),
                        user_status="PENDING",
                    )
                    self.session.add(user)
                    await self.session.flush()
            except IntegrityError as exc:
                if self._is_active_username_conflict(exc):
                    raise AppError("ACCOUNT_USERNAME_EXISTS", "Username already exists", 409) from exc
                raise
        return self._user(user, [])

    async def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> None:
        async with transaction_scope(self.session):
            user = await self.repository.active_user_for_update(user_id)
            if user is None:
                raise AppError("AUTH_UNAUTHORIZED", "Invalid access token", 401)
            if not verify_password(current_password, user.password_hash):
                raise AppError("AUTH_INVALID_CREDENTIALS", "Invalid credentials", 401)
            user.password_hash = hash_password(new_password)
            user.token_version += 1
            user.updated_by = user_id
            await AuthSessionService(self.session).revoke_all_for_user(
                user_id, "password_changed"
            )

    async def delete_user(self, user_id: uuid.UUID, actor: uuid.UUID) -> None:
        if user_id == actor:
            raise AppError(
                "ACCOUNT_USER_SELF_DELETE_FORBIDDEN",
                "不能删除当前登录账号，请使用其他管理员账号操作",
                409,
            )
        async with transaction_scope(self.session):
            user = await self.repository.active_user_for_update(user_id)
            if user is None:
                raise AppError("ACCOUNT_USER_NOT_FOUND", "User not found", 404)
            user.is_deleted = True
            user.deleted_by = actor
            user.deleted_at = datetime.now()
            user.updated_by = actor
            user.token_version += 1
            await AuthSessionService(self.session).revoke_all_for_user(
                user_id, "user_deleted"
            )

    async def list_users(
        self, page: PageParams, pending_only: bool = False
    ) -> PageResult[UserResponse]:
        users, total = await self.repository.users(page, pending_only)
        items = [
            self._user(user, await self.repository.roles_for_user(user.id)) for user in users
        ]
        return PageResult(items=items, total=total, page=page.page, page_size=page.page_size)

    async def list_registration_history(self, page: PageParams) -> PageResult[UserResponse]:
        users, total = await self.repository.reviewed_users(page)
        items = [
            self._user(user, await self.repository.roles_for_user(user.id)) for user in users
        ]
        return PageResult(items=items, total=total, page=page.page, page_size=page.page_size)

    async def replace_user_roles(
        self, user_id: uuid.UUID, role_ids: list[uuid.UUID], actor: uuid.UUID
    ) -> UserResponse:
        normalized_role_ids = list(dict.fromkeys(role_ids))
        async with transaction_scope(self.session):
            user = await self.repository.active_user_for_update(user_id)
            if user is None:
                raise AppError("ACCOUNT_USER_NOT_FOUND", "User not found", 404)
            if user.user_status != "ENABLED":
                raise AppError(
                    "ACCOUNT_USER_NOT_ENABLED", "Only enabled users can be assigned roles", 409
                )
            roles = await self.repository.active_roles(normalized_role_ids)
            if len(roles) != len(normalized_role_ids):
                raise AppError("ACCOUNT_ROLE_NOT_FOUND", "One or more roles do not exist", 404)
            await self.repository.replace_user_roles(user_id, normalized_role_ids, actor)
        return self._user(user, self._roles_in_requested_order(normalized_role_ids, roles))

    async def roles(self) -> list[RoleResponse]:
        roles = await self.repository.roles()
        return [
            self._role(role, await self.repository.permission_ids_for_role(role.id))
            for role in roles
        ]

    async def create_role(self, role_code: str, role_name: str, actor: uuid.UUID) -> RoleResponse:
        async with transaction_scope(self.session):
            if await self.repository.active_role_by_code(role_code):
                raise AppError("ACCOUNT_ROLE_CODE_EXISTS", "角色编码已存在", 409)
            if await self.repository.active_role_by_name(role_name):
                raise AppError("ACCOUNT_ROLE_NAME_EXISTS", "角色名称已存在", 409)
            try:
                async with self.session.begin_nested():
                    role = Role(
                        role_code=role_code,
                        role_name=role_name,
                        is_builtin=False,
                        is_deleted=False,
                        created_by=actor,
                        updated_by=actor,
                    )
                    self.session.add(role)
                    await self.session.flush()
            except IntegrityError as exc:
                if self._is_role_code_conflict(exc):
                    raise AppError("ACCOUNT_ROLE_CODE_EXISTS", "角色编码已存在", 409) from exc
                raise
        return self._role(role, [])

    async def delete_role(self, role_id: uuid.UUID, actor: uuid.UUID) -> None:
        async with transaction_scope(self.session):
            role = await self.repository.active_role_for_update(role_id)
            if role is None:
                raise AppError("ACCOUNT_ROLE_NOT_FOUND", "Role not found", 404)
            if role.is_builtin:
                raise AppError(
                    "ACCOUNT_BUILTIN_ROLE_DELETE_FORBIDDEN",
                    "Built-in roles cannot be deleted",
                    409,
                )
            if await self.repository.user_count_for_role(role_id):
                raise AppError(
                    "ACCOUNT_ROLE_ASSIGNED_DELETE_FORBIDDEN",
                    "Remove this role from all users before deleting it",
                    409,
                )
            role.is_deleted = True
            role.updated_by = actor

    async def replace_role_permissions(
        self, role_id: uuid.UUID, permission_ids: list[uuid.UUID], actor: uuid.UUID
    ) -> RoleResponse:
        normalized_permission_ids = list(dict.fromkeys(permission_ids))
        async with transaction_scope(self.session):
            role = await self.repository.active_role_for_update(role_id)
            if role is None:
                raise AppError("ACCOUNT_ROLE_NOT_FOUND", "Role not found", 404)
            permissions = await self.repository.active_permissions(normalized_permission_ids)
            if len(permissions) != len(normalized_permission_ids):
                raise AppError(
                    "ACCOUNT_PERMISSION_NOT_FOUND", "One or more permissions do not exist", 404
                )
            await self._ensure_actor_keeps_role_management_access(
                actor, role_id, set(normalized_permission_ids)
            )
            await self.repository.replace_role_permissions(role_id, normalized_permission_ids, actor)
        return self._role(role, normalized_permission_ids)

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
        async with transaction_scope(self.session):
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
            roles = await self.repository.roles_for_user(user.id)
        return self._user(user, roles)

    @staticmethod
    def _user(user: User, roles: list[Role]) -> UserResponse:
        return UserResponse(
            id=user.id,
            username=user.username,
            user_status=user.user_status,
            role_ids=[role.id for role in roles],
            role_names=[role.role_name for role in roles],
            reviewed_by=user.reviewed_by,
            reviewed_at=user.reviewed_at,
            review_note=user.review_note,
        )

    @staticmethod
    def _roles_in_requested_order(role_ids: list[uuid.UUID], roles: list[Role]) -> list[Role]:
        roles_by_id = {role.id: role for role in roles}
        return [roles_by_id[role_id] for role_id in role_ids]

    @staticmethod
    def _role(role: Role, permission_ids: list[uuid.UUID]) -> RoleResponse:
        return RoleResponse(
            id=role.id,
            role_code=role.role_code,
            role_name=role.role_name,
            is_builtin=role.is_builtin,
            permission_ids=permission_ids,
        )

    async def _ensure_actor_keeps_role_management_access(
        self, actor: uuid.UUID, role_id: uuid.UUID, replacement_permission_ids: set[uuid.UUID]
    ) -> None:
        actor_roles = await self.repository.roles_for_user(actor)
        if not any(role.id == role_id for role in actor_roles):
            return
        effective_permission_ids: set[uuid.UUID] = set()
        for actor_role in actor_roles:
            if actor_role.id == role_id:
                effective_permission_ids.update(replacement_permission_ids)
            else:
                effective_permission_ids.update(
                    await self.repository.permission_ids_for_role(actor_role.id)
                )
        effective_codes = await self.repository.permission_codes(effective_permission_ids)
        if not ROLE_MANAGEMENT_PERMISSION_CODES.issubset(effective_codes):
            raise AppError(
                "ACCOUNT_ROLE_MANAGEMENT_SELF_LOCKOUT",
                "不能移除当前账号的角色管理必要权限，请先由其他管理员接管",
                409,
            )

    @staticmethod
    def _is_active_username_conflict(exc: IntegrityError) -> bool:
        detail = str(exc.orig).lower()
        return "uq_sys_user_active_username" in detail or "active_username" in detail

    @staticmethod
    def _is_role_code_conflict(exc: IntegrityError) -> bool:
        detail = str(exc.orig).lower()
        return "role_code" in detail
