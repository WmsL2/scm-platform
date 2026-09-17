# Change Record: Merge Category and Product Import Migration Heads

Change ID: 2026-09-17-002  
Module: catalog, product-import  
Date: 2026-09-17  
Branch: feat/product-import-reimport-update

## Goal

Resolve the Alembic multiple-head condition introduced when the category permission Migration `20260916_0028` and the Product Import reimport-update Migration `20260917_0028` were merged from parallel branches.

## Database / Alembic

Revision `20260917_0029` is an empty Alembic merge revision with both prior revisions as `down_revision`. It changes no table, row, permission definition or business rule; it establishes one authoritative Alembic head so `alembic upgrade head` can apply both branches deterministically.

## Verification

- `alembic heads` / `alembic upgrade head` / `alembic current`: PASS; one Head `20260917_0029`.
- `python -m ruff check app tests alembic/versions/20260917_0029_merge_category_and_product_import_heads.py`: PASS.
- `python -m mypy app`: PASS (`87` source files).
- `python -m pytest -q`: PASS (`164 passed`).
- Web Admin `npm run typecheck`, `npm test -- --run`, `npm run build`: PASS (`81 passed`); build has the existing Vite chunk-size warning only.
