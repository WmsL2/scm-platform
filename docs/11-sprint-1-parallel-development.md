# Sprint 1 Parallel Development

Status: FROZEN.

Modules are app/modules/auth, app/modules/system and app/modules/supplier, each using existing api, application, domain, infrastructure, schemas and dependencies.py convention. Create only files required by implementation; main.py must not accumulate business code.

- feat/auth-rbac delivers the minimum Auth Kernel first: user, role, permission, relation tables, CurrentUser and require_permission.
- feat/supplier begins real Auth Actor dependency only after Auth Kernel reaches main.
- Supplier migration remains blocked by SUPPLIER_FIELD_DICTIONARY_PENDING_SOURCE_CONFIRMATION.

| Shared area | Owner | Rule |
|---|---|---|
| app/main.py; app/api/v1/router.py | integrator | module developers do not pile routes here |
| app/core and app/common | System/Auth owner | contract PR first |
| Alembic config and heads | integrator | add-only revisions and merge heads |
| README; CURRENT_STATUS | integrator | update through change records |
| auth/system modules | Auth owner | Supplier branch does not edit |
| supplier module | Supplier owner | Auth branch does not edit |

Migration integration: Auth/RBAC Kernel -> Business Sequence -> Supplier Master. Existing main migrations are immutable; solve multiple heads with Alembic merge.

