# Change Record: Auth Login / Register Tabs

Change ID: 2026-09-14-022
Module: auth-rbac / web-admin
Date: 2026-09-14
Branch: feat/auth-login-register-tabs

## Goal

Combine the login and registration entry into one enterprise-style authentication card with
left/right tab switching, without changing authentication or registration approval rules.

## Delivered

- `/login` and `/register` render the same authentication page and select the matching tab.
- Login and registration keep independent form state, validation and submission loading state.
- Registration continues to call the real registration API and shows the pending-approval result.
- Authenticated users are redirected away from both anonymous authentication routes.
- The obsolete standalone registration view was removed.
- The authentication panel uses a stable top anchor so switching to the taller registration form
  does not move the login/register tabs.

## Verification

- `npm run typecheck` — PASS.
- `npm test -- --run` — PASS (42 tests).
- `npm run build` — PASS; the existing Vite chunk-size warning remains unchanged.

## Boundaries

- No backend API, database schema, permission or approval lifecycle changes.
- No default account, password or mock registration behavior was added.
