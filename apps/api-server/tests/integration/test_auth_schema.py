import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.database import SessionLocal
from app.modules.auth.security import hash_password
from app.modules.system.models import User

AUTH_TABLES = {
    "sys_user",
    "sys_role",
    "sys_permission",
    "sys_user_role",
    "sys_role_permission",
}

UUID_COLUMNS = {
    "sys_user": {"id", "created_by", "updated_by"},
    "sys_role": {"id", "created_by", "updated_by"},
    "sys_permission": {"id", "created_by", "updated_by"},
    "sys_user_role": {"user_id", "role_id", "created_by"},
    "sys_role_permission": {"role_id", "permission_id", "created_by"},
}


async def test_auth_schema_contract_and_active_username_unique() -> None:
    async with SessionLocal() as session:
        tables = set(
            (
                await session.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema=DATABASE()"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert AUTH_TABLES <= tables

        uuid_rows = (
            await session.execute(
                text(
                    "SELECT table_name, column_name, data_type, character_maximum_length "
                    "FROM information_schema.columns "
                    "WHERE table_schema=DATABASE() AND table_name IN "
                    "('sys_user', 'sys_role', 'sys_permission', 'sys_user_role', "
                    "'sys_role_permission')"
                )
            )
        ).all()
        uuid_metadata = {(row[0], row[1]): (row[2], row[3]) for row in uuid_rows}
        for table, columns in UUID_COLUMNS.items():
            for column in columns:
                assert uuid_metadata[(table, column)] == ("char", 36)

        foreign_keys = {
            (row[0], row[1]): (row[2], row[3], row[4])
            for row in (
                await session.execute(
                    text(
                        "SELECT k.table_name, k.column_name, k.referenced_table_name, "
                        "k.referenced_column_name, r.delete_rule "
                        "FROM information_schema.key_column_usage AS k "
                        "JOIN information_schema.referential_constraints AS r "
                        "ON r.constraint_schema=k.constraint_schema "
                        "AND r.table_name=k.table_name "
                        "AND r.constraint_name=k.constraint_name "
                        "WHERE k.constraint_schema=DATABASE() "
                        "AND k.referenced_table_name IS NOT NULL"
                    )
                )
            ).all()
        }
        expected_foreign_keys = {
            ("sys_user_role", "user_id"): ("sys_user", "id"),
            ("sys_user_role", "role_id"): ("sys_role", "id"),
            ("sys_role_permission", "role_id"): ("sys_role", "id"),
            ("sys_role_permission", "permission_id"): ("sys_permission", "id"),
        }
        for key, target in expected_foreign_keys.items():
            table, column, delete_rule = foreign_keys[key]
            assert (table, column) == target
            assert delete_rule in {"RESTRICT", "NO ACTION"}

        try:
            checks = {
                row[0]: row[1]
                for row in (
                    await session.execute(
                        text(
                            "SELECT tc.table_name, cc.check_clause "
                            "FROM information_schema.table_constraints AS tc "
                            "JOIN information_schema.check_constraints AS cc "
                            "ON cc.constraint_schema=tc.constraint_schema "
                            "AND cc.constraint_name=tc.constraint_name "
                            "WHERE tc.constraint_schema=DATABASE() "
                            "AND tc.constraint_type='CHECK'"
                        )
                    )
                ).all()
            }
        except OperationalError:
            await session.rollback()
            checks = None

        if checks is not None:
            assert "user_status" in checks["sys_user"]
            assert "permission_type" in checks["sys_permission"]

        index_rows = (
            await session.execute(
                text(
                    "SELECT table_name, index_name, non_unique, seq_in_index, column_name "
                    "FROM information_schema.statistics "
                    "WHERE table_schema=DATABASE() AND table_name IN "
                    "('sys_role', 'sys_permission', 'sys_user_role', 'sys_role_permission')"
                )
            )
        ).all()
        indexes: dict[tuple[str, str], list[tuple[int, str, int]]] = {}
        for table, index_name, non_unique, sequence, column in index_rows:
            indexes.setdefault((table, index_name), []).append((sequence, column, non_unique))

        def has_unique_index(table: str, columns: tuple[str, ...]) -> bool:
            return any(
                all(non_unique == 0 for _, _, non_unique in values)
                and tuple(column for _, column, _ in sorted(values)) == columns
                for (index_table, _), values in indexes.items()
                if index_table == table
            )

        assert has_unique_index("sys_role", ("role_code",))
        assert has_unique_index("sys_permission", ("permission_code",))
        assert has_unique_index("sys_user_role", ("user_id", "role_id"))
        assert has_unique_index("sys_role_permission", ("role_id", "permission_id"))
        assert any(
            index_table == "sys_user_role"
            and index_name != "PRIMARY"
            and any(sequence == 1 and column == "role_id" for sequence, column, _ in values)
            for (index_table, index_name), values in indexes.items()
        )
        assert any(
            index_table == "sys_role_permission"
            and index_name != "PRIMARY"
            and any(sequence == 1 and column == "permission_id" for sequence, column, _ in values)
            for (index_table, index_name), values in indexes.items()
        )

        if checks is not None:
            with pytest.raises(OperationalError):
                await session.execute(
                    text(
                        "INSERT INTO sys_user (id, username, password_hash, user_status, "
                        "token_version, is_deleted) VALUES "
                        "(:id, :username, :password_hash, 'INVALID', 1, false)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "username": f"invalid-status-{uuid.uuid4()}",
                        "password_hash": "x",
                    },
                )
            await session.rollback()
            with pytest.raises(OperationalError):
                await session.execute(
                    text(
                        "INSERT INTO sys_permission (id, permission_code, permission_name, "
                        "permission_type, is_deleted) VALUES "
                        "(:id, :code, 'invalid type', 'INVALID', false)"
                    ),
                    {"id": str(uuid.uuid4()), "code": f"invalid-type-{uuid.uuid4()}"},
                )
            await session.rollback()

        username = f"active-unique-{uuid.uuid4()}"
        deleted_first = User(username=username, password_hash=hash_password("x"), is_deleted=True)
        deleted_second = User(username=username, password_hash=hash_password("x"), is_deleted=True)
        active = User(username=username, password_hash=hash_password("x"))
        session.add_all([deleted_first, deleted_second, active])
        await session.commit()
        session.add(User(username=username, password_hash=hash_password("x")))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        await session.delete(deleted_first)
        await session.delete(deleted_second)
        await session.delete(active)
        await session.commit()
