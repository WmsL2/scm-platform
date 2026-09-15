# Change Record: Product Import DISPIMG Preview Async Fix

Change ID: 2026-09-15-024
Module: catalog / product-import
Date: 2026-09-15
Branch: feat/product-import-category-binding

## Problem

An Excel workbook containing WPS/Excel `DISPIMG` formulas saved its temporary source file during preview. Subsequent access to a not-yet-loaded relationship caused SQLAlchemy async `MissingGreenlet`, returning HTTP 500 instead of an import preview.

## Delivered

- Reload the new import task with its staging rows and supplier matches before assigning the temporary source-file key.
- Keep the existing staged source-file behavior: preview does not extract or create Product image files; only Confirm does so for passing rows.

## Verification

- Targeted Product Import API tests passed, including a WPS-style `=_xlfn.DISPIMG(...)` formula preview and Confirm flow.
- Ruff and mypy passed for the changed import service.
- `模板测试.xlsx` was parsed successfully: 50 data rows, exact 32-column header, `DISPIMG` image formulas, and one active exact Mall Category match for its category path.

## Boundaries

- No new API, UI control, permission, table, or Alembic revision.
- The workbook's source-supplier cell is empty; after the preview opens, its rows still require a source supplier to pass and be confirmed.
