from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bid.infrastructure.models import BidProject
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier

ACTIVE_PROJECT_STATUSES = ("IMPORTED", "MATCHING", "SELECTING", "READY", "EXPORTED", "SUBMITTED")


@dataclass(frozen=True)
class DashboardCounts:
    formal_product_count: int
    normal_supplier_count: int
    active_project_count: int
    pending_supplier_count: int


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary_counts(self) -> DashboardCounts:
        formal_product_count = await self.session.scalar(
            select(func.count())
            .select_from(Product)
            .join(Supplier, Product.source_supplier_id == Supplier.id)
            .where(
                Product.status == ProductStatus.ACTIVE,
                Supplier.is_deleted.is_(False),
                Supplier.cooperation_status == CooperationStatus.NORMAL,
            )
        )
        normal_supplier_count = await self.session.scalar(
            select(func.count())
            .select_from(Supplier)
            .where(
                Supplier.is_deleted.is_(False),
                Supplier.archive_status == ArchiveStatus.ARCHIVED,
                Supplier.cooperation_status == CooperationStatus.NORMAL,
            )
        )
        active_project_count = await self.session.scalar(
            select(func.count())
            .select_from(BidProject)
            .where(BidProject.status.in_(ACTIVE_PROJECT_STATUSES))
        )
        pending_supplier_count = await self.session.scalar(
            select(func.count())
            .select_from(Supplier)
            .where(
                Supplier.is_deleted.is_(False),
                Supplier.archive_status == ArchiveStatus.PENDING,
            )
        )
        return DashboardCounts(
            formal_product_count=int(formal_product_count or 0),
            normal_supplier_count=int(normal_supplier_count or 0),
            active_project_count=int(active_project_count or 0),
            pending_supplier_count=int(pending_supplier_count or 0),
        )

    async def recent_projects(self, limit: int = 5) -> list[BidProject]:
        return list(
            (
                await self.session.scalars(
                    select(BidProject).order_by(BidProject.updated_at.desc()).limit(limit)
                )
            ).all()
        )
