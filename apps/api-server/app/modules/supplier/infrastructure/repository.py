import uuid
from typing import cast

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.contracts import PageParams
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier, SupplierCooperationRecord


class SupplierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def active_by_id(self, supplier_id: str) -> Supplier | None:
        return cast(
            Supplier | None,
            await self.session.scalar(
                select(Supplier)
                .options(selectinload(Supplier.contacts))
                .where(Supplier.id == supplier_id, Supplier.is_deleted.is_(False))
            ),
        )

    async def active_by_id_for_update(self, supplier_id: str) -> Supplier | None:
        return cast(
            Supplier | None,
            await self.session.scalar(
                select(Supplier)
                .options(selectinload(Supplier.contacts))
                .where(Supplier.id == supplier_id, Supplier.is_deleted.is_(False))
                .with_for_update()
            ),
        )

    async def list_active(
        self,
        page_params: PageParams,
        *,
        keyword: str | None,
        archive_status: ArchiveStatus | None,
        cooperation_status: CooperationStatus | None,
    ) -> tuple[list[Supplier], int]:
        statement: Select[tuple[Supplier]] = select(Supplier).where(Supplier.is_deleted.is_(False))
        count_statement = (
            select(func.count()).select_from(Supplier).where(Supplier.is_deleted.is_(False))
        )
        if keyword:
            criteria = or_(
                Supplier.supplier_code.contains(keyword),
                Supplier.supplier_name.contains(keyword),
                Supplier.main_brands.contains(keyword),
            )
            statement = statement.where(criteria)
            count_statement = count_statement.where(criteria)
        if archive_status:
            statement = statement.where(Supplier.archive_status == archive_status)
            count_statement = count_statement.where(Supplier.archive_status == archive_status)
        if cooperation_status:
            statement = statement.where(Supplier.cooperation_status == cooperation_status)
            count_statement = count_statement.where(
                Supplier.cooperation_status == cooperation_status
            )
        statement = statement.order_by(Supplier.created_at.desc(), Supplier.id.desc()).offset(
            (page_params.page - 1) * page_params.page_size
        ).limit(page_params.page_size)
        suppliers = list((await self.session.scalars(statement)).all())
        total = cast(int, await self.session.scalar(count_statement))
        return suppliers, total

    def add_cooperation_record(
        self,
        *,
        supplier_id: uuid.UUID,
        from_status: str,
        to_status: CooperationStatus,
        reason: str,
        actor_id: uuid.UUID,
    ) -> None:
        self.session.add(
            SupplierCooperationRecord(
                supplier_id=supplier_id,
                from_status=from_status,
                to_status=target_value(to_status),
                reason=reason,
                actor_id=actor_id,
            )
        )


def target_value(status: CooperationStatus) -> str:
    return status.value
