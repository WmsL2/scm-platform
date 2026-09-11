# Change Record: Supplier Archive Status Selection

Change ID: 2026-09-11-016  
Module: supplier  
Date: 2026-09-11  
Branch: feat/supplier-initial-archive-status

## Goal

Allow the operator to choose a supplier's archive status at creation, Excel import confirmation and later editing instead of forcing a single status.

## Delivered

- Supplier create request now accepts `archive_status`, defaulting to `DRAFT`.
- Supplier Excel preview no longer auto-confirms a valid file. The dialog lets the uploader choose the batch's initial archive status and explicitly confirm; API callers that omit a body retain the prior `ARCHIVED` default.
- Supplier edit now accepts `archive_status`; `supplier_code` and `cooperation_status` remain protected from generic editing.
- The backend writes archive actor/time only for `ARCHIVED` and clears them for `DRAFT` or `PENDING`, including logical-deleted supplier recovery.
- ADR-0012 and Supplier documentation record the updated rule. No database schema change or new permission is required.

## Verification

- Backend schema/API tests cover create, edit and Excel confirm status selection, default compatibility and archive audit fields.
- Frontend API/type tests, typecheck and production build are run for the status selector flow.

## Boundaries

- Excel import cooperation status remains `NORMAL`.
- Product source-supplier eligibility remains `ARCHIVED + NORMAL + not deleted`; selecting another archive status does not make a supplier eligible for Product Import.
