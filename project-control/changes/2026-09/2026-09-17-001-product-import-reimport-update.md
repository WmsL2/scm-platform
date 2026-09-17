# Change Record: Product Import Reimport Update

Change ID: 2026-09-17-001  
Module: product-import, catalog  
Date: 2026-09-17  
Branch: feat/product-import-reimport-update

## Goal

Allow a new approved Product Master workbook to update an existing normal Product with the same source supplier and SKU, while retaining explicit preview, confirmation, audit and lifecycle safeguards.

## Database / Alembic

Revision `20260917_0028` adds `update_rows` to `scm_product_import_task`, and `write_action` (`CREATE` / `UPDATE`) plus `changed_fields` to `scm_product_import_row`.

## API / UI

- Preview marks same-key `ACTIVE` Products as update rows and reports changed template fields; same-key `DISABLED` Products remain invalid.
- Confirm locks references and matching Products, creates new rows or updates the existing Product in one transaction, and returns total writes plus separate created/updated counts.
- The Web Admin preview displays counts for passed/new, update and failed rows; it adds an Update filter and preserves “已导入” / “已更新” results after confirmation.

## Boundaries

- Product ID, creator, creation time, lifecycle status and the `source_supplier_id + sku` key are retained on update.
- No new permission, supplier creation, supplier quote/history, pricing-service recomputation or deletion of prior Product media is introduced.
- An Excel row with a disabled duplicate, unresolved supplier, invalid category or an intra-workbook duplicate remains blocked and never writes Product data.

## Verification

- Backend targeted import API regression: PASS (`4 passed`); full backend suite: PASS (`162 passed`).
- Ruff and mypy: PASS (`87` source files).
- Alembic `upgrade head` / `current`: PASS at `20260917_0028`.
- Frontend typecheck: PASS; Vitest: PASS (`78 passed`); production build: PASS (existing Vite chunk-size warning only).
- `git diff --check`: PASS.
