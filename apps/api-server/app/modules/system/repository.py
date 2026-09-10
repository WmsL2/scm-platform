import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.system.models import (
    BusinessSequence,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def active_by_username(self, username: str) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(
                select(User).where(User.username == username, User.is_deleted.is_(False))
            ),
        )

    async def active_by_id(self, user_id: uuid.UUID) -> User | None:
        return cast(
            User | None,
            await self.session.scalar(
                select(User).where(User.id == user_id, User.is_deleted.is_(False))
            ),
        )

    async def codes(
        self, user_id: uuid.UUID
    ) -> tuple[list[str], dict[str, str], list[str], dict[str, str]]:
        role_rows = (
            await self.session.execute(
                select(Role.role_code, Role.role_name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id, Role.is_deleted.is_(False))
            )
        ).all()
        role_names: dict[str, str] = {
            role_code: role_name for role_code, role_name in role_rows
        }
        permission_rows = (
            await self.session.execute(
                select(Permission.permission_code, Permission.permission_name)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == RolePermission.role_id)
                .where(
                    UserRole.user_id == user_id,
                    Role.is_deleted.is_(False),
                    Permission.is_deleted.is_(False),
                )
            )
        ).all()
        permission_names: dict[str, str] = {
            permission_code: permission_name
            for permission_code, permission_name in permission_rows
        }
        return sorted(role_names), role_names, sorted(permission_names), permission_names


class BusinessSequenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_key_for_update(self, sequence_key: str) -> BusinessSequence | None:
        return cast(
            BusinessSequence | None,
            await self.session.scalar(
                select(BusinessSequence)
                .where(BusinessSequence.sequence_key == sequence_key)
                .with_for_update()
            ),
        )
