# Change Record: Supplier Matching Foundation

Change ID: 2026-09-09-022
Module: supplier
Date: 2026-09-09
Branch: fix/supplier-matching-foundation

## Goal

Provide deterministic supplier-name matching rules for a future Product Import,
and prevent blank Supplier Master request values from becoming stored empty strings.
Product Import, Product Schema, Supplier Quote, Migration and Frontend are outside
this change.

## Baseline

- Base SHA: `228e043ec306b4fecd4163cf70106ceb79683a13`
- Relevant authority: ADR-0008 Product Source Supplier Resolution.

## Code

- `SupplierCreateRequest` and `SupplierUpdateRequest` now share local Pydantic
  validation for `supplier_name`, `main_brands` and `advantage`: trim surrounding
  whitespace, then reject an empty result. `SupplierContactInput` normalizes blank
  optional contact fields to `None` and still requires a name or phone.
- Added `domain/matching.py` with pure deterministic helpers:
  `normalize_supplier_name()`, `is_eligible_source_supplier()` and
  `classify_supplier_name_match()`.
- Name normalization is exactly Unicode NFKC, trim and whitespace collapse. It
  does not remove company suffixes or regions, and does not apply aliases,
  case conversion, fuzzy matching or AI matching.
- A candidate is eligible only when it is `ARCHIVED`, `NORMAL` and not logically
  deleted. Exact-name results are `UNMATCHED`, `INELIGIBLE`, `MATCHED/NAME_EXACT`
  or `AMBIGUOUS`; only one eligible candidate is automatically selected.

## Repository and Database Boundary

No Repository method was added. The existing Supplier list `contains` search is
not deterministic matching and is not reused. There is no normalized Supplier-name
database column in this scope, so candidate retrieval remains a future Product
Import Schema decision.

No Migration, ORM model, Product Import table, Product Schema, API, permission or
Frontend change was made.

## Tests and Verification

- `python -m ruff check .` — PASS
- `python -m mypy app` — PASS (39 source files)
- `python -m pytest tests/supplier -q` — PASS (40 tests)
- `python -m pytest` — PASS (94 tests)

The matching tests cover NFKC, trim, whitespace collapse, suffix and region
preservation, no fuzzy match, all three ineligible conditions, unique exact match,
ambiguous candidates and one-valid-plus-one-invalid candidates. Request-schema
tests cover create/update blank rejection and contact blank handling.

## Remaining Work

Future Product Import owns database candidate retrieval, Match Decision persistence,
manual resolution, import state transitions and Confirm-time eligibility rechecks.
This change does not create or mark any Product Import capability as implemented.
