# Secure refresh-session continuation handoff

Implementation resumed from the existing dirty working tree. Existing GPS, cart,
discovery, upload, navigation, moderation and authorization changes were preserved.
No environment files, application records, application migrations, deployment,
commits or pushes are authorized by this handoff.

## Confirmed timezone defect

The pre-fix regression failed in `set_refresh_cookie` → Starlette `set_cookie` →
Python `email.utils.format_datetime(..., usegmt=True)` with
`ValueError: usegmt option requires a UTC datetime`. PostgreSQL TIMESTAMPTZ values
retain the same instant but arrive with the connection's timezone offset; Python's
HTTP date formatter requires UTC specifically.

`set_refresh_cookie` now normalizes aware expiry values with
`expires_at.astimezone(timezone.utc)` before arithmetic and cookie serialization.
Naive datetimes are explicitly rejected as ambiguous; no timezone is guessed.
No global database timezone was changed. Unit tests check the exact GMT instant and
naive rejection. Real integration connections use local `Asia/Kolkata`, assert the
loaded +05:30 offset, and verify refresh serializes the identical instant in GMT.

## Session architecture

- Access JWT: 15 minutes, memory-only frontend storage, identity and `sid` claims;
  existing `access_token`, `token_type`, `expires_in`, `user` response contract.
- Database session family: absolute eight-hour BUYER/SELLER lifetime and absolute
  15-minute ADMIN lifetime. Renewal never extends that deadline.
- Refresh credentials: cryptographically random opaque 256-bit tokens; only SHA-256
  digests and use history stored server-side. Each successful refresh rotates.
- Refresh locking: user → session → token. Reuse of a used token revokes the family;
  concurrent use of the same old token yields one rotation and replay revocation.
  Returning a rejection response commits revocation rather than rolling it back.
- Cookie: `wn_refresh`, HttpOnly, Secure, SameSite Strict, host-only, auth path
  `/api/v1/auth`, absolute expiry and remaining max-age. Never exposed in JSON.
- CSRF: login/refresh/logout require exact approved or same Origin plus
  `X-WhatNot-CSRF: 1`; cross-site Fetch Metadata is rejected. Credentialed CORS uses
  explicit origins. Cookie alone cannot authenticate protected Bearer routes.
- Every protected request checks current user activity, current role, session owner,
  absolute expiry and revocation. Role changes invalidate old sessions. Logout
  revokes the family and clears the cookie; legacy JWTs without `sid` are rejected.
- Frontend: reload bootstrap, timer/focus/visibility recovery, shared in-flight
  refresh, serialized cookie operations, Web Locks for concurrent tabs, bounded
  single retry of a protected 401, stale identity/response guards and logout signal.
  Identity changes in another tab fail closed locally. Access/refresh credentials
  are never put in localStorage or broadcast messages.

## Migration and prerequisites

Prepared migration: `backend/alembic/versions/0010_auth_sessions.py`, revision
`0010`, parent `0009`. It creates only `auth_sessions` and `auth_refresh_tokens`.
TIMESTAMPTZ expiry/revocation/use timestamps, primary keys, foreign keys with cascade
deletion and user/expiry/session indexes are included. No user/order data rewrite.

The new application expects revision 0010. Before a separately approved application
upgrade: verify the intended application database is at 0009, back up and test
restoration, ensure the migration role may create tables/indexes/foreign keys,
schedule a controlled application restart, and arrange HTTPS with a same-site API.
Existing JWTs require one new login. Do not run old and new authentication versions
concurrently during rollout.

Downgrade refuses to destroy any session history, even expired/revoked families.
An empty session schema can downgrade to 0009; otherwise a separately reviewed
archive/recovery procedure is required. No automatic history deletion was added.
The actual Alembic 0009 → 0010 → 0009 → head sequence passed in fresh test-only
storage; a history-bearing downgrade rejection also passed.

## Verification evidence

- Original timezone regression: 1 failed before the fix (`refresh-resume-utc-red.log`).
- Initial combined invocation: collection error from duplicate test module names;
  adding the integration package marker resolved it.
- Combined unit/security/offline migration and PostgreSQL session/migration checks:
  37 passed (`refresh-resume-postgres-retry.log`).
- Explicit PostgreSQL offset and actual Alembic current-head round trip: 2 passed
  (`refresh-resume-postgres-additional.log`).
- Seller order action after renewal, confirmed-destination ownership, unrelated
  seller denial and admin denial: 1 passed (`refresh-resume-order-renewal-retry.log`).
  Its first run failed response validation because the synthetic fixture omitted
  order items; adding the required synthetic item fixed the fixture, with no
  production code or authorization changes.
- Backend non-persistence suite: 425 passed (`refresh-resume-unit-final.log`).
- Standard persistence startup: 1 fixture error, zero executed tests, Windows
  `pg_ctl` restricted-token error 87 (`refresh-resume-persistence.log`).
- Frontend full suite: 44 files, 397 tests passed (`.frontend-final-test.log`).
  The original completed full run had 45 failed/345 passed (16 failed/27 passed
  files) and one EBUSY worker error. It exposed stale no-refresh/default-URL test
  contracts and real lifecycle/account-switch defects, all corrected before final
  verification. The second broad run was interrupted and has no final count.
  Earlier parallel attempts encountered five-second worker timeouts and EBUSY under
  host contention; the isolated App attempt recorded 13 failed/16 passed, then
  passed all 29 when rerun without competing workers. Final full verification used
  sequential vmThreads with the normal timeout, not relaxed assertions.
- Production build: TypeScript and Vite passed, 1,947 modules transformed
  (`.frontend-build.log`). Initial builds found test-mock TypeScript typing errors;
  two failed attempts reported nine then six diagnostics. Corrected mock argument
  types and normalized assertion headers with `new Headers`; the final build passed.
- Python compileall passed; pip reported no broken requirements. Alembic reports a
  single head, `0010`.
- Diff whitespace check passed; line-ending conversion advisories are informational.
  Credential-pattern scan found zero matches in changed additions and untracked
  source/docs (`refresh-resume-secret-scan.log`); this is a bounded pattern check.
- Full persistence suite: 449 passed, 2 failed, no deselections, 583.03 seconds
  (`refresh-persistence-expanded-full.log`). Both were historical test compatibility
  issues: 0008 downgrade refusal must be checked before advancing through the
  irreversible 0009 consent migration, and the 0008/0009 storage-compatibility test
  must isolate authentication because those historical schemas predate sessions.
  Test-only corrections retained the original preservation/privacy assertions.
  Each corrected test passed independently: 1 passed/450 deselected in 13.24 seconds
  and 1 passed/450 deselected in 5.88 seconds (`refresh-persistence-beta-final.log`,
  `refresh-persistence-seller-final.log`). All 451 persistence tests have passing
  coverage; the entire suite was not rerun after these two test-only corrections.
- Earlier metadata-only fallback attempt: 424 passed, 2 failed, 25 deselected and
  1 teardown error. Replaced with actual head migrations in guarded schemas;
  corrected missing readiness metadata and stale role-change assertion. No final
  persistence tests were excluded.
- All 21 PostgreSQL session/migration integration cases have passing results across
  the combined run and the three added focused cases; collection inventory is
  `refresh-resume-integration-collection.log`. The combined 37 count includes 19
  unit/offline cases already included in the 425 unit total; do not double-count it.

The fallback verifies localhost, database name/OID/ownership and generated schema
before work, uses only synthetic identities, and verifies the disposable database's
public tables/revision are unchanged. It never connects to the application database.
This host's test identity is intentionally fixed; another machine must explicitly
provision and verify its own disposable target rather than relaxing safety checks.

Reproduction commands (repository root unless stated):

```text
node node_modules/vitest/vitest.mjs run --pool=vmThreads --maxWorkers=1 --reporter=dot
npm run build
git diff --check
backend/.venv/Scripts/python.exe docs/security/check_refresh_diff.py
# From backend:
.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence --ignore=tests/session_integration -q
.venv/Scripts/python.exe persistence_schema_runner.py
.venv/Scripts/python.exe -m pytest tests/test_refresh_sessions.py tests/test_refresh_migration.py tests/session_integration -q
```

The schema runner is explicitly host-specific and refuses an unexpected database.
The normal persistence fixture still creates its own disposable PostgreSQL cluster;
it remains blocked by this host's Windows restricted-token startup issue. Backend
case results, frontend case results and production compilation are verified; real
HTTPS browser checks are still pending. Independent code review found and resolved
the frontend cross-tab identity mismatch and found no further concrete runtime
blocker; the compatibility concerns below remain.

## Remaining browser and operational checks

1. After separately approved migration/deployment to an isolated beta environment,
   open HTTPS in a current browser with Web Locks. Verify the refresh cookie is
   HttpOnly/Secure/SameSite Strict and no credential is in browser storage.
2. Sign in as buyer; reload, open another tab, switch away for 2–3 minutes and
   return. Repeat after 15 minutes. Confirm renewal, current identity, addresses,
   cart and checkout state; verify no unauthorized order or duplicate submission.
3. Repeat as seller; verify product uploads and order actions after renewal. Accept
   an eligible order with buyer-confirmed destination and verify navigation; pending,
   unconfirmed and unrelated seller access must retain their existing restrictions.
4. Switch accounts in another tab. The old tab must clear its old identity rather
   than combine it with the new account's token/private records.
5. Logout and reload both tabs. Protected requests and renewal must fail. With a
   deliberately offline logout, verify the warning: local logout cannot promise
   server revocation until the server receives the request.
6. Verify admin login/RBAC and forced sign-in after 15 minutes; buyer/seller absolute
   eight-hour expiry must also require credentials. Do not shorten or alter real
   customer session records for this check; use synthetic beta accounts.
7. Inspect proxy handling: preserve Origin, cookies, no-store headers and trustworthy
   client IP attribution. Cross-site API hosting is incompatible with Strict cookies.
8. Test supported mobile/desktop browsers. Without Web Locks, fallback locking is
   per-tab only; simultaneous refresh across tabs can intentionally trigger replay
   revocation. This remains a documented compatibility limitation.
9. Capacity-check existing auth source rate limit (default 20 calls/15 minutes),
   shared by login and refresh, especially shared NAT networks and frequent reloads.
   No abuse controls were disabled to pass tests.

Expired token history needs a separately scheduled maintenance policy as usage
grows; retain all replay history for families which can still authenticate. Pattern
scanning and unit/integration checks do not replace real HTTPS browser verification.

## Review boundary

Application migration and controlled browser verification remain required before
deployment readiness can be claimed. Stop here for explicit approval; no application
migration, GitHub push or AWS deployment is performed by this work.
Final inventory: 69 tracked changed files, 176 untracked files, zero staged changes;
this includes preserved earlier work. No working-tree changes were discarded.

## Exact authentication-related files

The complete dirty-tree inventory, including preserved unrelated prior work, is
`docs/security/evidence/refresh-session-git-status.txt`. The session work is in:

Runtime/configuration:

- `backend/app/api/dependencies.py`
- `backend/app/api/routes/auth.py`
- `backend/app/core/security.py`
- `backend/app/db/schema.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/auth_session.py`
- `backend/app/services/refresh_sessions.py`
- `backend/alembic/versions/0010_auth_sessions.py` (revision `0010`, parent `0009`)
- `src/api/auth.ts`
- `src/api/client.ts`
- `src/state/AuthContext.tsx`
- `src/pages/LoginPages.tsx`
- `vite.config.ts`

Backend verification and compatibility fixtures:

- `backend/persistence_schema_runner.py`
- `backend/tests/session_integration/__init__.py`
- `backend/tests/session_integration/conftest.py`
- `backend/tests/session_integration/test_refresh_sessions.py`
- `backend/tests/session_integration/test_migration_execution.py`
- `backend/tests/session_integration/test_refresh_migration_chain.py`
- `backend/tests/test_refresh_sessions.py`
- `backend/tests/test_refresh_migration.py`
- `backend/tests/test_health.py`
- `backend/tests/persistence/conftest.py`
- `backend/tests/persistence/test_auth_transactions.py`
- `backend/tests/persistence/test_authentication.py`
- `backend/tests/persistence/test_authorization.py`
- `backend/tests/persistence/test_dispatch_location.py`
- `backend/tests/persistence/test_beta_resume.py`
- `backend/tests/persistence/test_seller_schema_compatibility.py`

Frontend verification and session-bootstrap fixture compatibility:

- `src/api/refresh.test.ts`
- `src/state/AuthContext.test.tsx`
- `src/state/SessionLifecycle.test.tsx`
- `src/api/productionConfiguration.test.ts`
- `src/App.test.tsx`
- `src/BetaFlows.test.tsx`
- `src/BetaResume.test.tsx`
- `src/BusinessScope.test.tsx`
- `src/Checkout.test.tsx`
- `src/DeliverySupport.test.tsx`
- `src/LocationDiscovery.test.tsx`
- `src/Marketplace.test.tsx`
- `scripts/discovery-layout.test.tsx`
- `scripts/admin-layout.test.tsx`

Documentation/evidence:

- `README.md`
- `backend/AUTHENTICATION.md`
- `docs/FRONTEND_INTEGRATION.md`
- `docs/REFRESH_SESSION_IMPLEMENTATION.md`
- `docs/superpowers/plans/2026-11-16-refresh-sessions.md`
- `docs/security/check_refresh_diff.py`
- `docs/security/evidence/refresh-session-git-status.txt`

Some files above already contained earlier work; the inventory does not imply their
entire diff was introduced during this continuation. No existing changes were reset.
