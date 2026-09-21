# Handoff: Product List Price, Multi-select and Column Order

Status: IMPLEMENTED / BROWSER ACCEPTANCE PENDING
Date: 2026-09-21
Branch: feat/product-list-price-and-multiselect-filters

## Completed

- Added Product List inclusive 京东价 and 利润 ranges, plus repeated multi-select query values for 所属公司、采销员、品牌 and formal来源供应商 ID.
- Added `GET /api/v1/products/filter-options` for bounded remote candidates from visible formal Product data; active results remain restricted to normal, non-deleted suppliers. The four multi-select controls load 50 values per request and append the next `offset` page when their dropdown nears the bottom.
- Added Revisions `20260921_0036` / `20260921_0037` with `status + jd_price`, `status + profit` and `status + company_name` indexes.
- Made 商品图片、SKU、商品名称 fixed left-pinned first/second/third business columns. All remaining supported Product List business columns, including 利润 and three margin fields, are configurable and render in click order.
- Updated Product field dictionary, Catalog module status, Current Status and Change Record.

## Verified

- Web Admin Vitest: `98 passed`; typecheck and production build passed.
- Backend Ruff and mypy passed after the company follow-up; Alembic has one head: `20260921_0037`.
- Backend Product API integration tests: `14 passed`.

## Pending

- `alembic upgrade head` has not been applied to the local development database for this change; migration SQL rendering and head verification passed.
- Authenticated browser acceptance remains pending, including an authorized `product:list` account and a product-data volume sufficient to exercise dropdown continuation.

## Resume

1. Apply `alembic upgrade head` to the intended checkout-local development database; do not use another checkout or production database.
2. With an authorized `product:list` account, verify selecting 京东价／利润 ranges, multiple 所属公司／采销员／品牌／供应商 values, and that the first clicked optional column follows the three fixed columns.
3. Use enough Product data to scroll a filter dropdown beyond 50 candidates and verify `offset` continuation through the final `has_more=false` page.
