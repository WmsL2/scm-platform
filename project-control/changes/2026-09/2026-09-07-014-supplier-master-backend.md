# Change Record: Supplier Master Backend

Change ID: 2026-09-07-014
Module: supplier
Date: 2026-09-07
Branch: feat/supplier-master-backend

## Goal

Implement only the frozen Supplier Master backend: MySQL schema, API, authorization, lifecycle rules, audit persistence and tests. Supplier frontend and Product/Category/Pricing are excluded.

## Code

Created:

- `apps/api-server/app/modules/supplier/` Router, application service, domain rules, repository, ORM models and Pydantic schemas
- `apps/api-server/alembic/versions/20260907_0004_supplier_master.py`
- `apps/api-server/tests/supplier/test_supplier_api.py`
- `apps/api-server/tests/integration/test_supplier_schema.py`

Modified:

- `apps/api-server/app/api/v1/router.py` to register Supplier APIs
- `apps/api-server/app/modules/system/service.py` so BusinessSequenceService can participate in a caller-owned transaction
- `apps/api-server/tests/integration/test_auth_schema.py` to remove the obsolete phase-only assertion that prohibited all Supplier tables

## Database / Alembic

Revision: `20260907_0004`, down revision `20260907_0003`.

Creates `scm_supplier`, `scm_supplier_contact`, `scm_supplier_qualification` and `scm_supplier_cooperation_record`; uses UUID CHAR(36), RESTRICT foreign keys, logical deletion where frozen, status CHECK constraints and global UNIQUE `supplier_code`.

The qualification table deliberately has no qualification business columns because the source material has not confirmed any. The Migration also seeds the eight frozen Supplier permission codes. It does not seed or alter user-role assignments.

## API / Permission

Implements the frozen list/detail/create/update and command routes under `/api/v1/suppliers`; every route uses `require_permission`. Code generation is backend-only. Generic PATCH cannot change either status or the code.

## Tests and verification

- `python -m ruff check .` — PASS
- `python -m mypy app` — PASS
- `python -m pytest -q` — PASS (45 tests)
- `python -m alembic upgrade head` — PASS, local database at `20260907_0004`
- `python -m alembic current` / `heads` — both `20260907_0004`

## Remaining work

- Supplier Master frontend is not implemented in this branch.
- Qualification business fields/API and reverse/recovery state transitions remain gated pending approved policy/source material.
- Open a PR, complete review and merge before treating this work as available on `main`.
