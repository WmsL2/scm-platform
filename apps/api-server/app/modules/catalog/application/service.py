import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import AppError, PageParams, PageResult
from app.core.transaction import transaction_scope
from app.infrastructure.adapters import ObjectStorage, get_object_storage
from app.modules.catalog.application.media import local_media_storage_key
from app.modules.catalog.application.product_category_filter import (
    parse_selection,
    selection_key,
)
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.infrastructure.models import Product, ProductPurgeAudit
from app.modules.catalog.infrastructure.repository import ProductRepository
from app.modules.catalog.schemas import (
    ProductCategoryFilterOptionPageResponse,
    ProductCategoryFilterOptionResponse,
    ProductCostUpdateRequest,
    ProductDetailResponse,
    ProductFilterOptionPageResponse,
    ProductFilterOptionResponse,
    ProductLifecycleResponse,
    ProductListItem,
    ProductPurgeResponse,
    ProductSourceSupplierCandidateResponse,
    ProductUpdateRequest,
)
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.infrastructure.models import Supplier
from app.modules.supplier.infrastructure.repository import SupplierRepository
from app.modules.system.repository import UserRepository


class ProductService:
    def __init__(self, session: AsyncSession, storage: ObjectStorage | None = None) -> None:
        self.session = session
        self.storage = storage or get_object_storage()
        self.repository = ProductRepository(session)
        self.supplier_repository = SupplierRepository(session)
        self.user_repository = UserRepository(session)

    async def list(
        self,
        page_params: PageParams,
        *,
        keyword: str | None,
        company_name: str | None,
        purchasing_agent: str | None,
        brand: str | None,
        supplier_name: str | None,
        company_names: List[str],
        purchasing_agents: List[str],
        brands: List[str],
        source_supplier_ids: List[uuid.UUID],
        source_supplier_id: uuid.UUID | None,
        category_level1_name: str | None,
        category_level2_name: str | None,
        category_selections: List[str],
        cost_price_min: Decimal | None,
        cost_price_max: Decimal | None,
        agreement_price_min: Decimal | None,
        agreement_price_max: Decimal | None,
        jd_price_min: Decimal | None,
        jd_price_max: Decimal | None,
        profit_min: Decimal | None,
        profit_max: Decimal | None,
        discount_rate_min: Decimal | None,
        discount_rate_max: Decimal | None,
        sales_volume_min: int | None,
        sales_volume_max: int | None,
        status: ProductStatus,
    ) -> PageResult[ProductListItem]:
        self._validate_range("cost_price", cost_price_min, cost_price_max)
        self._validate_range("agreement_price", agreement_price_min, agreement_price_max)
        self._validate_range("jd_price", jd_price_min, jd_price_max)
        self._validate_range("profit", profit_min, profit_max)
        self._validate_range("discount_rate", discount_rate_min, discount_rate_max)
        self._validate_range("sales_volume", sales_volume_min, sales_volume_max)
        level1_names, level2_paths, level3_paths = self._resolve_category_selections(
            category_selections
        )
        products, total = await self.repository.list(
            page_params,
            keyword=keyword.strip() if keyword else None,
            company_name=company_name.strip() if company_name else None,
            purchasing_agent=purchasing_agent.strip() if purchasing_agent else None,
            brand=brand.strip() if brand else None,
            supplier_name=supplier_name.strip() if supplier_name else None,
            company_names=self._normalize_multi_filter_values(company_names),
            purchasing_agents=self._normalize_multi_filter_values(purchasing_agents),
            brands=self._normalize_multi_filter_values(brands),
            source_supplier_ids=self._normalize_source_supplier_ids(source_supplier_ids),
            source_supplier_id=source_supplier_id,
            category_level1_name=category_level1_name,
            category_level2_name=category_level2_name,
            category_level1_names=level1_names,
            category_level2_paths=level2_paths,
            category_level3_paths=level3_paths,
            cost_price_min=cost_price_min,
            cost_price_max=cost_price_max,
            agreement_price_min=agreement_price_min,
            agreement_price_max=agreement_price_max,
            jd_price_min=jd_price_min,
            jd_price_max=jd_price_max,
            profit_min=profit_min,
            profit_max=profit_max,
            discount_rate_min=discount_rate_min,
            discount_rate_max=discount_rate_max,
            sales_volume_min=sales_volume_min,
            sales_volume_max=sales_volume_max,
            status=status,
        )

        usernames = await self.user_repository.usernames_by_ids(
            {
                user_id
                for product in products
                for user_id in (product.created_by, product.updated_by)
                if user_id is not None
            }
        )
        return PageResult(
            items=[await self._list_item(product, usernames) for product in products],
            total=total,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    @staticmethod
    def _normalize_multi_filter_values(values: List[str]) -> List[str]:
        result: List[str] = []
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in result:
                result.append(normalized)
        if len(result) > 50:
            raise AppError(
                "PRODUCT_FILTER_SELECTION_LIMIT_EXCEEDED",
                "A product filter accepts at most 50 selections",
                422,
            )
        return result

    @staticmethod
    def _normalize_source_supplier_ids(values: List[uuid.UUID]) -> List[uuid.UUID]:
        result = list(dict.fromkeys(values))
        if len(result) > 50:
            raise AppError(
                "PRODUCT_FILTER_SELECTION_LIMIT_EXCEEDED",
                "A product filter accepts at most 50 selections",
                422,
            )
        return result

    def _resolve_category_selections(
        self, selections: List[str]
    ) -> tuple[set[str], set[tuple[str, str]], set[tuple[str, str, str]]]:
        level1_names: set[str] = set()
        level2_paths: set[tuple[str, str]] = set()
        level3_paths: set[tuple[str, str, str]] = set()
        for selection in selections:
            try:
                parsed = parse_selection(selection)
            except ValueError as exc:
                raise AppError(
                    "PRODUCT_CATEGORY_SELECTION_INVALID", "Invalid category selection", 422
                ) from exc
            if parsed.level == "LEVEL1":
                level1_names.add(parsed.path[0])
            elif parsed.level == "LEVEL2":
                level2_paths.add((parsed.path[0], parsed.path[1]))
            else:
                level3_paths.add((parsed.path[0], parsed.path[1], parsed.path[2]))
        return level1_names, level2_paths, level3_paths

    async def category_filter_options(
        self,
        *,
        level: Literal["LEVEL1", "LEVEL2", "LEVEL3"],
        keyword: str | None,
        offset: int,
        limit: int,
        category_selections: List[str],
        status: ProductStatus,
    ) -> ProductCategoryFilterOptionPageResponse:
        level1_names, level2_paths, _ = self._resolve_category_selections(category_selections)
        rows, has_more = await self.repository.category_filter_options(
            level=level,
            keyword=keyword.strip() if keyword else None,
            offset=offset,
            limit=limit,
            level1_names=level1_names,
            level2_paths=level2_paths,
            status=status,
        )
        items: list[ProductCategoryFilterOptionResponse] = []
        for path in rows:
            level1_key = selection_key("LEVEL1", path[:1])
            level2_key = selection_key("LEVEL2", path[:2]) if len(path) >= 2 else level1_key
            items.append(
                ProductCategoryFilterOptionResponse(
                    selection_key=selection_key(level, path),
                    label=" / ".join(path),
                    level=level,
                    level1_selection_key=level1_key,
                    level2_selection_key=level2_key,
                    level1_label=path[0],
                    level2_label=" / ".join(path[:2]),
                )
            )
        return ProductCategoryFilterOptionPageResponse(items=items, has_more=has_more)

    async def filter_options(
        self,
        *,
        field: Literal["COMPANY", "PURCHASING_AGENT", "BRAND", "SUPPLIER"],
        keyword: str | None,
        offset: int,
        limit: int,
        status: ProductStatus,
    ) -> ProductFilterOptionPageResponse:
        rows, has_more = await self.repository.filter_options(
            field=field,
            keyword=keyword.strip() if keyword else None,
            offset=offset,
            limit=limit,
            status=status,
        )
        return ProductFilterOptionPageResponse(
            items=[ProductFilterOptionResponse(value=value, label=label) for value, label in rows],
            has_more=has_more,
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
            product.cost_price = payload.cost_price
            product.updated_by = actor_id
            await self.session.flush()
            return await self._detail(product)

    async def update_image(
        self,
        product_id: uuid.UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
        actor_id: uuid.UUID,
    ) -> ProductDetailResponse:
        allowed_types = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        suffix = allowed_types.get(content_type or "")
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        if suffix is None or Path(filename).suffix.lower() not in allowed_extensions:
            raise AppError(
                "PRODUCT_IMAGE_TYPE_INVALID",
                "Only JPG, PNG, WEBP or GIF is supported",
                422,
            )
        if not content:
            raise AppError("PRODUCT_IMAGE_EMPTY", "The image file is empty", 422)
        if len(content) > 10 * 1024 * 1024:
            raise AppError("PRODUCT_IMAGE_TOO_LARGE", "The image file exceeds 10 MB", 422)
        new_key = await self.storage.save(f"product-images/manual/{product_id}{suffix}", content)
        old_key: str | None = None
        try:
            async with transaction_scope(self.session):
                product = await self.repository.by_id_for_update(product_id)
                if product is None:
                    raise AppError("PRODUCT_NOT_FOUND", "Product not found", 404)
                old_key = self._local_media_key(product.image_reference)
                product.image_reference = f"local-media/{new_key}"
                product.updated_by = actor_id
                await self.session.flush()
                response = await self._detail(product)
        except Exception:
            await self.storage.delete(new_key)
            raise
        if old_key is not None and old_key != new_key:
            try:
                await self.storage.delete(old_key)
            except Exception:
                pass
        return response

    async def clear_image(
        self, product_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ProductDetailResponse:
        async with transaction_scope(self.session):
            product = await self.repository.by_id_for_update(product_id)
            if product is None:
                raise AppError("PRODUCT_NOT_FOUND", "Product not found", 404)
            old_key = self._local_media_key(product.image_reference)
            product.image_reference = None
            product.updated_by = actor_id
            await self.session.flush()
            response = await self._detail(product)
        if old_key is not None:
            try:
                await self.storage.delete(old_key)
            except Exception:
                pass
        return response

    async def disable(self, product_id: uuid.UUID, actor_id: uuid.UUID) -> ProductLifecycleResponse:
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

    async def enable(self, product_id: uuid.UUID, actor_id: uuid.UUID) -> ProductLifecycleResponse:
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

    async def _list_item(
        self, product: Product, usernames: dict[uuid.UUID, str]
    ) -> ProductListItem:
        supplier = await self.supplier_repository.active_by_id(product.source_supplier_id)
        return ProductListItem(
            id=product.id,
            company_name=product.company_name,
            listed_at=product.listed_at,
            brand=product.brand,
            image_reference=product.image_reference,
            model=product.model,
            sku=product.sku,
            product_name=product.product_name,
            item_number=product.item_number,
            jd_same_product_url=product.jd_same_product_url,
            category_path=self._category_path(product),
            source_supplier_id=product.source_supplier_id,
            source_supplier_name=supplier.supplier_name if supplier else None,
            cost_price=product.cost_price,
            agreement_price=product.agreement_price,
            jd_price=product.jd_price,
            market_price=product.market_price,
            agreement_purchase_price=product.agreement_purchase_price,
            profit=product.profit,
            jd_margin=product.jd_margin,
            deduction_review=product.deduction_review,
            gross_margin=product.gross_margin,
            purchasing_agent=product.purchasing_agent,
            barcode_text=product.barcode_text,
            certification_3c_code=product.certification_3c_code,
            product_specification=product.product_specification,
            selling_points=product.selling_points,
            packaging_list=product.packaging_list,
            warranty_period=product.warranty_period,
            restricted_regions=product.restricted_regions,
            jd_self_operated_price=product.jd_self_operated_price,
            storefront_type=product.storefront_type,
            reference_url=product.reference_url,
            sales_volume=product.sales_volume,
            positive_rating=product.positive_rating,
            discount_rate=product.discount_rate,
            price_inflation_rate=product.price_inflation_rate,
            tax_code=product.tax_code,
            invoice_name=product.invoice_name,
            tax_category=product.tax_category,
            shipping_courier=product.shipping_courier,
            after_sales_policy=product.after_sales_policy,
            remark=product.remark,
            status=product.status,
            created_by=product.created_by,
            created_by_username=usernames.get(product.created_by)
            if product.created_by is not None
            else None,
            created_at=product.created_at,
            updated_by=product.updated_by,
            updated_by_username=usernames.get(product.updated_by)
            if product.updated_by is not None
            else None,
            updated_at=product.updated_at,
        )

    async def _detail(self, product: Product) -> ProductDetailResponse:
        supplier = await self.supplier_repository.active_by_id(product.source_supplier_id)
        return ProductDetailResponse(
            id=product.id,
            company_name=product.company_name,
            listed_at=product.listed_at,
            brand=product.brand,
            image_reference=product.image_reference,
            model=product.model,
            sku=product.sku,
            product_name=product.product_name,
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
            certification_3c_code=product.certification_3c_code,
            deduction_review=product.deduction_review,
            product_specification=product.product_specification,
            selling_points=product.selling_points,
            packaging_list=product.packaging_list,
            warranty_period=product.warranty_period,
            gross_margin=product.gross_margin,
            remark=product.remark,
            discount_rate=product.discount_rate,
            restricted_regions=product.restricted_regions,
            jd_self_operated_price=product.jd_self_operated_price,
            reference_url=product.reference_url,
            storefront_type=product.storefront_type,
            sales_volume=product.sales_volume,
            positive_rating=product.positive_rating,
            price_inflation_rate=product.price_inflation_rate,
            deduction_rate=product.deduction_rate,
            tax_code=product.tax_code,
            invoice_name=product.invoice_name,
            tax_category=product.tax_category,
            shipping_courier=product.shipping_courier,
            after_sales_policy=product.after_sales_policy,
            status=product.status,
            created_at=product.created_at,
            updated_at=product.updated_at,
        )

    @staticmethod
    def _source_supplier_is_eligible(supplier: Supplier) -> bool:
        return (
            supplier.is_deleted is False
            and supplier.archive_status == ArchiveStatus.ARCHIVED
            and supplier.cooperation_status == CooperationStatus.NORMAL
        )

    @staticmethod
    def _category_path(product: Product) -> str:
        return " / ".join(
            value
            for value in (
                product.category_level1_name,
                product.category_level2_name,
                product.category_level3_name,
            )
            if value
        )

    @staticmethod
    def _validate_range(
        name: str, minimum: Decimal | int | None, maximum: Decimal | int | None
    ) -> None:
        if minimum is not None and maximum is not None and minimum > maximum:
            raise AppError(
                "PRODUCT_FILTER_RANGE_INVALID",
                f"{name} minimum must be less than or equal to maximum",
                422,
            )

    @staticmethod
    def _local_media_key(image_reference: str | None) -> str | None:
        return local_media_storage_key(image_reference)
