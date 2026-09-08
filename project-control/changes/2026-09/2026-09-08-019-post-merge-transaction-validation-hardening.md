# Change Record: Post-Merge Transaction and Validation Hardening

Change ID: 2026-09-08-019
Module: auth-rbac / supplier
Date: 2026-09-08
Branch: fix/post-merge-hardening

## Goal

Resolve three post-merge P1 defects without changing business scope or database schema: duplicate Account association IDs could cause composite-primary-key failures, Service transaction ownership could end a caller transaction, and invalid Supplier UUID path values could reach ORM binding as strings.

## Changes

- Account whole-set role and permission replacement now de-duplicates IDs in input order before validation, persistence and response construction. Repeated IDs are idempotent; `[]` still clears all associations.
- HTTP database dependency now owns a request-scoped transaction. AccountService, SupplierService and SupplierImportService share `transaction_scope()`: they participate in an existing caller transaction and own a transaction only for a fresh Session.
- Registration keeps its username precheck and uses a nested transaction / SAVEPOINT for INSERT+flush unique-conflict recovery. The active-username constraint remains the concurrency authority and conflicts map to `ACCOUNT_USERNAME_EXISTS` without rolling back the outer transaction.
- Supplier `supplier_id` and import `batch_id` router parameters are `uuid.UUID`; corresponding Service and Repository boundaries accept UUID values directly.

## Regression Coverage

- Duplicate user-role and role-permission replacement requests return one persisted relation and no 500.
- Account, Supplier and SupplierImport writes are rolled back when their caller rolls back an outer transaction.
- Concurrent username registration remains one created account and one deterministic conflict; the SAVEPOINT conflict path leaves its outer transaction usable.
- All Supplier UUID path routes, including import confirm, return `422` / `VALIDATION_ERROR` for invalid UUID input.

## Database / Alembic

No migration was created or modified. Alembic remains the single head `20260908_0006`.

## Decision

ADR-0007 freezes request transaction ownership and Service participation rules.
