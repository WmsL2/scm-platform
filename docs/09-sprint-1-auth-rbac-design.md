# Sprint 1 Auth/RBAC Design Freeze

Status: FROZEN except listed PENDING items. Auth stays inside the FastAPI Modular Monolith.

## Shared contract

Implementation clarification: UUID is MySQL CHAR(36) through UUIDChar36 (ADR-0006); sys_user includes token_version. ADR-0016 supersedes the phase-1 stateless logout boundary.

UUID primary keys and ID foreign keys only. Audit actor fields store user_id, never username or real name. CurrentUser is built only by Router/permission dependency; services receive an actor and never parse tokens. Historical business records do not cascade; ephemeral `sys_auth_session` records are the explicit exception and cascade only if a user is physically removed outside normal application behavior.

## Data dictionary

| Table | Responsibility | FROZEN columns and constraints |
|---|---|---|
| sys_user | authentication subject | id UUID PK; username varchar(64) NOT NULL UNIQUE; password_hash varchar(255) NOT NULL; user_status ENABLED/DISABLED default ENABLED; is_deleted default false; created/updated time and actor IDs. |
| sys_role | stable role collection | id UUID PK; role_code varchar(64) UNIQUE; role_name varchar(128); is_builtin default false; is_deleted default false; audit fields. |
| sys_permission | authorization directory | id UUID PK; permission_code varchar(128) UNIQUE; permission_name varchar(128); permission_type MENU/API/ACTION; is_deleted default false; audit fields. |
| sys_user_role | user-role association | user_id and role_id UUID FK; UNIQUE(user_id,role_id); index role_id; creation audit. |
| sys_role_permission | role-permission association | role_id and permission_id UUID FK; UNIQUE(role_id,permission_id); index permission_id; creation audit. |
| sys_auth_session | revocable browser session | id UUID PK; user_id FK; current/previous Refresh Token hashes; rotation counter; activity, idle/absolute expiry and revocation fields. |
| sys_biz_sequence | concurrency-safe number source | id UUID CHAR(36) PK; sequence_key varchar(64) UNIQUE; prefix varchar(16); next_value bigint CHECK >= 1; audit fields. |

FK is RESTRICT. IDs/FKs and UNIQUE keys are indexed. Exact MySQL DDL is deferred to a future migration.

## FROZEN behavior

username uniqueness applies to non-deleted accounts. Store only Argon2id password hashes; no plaintext/reversible secret. Referenced users are disabled or logically deleted, never physically deleted. role_code is stable machine code and role_name is display text; built-in roles cannot be deleted. Referenced role/permission records are logically deleted or disabled, never physically deleted. Custom roles use an immutable lower-case `role_code` made of letters, numbers and underscores, plus a display `role_name`; a new custom role starts with no permissions and requires `system:role:create` to create.

Permissions use lower-case domain:resource:action; never use Chinese page labels for authorization.

| Domain | Codes |
|---|---|
| system | system:user:list/create/update/disable; system:role:list/create/permission:update |
| supplier | supplier:list/detail/create/update/submit/archive/stop/blacklist |

CurrentUser contains user_id, username, roles and permissions. Flow: Router -> CurrentUser/require_permission -> Application Service -> Repository. 401 is unauthenticated, 403 is authenticated but unauthorized.

## Business Sequence implementation

Revision `20260907_0003` creates `sys_biz_sequence` and initializes the controlled
`SUPPLIER` sequence as `prefix=SUP`, `next_value=1`. `BusinessSequenceService`
uses one database transaction and `SELECT ... FOR UPDATE` on `sequence_key` before
reading and incrementing `next_value`. It returns the assigned prefix plus an
eight-digit zero-padded number, so the first supplier allocation is `SUP00000001`.
The service never creates a missing sequence, reuses an issued value, or exposes an
HTTP endpoint; Supplier Master will consume it after its field Gate is removed.

Login is POST /api/v1/auth/login; refresh is POST /api/v1/auth/refresh; current user is GET /api/v1/auth/me; logout is POST /api/v1/auth/logout. Access Token defaults to 30 minutes and contains only user/session identity, token version, unique token ID and timing claims; it must not contain roles, permissions, suppliers, or business snapshots. Refresh Token is opaque, rotating, stored only as a hash on the server and transported in an HttpOnly Cookie. Sessions expire after three days without refresh and absolutely after thirty days. Permission changes remain visible on the next request because effective permissions are loaded dynamically.

## PENDING

Role disable policy and an administrator-facing device/session management page remain outside the current frozen scope.
