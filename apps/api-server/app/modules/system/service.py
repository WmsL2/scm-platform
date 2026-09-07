from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError
from app.modules.system.repository import BusinessSequenceRepository


class BusinessSequenceService:
    """Issues irreversible, transaction-safe business codes from a configured sequence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BusinessSequenceRepository(session)

    async def issue_code(self, sequence_key: str) -> str:
        if self.session.in_transaction():
            return await self._issue_code(sequence_key)
        async with self.session.begin():
            return await self._issue_code(sequence_key)

    async def _issue_code(self, sequence_key: str) -> str:
        sequence = await self.repository.by_key_for_update(sequence_key)
        if sequence is None:
            raise AppError(
                "BUSINESS_SEQUENCE_NOT_FOUND", "Business sequence is not configured", 404
            )

        issued_value = sequence.next_value
        sequence.next_value += 1
        return f"{sequence.prefix}{issued_value:08d}"
