import uuid
from typing import cast

from sqlalchemy import Select, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.contracts import PageParams
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Category, Product, ProductImportTask
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
        category_id: uuid.UUID | None,
        source_supplier_id: uuid.UUID | None,
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
            )
            statement = statement.where(criteria)
            count_statement = count_statement.where(criteria)
        if category_id:
            statement = statement.where(Product.category_id == category_id)
            count_statement = count_statement.where(Product.category_id == category_id)
        if source_supplier_id:
            statement = statement.where(Product.source_supplier_id == source_supplier_id)
            count_statement = count_statement.where(
                Product.source_supplier_id == source_supplier_id
            )
        statement = (
            statement.order_by(Product.updated_at.desc(), Product.id.desc())
            .offset((page_params.page - 1) * page_params.page_size)
            .limit(page_params.page_size)
        )
        products = list((await self.session.scalars(statement)).all())
        total = cast(int, await self.session.scalar(count_statement))
        return products, total
