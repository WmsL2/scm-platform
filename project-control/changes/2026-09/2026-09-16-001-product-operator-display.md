# Change Record: Product Operator Display

Change ID: 2026-09-16-001
Module: catalog
Date: 2026-09-16
Branch: feat/product-operator-display

## Delivered

- Product list API now returns the existing `created_by`, `created_at`, `updated_by`, and `updated_at` values together with the corresponding historical usernames.
- Product Master adds a switchable `商品列表 / 操作记录` tab. The operation-record tab reuses the existing filters and pagination and displays the product image plus the four requested fields per product.
- Historical usernames remain visible even if the user account was later logically deleted.

## Boundaries

- No new audit table, import-batch page, API permission, or Alembic revision.
- This is the current per-product creation and latest-update state, not a full sequence of every historical edit.

## Verification

- Product API integration coverage verifies importer and later updater identifiers, usernames, and timestamps in the list response.
- Frontend typecheck, unit tests, and production build are required before delivery.
