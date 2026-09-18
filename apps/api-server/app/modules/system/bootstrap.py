"""One-time initial administrator provisioning for a new deployment."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.auth.security import hash_password
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole

INITIAL_ADMIN_ROLE_CODE = "boss"
INITIAL_ADMIN_ROLE_NAME = "系统管理员"


async def provision_initial_administrator(
    session: AsyncSession, *, username: str | None = None, password: str | None = None
) -> bool:
    """Create the configured initial administrator once; never restore a deleted account."""
    settings = get_settings()
    configured_username = username if username is not None else settings.initial_admin_username
    configured_password = (
        password
        if password is not None
        else (
            settings.initial_admin_password.get_secret_value()
            if settings.initial_admin_password is not None
            else None
        )
    )
    if configured_username is None and configured_password is None:
        return False
    if configured_username is None or configured_password is None:
        raise RuntimeError(
            "Initial administrator username and password must be configured together"
        )
    normalized_username = configured_username.strip()
    if not normalized_username or len(normalized_username) > 64:
        raise RuntimeError("Initial administrator username must be 1 to 64 characters")
    if len(configured_password) < 8:
        raise RuntimeError("Initial administrator password must be at least 8 characters")

    existing_user = await session.scalar(select(User).where(User.username == normalized_username))
    if existing_user is not None:
        return False

    role = await session.scalar(
        select(Role).where(Role.role_code == INITIAL_ADMIN_ROLE_CODE, Role.is_deleted.is_(False))
    )
    if role is None:
        role = Role(
            role_code=INITIAL_ADMIN_ROLE_CODE,
            role_name=INITIAL_ADMIN_ROLE_NAME,
            is_builtin=True,
        )
        session.add(role)
        await session.flush()

    administrator = User(
        username=normalized_username,
        password_hash=hash_password(configured_password),
        user_status="ENABLED",
    )
    session.add(administrator)
    await session.flush()
    session.add(UserRole(user_id=administrator.id, role_id=role.id, created_by=administrator.id))
    permissions = list(
        (await session.scalars(select(Permission).where(Permission.is_deleted.is_(False)))).all()
    )
    existing_permission_ids = set(
        (await session.scalars(
            select(RolePermission.permission_id).where(RolePermission.role_id == role.id)
        )).all()
    )
    session.add_all(
        [
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                created_by=administrator.id,
            )
            for permission in permissions
            if permission.id not in existing_permission_ids
        ]
    )
    return True
