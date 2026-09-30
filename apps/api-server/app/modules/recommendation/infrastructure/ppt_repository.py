from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import cast

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.bid.domain.lifecycle import BidFileType, BidProjectType
from app.modules.bid.infrastructure.models import BidProject, BidProjectFile
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.recommendation.infrastructure.models import (
    PptGenerationTask,
    PptRecommendationConfig,
    PptSolutionPackage,
    PptSolutionPackageItem,
    PptSolutionPlan,
    RecommendationCandidate,
    RecommendationCategoryChoice,
    RecommendationConfirmation,
    RecommendationRun,
)
from app.modules.recommendation.schemas import CategoryPath, ParsedRequirement
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


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

    async def config(
        self, project_id: uuid.UUID, *, lock: bool = False
    ) -> PptRecommendationConfig | None:
        statement = select(PptRecommendationConfig).where(
            PptRecommendationConfig.project_id == project_id
        )
        if lock:
            statement = statement.with_for_update()
        return cast(PptRecommendationConfig | None, await self.session.scalar(statement))

    async def run_for_update(self, run_id: uuid.UUID) -> RecommendationRun | None:
        return cast(
            RecommendationRun | None,
            await self.session.scalar(
                select(RecommendationRun).where(RecommendationRun.id == run_id).with_for_update()
            ),
        )

    async def run(self, run_id: uuid.UUID) -> RecommendationRun | None:
        return cast(
            RecommendationRun | None,
            await self.session.scalar(
                select(RecommendationRun).where(RecommendationRun.id == run_id)
            ),
        )

    async def category_pool(self, requirement: ParsedRequirement) -> list[tuple[CategoryPath, int]]:
        """Type-5-owned V8 catalogue source; do not call the Type-4 repository."""
        statement = (
            select(
                Product.category_level1_name,
                Product.category_level2_name,
                Product.category_level3_name,
                func.count(Product.id),
            )
            .select_from(Product)
            .join(Supplier, Product.source_supplier_id == Supplier.id)
            .where(*self._eligibility_filters(requirement))
            .where(Product.category_level3_name.is_not(None))
            .group_by(
                Product.category_level1_name,
                Product.category_level2_name,
                Product.category_level3_name,
            )
            .order_by(
                func.count(Product.id).desc(),
                Product.category_level1_name,
                Product.category_level2_name,
                Product.category_level3_name,
            )
        )
        rows = (await self.session.execute(statement)).all()
        return [
            (
                CategoryPath(level1_name=row[0], level2_name=row[1], level3_name=row[2]),
                int(row[3]),
            )
            for row in rows
        ]

    async def category_choices(self, run_id: uuid.UUID) -> list[RecommendationCategoryChoice]:
        return list(
            (
                await self.session.scalars(
                    select(RecommendationCategoryChoice)
                    .where(RecommendationCategoryChoice.run_id == run_id)
                    .order_by(
                        RecommendationCategoryChoice.created_at, RecommendationCategoryChoice.id
                    )
                )
            ).all()
        )

    async def all_eligible_products(
        self, requirement: ParsedRequirement, category_paths: Sequence[CategoryPath]
    ) -> list[tuple[Product, Supplier]]:
        statement = (
            select(Product, Supplier)
            .join(Supplier, Product.source_supplier_id == Supplier.id)
            .where(*self._eligibility_filters(requirement))
            .order_by(Product.positive_rating.desc(), Product.id)
        )
        if category_paths:
            path_conditions: list[ColumnElement[bool]] = []
            for path in category_paths:
                parts: list[ColumnElement[bool]] = []
                if path.level1_name:
                    parts.append(Product.category_level1_name == path.level1_name)
                if path.level2_name:
                    parts.append(Product.category_level2_name == path.level2_name)
                if path.level3_name:
                    parts.append(Product.category_level3_name == path.level3_name)
                path_conditions.append(and_(*parts))
            statement = statement.where(or_(*path_conditions))
        rows = await self.session.execute(statement)
        return [(row[0], row[1]) for row in rows]

    async def project_has_candidates(self, project_id: uuid.UUID) -> bool:
        value = await self.session.scalar(
            select(func.count(RecommendationCandidate.id))
            .join(RecommendationRun, RecommendationRun.id == RecommendationCandidate.run_id)
            .where(RecommendationRun.project_id == project_id)
        )
        return bool(value)

    @staticmethod
    def _eligibility_filters(requirement: ParsedRequirement) -> list[ColumnElement[bool]]:
        """Keep Type-5 V8 hard filtering local to this repository."""
        filters: list[ColumnElement[bool]] = [
            Product.status == ProductStatus.ACTIVE,
            Supplier.archive_status == ArchiveStatus.ARCHIVED,
            Supplier.cooperation_status == CooperationStatus.NORMAL,
            Supplier.is_deleted.is_(False),
        ]
        for field, column, comparison in (
            ("gross_margin_min", Product.gross_margin, "min"),
            ("gross_margin_max", Product.gross_margin, "max"),
            ("agreement_price_min", Product.agreement_price, "min"),
            ("agreement_price_max", Product.agreement_price, "max"),
            ("jd_price_min", Product.jd_price, "min"),
            ("jd_price_max", Product.jd_price, "max"),
            ("discount_rate_min", Product.discount_rate, "min"),
            ("discount_rate_max", Product.discount_rate, "max"),
        ):
            value = getattr(requirement, field)
            if value is not None:
                filters.append(column >= value if comparison == "min" else column <= value)
        return filters

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

    async def candidates(self, run_id: uuid.UUID) -> list[RecommendationCandidate]:
        return list(
            (
                await self.session.scalars(
                    select(RecommendationCandidate)
                    .where(RecommendationCandidate.run_id == run_id)
                    .order_by(RecommendationCandidate.rank, RecommendationCandidate.id)
                )
            ).all()
        )

    async def plans(self, run_id: uuid.UUID) -> list[PptSolutionPlan]:
        return list(
            (
                await self.session.scalars(
                    select(PptSolutionPlan)
                    .where(PptSolutionPlan.run_id == run_id)
                    .order_by(PptSolutionPlan.price_band_index, PptSolutionPlan.plan_no)
                )
            ).all()
        )

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

    async def package_for_update(self, package_id: uuid.UUID) -> PptSolutionPackage | None:
        return cast(
            PptSolutionPackage | None,
            await self.session.scalar(
                select(PptSolutionPackage)
                .where(PptSolutionPackage.id == package_id)
                .with_for_update()
            ),
        )

    async def package_items_for_update(self, package_id: uuid.UUID) -> list[PptSolutionPackageItem]:
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

    async def generation_for_update(self, task_id: uuid.UUID) -> PptGenerationTask | None:
        return cast(
            PptGenerationTask | None,
            await self.session.scalar(
                select(PptGenerationTask).where(PptGenerationTask.id == task_id).with_for_update()
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
