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

    async def codes(self, user_id: uuid.UUID) -> tuple[list[str], list[str]]:
        roles = (
            await self.session.scalars(
                select(Role.role_code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id, Role.is_deleted.is_(False))
            )
        ).all()
        permissions = (
            await self.session.scalars(
                select(Permission.permission_code)
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
        return sorted(set(roles)), sorted(set(permissions))


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
