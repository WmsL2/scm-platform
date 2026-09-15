# Change Record: Bid Matching and Manual Selection Foundation

Change ID: 2026-09-15-026
Module: matching
Date: 2026-09-15
Branch: feat/bid-matching-selection

## Goal

Implement the deterministic portion of Task 2: product-candidate recall, scoring,
explainable decisions and the request contracts for manual selection and no-quote.
This change deliberately stops before persistence because Task 1 has not yet merged
the shared bid-project tables into the current branch.

## Code

- Added `app.modules.matching.domain.rules` as a persistence-free matching engine.
  It normalizes Unicode NFKC, case, whitespace, separators and brackets, then recalls
  candidates in this order: buyer item code exact match; brand plus model exact match;
  name, specification and category fallback.
- Only `ACTIVE` products with a source supplier in `ARCHIVED`, `NORMAL`, and not
  logically deleted state are eligible.
- Brand conflicts are excluded from fallback; an explicit model conflict cannot be
  rescued by a name match. Price and supplier-state facts are never identity-score
  signals.
- Scores are stable by score then Product UUID, return at most 20 candidates, and
  persist-ready `match_reason` JSON records rules version, recall stage and signals.
- Added DTOs that require a persisted candidate ID for manual selection, use Decimal
  for the selected unit price, and require explanatory text for `OTHER` no-quote.

## Database and API Boundary

No Migration, ORM Model, Repository, router or permission seed was added. The
following Task 2 operations remain blocked until Task 1's shared tables are present:

- match task and candidate persistence;
- append-only `scm_bid_item_selection` snapshots and `current_selection_id` updates;
- no-quote persistence;
- the four bid-project API routes and TaskQueue progress handling.

The required table and field contract is recorded in the paired Handoff. This change
does not expose a partial HTTP endpoint that could fail at runtime.

## Tests and Verification

- `.venv\\Scripts\\python.exe -m pytest tests/matching -q` — PASS (18 tests)
- `.venv\\Scripts\\python.exe -m ruff check app/modules/matching tests/matching` — PASS
- `.venv\\Scripts\\python.exe -m mypy app/modules/matching` — PASS

The test suite covers normalization, exact code matching, normalized brand/model
matching, stable multiple-candidate ranking, brand/model conflict protection,
fallback manual selection, insufficient conditions, inactive/unavailable filtering,
selection DTO isolation and no-quote validation.

## Remaining Work

After Task 1 merges its schema, wire the matching engine to batch Product/Supplier
queries, persist versioned candidates and snapshots transactionally, add permissioned
routes, then run API and browser acceptance with Task 3.
