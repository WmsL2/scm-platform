import uuid
from typing import cast

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.contracts import PageParams
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import (
    Supplier,
    SupplierContact,
    SupplierCooperationRecord,
    SupplierImportBatch,
    SupplierImportRow,
    SupplierQualification,
)


class SupplierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def active_by_id(self, supplier_id: uuid.UUID) -> Supplier | None:
        return cast(
            Supplier | None,
            await self.session.scalar(
                select(Supplier)
                .options(selectinload(Supplier.contacts))
                .where(Supplier.id == supplier_id, Supplier.is_deleted.is_(False))
            ),
        )

    async def active_by_id_for_update(self, supplier_id: uuid.UUID) -> Supplier | None:
        return cast(
            Supplier | None,
            await self.session.scalar(
                select(Supplier)
                .options(selectinload(Supplier.contacts))
                .where(Supplier.id == supplier_id, Supplier.is_deleted.is_(False))
                .with_for_update()
            ),
        )

    async def by_name_for_update(self, supplier_name: str) -> Supplier | None:
        """Return an active or logically deleted supplier while holding a row lock."""
        return cast(
            Supplier | None,
            await self.session.scalar(
                select(Supplier)
                .options(selectinload(Supplier.contacts))
                .where(Supplier.supplier_name == supplier_name)
                .with_for_update()
            ),
        )

    async def active_supplier_names(self, supplier_names: set[str]) -> set[str]:
        if not supplier_names:
            return set()
        statement = select(Supplier.supplier_name).where(
            Supplier.supplier_name.in_(supplier_names),
            Supplier.is_deleted.is_(False),
        )
        return set((await self.session.scalars(statement)).all())

    async def eligible_source_suppliers(self) -> list[Supplier]:
        statement = (
            select(Supplier)
            .where(
                Supplier.is_deleted.is_(False),
                Supplier.archive_status == ArchiveStatus.ARCHIVED,
                Supplier.cooperation_status == CooperationStatus.NORMAL,
            )
            .order_by(Supplier.supplier_name, Supplier.id)
        )
        return list((await self.session.scalars(statement)).all())

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

    async def import_batch_by_id_for_update(
        self, batch_id: uuid.UUID
    ) -> SupplierImportBatch | None:
        return cast(
            SupplierImportBatch | None,
            await self.session.scalar(
                select(SupplierImportBatch)
                .where(SupplierImportBatch.id == batch_id)
                .with_for_update()
            ),
        )

    async def import_rows_by_batch_id_for_update(
        self, batch_id: uuid.UUID
    ) -> list[SupplierImportRow]:
        """Load persisted rows explicitly for the atomic import-confirm workflow."""
        statement = (
            select(SupplierImportRow)
            .where(SupplierImportRow.batch_id == batch_id)
            .order_by(SupplierImportRow.source_row_number)
            .with_for_update()
        )
        return list((await self.session.scalars(statement)).all())

    async def logical_delete_children(self, supplier_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        await self.session.execute(
            update(SupplierContact)
            .where(
                SupplierContact.supplier_id == supplier_id,
                SupplierContact.is_deleted.is_(False),
            )
            .values(is_deleted=True, updated_by=actor_id)
        )
        await self.session.execute(
            update(SupplierQualification)
            .where(
                SupplierQualification.supplier_id == supplier_id,
                SupplierQualification.is_deleted.is_(False),
            )
            .values(is_deleted=True, updated_by=actor_id)
        )

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
