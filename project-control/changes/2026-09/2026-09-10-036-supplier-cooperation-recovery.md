# Change Record: Supplier Cooperation Recovery

Change ID: 2026-09-10-036
Module: supplier

## Changes

- Added STOPPED → NORMAL recovery through `supplier:resume` and BLACKLIST → NORMAL
  recovery through `supplier:unblacklist`.
- Every cooperation command requires a reason and preserves forward/reverse
  `SupplierCooperationRecord` audit history; no cooperation status enum changed.
- Revision `20260910_0017` expands the history constraint and safely blocks a
  downgrade when reverse recovery history exists.
- No Product or existing `source_supplier_id` relation changes. ARCHIVED + NORMAL
  suppliers become eligible source-supplier candidates again after recovery.
