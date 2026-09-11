import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, AppError, PageParams, PageResult, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.catalog.application.import_service import ProductImportService
from app.modules.catalog.application.service import ProductService
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.schemas import (
    ProductCostUpdateRequest,
    ProductDetailResponse,
    ProductImportConfirmResponse,
    ProductImportPreviewResponse,
    ProductImportResolveSupplierRequest,
    ProductImportSupplierCandidateResponse,
    ProductLifecycleResponse,
    ProductListItem,
    ProductPurgeRequest,
    ProductPurgeResponse,
    ProductSourceSupplierCandidateResponse,
    ProductUpdateRequest,
)

router = APIRouter(prefix="/products", tags=["products"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
PRODUCT_IMPORT_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1] / "resources" / "product-master-template.xlsx"
)


@router.get("", response_model=ApiResponse[PageResult[ProductListItem]])
async def list_products(
    current: Annotated[CurrentUser, Depends(require_permission("product:list"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    category_id: uuid.UUID | None = None,
    source_supplier_id: uuid.UUID | None = None,
    status: ProductStatus = ProductStatus.ACTIVE,
) -> ApiResponse[PageResult[ProductListItem]]:
    if status == ProductStatus.DISABLED and "product:disable" not in current.permissions:
        raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)
    return success(
        await ProductService(session).list(
            page_params,
            keyword=keyword,
            category_id=category_id,
            source_supplier_id=source_supplier_id,
            status=status,
        )
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


@router.get("/imports/template", response_class=FileResponse)
async def download_product_import_template(
    _: Annotated[CurrentUser, Depends(require_permission("product:import"))],
) -> FileResponse:
    if not PRODUCT_IMPORT_TEMPLATE_PATH.is_file():
        raise AppError("PRODUCT_IMPORT_TEMPLATE_UNAVAILABLE", "Import template is unavailable", 503)
    return FileResponse(
        PRODUCT_IMPORT_TEMPLATE_PATH,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="商品大表模板.xlsx",
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


@router.get(
    "/source-supplier-candidates",
    response_model=ApiResponse[list[ProductSourceSupplierCandidateResponse]],
)
async def source_supplier_candidates(
    _: Annotated[CurrentUser, Depends(require_permission("product:update"))],
    session: SessionDep,
) -> ApiResponse[list[ProductSourceSupplierCandidateResponse]]:
    return success(await ProductService(session).source_supplier_candidates())


@router.get("/{product_id}", response_model=ApiResponse[ProductDetailResponse])
async def get_product(
    product_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("product:detail"))],
    session: SessionDep,
) -> ApiResponse[ProductDetailResponse]:
    return success(await ProductService(session).get(product_id))


@router.patch("/{product_id}", response_model=ApiResponse[ProductDetailResponse])
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("product:update"))],
    session: SessionDep,
) -> ApiResponse[ProductDetailResponse]:
    return success(await ProductService(session).update(product_id, payload, current.user_id))


@router.patch("/{product_id}/cost-price", response_model=ApiResponse[ProductDetailResponse])
async def update_product_cost(
    product_id: uuid.UUID,
    payload: ProductCostUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("product:cost:update"))],
    session: SessionDep,
) -> ApiResponse[ProductDetailResponse]:
    return success(await ProductService(session).update_cost(product_id, payload, current.user_id))


@router.post(
    "/{product_id}/commands/disable", response_model=ApiResponse[ProductLifecycleResponse]
)
async def disable_product(
    product_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("product:disable"))],
    session: SessionDep,
) -> ApiResponse[ProductLifecycleResponse]:
    return success(await ProductService(session).disable(product_id, current.user_id))


@router.post(
    "/{product_id}/commands/enable", response_model=ApiResponse[ProductLifecycleResponse]
)
async def enable_product(
    product_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("product:disable"))],
    session: SessionDep,
) -> ApiResponse[ProductLifecycleResponse]:
    return success(await ProductService(session).enable(product_id, current.user_id))


@router.delete("/{product_id}", response_model=ApiResponse[ProductPurgeResponse])
async def purge_product(
    product_id: uuid.UUID,
    payload: ProductPurgeRequest,
    current: Annotated[CurrentUser, Depends(require_permission("product:purge"))],
    session: SessionDep,
) -> ApiResponse[ProductPurgeResponse]:
    del payload
    return success(await ProductService(session).purge(product_id, current.user_id))
