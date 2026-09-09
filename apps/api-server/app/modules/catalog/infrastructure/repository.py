import uuid
from typing import cast

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import PageParams
from app.modules.catalog.infrastructure.models import Category, Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def by_id(self, product_id: uuid.UUID) -> Product | None:
        statement = select(Product).where(Product.id == product_id)
        return cast(Product | None, await self.session.scalar(statement))

    async def by_id_for_update(self, product_id: uuid.UUID) -> Product | None:
        statement = select(Product).where(Product.id == product_id).with_for_update()
        return cast(Product | None, await self.session.scalar(statement))

    async def category_by_id(self, category_id: uuid.UUID) -> Category | None:
        statement = select(Category).where(Category.id == category_id)
        return cast(Category | None, await self.session.scalar(statement))

    async def list(
        self,
        page_params: PageParams,
        *,
        keyword: str | None,
        category_id: uuid.UUID | None,
    ) -> tuple[list[Product], int]:
        statement: Select[tuple[Product]] = select(Product)
        count_statement = select(func.count()).select_from(Product)
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
        statement = (
            statement.order_by(Product.updated_at.desc(), Product.id.desc())
            .offset((page_params.page - 1) * page_params.page_size)
            .limit(page_params.page_size)
        )
        products = list((await self.session.scalars(statement)).all())
        total = cast(int, await self.session.scalar(count_statement))
        return products, total
