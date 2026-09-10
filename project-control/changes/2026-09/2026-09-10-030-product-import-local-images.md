# Change Record: Product Import Local Images

Change ID: 2026-09-10-030
Module: catalog / product-import
Date: 2026-09-10
Branch: feat/product-import

## Goal

Persist embedded product images from the fixed Excel template in a project-relative local directory without committing media files to Git.

## Delivered

- `20260910_0015` adds `scm_product_import_row.image_storage_key`.
- WPS/Excel `DISPIMG` identifiers are resolved through `xl/cellimages.xml` and its relationship file, then the mapped `xl/media` image bytes are saved through `ObjectStorage`.
- Local storage preserves a safe relative key under `product-images/<import-task-id>/`; Product stores a `local-media/...` relative reference and the API exposes it from `/local-media/`.
- Product import preview indicates saved images; Product detail displays and previews saved images.
- `LOCAL_STORAGE_PATH` now resolves relative paths from the project root. `.gitignore` explicitly documents local media isolation.

## Verification

- The supplied workbook was inspected read-only: 49 `DISPIMG` identifiers, 49 extracted embedded images, 49 identifier-to-image matches.
- `alembic upgrade head`, `alembic current`, `alembic heads` — `20260910_0015` is the local single Head.
- `python -m ruff check .` — pass.
- `python -m mypy app` — pass.
- `python -m pytest -q` — 111 passed, including WPS `DISPIMG` extraction and nested safe LocalFileStorage tests.
- Web Admin `npm run typecheck`, `npm test -- --run`, `npm run build` — pass; 32 tests passed. Build has the existing Vite chunk-size warning only.
- `local-data/files/product-images/example.png` is confirmed ignored by Git.

## Next Step

Re-upload the fixed workbook to create a new preview with staged images, resolve its Supplier Master issues, then Confirm. Existing preview tasks intentionally remain unchanged and are not retroactively rewritten.
