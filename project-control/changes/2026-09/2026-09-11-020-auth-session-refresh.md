# Change Record: Auth Session Refresh

Change ID: 2026-09-11-020  
Module: auth-rbac / web-admin  
Date: 2026-09-11  
Branch: feat/auth-session-refresh

## Goal

Replace stateless browser login persistence with a revocable enterprise session: 30-minute Access Token, HttpOnly rotating Refresh Token, three-day inactivity timeout and thirty-day absolute lifetime.

## Backend

- Added `sys_auth_session` through Revision `20260911_0021`, with hashed refresh credentials, rotation counter, activity/expiry timestamps and revocation audit fields.
- Login creates a server-side session and writes the Refresh Token only to a restricted HttpOnly Cookie.
- `POST /api/v1/auth/refresh` locks and validates the session, rotates the Refresh Token and slides only the inactivity deadline.
- Session-bound JWTs include `sid` and `jti`; authorization validates the current user, token version and active session.
- Logout revokes both the signed Bearer session and the Cookie's verified session. Password change and user logical delete revoke every session for that user; disabled/deleted users cannot access or refresh.
- Old Refresh Token replay outside the 30-second multi-tab grace window revokes the session.

## Frontend

- Access Tokens are memory-only; startup removes legacy Web Storage tokens, while page reload and browser restart restore an eligible session from the HttpOnly Cookie.
- Every API request includes credentials. A protected 401 shares one refresh attempt across concurrent requests and retries each original request no more than once.
- Refresh failure emits the existing unauthorized flow, clears local auth state and returns the user to Login.
- Mock auth mirrors login/refresh/logout session availability for local UI development.

## Configuration

- `AUTH_ACCESS_TOKEN_MINUTES=30`
- `AUTH_REFRESH_IDLE_DAYS=3`
- `AUTH_SESSION_ABSOLUTE_DAYS=30`
- `AUTH_REFRESH_ROTATION_GRACE_SECONDS=30`
- `AUTH_REFRESH_COOKIE_SECURE` may override environment-derived HTTPS Cookie behavior.

## Verification

- Backend Ruff and mypy: PASS; full pytest: PASS (127 tests).
- Auth/account/schema targeted pytest: PASS (37 tests).
- Frontend Vitest: PASS (42 tests); typecheck and production build: PASS.
- Alembic downgrade `0021 -> 0020`, upgrade to head, `current`/`heads`: PASS.
