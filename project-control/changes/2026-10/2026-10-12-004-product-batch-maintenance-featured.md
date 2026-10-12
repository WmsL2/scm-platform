# Change Record: Product Batch Maintenance and Featured Marker

Change ID: 2026-10-12-004
Module: catalog
Date: 2026-10-12
Branch: codex/feat/product-bulk-status-featured

## Goal

Let an operator change selected Product Master records together, including batch disable/enable and an explicit human-only featured marker, without changing formal product identity or recommendation behavior.

## Database

- Revision `20261012_0054` adds `scm_product.is_featured BOOLEAN NOT NULL DEFAULT false` and the `(status, is_featured)` list-filter index.
- `is_featured` is outside the frozen 43-column import template. New products default to non-featured; same-key re-import does not overwrite an existing manual marker.

## API / Permission

- `GET /api/v1/products` and `GET /api/v1/products/selection-ids` accept optional `is_featured=true|false`.
- `PATCH /api/v1/products/batch` accepts 1--5,000 unique active Product IDs and a non-empty subset of `company_name`, `brand`, three category text fields, `purchasing_agent`, and `is_featured`; requires `product:update`.
- `POST /api/v1/products/commands/batch-disable` and `/batch-enable` accept 1--5,000 unique IDs; both require `product:disable`.
- Batch requests lock all targets in one transaction. Missing, wrong-status, unavailable-supplier or otherwise ineligible target causes no partial mutation.
- SKU, source supplier, product name and price fields are intentionally excluded from batch edit. Cost price retains its dedicated `product:cost:update` flow.

## UI

- The Product list displays a 主推 tag and filters for 主推 / 非主推.
- Selected normal products open one batch-edit dialog for the approved fields and set/cancel 主推. The normal view exposes batch disable; the disabled view exposes batch enable.
- Existing cross-page selection is reused and is cleared after a successful mutation.

## Explicit Boundary

`is_featured` is only a human catalog-management marker. It is not read by Types 1--5 matching, eligibility filtering, recommendation ranking, candidate snapshots or AI prompts.

## Verification

- 2026-10-12 CI follow-up: sorted the migration imports and aligned the Product schema regression assertion with `is_featured`, so repository-wide Ruff and pytest can complete.
- Backend Product API tests: `25 passed`.
- Backend Ruff and Mypy: passed.
- Alembic head: `20261012_0054`; local development database upgraded to that revision.
- Frontend API/UI Vitest, typecheck and production build: passed.
- Authenticated browser acceptance remains pending.
