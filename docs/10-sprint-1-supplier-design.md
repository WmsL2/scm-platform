# Sprint 1 Supplier Design Freeze

Status: system relationship, lifecycle and confirmed field dictionary are FROZEN; ready for Schema Design.

Supplier Master answers who supplies. It is independent from Product Master and Supplier Product Quote. Every future relation uses supplier_id, never supplier_name.

| Table | Responsibility | FROZEN columns/relationships |
|---|---|---|
| scm_supplier | supplier subject | id UUID PK; supplier_code varchar(16) UNIQUE; archive_status DRAFT/PENDING/ARCHIVED default DRAFT; cooperation_status NORMAL/STOPPED/BLACKLIST default NORMAL; is_deleted; created/updated/archived actor and time. |
| scm_supplier_contact | contacts | id UUID PK; supplier_id FK RESTRICT; audit and logical deletion. Contact business fields are GATED. |
| scm_supplier_qualification | qualifications | id UUID PK; supplier_id FK RESTRICT; audit and logical deletion. Qualification fields are GATED. |
| scm_supplier_cooperation_record | status history | id UUID PK; supplier_id FK RESTRICT; from/to cooperation status, reason, actor, occurred_at. Historical; no physical delete. |

Supplier code is generated only through BusinessSequence with key SUPPLIER, format direction SUP00000001, in a transaction using SELECT FOR UPDATE and database UNIQUE fallback. Never MAX(id)+1; never reuse; clients cannot provide or update it.

## Field Gate

真实供应商来源资料已确认，详见 `docs/data-gates/supplier-field-dictionary.md`。`supplier_name`、`main_brands`、`advantage`、`contact_name`、`contact_phone` 的来源语义与已确认规则可用于 Schema Design；其中联系人与电话为 nullable。`supplier_code` 继续仅由系统生成，来源旧编码不能作为正式系统编码。

未在资料中确认的企业、税务、地址、银行、资质及合作等级字段仍为 GATED：不得自行添加，也不得由样例推断 nullable 或 UNIQUE 规则。Supplier Migration 尚未授权；本冻结只解除字段设计门禁。

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
