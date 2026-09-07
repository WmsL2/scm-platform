# Change Record: Business Sequence

Change ID: 2026-09-07-011
Module: system
Author / Agent: 人员 A
Date: 2026-09-07
Branch: feat/business-sequence
Commit: 以 GitHub / main Git History 为事实来源

## Goal

Implement the reusable, MySQL transaction-safe business-number service required by
the frozen Supplier code rule, without implementing Supplier, Product, Quote, or
additional Auth features.

## Created Files

- `apps/api-server/alembic/versions/20260907_0003_business_sequence.py`
- `apps/api-server/app/modules/system/service.py`
- `apps/api-server/tests/integration/test_business_sequence.py`

## Modified Files

- `apps/api-server/app/modules/system/models.py`
- `apps/api-server/app/modules/system/repository.py`
- `apps/api-server/tests/integration/test_auth_schema.py`
- `project-control/CURRENT_STATUS.md`
- `project-control/modules/system.md`
- `docs/09-sprint-1-auth-rbac-design.md`

## Deleted Files

None.

## Database / Alembic

Revision: `20260907_0003` (down revision `20260903_0002`).

Creates `sys_biz_sequence` with UUID CHAR(36), unique `sequence_key`, `prefix`,
`next_value`, audit fields, and a controlled `SUPPLIER` seed row. The first issued
Supplier code is `SUP00000001`.

## API Changes

None. BusinessSequenceService is internal infrastructure and has no HTTP route.

## UI Changes

None.

## Permission Changes

None.

## Business Rule Changes

`BusinessSequenceService.issue_code()` locks the configured sequence row with
`SELECT FOR UPDATE`, issues the current value, increments it in the same transaction,
and does not create missing configurations or reuse issued values.

## Tests

Commands:

- `python -m ruff check .`
- `python -m mypy app`
- `python -m pytest`
- `python -m alembic current`
- `python -m alembic heads`
- `npm run test`
- `npm run typecheck`
- `npm run build`

Result: Ruff PASS; mypy PASS; pytest 42 passed; Alembic current/head both
`20260907_0003`; frontend Vitest 11 passed; frontend typecheck and production
build PASS; `/health/live` and `/health/ready` both HTTP 200.

## Known Issues

The local MySQL is 8.0.12, which lacks `information_schema.check_constraints`.
The existing Auth Schema test now performs CHECK metadata and invalid-value assertions
only where that system view is available; all other schema checks run on every MySQL 8
environment. CI uses its own ephemeral MySQL 8 service.

`alembic check` is not currently available because the pre-existing
`alembic/env.py` does not configure `target_metadata`; this does not affect
`alembic upgrade head`, which completed successfully. This branch does not expand
that unrelated Alembic autogenerate configuration scope.

## Remaining Work

Supplier Master remains gated by `SUPPLIER_FIELD_DICTIONARY_PENDING_SOURCE_CONFIRMATION`.
Feature Branch、PR 与 Merge 事实以 GitHub / `main` 历史为准。

## Next Step

After Supplier Field Gate removal, Supplier Master should call BusinessSequenceService
instead of generating codes from IDs or row counts.
