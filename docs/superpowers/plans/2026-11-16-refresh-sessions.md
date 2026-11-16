# Secure beta refresh sessions

User approved implementation. On continuation, migration execution is authorized only in isolated disposable test storage; never in the development or production database. Work in the existing shared working tree to retain the beta fixes already under review. No `.env`, customer data, deploy, commit or push changes.

## Contract and decisions

- Access JWT 15 minutes. Buyer/seller session absolute eight hours; admin absolute 15 minutes. Current database role/activity and session revocation checked on every protected request.
- Login/refresh return the existing token response; refresh/logout are new auth endpoints. Refresh tokens are random opaque values whose SHA-256 digests/history are stored in separate session/token tables. Rotate under lock, detect reuse and commit revocation before returning rejection.
- `wn_refresh` cookie: HttpOnly, Secure, SameSite Strict, auth-only path. Require explicit approved/same Origin and `X-WhatNot-CSRF: 1` for cookie-changing auth calls. Credentialed CORS stays explicitly allowlisted. Development uses the existing frontend through a same-origin Vite API proxy; production retains `/api/v1` as the preferred API base.
- In-memory access token; fresh page restores via cookie refresh. Single-flight renewal and bounded one-retry handling, cross-tab refresh serialization, no secret-bearing storage/broadcast. Keep mutation idempotency/cancellation rules.
- Migration next revision 0010, previous 0009. Review SQL offline and exercise upgrade/downgrade in rollback-only transactions in an isolated synthetic test schema, never a customer schema.

## Tasks and verification

1. Backend implementer: tests first; models, migration, session rotation/revocation, JWT session binding, secure auth endpoints, dependency/CORS/readiness integration and focused unit verification.
2. Frontend implementer: tests first; bootstrap/timed/focus renewal, one in-flight refresh, cookie transport, logout, stale response guards and role/checkout/upload regression coverage.
3. Coordinator: isolated PostgreSQL harness with identity/schema guards and synthetic fixtures. Verify login/refresh/logout, hash storage/history, replay, expiry, admin ceiling, RBAC, revocation/current identity and concurrency. Review offline upgrade/downgrade SQL without applying it.
4. Run complete frontend/backend unit suites, isolated PostgreSQL tests, production build, diff/security checks, and independent review. Record exact results, changed files and manual browser steps in a final report. Stop for review.

## Execution ledger

- Backend and frontend tasks dispatched separately with the above API/cookie contract.
- Continuation: reproduced non-UTC cookie expiry ValueError, normalized aware datetimes to UTC and rejected naive expiries explicitly. Integration connections use local Asia/Kolkata timezone; no global database settings changed.
- Standard disposable-cluster fixture cannot start on this Windows host (pg_ctl restricted-token error 87). Guarded test-schema runner preserves the designated test database's public schema and verifies identity/ownership before work.
- Verification complete: backend unit 425 passed; all 451 persistence cases have passing coverage (449 in full run, two corrected historical fixtures passed targeted reruns); all 21 dedicated PostgreSQL integration cases passed across focused runs. Frontend 397 tests/44 files passed and production build passed. Diff/secret-pattern checks passed. See `docs/REFRESH_SESSION_IMPLEMENTATION.md` for original failures, exact files, evidence and manual gates.
- Independent review found the frontend cross-tab account mismatch; identity binding and regression tests now reject it before token acceptance. No further concrete runtime blocker found. Web Locks, HTTPS/same-site hosting and auth quota capacity remain documented requirements/risks.
- Stopped for review. No application migrations, environment edits, commits, pushes or deployment performed.
