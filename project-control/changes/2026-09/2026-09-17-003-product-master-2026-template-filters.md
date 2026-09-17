# Change Record: Product Master 2026 Template and Filters

Change ID: 2026-09-17-003  
Module: catalog, product-import  
Date: 2026-09-17  
Branch: feat/product-master-2026-template-filters

## Goal

Replace the approved Product Master workbook with the 2026 43-column structure, persist its new fields, and provide complete Product query, display and editing capabilities.

## Database / Alembic

Revision `20260917_0030` adds 11 Product business fields, nonnegative/range constraints for sales and positive rating, and indexes for cost price, agreement price, discount rate and sales volume.

## API / UI

- Product import now validates the exact 43-column template, accepts controlled percentage notation, directly stores workbook prices, and uses blank cells to clear previous values.
- Supplier and SKU remain immutable business keys. General Product editing covers all other business fields and active mall category selection; images use controlled upload/clear APIs.
- Product list and edit page use three separate searchable category selects; level 1 constrains level 2 and level 2 constrains level 3. The list also supports comprehensive search, fuzzy company/agent/brand/supplier filters, and inclusive cost/agreement/discount/sales ranges.
- The list has browser-local selectable columns; details show all Product Master fields.

## Media lifecycle

When reimport or manual image maintenance replaces/clears a local Product image, the old file is deleted only after the database transaction succeeds. The confirmed import source workbook continues to be deleted by the existing temporary-media lifecycle.

## Verification

- Approved workbook and backend header tuple: 43 columns, exact order match.
- Backend full pytest: PASS (`165 passed`); Ruff and mypy: PASS.
- Frontend Vitest (82 tests), typecheck and production build: PASS; existing Vite chunk-size warning remains.
- Alembic `heads` / `current`: single Head `20260917_0030`; local upgrade succeeded.
- Local startup: API `/health/live` and `/health/ready` returned 200; Vite development page returned 200.
