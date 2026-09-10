import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, PageParams, PageResult, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.catalog.application.import_service import ProductImportService
from app.modules.catalog.application.service import ProductService
from app.modules.catalog.schemas import (
    ProductCostUpdateRequest,
    ProductDetailResponse,
    ProductImportConfirmResponse,
    ProductImportPreviewResponse,
    ProductImportResolveSupplierRequest,
    ProductImportSupplierCandidateResponse,
    ProductListItem,
)

router = APIRouter(prefix="/products", tags=["products"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=ApiResponse[PageResult[ProductListItem]])
async def list_products(
    _: Annotated[CurrentUser, Depends(require_permission("product:list"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    category_id: uuid.UUID | None = None,
) -> ApiResponse[PageResult[ProductListItem]]:
    return success(
        await ProductService(session).list(page_params, keyword=keyword, category_id=category_id)
    )


@router.post("/imports/preview", response_model=ApiResponse[ProductImportPreviewResponse])
async def preview_product_import(
    file: Annotated[UploadFile, File(...)],
    current: Annotated[CurrentUser, Depends(require_permission("product:import"))],
    session: SessionDep,
) -> ApiResponse[ProductImportPreviewResponse]:
    return success(
        await ProductImportService(session).preview(
            file.filename or "product-import.xlsx", await file.read(), current.user_id
        )
    )


@router.get(
    "/imports/supplier-candidates",
    response_model=ApiResponse[list[ProductImportSupplierCandidateResponse]],
)
async def product_import_supplier_candidates(
    _: Annotated[CurrentUser, Depends(require_permission("product:import:resolve"))],
    session: SessionDep,
) -> ApiResponse[list[ProductImportSupplierCandidateResponse]]:
    return success(await ProductImportService(session).supplier_candidates())


@router.get("/imports/{task_id}", response_model=ApiResponse[ProductImportPreviewResponse])
async def get_product_import(
    task_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("product:import"))],
    session: SessionDep,
) -> ApiResponse[ProductImportPreviewResponse]:
    return success(await ProductImportService(session).get_preview(task_id))


@router.post(
    "/imports/{task_id}/supplier-matches/{match_id}/resolve",
    response_model=ApiResponse[ProductImportPreviewResponse],
)
async def resolve_product_import_supplier(
    task_id: uuid.UUID,
    match_id: uuid.UUID,
    payload: ProductImportResolveSupplierRequest,
    current: Annotated[CurrentUser, Depends(require_permission("product:import:resolve"))],
    session: SessionDep,
) -> ApiResponse[ProductImportPreviewResponse]:
    return success(
        await ProductImportService(session).resolve_supplier(
            task_id, match_id, payload, current.user_id
        )
    )


@router.post("/imports/{task_id}/confirm", response_model=ApiResponse[ProductImportConfirmResponse])
async def confirm_product_import(
    task_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("product:import"))],
    session: SessionDep,
) -> ApiResponse[ProductImportConfirmResponse]:
    return success(await ProductImportService(session).confirm(task_id, current.user_id))


@router.get("/{product_id}", response_model=ApiResponse[ProductDetailResponse])
async def get_product(
    product_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("product:detail"))],
    session: SessionDep,
) -> ApiResponse[ProductDetailResponse]:
    return success(await ProductService(session).get(product_id))


@router.patch("/{product_id}/cost-price", response_model=ApiResponse[ProductDetailResponse])
async def update_product_cost(
    product_id: uuid.UUID,
    payload: ProductCostUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("product:cost:update"))],
    session: SessionDep,
) -> ApiResponse[ProductDetailResponse]:
    return success(await ProductService(session).update_cost(product_id, payload, current.user_id))
