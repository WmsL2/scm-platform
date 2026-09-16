# Change Record: Category CRUD RBAC Permissions

Change ID: 2026-09-16-005
Module: catalog / auth-rbac
Date: 2026-09-16
Branch: feat/category-rbac-permissions

## Delivered

- Added Alembic Revision `20260916_0028` after `20260916_0027` to seed `category:list`, `category:detail`, `category:create`, `category:update`, and `category:delete`.
- Granted the five new permissions to the existing non-deleted `boss` role; other roles are unchanged and must be configured explicitly.
- Replaced the Category management CRUD endpoints' reused Product permissions with the matching Category permissions.
- Kept `/categories/selection` protected by `product:list`, because it serves Product editing, and kept Category template/download import protected by `product:import`.
- Updated the Category menu and route to `category:list`; create, update, delete, template, and import controls now follow their actual backend permissions.
- Added a dedicated Category group to the role permission UI.

## Verification

- Backend integration coverage verifies independent Category CRUD authorization and the boundary between `category:list` and Product category selection.
- Frontend tests verify the Category route, menu, buttons, and role permission grouping contracts.

## Schema / API / Permission

- Schema: no table or column changes; permission catalogue data only.
- Alembic Revision: `20260916_0028`.
- API: Category list/detail/create/update/delete now require their corresponding `category:*` permission.
- UI: Category menu and CRUD actions are independently permission-gated.
