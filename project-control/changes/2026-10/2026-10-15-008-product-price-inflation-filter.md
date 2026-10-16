# Change Record: Product Price Inflation Rate Range Filter

Change ID: 2026-10-15-008
Module: catalog
Date: 2026-10-15
Branch: codex/feat/product-price-inflation-filter

## Goal

Allow operators to narrow the Product Master list by a closed percentage range for `price_inflation_rate` (价格虚高比例), using the same interaction and conversion contract as the existing discount-rate filter.

## API / UI

- `GET /api/v1/products` and `GET /api/v1/products/selection-ids` accept `price_inflation_rate_min` and `price_inflation_rate_max`.
- The Product Master advanced filters show “价格虚高比例区间（%）”. Input `30` is sent as `0.3`; blank boundaries remain unbounded.
- List results, total count and cross-page “select all” use the same inclusive range criteria. A minimum greater than its maximum returns the established `PRODUCT_FILTER_RANGE_INVALID` response.

## Database

- Alembic revision `20261015_0057` adds `ix_scm_product_price_inflation_rate` on `scm_product.price_inflation_rate`.
- The migration neither changes data nor redefines how the imported/maintained rate is calculated or stored.

## Boundary

This is a Product Master querying capability only. It introduces no permission, import, matching, recommendation, AI, or price-calculation change.

## Verification

- Backend Product API regression: `25 passed`.
- Backend Ruff and Mypy: passed; Alembic reports `20261015_0057` as the sole head.
- Frontend API and price-inflation-filter Vitest: `15 passed`.
- Frontend typecheck and production build: passed (existing large-chunk warning only).
