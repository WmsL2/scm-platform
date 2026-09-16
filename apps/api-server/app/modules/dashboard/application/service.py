from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.infrastructure.repository import DashboardRepository
from app.modules.dashboard.schemas import DashboardSummaryResponse


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = DashboardRepository(session)

    async def summary(self) -> DashboardSummaryResponse:
        formal_product_count, archived_supplier_count = await self.repository.summary_counts()
        return DashboardSummaryResponse(
            formal_product_count=formal_product_count,
            archived_supplier_count=archived_supplier_count,
        )
