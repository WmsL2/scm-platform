# Change Record: Product Master Category Decoupling

Change ID: 2026-09-18-006  
Date: 2026-09-18  
Status: IMPLEMENTED

## Scope

Implement the approved temporary removal of the Product Master to Category Master association while
retaining Category Management as a separate module.

## Database

- Added Alembic Revision `20260918_0032` (parent `20260918_0031`).
- Removed `category_id`, its foreign key, and supporting index from `scm_product` and
  `scm_product_import_row`.
- The migration does not delete `scm_category` data or any of the three Product category text columns.

## Behaviour

- Import requires non-empty level-1, level-2 and level-3 category texts, but does not resolve them
  through Category Master.
- Confirm and re-import write those three values directly; Supplier + SKU remains immutable.
- Product edit requires the same three texts, provides Product Master-backed linked suggestions, and
  accepts a newly typed path without creating a Category record.
- Category deletion is no longer blocked by Product references.

## Verification

- `python -m alembic upgrade head`: PASS on local MySQL; current revision `20260918_0032`.
- `python -m pytest tests/catalog -q`: 34 passed.
- Remaining backend suites: 94 passed.
- Web Admin typecheck, targeted Vitest (9 tests), and production build: PASS.
