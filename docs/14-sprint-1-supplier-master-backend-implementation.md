# Sprint 1 Supplier Master Backend

Status: MERGED into `main` via PR #13. Supplier Frontend integration is implemented on `feat/supplier-master-frontend`.

## Scope and field boundary

Revision `20260907_0004` implements only the frozen Supplier Master fields from `docs/data-gates/supplier-field-dictionary.md`:

- `scm_supplier`: system-generated immutable `supplier_code`, `supplier_name`, `main_brands`, `advantage`, two lifecycle statuses, logical deletion and audit actors/timestamps.
- `scm_supplier_contact`: nullable `contact_name` and `contact_phone`, logical deletion and audit. A stored contact must contain at least one of those two values.
- `scm_supplier_qualification`: only its confirmed supplier relationship, logical deletion and audit columns. No unconfirmed qualification business field or qualification API exists.
- `scm_supplier_cooperation_record`: immutable NORMAL → STOPPED/BLACKLIST history with reason, actor and occurrence time.

The source supplier code is not persisted or used as `supplier_code`. The backend issues codes only through `BusinessSequenceService` key `SUPPLIER` under `SELECT FOR UPDATE`; the service joins the Supplier write transaction, and `supplier_code` also has a database UNIQUE constraint.

## API and permission contract

| API | Permission | Behavior |
|---|---|---|
| `GET /api/v1/suppliers` | `supplier:list` | paged list with optional keyword/status filters |
| `GET /api/v1/suppliers/{id}` | `supplier:detail` | detail and active contacts |
| `POST /api/v1/suppliers` | `supplier:create` | creates DRAFT + NORMAL supplier and system code |
| `PATCH /api/v1/suppliers/{id}` | `supplier:update` | edits frozen business fields and replaces active contacts; cannot alter code or statuses |
| `POST .../commands/submit` | `supplier:submit` | DRAFT → PENDING |
| `POST .../commands/archive` | `supplier:archive` | PENDING → ARCHIVED and records archive actor/time |
| `POST .../commands/stop` | `supplier:stop` | NORMAL → STOPPED with required reason/history |
| `POST .../commands/blacklist` | `supplier:blacklist` | NORMAL → BLACKLIST with required reason/history |

The Migration seeds these eight permissions into `sys_permission`; role assignment remains system authorization administration scope. The API rejects unrecognized request fields, so callers cannot silently supply a supplier code or bypass the command state machine.

## State and audit behavior

- Reverse archive transitions and cooperation recovery are intentionally not implemented because their approval policy remains pending.
- Create/edit/submit update audit actor/time. Archive additionally writes `archived_by` and `archived_at`. Stop/blacklist additionally insert a cooperation history row.
- No physical supplier delete endpoint is exposed. No CASCADE foreign keys are used.

## Verification

On the local MySQL development database, `alembic upgrade head` reached `20260907_0004`. Backend checks: Ruff, mypy and pytest passed; the suite covers schema, permission denials, create/edit, code protection, all allowed and rejected lifecycle paths, and cooperation history.
