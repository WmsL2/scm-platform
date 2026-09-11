import uuid
from datetime import datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AuthSession


class AuthSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_id(self, session_id: uuid.UUID) -> AuthSession | None:
        return cast(AuthSession | None, await self.session.get(AuthSession, session_id))

    async def by_id_for_update(self, session_id: uuid.UUID) -> AuthSession | None:
        return cast(
            AuthSession | None,
            await self.session.scalar(
                select(AuthSession)
                .where(AuthSession.id == session_id)
                .with_for_update()
            ),
        )

    async def revoke_all_for_user(
        self,
        user_id: uuid.UUID,
        reason: str,
        revoked_at: datetime,
    ) -> None:
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=revoked_at, revoked_reason=reason)
        )
