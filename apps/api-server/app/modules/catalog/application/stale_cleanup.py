from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transaction import transaction_scope
from app.infrastructure.adapters import ObjectStorage, get_object_storage
from app.modules.catalog.infrastructure.repository import ProductRepository


@dataclass(frozen=True)
class StaleImportCleanupReport:
    selected_tasks: int = 0
    deleted_tasks: int = 0
    retained_tasks: int = 0
    skipped_locked_tasks: int = 0


class ProductImportStaleCleanupService:
    """Scheduler-only cleanup that never loads ProductImportRow JSON payloads."""

    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self.session = session
        self.storage = storage or get_object_storage()
        self.repository = ProductRepository(session)

    async def run(self, *, older_than_hours: int, task_limit: int) -> StaleImportCleanupReport:
        if older_than_hours <= 0 or task_limit <= 0:
            raise ValueError("older_than_hours and task_limit must be positive")
        stale_before = datetime.now() - timedelta(hours=older_than_hours)
        task_ids = await self.repository.stale_import_task_ids(
            stale_before=stale_before, limit=task_limit
        )
        deleted = retained = skipped = 0
        for task_id in task_ids:
            result = await self.purge_task(
                task_id, stale_before=stale_before, skip_locked=True
            )
            if result == "DELETED":
                deleted += 1
            elif result == "SKIPPED_LOCKED":
                skipped += 1
            else:
                retained += 1
        return StaleImportCleanupReport(
            selected_tasks=len(task_ids),
            deleted_tasks=deleted,
            retained_tasks=retained,
            skipped_locked_tasks=skipped,
        )

    async def purge_task(
        self, task_id: UUID, *, stale_before: datetime, skip_locked: bool
    ) -> str:
        async with transaction_scope(self.session):
            task = await self.repository.import_task_cleanup_snapshot_for_update(
                task_id, skip_locked=skip_locked
            )
            if task is None:
                return "SKIPPED_LOCKED" if skip_locked else "MISSING"
            if task.created_at >= stale_before:
                return "TOO_RECENT"
            media = (
                []
                if task.status == "CONFIRMED"
                else await self.repository.unimported_task_media(task.id)
            )
            if task.status != "CONFIRMED":
                await self.repository.expire_import_task(task.id)

        deleted_source = False
        deleted_image_ids: list[UUID] = []
        if task.source_file_storage_key is not None:
            try:
                await self.storage.delete(task.source_file_storage_key)
                deleted_source = True
            except Exception:
                pass
        for row_id, image_key in media:
            try:
                await self.storage.delete(image_key)
                deleted_image_ids.append(row_id)
            except Exception:
                pass
        if deleted_source or deleted_image_ids:
            async with transaction_scope(self.session):
                await self.repository.clear_deleted_cleanup_media(
                    task_id=task.id,
                    source_key=task.source_file_storage_key if deleted_source else None,
                    row_image_ids=deleted_image_ids,
                )

        async with transaction_scope(self.session):
            current = await self.repository.import_task_cleanup_snapshot_for_update(
                task_id, skip_locked=skip_locked
            )
            if current is None:
                return "SKIPPED_LOCKED" if skip_locked else "MISSING"
            if current.source_file_storage_key is not None:
                return "RETAINED"
            if (
                current.status == "EXPIRED"
                and await self.repository.has_unimported_task_media(task_id)
            ):
                return "RETAINED"
            if current.status not in {"EXPIRED", "CONFIRMED"}:
                return "RETAINED"
            await self.repository.delete_import_task_staging(task_id)
            return "DELETED"
