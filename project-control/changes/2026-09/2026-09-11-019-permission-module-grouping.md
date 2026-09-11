# Change Record: Permission Module Grouping

Change ID: 2026-09-11-019  
Module: auth-rbac / web-admin  
Date: 2026-09-11  
Branch: feat/permission-module-grouping

## Goal

Improve the role permission assignment page by grouping the existing dynamic permission directory into business modules without changing backend permission codes or authorization behavior.

## Frontend

- Derives each module from the prefix of `permission_code`.
- Displays known modules as 系统管理、供应商管理 and 商品管理; unknown prefixes remain visible through a deterministic fallback label.
- Uses collapsible module sections.
- Supports module-level select all / clear all and an indeterminate state when only some permissions are selected.
- Preserves individual permission selection and the existing single-save API contract.
- Shows each permission's display name and machine code for unambiguous administration.

## Verification

- `npm run test` — PASS (38 tests)
- `npm run typecheck` — PASS
- `npm run build` — PASS

## Database / Backend

No database, migration, backend API or authorization-policy change.
