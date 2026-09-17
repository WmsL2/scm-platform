# ruff: noqa: E501
import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, PageParams, PageResult, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.catalog.application.category_service import CategoryService
from app.modules.catalog.schemas import (
    CategoryImportResponse,
    CategoryResponse,
    CategoryWriteRequest,
)

router = APIRouter(prefix="/categories", tags=["categories"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=ApiResponse[PageResult[CategoryResponse]])
async def list_categories(
    _: Annotated[CurrentUser, Depends(require_permission("category:list"))],
    session: SessionDep,
    page_params: Annotated[PageParams, Depends()],
    active_only: bool = False,
    level1_name: str | None = None,
    level2_name: str | None = None,
    level3_name: str | None = None,
    deduction_rate: Decimal | None = None,
    is_active: bool | None = None,
    business_unit: str | None = None,
) -> ApiResponse[PageResult[CategoryResponse]]:
    result = await CategoryService(session).list_page(
        page_params,
        active_only=active_only,
        level1_name=level1_name,
        level2_name=level2_name,
        level3_name=level3_name,
        deduction_rate=deduction_rate,
        is_active=is_active,
        business_unit=business_unit,
    )
    return success(PageResult(items=[CategoryResponse.model_validate(item) for item in result.items], total=result.total, page=result.page, page_size=result.page_size))


@router.get("/selection", response_model=ApiResponse[list[CategoryResponse]])
async def category_selection(
    _: Annotated[CurrentUser, Depends(require_permission("product:list"))], session: SessionDep
) -> ApiResponse[list[CategoryResponse]]:
    categories = await CategoryService(session).list_active_selection()
    return success([CategoryResponse.model_validate(item) for item in categories])


@router.get("/imports/template")
async def download_template(
    _: Annotated[CurrentUser, Depends(require_permission("product:import"))], session: SessionDep
) -> Response:
    return Response(
        content=CategoryService(session).template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="category-import-template.xlsx"'},
    )


@router.post("/imports", response_model=ApiResponse[CategoryImportResponse])
async def import_categories(
    file: Annotated[UploadFile, File(...)],
    deduction_rate_percent: Annotated[str, Form(...)],
    current: Annotated[CurrentUser, Depends(require_permission("product:import"))],
    session: SessionDep,
) -> ApiResponse[CategoryImportResponse]:
    return success(
        await CategoryService(session).import_xlsx(
            file.filename or "category-import.xlsx", await file.read(), deduction_rate_percent, current.user_id
        )
    )


@router.get("/{category_id}", response_model=ApiResponse[CategoryResponse])
async def get_category(
    category_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("category:detail"))],
    session: SessionDep,
) -> ApiResponse[CategoryResponse]:
    return success(CategoryResponse.model_validate(await CategoryService(session).get(category_id)))


@router.post("", response_model=ApiResponse[CategoryResponse])
async def create_category(
    payload: CategoryWriteRequest,
    current: Annotated[CurrentUser, Depends(require_permission("category:create"))],
    session: SessionDep,
) -> ApiResponse[CategoryResponse]:
    return success(CategoryResponse.model_validate(await CategoryService(session).create(payload, current.user_id)))


@router.put("/{category_id}", response_model=ApiResponse[CategoryResponse])
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryWriteRequest,
    current: Annotated[CurrentUser, Depends(require_permission("category:update"))],
    session: SessionDep,
) -> ApiResponse[CategoryResponse]:
    return success(CategoryResponse.model_validate(await CategoryService(session).update(category_id, payload, current.user_id)))


@router.delete("/{category_id}", response_model=ApiResponse[None])
async def delete_category(
    category_id: uuid.UUID,
    _: Annotated[CurrentUser, Depends(require_permission("category:delete"))],
    session: SessionDep,
) -> ApiResponse[None]:
    await CategoryService(session).delete(category_id)
    return success(None)
