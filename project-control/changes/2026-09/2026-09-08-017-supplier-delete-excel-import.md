# Change Record: Supplier Delete & Excel Import

Change ID: 2026-09-08-017
Module: supplier
Date: 2026-09-08
Branch: fix/supplier-delete-import

## Goal

Implement the Supplier patch only: permission-protected logical deletion and a standard Excel template/download, upload validation, error preview and explicit confirmation import workflow. Phone-format validation, Account/Registration/Profile, Product and qualification business fields are excluded.

## Code

Created:

- `apps/api-server/alembic/versions/20260908_0005_supplier_delete_import.py`
- `apps/api-server/app/modules/supplier/application/import_service.py`

Modified:

- Supplier Router, Service, Repository, ORM models and Pydantic schemas
- Web Admin Supplier API/types/list page and shared HTTP client for multipart upload/binary download
- Supplier API and schema tests
- `apps/api-server/pyproject.toml` to declare `openpyxl` and `python-multipart`; `types-openpyxl` is a dev type-check dependency

## Database / Alembic

Revision: `20260908_0005`, down revision `20260907_0004`.

Adds `deleted_by` / `deleted_at` to `scm_supplier`; creates `scm_supplier_import_batch` and `scm_supplier_import_row`; and seeds `supplier:delete`. Import staging persists only the frozen five supplier data fields plus validation/audit metadata. It does not persist source legacy codes or source status text.

## API / UI / Permission

- `DELETE /api/v1/suppliers/{id}` requires `supplier:delete` and performs logical deletion.
- Template download, Excel preview and confirmation routes require `supplier:create`.
- The list page hides delete controls without `supplier:delete`; it supports template download, `.xlsx` upload, row-error preview and confirmation only when every row is valid.

## Verification

- `python -m ruff check .` — PASS
- `python -m mypy app` — PASS
- `python -m pytest tests/supplier tests/integration/test_supplier_schema.py -q` — PASS (5 tests)
- `python -m pytest -q` — PASS (47 tests)
- `npm run typecheck` — PASS
- `npm run test` — PASS (18 tests)
- `npm run build` — PASS (existing Vite chunk-size warning only)
- `python -m alembic upgrade head` / `current` — PASS, local database at `20260908_0005`

## Remaining Work

- Merge this branch through a PR before treating it as `main` functionality.
- The Account branch must provide administrator user/role/permission assignment UI; the new `supplier:delete` permission is only seeded, not automatically assigned.
- Phone-format validation, registration, profile/password changes and qualification business fields remain outside this branch.
