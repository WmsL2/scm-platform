# Change Record: Product Disable and Permanent Delete

Change ID: 2026-09-11-019  
Module: catalog, product-import  
Date: 2026-09-11  
Branch: codex/product-disable-permanent-delete

## Goal

Replace Product logical deletion and Import Confirm restoration with explicit disable/enable and controlled permanent deletion, so a newly imported same-key product cannot silently retain old fields.

## Database / Alembic

Revision `20260911_0020`:

- replaces Product `is_deleted` audit columns with `status` (`ACTIVE` / `DISABLED`) and disabled audit fields, migrating existing deleted Products to `DISABLED`;
- adds `scm_product_purge_audit` for the minimum permanent-delete audit;
- replaces `product:delete` with `product:disable` and `product:purge`, migrating existing delete-role assignments to disable and granting both to the system administrator.

## API / UI

- `POST /api/v1/products/{id}/commands/disable` and `enable` require `product:disable`.
- `DELETE /api/v1/products/{id}` requires `product:purge`, `{"confirm": true}`, and an already disabled Product.
- Product List supports normal/disabled filtering for authorized users, explicit disable/enable, and a SKU/name confirmation before permanent delete.
- Import Preview blocks a same source-supplier + SKU Product in either `ACTIVE` or `DISABLED` state. It no longer restores or overwrites an existing Product.

## Verification

- `python -m alembic upgrade head` — PASS; local development DB at `20260911_0020` single Head.
- `python -m ruff check app tests` — PASS.
- `python -m mypy app` — PASS.
- `python -m pytest -q` — PASS (121 tests).
- `npm run typecheck` — PASS.
- `npm test` — PASS (38 tests).
- `npm run build` — PASS (Vite emitted only the existing chunk-size warning).

## Boundaries

- Permanent delete does not delete unconfirmed-import local media; media cleanup remains a separate lifecycle task.
- A future Excel bulk-overwrite mode is not introduced. To apply changed Excel fields to a retained Product, use explicit Product editing; to create a new same-key Product, permanently delete the disabled Product first.
