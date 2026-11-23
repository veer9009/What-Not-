# What Not? — local combined implementation and security review

Implementation began 22 November and verification continued 23 November 2026.
Branch: `ui/sage-premium-redesign`; baseline and final HEAD: `15a8430`.
User-approved design: `docs/superpowers/specs/2026-11-22-durable-recovery-registration-design.md`.
No commit, push, merge, deployment, real email, real credential configuration,
infrastructure edit, account/transaction modification or migration execution.
The pre-existing untracked `codex-auth-review.txt` remains untouched.

## Task 1: durable recovery

The existing FastAPI recovery service already generated cryptographic six-digit
OTPs, HMAC digests, five-minute expiry, five attempts, cooldown/quota enforcement,
challenge/reset-proof supersession, password binding and session revocation.
Those controls were preserved. The defect was delivery through an in-process
post-commit task, which loses work on restart and cannot retry durably. The
ordinary EmailOutbox JSON is unsuitable for OTP plaintext.

Implemented a separate recovery-delivery table and atomic encrypted enqueue
inside the existing service savepoint. Recipient and OTP are AES-256-GCM
encrypted through the installed `cryptography==49.0.0`, with fresh 96-bit nonces,
versioned independent 256-bit keys and associated data binding challenge, user
and UTC expiry. No custom encryption was introduced. Encryption/enqueue failure
rolls back challenge creation and supersession. Suppressed/ineligible requests
enqueue no deliverable mail. Normal notification JSON/APIs remain unchanged.

The worker uses committed leases, SKIP LOCKED claims, token fencing, bounded
attempts, exponential backoff and crash-lease recovery. Send transactions lock
user → recovery → delivery, revalidate credential state and hold locks through
bounded SMTP and acknowledgement. Supersession waits for an active send. Both
lease and OTP must have the full send budget plus margin remaining. Expired,
superseded, invalid, completed and terminally failed work loses its ciphertext
and key identifier. Cleanup advances within the bounded batch, allowing fresh
mail behind expired jobs to proceed.

The existing SMTP adapter runs in a private child with credentials/message in
anonymous stdin. Parent timeout and a child watchdog enforce the same absolute
monotonic deadline. Killing the worker does not remove the child's deadline.
Tests kill a real synthetic worker during fake blocked SMTP and wait for its
orphan child to terminate; no network is contacted. Database disconnect during
an accepted fake send is also tested: acknowledgement rolls back, the persisted
lease is reclaimed and the same Message-ID can be retried. This deliberately
documents possible duplicate delivery, **not exactly-once SMTP**.

Live recovery stays disabled by default. No activation setting was changed.
The fake-only legacy test path remains for existing tests and cannot deliver
live email. Actual activation requires independent keys, SMTP/TLS prerequisites,
the dependency, migration and supervised workers; see the operations runbook.

### Migration

Added `backend/alembic/versions/0012_recovery_deliveries.py`, parent `0011`.
It adds one table, restrictive foreign keys, state/attempt/payload/lease checks
and user/expiry/due/lease indexes. Downgrade locks and refuses retained history.
No existing rows are rewritten. Revision chain and PostgreSQL DDL are checked
offline; no Alembic upgrade/downgrade was executed. Integration behavior uses
ORM DDL only in the existing guarded synthetic-schema fixture; public tables
and revision snapshots are checked unchanged.

The application readiness/bootstrap expectation is now 0012. Existing databases
were not migrated; an older deployed schema will fail this build's readiness.
Do not deploy this build without separately authorized migration/rehearsal.

## Task 2: seller/buyer registration

Root cause: `RegisterPage` preselected SELLER from a query parameter but always
rendered the generic account selector/title. Fixed `/register?role=seller` to
show Create Seller Account with no Buyer/Seller selector or buyer switch.
The submitted payload is forced to SELLER by that journey, independent of generic
form state. Existing fields/validation and sign-in return remain. No seller
verification or administrator approval was granted by registration.

Login now links Create Buyer Account to `/register?role=buyer`, fixing BUYER and
hiding selection. Generic `/register` retains existing compatibility and its
selector. Backend UserRegistration still permits only BUYER/SELLER, duplicate
identity checks remain, and server authorization/moderation remain authoritative.

## Task 3: Creative Services

Audit found an existing single-role SELLER + unique CreativeProvider system,
studio/dashboard, bio/profile, portfolios, four supported categories including
VFX, pricing, remote/local service area, moderated listings, RFQs, quotations,
engagement delivery/completion and reviews. This functionality was reused.

Login now offers `/register?intent=services`. Service Provider Registration hides
the irrelevant selector and submits SELLER to the existing endpoint. It explains
provider/profile/listing setup in the existing studio and admin review. Sign-in
with the literal services intent continues SELLER to `/seller/creative`; BUYER
goes to the unsupported-enrollment explanation; ADMIN retains `/admin`. An
arbitrary `next` parameter is ignored, preventing an open redirect.

Signed-in sellers open their current studio without registering again. Existing
buyers see that buyer-to-provider enrollment is not yet supported, retain their
role and are explicitly told not to create another account. No new role,
membership system, role overwrite, enrollment endpoint or dashboard was added.

Remaining architecture gaps: no multi-role enrollment, separate provider-
verification state, availability calendar or dedicated experience field. Bio may
describe experience but is not verification. Categories beyond Video Editing,
Travel Video Editing, Influencer Reel Editing and VFX require separate changes.
Creative Services payments/escrow remain unavailable. Pending listings are not
public; only administrators may approve them. Registration is not provider approval.

## Independent review and fixes

A separate reviewer performed a read-only static review without tests, SMTP,
migrations, secret inspection, edits or further delegation. It found no Critical
issue and two Important issues in the initial implementation:

1. The AES separation validator accepted the identical base64 configuration value
   for AES and JWT/HMAC. Added raw/encoded equality rejection. Both reproductions
   failed first and then passed.
2. A worker-owned SMTP timeout could disappear on worker death. Added the child-
   enforced deadline and a real orphan-process regression. It failed before the
   fix and passed afterward.

The review also identified missing lease indexing/state consistency and services
continuation coverage. Added the index/check and BUYER/SELLER/ADMIN continuation
tests. Self-review additionally reproduced/fixed premature expiry-cleanup batch
termination. OTP near-expiry send suppression also has a failing-then-passing
regression. The reviewer did not assess actual deployed DB limits, supervision,
provisioned key quality/independence, backups or production readiness. These remain
operator verification, not silently accepted deployment conditions.

## UI/artwork

No assets, CSS theme or unrelated pages were redesigned. The original
`neighborhood-world.*` artwork and City/Town/Village remain in the shared public
authentication panel. Unified login, separate admin login and the existing seller
and creative dashboards remain. No India map, boundary or geographic outline was
introduced. Browser evidence covers the new registration routes and all recovery
steps at 390/768/1440, including fixed titles and absent role selectors.

## Verification commands and outcomes

Commands below are the exact test/build invocation before stdout/stderr log
redirection. Python commands run from `backend/`, Node commands from repo root.
Counts overlap across runs and must not be added together. Logs `combined-*.log`
are local ignored artifacts; browser results/screenshots are under the existing
ignored `docs/security/evidence/combined-auth-review/` folder.

Final backend command:

```powershell
.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence --ignore=tests/session_integration/test_migration_execution.py --ignore=tests/session_integration/test_refresh_migration_chain.py -q --tb=short
```

**534 passed, 0 failed, 0 skipped**, 217.60s, exit 0 (`combined-backend-verified.log`).
Includes recovery unit/integration, real encryption, worker/crash/DB-loss/retry,
proxy, authentication/session, role/authorization and provider onboarding cases.
The migration-executing suites listed above and persistence directory are **not
run**, not pytest skips. Two edited migration/persistence tests only update head
expectations; their database-executing runners remain unexecuted.

Final frontend aggregate command:

```powershell
node node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=2 --testTimeout=15000 --reporter=verbose
```

**448 passed, 1 failed, 0 skipped**, 51 files, 384.84s, exit 1
(`combined-frontend-verified.log`). The one failure is the unchanged
`src/LocationDiscovery.test.tsx` case `associates PIN guidance and styles the clear
action as a secondary button`: Longitude could not be found during manual entry.
It passed in the earlier single-worker full run. A final isolated retry:

```powershell
node node_modules/vitest/vitest.mjs run src/LocationDiscovery.test.tsx --pool=threads --maxWorkers=1 --testTimeout=15000 --reporter=verbose
```

**12 passed, 0 failed, 0 skipped**, 24.55s, exit 0
(`combined-location-retry.log`), without changing location application/test code.
The prior Sage fixture failure is fixed and passed in this final full run. All
authentication/registration/recovery cases passed. Every frontend case has passed
across these runs, but **there is no single clean green full frontend invocation**.
The intermittent aggregate failure's root cause is unresolved and must be reviewed
before beta deployment; it is not silently attributed to CPU or infrastructure.

Other completed verification:

| Command | Outcome |
| --- | --- |
| `node node_modules/typescript/bin/tsc -b` | Exit 0, including final check (`combined-typecheck-final.log`) |
| `node node_modules/vite/bin/vite.js build --config vite.config.ts` | Exit 0, 1961 modules, built in 21.01s (`combined-build.log`) |
| `node scripts/verify_auth_layout.mjs` | Final exit 0; 36/36 cases plus reduced-motion, validation and separate-admin checks; fixed registration headings/selectors also checked |
| `git diff --check` | Exit 0; Windows LF/CRLF notices only |

Browser server: `npm.cmd run dev -- --host 127.0.0.1`; stopped after browser
verification. Recovery responses were synthetic; browser evidence does not prove
real SMTP/API delivery. Fonts may fall back to system fonts. An unavailable
backend notice in login screenshots is expected without a live backend.

### Earlier runs, failures and retries

All ordinary successful runs below had zero skips. No suite was interrupted in
this approved implementation phase; the documentation rewrite shell operation
was interrupted and replaced with a completed targeted patch. It was not a test.

| Exact command | Recorded outcomes/logs |
| --- | --- |
| `.venv/Scripts/python.exe -m pytest tests/test_recovery_delivery.py -q --tb=short` | Initial RED 7 failed (missing implementation); after review fixes 15 passed in 11.08s (`combined-delivery-red.log`, `combined-review-green.log`) |
| `.venv/Scripts/python.exe -m pytest tests/test_recovery_delivery.py tests/test_password_recovery.py tests/test_recovery_proxy_boundary.py -q --tb=short` | 26 passed (`combined-delivery-unit.log`) |
| `.venv/Scripts/python.exe -m pytest tests/session_integration/test_recovery_delivery.py -v --tb=short` | First 13 passed/3 failed (fixture cooldown/shared pending work); second 15 passed/1 failed (synthetic `.test` email rejected). Corrected fixture teardown/cooldown/email (`combined-delivery-integration*.log`) |
| `.venv/Scripts/python.exe -m pytest tests/session_integration/test_provider_onboarding.py -q --tb=short` | Initial 1 passed/4 failed: tests expected OwnershipError instead of existing InvalidRole. Corrected assertions; all five pass in final suite |
| `.venv/Scripts/python.exe -m pytest tests/test_recovery_delivery.py tests/test_recovery_delivery_migration.py tests/test_recovery_migration.py tests/test_password_recovery.py tests/test_recovery_proxy_boundary.py tests/session_integration/test_recovery_delivery.py tests/session_integration/test_password_recovery.py tests/session_integration/test_refresh_sessions.py -q --tb=short` | Initial 80 passed/8 failed: overly broad DDL text assertion and source quota interference across independent cases. Scoped assertion and unique synthetic peers; limits remain enabled (`combined-backend-focused.log`) |
| `.venv/Scripts/python.exe -m pytest tests/test_recovery_delivery.py tests/test_recovery_delivery_migration.py tests/test_recovery_migration.py tests/test_password_recovery.py tests/test_recovery_proxy_boundary.py tests/session_integration/test_recovery_delivery.py tests/session_integration/test_password_recovery.py tests/session_integration/test_refresh_sessions.py tests/session_integration/test_provider_onboarding.py -q --tb=short` | 93 passed (`combined-backend-final.log`), before later regressions were added |
| `.venv/Scripts/python.exe -m pytest tests/test_recovery_delivery.py -k 'identical_encoded or survives_worker_death' -q --tb=short` | RED: 3 failed, 12 deselected (`combined-review-red.log`); final suite passes all three |
| `.venv/Scripts/python.exe -m pytest tests/session_integration/test_recovery_delivery.py -k otp_will_expire -q --tb=short` | RED: 1 failed, 17 deselected; final suite passes (`combined-expiry-red.log`) |
| `.venv/Scripts/python.exe -m pytest tests/session_integration/test_recovery_delivery.py -q --tb=short` | 18 passed after lock-order cleanup (`combined-delivery-lock-order-final.log`), before the backlog regression |
| `.venv/Scripts/python.exe -m pytest tests/session_integration/test_recovery_delivery.py -k expiry_cleanup -q --tb=short` | RED: 1 failed, 18 deselected; final suite passes (`combined-cleanup-red.log`) |
| Final backend command above, earlier invocations | First 532 passed/1 failed due to assuming globally empty ordinary outbox after provider tests; corrected assertion to the recovery account. Then 533 passed before the backlog regression was added (`combined-backend-suite*.log`) |
| `node node_modules/vitest/vitest.mjs run src/pages/RegistrationJourneys.test.tsx --pool=threads --maxWorkers=1 --reporter=verbose` | RED 6 failed, then GREEN 6 passed (`combined-registration-red.log`, `combined-registration-green.log`); later continuation tests are covered by retries/full run |
| `node node_modules/vitest/vitest.mjs run src/pages/RegistrationJourneys.test.tsx src/pages/LoginPresentation.test.tsx src/App.test.tsx src/pages/CreativePages.test.tsx src/pages/PasswordRecoveryPage.test.tsx src/api/passwordRecovery.test.ts src/state/AuthContext.test.tsx src/state/SessionLifecycle.test.tsx --pool=threads --maxWorkers=1 --testTimeout=15000` | 78 assertions passed in 7 files; SessionLifecycle suite failed to load due to Windows EBUSY on a dependency file; exit nonzero (`combined-frontend-focused.log`) |
| `node node_modules/vitest/vitest.mjs run src/pages/RegistrationJourneys.test.tsx src/state/SessionLifecycle.test.tsx --pool=threads --maxWorkers=1 --testTimeout=15000` | 14 passed, 2 files (`combined-frontend-retry.log`) |
| `node node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --testTimeout=15000` | 448 passed/1 failed across 51 files, 837.65s. Sage layout fixture lacked newly used roleHome mock and incorrectly treated public registration as signed in. Corrected fixture (`combined-frontend-suite.log`) |
| `node node_modules/vitest/vitest.mjs run scripts/sage-layout.test.tsx src/pages/RegistrationJourneys.test.tsx --pool=threads --maxWorkers=1 --testTimeout=15000` | 11 passed, 2 files (`combined-layout-fixture-retry.log`) |
| `node scripts/verify_auth_layout.mjs`, first invocation | 36/36 passed; final invocation additionally verifies fixed titles and hidden selectors |
| Final two-worker frontend command above | 448 passed/1 failed; unchanged location field case, 384.84s, exit 1 |
| Final isolated location command above | 12 passed, 24.55s, exit 0; no location code/test edits |

Dependency installation: the previously sandbox-denied attempt is historical.
After approval, `.venv/Scripts/python.exe -m pip install cryptography==49.0.0 --retries 0 --timeout 15`
installed the package, although the PowerShell wrapper returned 1 while emitting
a pip update notice on stderr. Verification command
`.venv/Scripts/python.exe -c "from importlib.metadata import version; print(version('cryptography'))"`
returned `49.0.0` with exit 0. Real AES-GCM tests ran; no missing-dependency skip or
substitute encryption is counted as a pass.

## Complete modified-file list and purpose

Tracked modifications:

- `backend/AUTHENTICATION.md`: current durable recovery and runbook link.
- `backend/app/api/routes/auth.py`: no background live send in durable mode.
- `backend/app/core/config.py`: default-off gate, independent versioned AEAD keys,
  bounded deadline and configuration validation.
- `backend/app/db/schema.py`: readiness/bootstrap expected revision 0012.
- `backend/app/models/__init__.py`: register new ORM mapping.
- `backend/app/services/auth_recovery.py`: atomic enqueue/cancel with preserved
  recovery controls and fresh timestamp after obtaining the user lock.
- `backend/app/services/mail.py`: bounded isolated recovery SMTP adapter.
- `backend/app/workers.py`: recovery-only bounded worker command.
- `backend/requirements.txt`: pinned established cryptography dependency.
- `backend/tests/persistence/test_beta_resume.py`: head expectation only; not run.
- `backend/tests/session_integration/test_password_recovery.py`: independent
  synthetic source identities so combined cases do not exhaust each other's quota.
- `backend/tests/session_integration/test_refresh_migration_chain.py`: head and
  new-table assertions only; migration-executing test not run.
- `backend/tests/test_admin_bootstrap.py`: expected current schema.
- `backend/tests/test_public_discovery.py`: readiness current-schema expectation.
- `backend/tests/test_recovery_migration.py`: complete revision chain through 0012.
- `scripts/sage-layout.test.tsx`: faithful auth mock and anonymous registration fixture.
- `scripts/verify_auth_layout.mjs`: new journeys, fixed headings and hidden selectors.
- `src/App.test.tsx`: buyer-specific login link assertion.
- `src/pages/LoginPages.tsx`: focused seller/buyer/services journeys and existing-user boundaries.
- `src/pages/LoginPresentation.test.tsx`: new route/link/selector/artwork assertions.

New files:

- `backend/alembic/versions/0012_recovery_deliveries.py`: additive encrypted queue DDL.
- `backend/app/models/recovery_delivery.py`: isolated encrypted delivery mapping.
- `backend/app/recovery_smtp.py`: private independently bounded SMTP child.
- `backend/app/services/recovery_delivery.py`: AEAD, atomic enqueue/cancel, leasing,
  validity/fencing, retries, erasure and bounded batch processing.
- `backend/tests/session_integration/test_provider_onboarding.py`: existing roles,
  categories, duplicate identity and admin moderation boundaries.
- `backend/tests/session_integration/test_recovery_delivery.py`: real encrypted
  PostgreSQL lifecycle, worker faults/concurrency/expiry/cleanup regressions.
- `backend/tests/test_recovery_delivery.py`: real AEAD/configuration, safe adapter
  behavior and actual orphan-process timeout regression.
- `backend/tests/test_recovery_delivery_migration.py`: offline additive/guarded DDL.
- `src/pages/RegistrationJourneys.test.tsx`: fixed submission roles, existing-user
  handling and literal services continuation for BUYER/SELLER/ADMIN.
- `docs/security/DURABLE_RECOVERY_OPERATIONS.md`: activation/key/DB/SMTP/rollback runbook.
- `docs/security/COMBINED_IMPLEMENTATION_2026-11-23.md`: this handoff and evidence.
- `docs/superpowers/plans/2026-11-22-durable-recovery-registration.md`: execution record.
- `docs/superpowers/specs/2026-11-22-durable-recovery-registration-design.md`: pre-existing
  untracked approved design, updated to record approval and resolved dependency.

## Remaining blockers before any beta activation

Keep recovery disabled until an operator separately reviews/applies the migration,
rehearses backup/restore, provisions independent keys and SMTP/TLS credentials,
supervises workers and verifies DB pool/lock/idle timeouts, actual proxy topology,
staging delivery, process/connection-loss behavior and monitoring. Resolve the
intermittent frontend aggregate failure and obtain a clean full run. SMTP duplicates
and delayed arrival remain possible; encrypted backups and worker-downtime cleanup
need retention policy. Provider-specific verification and multi-role enrollment
are explicitly absent. No production-readiness recommendation is made.

## Final Git status

No files were staged. The original `codex-auth-review.txt` is the only unrelated
untracked file and was neither read nor changed. HEAD remains `15a8430`.

```text
 M backend/AUTHENTICATION.md
 M backend/app/api/routes/auth.py
 M backend/app/core/config.py
 M backend/app/db/schema.py
 M backend/app/models/__init__.py
 M backend/app/services/auth_recovery.py
 M backend/app/services/mail.py
 M backend/app/workers.py
 M backend/requirements.txt
 M backend/tests/persistence/test_beta_resume.py
 M backend/tests/session_integration/test_password_recovery.py
 M backend/tests/session_integration/test_refresh_migration_chain.py
 M backend/tests/test_admin_bootstrap.py
 M backend/tests/test_public_discovery.py
 M backend/tests/test_recovery_migration.py
 M scripts/sage-layout.test.tsx
 M scripts/verify_auth_layout.mjs
 M src/App.test.tsx
 M src/pages/LoginPages.tsx
 M src/pages/LoginPresentation.test.tsx
?? backend/alembic/versions/0012_recovery_deliveries.py
?? backend/app/models/recovery_delivery.py
?? backend/app/recovery_smtp.py
?? backend/app/services/recovery_delivery.py
?? backend/tests/session_integration/test_provider_onboarding.py
?? backend/tests/session_integration/test_recovery_delivery.py
?? backend/tests/test_recovery_delivery.py
?? backend/tests/test_recovery_delivery_migration.py
?? codex-auth-review.txt
?? docs/security/COMBINED_IMPLEMENTATION_2026-11-23.md
?? docs/security/DURABLE_RECOVERY_OPERATIONS.md
?? docs/superpowers/plans/2026-11-22-durable-recovery-registration.md
?? docs/superpowers/specs/2026-11-22-durable-recovery-registration-design.md
?? src/pages/RegistrationJourneys.test.tsx
```
