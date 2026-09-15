from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bid.infrastructure.models import (
    BidProject,
    BidProjectItem,
    MatchCandidate,
    MatchTask,
)
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


class MatchingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def project_for_update(self, project_id: uuid.UUID) -> BidProject | None:
        return cast(
            BidProject | None,
            await self.session.scalar(
                select(BidProject).where(BidProject.id == project_id).with_for_update()
            ),
        )

    async def items(self, project_id: uuid.UUID) -> list[BidProjectItem]:
        return list(
            (
                await self.session.scalars(
                    select(BidProjectItem)
                    .where(BidProjectItem.project_id == project_id)
                    .order_by(BidProjectItem.sheet_name, BidProjectItem.source_row_number)
                )
            ).all()
        )

    async def item_for_update(
        self, project_id: uuid.UUID, item_id: uuid.UUID
    ) -> BidProjectItem | None:
        return cast(
            BidProjectItem | None,
            await self.session.scalar(
                select(BidProjectItem)
                .where(BidProjectItem.project_id == project_id, BidProjectItem.id == item_id)
                .with_for_update()
            ),
        )

    async def eligible_products(self) -> list[tuple[Product, Supplier]]:
        """One Product/Supplier query for a matching batch; never query per requirement row."""
        rows = await self.session.execute(
            select(Product, Supplier)
            .join(Supplier, Product.source_supplier_id == Supplier.id)
            .where(
                Product.status == ProductStatus.ACTIVE,
                Supplier.archive_status == ArchiveStatus.ARCHIVED,
                Supplier.cooperation_status == CooperationStatus.NORMAL,
                Supplier.is_deleted.is_(False),
            )
        )
        return [(row[0], row[1]) for row in rows.all()]

    async def latest_candidates(
        self, project_id: uuid.UUID, item_id: uuid.UUID
    ) -> list[tuple[MatchCandidate, Product, Supplier]]:
        task_id = await self.session.scalar(
            select(MatchTask.id)
            .where(MatchTask.project_id == project_id, MatchTask.status == "COMPLETED")
            .order_by(MatchTask.created_at.desc())
            .limit(1)
        )
        if task_id is None:
            return []
        rows = await self.session.execute(
            select(MatchCandidate, Product, Supplier)
            .join(Product, MatchCandidate.product_id == Product.id)
            .join(Supplier, MatchCandidate.supplier_id == Supplier.id)
            .where(
                MatchCandidate.match_task_id == task_id, MatchCandidate.project_item_id == item_id
            )
            .order_by(MatchCandidate.rank)
        )
        return [(row[0], row[1], row[2]) for row in rows.all()]

    async def candidate_for_update(
        self, project_id: uuid.UUID, item_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> tuple[MatchCandidate, Product, Supplier] | None:
        row = (
            await self.session.execute(
                select(MatchCandidate, Product, Supplier)
                .join(BidProjectItem, MatchCandidate.project_item_id == BidProjectItem.id)
                .join(Product, MatchCandidate.product_id == Product.id)
                .join(Supplier, MatchCandidate.supplier_id == Supplier.id)
                .where(
                    MatchCandidate.id == candidate_id,
                    MatchCandidate.project_item_id == item_id,
                    BidProjectItem.project_id == project_id,
                )
                .with_for_update()
            )
        ).first()
        if row is None:
            return None
        return cast(tuple[MatchCandidate, Product, Supplier], tuple(row))

    async def unresolved_count(self, project_id: uuid.UUID) -> int:
        value = await self.session.scalar(
            select(func.count())
            .select_from(BidProjectItem)
            .where(
                BidProjectItem.project_id == project_id,
                BidProjectItem.status.not_in(("SELECTED", "NO_QUOTE")),
            )
        )
        return cast(int, value)
