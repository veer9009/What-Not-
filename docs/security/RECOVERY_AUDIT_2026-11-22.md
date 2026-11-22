# Recovery and authentication artwork review — 22 November 2026

Branch: `ui/sage-premium-redesign`; starting HEAD: `c7068e9`.
The existing untracked `codex-auth-review.txt` was left untouched.

## Scope and findings

The interrupted implementation already contains user-row locking for request,
verification and reset; replacement issuance retires both older OTPs and verified
reset proofs in the same transaction. Cooldown/quota suppression leaves the useful
credential intact. Existing regression tests exercise concurrent issuance and
verification, one-winner reset, and reset racing with login/refresh. These controls
were retained, not reimplemented.

OTP generation uses `secrets.randbelow(1000000)` formatted as six digits, keyed
HMAC-SHA256 bound to the opaque challenge, five-minute expiry, and five committed
verification attempts. Reset proofs use 32 random bytes, keyed digests and a
five-minute lifetime. Reset updates the password and revokes every session family
atomically; access and refresh authentication check those families. Added tests
check a leading-zero OTP, exact lifetime and digest, plus HMAC algorithm, key
sensitivity and purpose separation. Existing CSRF, generic response shapes,
eligibility checks, password binding and role authorization remain intact.

**New defect fixed:** migration 0011's downgrade emptiness check could race with a
concurrent issuer. A row inserted after the check could be dropped with its table.
Downgrade now acquires ACCESS EXCLUSIVE before checking, held through DROP in the
normal Alembic PostgreSQL transaction. The offline regression failed before the
fix and passes after it. An offline revision traversal verifies the single
continuous `0001` → `0011` chain. No schema upgrade or downgrade is authorized by
this review. Runtime PostgreSQL migration/rollback execution remains unverified.

## Delivery and deployment blockers

Live recovery remains deliberately unavailable (503), including when SMTP is
configured. Only the injected fake adapter in the test environment is allowed.
An in-process post-commit task loses mail across restarts, has no persistent retry,
and can deliver superseded messages late. Supersession makes those codes unusable
but cannot provide reliable delivery. SMTP Message-ID is not an exactly-once
guarantee. Existing plaintext notification outbox fields must not store OTPs.

Before enabling recovery, approve and implement encrypted short-lived delivery
payloads in the existing PostgreSQL/worker infrastructure, with a separate managed
encryption key, transactional enqueue, leases, bounded retries, expiry and
supersession checks, payload erasure, restart tests and supervised workers. Define
rotation and the SMTP send/ack duplicate window. No new queue infrastructure is
needed solely for this workflow. See `backend/AUTHENTICATION.md` for the operational
decision and backup/rollback procedure.

Repository deployment templates bind Uvicorn to loopback, trust only 127.0.0.1,
and have Nginx overwrite X-Forwarded-For with `$remote_addr`. Application quotas use
`request.client.host`, not arbitrary forwarding headers. In-memory proxy tests
exercise spoofing, distinct trusted clients and missing headers. Actual deployed
proxy settings, network exposure and any additional upstream proxy remain manual
checks; templates do not prove the deployed configuration.

## Original artwork

The original already restored in HEAD is `src/assets/homepage/neighborhood-world.jpg`
with the 480/768/976 WebP variants. `src/assets/login/README.md` and the existing
`.superpowers/create-neighborhood-art.mjs` record the user-provided source
`What Not_ Local Possibilities Marketplace.png` and crop (696,84,976,596).
Visual inspection of both source and existing JPEG confirms the same shop, house,
toolbox, green pin and glowing circular base. No export/generation script was run
and no image bytes were changed. The generated `discovery-neighborhood.*`
replacement remains unused.

`LoginDiscoveryPanel` already shares this original across unified login, legacy
buyer/seller entry points, registration, seller registration and every recovery
step. City/Town/Village, Sage Green/White, seller defaults, Become a Seller and
separate administrator login are preserved. Mobile keeps the existing hidden
decorative panel. No India map, geographic outline or political boundary was added;
the rendered desktop scene was visually inspected.

The browser harness now checks the declared image URL when a hidden lazy-loaded
image has no `currentSrc`; previously the first mobile case falsely failed the
asset identity check. Browser recovery responses are synthetic. Screenshots do
not prove live SMTP/API behavior; fonts can use system fallback, and an unavailable
backend notice can be visible on public login.

## Verification

Commands below run from the repository root except Python commands, which run
from `backend/`. Counts are per invocation and overlap; do not add them together.
All completed successful runs below have zero failures and zero skips.

| Exact command | Result |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/test_password_recovery.py tests/test_recovery_migration.py tests/test_recovery_proxy_boundary.py -q --tb=short` | 22 passed; includes 13 recovery unit, 3 offline migration, 6 proxy cases |
| `.venv/Scripts/python.exe -m pytest tests/test_password_recovery.py tests/test_recovery_migration.py tests/test_recovery_proxy_boundary.py tests/test_auth_security.py tests/test_auth_schemas.py tests/test_beta_auth_configuration.py tests/session_integration/test_password_recovery.py -v --tb=short` | 78 passed in 150.66s; before the additional generation/lifetime integration test |
| `.venv/Scripts/python.exe -m pytest tests/session_integration/test_password_recovery.py tests/session_integration/test_refresh_sessions.py -q --tb=short` | Final: 36 passed in 134.62s; 17 recovery and 19 session/role/ownership cases |
| `node node_modules/vitest/vitest.mjs run src/pages/LoginPresentation.test.tsx src/pages/PasswordRecoveryPage.test.tsx src/api/passwordRecovery.test.ts src/state/AuthContext.test.tsx src/state/SessionLifecycle.test.tsx src/App.test.tsx --pool=threads --maxWorkers=1 --testTimeout=15000 --reporter=verbose` | 70 passed, 6 files, 173.81s |
| `node node_modules/vitest/vitest.mjs run src/Checkout.test.tsx src/pages/SellerProfileLocation.test.tsx --pool=threads --maxWorkers=1 --testTimeout=15000 --reporter=verbose` | 36 passed, 2 files, 81.62s; rerun of files that failed in the interrupted broad run |
| `node node_modules/vitest/vitest.mjs run src/api/passwordRecovery.test.ts --pool=threads --maxWorkers=1 --testTimeout=15000 --reporter=verbose` | Diagnostic: 5 passed, 1 file |
| `node node_modules/typescript/bin/tsc -b` | Exit 0 |
| `node node_modules/vite/bin/vite.js build --config vite.config.ts` | Exit 0; 1961 modules, 10.05s. Earlier `npm.cmd run build` also emitted successful TypeScript/build output; direct commands provide unambiguous exits. |
| `node scripts/verify_auth_layout.mjs` | Final exit 0; 27/27 cases: six initial routes × three widths, plus three later recovery steps × three widths; reduced motion, validation and separate admin also pass |
| `git diff --check` | Exit 0; only Windows LF/CRLF conversion notices |

The browser server command was `npm.cmd run dev -- --host 127.0.0.1`.
Evidence widths: 390, 768, 1440 pixels. No real backend recovery call or email was
used. Desktop art was visually inspected; source and crop were also inspected.

### Failures, interruptions and exclusions

- Regression RED: `.venv/Scripts/python.exe -m pytest tests/test_recovery_migration.py -q --tb=short`
  initially produced 1 failed, 2 passed (missing downgrade lock). The final
  22-test run includes all three passing migration tests.
- The first session run used the final 36-test command with `-v` instead of `-q`:
  **35 passed, 1 failed**, 377.72s. The refresh/reset race failed on PostgreSQL's
  fixture `lock_timeout=5000`, while waiting for the user lock. The same case
  passed in the earlier 78-test run and the final 36-test rerun after stopping
  broad competing runs. No production/test lock-timeout setting was changed.
  Treat this as a recorded intermittent failure; successful retries alone do not
  establish behavior under production load.
- Broad frontend command `node node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=2 --testTimeout=15000`
  was interrupted after two files reported **34 passed, 2 failed**. Failures:
  `Checkout.test.tsx` — `offers the existing address manager when the buyer has no saved addresses`;
  `SellerProfileLocation.test.tsx` — `rejects invalid device point 91, 0`.
  Both files pass all 36 cases on the serial rerun above without code changes.
  This is **not** a completed green full frontend run.
- `npx vitest run --maxWorkers=2 --testTimeout=15000` and `npx tsc -b` were blocked
  by PowerShell's execution policy (no test results). The `.cmd` equivalents ran;
  `npx.cmd vitest run --maxWorkers=2 --testTimeout=15000` and the six-file direct
  frontend command without `--pool=threads` stalled after the runner banner and
  were interrupted with no test counts. The direct threaded commands above
  completed. No execution policy was changed.
- Broad backend attempts were stopped before producing test results. Commands:
  `.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence -q`;
  the same with `--ignore=tests/session_integration/test_refresh_migration_chain.py -q --tb=short`;
  and `.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence --ignore=tests/session_integration/test_migration_execution.py --ignore=tests/session_integration/test_refresh_migration_chain.py -q --tb=short`.
  No complete full-backend result is claimed. The final focused runs execute no
  migration runner. No migration execution was observed in the aborted attempts.
- Database upgrade/downgrade suites under `tests/persistence/` and
  `tests/session_integration/test_migration_execution.py` /
  `test_refresh_migration_chain.py` were excluded from final verification because
  they apply migrations, contrary to the task restriction. These are **not run**,
  not pytest skips. PostgreSQL recovery/session tests use the existing guarded
  disposable-schema fixture and ORM test DDL; public table counts/revision are
  checked before and after. No application records or production DB were touched.
- The initial browser attempt could not load `/login` before Vite was ready. A
  subsequent run had 26 passed / 1 failed due to the hidden-image `currentSrc`
  harness defect. The final corrected run passes all 27.

### Independent review

A separate read-only reviewer inspected recovery locks/revocation, proxy
templates/tests, the working migration diff and artwork references. It found no
additional critical or important defect. It independently corroborated the asset
references/crop provenance; visual source comparison was performed by the main
reviewer. Runtime deployment and SMTP durability remain unresolved, not approved.

### Modified files and final Git status

Seven tracked files are modified and one new report is untracked:

- `backend/alembic/versions/0011_password_recovery.py`: close rollback insert race.
- `backend/tests/test_recovery_migration.py`: lock regression and revision chain.
- `backend/tests/test_password_recovery.py`: keyed algorithm/domain separation.
- `backend/tests/session_integration/test_password_recovery.py`: leading-zero
  cryptographic generation, exact five-minute lifetime and stored HMAC.
- `backend/AUTHENTICATION.md`: explain transactional downgrade lock and quiescence.
- `scripts/verify_auth_layout.mjs`: handle unloaded hidden image identity.
- `docs/superpowers/plans/2026-11-20-recovery-audit-auth-restoration.md`: resumed
  work and verification/deployment decisions.
- `docs/security/RECOVERY_AUDIT_2026-11-22.md`: this independent-review handoff.

The pre-existing untracked `codex-auth-review.txt` is unchanged. HEAD remains
`c7068e9`; no commit, push, merge, deployment, AWS/Nginx/DNS edit, credential
configuration, real email, database migration, or unrelated page redesign.

Logs named `recovery-*.log` and browser evidence under
`docs/security/evidence/combined-auth-review/` are local ignored artifacts.

## Manual beta actions

1. Resolve durable delivery and keep recovery disabled until synthetic crash,
   retry, expiry and stale-delivery tests pass.
2. Review the intended database identity, schema, ownership and current revision;
   back up and rehearse restore before separately authorizing migration 0011.
   Prefer app rollback retaining the additive table; never delete history to
   force downgrade. Quiesce recovery traffic for any approved downgrade.
3. Verify actual Nginx/Uvicorn trust settings and direct backend isolation. Review
   any CDN/load balancer trust chain before changing the single-proxy template.
4. Provision independent HMAC/encryption keys and SMTP TLS/sender credentials via
   an approved secret manager only after delivery is implemented; then perform an
   explicitly authorized staging email and cross-browser review.
5. Obtain independent approval of this working diff and resolve any remaining
   verification gaps before beta deployment. No production-readiness claim.
