from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bid.domain.lifecycle import BidFileType, BidProjectType
from app.modules.bid.infrastructure.models import BidProject, BidProjectFile
from app.modules.recommendation.infrastructure.models import (
    PptGenerationTask,
    PptSolutionPackage,
    PptSolutionPackageItem,
    RecommendationCandidate,
    RecommendationConfirmation,
    RecommendationRun,
)


class PptSolutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def project_for_update(self, project_id: uuid.UUID) -> BidProject | None:
        return cast(
            BidProject | None,
            await self.session.scalar(
                select(BidProject)
                .where(
                    BidProject.id == project_id,
                    BidProject.project_type == BidProjectType.PPT_SOLUTION.value,
                )
                .with_for_update()
            ),
        )

    async def project(self, project_id: uuid.UUID) -> BidProject | None:
        return cast(
            BidProject | None,
            await self.session.scalar(
                select(BidProject).where(
                    BidProject.id == project_id,
                    BidProject.project_type == BidProjectType.PPT_SOLUTION.value,
                )
            ),
        )

    async def run_for_update(self, run_id: uuid.UUID) -> RecommendationRun | None:
        return cast(
            RecommendationRun | None,
            await self.session.scalar(
                select(RecommendationRun)
                .where(RecommendationRun.id == run_id)
                .with_for_update()
            ),
        )

    async def confirmed_candidates(
        self, run_id: uuid.UUID, candidate_ids: Sequence[uuid.UUID] | None = None
    ) -> list[tuple[RecommendationCandidate, RecommendationConfirmation]]:
        statement = (
            select(RecommendationCandidate, RecommendationConfirmation)
            .join(
                RecommendationConfirmation,
                RecommendationConfirmation.candidate_id == RecommendationCandidate.id,
            )
            .where(RecommendationCandidate.run_id == run_id)
            .order_by(RecommendationCandidate.rank)
        )
        if candidate_ids is not None:
            statement = statement.where(RecommendationCandidate.id.in_(candidate_ids))
        rows = await self.session.execute(statement)
        return [(row[0], row[1]) for row in rows]

    async def packages(self, run_id: uuid.UUID) -> list[PptSolutionPackage]:
        return list(
            (
                await self.session.scalars(
                    select(PptSolutionPackage)
                    .where(PptSolutionPackage.run_id == run_id)
                    .order_by(PptSolutionPackage.created_at, PptSolutionPackage.id)
                )
            ).all()
        )

    async def package_items(
        self, package_ids: Sequence[uuid.UUID]
    ) -> list[tuple[PptSolutionPackageItem, RecommendationCandidate]]:
        if not package_ids:
            return []
        rows = await self.session.execute(
            select(PptSolutionPackageItem, RecommendationCandidate)
            .join(
                RecommendationCandidate,
                RecommendationCandidate.id == PptSolutionPackageItem.candidate_id,
            )
            .where(PptSolutionPackageItem.package_id.in_(package_ids))
            .order_by(PptSolutionPackageItem.package_id, PptSolutionPackageItem.sort_order)
        )
        return [(row[0], row[1]) for row in rows]

    async def package_for_update(
        self, package_id: uuid.UUID
    ) -> PptSolutionPackage | None:
        return cast(
            PptSolutionPackage | None,
            await self.session.scalar(
                select(PptSolutionPackage)
                .where(PptSolutionPackage.id == package_id)
                .with_for_update()
            ),
        )

    async def package_items_for_update(
        self, package_id: uuid.UUID
    ) -> list[PptSolutionPackageItem]:
        return list(
            (
                await self.session.scalars(
                    select(PptSolutionPackageItem)
                    .where(PptSolutionPackageItem.package_id == package_id)
                    .with_for_update()
                )
            ).all()
        )

    async def latest_template(self, project_id: uuid.UUID) -> BidProjectFile | None:
        return cast(
            BidProjectFile | None,
            await self.session.scalar(
                select(BidProjectFile)
                .where(
                    BidProjectFile.project_id == project_id,
                    BidProjectFile.file_type == BidFileType.PPT_TEMPLATE.value,
                )
                .order_by(BidProjectFile.version_no.desc())
                .limit(1)
            ),
        )

    async def next_output_version(self, project_id: uuid.UUID) -> int:
        value = await self.session.scalar(
            select(func.max(BidProjectFile.version_no)).where(
                BidProjectFile.project_id == project_id,
                BidProjectFile.file_type == BidFileType.PPT_EXPORT.value,
            )
        )
        return int(value or 0) + 1

    async def generations(self, project_id: uuid.UUID) -> list[PptGenerationTask]:
        return list(
            (
                await self.session.scalars(
                    select(PptGenerationTask)
                    .where(PptGenerationTask.project_id == project_id)
                    .order_by(PptGenerationTask.created_at.desc())
                )
            ).all()
        )

    async def generation_for_update(
        self, task_id: uuid.UUID
    ) -> PptGenerationTask | None:
        return cast(
            PptGenerationTask | None,
            await self.session.scalar(
                select(PptGenerationTask)
                .where(PptGenerationTask.id == task_id)
                .with_for_update()
            ),
        )

    async def generation_output(
        self, task_id: uuid.UUID, file_id: uuid.UUID
    ) -> BidProjectFile | None:
        return cast(
            BidProjectFile | None,
            await self.session.scalar(
                select(BidProjectFile)
                .join(PptGenerationTask, PptGenerationTask.output_file_id == BidProjectFile.id)
                .where(PptGenerationTask.id == task_id, BidProjectFile.id == file_id)
            ),
        )
