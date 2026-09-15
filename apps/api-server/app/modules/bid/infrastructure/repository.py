from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bid.domain.lifecycle import BidFileType
from app.modules.bid.infrastructure.models import (
    BidItemSelection,
    BidProject,
    BidProjectEvent,
    BidProjectFile,
    BidProjectItem,
    BidTemplate,
)


class BidProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def template_by_fingerprint(self, fingerprint: str) -> BidTemplate | None:
        return cast(
            BidTemplate | None,
            await self.session.scalar(
                select(BidTemplate)
                .where(BidTemplate.fingerprint == fingerprint, BidTemplate.is_active.is_(True))
                .order_by(BidTemplate.version.desc())
            ),
        )

    async def project_by_id(
        self, project_id: uuid.UUID, *, lock: bool = False
    ) -> BidProject | None:
        statement = select(BidProject).where(BidProject.id == project_id)
        if lock:
            statement = statement.with_for_update()
        return cast(BidProject | None, await self.session.scalar(statement))

    async def project_page(
        self, *, page: int, page_size: int, keyword: str | None, status: str | None
    ) -> tuple[list[BidProject], int]:
        statement = select(BidProject)
        count_statement = select(func.count()).select_from(BidProject)
        if keyword:
            condition = BidProject.project_name.contains(
                keyword
            ) | BidProject.project_code.contains(keyword)
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        if status:
            statement = statement.where(BidProject.status == status)
            count_statement = count_statement.where(BidProject.status == status)
        statement = (
            statement.order_by(BidProject.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.scalars(statement)).all())
        return rows, cast(int, await self.session.scalar(count_statement))

    async def files(self, project_id: uuid.UUID) -> list[BidProjectFile]:
        return list(
            (
                await self.session.scalars(
                    select(BidProjectFile)
                    .where(BidProjectFile.project_id == project_id)
                    .order_by(BidProjectFile.file_type, BidProjectFile.version_no)
                )
            ).all()
        )

    async def file_by_id(self, project_id: uuid.UUID, file_id: uuid.UUID) -> BidProjectFile | None:
        return cast(
            BidProjectFile | None,
            await self.session.scalar(
                select(BidProjectFile).where(
                    BidProjectFile.id == file_id, BidProjectFile.project_id == project_id
                )
            ),
        )

    async def original_file(self, project_id: uuid.UUID) -> BidProjectFile | None:
        return cast(
            BidProjectFile | None,
            await self.session.scalar(
                select(BidProjectFile).where(
                    BidProjectFile.project_id == project_id,
                    BidProjectFile.file_type == BidFileType.ORIGINAL.value,
                )
            ),
        )

    async def next_export_version(self, project_id: uuid.UUID) -> int:
        latest = await self.session.scalar(
            select(func.max(BidProjectFile.version_no)).where(
                BidProjectFile.project_id == project_id,
                BidProjectFile.file_type == BidFileType.QUOTED_EXPORT.value,
            )
        )
        return (latest or 0) + 1

    async def events(self, project_id: uuid.UUID) -> list[BidProjectEvent]:
        return list(
            (
                await self.session.scalars(
                    select(BidProjectEvent)
                    .where(BidProjectEvent.project_id == project_id)
                    .order_by(BidProjectEvent.occurred_at.asc())
                )
            ).all()
        )

    async def item_page(
        self, project_id: uuid.UUID, *, page: int, page_size: int, status: str | None
    ) -> tuple[list[BidProjectItem], int]:
        statement = select(BidProjectItem).where(BidProjectItem.project_id == project_id)
        count_statement = (
            select(func.count())
            .select_from(BidProjectItem)
            .where(BidProjectItem.project_id == project_id)
        )
        if status:
            statement = statement.where(BidProjectItem.status == status)
            count_statement = count_statement.where(BidProjectItem.status == status)
        statement = statement.order_by(BidProjectItem.sheet_name, BidProjectItem.source_row_number)
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.session.scalars(statement)).all())
        return rows, cast(int, await self.session.scalar(count_statement))

    async def export_rows(
        self, project_id: uuid.UUID
    ) -> list[tuple[BidProjectItem, BidItemSelection]]:
        rows = await self.session.execute(
            select(BidProjectItem, BidItemSelection)
            .join(BidItemSelection, BidProjectItem.current_selection_id == BidItemSelection.id)
            .where(BidProjectItem.project_id == project_id)
        )
        return [(row[0], row[1]) for row in rows.all()]
