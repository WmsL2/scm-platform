import uuid

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.modules.auth.security import verify_password
from app.modules.system.bootstrap import INITIAL_ADMIN_ROLE_CODE, provision_initial_administrator
from app.modules.system.models import Permission, Role, RolePermission, User, UserRole


async def test_initial_administrator_is_created_once_and_not_restored_after_deletion() -> None:
    username = f"initial-admin-{uuid.uuid4()}"
    user_id: uuid.UUID | None = None
    boss_preexisting = False
    try:
        async with SessionLocal() as session:
            boss_preexisting = await session.scalar(
                select(Role.id).where(Role.role_code == INITIAL_ADMIN_ROLE_CODE)
            ) is not None
        async with SessionLocal() as session:
            async with session.begin():
                assert await provision_initial_administrator(
                    session, username=username, password="bootstrap-secret"
                )

        async with SessionLocal() as session:
            user = await session.scalar(select(User).where(User.username == username))
            boss = await session.scalar(
                select(Role).where(Role.role_code == INITIAL_ADMIN_ROLE_CODE)
            )
            permission_ids = set(
                (
                    await session.scalars(
                        select(Permission.id).where(Permission.is_deleted.is_(False))
                    )
                ).all()
            )
            assert user is not None and boss is not None
            assert user.user_status == "ENABLED"
            assert verify_password("bootstrap-secret", user.password_hash)
            assert await session.scalar(
                select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == boss.id)
            ) is not None
            assert permission_ids == set(
                (await session.scalars(
                    select(RolePermission.permission_id).where(RolePermission.role_id == boss.id)
                )).all()
            )
            user_id = user.id
            user.is_deleted = True
            await session.commit()

        async with SessionLocal() as session:
            async with session.begin():
                assert not await provision_initial_administrator(
                    session, username=username, password="bootstrap-secret"
                )
    finally:
        if user_id is not None:
            async with SessionLocal() as session:
                await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
                await session.execute(delete(User).where(User.id == user_id))
                if not boss_preexisting:
                    boss = await session.scalar(
                        select(Role).where(Role.role_code == INITIAL_ADMIN_ROLE_CODE)
                    )
                    if boss is not None:
                        await session.execute(
                            delete(RolePermission).where(RolePermission.role_id == boss.id)
                        )
                        await session.execute(delete(Role).where(Role.id == boss.id))
                await session.commit()
