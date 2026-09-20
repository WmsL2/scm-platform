import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, cast

from sqlalchemy import Select, and_, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.common.contracts import PageParams
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import (
    Product,
    ProductImportRow,
    ProductImportTask,
)
from app.modules.supplier.domain.rules import CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier

PRODUCT_IMPORT_PRODUCT_LOOKUP_BATCH_SIZE = 500


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_id(self, product_id: uuid.UUID) -> Product | None:
        statement = (
            select(Product)
            .join(Supplier)
            .where(
                Product.id == product_id,
                Product.status == ProductStatus.ACTIVE,
                Supplier.is_deleted.is_(False),
                Supplier.cooperation_status == CooperationStatus.NORMAL,
            )
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

    async def category_filter_options(
        self,
        *,
        level: Literal["LEVEL1", "LEVEL2", "LEVEL3"],
        keyword: str | None,
        offset: int,
        limit: int,
        level1_names: set[str],
        level2_paths: set[tuple[str, str]],
        status: ProductStatus,
    ) -> tuple[list[tuple[str, ...]], bool]:
        columns = (
            (Product.category_level1_name,)
            if level == "LEVEL1"
            else (Product.category_level1_name, Product.category_level2_name)
            if level == "LEVEL2"
            else (
                Product.category_level1_name,
                Product.category_level2_name,
                Product.category_level3_name,
            )
        )
        supplier_criteria = (
            (
                Supplier.is_deleted.is_(False),
                Supplier.cooperation_status == CooperationStatus.NORMAL,
            )
            if status == ProductStatus.ACTIVE
            else ()
        )
        category_criteria = [Product.category_level1_name.is_not(None)]
        if level in {"LEVEL2", "LEVEL3"}:
            category_criteria.append(Product.category_level2_name.is_not(None))
        if level == "LEVEL3":
            category_criteria.append(Product.category_level3_name.is_not(None))
        statement = (
            select(*columns)
            .select_from(Product)
            .join(Supplier)
            .where(
                Product.status == status,
                *category_criteria,
                *supplier_criteria,
            )
        )
        if keyword:
            searchable_columns = columns
            statement = statement.where(
                or_(*[column.contains(keyword) for column in searchable_columns])
            )
        parent_criteria: list[ColumnElement[bool]] = []
        if level != "LEVEL1" and level1_names:
            parent_criteria.append(Product.category_level1_name.in_(level1_names))
        if level == "LEVEL3" and level2_paths:
            parent_criteria.append(
                or_(
                    *[
                        and_(
                            Product.category_level1_name == level1_name,
                            Product.category_level2_name == level2_name,
                        )
                        for level1_name, level2_name in level2_paths
                    ]
                )
            )
        if parent_criteria:
            statement = statement.where(or_(*parent_criteria))
        rows = list(
            (
                await self.session.execute(
                    statement.distinct().order_by(*columns).offset(offset).limit(limit + 1)
                )
            ).tuples()
        )
        return [tuple(value for value in row if value is not None) for row in rows[:limit]], len(
            rows
        ) > limit

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

    async def import_task_summary_by_id(self, task_id: uuid.UUID) -> ProductImportTask | None:
        statement = (
            select(ProductImportTask)
            .options(
                noload(ProductImportTask.rows),
                selectinload(ProductImportTask.supplier_matches),
            )
            .where(ProductImportTask.id == task_id)
        )
        return cast(ProductImportTask | None, await self.session.scalar(statement))

    async def import_rows_page(
        self,
        task_id: uuid.UUID,
        page_params: PageParams,
        *,
        row_status: str,
    ) -> tuple[list[ProductImportRow], int]:
        criteria = [ProductImportRow.import_task_id == task_id]
        if row_status == "PASSED":
            criteria.extend(
                (
                    ProductImportRow.is_valid.is_(True),
                    ProductImportRow.is_imported.is_(False),
                    ProductImportRow.write_action == "CREATE",
                )
            )
        elif row_status == "UPDATE":
            criteria.extend(
                (
                    ProductImportRow.is_valid.is_(True),
                    ProductImportRow.is_imported.is_(False),
                    ProductImportRow.write_action == "UPDATE",
                )
            )
        elif row_status == "FAILED":
            criteria.extend(
                (
                    ProductImportRow.is_valid.is_(False),
                    ProductImportRow.is_imported.is_(False),
                )
            )
        statement = (
            select(ProductImportRow)
            .where(*criteria)
            .order_by(ProductImportRow.source_row_number, ProductImportRow.id)
            .offset((page_params.page - 1) * page_params.page_size)
            .limit(page_params.page_size)
        )
        count_statement = select(func.count()).select_from(ProductImportRow).where(*criteria)
        rows = list((await self.session.scalars(statement)).all())
        total = cast(int, await self.session.scalar(count_statement))
        return rows, total

    async def failed_import_rows(self, task_id: uuid.UUID) -> list[ProductImportRow]:
        statement = (
            select(ProductImportRow)
            .where(
                ProductImportRow.import_task_id == task_id,
                ProductImportRow.is_valid.is_(False),
                ProductImportRow.is_imported.is_(False),
            )
            .order_by(ProductImportRow.source_row_number, ProductImportRow.id)
        )
        return list((await self.session.scalars(statement)).all())

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
        ordered_keys = sorted(keys, key=lambda item: (str(item[0]), item[1]))
        products_by_key: dict[tuple[uuid.UUID, str], Product] = {}
        # A giant tuple IN (...) makes MySQL's range optimizer exceed its default 8MB
        # budget on real workbooks. Keep the key batches sorted so concurrent confirms
        # acquire matching product locks in a stable order.
        for offset in range(0, len(ordered_keys), PRODUCT_IMPORT_PRODUCT_LOOKUP_BATCH_SIZE):
            key_batch = ordered_keys[offset : offset + PRODUCT_IMPORT_PRODUCT_LOOKUP_BATCH_SIZE]
            statement = (
                select(Product)
                .where(tuple_(Product.source_supplier_id, Product.sku).in_(key_batch))
                .order_by(Product.source_supplier_id, Product.sku, Product.id)
            )
            if for_update:
                statement = statement.with_for_update()
            products = list((await self.session.scalars(statement)).all())
            products_by_key.update(
                {
                    (product.source_supplier_id, product.sku): product
                    for product in products
                    if product.sku is not None
                }
            )
        return products_by_key

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
        category_level1_names: set[str],
        category_level2_paths: set[tuple[str, str]],
        category_level3_paths: set[tuple[str, str, str]],
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
        statement: Select[tuple[Product]] = (
            select(Product).join(Supplier).where(Product.status == status, *supplier_criteria)
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
        category_selection_criteria: List[ColumnElement[bool]] = []
        if category_level1_names:
            category_selection_criteria.append(
                Product.category_level1_name.in_(category_level1_names)
            )
        if category_level2_paths:
            category_selection_criteria.append(
                or_(
                    *[
                        and_(
                            Product.category_level1_name == level1,
                            Product.category_level2_name == level2,
                        )
                        for level1, level2 in category_level2_paths
                    ]
                )
            )
        if category_level3_paths:
            category_selection_criteria.append(
                or_(
                    *[
                        and_(
                            Product.category_level1_name == level1,
                            Product.category_level2_name == level2,
                            Product.category_level3_name == level3,
                        )
                        for level1, level2, level3 in category_level3_paths
                    ]
                )
            )
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
