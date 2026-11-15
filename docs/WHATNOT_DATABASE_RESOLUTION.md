# What Not? database resolution and beta gates

15 November 2026. **DATABASE FIX VERIFIED** for the isolated migration and application/schema compatibility checks. **BETA NOT READY**: release gates below remain open. The original database was not migrated or repaired in place; it remains protected at `0008`.

## 1. Isolated migration evidence

| Check | Verified result |
|---|---|
| Original identity | `127.0.0.1:5432`, PostgreSQL 17.11 primary, `whatnot_app_dev`, OID **41069**, revision **0008** |
| Original preservation | Final read-only comparison: **all 24 table fingerprints unchanged**, including account IDs, roles, statuses and password hashes |
| Original/restored counts | **6 users, 2 seller profiles, 3 products, 1 address, 3 orders** |
| Rehearsal | `whatnot_0009_rehearsal_20261115_f24a8f87`, OID **51678**, reused existing restored data; no overwrite/recreation |
| Migration | Only `0008 → 0009`, **exit 0**, committed on rehearsal only |
| Schema | Four nullable public-discovery columns, correct numeric/timestamp/varchar types, three validated CHECK constraints; existing columns, constraints and indexes preserved |
| Constraint behavior | **12 probes passed** per migration attempt, including permitted boundaries, NULL/unset point, invalid latitude/longitude and incomplete/blank consent; all temporary updates rolled back to savepoints |
| Seller consent | All existing seller public fields remain NULL; no private dispatch coordinate copying |
| Data preservation | All 24 original table fingerprints match after excluding only the four new seller fields and allowing the Alembic version change |
| Application compatibility | SQLAlchemy seller projection succeeds; in-process isolated FastAPI **GET `/api/v1/ready` → 200**, `schema=0009` |
| Discovery compatibility | Read-only synthetic 1/2/3 km service queries succeed; correctly return empty until public consent. This is not positive-product or real-GPS acceptance |
| Transaction rollback | Separate OID **51679**, `whatnot_0009_rollback_20261115_f24a8f87`: migration and probes executed inside an outer transaction, deliberate exception before commit; exact `0008` schema/data restored |

The original API's known `0008` versus expected `0009` readiness mismatch is deliberately unchanged. No original active configuration or service was restarted. Existing Chrome QA was not used for test writes. No credentials changed, AWS resources created, deployment, commit or push occurred. Both rehearsal databases and all prior backups remain retained.

Backup used, independently rechecked before migration:

```text
C:\Users\DELL\AppData\Local\Temp\WhatNot0009Rehearsal-_danj7tx\whatnot_app_dev-0008-before-0009-d200cb1f.dump
SHA-256 90f03b591b42dfb92110c80ad19c4bece3bb3885829470adc4f4e4099446c7b8
96,098 bytes; custom format; consistent exported snapshot; listing/full decoding exit 0
```

This protected TEMP archive is not a durable production backup. Migration file `backend/alembic/versions/0009_public_discovery.py` remained unchanged:

```text
SHA-256 25f693303c54011f36ca282c017e03fccd097fe662719d7d6ae5c2f86261856d
```

Execution command, repository root:

```powershell
& .\backend\.venv\Scripts\python.exe -u .\docs\security\rehearse_0009_migration.py --resume 'C:\Users\DELL\AppData\Local\Temp\WhatNot0009Rehearsal-_danj7tx\manifest.json' --rehearsal-oid 51678 --rollback-oid 51679 --continue-restored
```

Exit **0**. This completed command is not idempotent and must not be rerun against the now-migrated target.

Evidence: `docs/security/evidence/0009-rehearsal.json`, `database-resolution-final-checks.json`, and private migration logs under the backup directory. Private fingerprints/logs are not published in this report.

## 2. Corrections implemented

The validator first retains exact comparison, permitting only the documented two cast forms for the twelve named CHECK constraints. It preserves column/literal order and spelling, types, operators, constraint names, validation flags and extended enforcement/column/collation metadata. Unknown syntax and genuinely different constraints fail closed. Legacy snapshot metadata is enriched only after checking its historical fields against a verified read-only source.

Continuation now requires the exact existing restored target at `0008`, no other sessions, matching data and schema, verified archive/migration checksums and the separate empty rollback target. It skips the rehearsal restore entirely. Every mutating SQLAlchemy statement and the rollback restore connection are guarded by target identity checks. The source connector forbids write mode.

Database failures were stale tests: geography fixtures confirmed only private dispatch, omitting explicit public-point consent; assertions expected old coarse discovery outside the exact radius. Only synthetic test consent and expectations were corrected. Direct checkout rejection, stock rollback, authoritative pricing, ownership and private-delivery restrictions remain exercised. No eligibility or business rule was loosened.

Checkout frontend tests expected only `address_id`, although the real client intentionally sends `radius_km: 3` too. The mock assertion was corrected; application checkout code was unchanged.

The bootstrap's exact roster count changed from five to **ten**, including the administrator. Production-only settings, pilot-name restriction, exact database/user/server/port/OID, expected schema, empty users, table lock, admitted admin, existing UserService/Argon2 hasher and transaction safeguards remain. No administrator was created. Nine/eleven identities and old five-person input are rejected. The owner must still supply and approve the actual roster.

## 3. Tests and outstanding coverage

Commands are from repository root unless stated otherwise.

| Command | Result |
|---|---|
| `backend\.venv\Scripts\python.exe -m pytest docs/security/test_0009_rehearsal.py -q` | **54 passed**; new acceptance regressions failed first, then passed |
| From `backend`: `.venv\Scripts\python.exe -m pytest tests --ignore=tests/persistence -q` | **333 passed** after bootstrap correction; initial run 329 passed before four added parameter cases |
| `backend\.venv\Scripts\python.exe -u docs/security/audit_beta_isolated_tests.py --execute-test-schema-after-approval` | Before correction **379 passed / 19 failed / 28 skipped**; after **398 passed / 0 failed / 28 skipped**, exit 0 |
| `node node_modules/vitest/vitest.mjs --run src/Checkout.test.tsx` | **23 passed**, exit 0 |
| `npm.cmd test -- --run` before frontend correction | **268 passed / 31 failed**, 5 failed files; includes checkout stale contract plus async UI failures |
| `npm.cmd test -- --run --maxWorkers=1` after correction | Interrupted after unusually slow progress; AdminOperations and BetaResume async failures observed. Not a passing full-suite result |
| `node node_modules/vitest/vitest.mjs --run --maxWorkers=2` | **299 passed / 0 failed**, all 33 files, exit **0**, 300.57 seconds |
| `npm.cmd run build` | Production **PASS**, independently captured native exit **0**; TypeScript and Vite build succeeded |

The persistence runner used only new generated schemas inside isolated test DB `whatnot_tests_20261115_a7e394c2`, OID **49265**. Identity/search-path guards run per statement. Fresh migrations ran **base → 0009**, with no development-record import. Final successful schema: `whatnot_audit_2fd421b1b17643eebb251da556ef4a68`. Test public schema remains at `0008`, with empty business tables and unchanged public table list. Synthetic schemas retained.

All **28 skips** require an additional disposable database/cluster. The application role lacks CREATEDB, and the known failed Windows isolated-server startup was not retried. Migration/concurrency/independent-transaction cases requiring those fixtures remain unverified. A schema-isolated full run is not a substitute for those checks.

Evidence: `database-resolution-persistence.json` (426 total, 28 skipped, 0 errors/failures), `database-resolution-unit-final.log`, `database-resolution-checkout.log`, `database-resolution-build-final.log`, `database-resolution-frontend-bounded.log`, and `database-resolution-command-summary.json`. The legacy runner also regenerated `beta-final-persistence.json`; the earlier audit report remains historical, while the first fresh failed-run private log is retained at `C:\Users\DELL\AppData\Local\Temp\WhatNotFinalAudit-2z9zok80\pytest.log`. Latest passing persistence log is at `C:\Users\DELL\AppData\Local\Temp\WhatNotFinalAudit-xm9qjyas\pytest.log`.

The completed two-worker frontend run is a full-suite pass, not a focused-test waiver. Earlier async failures did not recur with bounded concurrency; their underlying timing mechanism was not proven or fixed. Retain those failed/interrupted logs and use the recorded two-worker command for reproducible local verification. No timeout or application logic was loosened. Browser acceptance and CI/load reproducibility remain separate gates.

## 4. Clean AWS beta database workflow — prepared, not deployed

Use a **new empty** `whatnot_pilot_beta` database and new dedicated runtime/migration credentials; never restore a development/rehearsal/QA archive into beta. No AWS resources, roles, secrets or pilot database were created by this task. These steps require separately authorized deployment and verified operator access.

1. Freeze/review the current application plus migrations through `0009`, record checksums and build artifact digest. Keep application/workers/restart automation stopped during initialization. Confirm owner-approved ten identities including admin, domain `avetest.online`, business scope and private perimeter.
2. Provision PostgreSQL privately through the approved AWS architecture. Permit 5432 only from the application/migration hosts' security groups; no public database endpoint exposure. Do not expose application port 8000. Require verified TLS/CA for remote DB connections. Database roles must not be superuser, CREATEROLE or CREATEDB. Use a separate database-owning migration role, `whatnot_migrator`, and runtime `whatnot_runtime`; provision unique secrets privately through the approved secret store, never commands/history/artifacts. Do not reuse local credentials or signing keys.
3. An authorized database operator creates the new database from `template0`, owned by the migration role, refuses an existing name, revokes PUBLIC database/schema CREATE access, and allows only the two roles to connect. Record the **actual OID**, server address/port, primary status, owner and role privileges. Through a read-only migration-role connection verify zero user tables/routines/extra schemas and no other sessions. Stop on any unexpected contents or wrong identity.
4. Load the migration URL privately, separately from runtime configuration. Run the following reviewed pattern **only after filling the expected target identity from step 3**. It never uses `Settings()` or development `.env` fallback. This is operator instruction, not an executed production migration:

```python
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from alembic.config import Config
from alembic import command

def require(value):
    if not value:
        raise RuntimeError('Beta initialization safeguard failed; no automatic retry')

url = make_url(os.environ['WHAT_NOT_MIGRATION_DATABASE_URL'])
expected_oid = int(os.environ['WHAT_NOT_BETA_DATABASE_OID'])
expected_address = os.environ['WHAT_NOT_BETA_DATABASE_ADDRESS']
require(url.database == 'whatnot_pilot_beta')
require(url.username == 'whatnot_migrator' and url.drivername == 'postgresql+psycopg')
require(url.query.get('sslmode') == 'verify-full' and url.query.get('sslrootcert'))
engine = create_engine(url, echo=False, hide_parameters=True)
try:
    with engine.begin() as c:
        require(c.execute(text('''SELECT current_database(), current_user,
            (SELECT oid FROM pg_database WHERE datname=current_database()),
            host(inet_server_addr()), inet_server_port(), pg_is_in_recovery()''')).one() == (
                'whatnot_pilot_beta', 'whatnot_migrator', expected_oid,
                expected_address, 5432, False))
        require(c.scalar(text("SELECT count(*) FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema')")) == 0)
        require(c.scalar(text('SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()')) == 0)
        c.execute(text("SET LOCAL lock_timeout = '5s'"))
        c.execute(text("SET LOCAL statement_timeout = '60s'"))
        cfg = Config('alembic.ini')  # Run from reviewed backend directory.
        cfg.attributes['connection'] = c
        cfg.attributes['database_url'] = url
        command.upgrade(cfg, '0009')
        require(c.scalar(text('SELECT version_num FROM alembic_version')) == '0009')
finally:
    engine.dispose()
```

Do not print the URL or unsanitized exceptions; retain operator diagnostics privately. Stop on failure, with no blind retry, downgrade, stamp, reset or automatic restoration. This held-connection transaction targets one immutable database identity. The preflight and writer barrier are necessary; zero sessions at one instant alone does not prevent future writers.

5. Verify four columns/three constraints and empty business tables in a fresh read-only connection. The base-to-0009 migration path was proven twice on isolated generated schemas here; **full fresh-database provisioning, separate-role grants and AWS TLS are NOT VERIFIED** because the application role cannot create databases/roles. Use a separately created disposable staging database to close those gates before AWS admission.
6. As migration owner grant runtime schema USAGE; table SELECT/INSERT/UPDATE/DELETE and sequence USAGE/SELECT needed by the application, with matching migration-role default privileges. Revoke runtime INSERT/UPDATE/DELETE on `alembic_version`; runtime needs only SELECT there. Do not grant ownership, schema CREATE or migration privileges to runtime. Verify denied DDL and permitted intended operations on disposable staging first. Do not apply blanket administrative grants to make tests pass.
7. Render `backend/.env.production.example` privately: production mode, **new strong JWT key**, runtime URL, ten approved unique emails, abuse limits on, `avetest.online` trusted host and exact approved HTTPS CORS origins (or same-origin-only empty list). JSON arrays need outer single quotes in dotenv/systemd EnvironmentFile. Never source an environment file as shell code. Separate migration credentials from runtime service environment. SMTP disabled requires explicitly approved in-app-only beta scope.
8. With verified runtime settings loaded and all writers still stopped, run from the approved backend release directory, substituting the exact observed address/OID:

```text
.venv/bin/python -m app.bootstrap_admin --database whatnot_pilot_beta --server-address <verified-address> --port 5432 --oid <verified-oid>
```

The existing tool prompts for exact target confirmation and local hidden password/confirmation, then creates one admitted ADMIN in one transaction on an empty users table. No admin password or token belongs in CLI arguments. This task verified its strict ten-user guard/service-hasher unit tests, **not a real separate-runtime-role bootstrap**. Rehearse that transaction and duplicate refusal on empty staging before executing it on beta.
9. Verify independent database identity/version and isolated application readiness `200/schema=0009`. Then verify invited/uninvited authentication, admin/seller/buyer RBAC, owner-only records, seller consent, positive/empty 1/2/3km discovery, checkout totals/stock/idempotency and order lifecycle on synthetic staging data. An unset public point correctly hides products; obtain explicit seller public-point consent through the UI, never backfill dispatch locations.
10. Create encrypted durable off-host backups, restore into a new isolated target, validate/time recovery and approve RPO/RTO/retention. Prove alert delivery, worker scheduling and private HTTPS access/denied-outsider behavior. Permit pilot writers only after integrity, privacy and operational gates pass. If initialization fails, retain evidence and target; use reviewed forward repair/compatible application rollback, not an automatic migration downgrade.

## 5. Remaining release blockers

| Gate | Beta impact and exact closure |
|---|---|
| Frontend/browser acceptance and timing | Latest full suite **299/299 PASS**; prior async failures under other execution conditions remain a timing/reproducibility risk. Checkout contract corrected. Reproduce the frozen release on intended CI resources and witness admin approval/buyer checkout on HTTPS; no timeouts or assertions were weakened |
| Independent transaction/migration cases | 28 skipped; provide separately authorized disposable DB capability and rerun these tests without original/QA fallback |
| Empty staging database / production roles | Verify new database, grants/denied DDL, TLS and actual transactional admin bootstrap + duplicate refusal using intended roles |
| Real private HTTPS release | AWS IAM/network/TLS/DNS, Linux Nginx/systemd validation and whole-site private perimeter were not executed. Verify allowed and outsider HTML/API/public-listing requests, TLS chain/renewal, no public 8000/5432, correct proxy trust and readiness |
| Backups, monitoring, mail/worker operations | This is a local rehearsal, not a production restore/alert proof. Demonstrate durable backup and timed restore, approved RPO/RTO, alert receipt and scheduled workers; approve mail scope |
| Privacy/business scope | Owner contact/privacy/support/retention details and ten-user roster still required. Explicitly approve property/Creative scope and exclude unsupported payment recording/settlement, or separately implement it |
| Security/artifact clearance | Current dependency/live-secret scanning and final artifact review remain pending; password reset does not revoke already-issued JWTs. Approve bounded-token incident handling or separately implement session revocation |
| Final browser UAT | Witness buyer/seller/admin lifecycle on the reviewed HTTPS artifact. Mocked tests/in-process readiness do not prove real GPS, deliveries or payments |

These carry forward inspected evidence from `BETA_FINAL_READINESS_AUDIT.md`; this task did not re-audit or silently waive unrelated release gates. The old original runtime is unsuitable as the beta runtime without a separately approved schema-compatible database plan; this workflow uses a new database.

## 6. Exact changed files

- `docs/security/rehearse_0009_migration.py` — conservative constraint comparison, metadata, protected continuation and transactional behavior probes.
- `docs/security/test_0009_rehearsal.py` — targeting/comparison/continuation regressions.
- `backend/tests/persistence/test_order_geography.py` — synthetic public consent and exact-discovery expectations.
- `src/Checkout.test.tsx` — expected real discovery payload.
- `backend/app/bootstrap_admin.py` and `backend/tests/test_admin_bootstrap.py` — exact ten-person guard/tests, retained other safeguards.
- `backend/.env.production.example` — ten-person template comment; no active configuration changed.
- `docs/AWS_PILOT_DEPLOYMENT_RUNBOOK.md` — current schema/count references and clean-beta workflow link.
- `docs/WHATNOT_DATABASE_RESOLUTION.md` — this consolidated report.
- Evidence generated/updated: `docs/security/evidence/0009-rehearsal.json`, `beta-final-persistence.json`, `database-resolution-persistence.json`, `database-resolution-final-checks.json`, `database-resolution-command-summary.json`; ignored command logs listed above. Private backup manifest metadata was enriched, and protected restore/migration logs and synthetic test schemas were retained.

Existing unrelated dirty-worktree changes were preserved. No commit/push. No original migration is implied or authorized by this result.
