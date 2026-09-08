import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams, PageResult
from app.core.transaction import transaction_scope
from app.modules.supplier.domain.rules import (
    ArchiveStatus,
    CooperationStatus,
    assert_archive_transition,
    assert_cooperation_transition,
    normalize_reason,
)
from app.modules.supplier.infrastructure.models import Supplier, SupplierContact
from app.modules.supplier.infrastructure.repository import SupplierRepository
from app.modules.supplier.schemas import (
    SupplierContactInput,
    SupplierContactResponse,
    SupplierCreateRequest,
    SupplierDeleteResponse,
    SupplierDetailResponse,
    SupplierListItem,
    SupplierUpdateRequest,
)
from app.modules.system.service import BusinessSequenceService


class SupplierService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SupplierRepository(session)

    async def list(
        self,
        page_params: PageParams,
        *,
        keyword: str | None,
        archive_status: ArchiveStatus | None,
        cooperation_status: CooperationStatus | None,
    ) -> PageResult[SupplierListItem]:
        suppliers, total = await self.repository.list_active(
            page_params,
            keyword=keyword.strip() if keyword else None,
            archive_status=archive_status,
            cooperation_status=cooperation_status,
        )
        return PageResult(
            items=[self._list_item(supplier) for supplier in suppliers],
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def get(self, supplier_id: uuid.UUID) -> SupplierDetailResponse:
        supplier = await self.repository.active_by_id(supplier_id)
        if supplier is None:
            raise AppError("SUPPLIER_NOT_FOUND", "Supplier not found", 404)
        return self._detail(supplier)

    async def create(
        self, payload: SupplierCreateRequest, actor_id: uuid.UUID
    ) -> SupplierDetailResponse:
        async with transaction_scope(self.session):
            supplier = Supplier(
                supplier_code=await BusinessSequenceService(self.session).issue_code("SUPPLIER"),
                supplier_name=payload.supplier_name.strip(),
                main_brands=payload.main_brands.strip(),
                advantage=payload.advantage.strip(),
                created_by=actor_id,
                updated_by=actor_id,
                contacts=[
                    self._contact_from_input(contact_input, actor_id)
                    for contact_input in payload.contacts
                ],
            )
            self.session.add(supplier)
            await self.session.flush()
            result = await self.get(supplier.id)
        return result

    async def update(
        self, supplier_id: uuid.UUID, payload: SupplierUpdateRequest, actor_id: uuid.UUID
    ) -> SupplierDetailResponse:
        if not payload.model_fields_set:
            raise AppError("SUPPLIER_UPDATE_EMPTY", "At least one field must be supplied", 400)
        async with transaction_scope(self.session):
            supplier = await self._active_for_update(supplier_id)
            if "supplier_name" in payload.model_fields_set:
                supplier.supplier_name = self._required_text(payload.supplier_name, "supplier_name")
            if "main_brands" in payload.model_fields_set:
                supplier.main_brands = self._required_text(payload.main_brands, "main_brands")
            if "advantage" in payload.model_fields_set:
                supplier.advantage = self._required_text(payload.advantage, "advantage")
            if "contacts" in payload.model_fields_set:
                self._replace_contacts(supplier, payload.contacts or [], actor_id)
            supplier.updated_by = actor_id
            result = await self.get(supplier_id)
        return result

    async def delete(self, supplier_id: uuid.UUID, actor_id: uuid.UUID) -> SupplierDeleteResponse:
        async with transaction_scope(self.session):
            supplier = await self._active_for_update(supplier_id)
            supplier.is_deleted = True
            supplier.deleted_by = actor_id
            supplier.deleted_at = datetime.now()
            supplier.updated_by = actor_id
            await self.repository.logical_delete_children(supplier.id, actor_id)
        return SupplierDeleteResponse(id=supplier.id)

    async def submit(self, supplier_id: uuid.UUID, actor_id: uuid.UUID) -> SupplierDetailResponse:
        async with transaction_scope(self.session):
            supplier = await self._active_for_update(supplier_id)
            assert_archive_transition(supplier.archive_status, ArchiveStatus.PENDING)
            supplier.archive_status = ArchiveStatus.PENDING
            supplier.updated_by = actor_id
            result = await self.get(supplier_id)
        return result

    async def archive(self, supplier_id: uuid.UUID, actor_id: uuid.UUID) -> SupplierDetailResponse:
        async with transaction_scope(self.session):
            supplier = await self._active_for_update(supplier_id)
            assert_archive_transition(supplier.archive_status, ArchiveStatus.ARCHIVED)
            supplier.archive_status = ArchiveStatus.ARCHIVED
            supplier.archived_by = actor_id
            supplier.archived_at = datetime.now()
            supplier.updated_by = actor_id
            result = await self.get(supplier_id)
        return result

    async def stop(
        self, supplier_id: uuid.UUID, reason: str, actor_id: uuid.UUID
    ) -> SupplierDetailResponse:
        return await self._change_cooperation_status(
            supplier_id, CooperationStatus.STOPPED, reason, actor_id
        )

    async def blacklist(
        self, supplier_id: uuid.UUID, reason: str, actor_id: uuid.UUID
    ) -> SupplierDetailResponse:
        return await self._change_cooperation_status(
            supplier_id, CooperationStatus.BLACKLIST, reason, actor_id
        )

    async def _change_cooperation_status(
        self,
        supplier_id: uuid.UUID,
        target_status: CooperationStatus,
        reason: str,
        actor_id: uuid.UUID,
    ) -> SupplierDetailResponse:
        normalized_reason = normalize_reason(reason)
        async with transaction_scope(self.session):
            supplier = await self._active_for_update(supplier_id)
            assert_cooperation_transition(supplier.cooperation_status, target_status)
            self.repository.add_cooperation_record(
                supplier_id=supplier.id,
                from_status=supplier.cooperation_status,
                to_status=target_status,
                reason=normalized_reason,
                actor_id=actor_id,
            )
            supplier.cooperation_status = target_status
            supplier.updated_by = actor_id
            result = await self.get(supplier_id)
        return result

    async def _active_for_update(self, supplier_id: uuid.UUID) -> Supplier:
        supplier = await self.repository.active_by_id_for_update(supplier_id)
        if supplier is None:
            raise AppError("SUPPLIER_NOT_FOUND", "Supplier not found", 404)
        return supplier

    def _replace_contacts(
        self, supplier: Supplier, contacts: Sequence[SupplierContactInput], actor_id: uuid.UUID
    ) -> None:
        for contact in supplier.contacts:
            if not contact.is_deleted:
                contact.is_deleted = True
                contact.updated_by = actor_id
        for contact_input in contacts:
            supplier.contacts.append(self._contact_from_input(contact_input, actor_id))

    @staticmethod
    def _contact_from_input(
        contact_input: SupplierContactInput, actor_id: uuid.UUID
    ) -> SupplierContact:
        return SupplierContact(
            contact_name=contact_input.contact_name.strip() if contact_input.contact_name else None,
            contact_phone=(
                contact_input.contact_phone.strip() if contact_input.contact_phone else None
            ),
            created_by=actor_id,
            updated_by=actor_id,
        )

    @staticmethod
    def _required_text(value: str | None, field_name: str) -> str:
        if value is None or not value.strip():
            raise AppError("SUPPLIER_VALIDATION_ERROR", f"{field_name} must not be blank", 422)
        return value.strip()

    @staticmethod
    def _list_item(supplier: Supplier) -> SupplierListItem:
        return SupplierListItem(
            id=supplier.id,
            supplier_code=supplier.supplier_code,
            supplier_name=supplier.supplier_name,
            main_brands=supplier.main_brands,
            advantage=supplier.advantage,
            archive_status=ArchiveStatus(supplier.archive_status),
            cooperation_status=CooperationStatus(supplier.cooperation_status),
        )

    @staticmethod
    def _detail(supplier: Supplier) -> SupplierDetailResponse:
        return SupplierDetailResponse(
            **SupplierService._list_item(supplier).model_dump(),
            contacts=[
                SupplierContactResponse(
                    id=contact.id,
                    contact_name=contact.contact_name,
                    contact_phone=contact.contact_phone,
                )
                for contact in supplier.contacts
                if not contact.is_deleted
            ],
            archived_by=supplier.archived_by,
            archived_at=supplier.archived_at,
            created_at=supplier.created_at,
            updated_at=supplier.updated_at,
        )
