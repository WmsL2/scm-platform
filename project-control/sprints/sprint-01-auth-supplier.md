# Sprint 01: Auth/RBAC + Supplier

Status: IN_PROGRESS.

- Auth Kernel: DONE via PR #6 (Merge Commit `6f229e75`); Revision `20260903_0002`.
- Web Admin Auth: DONE / REAL API VERIFIED.
- Business Sequence: DONE / IMPLEMENTED; Revision `20260907_0003`, available for Supplier Master `supplier_code` generation.
- Supplier Field Dictionary: FROZEN / READY FOR SCHEMA DESIGN.
- Supplier Master Backend: IMPLEMENTED on `feat/supplier-master-backend`; Revision `20260907_0004` adds the frozen Supplier schema, permission directory, API, lifecycle and tests. It is not a `main` fact until merged.
- Supplier Master Frontend: NEXT — integrate the frozen Supplier API without adding unconfirmed fields.
- PENDING: Refresh Token policy is future Auth scope and does not block Supplier / Product development. Enterprise, tax, address, banking and qualification fields not confirmed by supplier source material remain locally GATED and must not be invented.
