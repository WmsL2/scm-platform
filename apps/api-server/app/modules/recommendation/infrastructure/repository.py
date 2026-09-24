from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import cast

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.bid.domain.lifecycle import BidProjectType
from app.modules.bid.infrastructure.models import BidProject, BidProjectFile
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product
from app.modules.recommendation.infrastructure.models import (
    RecommendationCandidate,
    RecommendationConfirmation,
    RecommendationExport,
    RecommendationRun,
)
from app.modules.recommendation.schemas import CategoryPath, ParsedRequirement
from app.modules.recommendation.template.models import RecommendationTemplateMapping
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def free_project_for_update(self, project_id: uuid.UUID) -> BidProject | None:
        return cast(
            BidProject | None,
            await self.session.scalar(
                select(BidProject)
                .where(
                    BidProject.id == project_id,
                    BidProject.project_type == BidProjectType.FREE_RECOMMENDATION.value,
                )
                .with_for_update()
            ),
        )

    async def latest_template_mapping(
        self, project_id: uuid.UUID
    ) -> tuple[RecommendationTemplateMapping, BidProjectFile] | None:
        row = (
            await self.session.execute(
                select(RecommendationTemplateMapping, BidProjectFile)
                .join(
                    BidProjectFile,
                    RecommendationTemplateMapping.template_file_id == BidProjectFile.id,
                )
                .where(RecommendationTemplateMapping.project_id == project_id)
                .order_by(BidProjectFile.version_no.desc())
                .limit(1)
            )
        ).first()
        if row is None:
            return None
        return cast(tuple[RecommendationTemplateMapping, BidProjectFile], tuple(row))

    async def latest_template_mapping_for_update(
        self, project_id: uuid.UUID
    ) -> tuple[RecommendationTemplateMapping, BidProjectFile] | None:
        row = (
            await self.session.execute(
                select(RecommendationTemplateMapping, BidProjectFile)
                .join(
                    BidProjectFile,
                    RecommendationTemplateMapping.template_file_id == BidProjectFile.id,
                )
                .where(RecommendationTemplateMapping.project_id == project_id)
                .order_by(BidProjectFile.version_no.desc())
                .limit(1)
                .with_for_update()
            )
        ).first()
        if row is None:
            return None
        return cast(tuple[RecommendationTemplateMapping, BidProjectFile], tuple(row))

    async def run_for_update(self, run_id: uuid.UUID) -> RecommendationRun | None:
        return cast(
            RecommendationRun | None,
            await self.session.scalar(
                select(RecommendationRun).where(RecommendationRun.id == run_id).with_for_update()
            ),
        )

    async def run_by_id(self, run_id: uuid.UUID) -> RecommendationRun | None:
        return cast(
            RecommendationRun | None,
            await self.session.scalar(
                select(RecommendationRun).where(RecommendationRun.id == run_id)
            ),
        )

    async def runs(self, project_id: uuid.UUID) -> list[RecommendationRun]:
        return list(
            (
                await self.session.scalars(
                    select(RecommendationRun)
                    .where(RecommendationRun.project_id == project_id)
                    .order_by(RecommendationRun.created_at.desc())
                )
            ).all()
        )

    async def category_pool(
        self, requirement: ParsedRequirement, keywords: Sequence[str] = ()
    ) -> list[tuple[CategoryPath, int]]:
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
                # category intent is a recall signal, never a hidden eligibility rule.
                func.count(Product.id).desc(),
                Product.category_level1_name,
                Product.category_level2_name,
                Product.category_level3_name,
            )
            .limit(160)
        )
        rows = (await self.session.execute(statement)).all()
        return [
            (
                CategoryPath(level1_name=row[0], level2_name=row[1], level3_name=row[2]),
                int(row[3]),
            )
            for row in rows
        ]

    async def eligible_products(
        self,
        requirement: ParsedRequirement,
        category_paths: Sequence[CategoryPath] = (),
        *,
        keywords: Sequence[str] = (),
        preferred_brands: Sequence[str] = (),
    ) -> list[tuple[Product, Supplier]]:
        statement: Select[tuple[Product, Supplier]] = (
            select(Product, Supplier)
            .join(Supplier, Product.source_supplier_id == Supplier.id)
            .where(*self._eligibility_filters(requirement))
            # Do not let a qualifying margin dominate all candidate recall.  The
            # service applies stable, explainable recall buckets below.
            .order_by(Product.id)
            .limit(500)
        )
        if category_paths:
            path_conditions = []
            for path in category_paths:
                parts = []
                if path.level1_name:
                    parts.append(Product.category_level1_name == path.level1_name)
                if path.level2_name:
                    parts.append(Product.category_level2_name == path.level2_name)
                if path.level3_name:
                    parts.append(Product.category_level3_name == path.level3_name)
                path_conditions.append(and_(*parts))
            statement = statement.where(or_(*path_conditions))
        rows = [(row[0], row[1]) for row in (await self.session.execute(statement)).all()]
        normalized_keywords = tuple(value.casefold() for value in keywords if value.strip())
        normalized_brands = tuple(value.casefold() for value in preferred_brands if value.strip())

        def bucket(
            row: tuple[Product, Supplier],
        ) -> tuple[int, bool, Decimal | int, int, bool, uuid.UUID]:
            product, _ = row
            searchable = " ".join(
                str(value or "")
                for value in (
                    product.product_name,
                    product.sku,
                    product.brand,
                    product.model,
                    product.product_specification,
                    product.selling_points,
                    product.category_level1_name,
                    product.category_level2_name,
                    product.category_level3_name,
                )
            ).casefold()
            keyword_match = bool(normalized_keywords) and any(
                key in searchable for key in normalized_keywords
            )
            brand_match = bool(normalized_brands) and any(
                key in str(product.brand or "").casefold() for key in normalized_brands
            )
            # Stable buckets, not a synthetic score: keyword, preferred brand,
            # actual discount, sales, then the remaining eligible products.  A
            # discount rate is agreement/self-operated price, so lower is stronger.
            return (
                (
                    0
                    if keyword_match
                    else 1 if brand_match else 2 if product.discount_rate is not None else 3
                ),
                product.discount_rate is None,
                product.discount_rate if product.discount_rate is not None else 0,
                -(product.sales_volume or 0),
                product.jd_price is None,
                product.id,
            )

        prioritized = sorted(rows, key=bucket)
        # Keyword misses must still receive category+hard-constraint fallback.
        return prioritized

    async def eligible_products_by_ids(
        self, requirement: ParsedRequirement, product_ids: Sequence[uuid.UUID]
    ) -> list[tuple[Product, Supplier]]:
        if not product_ids:
            return []
        rows = await self.session.execute(
            select(Product, Supplier)
            .join(Supplier, Product.source_supplier_id == Supplier.id)
            .where(Product.id.in_(product_ids), *self._eligibility_filters(requirement))
        )
        return [(row[0], row[1]) for row in rows]

    async def candidates(
        self, run_id: uuid.UUID
    ) -> list[tuple[RecommendationCandidate, RecommendationConfirmation | None]]:
        rows = await self.session.execute(
            select(RecommendationCandidate, RecommendationConfirmation)
            .outerjoin(
                RecommendationConfirmation,
                RecommendationConfirmation.candidate_id == RecommendationCandidate.id,
            )
            .where(RecommendationCandidate.run_id == run_id)
            .order_by(RecommendationCandidate.rank)
        )
        return [(row[0], row[1]) for row in rows]

    async def candidate_with_run_for_update(
        self, candidate_id: uuid.UUID
    ) -> (
        tuple[RecommendationCandidate, RecommendationRun, RecommendationConfirmation | None] | None
    ):
        row = (
            await self.session.execute(
                select(RecommendationCandidate, RecommendationRun, RecommendationConfirmation)
                .join(RecommendationRun, RecommendationRun.id == RecommendationCandidate.run_id)
                .outerjoin(
                    RecommendationConfirmation,
                    RecommendationConfirmation.candidate_id == RecommendationCandidate.id,
                )
                .where(RecommendationCandidate.id == candidate_id)
                .with_for_update()
            )
        ).first()
        if row is None:
            return None
        return cast(
            tuple[RecommendationCandidate, RecommendationRun, RecommendationConfirmation | None],
            tuple(row),
        )

    async def candidates_with_confirmations_for_update(
        self, run_id: uuid.UUID, candidate_ids: Sequence[uuid.UUID]
    ) -> list[tuple[RecommendationCandidate, RecommendationConfirmation | None]]:
        rows = await self.session.execute(
            select(RecommendationCandidate, RecommendationConfirmation)
            .outerjoin(
                RecommendationConfirmation,
                RecommendationConfirmation.candidate_id == RecommendationCandidate.id,
            )
            .where(
                RecommendationCandidate.run_id == run_id,
                RecommendationCandidate.id.in_(candidate_ids),
            )
            .order_by(RecommendationCandidate.rank)
            .with_for_update()
        )
        return [(row[0], row[1]) for row in rows]

    async def confirmed_candidates_for_export(
        self, run_id: uuid.UUID
    ) -> list[tuple[RecommendationCandidate, RecommendationConfirmation]]:
        rows = await self.session.execute(
            select(RecommendationCandidate, RecommendationConfirmation)
            .join(
                RecommendationConfirmation,
                RecommendationConfirmation.candidate_id == RecommendationCandidate.id,
            )
            .where(RecommendationCandidate.run_id == run_id)
            .order_by(RecommendationCandidate.rank)
            .with_for_update()
        )
        return [(row[0], row[1]) for row in rows]

    async def next_export_version(self, project_id: uuid.UUID) -> int:
        latest = await self.session.scalar(
            select(func.max(RecommendationExport.version_no)).where(
                RecommendationExport.project_id == project_id,
            )
        )
        return int(latest or 0) + 1

    async def export_file_for_run(
        self, run_id: uuid.UUID, file_id: uuid.UUID
    ) -> BidProjectFile | None:
        return cast(
            BidProjectFile | None,
            await self.session.scalar(
                select(BidProjectFile)
                .join(
                    RecommendationExport,
                    RecommendationExport.export_file_id == BidProjectFile.id,
                )
                .where(RecommendationExport.run_id == run_id, BidProjectFile.id == file_id)
            ),
        )

    @staticmethod
    def _eligibility_filters(requirement: ParsedRequirement) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = [
            Product.status == ProductStatus.ACTIVE,
            Supplier.archive_status == ArchiveStatus.ARCHIVED,
            Supplier.cooperation_status == CooperationStatus.NORMAL,
            Supplier.is_deleted.is_(False),
        ]
        if requirement.gross_margin_min is not None:
            filters.append(Product.gross_margin >= requirement.gross_margin_min)
        if requirement.jd_price_min is not None:
            filters.append(Product.jd_price >= requirement.jd_price_min)
        if requirement.jd_price_max is not None:
            filters.append(Product.jd_price <= requirement.jd_price_max)
        explicit_categories = (
            requirement.explicit_category_keywords or requirement.category_keywords
        )
        if explicit_categories:
            filters.append(
                or_(
                    *[
                        or_(
                            Product.category_level1_name.contains(keyword),
                            Product.category_level2_name.contains(keyword),
                            Product.category_level3_name.contains(keyword),
                        )
                        for keyword in explicit_categories
                    ]
                )
            )
        required_brands = requirement.required_brands or requirement.brand_keywords
        if required_brands:
            filters.append(
                or_(*[Product.brand.contains(keyword) for keyword in required_brands])
            )
        if requirement.excluded_brands:
            filters.extend(
                or_(Product.brand.is_(None), ~Product.brand.contains(keyword))
                for keyword in requirement.excluded_brands
            )
        if requirement.excluded_category_keywords:
            for keyword in requirement.excluded_category_keywords:
                filters.append(
                    and_(
                        or_(
                            Product.category_level1_name.is_(None),
                            ~Product.category_level1_name.contains(keyword),
                        ),
                        or_(
                            Product.category_level2_name.is_(None),
                            ~Product.category_level2_name.contains(keyword),
                        ),
                        or_(
                            Product.category_level3_name.is_(None),
                            ~Product.category_level3_name.contains(keyword),
                        ),
                    )
                )
        return filters
