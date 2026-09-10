# Change Record: Auth Profile Permission Names

Change ID: 2026-09-10-032
Module: auth-rbac / web-admin

## Changes

- `GET /api/v1/auth/me` now includes `role_names` and `permission_names`,
  database-backed `role_code` / `permission_code` to Chinese display-name mappings
  from `sys_role` and `sys_permission` for the current user's active roles.
- Machine-readable `roles` and sorted `permissions` remain intact. Permissions
  are still the only values used by `require_permission` and frontend
  `hasPermission` checks.
- The profile dialog and topbar display database role and permission names, with
  a code fallback when a mapping is unavailable. No frontend mapping or
  permission-directory request is added.
- Duplicate permissions granted through multiple roles are returned once; deleted
  roles and permissions are excluded from their codes and display-name mappings.

## Database

No database schema or Alembic migration change. `sys_permission.permission_name`
already provides the display value.
