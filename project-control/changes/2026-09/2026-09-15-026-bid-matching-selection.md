# Change Record: Bid Matching and Manual Selection Foundation

Change ID: 2026-09-15-026
Module: matching
Date: 2026-09-15
Branch: feat/bid-matching-selection

## Goal

Implement the deterministic portion of Task 2: product-candidate recall, scoring,
explainable decisions and the request contracts for manual selection and no-quote.
Task 1's shared bid-project tables are now merged through PR #46, so this change
also persists matching results and manual selection decisions on that schema.

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

No Migration, ORM Model or permission seed was added. This task uses Task 1's
`20260915_0024` shared tables and existing `bid:match` / `bid:select` permissions.

- `POST /api/v1/bid-projects/{id}/commands/start-matching` writes a task, processes
  the project's parsed items from one eligible Product/Supplier batch, persists the
  Top 20 candidates and moves the project to `SELECTING`.
- `GET /api/v1/bid-projects/{id}/items/{item_id}/candidates` returns the newest
  completed task's candidate list.
- Selection locks the project, item, candidate, Product and Supplier, rechecks live
  eligibility and max price, appends immutable snapshots, then moves the item's
  `current_selection_id` in the same transaction.
- No-quote clears the current selection pointer and stores the selected reason JSON.

## Tests and Verification

- `.venv\\Scripts\\python.exe -m pytest tests/matching -q` — PASS (20 tests)
- `.venv\\Scripts\\python.exe -m ruff check app/modules/matching tests/matching` — PASS
- `.venv\\Scripts\\python.exe -m mypy app/modules/matching` — PASS

The test suite covers normalization, exact code matching, normalized brand/model
matching, stable multiple-candidate ranking, brand/model conflict protection,
fallback manual selection, insufficient conditions, inactive/unavailable filtering,
selection DTO isolation and no-quote validation.

## Remaining Work

Perform browser acceptance with Task 3. Matching uses the existing `TaskQueue` abstraction
with the local inline adapter; a future ARQ runtime must provide a worker/session-safe task
runner before enabling asynchronous dispatch.
