# Change Record: Product Import Confirm-Time Media Storage

Change ID: 2026-09-14-021
Module: product-import / catalog
Date: 2026-09-14
Branch: feat/product-import-confirm-media

## Goal

Stop duplicate local product-image files when users only upload or preview an Excel workbook, while preserving later supplier resolution and safe partial confirmation.

## Delivered

- Revision `20260914_0023` adds `scm_product_import_task.source_file_storage_key` and `EXPIRED` status.
- Preview detects formula images and stores only a temporary source `.xlsx`; it no longer extracts per-row product images. The Web Admin now shows “确认后保存”.
- Confirm reads that source file and saves images only for the rows actually written to `scm_product`; a fully confirmed task removes its source file.
- Each later preview expires tasks older than configurable `PRODUCT_IMPORT_UNCONFIRMED_RETENTION_DAYS` (default 7). Cleanup uses exact storage keys, removes only source files and unimported-row media, and never removes Product-referenced images.

## Verification

- `alembic upgrade head`, `alembic current`, `alembic heads` — PASS; single Head `20260914_0023`.
- `python -m ruff check app tests alembic/versions/20260914_0023_product_import_confirm_media.py` — PASS.
- `python -m mypy app` — PASS (56 source files).
- `python -m pytest -q` — PASS (130 tests), including image extraction, confirmation-time staging and product-import regression coverage.
- Web Admin `npm run typecheck`, `npm test -- --run`, `npm run build` — PASS; 42 tests passed. Build has the existing Vite chunk-size warning only.

## Boundaries

- Existing current Product media is not bulk-deleted or migrated by this change.
- The cleanup is invoked by a new import preview; it is not an independent scheduler or a broad filesystem delete.
