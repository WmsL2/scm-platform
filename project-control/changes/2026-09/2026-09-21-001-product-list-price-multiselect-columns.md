# Change Record: Product List Price, Multi-select and Column Order

Change ID: 2026-09-21-001  
Module: catalog  
Date: 2026-09-21  
Branch: feat/product-list-price-and-multiselect-filters

## Goal

Extend Product List filtering with 京东价 and 利润 ranges; make 所属公司、采销员、品牌、供应商 remotely searchable multi-select filters; and make the custom column picker complete and ordered by the user's selection.

## API / UI

- `GET /api/v1/products` accepts repeated `company_names`, `purchasing_agents`, `brands` and `source_supplier_ids`, plus inclusive `jd_price_min` / `jd_price_max` and `profit_min` / `profit_max` values. Repeated values within the same field are OR; all other filters compose with AND. The original single-text query parameters remain compatible.
- `GET /api/v1/products/filter-options` supplies bounded, remotely searchable candidates for `COMPANY`, `PURCHASING_AGENT`, `BRAND` and `SUPPLIER`, scoped to visible formal Product records for the selected status. Supplier candidates submit the formal UUID and display code/name. Each frontend request is bounded to 50 values; scrolling near the dropdown bottom follows the endpoint's `offset` / `has_more` contract to append the next page.
- 商品图片、SKU、商品名称 are fixed, left-pinned first/second/third columns. The picker exposes all remaining list business fields, including 利润、京东价毛利、扣点复核和毛利率; its optional columns render in user click order and persist under a new browser storage key while safely reading the previous key once.

## Database / Permission

- Added Alembic Revisions `20260921_0036` and `20260921_0037`, creating indexes for `status + jd_price`, `status + profit`, and `status + company_name`.
- No Product business-column, pricing-rule or permission change. `product:list` continues to protect the list and filter-option endpoint; disabled-product options still require `product:disable`.

## Verification

- Frontend Vitest: `98 passed`.
- Frontend typecheck and production build: PASS.
- Backend Ruff and mypy: PASS.
- Alembic heads: `20260921_0037 (head)`.
- Backend Product API integration tests: `14 passed`.
- The migration SQL was rendered and the Alembic head was checked, but `alembic upgrade head` has not been applied to the local development database in this change; authenticated browser acceptance also remains pending.
