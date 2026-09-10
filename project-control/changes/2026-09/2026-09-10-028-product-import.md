# Change Record: Product Import

Change ID: 2026-09-10-028
Module: catalog / product-import
Date: 2026-09-10
Branch: feat/product-import

状态：部分内容已由 `2026-09-10-029` 与 ADR-0010 替代；其中类目预加载/解析和导入时价格公式重算不再适用于固定商品大表。

## Goal

Implement the frozen fixed-template Product Master import workflow: staging only, deterministic source-supplier matching, preview, manual resolution and all-or-nothing Product confirmation.

## Delivered

- Alembic revision `20260910_0010` creates `scm_product_import_task`, `scm_product_import_row` and `scm_product_import_supplier_match`.
- The backend accepts only the approved 32-column `.xlsx` template. It stores formula/source and cached cell values in staging, keeps `supplier_name_raw` only in staging, validates row fields and uses the frozen Decimal Pricing Service for derived-value checks.
- Matching is exact after NFKC/trim/whitespace normalization. Only archived, normal and non-deleted Supplier Master records participate. Ambiguous, unmatched and ineligible groups require an explicit manual `supplier_id` resolution.
- `POST /api/v1/products/imports/preview`, task preview, eligible-supplier candidates, manual resolution and Confirm APIs are protected by `product:import` / `product:import:resolve`.
- Confirm locks the import task, revalidates all references and prices, then creates all Products in one transaction with `source_supplier_id`; it does not create a quote record or a supplier from Excel.
- Web Admin Product List now provides upload, preview, row messages, grouped supplier resolution and permission-controlled Confirm controls.

## Explicitly excluded

- No Category Source Loader or source-category master-data write path.
- No fuzzy/AI supplier binding, silent error-row import, Product manual-create API, Product deletion policy or independent supplier quote domain.

## Verification

- `alembic upgrade head`, `alembic current`, `alembic heads` — `20260910_0010` is the single local Head.
- `python -m ruff check .` — pass.
- `python -m mypy app` — pass.
- `python -m pytest -q` — 109 passed.
- Web Admin `npm run typecheck`, `npm test -- --run`, `npm run build` — pass; 32 tests passed. Build has the existing Vite chunk-size warning only.
- The user-provided fixed template was previewed inside a transaction and rolled back. The file was not changed and no import task/Product was retained. Its 50 rows currently remain invalid because the local Category Master is empty and supplier values contain blanks or do not exactly match an eligible Supplier Master.

## Next Step

Implement and load the frozen Category Source data, then prepare/archive-normal Supplier Master records for the template's source supplier names and repeat preview before Confirm. Do not bypass the preview or use Excel supplier names as Product foreign keys.
