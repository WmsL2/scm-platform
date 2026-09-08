import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, PageParams, PageResult, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.supplier.application.import_service import SupplierImportService
from app.modules.supplier.application.service import SupplierService
from app.modules.supplier.domain.rules import ArchiveStatus, CooperationStatus
from app.modules.supplier.schemas import (
    CooperationCommand,
    SupplierCreateRequest,
    SupplierDeleteResponse,
    SupplierDetailResponse,
    SupplierImportConfirmResponse,
    SupplierImportPreviewResponse,
    SupplierListItem,
    SupplierUpdateRequest,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=ApiResponse[PageResult[SupplierListItem]])
async def list_suppliers(
    _: Annotated[CurrentUser, Depends(require_permission("supplier:list"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    keyword: Annotated[str | None, Query(max_length=255)] = None,
    archive_status: ArchiveStatus | None = None,
    cooperation_status: CooperationStatus | None = None,
) -> ApiResponse[PageResult[SupplierListItem]]:
    result = await SupplierService(session).list(
        page_params,
        keyword=keyword,
        archive_status=archive_status,
        cooperation_status=cooperation_status,
    )
    return success(result)


@router.get("/imports/template")
async def download_import_template(
    _: Annotated[CurrentUser, Depends(require_permission("supplier:create"))],
    session: SessionDep,
) -> Response:
    template = SupplierImportService(session).build_template()
    return Response(
        content=template,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="supplier-import-template.xlsx"'},
    )


@router.post("/imports/preview", response_model=ApiResponse[SupplierImportPreviewResponse])
async def preview_import(
    file: Annotated[UploadFile, File(...)],
    current: Annotated[CurrentUser, Depends(require_permission("supplier:create"))],
    session: SessionDep,
) -> ApiResponse[SupplierImportPreviewResponse]:
    return success(
        await SupplierImportService(session).preview(
            file.filename or "supplier-import.xlsx", await file.read(), current.user_id
        )
    )


@router.post(
    "/imports/{batch_id}/confirm", response_model=ApiResponse[SupplierImportConfirmResponse]
)
async def confirm_import(
    batch_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("supplier:create"))],
    session: SessionDep,
) -> ApiResponse[SupplierImportConfirmResponse]:
    return success(await SupplierImportService(session).confirm(batch_id, current.user_id))


@router.get("/{supplier_id}", response_model=ApiResponse[SupplierDetailResponse])
async def get_supplier(
    supplier_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("supplier:detail"))],
    session: SessionDep,
) -> ApiResponse[SupplierDetailResponse]:
    return success(await SupplierService(session).get(supplier_id))


@router.post("", response_model=ApiResponse[SupplierDetailResponse], status_code=201)
async def create_supplier(
    payload: SupplierCreateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("supplier:create"))],
    session: SessionDep,
) -> ApiResponse[SupplierDetailResponse]:
    return success(await SupplierService(session).create(payload, current.user_id))


@router.patch("/{supplier_id}", response_model=ApiResponse[SupplierDetailResponse])
async def update_supplier(
    supplier_id: uuid.UUID,
    payload: SupplierUpdateRequest,
    current: Annotated[CurrentUser, Depends(require_permission("supplier:update"))],
    session: SessionDep,
) -> ApiResponse[SupplierDetailResponse]:
    return success(await SupplierService(session).update(supplier_id, payload, current.user_id))


@router.delete("/{supplier_id}", response_model=ApiResponse[SupplierDeleteResponse])
async def delete_supplier(
    supplier_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("supplier:delete"))],
    session: SessionDep,
) -> ApiResponse[SupplierDeleteResponse]:
    return success(await SupplierService(session).delete(supplier_id, current.user_id))


@router.post("/{supplier_id}/commands/submit", response_model=ApiResponse[SupplierDetailResponse])
async def submit_supplier(
    supplier_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("supplier:submit"))],
    session: SessionDep,
) -> ApiResponse[SupplierDetailResponse]:
    return success(await SupplierService(session).submit(supplier_id, current.user_id))


@router.post("/{supplier_id}/commands/archive", response_model=ApiResponse[SupplierDetailResponse])
async def archive_supplier(
    supplier_id: uuid.UUID,
    current: Annotated[CurrentUser, Depends(require_permission("supplier:archive"))],
    session: SessionDep,
) -> ApiResponse[SupplierDetailResponse]:
    return success(await SupplierService(session).archive(supplier_id, current.user_id))


@router.post("/{supplier_id}/commands/stop", response_model=ApiResponse[SupplierDetailResponse])
async def stop_supplier(
    supplier_id: uuid.UUID,
    payload: CooperationCommand,
    current: Annotated[CurrentUser, Depends(require_permission("supplier:stop"))],
    session: SessionDep,
) -> ApiResponse[SupplierDetailResponse]:
    return success(
        await SupplierService(session).stop(supplier_id, payload.reason, current.user_id)
    )


@router.post(
    "/{supplier_id}/commands/blacklist", response_model=ApiResponse[SupplierDetailResponse]
)
async def blacklist_supplier(
    supplier_id: uuid.UUID,
    payload: CooperationCommand,
    current: Annotated[CurrentUser, Depends(require_permission("supplier:blacklist"))],
    session: SessionDep,
) -> ApiResponse[SupplierDetailResponse]:
    return success(
        await SupplierService(session).blacklist(supplier_id, payload.reason, current.user_id)
    )
