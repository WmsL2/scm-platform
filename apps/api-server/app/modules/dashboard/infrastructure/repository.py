from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary_counts(self) -> tuple[int, int]:
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
        archived_supplier_count = await self.session.scalar(
            select(func.count())
            .select_from(Supplier)
            .where(
                Supplier.is_deleted.is_(False),
                Supplier.archive_status == ArchiveStatus.ARCHIVED,
            )
        )
        return int(formal_product_count or 0), int(archived_supplier_count or 0)
