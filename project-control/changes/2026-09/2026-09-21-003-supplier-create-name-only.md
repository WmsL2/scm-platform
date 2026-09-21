# 2026-09-21-003 Supplier Manual Create Name-Only

## Scope

Align manual Supplier creation with the approved Excel import rule: only `supplier_name` is mandatory. `main_brands`、`advantage` and contacts may be completed later.

## Implementation

- `SupplierCreateRequest` accepts omitted or blank `main_brands` and `advantage` while continuing to reject an omitted or blank `supplier_name`.
- Supplier Service writes omitted optional business text as empty strings to the existing non-null database columns; no Schema change is required.
- Supplier editing also permits these two optional fields to be cleared, so a name-only supplier can be edited without being forced to complete them.
- The Web Admin form validates only the supplier name and labels the two optional business fields explicitly.
- Supplier code generation, name uniqueness, archive/cooperation status, contacts, audit and permissions are unchanged.

## Verification

- Backend schema tests cover name-only create requests and optional-text normalization.
- Supplier API integration coverage creates a supplier using only its name, verifies empty-string persistence, and verifies optional fields can be cleared on edit.
- Frontend unit coverage verifies a name-only draft passes validation.

## Schema / API / UI

- Alembic Revision: none.
- API: `POST /api/v1/suppliers` now requires only `supplier_name`; `main_brands` and `advantage` are optional.
- UI: manual create/edit labels 主营品牌 and 主要优势 as optional and no longer blocks submission when they are empty.
- Permission changes: none.
