# Change Record: Web Admin Data Refresh

Change ID: 2026-09-10-033
Module: web-admin / catalog
Date: 2026-09-10
Branch: fix/web-admin-patch

## Goal

Fix stale data displayed after a successful user action, where a list or detail reload could reuse a browser-cached GET response and require a manual page refresh.

## Change

- Updated the shared Web Admin HTTP client to send every API request with `cache: "no-store"`.
- Existing post-action reloads, including Product Import Confirm → Product list reload, now always request current API data.
- Added an HTTP client unit-test assertion for the no-cache request option.

## Scope

No backend route, database migration, Product/Supplier business rule or Excel-import behavior changed.

## Verification

- `npm test -- --run` — 34 passed.
- `npm run typecheck` — pass.
- `npm run build` — pass.
