# Change Record: Product Import Empty Supplier Async Load Fix

Date: 2026-09-21  
Branch: `fix/product-import-empty-supplier-missing-greenlet`  
Alembic Revision: None

## Problem

When every imported row had an empty supplier value, no supplier match objects were appended to the new import task. After `flush`, reading the uninitialized `supplier_matches` relationship attempted implicit database I/O and raised SQLAlchemy `MissingGreenlet` instead of returning a normal failed-row preview.

## Change

- Build supplier match objects as a plain local list before constructing the import task.
- Pass the list, including an empty list, into `ProductImportTask` so the relationship is always initialized before persistence.
- Use the local list to map normalized supplier names after `flush`, avoiding ORM relationship reads that could issue implicit async I/O.
- Add an API regression test for a workbook whose every supplier cell is empty.

## Expected Result

The preview endpoint returns `200` with an empty `supplier_matches` collection and marks every affected row as invalid with `供应商不能为空`. Supplier remains a required field and no invalid row is written to formal Product Master data.

## Verification

- Pure ORM-state regression: passed; the empty match list is loaded as `[]`, not `NO_VALUE`.
- Ruff and mypy: passed for the modified backend files.
- MySQL API integration test: added, but the local run is currently blocked before the changed code path because the development MySQL service crashes while reading `scm_product_import_row.ibd` with InnoDB OS errors 483/583. Re-run after repairing or moving the local MySQL data directory.

## API / UI / Permission

- API: no route or schema change; corrected `POST /api/v1/products/imports/preview` behavior for all-empty supplier workbooks.
- UI: no change.
- Permission: no change; continues to use `product:import`.
