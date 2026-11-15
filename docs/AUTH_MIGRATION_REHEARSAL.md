# Authentication recovery rehearsal — backup verified, isolated startup failed

**Superseded by the completed 15 November rehearsal:** see
[final results and approval conditions](AUTH_MIGRATION_FINAL_REHEARSAL.md).
Restore and migration to 0008 passed on the approved rehearsal database; 182
database-backed tests passed on the separate test database. The original remains
unchanged at 0004. The earlier blocker history below is retained as evidence.

## Existing-server investigation — 15 November 2026

**NO-GO: database creation privilege unavailable.** This is the current blocker,
superseding the Windows process-startup blocker for the proposed existing-server
approach. No initdb/pg_ctl startup was retried.

Read-only command output confirmed:

```json
{
  "database": "whatnot_app_dev",
  "revision": "0004",
  "users": 5,
  "order_counts": {"PLACED": 1, "DELIVERED": 2},
  "configured_role_superuser": false,
  "configured_role_createdb": false,
  "configured_role_createrole": false,
  "settable_database_creation_roles": 0
}
```

The account owns the original database and can connect to maintenance database
`postgres`, but database ownership does not confer CREATEDB. No eligible role can
be selected through SET ROLE. An unauthorized CREATE DATABASE was not attempted;
this conclusion comes from the role catalog and membership checks, not an observed
permission-error response. No administrator credentials were requested or exposed.

The protected archive still exists, **31,480 bytes**. pg_restore --list again
exited **0**, including table data. Independently recomputed SHA-256 again matched:

```text
4e3ea42158673f1ee355150b083e41bd72f35ffd1d39006073e4a15d8135708b
```

Backup:
`C:\Users\DELL\AppData\Local\Temp\WhatNotRecovery-321h5wu2\original-0004.dump`

No new database, restore or migration was executed. Restored record counts/final
rehearsal revision remain unavailable. Authentication/persistence database tests
were not run because no verified writable test target exists. Zero original orders
were affected. All database connections in this investigation enforced read-only
defaults; the original remains unchanged. No deployment, commit or push occurred.

### Smallest safe next step

An existing local PostgreSQL administrator can create **only two empty databases**
owned by the original application's role. This avoids granting CREATEDB, changing
credentials or restarting the server. Prepared script:
`docs/security/create_rehearsal_databases.psql`.

Proposed names were checked against pg_database and are currently unused:

- `whatnot_rehearsal_20261115_a7e394c2`
- `whatnot_tests_20261115_a7e394c2`

The script rechecks target-name availability, maintenance-database identity and
database-creation privileges. It refuses existing names, resolves ownership from
the original's catalog entry, uses template0, and runs no DROP, restore, migration
or original-database statement. If the second creation fails, the first is retained.

From the repository root, run this in PowerShell using an existing administrator
role (`postgres` below, substitute the actual local administrator if different).
Enter its password only at the local psql prompt; do not send credentials in chat:

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\psql.exe' -h 127.0.0.1 -p 5432 -U postgres -d postgres -W -f .\docs\security\create_rehearsal_databases.psql
```

The administrator script is **prepared, not executed**. After empty database
creation is confirmed, the existing-server rehearsal executor must verify their
database OIDs, ownership, emptiness and exact target identities before writes.
Use explicit URLs for each pg_restore/Alembic/test connection, with connection-time
identity checks; never use the original as a write target. The existing
isolated-cluster runner must be adapted before reuse: its different-port guard
and PostgreSQL-startup code are inappropriate for this approach. Tests require a
separate database and fixture overrides rather than retrying the blocked pg_ctl
fixture. No successful rehearsal or restoration is claimed.

Separate explicit approval remains mandatory for any original-database migration.
Evidence: `docs/security/evidence/auth-existing-server-preflight.json`.

## Latest attempt — 14 November 2026

Recommendation: **NO-GO for migrating the original database.** The backup exists,
but a restore and migration rehearsal have not yet completed. The original remains
at revision 0004. This supersedes the earlier preflight-only result below.

### Guard correction and verification

`docs/security/rehearse_auth_recovery.py` now permits ordinary idle sessions with
no open transaction or potentially writable business-table lock. It reports and
blocks open transactions, active/idle-in-transaction/unobservable sessions,
potential write locks, and prepared transactions. No unrelated session is terminated.
The observation explicitly records `future_writes_excluded: false`: it does not
claim writer quiescence. Backup consistency uses the exported REPEATABLE READ,
READ ONLY transaction snapshot supplied to pg_dump while the exporting transaction
remains open. Source connections and pg_dump enforce read-only defaults.

Eight regression tests in `backend/tests/test_recovery_preflight.py` first failed
against the missing transaction-aware classifier, then **8 passed in 1.94 seconds**
after implementation. A live preflight initially exposed a trailing-comma SQL
syntax error (42601), before any backup; it was corrected and preflight rerun.

### Actual command evidence

Executed from the repository root:

```powershell
& .\backend\.venv\Scripts\python.exe docs/security/rehearse_auth_recovery.py
```

- Source verified: loopback `whatnot_app_dev`, port 5432, PostgreSQL 17.11,
  revision **0004**, **5 users**, **2 DELIVERED + 1 PLACED orders**.
- Session observation: **1 ordinary idle**, **0 risk sessions**, **0 prepared
  transactions**. Preflight **PASS**; no assumption that future writes are excluded.
- Backup: pg_dump custom archive with exported snapshot, exit **0**; pg_restore
  archive listing exit **0**, contains table data; **31,480 bytes**.
- Backup path:
  `C:\Users\DELL\AppData\Local\Temp\WhatNotRecovery-321h5wu2\original-0004.dump`
- SHA-256:
  `4e3ea42158673f1ee355150b083e41bd72f35ffd1d39006073e4a15d8135708b`
- A sidecar checksum file was written. The checksum matched before progression
  and was independently recomputed after the failed startup.
- The archive retains source ownership/ACL metadata, but is a single-database
  backup: cluster-wide roles/tablespaces are excluded. The rehearsal restore is
  configured to remap ownership/privileges to its isolated role. Permission parity
  with the original runtime still requires verification before a real cutover.
- Directory access inheritance was removed; current Windows user and SYSTEM have
  access. This is outside OneDrive. Retain it; TEMP cleanup could otherwise remove it.
- initdb completed. Isolated pg_ctl startup **FAILED**, runner exit **1**:

```text
pg_ctl: could not create restricted token: error code 87
pg_ctl: could not start server: error code 3
```

The automatic shutdown attempt also returned a failure because no postmaster PID
file existed. A subsequent exact-data-directory status check confirmed:

```text
pg_ctl: no server running
```

No restore was executed. **Restored record counts: unavailable. Final rehearsal
revision: unavailable. Migration results/audit validation: not run.** Zero original
orders were affected. Database-backed tests were not run after the failed restore
stage; the user explicitly required stopping. The archive listing and checksum
are not a substitute for a successful restore test.

A final enforced-read-only source check again returned revision **0004**, **5
users**, **2 DELIVERED + 1 PLACED**. The runner made no original writes, changed no
credentials and did not deploy, commit or push. No original database reset,
cleanup or session termination occurred.

### Remaining blocker and next step

Windows prevented pg_ctl from creating its restricted process token. The log proves
the token-creation failure; it does not by itself prove whether sandbox policy or
another Windows execution-context restriction caused it. No automatic bypass or
startup retry was attempted after this restore-stage failure.

The next attempt must use an execution context that supports isolated PostgreSQL
startup, retain the protected backup, and reverify its checksum before restoring.
Then verify all restored rows against the source backup snapshot, migrate only the
isolated target to pinned 0008, validate two LEGACY conversions and their audit
events, verify all five original users and authentication, and run isolated
database-backed tests. Source data may evolve after backup; take a fresh consistent
snapshot/backup if comparison with the original is needed on a later attempt.

Separate explicit approval is still required before migrating the original.
Redacted command evidence: `docs/security/evidence/auth-rehearsal-backup.json`.

## Earlier attempt — stopped at preflight

Date: 14 November 2026. Recommendation: **NO-GO for migrating the original**
until backup, restored-copy migration and validation have completed.

The approved workflow was started with:

```powershell
& .\backend\.venv\Scripts\python.exe docs/security/rehearse_auth_recovery.py
```

Actual command output, exit code 1:

```json
{"stage":"preflight","status":"FAIL","exception_class":"RuntimeError","sqlstate":null,"message":"Other source sessions exist; stop for writer review"}
```

The runner had verified the loopback database identity, read-only transaction,
revision 0004, five users, and order counts before stopping. A subsequent strictly
read-only inspection confirmed database `whatnot_app_dev`, revision `0004`, five
users, two DELIVERED orders and one PLACED order. One other connection was **idle
with no open transaction**. No listener on local port 8000 was observed.

The preflight guard was stricter than necessary: an idle session is not evidence
of an active writer, and an exported snapshot permits a consistent pg_dump even
with concurrent connections. It must not be described as a failed backup or as
proof of data corruption. Execution stopped at the failed check; no session was
terminated and no automatic retry was attempted.

## Artifacts and completed checks

- Prepared `docs/security/rehearse_auth_recovery.py`; Python AST syntax check passed.
- `git diff --check` passed, with existing Windows line-ending warnings.
- Created access-restricted local recovery directory:
  `C:\Users\DELL\AppData\Local\Temp\WhatNotRecovery-57scg4ua`.
  Inheritance was removed; the current Windows user and SYSTEM were granted access.
  This directory contains preflight evidence, **not a database backup**.
- Redacted results: `docs/security/evidence/auth-rehearsal-preflight.json`.
- No backup archive, restore, rehearsal cluster, migration or database-backed test
  was executed. There are no restore or authentication success results to report.
- Affected order count: **zero**. The expected two DELIVERED → COMPLETED/LEGACY
  conversions remain unexecuted; no migration audit events were created.
- No original schema/data/credentials were changed, and nothing was deployed,
  committed or pushed. Existing application/migration files were not changed.

## Remaining steps

Review the idle connection before resuming. Either close the known local database
client normally, or revise the guard to accept idle connections with no open
transactions while retaining the exported-snapshot backup and original read-only
connections. Do not kill an unidentified process or terminate database sessions.

Then rerun the approved backup → isolated restore → pinned 0008 migration →
data/schema/auth validation workflow. Retain command evidence and run relevant
PostgreSQL-backed regression tests on the test harness's separate temporary cluster.
If any of those stages fails, stop and report. The original database migration
still requires **separate explicit approval**, regardless of rehearsal outcome.
