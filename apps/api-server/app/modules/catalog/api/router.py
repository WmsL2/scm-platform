import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.contracts import ApiResponse, PageParams, PageResult, success
from app.core.database import get_db_session
from app.modules.auth.dependencies import require_permission
from app.modules.auth.schemas import CurrentUser
from app.modules.catalog.application.service import ProductService
from app.modules.catalog.schemas import (
    ProductCostUpdateRequest,
    ProductDetailResponse,
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
        await ProductService(session).list(
            page_params, keyword=keyword, category_id=category_id
        )
    )


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
