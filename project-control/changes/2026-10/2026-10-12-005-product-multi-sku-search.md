# Change Record: Product Multi-SKU Exact Search

Change ID: 2026-10-12-005
Module: catalog
Date: 2026-10-12
Branch: codex/feat/product-multi-sku-search

## Goal

Allow an operator to find several Product Master records in one request by pasting multiple SKU values.

## API / UI

- `GET /api/v1/products` and `GET /api/v1/products/selection-ids` accept repeated `skus` query parameters.
- The UI accepts whitespace, Chinese or English commas, semicolons, and line breaks, trims and de-duplicates values, then sends one `skus` parameter per value.
- SKU matching ignores leading and trailing whitespace retained by historical imports, then applies exact OR-based matching. All remaining list filters, including status, featured marker, category, supplier and price ranges, remain AND conditions.
- The service rejects more than 500 distinct SKU values with a clear 422 error. Existing `keyword` search remains unchanged.

## Boundary

This is only a Product Master list and selection filter. It changes no Product fields, import behavior, permissions, matching, recommendation or AI inputs.

## Database

No Migration. The existing `source_supplier_id + sku` unique index remains unchanged.

## Verification

- Backend Product API tests: `25 passed`.
- Backend Ruff and Mypy: passed.
- Frontend API and SKU-parser Vitest: `16 passed`.
- Frontend typecheck and production build: passed (existing large-chunk warning only).
- Local backend OpenAPI exposes `skus` on both list and selection-ID endpoints; authenticated browser acceptance remains pending.
