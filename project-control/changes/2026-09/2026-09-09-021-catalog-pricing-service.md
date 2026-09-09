# Change Record: Catalog Pricing Service

Change ID: 2026-09-09-021
Module: catalog
Branch: feat/catalog-pricing-service

## Changes

- Added a pure, stateless Product Pricing domain service and immutable result object.
- Applied all frozen formulas with Decimal only; every derived value is quantized to four decimal places before downstream use.
- Applied ROUND_HALF_UP to ordinary values and ROUND_DOWN only to `deduction_review`.
- Added deterministic domain errors for zero denominators and tests for rates, rounding, staged calculation, Decimal-only input, and output scale.
- Pricing Service only provides System Calculated Values. A later Product Import must compare each Excel derived price with the corresponding system value: matching values pass; a mismatch must produce an explicit `PRICE_MISMATCH` (or equivalent) error state. Excel values must not silently override system formulas, and this service does not decide manual-resolution or Confirm policy.

## Database / API / Frontend

No Migration, ORM, API, Router, Frontend, Supplier code, or Product Import implementation changes.

## Tests

Run `ruff check .`, `mypy app`, `pytest tests/catalog/test_pricing.py -q`, and the full backend `pytest` from `apps/api-server`.

## Next Step

Integrate this domain service in the later Catalog Schema / Product Backend workstream after its Schema/Migration work is ready.
