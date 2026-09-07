import asyncio
import uuid

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from app.common.contracts import AppError
from app.core.database import SessionLocal
from app.modules.system.models import BusinessSequence
from app.modules.system.service import BusinessSequenceService


async def create_sequence(sequence_key: str, prefix: str, next_value: int = 1) -> None:
    async with SessionLocal() as session:
        session.add(
            BusinessSequence(
                sequence_key=sequence_key,
                prefix=prefix,
                next_value=next_value,
            )
        )
        await session.commit()


async def delete_sequence(sequence_key: str) -> None:
    async with SessionLocal() as session:
        await session.execute(
            delete(BusinessSequence).where(BusinessSequence.sequence_key == sequence_key)
        )
        await session.commit()


async def issue_code(sequence_key: str) -> str:
    async with SessionLocal() as session:
        return await BusinessSequenceService(session).issue_code(sequence_key)


async def next_value(sequence_key: str) -> int:
    async with SessionLocal() as session:
        sequence = await session.scalar(
            select(BusinessSequence).where(BusinessSequence.sequence_key == sequence_key)
        )
        assert sequence is not None
        return sequence.next_value


async def test_business_sequence_schema_and_supplier_seed() -> None:
    async with SessionLocal() as session:
        columns = {
            (row[0], row[1]): (row[2], row[3])
            for row in (
                await session.execute(
                    text(
                        "SELECT column_name, data_type, character_maximum_length, "
                        "column_key FROM information_schema.columns "
                        "WHERE table_schema=DATABASE() AND table_name='sys_biz_sequence'"
                    )
                )
            ).all()
        }
        assert columns[("id", "char")] == (36, "PRI")
        assert columns[("sequence_key", "varchar")] == (64, "UNI")
        assert columns[("prefix", "varchar")] == (16, "")
        assert columns[("next_value", "bigint")] == (None, "")

        supplier_sequence = await session.scalar(
            select(BusinessSequence).where(BusinessSequence.sequence_key == "SUPPLIER")
        )
        assert supplier_sequence is not None
        assert supplier_sequence.prefix == "SUP"
        assert supplier_sequence.next_value >= 1


async def test_issue_code_is_sequential_and_does_not_reuse_values() -> None:
    sequence_key = f"SEQUENTIAL_{uuid.uuid4().hex}"
    await create_sequence(sequence_key, "SEQ")
    try:
        assert await issue_code(sequence_key) == "SEQ00000001"
        assert await issue_code(sequence_key) == "SEQ00000002"
        assert await next_value(sequence_key) == 3
    finally:
        await delete_sequence(sequence_key)


async def test_issue_code_requires_preconfigured_sequence() -> None:
    async with SessionLocal() as session:
        with pytest.raises(AppError, match="Business sequence is not configured"):
            await BusinessSequenceService(session).issue_code("MISSING_SEQUENCE")


async def test_sequence_key_is_unique() -> None:
    sequence_key = f"UNIQUE_{uuid.uuid4().hex}"
    try:
        async with SessionLocal() as session:
            session.add_all(
                [
                    BusinessSequence(sequence_key=sequence_key, prefix="ONE", next_value=1),
                    BusinessSequence(sequence_key=sequence_key, prefix="TWO", next_value=1),
                ]
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    finally:
        await delete_sequence(sequence_key)


async def test_issue_code_is_safe_under_mysql_concurrency() -> None:
    sequence_key = f"CONCURRENT_{uuid.uuid4().hex}"
    issued_count = 20
    await create_sequence(sequence_key, "CON")
    try:
        codes = await asyncio.gather(*(issue_code(sequence_key) for _ in range(issued_count)))
        assert len(codes) == issued_count
        assert set(codes) == {f"CON{value:08d}" for value in range(1, issued_count + 1)}
        assert await next_value(sequence_key) == issued_count + 1
    finally:
        await delete_sequence(sequence_key)
