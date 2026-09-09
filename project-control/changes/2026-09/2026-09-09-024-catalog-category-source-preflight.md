# Change Record: Catalog Category Source Data Preflight

Change ID: 2026-09-09-024
Module: catalog / category-pricing
Branch: docs/catalog-category-preflight
Type: Source Data Preflight / Schema Rule Finalization

## Results

- Completed preflight of the two formal Category source files.
- Mall level-3 source: 6,289 rows; no blank names or level-3 external IDs, no duplicate external IDs, and no complete duplicate rows. Its external-ID UNIQUE constraint passed preflight.
- Mall source has two same-name-path groups with different level-3 external IDs; Product Import must treat a name-only match to either path as `AMBIGUOUS`.
- Industrial source: 578 rows, including three complete duplicate paths; deterministic full-path deduplication produces 575 formal paths.
- Estimated formal Category count is 6,864: 449 at `0.0500` and 6,415 at `0.0800`.
- Removed the recommendation for a global database `UNIQUE(source_type, level1_name, level2_name, level3_name)`. Industrial full path is now a Source Loader / Import deduplication and conflict-check rule only.

## Database / Code

No Migration, ORM, API, Frontend, or Backend business-code changes.

## Next Step

Create Category / Product Migration from the then-current Alembic Head; do not add global path UNIQUE or conditional-unique mechanisms without a separate ADR.
