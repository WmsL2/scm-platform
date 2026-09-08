# Change Record: Account / Registration / Profile

Change ID: 2026-09-08-018
Module: auth-rbac
Date: 2026-09-08
Branch: feat/account-registration-profile

## Goal

Complete and verify the first Account / Registration / Profile scope: self-registration and administrator review, permission-protected user/role/permission administration, profile display and password change. This change does not introduce a default administrator, a hard-coded administrator identity, refresh tokens or session / multi-device logout policy.

## Backend

- `POST /api/v1/auth/register` creates a `PENDING` account; the user lifecycle is `PENDING` / `ENABLED` / `DISABLED` / `REJECTED`.
- Registration review supports approve and reject commands. `reviewed_by`, `reviewed_at` and `review_note` retain the minimum review audit information.
- `POST /api/v1/auth/change-password` verifies the current password, persists a new Argon2id hash and increments `token_version`, invalidating tokens issued before the change.
- Administrator APIs provide user listing and whole-set user-role replacement, role listing and whole-set role-permission replacement, a dynamic permission directory, and registration-request listing/review.
- The permission directory seeds and reads seven permissions: `system:user:list`, `system:user:role:update`, `system:role:list`, `system:role:permission:update`, `system:permission:list`, `system:registration:list` and `system:registration:review`.

## Frontend

- Added `/register`, `/admin/users`, `/admin/roles` and `/admin/registrations`.
- User roles and role permissions are assigned dynamically from administrator APIs; no role or Supplier permission directory is hard-coded in the frontend.
- The profile dropdown exposes the complete current username, roles and permissions, with change-password and logout actions.
- The change-password dialog sends only the current and new passwords.
- Each system-management menu entry has its own permission condition instead of an administrator username or role check.

## Database / Alembic

Revision: `20260908_0006`, down revision `20260908_0005`.

The Account migration was originally drafted as temporary revision `20260908_0005`. Because the Supplier Delete & Import branch merged first, it was finalized as `20260908_0006` on top of Supplier Delete & Import revision `20260908_0005`. No merge migration was created.

## Verification

- Backend Ruff — PASS
- Backend mypy — PASS
- Backend pytest — PASS (51 passed)
- Frontend Vitest — PASS (22 passed)
- Frontend typecheck — PASS
- Frontend build — PASS
- Alembic heads / current — `20260908_0006`
- Supplier schema integration test — PASS

## Boundaries / Remaining Work

- No default administrator account, password or secret is created; administrator identity is never determined from a hard-coded username or role.
- The permission directory is sourced from `sys_permission`.
- Rejected registrations remain retained and active for username uniqueness: a `REJECTED` username continues to occupy its username. Reapply / reopen policy is future work.
- Refresh Token, Session and Multi-device Logout remain future scope.
- Role creation / deletion policy remains to be frozen.
