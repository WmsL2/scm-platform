import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, cast

from sqlalchemy import Select, and_, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.common.contracts import PageParams
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import (
    Category,
    Product,
    ProductImportRow,
    ProductImportTask,
)
from app.modules.supplier.domain.rules import CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_id(self, product_id: uuid.UUID) -> Product | None:
        statement = select(Product).join(Supplier).where(
            Product.id == product_id,
            Product.status == ProductStatus.ACTIVE,
            Supplier.is_deleted.is_(False),
            Supplier.cooperation_status == CooperationStatus.NORMAL,
        )
        return cast(Product | None, await self.session.scalar(statement))

    async def by_id_for_update(self, product_id: uuid.UUID) -> Product | None:
        statement = (
            select(Product)
            .join(Supplier)
            .where(
                Product.id == product_id,
                Product.status == ProductStatus.ACTIVE,
                Supplier.is_deleted.is_(False),
                Supplier.cooperation_status == CooperationStatus.NORMAL,
            )
            .with_for_update()
        )
        return cast(Product | None, await self.session.scalar(statement))

    async def by_id_any_status_for_update(self, product_id: uuid.UUID) -> Product | None:
        statement = select(Product).where(Product.id == product_id).with_for_update()
        return cast(Product | None, await self.session.scalar(statement))

    async def category_by_id(self, category_id: uuid.UUID) -> Category | None:
        statement = select(Category).where(Category.id == category_id)
        return cast(Category | None, await self.session.scalar(statement))

    async def active_categories_by_path(
        self, level1_name: str, level2_name: str, level3_name: str
    ) -> list[Category]:
        statement = select(Category).where(
            Category.is_active.is_(True),
            Category.level1_name == level1_name,
            Category.level2_name == level2_name,
            Category.level3_name == level3_name,
        )
        return list((await self.session.scalars(statement)).all())

    async def mall_categories(self) -> list[Category]:
        statement = select(Category).where(Category.source_type == "MALL_LEVEL3")
        return list((await self.session.scalars(statement)).all())

    async def active_mall_categories_by_ids(
        self, category_ids: set[uuid.UUID], *, for_update: bool = False
    ) -> dict[uuid.UUID, Category]:
        if not category_ids:
            return {}
        statement = select(Category).where(
            Category.id.in_(category_ids),
            Category.source_type == "MALL_LEVEL3",
            Category.is_active.is_(True),
        )
        if for_update:
            statement = statement.with_for_update()
        categories = list((await self.session.scalars(statement)).all())
        return {category.id: category for category in categories}

    async def active_category_by_id(self, category_id: uuid.UUID) -> Category | None:
        statement = select(Category).where(Category.id == category_id, Category.is_active.is_(True))
        return cast(Category | None, await self.session.scalar(statement))

    async def import_task_by_id(self, task_id: uuid.UUID) -> ProductImportTask | None:
        statement = (
            select(ProductImportTask)
            .options(
                selectinload(ProductImportTask.rows),
                selectinload(ProductImportTask.supplier_matches),
            )
            .where(ProductImportTask.id == task_id)
        )
        return cast(ProductImportTask | None, await self.session.scalar(statement))

    async def import_task_by_id_for_update(self, task_id: uuid.UUID) -> ProductImportTask | None:
        statement = (
            select(ProductImportTask)
            .options(
                selectinload(ProductImportTask.rows),
                selectinload(ProductImportTask.supplier_matches),
            )
            .where(ProductImportTask.id == task_id)
            .with_for_update()
        )
        return cast(ProductImportTask | None, await self.session.scalar(statement))

    async def temporary_media_cleanup_tasks_for_update(
        self, *, stale_before: datetime
    ) -> list[ProductImportTask]:
        statement = (
            select(ProductImportTask)
            .options(selectinload(ProductImportTask.rows))
            .where(
                or_(
                    and_(
                        ProductImportTask.status.in_(
                            (
                                "VALIDATED",
                                "NEEDS_RESOLUTION",
                                "READY_TO_CONFIRM",
                                "PARTIALLY_CONFIRMED",
                            )
                        ),
                        ProductImportTask.created_at < stale_before,
                    ),
                    and_(
                        ProductImportTask.status == "EXPIRED",
                        or_(
                            ProductImportTask.source_file_storage_key.is_not(None),
                            select(ProductImportRow.id)
                            .where(
                                ProductImportRow.import_task_id == ProductImportTask.id,
                                ProductImportRow.image_storage_key.is_not(None),
                            )
                            .exists(),
                        ),
                    ),
                    and_(
                        ProductImportTask.status == "CONFIRMED",
                        ProductImportTask.source_file_storage_key.is_not(None),
                    ),
                )
            )
            .with_for_update()
        )
        return list((await self.session.scalars(statement)).all())

    async def products_by_supplier_sku(
        self, keys: set[tuple[uuid.UUID, str]], *, for_update: bool = False
    ) -> dict[tuple[uuid.UUID, str], Product]:
        if not keys:
            return {}
        statement = select(Product).where(
            tuple_(Product.source_supplier_id, Product.sku).in_(keys)
        )
        if for_update:
            statement = statement.with_for_update()
        products = list((await self.session.scalars(statement)).all())
        return {
            (product.source_supplier_id, product.sku): product
            for product in products
            if product.sku is not None
        }

    async def other_product_with_supplier_sku(
        self, *, product_id: uuid.UUID, supplier_id: uuid.UUID, sku: str
    ) -> Product | None:
        statement = select(Product).where(
            Product.id != product_id,
            Product.source_supplier_id == supplier_id,
            Product.sku == sku,
        )
        return cast(Product | None, await self.session.scalar(statement))

    async def list(
        self,
        page_params: PageParams,
        *,
        keyword: str | None,
        company_name: str | None,
        purchasing_agent: str | None,
        brand: str | None,
        supplier_name: str | None,
        source_supplier_id: uuid.UUID | None,
        category_level1_name: str | None,
        category_level2_name: str | None,
        category_id: uuid.UUID | None,
        category_ids: set[uuid.UUID],
        category_level1_names: set[str],
        category_level2_paths: set[tuple[str, str]],
        cost_price_min: Decimal | None,
        cost_price_max: Decimal | None,
        agreement_price_min: Decimal | None,
        agreement_price_max: Decimal | None,
        discount_rate_min: Decimal | None,
        discount_rate_max: Decimal | None,
        sales_volume_min: int | None,
        sales_volume_max: int | None,
        status: ProductStatus,
    ) -> tuple[list[Product], int]:
        supplier_criteria = (
            (
                Supplier.is_deleted.is_(False),
                Supplier.cooperation_status == CooperationStatus.NORMAL,
            )
            if status == ProductStatus.ACTIVE
            else ()
        )
        statement: Select[tuple[Product]] = select(Product).join(Supplier).where(
            Product.status == status, *supplier_criteria
        )
        count_statement = (
            select(func.count())
            .select_from(Product)
            .join(Supplier)
            .where(Product.status == status, *supplier_criteria)
        )
        if keyword:
            criteria = or_(
                Product.brand.contains(keyword),
                Product.model.contains(keyword),
                Product.sku.contains(keyword),
                Product.product_name.contains(keyword),
                Product.item_number.contains(keyword),
                Product.barcode_text.contains(keyword),
                Product.product_specification.contains(keyword),
                Product.selling_points.contains(keyword),
                Product.category_level1_name.contains(keyword),
                Product.category_level2_name.contains(keyword),
                Product.category_level3_name.contains(keyword),
                Product.company_name.contains(keyword),
                Product.purchasing_agent.contains(keyword),
                Supplier.supplier_name.contains(keyword),
            )
            statement = statement.where(criteria)
            count_statement = count_statement.where(criteria)
        if category_id:
            statement = statement.where(Product.category_id == category_id)
            count_statement = count_statement.where(Product.category_id == category_id)
        category_selection_criteria: List[ColumnElement[bool]] = []
        if category_ids:
            category_selection_criteria.append(Product.category_id.in_(category_ids))
        if category_level1_names:
            category_selection_criteria.append(
                Product.category_level1_name.in_(category_level1_names)
            )
        if category_level2_paths:
            category_selection_criteria.append(or_(*[
                and_(Product.category_level1_name == level1, Product.category_level2_name == level2)
                for level1, level2 in category_level2_paths
            ]))
        if category_selection_criteria:
            category_criterion = or_(*category_selection_criteria)
            statement = statement.where(category_criterion)
            count_statement = count_statement.where(category_criterion)
        if source_supplier_id:
            statement = statement.where(Product.source_supplier_id == source_supplier_id)
            count_statement = count_statement.where(
                Product.source_supplier_id == source_supplier_id
            )
        filters = (
            (company_name, Product.company_name.contains),
            (purchasing_agent, Product.purchasing_agent.contains),
            (brand, Product.brand.contains),
            (supplier_name, Supplier.supplier_name.contains),
            (category_level1_name, Product.category_level1_name.__eq__),
            (category_level2_name, Product.category_level2_name.__eq__),
        )
        for value, operation in filters:
            if value:
                criterion = operation(value)
                statement = statement.where(criterion)
                count_statement = count_statement.where(criterion)
        range_criteria = []
        if cost_price_min is not None:
            range_criteria.append(Product.cost_price >= cost_price_min)
        if cost_price_max is not None:
            range_criteria.append(Product.cost_price <= cost_price_max)
        if agreement_price_min is not None:
            range_criteria.append(Product.agreement_price >= agreement_price_min)
        if agreement_price_max is not None:
            range_criteria.append(Product.agreement_price <= agreement_price_max)
        if discount_rate_min is not None:
            range_criteria.append(Product.discount_rate >= discount_rate_min)
        if discount_rate_max is not None:
            range_criteria.append(Product.discount_rate <= discount_rate_max)
        if sales_volume_min is not None:
            range_criteria.append(Product.sales_volume >= sales_volume_min)
        if sales_volume_max is not None:
            range_criteria.append(Product.sales_volume <= sales_volume_max)
        if range_criteria:
            statement = statement.where(*range_criteria)
            count_statement = count_statement.where(*range_criteria)
        statement = (
            statement.order_by(Product.updated_at.desc(), Product.id.desc())
            .offset((page_params.page - 1) * page_params.page_size)
            .limit(page_params.page_size)
        )
        products = list((await self.session.scalars(statement)).all())
        total = cast(int, await self.session.scalar(count_statement))
        return products, total
