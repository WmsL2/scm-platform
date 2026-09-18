# Change Record: Product Master Category Filter Source

Change ID: 2026-09-18-005  
Module: catalog  
Date: 2026-09-18  
Branch: feat/product-master-category-filter-options

## Goal

Make Product List category filter options come directly from formal Product Master data while retaining
search, multi-select, parent display, cascading options and existing filter composition.

## Database / Alembic

- Added Revision `20260918_0031`.
- Added `ix_scm_product_status_category_path` on status plus the three category path columns, using
  128-character MySQL index prefixes for utf8mb4 text columns.
- No Product business data, permission or Category schema changed.

## API / UI

- Added `GET /api/v1/products/category-filter-options`, protected by `product:list`; requesting
  disabled Product options also requires `product:disable`.
- The endpoint returns distinct category paths from formal Product Master records, scoped to current
  Product status and visibility rules, with remote keyword search, 50-item pagination and parent narrowing.
- Product List now uses this endpoint instead of the Category Master option endpoint. It keeps direct
  input, multi-select, child-to-parent display, full path labels and OR semantics among direct category
  selections. Other Product filters remain AND conditions.

## Verification

- Backend Product API tests: `7 passed`.
- Ruff and mypy on changed backend files: PASS.
- Alembic upgrade/current: `20260918_0031 (head)`.
- Web Admin typecheck: PASS; targeted Vitest: `9 passed`; production build: PASS.
