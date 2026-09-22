# ruff: noqa: E501
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask

from app.common.contracts import ApiResponse, AppError, PageParams, PageResult, success
from app.core.config import get_settings
from app.core.database import FunctionSessionDep, get_db_session
from app.modules.auth.dependencies import require_permission, require_permission_before_response
from app.modules.auth.schemas import CurrentUser
from app.modules.catalog.application.export_service import ProductExportService
from app.modules.catalog.application.import_service import ProductImportService
from app.modules.catalog.application.service import ProductService
from app.modules.catalog.domain.lifecycle import ProductStatus
from app.modules.catalog.schemas import (
    ProductCategoryFilterOptionPageResponse,
    ProductCostUpdateRequest,
    ProductDetailResponse,
    ProductExportRequest,
    ProductFilterOptionPageResponse,
    ProductImportConfirmResponse,
    ProductImportDiscardResponse,
    ProductImportPreviewResponse,
    ProductImportResolveSupplierRequest,
    ProductImportSupplierCandidateResponse,
    ProductLifecycleResponse,
    ProductListItem,
    ProductPurgeRequest,
    ProductPurgeResponse,
    ProductSelectionIdsResponse,
    ProductSourceSupplierCandidateResponse,
    ProductUpdateRequest,
)

router = APIRouter(prefix="/products", tags=["products"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
PRODUCT_IMPORT_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1] / "resources" / "product-master-template.xlsx"
)
PRODUCT_IMPORT_UPLOAD_CHUNK_BYTES = 1024 * 1024


async def _stage_product_import_upload(file: UploadFile) -> tuple[Path, int]:
    """Copy an incoming workbook to disk without retaining it in application memory."""
    max_bytes = get_settings().product_import_max_file_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise AppError(
            "PRODUCT_IMPORT_FILE_TOO_LARGE",
            f"The import file exceeds {get_settings().product_import_max_file_mb} MB",
            422,
        )
    temporary = NamedTemporaryFile(prefix="scm-product-import-", suffix=".xlsx", delete=False)
    path = Path(temporary.name)
    file_size = 0
    try:
        with temporary:
            while chunk := await file.read(PRODUCT_IMPORT_UPLOAD_CHUNK_BYTES):
                file_size += len(chunk)
                if file_size > max_bytes:
                    raise AppError(
                        "PRODUCT_IMPORT_FILE_TOO_LARGE",
                        f"The import file exceeds {get_settings().product_import_max_file_mb} MB",
                        422,
                    )
                temporary.write(chunk)
        return path, file_size
    except Exception:
        path.unlink(missing_ok=True)
        raise


@router.get("", response_model=ApiResponse[PageResult[ProductListItem]])
async def list_products(
    current: Annotated[CurrentUser, Depends(require_permission("product:list"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    company_name: Annotated[str | None, Query(max_length=255)] = None,
    purchasing_agent: Annotated[str | None, Query(max_length=128)] = None,
    brand: Annotated[str | None, Query(max_length=128)] = None,
    supplier_name: Annotated[str | None, Query(max_length=255)] = None,
    company_names: Annotated[list[str] | None, Query(max_length=255)] = None,
    purchasing_agents: Annotated[list[str] | None, Query(max_length=128)] = None,
    brands: Annotated[list[str] | None, Query(max_length=128)] = None,
    source_supplier_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    category_level1_name: Annotated[str | None, Query(max_length=255)] = None,
    category_level2_name: Annotated[str | None, Query(max_length=255)] = None,
    category_selections: Annotated[list[str] | None, Query()] = None,
    source_supplier_id: uuid.UUID | None = None,
    cost_price_min: Annotated[Decimal | None, Query(ge=0)] = None,
    cost_price_max: Annotated[Decimal | None, Query(ge=0)] = None,
    agreement_price_min: Annotated[Decimal | None, Query(ge=0)] = None,
    agreement_price_max: Annotated[Decimal | None, Query(ge=0)] = None,
    jd_price_min: Decimal | None = None,
    jd_price_max: Decimal | None = None,
    profit_min: Decimal | None = None,
    profit_max: Decimal | None = None,
    discount_rate_min: Decimal | None = None,
    discount_rate_max: Decimal | None = None,
    sales_volume_min: Annotated[int | None, Query(ge=0)] = None,
    sales_volume_max: Annotated[int | None, Query(ge=0)] = None,
    status: ProductStatus = ProductStatus.ACTIVE,
) -> ApiResponse[PageResult[ProductListItem]]:
    if status == ProductStatus.DISABLED and "product:disable" not in current.permissions:
        raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)
    return success(
        await ProductService(session).list(
            page_params,
            keyword=keyword,
            company_name=company_name,
            purchasing_agent=purchasing_agent,
            brand=brand,
            supplier_name=supplier_name,
            company_names=company_names or [],
            purchasing_agents=purchasing_agents or [],
            brands=brands or [],
            source_supplier_ids=source_supplier_ids or [],
            category_level1_name=category_level1_name,
            category_level2_name=category_level2_name,
            category_selections=category_selections or [],
            source_supplier_id=source_supplier_id,
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
    )


@router.get("/selection-ids", response_model=ApiResponse[ProductSelectionIdsResponse])
async def product_selection_ids(
    current: Annotated[CurrentUser, Depends(require_permission("product:list"))],
    session: SessionDep,
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    company_name: Annotated[str | None, Query(max_length=255)] = None,
    purchasing_agent: Annotated[str | None, Query(max_length=128)] = None,
    brand: Annotated[str | None, Query(max_length=128)] = None,
    supplier_name: Annotated[str | None, Query(max_length=255)] = None,
    company_names: Annotated[list[str] | None, Query(max_length=255)] = None,
    purchasing_agents: Annotated[list[str] | None, Query(max_length=128)] = None,
    brands: Annotated[list[str] | None, Query(max_length=128)] = None,
    source_supplier_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    category_level1_name: Annotated[str | None, Query(max_length=255)] = None,
    category_level2_name: Annotated[str | None, Query(max_length=255)] = None,
    category_selections: Annotated[list[str] | None, Query()] = None,
    source_supplier_id: uuid.UUID | None = None,
    cost_price_min: Annotated[Decimal | None, Query(ge=0)] = None,
    cost_price_max: Annotated[Decimal | None, Query(ge=0)] = None,
    agreement_price_min: Annotated[Decimal | None, Query(ge=0)] = None,
    agreement_price_max: Annotated[Decimal | None, Query(ge=0)] = None,
    jd_price_min: Decimal | None = None,
    jd_price_max: Decimal | None = None,
    profit_min: Decimal | None = None,
    profit_max: Decimal | None = None,
    discount_rate_min: Decimal | None = None,
    discount_rate_max: Decimal | None = None,
    sales_volume_min: Annotated[int | None, Query(ge=0)] = None,
    sales_volume_max: Annotated[int | None, Query(ge=0)] = None,
    status: ProductStatus = ProductStatus.ACTIVE,
) -> ApiResponse[ProductSelectionIdsResponse]:
    if status == ProductStatus.DISABLED and "product:disable" not in current.permissions:
        raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)
    ids = await ProductService(session).selection_ids(
        keyword=keyword,
        company_name=company_name,
        purchasing_agent=purchasing_agent,
        brand=brand,
        supplier_name=supplier_name,
        company_names=company_names or [],
        purchasing_agents=purchasing_agents or [],
        brands=brands or [],
        source_supplier_ids=source_supplier_ids or [],
        category_level1_name=category_level1_name,
        category_level2_name=category_level2_name,
        category_selections=category_selections or [],
        source_supplier_id=source_supplier_id,
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
    return success(ProductSelectionIdsResponse(ids=ids, total=len(ids)))


@router.get(
    "/filter-options",
    response_model=ApiResponse[ProductFilterOptionPageResponse],
)
async def product_filter_options(
    current: Annotated[CurrentUser, Depends(require_permission("product:list"))],
    session: SessionDep,
    field: Literal["COMPANY", "PURCHASING_AGENT", "BRAND", "SUPPLIER"],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    status: ProductStatus = ProductStatus.ACTIVE,
) -> ApiResponse[ProductFilterOptionPageResponse]:
    if status == ProductStatus.DISABLED and "product:disable" not in current.permissions:
        raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)
    return success(
        await ProductService(session).filter_options(
            field=field,
            keyword=keyword,
            offset=offset,
            limit=limit,
            status=status,
        )
    )


@router.get(
    "/category-filter-options",
    response_model=ApiResponse[ProductCategoryFilterOptionPageResponse],
)
async def product_category_filter_options(
    current: Annotated[CurrentUser, Depends(require_permission("product:list"))],
    session: SessionDep,
    level: Literal["LEVEL1", "LEVEL2", "LEVEL3"],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    category_selections: Annotated[list[str] | None, Query()] = None,
    status: ProductStatus = ProductStatus.ACTIVE,
) -> ApiResponse[ProductCategoryFilterOptionPageResponse]:
    if status == ProductStatus.DISABLED and "product:disable" not in current.permissions:
        raise AppError("AUTH_FORBIDDEN", "Permission denied", 403)
    return success(
        await ProductService(session).category_filter_options(
            level=level,
            keyword=keyword,
            offset=offset,
            limit=limit,
            category_selections=category_selections or [],
            status=status,
        )
    )

@router.post("/export")
async def export_products(payload: ProductExportRequest, current: Annotated[CurrentUser, Depends(require_permission("product:list"))], session: SessionDep) -> Response:
    content = await ProductExportService(session).export(payload.product_ids, payload.columns, "product:disable" in current.permissions)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="product-export-{datetime.now():%Y%m%d_%H%M%S}.xlsx"'})


@router.post("/imports/preview", response_model=ApiResponse[ProductImportPreviewResponse])
async def preview_product_import(
    file: Annotated[UploadFile, File(...)],
    current: Annotated[CurrentUser, Depends(require_permission("product:import"))],
    session: SessionDep,
) -> ApiResponse[ProductImportPreviewResponse]:
    upload_path: Path | None = None
    try:
        upload_path, file_size = await _stage_product_import_upload(file)
        return success(
            await ProductImportService(session).preview(
                file.filename or "product-import.xlsx",
                upload_path,
                file_size,
                current.user_id,
            )
        )
    finally:
        if upload_path is not None:
            upload_path.unlink(missing_ok=True)
        await file.close()


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
    current: Annotated[CurrentUser, Depends(require_permission("product:import"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    row_status: Literal["ALL", "PASSED", "UPDATE", "FAILED"] = Query("ALL"),
) -> ApiResponse[ProductImportPreviewResponse]:
    return success(
        await ProductImportService(session).get_preview(
            task_id,
            current.user_id,
            page_params,
            row_status=row_status,
        )
    )


@router.get("/imports/{task_id}/failed-rows", response_class=FileResponse)
async def export_product_import_failed_rows(
    task_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("product:import"))],
    session: SessionDep,
) -> FileResponse:
    path, filename = await ProductImportService(session).export_failed_rows(
        task_id,
        current.user_id,
    )
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
        background=BackgroundTask(path.unlink, missing_ok=True),
    )


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
    current: Annotated[CurrentUser, Depends(require_permission_before_response("product:import"))],
    session: FunctionSessionDep,
) -> ApiResponse[ProductImportConfirmResponse]:
    return success(await ProductImportService(session).confirm(task_id, current.user_id))


@router.post("/imports/{task_id}/discard", response_model=ApiResponse[ProductImportDiscardResponse])
async def discard_product_import(
    task_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("product:import"))],
    session: SessionDep,
) -> ApiResponse[ProductImportDiscardResponse]:
    return success(await ProductImportService(session).discard(task_id, current.user_id))


@router.get(
    "/source-supplier-candidates",
    response_model=ApiResponse[list[ProductSourceSupplierCandidateResponse]],
)
async def source_supplier_candidates(
    _: Annotated[CurrentUser, Depends(require_permission("product:update"))],
    session: SessionDep,
) -> ApiResponse[list[ProductSourceSupplierCandidateResponse]]:
    return success(await ProductService(session).source_supplier_candidates())


@router.post("/{product_id}/image", response_model=ApiResponse[ProductDetailResponse])
async def update_product_image(
    product_id: uuid.UUID,
    file: Annotated[UploadFile, File(...)],
    current: Annotated[CurrentUser, Depends(require_permission("product:update"))],
    session: SessionDep,
) -> ApiResponse[ProductDetailResponse]:
    return success(
        await ProductService(session).update_image(
            product_id,
            file.filename or "product-image",
            file.content_type,
            await file.read(),
            current.user_id,
        )
    )


@router.delete("/{product_id}/image", response_model=ApiResponse[ProductDetailResponse])
async def clear_product_image(
    product_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("product:update"))],
    session: SessionDep,
) -> ApiResponse[ProductDetailResponse]:
    return success(await ProductService(session).clear_image(product_id, current.user_id))


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


@router.post("/{product_id}/commands/disable", response_model=ApiResponse[ProductLifecycleResponse])
async def disable_product(
    product_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("product:disable"))],
    session: SessionDep,
) -> ApiResponse[ProductLifecycleResponse]:
    return success(await ProductService(session).disable(product_id, current.user_id))


@router.post("/{product_id}/commands/enable", response_model=ApiResponse[ProductLifecycleResponse])
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
