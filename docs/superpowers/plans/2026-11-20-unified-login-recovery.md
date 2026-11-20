# Unified login and secure email recovery

**Goal:** Unified public login and real email-OTP password recovery in the existing session architecture.

**Architecture:** Keep the current server-verified single-role identity and separate admin route. Add persistent recovery state with keyed OTP hashes, opaque single-use reset credentials, bounded verification/resend quotas, and transactional revocation of every existing session after reset. Reuse SMTP with a fake adapter for tests; no new authentication provider. Public pages use real forms and in-memory-only recovery credentials.

**User decision:** Preserve single-role authorization. Multi-role accounts/switching remain unsupported; do not add grants or infer roles from URLs.

## Tasks

- [x] Inspect sessions, mail, transaction boundaries, existing role constraints and local configuration without exposing secrets.
- [x] Add backward-compatible recovery migration, schemas, service/routes, safe mail integration and security tests.
- [x] Replace role picker with direct login; retain legacy login entry points, simplify art/remove map, add recovery UI and accessible links.
- [x] Integrate CSRF-safe client requests and local credential clearing after reset; verify role isolation.
- [x] Run backend/frontend suites, TypeScript/build, recovery/session tests, migration tests, and live responsive checks.
- [x] Review the complete change and document configuration, migration and live-delivery limitations. No commit, push, merge or deployment.

## Interfaces

- `POST /auth/password-recovery/request {email}` returns generic `{message,challenge,resend_after}` for eligible/unknown accounts.
- `POST /auth/password-recovery/verify {challenge,otp}` returns `{reset_token}` only on valid unexpired OTP.
- `POST /auth/password-recovery/reset {reset_token,password}` replaces password and revokes sessions atomically.
- All recovery routes require the existing same-origin CSRF boundary and no-store responses. Opaque challenge field must not be named `*_id`: the shared frontend parser correctly reserves those fields for numeric marketplace identities.

## Security review focus

Concurrency/replay; attempts and cooldown durable across rollback; HMAC domain separation and password binding; unknown/inactive/not-admitted account equivalence; no plaintext secrets in database/logs/URLs/storage; reset/login/refresh lock order; disabled mail/key fail-closed; safe test database isolation; unchanged product/order/payment/discovery logic.

## Files changed for this task

Existing uncommitted homepage, marketplace typography and dashboard presentation changes predate this task and were preserved. This task changes these exact source/test/documentation files:

- `src/App.tsx`, `src/App.test.tsx`
- `src/pages/LoginPages.tsx`, `src/pages/LoginPresentation.test.tsx`
- `src/pages/PasswordRecoveryPage.tsx`, `src/pages/PasswordRecoveryPage.test.tsx`
- `src/components/LoginDiscoveryPanel.tsx`
- `src/styles/login-discovery.css`, `src/styles/password-recovery.css`
- `src/api/auth.ts`, `src/api/client.ts`, `src/api/passwordRecovery.test.ts`
- `src/assets/login/README.md`; removed `src/assets/login/india-outline.svg`
- `scripts/sage-layout.test.tsx`, `scripts/verify_sage_layout.mjs` (remove obsolete role-picker export/check)
- `scripts/verify_auth_layout.mjs` (live-browser presentation verification)
- `backend/app/api/routes/auth.py`, `backend/app/core/config.py`
- `backend/app/db/schema.py`, `backend/app/models/__init__.py`
- `backend/app/models/auth_recovery.py`, `backend/app/schemas/auth_recovery.py`, `backend/app/services/auth_recovery.py`
- `backend/alembic/versions/0011_password_recovery.py`
- `backend/tests/test_password_recovery.py`, `backend/tests/test_recovery_migration.py`
- `backend/tests/session_integration/test_password_recovery.py`, `backend/tests/session_integration/test_refresh_migration_chain.py`
- `backend/tests/test_api_contracts.py`, `backend/tests/test_admin_bootstrap.py`, `backend/tests/test_public_discovery.py`, `backend/tests/persistence/test_beta_resume.py` (new public endpoints/current schema expectations)
- `backend/AUTHENTICATION.md`
- This plan/verification record.

Generated local browser evidence: `docs/security/evidence/unified-auth/` contains `/login`, legacy buyer/seller and recovery screenshots at 390, 768 and 1440px, plus machine-readable results. The evidence directory follows the repository's existing ignore rules.

## Operational requirements and limits

Apply additive migration **0011** through the existing operator migration procedure before running this backend build. It was exercised only in guarded disposable test schemas; no application database migration was performed.

Live recovery requires `WHAT_NOT_PASSWORD_RECOVERY_KEY` (secure random secret, at least 32 bytes; separate from JWT key) and the existing SMTP provider configuration. Local configuration has email delivery disabled and SMTP host/sender/credentials unset. No real email was sent or live delivery claimed. Tests use the fake adapter.

SMTP delivery executes after database commit in an in-process background task. It is not a durable queue: process termination can lose delivery, requiring a new request after cooldown. Recovery state remains server-side and unusable without the emailed code.

Multi-role accounts and switching remain unsupported by explicit user decision. Buyer, seller and administrator roles remain server-managed single-role identities. Browser screenshots show the existing API-unavailable notice because a working live backend roundtrip was unavailable; isolated backend/API and frontend integration tests supply functional verification. External web fonts were unavailable in headless Chrome, so screenshots use fallback fonts. Automated geometry checks and visual inspection do not replace a manual assistive-technology audit.

Security implementation was cross-checked against the [OWASP Forgot Password guidance](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) and independently reviewed for backend security and UI integration. No critical or important issues were found in that review. No commit, push, merge or deployment was performed.

## Verification results

- Backend: `.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence -q --tb=short` — **475 passed**, fresh final run in 88.43s. Includes unit, API and real PostgreSQL authentication/recovery/concurrency tests. An earlier run exposed two stale test expectations for schema head/public endpoints; these were corrected before the final run.
- Persistence: `.venv/Scripts/python.exe persistence_schema_runner.py -q --tb=short` — **461 passed**, exit 0, using the guarded disposable-schema harness. Collection independently confirmed 461 cases. Migration upgrade/head and empty downgrade checks passed. No application schema was changed.
- Frontend: `node node_modules/vitest/vitest.mjs run --config vite.config.ts --pool=threads --maxWorkers=2 --testTimeout=15000` — **427 passed, 3 failed** on the full run (430 total). One obsolete layout fixture still imported the removed role-selection component; it was updated. Two existing seller/admin tests hit asynchronous lookup timing failures under machine load. The three affected files were rerun with `--maxWorkers=1`: **36 passed**, including every failed case. Thus all **430 distinct frontend tests** passed across the full run and targeted rerun; a second full-suite run was not performed. No unrelated workflow implementation was changed to address timing failures.
- TypeScript: `node node_modules/typescript/bin/tsc -b` — exit 0.
- Production: `node node_modules/vite/bin/vite.js build --config vite.config.ts` — exit 0; final build 9.44s, JavaScript 138.27kB gzip. No new runtime dependencies.
- Browser: `node scripts/verify_auth_layout.mjs` — exit 0. All **12** initial-form layouts (`/login`, `/login/buyer`, `/login/seller`, `/forgot-password` × 390/768/1440px) passed containment, overflow, loaded assets, image aspect ratio, split/mobile presentation, navigation destinations, map absence and zero GPS calls. Reduced-motion, empty recovery validation and separate admin presentation passed. Later recovery steps are covered by frontend integration tests; live SMTP/API recovery was not exercised in the browser.
- Visual inspection confirmed readable headings/form text, retained City/Town/Village scenes, an undistorted neighborhood, and prominent mobile fields. Artwork entrance uses movement only to avoid headless Chromium's opacity/blending compositing artifact. Security and beta notices remain visible.
- `git diff --check` — exit 0. Existing Windows line-ending notices are informational.
