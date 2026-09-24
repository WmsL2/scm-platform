from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.infrastructure.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    DashboardRecentProjectResponse,
    DashboardSummaryResponse,
)


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = DashboardRepository(session)

    async def summary(self, *, include_recent_projects: bool = False) -> DashboardSummaryResponse:
        counts = await self.repository.summary_counts()
        recent_projects = await self.repository.recent_projects() if include_recent_projects else []
        return DashboardSummaryResponse(
            formal_product_count=counts.formal_product_count,
            normal_supplier_count=counts.normal_supplier_count,
            active_project_count=counts.active_project_count,
            pending_supplier_count=counts.pending_supplier_count,
            recent_projects=[
                DashboardRecentProjectResponse(
                    id=project.id,
                    project_code=project.project_code,
                    project_name=project.project_name,
                    project_type=project.project_type,
                    status=project.status,
                    updated_at=project.updated_at,
                )
                for project in recent_projects
            ],
        )
