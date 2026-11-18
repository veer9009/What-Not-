# Controlled beta authentication verification — 2026-11-18

## Scope and root causes

No AWS/EC2 connection, live HTTP probe, deployment, service restart,
infrastructure modification, production database access, commit or push occurred.

The supplied fresh-settings failure is a configuration blocker. Production
requires a nonempty approved-email JSON allowlist and abuse protection. Current
code already normalizes emails and enforces admission on registration, login,
refresh and authenticated requests; no backend admission bypass was added.

The supplied running-process/file timestamps support stale runtime code/config
as a hypothesis, but do not establish its exact effective settings. In this
checkout, the supplied explicit 403 requires a nonempty list excluding the
submitted email; an empty production list instead prevents startup. The supplied
live refresh 404 is inconsistent with the current implemented route. Deployed
version/routing compatibility remains a manual verification requirement.

The reproduced code defect was loss of the beta-specific explanation in the
frontend. The minimal client fix maps only the known public auth denial to safe,
actionable guidance. All other server details remain sanitized.

## Files changed

| Path | Purpose |
| --- | --- |
| `src/api/client.ts` | Explain the known auth admission denial without exposing arbitrary server text. |
| `src/api/client.test.ts` | Four regression cases for beta denial plus unrelated permission-error handling. |
| `backend/tests/test_beta_auth_configuration.py` | Ten synthetic configuration cases: JSON, dotenv/process precedence, normalization, missing/empty/invalid allowlist and abuse enforcement. |
| `backend/tests/persistence/test_beta_authentication.py` | Ten real PostgreSQL/HTTP admission, login, roles, refresh, logout and expiry cases. |
| `backend/.env.example` | Placeholder allowlist syntax, normalization and process-lifetime guidance. |
| `backend/.env.production.example` | Placeholder syntax and distinction from ten-identity admin bootstrap requirements. |
| `docs/BETA_AUTHENTICATION.md` | Complete auth trace, evidence boundaries and exact private manual configuration/release instructions. |
| `docs/BETA_AUTHENTICATION_RESULTS.md` | This report. |
| `docs/superpowers/plans/2026-11-18-beta-authentication.md` | Scope and test-first implementation plan. |

## Verification

Backend commands below ran from `backend`; frontend commands ran from repository
root. Output logs are ignored local artifacts, not committed files. Counts from
overlapping runs must not be added together.

| Command | Outcome | Local log |
| --- | --- | --- |
| `.venv/Scripts/python.exe -m pytest --ignore=tests/persistence --ignore=tests/session_integration -q` (baseline) | 425 passed | `auth-beta-backend-unit.log` |
| `node node_modules/vitest/vitest.mjs run src/api/client.test.ts --maxWorkers=1` (before fix) | 4 failed, 17 passed; expected beta-message failures | `auth-beta-message-red.log` |
| Same client command after fix | 21 passed | `auth-beta-message-green.log` |
| `.venv/Scripts/python.exe -m pytest tests/test_beta_auth_configuration.py -q` | 10 passed | `auth-beta-settings.log` |
| `.venv/Scripts/python.exe -m pytest tests/test_beta_auth_configuration.py tests/test_beta_settings.py tests/test_auth_security.py tests/test_auth_schemas.py tests/test_refresh_sessions.py -q` | 65 passed | `auth-beta-focused-backend.log` |
| `.venv/Scripts/python.exe persistence_schema_runner.py -k 'admitted_registration_login_refresh_roles_and_logout or unapproved_registration_creates_no_account or removed_admission_blocks_existing_login_access_and_refresh or admitted_duplicate_and_wrong_password or invalid_access_tokens_are_rejected or absolute_session_expiry_blocks_refresh'` | 10 passed, 451 deselected | `auth-beta-new-integration.log` |
| `.venv/Scripts/python.exe -m pytest tests/persistence/test_authentication.py -q` | 5 passed, 24 setup errors (Windows launcher) | `auth-beta-postgres-baseline.log` |
| `.venv/Scripts/python.exe -m pytest -q` | 496 passed, 421 setup errors (Windows launcher) | `auth-beta-backend-full.log` |
| `.venv/Scripts/python.exe persistence_schema_runner.py` | 461 passed | `auth-beta-persistence.log` |
| `.venv/Scripts/python.exe -m pytest --ignore=tests/persistence --ignore=tests/session_integration -q` (final) | 435 passed | `auth-beta-backend-unit-final.log` |
| `.venv/Scripts/python.exe -m pytest tests/session_integration -q` | 21 passed | `auth-beta-session-integration.log` |
| `node node_modules/vitest/vitest.mjs run src/api/client.test.ts src/api/refresh.test.ts src/state/AuthContext.test.tsx src/state/SessionLifecycle.test.tsx --maxWorkers=1 --testTimeout=15000` | 43 passed, 4 files | `auth-beta-frontend-focused.log` |
| `node node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --testTimeout=15000 --reporter=verbose` | 402 passed, 44 files, exit 0; 507.95 seconds | `auth-beta-frontend-serial.log` |
| `node node_modules/typescript/bin/tsc -b` | Exit 0 | `auth-beta-typecheck.log` |
| `npm.cmd run build` | Exit 0; 1,947 modules transformed | `auth-beta-build.log` |
| `git diff --check` | Exit 0; only Git LF/CRLF conversion notices | Terminal output |

The standard PostgreSQL launcher failed with `pg_ctl: could not create restricted
token: error code 87`; all 421 errors were fixture setup, not failed assertions.
The fallback runner verifies the designated loopback test DB name, OID, address,
ownership and empty application tables before writing only generated schemas.
It verifies the public schema snapshot at cleanup. Production and application
records were not modified. All 461 persistence tests passed through that harness.
The final unit (435), persistence (461), and session integration (21) partitions
cover all 917 collected backend cases with passing evidence, although the default
combined command itself remains unsuccessful due to the launcher errors.

The first full frontend command (`node node_modules/vitest/vitest.mjs run
--maxWorkers=1`) was stopped after it ceased reporting progress. It reported nine
failures before stopping, with no final total:

- `src/App.test.tsx`: `does not promote admin sign-in on the public homepage`;
  `reports registration rejection 422`.
- `src/LocationDiscovery.test.tsx`: `refreshes synthetic supported/unsupported/supported points without retaining old cards`;
  `associates PIN guidance and styles the clear action as a secondary button`;
  `requires an explicit source, uses backend list/detail and adds real products to the cart`;
  `does not silently select a default address`.
- `src/pages/AdminWorkspace.test.tsx`: `preserves service pagination offsets and refresh requests`.
- `src/pages/AddressLocation.test.tsx`: `detects only on click, keeps postal fields editable and saves GPS only after explicit save`.
- `src/pages/AdminOperations.test.tsx`: `requires an investigation reason and sends only authorized account action fields`.

A second frontend run (`node node_modules/vitest/vitest.mjs run --maxWorkers=1
--pool=forks --testTimeout=15000`, `auth-beta-frontend-final.log`) was stopped
because worker turnover remained slow; it had not emitted any failures or final
total. Neither incomplete frontend run is counted as a passing suite. The final
run uses one thread worker and verbose reporting; its result is recorded below.
A two-thread diagnostic run (`--pool=threads --maxWorkers=2 --testTimeout=15000
--reporter=verbose`, `auth-beta-frontend-threads.log`) was also stopped: it reported
`src/Marketplace.test.tsx > creates a product without moderation/actor fields or
fake geography` failing to find `Description`, with a sign-in page rendered.
Concurrent auth tests and Node's cross-thread BroadcastChannel are a
possible source of test interference; this is not claimed as a proven product bug.
The final serial thread run completed successfully: all 402 tests passed across
44 files. Every initially reported failing case passed in that full run. No
frontend product failure remains reproduced by the final suite; the earlier
failures and interrupted runs are retained above for transparency.

## Security and readiness

Production admission remains fail-closed and case-insensitive; abuse quotas,
Argon2id/password preservation, JWT expiry, cookie security, CSRF, session
rotation/revocation and backend/frontend RBAC remain intact. Bootstrap safeguards
are unchanged. No credentials or tester identities were added to repository source
files; test/example identities are synthetic placeholders.

No current-checkout frontend/backend auth endpoint incompatibility was found.
The reported live 404 remains a deployment/routing verification item. Review
`BETA_AUTHENTICATION.md` for private JSON configuration, environment precedence,
same-origin HTTPS, schema `0010`, and coordinated release requirements. A live
fix requires a separately authorized deployment and verification.

The patch and configuration instructions are ready for manual review. TypeScript,
production build, the full serial frontend suite and all backend partitions have
passing evidence. This is not an unconditional production release sign-off:
correct the private approved allowlist and stale environment overrides, verify
the actual release/schema/API routing together, then obtain separate deployment
authorization and perform browser/live acceptance checks. No claim is made that
the live website is fixed.
