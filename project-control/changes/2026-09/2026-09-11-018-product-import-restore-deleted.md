# Change Record: Restore Deleted Product During Import Confirm

Change ID: 2026-09-11-018  
Module: catalog  
Date: 2026-09-11  
Branch: feat/product-import-restore-deleted

## Goal

Allow a fixed Product Master Excel import to restore an existing logically deleted Product with the same source supplier and SKU, without creating a duplicate or overwriting the original Product fields.

## Delivered

- Preview distinguishes an active duplicate (error) from a logically deleted duplicate (restore warning).
- Confirm locks matching Products and restores only logically deleted matches by clearing delete state and updating the current actor.
- Confirm response and Product List feedback separately report imported and restored counts.
- ADR-0014 and Product Import documentation freeze the narrow restore boundary.

## Verification

- Catalog import API regression covers active-duplicate rejection, preview warning, confirm restore, cleared deletion audit fields and preserved Product fields.
- Frontend typecheck/build and API tests cover the added confirm response field.

## Boundaries

- This does not add a generic restore endpoint, a restore permission, a new Migration or deleted-SKU reuse.
- Restoring through Confirm never overwrites existing Product values with Excel row values.
