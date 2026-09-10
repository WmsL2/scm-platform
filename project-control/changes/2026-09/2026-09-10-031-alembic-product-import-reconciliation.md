# Change Record: Product Import Alembic Reconciliation

Change ID: 2026-09-10-031
Module: database / account / catalog
Date: 2026-09-10
Branch: feat/product-import

## Goal

Resolve the collision created when the merged Account logical-delete migration and the unmerged Product Import migration both used Alembic revision `20260910_0010`.

## Delivered

- Retained merged `20260910_0010_account_user_delete.py` unchanged.
- Renumbered the not-yet-merged Product Import chain to `20260910_0013` → `20260910_0014` → `20260910_0015`, each based on its actual predecessor.
- Documented a checked local reconciliation path for databases that had already applied the legacy Product Import revision `20260910_0012`: verify its known Product Import schema, apply the missing Account logical-delete schema/permission, then record the equivalent canonical `20260910_0015` revision.

## Data Safety

- The reconciliation does not delete or rewrite Product, Product Import Task, or Product Import Row business data.
- It only adds nullable `sys_user.deleted_by` / `deleted_at`, adds the existing `system:user:delete` permission when absent, grants it to the built-in system administrator when applicable, and updates Alembic's version marker after all structural checks pass.
- New databases use only `alembic upgrade head`; the reconciliation path is exclusively for the already-applied legacy local state.

## Verification

- Before reconciliation, the local database was at legacy `20260910_0012`, had the Product Import tables/columns and 12 tasks / 600 staging rows / 100 Products, but lacked `sys_user.deleted_by` and `deleted_at`.
- Reconciliation completed at `20260910_0015` with the same 12 tasks / 600 staging rows / 100 Products.
- `alembic upgrade head`, `alembic current`, and `alembic heads` report the single Head `20260910_0015`.
- `pytest -q` — 112 passed; `ruff check .` and `mypy app` — pass.
- `GET /health/ready` returns HTTP 200 with MySQL ready; a deliberately invalid login now reaches the authentication rule and returns HTTP 401 rather than a missing-column HTTP 500.
