import uuid
from datetime import datetime
from typing import List

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams, PageResult
from app.core.transaction import transaction_scope
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.domain.pricing import PricingCalculationError, calculate_product_pricing
from app.modules.catalog.infrastructure.models import Category, Product, ProductPurgeAudit
from app.modules.catalog.infrastructure.repository import ProductRepository
from app.modules.catalog.schemas import (
    CategoryResponse,
    ProductCostUpdateRequest,
    ProductDetailResponse,
    ProductLifecycleResponse,
    ProductListItem,
    ProductPurgeResponse,
    ProductSourceSupplierCandidateResponse,
    ProductUpdateRequest,
)
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier
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
        source_supplier_id: uuid.UUID | None,
        status: ProductStatus,
    ) -> PageResult[ProductListItem]:
        products, total = await self.repository.list(
            page_params,
            keyword=keyword.strip() if keyword else None,
            category_id=category_id,
            source_supplier_id=source_supplier_id,
            status=status,
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

    async def source_supplier_candidates(self) -> List[ProductSourceSupplierCandidateResponse]:
        return [
            ProductSourceSupplierCandidateResponse(
                id=supplier.id,
                supplier_code=supplier.supplier_code,
                supplier_name=supplier.supplier_name,
                main_brands=supplier.main_brands,
            )
            for supplier in await self.supplier_repository.eligible_source_suppliers()
        ]

    async def update(
        self, product_id: uuid.UUID, payload: ProductUpdateRequest, actor_id: uuid.UUID
    ) -> ProductDetailResponse:
        async with transaction_scope(self.session):
            product = await self.repository.by_id_for_update(product_id)
            if product is None:
                raise AppError("PRODUCT_NOT_FOUND", "Product not found", 404)

            update_values = payload.model_dump(exclude_unset=True)
            source_supplier_id = update_values.get("source_supplier_id", product.source_supplier_id)
            if source_supplier_id is None:
                raise AppError(
                    "PRODUCT_SOURCE_SUPPLIER_REQUIRED", "Source supplier is required", 422
                )
            if source_supplier_id != product.source_supplier_id:
                supplier = await self.supplier_repository.active_by_id(source_supplier_id)
                if supplier is None or not self._source_supplier_is_eligible(supplier):
                    raise AppError(
                        "PRODUCT_SOURCE_SUPPLIER_INELIGIBLE",
                        "Only archived, normal and non-deleted suppliers may be selected",
                        409,
                    )

            sku = update_values.get("sku", product.sku)
            if sku is None:
                raise AppError("PRODUCT_SKU_REQUIRED", "SKU is required", 422)
            duplicate = await self.repository.other_product_with_supplier_sku(
                product_id=product.id, supplier_id=source_supplier_id, sku=sku
            )
            if duplicate is not None:
                raise AppError(
                    "PRODUCT_SUPPLIER_SKU_EXISTS",
                    "A product with this source supplier and SKU already exists",
                    409,
                )
            for field, value in update_values.items():
                setattr(product, field, value)
            product.updated_by = actor_id
            await self.session.flush()
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
            category = (
                await self.repository.category_by_id(product.category_id)
                if product.category_id is not None
                else None
            )
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

    async def disable(
        self, product_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ProductLifecycleResponse:
        async with transaction_scope(self.session):
            product = await self.repository.by_id_any_status_for_update(product_id)
            if product is None:
                raise AppError("PRODUCT_NOT_FOUND", "Product not found", 404)
            if product.status != ProductStatus.ACTIVE:
                raise AppError("PRODUCT_NOT_ACTIVE", "Product is not active", 409)
            product.status = ProductStatus.DISABLED
            product.disabled_by = actor_id
            product.disabled_at = datetime.now()
            product.updated_by = actor_id
        return ProductLifecycleResponse(id=product.id, status=product.status)

    async def enable(
        self, product_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ProductLifecycleResponse:
        async with transaction_scope(self.session):
            product = await self.repository.by_id_any_status_for_update(product_id)
            if product is None:
                raise AppError("PRODUCT_NOT_FOUND", "Product not found", 404)
            if product.status != ProductStatus.DISABLED:
                raise AppError("PRODUCT_NOT_DISABLED", "Product is not disabled", 409)
            supplier = await self.supplier_repository.active_by_id(product.source_supplier_id)
            if supplier is None or not self._source_supplier_is_eligible(supplier):
                raise AppError(
                    "PRODUCT_SOURCE_SUPPLIER_INELIGIBLE",
                    "The source supplier must be archived, normal and non-deleted before enabling",
                    409,
                )
            product.status = ProductStatus.ACTIVE
            product.disabled_by = None
            product.disabled_at = None
            product.updated_by = actor_id
        return ProductLifecycleResponse(id=product.id, status=product.status)

    async def purge(self, product_id: uuid.UUID, actor_id: uuid.UUID) -> ProductPurgeResponse:
        try:
            async with transaction_scope(self.session):
                product = await self.repository.by_id_any_status_for_update(product_id)
                if product is None:
                    raise AppError("PRODUCT_NOT_FOUND", "Product not found", 404)
                if product.status != ProductStatus.DISABLED:
                    raise AppError(
                        "PRODUCT_PURGE_REQUIRES_DISABLED",
                        "Only a disabled product can be permanently deleted",
                        409,
                    )
                self.session.add(
                    ProductPurgeAudit(
                        product_id=product.id,
                        source_supplier_id=product.source_supplier_id,
                        sku=product.sku,
                        product_name=product.product_name,
                        purged_by=actor_id,
                    )
                )
                await self.session.delete(product)
                await self.session.flush()
        except IntegrityError as exc:
            raise AppError(
                "PRODUCT_PURGE_REFERENCED",
                "The product is referenced and cannot be permanently deleted; disable it instead",
                409,
            ) from exc
        return ProductPurgeResponse(id=product_id)

    async def _list_item(self, product: Product) -> ProductListItem:
        category = await self._category(product.category_id)
        supplier = await self.supplier_repository.active_by_id(product.source_supplier_id)
        return ProductListItem(
            id=product.id,
            listed_at=product.listed_at,
            brand=product.brand,
            image_reference=product.image_reference,
            model=product.model,
            sku=product.sku,
            product_name=product.product_name,
            item_number=product.item_number,
            category_id=product.category_id,
            category_path=self._category_path(product, category),
            source_supplier_id=product.source_supplier_id,
            source_supplier_name=supplier.supplier_name if supplier else None,
            cost_price=product.cost_price,
            agreement_price=product.agreement_price,
            jd_price=product.jd_price,
            status=product.status,
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
            category=CategoryResponse.model_validate(category) if category else None,
            category_level1_name=product.category_level1_name,
            category_level2_name=product.category_level2_name,
            category_level3_name=product.category_level3_name,
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

    async def _category(self, category_id: uuid.UUID | None) -> Category | None:
        if category_id is None:
            return None
        category = await self.repository.category_by_id(category_id)
        return category

    @staticmethod
    def _source_supplier_is_eligible(supplier: Supplier) -> bool:
        return (
            supplier.is_deleted is False
            and supplier.archive_status == ArchiveStatus.ARCHIVED
            and supplier.cooperation_status == CooperationStatus.NORMAL
        )

    @staticmethod
    def _category_path(product: Product, category: Category | None) -> str:
        if category is not None:
            return " / ".join((category.level1_name, category.level2_name, category.level3_name))
        return " / ".join(
            value
            for value in (
                product.category_level1_name,
                product.category_level2_name,
                product.category_level3_name,
            )
            if value
        )
