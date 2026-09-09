# Change Record: Product Master

Change ID: 2026-09-09-026
Module: catalog / product
Date: 2026-09-09
Branch: feat/product-master

## Goal

Implement the frozen Product Master foundation only: Category/Product schema, Product read APIs, permission-controlled current cost updates, Pricing Service integration, Web Admin pages and verification.

## Delivered

- Alembic revision `20260909_0008` creates `scm_category` and `scm_product`; `20260909_0009` aligns Product with the latest 32-column Excel by adding `selling_points` and `storefront_type` and removing the superseded remote-freight note.
- Three permissions are seeded and assigned to the existing `system_administrator` role: `product:list`, `product:detail`, `product:cost:update`.
- `GET /api/v1/products`, `GET /api/v1/products/{id}` and `PATCH /api/v1/products/{id}/cost-price` are protected by those permissions.
- Cost update locks the Product row, reads the formal Category deduction rate, calls the frozen Pricing Service and persists every derived price/margin in the same transaction. `source_supplier_id` is never changed.
- Vue Product list/detail pages expose the cost operation only to users with `product:cost:update`.

## Explicitly excluded

- No `scm_supplier_product_quote`, quotation history, quote validity, quote voiding or multi-supplier comparison.
- No manual Product-create API, Product Excel import, Category Source Loader, staging tables or Supplier Matching persistence.
- No Product/Category deletion or recovery model.

## Verification

- `alembic upgrade head`, `alembic current`, `alembic heads` — revision `20260909_0009` is the single head.
- `ruff check .` — pass.
- `mypy app --cache-dir C:\\scm-platform\\.mypy-codex-cache` — pass.
- `pytest -q` — 108 passed.
- Web Admin `npm run typecheck`, `npm test -- --run`, `npm run build` — pass; 31 tests passed.

## Next Step

Implement Product Import using the already frozen Category Source Loader, staging, deterministic Supplier Matching, price-difference preview and all-or-nothing Confirm rules. Do not introduce an independent quote domain.
