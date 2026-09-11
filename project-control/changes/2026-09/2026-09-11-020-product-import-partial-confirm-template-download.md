# Change Record: Product Import Partial Confirm and Template Download

Change ID: 2026-09-11-020  
Module: product-import, catalog  
Date: 2026-09-11  
Branch: feat/product-import-partial-confirm-template-download

## Goal

Allow users to import validated Product Master rows without silently importing failed rows, and provide the approved fixed template from the product page.

## Database / Alembic

Revision `20260911_0022` adds `imported_rows` to `scm_product_import_task`, plus `is_imported`, `imported_by`, and `imported_at` to `scm_product_import_row`. It adds `PARTIALLY_CONFIRMED` to the task status constraint and backfills previous atomic `CONFIRMED` batches as imported.

## API / UI

- `POST /api/v1/products/imports/{task_id}/confirm` now writes only currently valid, not-yet-imported rows in one transaction and returns remaining counts.
- `GET /api/v1/products/imports/template` requires `product:import` and downloads the approved 32-column template packaged with the backend.
- The Web Admin preview shows imported, passed, and failed counts; users can filter rows and import only passed rows. Failed rows stay in Staging and never enter the Product table.

## Verification

- `python -m alembic upgrade head` — PASS; local development DB at `20260911_0022` single Head.
- `python -m ruff check app tests alembic/versions/20260911_0022_product_import_partial_confirm.py` — PASS.
- `python -m mypy app` — PASS (56 source files).
- `python -m pytest -q` — PASS (128 tests).
- `npm run typecheck` — PASS.
- `npm test` — PASS (42 tests).
- `npm run build` — PASS; Vite emitted the existing chunk-size warning only.

## Boundaries

- The downloaded template is a version-controlled copy of the approved workbook; the original user-provided file is not altered.
- A failed row is not a partial-write fallback. It must be corrected or supplier-resolved before it can become a later valid row.
