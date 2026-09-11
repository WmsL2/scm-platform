# Change Record: Product / Role / Supplier Lifecycle Patches

Change ID: 2026-09-11-015  
Module: catalog, account, supplier  
Date: 2026-09-11  
Branch: fix/product-role-lifecycle-patches

## Goal

Close four confirmed operational gaps without expanding Product deletion, Category management or pricing scope:

- prevent duplicate Product imports by the source supplier + SKU business key;
- permit safe deletion of unused custom roles;
- support controlled Product basic-data editing;
- hide Products whose source supplier is stopped or blacklisted.

## Database / Permissions

Revision `20260911_0018` adds `uq_scm_product_source_supplier_sku` and seeds:

- `product:update` — edit Product basic data;
- `system:role:delete` — delete custom roles.

The migration deliberately refuses to run when historical duplicate non-null supplier + SKU records exist. It does not silently delete or merge business data. The local development database was explicitly cleared of Supplier/Product data by the operator before the migration was applied.

## Behavior

- Product Excel preview rejects an empty SKU, an existing supplier + SKU combination, and a later duplicate row in the same workbook. Confirm revalidates and the database unique constraint protects concurrent confirms.
- Product detail supports basic source-data editing and switching only to an archived, normal, non-deleted source supplier. Category and price fields remain controlled; `cost_price` continues to use the dedicated atomic recalculation endpoint.
- Product list, supplier-related Product list, Product detail, Product editing and cost updates all exclude a Product when its source supplier is logically deleted, `STOPPED` or `BLACKLIST`. Restoring the supplier to `NORMAL` makes its Products visible again.
- Role deletion is logical and limited to custom roles. Built-in roles and any role still assigned to an active user are rejected; logically deleted users retain their association only as audit history and no longer block role deletion. Deleted roles are removed from active authorization lookups while their audit history remains intact.

## Verification

- `python -m alembic upgrade head` — PASS (`20260911_0018` single head)
- `python -m ruff check app tests` — PASS
- `python -m mypy app` — PASS
- `python -m pytest -q` — PASS (119 tests)
- Web Admin Vitest — PASS (37 tests)
- Web Admin typecheck and production build — PASS

## Boundaries

- Product physical/logical deletion policy is still not implemented.
- Existing Product records with null SKU are not rewritten by this patch; newly imported and edited Products require an SKU.
