# Change Record: Custom Role Creation

Change ID: 2026-09-08-021
Module: auth-rbac / web-admin
Date: 2026-09-08
Branch: feat/role-management

## Goal

Allow authorized administrators to create a custom role, then configure its permissions through
the existing role-permission management flow. Role edit, disable and delete behavior remain out of
scope until their lifecycle policy is frozen.

## Backend and Permission

- Added `POST /api/v1/admin/roles`, protected by `system:role:create`.
- A new role has an immutable lower-case role code made of letters, numbers and underscores, a
  trimmed display name, no initial permissions, and `created_by` / `updated_by` set to the actor.
- Active role-code and role-name conflicts return deterministic `409` errors. Invalid request
  values return the existing FastAPI validation response.
- Revision `20260908_0007` seeds the `system:role:create` permission. If the local database
  contains the active built-in `system_administrator` role, the migration grants it that permission
  without creating any account or assigning any user to a role.

## Frontend

- The Role Permissions page shows “新增角色” only with `system:role:create`.
- The dialog validates the role-code rule locally, submits the real API, refreshes the list and,
  when the user can list and update permissions, opens the existing permission dialog directly.
- Internal IDs remain hidden; role edit, disable and delete controls are intentionally absent.
- Removed the `RouterView` `out-in` transition from the shared layout. Rapid menu or workspace-tab
  switches could interrupt that leave-before-enter transition and leave the content area empty.
- Permission dialogs prevent concurrent open/save requests and show a loading state while a save is
  in progress. After updating a role assigned to the current user, the client refreshes the current
  authority snapshot.
- The backend rejects a self-role update that would remove the current actor's role-list,
  permission-list or role-permission-update capability across all of their active roles.

## Verification

- Targeted account API tests cover creation, code/name conflicts, invalid codes, initial empty
  permissions, audit actor fields, built-in flag and role-management self-lockout prevention.
- Full backend and frontend quality checks are recorded with the delivery after implementation.

## Database / Alembic

Revision `20260908_0007`, down revision `20260908_0006`. No table or column was added.
