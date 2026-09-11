import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.auth.models import AuthSession
from app.modules.auth.repository import AuthSessionRepository
from app.modules.auth.security import (
    create_refresh_token,
    create_token,
    hash_refresh_token,
    parse_refresh_token,
    refresh_token_matches,
)
from app.modules.system.models import User
from app.modules.system.repository import UserRepository


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str


class AuthSessionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AuthSessionRepository(session)

    async def create(self, user: User) -> IssuedTokens:
        settings = get_settings()
        now = utc_now()
        session_id = uuid.uuid4()
        refresh_token = create_refresh_token(session_id)
        auth_session = AuthSession(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            last_activity_at=now,
            idle_expires_at=now + timedelta(days=settings.auth_refresh_idle_days),
            absolute_expires_at=now + timedelta(days=settings.auth_session_absolute_days),
        )
        self.session.add(auth_session)
        await self.session.flush()
        return IssuedTokens(
            access_token=create_token(user.id, user.token_version, session_id),
            refresh_token=refresh_token,
        )

    async def rotate(self, refresh_token: str) -> IssuedTokens | None:
        try:
            session_id = parse_refresh_token(refresh_token)
        except (ValueError, TypeError):
            return None

        auth_session = await self.repository.by_id_for_update(session_id)
        if auth_session is None:
            return None

        now = utc_now()
        if auth_session.revoked_at is not None:
            return None
        if now >= auth_session.absolute_expires_at:
            self._revoke(auth_session, now, "absolute_expired")
            return None
        if now >= auth_session.idle_expires_at:
            self._revoke(auth_session, now, "idle_expired")
            return None
        matches_current = refresh_token_matches(
            refresh_token, auth_session.refresh_token_hash
        )
        matches_previous_in_grace = (
            auth_session.previous_refresh_token_hash is not None
            and auth_session.previous_token_valid_until is not None
            and now < auth_session.previous_token_valid_until
            and refresh_token_matches(
                refresh_token, auth_session.previous_refresh_token_hash
            )
        )
        if not matches_current and not matches_previous_in_grace:
            self._revoke(auth_session, now, "refresh_token_reuse")
            return None

        user = await UserRepository(self.session).active_by_id(auth_session.user_id)
        if user is None or user.user_status != "ENABLED":
            self._revoke(auth_session, now, "user_unavailable")
            return None

        settings = get_settings()
        rotated_refresh_token = create_refresh_token(auth_session.id)
        auth_session.previous_refresh_token_hash = auth_session.refresh_token_hash
        auth_session.previous_token_valid_until = now + timedelta(
            seconds=settings.auth_refresh_rotation_grace_seconds
        )
        auth_session.refresh_token_hash = hash_refresh_token(rotated_refresh_token)
        auth_session.rotation_counter += 1
        auth_session.last_activity_at = now
        auth_session.idle_expires_at = min(
            now + timedelta(days=settings.auth_refresh_idle_days),
            auth_session.absolute_expires_at,
        )
        return IssuedTokens(
            access_token=create_token(user.id, user.token_version, auth_session.id),
            refresh_token=rotated_refresh_token,
        )

    async def revoke_by_refresh_token(self, refresh_token: str, reason: str) -> None:
        try:
            session_id = parse_refresh_token(refresh_token)
        except (ValueError, TypeError):
            return
        auth_session = await self.repository.by_id_for_update(session_id)
        if auth_session is None or auth_session.revoked_at is not None:
            return
        now = utc_now()
        matches_current = refresh_token_matches(
            refresh_token, auth_session.refresh_token_hash
        )
        matches_previous_in_grace = (
            auth_session.previous_refresh_token_hash is not None
            and auth_session.previous_token_valid_until is not None
            and now < auth_session.previous_token_valid_until
            and refresh_token_matches(
                refresh_token, auth_session.previous_refresh_token_hash
            )
        )
        if matches_current or matches_previous_in_grace:
            self._revoke(auth_session, now, reason)

    async def revoke_by_session_id(self, session_id: uuid.UUID, reason: str) -> None:
        auth_session = await self.repository.by_id_for_update(session_id)
        if auth_session is not None and auth_session.revoked_at is None:
            self._revoke(auth_session, utc_now(), reason)

    async def revoke_all_for_user(self, user_id: uuid.UUID, reason: str) -> None:
        await self.repository.revoke_all_for_user(user_id, reason, utc_now())

    @staticmethod
    def is_active(auth_session: AuthSession, now: datetime | None = None) -> bool:
        current = now or utc_now()
        return (
            auth_session.revoked_at is None
            and current < auth_session.idle_expires_at
            and current < auth_session.absolute_expires_at
        )

    @staticmethod
    def _revoke(auth_session: AuthSession, now: datetime, reason: str) -> None:
        auth_session.revoked_at = now
        auth_session.revoked_reason = reason
