# Change Record: Product Import Direct Master Values

Change ID: 2026-09-10-029
Module: catalog / product-import
Date: 2026-09-10
Branch: feat/product-import

## Goal

Apply the confirmed business change that the fixed Product Master workbook already contains complete category and price data. Remove Category Source Loader and formula recomputation from the Product Import gate.

## Delivered

- ADR-0010 freezes direct storage of the Excel three-level category and all price/margin values for Product Import.
- Alembic revision `20260910_0014` makes `scm_product.category_id` nullable and adds `category_level1_name`, `category_level2_name` and `category_level3_name`.
- Import no longer queries `scm_category`, resolves a category ID, invokes Pricing Service or compares Excel values against formulas.
- Import writes direct Decimal values from the approved workbook. Formula cells use their saved Excel calculation value when available; an unavailable non-required value becomes a warning and remains null rather than triggering a system recalculation.
- Product detail displays directly stored category text and direct Excel prices. The separate cost-price update control remains available only for a Product that has an existing controlled Category relation.
- Supplier Match Decision, valid Supplier Master constraint, source supplier foreign key and all-or-nothing Confirm remain unchanged.

## Explicitly excluded

- No Category Source Loader is implemented or required for this Product Import flow.
- No fuzzy supplier matching, Supplier creation from Excel, independent quotation table or price recomputation during import.

## Verification

- `alembic upgrade head`, `alembic current`, `alembic heads` — `20260910_0014` is the local single Head.
- The supplied 50-row workbook was re-previewed in a rolled-back transaction after the change: 34 rows are valid; 16 rows remain blocked only by blank or unresolved source suppliers. No Category error remains and no data was retained.
- Full backend/frontend verification is recorded after final code and document synchronization.

## Next Step

Fill or resolve the workbook's missing source suppliers and maintain their existing Supplier Master records as `ARCHIVED + NORMAL`; then preview and Confirm the batch. Category preloading is not required.
