# Sprint 1 Supplier Design Freeze

Status: system relationship and lifecycle are FROZEN. Field dictionary is GATED.

Supplier Master answers who supplies. It is independent from Product Master and Supplier Product Quote. Every future relation uses supplier_id, never supplier_name.

| Table | Responsibility | FROZEN columns/relationships |
|---|---|---|
| scm_supplier | supplier subject | id UUID PK; supplier_code varchar(16) UNIQUE; archive_status DRAFT/PENDING/ARCHIVED default DRAFT; cooperation_status NORMAL/STOPPED/BLACKLIST default NORMAL; is_deleted; created/updated/archived actor and time. |
| scm_supplier_contact | contacts | id UUID PK; supplier_id FK RESTRICT; audit and logical deletion. Contact business fields are GATED. |
| scm_supplier_qualification | qualifications | id UUID PK; supplier_id FK RESTRICT; audit and logical deletion. Qualification fields are GATED. |
| scm_supplier_cooperation_record | status history | id UUID PK; supplier_id FK RESTRICT; from/to cooperation status, reason, actor, occurred_at. Historical; no physical delete. |

Supplier code is generated only through BusinessSequence with key SUPPLIER, format direction SUP00000001, in a transaction using SELECT FOR UPDATE and database UNIQUE fallback. Never MAX(id)+1; never reuse; clients cannot provide or update it.

## Field Gate

SUPPLIER_FIELD_DICTIONARY_PENDING_SOURCE_CONFIRMATION is active: no supplier archive/template exists in the repository. Enterprise name, tax ID, address, banking, contact details and cooperation-level fields are GATED; their nullable/UNIQUE rules must not be invented. Supplier Migration is prohibited until this gate is removed.

## State matrix

| Dimension | Transition | Permission | Required action |
|---|---|---|---|
| archive | DRAFT -> PENDING | supplier:submit | audit actor/time |
| archive | PENDING -> ARCHIVED | supplier:archive | archived actor/time and audit |
| archive | reverse transitions | PENDING | no implementation until review policy is confirmed |
| cooperation | NORMAL -> STOPPED | supplier:stop | reason, actor/time, cooperation record, audit |
| cooperation | NORMAL -> BLACKLIST | supplier:blacklist | reason, actor/time, cooperation record, audit |
| cooperation | STOPPED/BLACKLIST -> NORMAL | PENDING | recovery policy required |

Effective selectable supplier is ARCHIVED + NORMAL + not deleted.

Supplier is logical-delete only. Contacts/qualifications can logical-delete; referenced history is retained. No cascade deletes.

## Design API and pages

All business APIs use /api/v1 and the shared response/error envelope. Command endpoints are frozen to prevent generic PATCH bypassing state rules.

| API | Permission |
|---|---|
| GET /api/v1/suppliers; GET /api/v1/suppliers/{id} | supplier:list/detail |
| POST /api/v1/suppliers; PATCH /api/v1/suppliers/{id} | supplier:create/update |
| POST /api/v1/suppliers/{id}/commands/submit, archive, stop, blacklist | matching action code |

Page designs only: /suppliers, /suppliers/new, /suppliers/:id, /suppliers/:id/edit. UI permission control is not the security boundary; backend require_permission is.

