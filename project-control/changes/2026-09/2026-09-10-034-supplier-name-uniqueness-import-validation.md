# Change Record: Supplier Name Uniqueness and Import Validation

Change ID: 2026-09-10-034
Module: supplier
Date: 2026-09-10
Branch: fix/supplier-import-duplicate-validation

## Goal

Enforce the business rule that a supplier name has one retained database record, make duplicate feedback actionable during creation and Excel upload, and reduce a valid Excel upload to one user action.

## Database

- Revision `20260910_0016` adds global UNIQUE constraint `uq_scm_supplier_supplier_name`.
- Existing local duplicates were reviewed before cleanup. For each duplicate name, the earliest record was retained as the historical logical-delete record; four later duplicate supplier rows and their two unreferenced contact rows were physically deleted. No candidate was linked to Product or Product Import supplier matching.
- The retained logical-delete record intentionally still occupies its supplier name. It is the single auditable row to restore when the same supplier is created or imported again.

## Behavior

- An active supplier with the same name returns `409 SUPPLIER_NAME_EXISTS` and message `该供应商已存在` on create or rename.
- Creating a logically deleted supplier name restores the retained row, keeps its original `supplier_code`, clears deletion metadata, resets it to `DRAFT + NORMAL`, and overwrites editable supplier/contact data.
- Import preview rejects every row that conflicts with an active supplier and identifies later same-name rows in the Excel file with their original Excel row number.
- A valid import is confirmed immediately by the Web Admin after preview validation. A logically deleted name in a valid import restores and overwrites its retained row as `ARCHIVED + NORMAL`.

## Verification

- MySQL schema test verifies the new unique index.
- Supplier API tests cover active-name rejection, deleted-record recovery, Excel/database duplicate feedback, and import recovery.

## Import Confirmation Integrity Fix

- The confirm workflow now locks and reads persisted `scm_supplier_import_row` records explicitly rather than treating an ORM relationship collection as its work list.
- It verifies row counts against the batch header, flushes every Supplier write before changing the batch status, and reports the actual processed count.
- Any row-count mismatch or database write failure leaves the batch unconfirmed and rolls back the entire operation. Existing historical `CONFIRMED` batches are not replayed automatically because their intended final data cannot be inferred safely.

## Exclusions

- This does not add supplier fields, physical-delete API behavior, qualification fields, phone validation, or Product/Supplier Matching changes.
