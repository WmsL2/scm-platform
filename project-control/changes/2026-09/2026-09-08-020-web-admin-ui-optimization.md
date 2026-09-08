# Change Record: Web Admin UI Optimization

Change ID: 2026-09-08-020
Module: auth-rbac / web-admin
Date: 2026-09-08
Branch: feat/web-admin-ui-optimization

## Goal

Improve the existing Web Admin account-management interface without changing the API, database
schema, authorization model or registration-review lifecycle. Internal role and permission UUIDs
must not be displayed to business users. Pending registration work must be visible from the
sidebar menu.

## Frontend Changes

- User Management now displays username, a Chinese user-status tag, role-name tags and the
  permission-gated “分配角色” action. Role UUIDs are not rendered. An unassigned user displays
  “未分配角色”; the role assignment dialog lists role names. The action is visible only for
  `ENABLED` users.
- Role Permissions now displays only role code, role name and the permission-gated “配置权限”
  action. Permission UUIDs are not rendered. The configuration dialog lists permission names.
- A Pinia registration store reads the existing pending-registration endpoint `total`. The sidebar
  “注册审批” menu shows a red numeric badge only when the total is greater than zero. Loading the
  approval page and completing an approve/reject action synchronise the badge immediately.
- Registration Approval now separates pending requests from approval history. History is paginated
  and shows the processed username, result, review timestamp and review note. It excludes pending
  requests and refreshes after an approval action.
- The new status presentation helper maps `PENDING` / `ENABLED` / `DISABLED` / `REJECTED` to
  待审批 / 已启用 / 已禁用 / 已拒绝. Unexpected server values remain visible with a neutral tag.

## API / Permission / Database

- No existing API route, request body, backend permission or database schema changed. `UserResponse`
  now adds the backwards-compatible read-only `role_names` field alongside retained `role_ids`, so
  the UI can show role names without requesting role administration data separately.
- `GET /api/v1/admin/registration-history` is a new paginated, read-only endpoint guarded by the
  existing `system:registration:list` permission. It returns only users with `reviewed_at` set,
  ordered from newest review to oldest.
- `PUT /api/v1/admin/users/{user_id}/roles` now returns `409 ACCOUNT_USER_NOT_ENABLED` unless the
  target user's status is `ENABLED`. This enforces the UI rule for PENDING, REJECTED and DISABLED
  users at the backend boundary.
- The badge continues to use `GET /api/v1/admin/registration-requests`, which is already guarded
  by `system:registration:list` and returns only pending registrations. Approval actions remain
  guarded by `system:registration:review`.
- Alembic Revision: none. No database migration was created or modified.

## Verification

- `npm run test` — PASS, 12 files / 31 tests.
- `npm run typecheck` — PASS.
- `npm run build` — PASS. Existing Vite chunk-size warning remains (`index` bundle larger than
  500 kB); it is outside this scoped UI change.
- `python -m ruff check .` — PASS.
- `python -m mypy app` — PASS.
- `python -m pytest tests/account/test_account_api.py -q` — PASS, 9 tests.
- `git diff --check` — PASS.

## Remaining Work

- Browser acceptance with an account that can view registration requests and review them: verify
  the badge is hidden at zero, displays the exact pending count above zero, and refreshes after
  approval or rejection.
