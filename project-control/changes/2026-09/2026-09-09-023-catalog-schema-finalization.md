# Change Record: Catalog Schema Finalization

Change ID: 2026-09-09-023
Module: catalog / category-pricing
Date: 2026-09-09
Branch: docs/catalog-schema-finalization
Type: Schema Review Closure

## Goal

Close the irreversible Catalog schema decisions before any Category/Product Migration. This change is documentation-only: it creates no Migration, ORM, API, frontend, Pricing Service or Product Import implementation.

## Decisions

- `scm_product.category_id` is FROZEN as `CHAR(36) NOT NULL`: the formal Product Confirm path requires successful category resolution and pricing derives its rate from Category.
- `source_supplier_id` remains FROZEN per ADR-0008: `CHAR(36) NOT NULL`, indexed, non-unique and FK to `scm_supplier.id ON DELETE RESTRICT`; it means only Source Supplier.
- Product and Category logical-delete policies are BUSINESS_DECISION_REQUIRED. C1 must not add deletion columns merely by convention; Category retains `is_active` as availability, not deletion.
- Product-to-Category `ON DELETE RESTRICT` remains RECOMMENDED; `CASCADE` is prohibited.
- `brand` / `model` / `product_name` and the three pricing input columns remain RECOMMENDED nullable because the supplied field dictionary does not freeze business requiredness.
- Category UNIQUE constraints remain RECOMMENDED pending data preflight.

## Category Data Preflight

The current environment contains `京东大表-礼品.xlsx`, a Product Master workbook rather than either authoritative Category dimension source. It contains 16,333 product rows: 16,321 have a complete three-level path, 12 have a blank category component, and 227 complete paths are distinct. The 199 repeated paths (16,293 product rows) are expected Product-to-Category reuse, not duplicate Category-dimension rows. This workbook has no category external-ID column, source type, active flag or business-unit field, so it cannot validate the proposed Category UNIQUE constraints. Before the Category/Product Migration, the actual dimension sources must be checked for duplicate external IDs, duplicate full paths, NULL external IDs, empty names, exact duplicate rows, same ID/different name and same name/different ID.

## Migration Plan

Current Alembic head is `20260908_0007`. The next Category/Product Migration should contain only `scm_category` and `scm_product`, their frozen/recommended fields, FKs, indexes, Decimal columns and Category unique constraints after preflight. It must not include Product Import staging or supplier-match tables.

## ADR

No ADR-0009 is proposed. This closure applies existing product, pricing, UUID and source-supplier decisions; it does not introduce a new architecture decision.

## Verification

- `git diff --check` — PASS.
- `apps/api-server/.venv/Scripts/python.exe -m pytest apps/api-server/tests/test_project_control_gate.py -q` — PASS (7 passed; pytest cache write warning only).
