# ruff: noqa: E501
import uuid
from typing import cast

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.common.contracts import PageParams
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole


class AccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def active_user_by_username(self, username: str) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(
                select(User).where(User.username == username, User.is_deleted.is_(False))
            ),
        )

    async def active_user_for_update(self, user_id: uuid.UUID) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(
                select(User).where(User.id == user_id, User.is_deleted.is_(False)).with_for_update()
            ),
        )

    async def users(self, page: PageParams, pending_only: bool = False) -> tuple[list[User], int]:
        criteria: tuple[ColumnElement[bool], ...] = (User.is_deleted.is_(False),)
        if pending_only:
            criteria += (User.user_status == "PENDING",)
        statement = (
            select(User)
            .where(*criteria)
            .order_by(User.created_at.desc())
            .offset((page.page - 1) * page.page_size)
            .limit(page.page_size)
        )
        total = cast(
            int, await self.session.scalar(select(func.count()).select_from(User).where(*criteria))
        )
        return list((await self.session.scalars(statement)).all()), total

    async def reviewed_users(self, page: PageParams) -> tuple[list[User], int]:
        criteria: tuple[ColumnElement[bool], ...] = (
            User.is_deleted.is_(False),
            User.reviewed_at.is_not(None),
        )
        statement = (
            select(User)
            .where(*criteria)
            .order_by(User.reviewed_at.desc())
            .offset((page.page - 1) * page.page_size)
            .limit(page.page_size)
        )
        total = cast(
            int, await self.session.scalar(select(func.count()).select_from(User).where(*criteria))
        )
        return list((await self.session.scalars(statement)).all()), total

    async def active_roles(self, ids: list[uuid.UUID]) -> list[Role]:
        if not ids:
            return []
        return list(
            (
                await self.session.scalars(
                    select(Role).where(Role.id.in_(ids), Role.is_deleted.is_(False))
                )
            ).all()
        )

    async def active_role_by_code(self, role_code: str) -> Role | None:
        return cast(
            Role | None,
            await self.session.scalar(
                select(Role).where(Role.role_code == role_code, Role.is_deleted.is_(False))
            ),
        )

    async def active_role_by_name(self, role_name: str) -> Role | None:
        return cast(
            Role | None,
            await self.session.scalar(
                select(Role).where(Role.role_name == role_name, Role.is_deleted.is_(False))
            ),
        )

    async def active_permissions(self, ids: list[uuid.UUID]) -> list[Permission]:
        if not ids:
            return []
        return list(
            (
                await self.session.scalars(
                    select(Permission).where(
                        Permission.id.in_(ids), Permission.is_deleted.is_(False)
                    )
                )
            ).all()
        )

    async def roles(self) -> list[Role]:
        return list(
            (
                await self.session.scalars(
                    select(Role).where(Role.is_deleted.is_(False)).order_by(Role.role_code)
                )
            ).all()
        )

    async def permissions(self) -> list[Permission]:
        return list(
            (
                await self.session.scalars(
                    select(Permission)
                    .where(Permission.is_deleted.is_(False))
                    .order_by(Permission.permission_code)
                )
            ).all()
        )

    async def roles_for_user(self, user_id: uuid.UUID) -> list[Role]:
        return list(
            (
                await self.session.scalars(
                    select(Role)
                    .join(UserRole, UserRole.role_id == Role.id)
                    .where(UserRole.user_id == user_id, Role.is_deleted.is_(False))
                    .order_by(Role.role_code)
                )
            ).all()
        )

    async def permission_ids_for_role(self, role_id: uuid.UUID) -> list[uuid.UUID]:
        return list(
            (
                await self.session.scalars(
                    select(RolePermission.permission_id).where(RolePermission.role_id == role_id)
                )
            ).all()
        )

    async def permission_codes(self, ids: set[uuid.UUID]) -> set[str]:
        if not ids:
            return set()
        return set(
            (
                await self.session.scalars(
                    select(Permission.permission_code).where(
                        Permission.id.in_(ids), Permission.is_deleted.is_(False)
                    )
                )
            ).all()
        )

    async def active_role_for_update(self, role_id: uuid.UUID) -> Role | None:
        return cast(
            Role | None,
            await self.session.scalar(
                select(Role).where(Role.id == role_id, Role.is_deleted.is_(False)).with_for_update()
            ),
        )

    async def user_count_for_role(self, role_id: uuid.UUID) -> int:
        return cast(
            int,
            await self.session.scalar(
                select(func.count())
                .select_from(UserRole)
                .join(User, User.id == UserRole.user_id)
                .where(UserRole.role_id == role_id, User.is_deleted.is_(False))
            ),
        )

    async def replace_user_roles(
        self, user_id: uuid.UUID, role_ids: list[uuid.UUID], actor: uuid.UUID
    ) -> None:
        await self.session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        self.session.add_all(
            [UserRole(user_id=user_id, role_id=role_id, created_by=actor) for role_id in role_ids]
        )

    async def replace_role_permissions(
        self, role_id: uuid.UUID, permission_ids: list[uuid.UUID], actor: uuid.UUID
    ) -> None:
        await self.session.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        self.session.add_all(
            [
                RolePermission(role_id=role_id, permission_id=permission_id, created_by=actor)
                for permission_id in permission_ids
            ]
        )
