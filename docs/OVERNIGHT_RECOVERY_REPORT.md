# What Not? overnight local recovery

Date: **15 November 2026**, Asia/Calcutta.

**Local recovery: GO. AWS deployment/public launch: NO-GO pending readiness review.**
The original local database migrated successfully and authentication passed against
it. This report does not certify production readiness or authorize deployment.

## Database and migration evidence

Original: **127.0.0.1:5432 / whatnot_app_dev**, verified OID **41069**.

| Check | Before | After |
| --- | --- | --- |
| Alembic revision | 0004 | **0008** |
| Original users | 5 | **5 preserved**, including identity/password fields |
| Original orders | 3 | **3 preserved** |
| Legacy delivery orders | 2 DELIVERED | **2 COMPLETED / LEGACY** |
| Other order | 1 PLACED | **1 PLACED, unchanged** |
| Matching migration audit events | absent | **2** |

Actual command, repository root:

```powershell
& .\backend\.venv\Scripts\python.exe docs/security/execute_local_cutover.py
```

Actual Alembic call: `command.upgrade(config, '0008')` with explicit local URL and
the held, identity-checked original-database connection. **Exit status 0**, migration
**1.610 seconds**. Migration log:

```text
C:\Users\DELL\AppData\Local\Temp\WhatNotCutover-lmyzuezk\migration.log
Running upgrade 0004 -> 0005
Running upgrade 0005 -> 0006
Running upgrade 0006 -> 0007
Running upgrade 0007 -> 0008
```

Migrations 0005–0008 matched the rehearsed SHA-256 values. No migration script was
changed. The upgrade was attempted/committed **once** against the original; no
downgrade, stamp, reset, original-database restore or migration retry occurred.

Read-only integrity checks passed before reopening: all five users, all three
orders, both exact audit mappings, all other original business rows, mapped
tables/columns and auth ORM projections. Alembic check reported **No new upgrade
operations detected**. Required request_quotas and verification timestamp columns
are present; existing verification fields remain NULL. No buyer consent or
completion timestamps were fabricated.

Evidence: [cutover stages](security/evidence/auth-cutover-result.json) and
[final read-only state](security/evidence/overnight-final-state.json).

## Backups and maintenance

Fresh successful-cutover backup: **31,700 bytes**, custom format:

```text
C:\Users\DELL\AppData\Local\Temp\WhatNotCutover-lmyzuezk\whatnot_app_dev-0004-cutover.dump
```

SHA-256, independently rechecked after recovery:

```text
75cbb960eb64b61ebe9aba5f377efe7d4c96018b556502ad43ade30951a08025
```

pg_dump exited **0** with an exported, read-only repeatable-read snapshot.
pg_restore --list exited **0**. The archive is read-only in an ACL-restricted
directory outside OneDrive; previous backups were preserved. A fresh archive
restore was not performed: the prior rehearsal archive was successfully restored,
but that is not a restore test of this particular file. This is a single-database
backup, excluding cluster-wide roles/tablespaces. Preserve a copy in an approved
durable, encrypted backup location before deployment; TEMP cleanup can remove it.

The corrected control path uses a distinct **postgres** maintenance connection.
Every administrative mutation checks its actual database, loopback server/port,
target OID and target ownership. Every action names only whatnot_app_dev.

Normal new application connections were first forced read-only; a zero-row write
probe failed with **25006**. No other sessions/prepared transactions remained.
New connections were then disabled from postgres. The already held migration
connection explicitly retained read-write capability; new connections were
verified rejected. This prevents an application restart from writing during the
cutover, without terminating unrelated processes/sessions or changing credentials.

An initial corrected-runner invocation stopped before migration because psycopg
wrapped the expected maintenance refusal in OperationalError without SQLSTATE.
Read-only catalog checks proved the barrier was actually active. The narrow
classification was fixed and regression-tested. Read-only-only admission was
verified before reacquiring the held migration connection and reapplying the hard
barrier. That stop is preserved in
`security/evidence/auth-cutover-refusal-probe-stop.json`; the earlier 22023 failure
is preserved separately. No failed migration was retried.

**Final maintenance state:** connections allowed; temporary database-level
read-only setting removed, restoring the original empty database-default list.
Final inspection found **0 other original-database sessions**. No FastAPI/Uvicorn
background process was started by this workflow. The controlled test harness is
closed. A restricted localhost port-8000 probe timed out, so it is not proof of a
live listener or proof of its absence.

## Authentication verification on the migrated original

Used actual development settings and the verified original database through a
controlled FastAPI TestClient, with no unmanaged background server or SMTP delivery.

| Check | Actual HTTP |
| --- | ---: |
| /api/v1/health | **200** |
| /api/v1/ready | **200** |
| Synthetic buyer registration | **201** |
| Duplicate registration | **409** |
| Login | **200** |
| Authenticated identity | **200** |
| Incorrect password | **401** |
| Bounded quota enforcement | **429**, positive Retry-After |

The quota check temporarily lowered only the in-memory harness limit and restored
it; no environment/configuration file was changed. Two quota rows were written.
**0 storage_operation_failed events and 0 unexpected 503 responses** were observed
within these checks. No passwords, tokens or private original-user fields were
printed. Real original users' plaintext passwords were not requested or used.

**Expected additional data:** the explicitly authorized registration test created
one non-sensitive synthetic BUYER. Current user total is **6**: the five originals
plus this account. All original users and unrelated business rows remain unchanged;
orders remain 3 and migration audits remain 2. The test identity is not a production
beta admission decision. No account was automatically deleted.

Evidence: [authentication HTTP results](security/evidence/auth-local-http.json).

## Regression/build results

| Check | Result / scope |
| --- | --- |
| Backend non-persistence suite | **266 passed in 45.29s**, warnings treated as errors |
| Selected real PostgreSQL persistence/auth suite | **182 passed in 93.886s**, no failures/errors/skips |
| Combined backend checks this run | **448 passed**; not the entire backend persistence suite |
| Maintenance/target/preflight guards | **25 passed in 1.44s**, included in the 266; do not add twice |
| Python dependency consistency | **No broken requirements found**; this is not a CVE scan |
| Production build / TypeScript | **PASS**, Vite 8.3.8; build finished in 14.99s |
| Frontend full suite | **253 passed, 1 failed / 254**, 29 files, 330.97s; exit 1 |
| Unchanged failed file + geolocation focused rerun | **17/17 passed**, 2 files, 23.45s; exit 0 |

Database tests used **only whatnot_tests_20261115_a7e394c2**, OID **49265**,
with **2,034 guarded SQL statements**. No migrations were run on that database
during this overnight phase. Only test quota counters were reset there. Original
public-table records matched before/after the test run. Destructive test fixtures
were never pointed at the original or rehearsal database.

Evidence: `security/evidence/auth-database-tests.json`; protected pytest log at
`C:\Users\DELL\AppData\Local\Temp\WhatNotRecovery-321h5wu2\guarded-tests-1794684778639729600\pytest.log`
and adjacent tests.xml. Non-persistence log: `overnight-backend-unit-tests.log`.
Build log: `overnight-build.log`.

pnpm.cmd was absent from PATH; npm/Node ran the installed packages without any
installation, upgrade or lockfile rewrite. The initial concurrent frontend run
reported timeouts/assertion failures and stalled. A single-worker restricted run
also stalled. Both owned test commands were interrupted and their output retained
in `overnight-frontend-tests.log` and `overnight-frontend-serial.log`. A final
single-thread run outside the restricted sandbox completed and uses
`overnight-frontend-verified.log`. Its failure was
`src/pages/AdminOperations.test.tsx:21`, test
"requires an investigation reason and sends only authorized account action fields":
the awaited "Suspend Buyer" button was not found in time. The unchanged file and
geolocation unit tests then passed **17/17**, logged in
`overnight-frontend-focused.log`. This subset is included in the full suite's
coverage and is **not** 17 additional unique frontend tests. The cause of the
full-run failure is not conclusively established; do not call the full suite green.
No test timeouts or application code were relaxed to obtain a pass. These
failed/incomplete attempts remain retained; resolve/reproduce the frontend failure
in the release environment before deployment.

## Working-tree review

All work remains uncommitted. Existing location/security edits were preserved.

- Modified tracked files: backend/alembic/env.py; package.json; pnpm-lock.yaml;
  scripts/beta_browser_smoke.mjs; src/LocationDiscovery.test.tsx;
  src/components/LocationPicker.tsx and its test;
  src/location/geolocation.ts and its test; src/pages/DiscoveryPages.tsx.
- New work includes recovery reports/scripts/redacted evidence under docs;
  backend/tests/test_cutover_control.py, test_recovery_preflight.py,
  test_recovery_targeting.py and persistence/test_security_audit.py;
  pnpm-workspace.yaml and src/utils/securityDependencies.test.js.
- Overnight control fixes are in docs/security/cutover_control.py and
  execute_local_cutover.py. The external Alembic connection path in env.py is
  necessary to preserve the held connection through the maintenance barrier.
- No deployment, commit, push, resource purchase, public launch, existing password
  change or broader database privilege grant occurred.

## AWS deployment-readiness steps — approval/review gates remain

1. Review the complete working-tree diff and retained test failures; resolve
   frontend regressions before release. Decide the reviewed release source and
   obtain explicit deployment approval. Nothing was committed automatically.
2. Close the open rows in [the security checklist](security/DEPLOYMENT_SECURITY_CHECKLIST.md)
   and [risk register](security/SECURITY_RISK_REGISTER.md). A local schema fix does
   not close infrastructure/security evidence gaps.
3. Run/review current Python CVE scanning and secret/history/artifact scanning.
   The prior dependency audit had 0 High/Critical and 2 Moderate Vitest mocker
   advisories; this was **not rescanned overnight**. Review those advisories,
   .env.production ignore coverage and secret provenance before release.
4. Review the exact AWS account/region/domain and infrastructure plan: private
   PostgreSQL, app/proxy boundaries, restricted management access, least-privilege
   IAM/runtime identity, secret delivery and encrypted storage/backups. No AWS
   account or infrastructure state was accessed or verified here.
5. Prepare/review HTTPS certificate/renewal, proxy/header/CORS configuration and
   frontend API base URL. App port 8000 and PostgreSQL 5432 must not be publicly
   exposed. Serve the built frontend through the reviewed production server.
6. Prepare the **separate** approved target migration and fresh backup/restore
   rehearsal for that environment. Do not reuse this local approval for AWS and
   do not import local real-user data or the synthetic smoke account casually.
7. Configure production environment, unique secrets and explicit beta account
   admission; review trusted proxy attribution, quotas, worker scheduling/SMTP,
   sanitized monitoring, backup restore procedures and failure response.
8. Complete buyer/seller/admin browser UAT and HTTPS geolocation checks; review
   privacy/retention, session-draft and logout/revocation decisions. Obtain named
   release sign-off before any pilot/public launch.

## Local startup for human browser verification (not executed overnight)

From the repository root, backend terminal:

```powershell
& .\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Expected backend: `http://127.0.0.1:8000`; health at `/api/v1/health`.
Frontend terminal:

```powershell
& 'C:\Program Files\nodejs\npm.cmd' run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Expected frontend: `http://127.0.0.1:5173`. Default frontend API base is
`http://127.0.0.1:8000/api/v1` unless VITE_API_BASE_URL overrides it. Use authorized
existing account credentials locally; do not paste credentials in reports/chat.

**SUCCESS: Local database migrated, authentication verified, ready for deployment-readiness review.**
