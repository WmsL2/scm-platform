# Change Record: Supplier Master Frontend Real API Integration

Change ID: 2026-09-07-016
Module: supplier / web-admin
Author / Agent: 人员 B
Date: 2026-09-07
Branch: feat/supplier-master-frontend
Commit: GitHub / main Git History is the source of truth.

## Goal

Connect the Supplier Master Web Admin pages to the Supplier API merged by PR #13,
without adding unconfirmed Supplier fields or a frontend Supplier mock API.

## Code

Created:

- `apps/web-admin/src/api/supplier.ts`
- `apps/web-admin/src/api/supplier.spec.ts`
- `apps/web-admin/src/types/supplier.ts`
- `apps/web-admin/src/types/supplier.spec.ts`
- `apps/web-admin/src/router/supplier-routes.spec.ts`
- `apps/web-admin/src/views/supplier/`

Modified:

- `apps/web-admin/src/router/index.ts`, `layouts/BasicLayout.vue`, and `views/dashboard/DashboardView.vue`
- `docs/02-pages.md`, `docs/14-sprint-1-supplier-master-backend-implementation.md`
- `project-control/CURRENT_STATUS.md`, `project-control/modules/supplier.md`, and `project-control/sprints/sprint-01-auth-supplier.md`

## API / UI / Permission Changes

- Consumes `GET /api/v1/suppliers` with the backend pagination, keyword and dual-status filters.
- Consumes `GET /api/v1/suppliers/{id}`, `POST /api/v1/suppliers`, and `PATCH /api/v1/suppliers/{id}`.
- Consumes Supplier command routes. `stop` and `blacklist` require a reason; every command remains constrained by server permission checks and lifecycle rules.
- Uses only frozen fields: supplier name, main brands, advantage and zero or more optional contacts. System supplier codes and statuses are never sent through generic create/update forms.

## Database / Alembic

No new Revision. The frontend consumes backend Revision `20260907_0004` already merged by PR #13.

## Documentation Repair

The backend merge restored stale statements claiming that Supplier Backend awaited merge and Supplier Frontend had not started. This change restores the project status, module status, Sprint and backend implementation document to the merged-code reality.

## Verification

- `npm run test`
- `npm run typecheck`
- `npm run build`
- Backend Supplier API suite and project-control gate
- Browser acceptance using a locally authorized account remains required because the migration seeds permissions but does not assign them to a role.

## Remaining Work

Supplier qualification business fields/API, recovery/reverse lifecycle commands, Supplier statistics and role assignment administration remain outside this change.
