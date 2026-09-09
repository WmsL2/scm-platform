import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams, PageResult
from app.core.transaction import transaction_scope
from app.modules.catalog.domain.pricing import PricingCalculationError, calculate_product_pricing
from app.modules.catalog.infrastructure.models import Category, Product
from app.modules.catalog.infrastructure.repository import ProductRepository
from app.modules.catalog.schemas import (
    CategoryResponse,
    ProductCostUpdateRequest,
    ProductDetailResponse,
    ProductListItem,
)
from app.modules.supplier.infrastructure.repository import SupplierRepository


class ProductService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProductRepository(session)
        self.supplier_repository = SupplierRepository(session)

    async def list(
        self,
        page_params: PageParams,
        *,
        keyword: str | None,
        category_id: uuid.UUID | None,
    ) -> PageResult[ProductListItem]:
        products, total = await self.repository.list(
            page_params,
            keyword=keyword.strip() if keyword else None,
            category_id=category_id,
        )
        return PageResult(
            items=[await self._list_item(product) for product in products],
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def get(self, product_id: uuid.UUID) -> ProductDetailResponse:
        product = await self.repository.by_id(product_id)
        if product is None:
            raise AppError("PRODUCT_NOT_FOUND", "Product not found", 404)
        return await self._detail(product)

    async def update_cost(
        self,
        product_id: uuid.UUID,
        payload: ProductCostUpdateRequest,
        actor_id: uuid.UUID,
    ) -> ProductDetailResponse:
        async with transaction_scope(self.session):
            product = await self.repository.by_id_for_update(product_id)
            if product is None:
                raise AppError("PRODUCT_NOT_FOUND", "Product not found", 404)
            category = await self.repository.category_by_id(product.category_id)
            if category is None:
                raise AppError("PRODUCT_CATEGORY_NOT_FOUND", "Product category not found", 409)
            if product.jd_price is None or product.jd_self_operated_price is None:
                raise AppError(
                    "PRODUCT_PRICING_INPUT_MISSING",
                    "Product pricing inputs are incomplete",
                    409,
                )
            try:
                result = calculate_product_pricing(
                    cost_price=payload.cost_price,
                    jd_price=product.jd_price,
                    jd_self_operated_price=product.jd_self_operated_price,
                    deduction_rate=category.deduction_rate,
                )
            except PricingCalculationError as exc:
                raise AppError("PRODUCT_PRICING_CALCULATION_FAILED", str(exc), 422) from exc
            product.cost_price = payload.cost_price
            product.market_price = result.market_price
            product.agreement_price = result.agreement_price
            product.agreement_purchase_price = result.agreement_purchase_price
            product.profit = result.profit
            product.jd_margin = result.jd_margin
            product.deduction_review = result.deduction_review
            product.gross_margin = result.gross_margin
            product.discount_rate = result.discount_rate
            product.price_inflation_rate = result.price_inflation_rate
            product.deduction_rate = category.deduction_rate
            product.updated_by = actor_id
            await self.session.flush()
            return await self._detail(product, category=category)

    async def _list_item(self, product: Product) -> ProductListItem:
        category = await self._category(product.category_id)
        supplier = await self.supplier_repository.active_by_id(product.source_supplier_id)
        return ProductListItem(
            id=product.id,
            listed_at=product.listed_at,
            brand=product.brand,
            model=product.model,
            sku=product.sku,
            product_name=product.product_name,
            item_number=product.item_number,
            category_id=product.category_id,
            category_path=self._category_path(category),
            source_supplier_id=product.source_supplier_id,
            source_supplier_name=supplier.supplier_name if supplier else None,
            cost_price=product.cost_price,
            agreement_price=product.agreement_price,
            jd_price=product.jd_price,
            updated_at=product.updated_at,
        )

    async def _detail(
        self, product: Product, *, category: Category | None = None
    ) -> ProductDetailResponse:
        category = category or await self._category(product.category_id)
        supplier = await self.supplier_repository.active_by_id(product.source_supplier_id)
        return ProductDetailResponse(
            id=product.id,
            listed_at=product.listed_at,
            brand=product.brand,
            image_reference=product.image_reference,
            model=product.model,
            sku=product.sku,
            product_name=product.product_name,
            category=CategoryResponse.model_validate(category),
            item_number=product.item_number,
            jd_same_product_url=product.jd_same_product_url,
            cost_price=product.cost_price,
            market_price=product.market_price,
            jd_price=product.jd_price,
            agreement_price=product.agreement_price,
            agreement_purchase_price=product.agreement_purchase_price,
            profit=product.profit,
            jd_margin=product.jd_margin,
            purchasing_agent=product.purchasing_agent,
            source_supplier_id=product.source_supplier_id,
            source_supplier_name=supplier.supplier_name if supplier else None,
            barcode_text=product.barcode_text,
            deduction_review=product.deduction_review,
            product_specification=product.product_specification,
            selling_points=product.selling_points,
            gross_margin=product.gross_margin,
            remark=product.remark,
            discount_rate=product.discount_rate,
            restricted_regions=product.restricted_regions,
            jd_self_operated_price=product.jd_self_operated_price,
            reference_url=product.reference_url,
            storefront_type=product.storefront_type,
            price_inflation_rate=product.price_inflation_rate,
            deduction_rate=product.deduction_rate,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    async def _category(self, category_id: uuid.UUID) -> Category:
        category = await self.repository.category_by_id(category_id)
        if category is None:
            raise AppError("PRODUCT_CATEGORY_NOT_FOUND", "Product category not found", 409)
        return category

    @staticmethod
    def _category_path(category: Category) -> str:
        return " / ".join((category.level1_name, category.level2_name, category.level3_name))
