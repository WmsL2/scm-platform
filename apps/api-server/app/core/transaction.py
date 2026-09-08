from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def transaction_scope(session: AsyncSession) -> AsyncIterator[None]:
    """Participate in a caller transaction or own one for standalone service use."""
    if session.in_transaction():
        yield
        return
    async with session.begin():
        yield
