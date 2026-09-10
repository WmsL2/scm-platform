# Change Record: Account User Delete

Change ID: 2026-09-10-028
Module: account / auth-rbac

## Changes

- Added logical user deletion through `DELETE /api/v1/admin/users/{user_id}` and `system:user:delete`.
- Added `deleted_by` / `deleted_at` audit fields; deletion increments token_version, preserves username, user status and user-role history, and prevents self-delete.
- Deleted users cannot authenticate or use existing protected-token sessions; UsersView now confirms and executes deletion for permitted non-self rows.

## Database / API / Frontend

Revision `20260910_0010`; no physical `sys_user` deletion, no user restore, role delete/disable, or user disable implementation.
