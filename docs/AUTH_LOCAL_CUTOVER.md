# Approved local cutover — stopped at maintenance-window gate

**Superseded by successful overnight recovery on 15 November 2026:** original
whatnot_app_dev is now at 0008; integrity and original-database authentication
checks passed. Normal database access is restored. See
[the morning report](OVERNIGHT_RECOVERY_REPORT.md) and
`security/evidence/auth-cutover-result.json`. Earlier failures below are retained.

## Resumed attempt — fresh backup passed; final barrier failed

15 November 2026. **NO-GO. Original migration was not executed.** This section
supersedes the earlier blocked-session result below; that session was closed by
the owner before this attempt.

Executed from the repository root:

```powershell
& .\backend\.venv\Scripts\python.exe docs/security/execute_local_cutover.py
```

Cutover runner exit status **1**. The Alembic upgrade command was **not reached**;
there is no migration exit status or migration log to report.

### Passed safeguards

- Source verified as **127.0.0.1:5432 / whatnot_app_dev**, database OID **41069**,
  owner matches configured role, revision **0004**.
- **5 users**, **3 orders**: **2 DELIVERED + 1 PLACED**. No other sessions or
  prepared transactions. Reported Uvicorn PIDs were no longer present.
- Actual migrations 0005–0008 match the previously recorded rehearsal hashes.
- New application connections were made read-only through the database setting
  `default_transaction_read_only=on`. A zero-row UPDATE probe was rejected with
  SQLSTATE **25006**, confirming the normal application write path was blocked.
- Fresh custom-format, consistent-snapshot pg_dump exited **0**; archive listing
  exited **0**; backup file was made read-only and kept in an ACL-restricted folder.

Fresh backup, **31,700 bytes**:

```text
C:\Users\DELL\AppData\Local\Temp\WhatNotCutover-ccqw8brx\whatnot_app_dev-0004-cutover.dump
```

SHA-256, reverified after stopping:

```text
eccda3083719c8e9a2203245b57c1e117881335e005dcc0a274de57f35fa21d5
```

The previous rehearsal backup was not overwritten. The fresh backup was **not test
restored** during this attempt. Its archive listing/checksum are not a restore test.

### Failure and current state

The additional hard barrier attempted:

```sql
ALTER DATABASE whatnot_app_dev ALLOW_CONNECTIONS false;
```

It was incorrectly issued through the connection to whatnot_app_dev itself.
PostgreSQL rejects disabling connections to the currently connected database with
SQLSTATE **22023**. This is a cutover-runner error, not an application data or
migration failure. The prohibition is explicit in the
[PostgreSQL 17 implementation](https://raw.githubusercontent.com/postgres/postgres/REL_17_STABLE/src/backend/commands/dbcommands.c).
The command must instead use a verified maintenance-database control connection,
while retaining the already verified migration connection to the original.

Execution stopped; no retry, downgrade, stamp, reset or restoration occurred.
An enforced-read-only follow-up confirmed:

| Item | Actual post-stop state |
| --- | --- |
| Revision | 0004 |
| Users | 5 |
| Orders | 2 DELIVERED, 1 PLACED |
| Order conversions/audit inserts | None; upgrade not reached |
| Database default_transaction_read_only | **on — maintenance setting retained** |
| Database allow_connections | true; failed command did not change it |
| Other sessions | 0 |
| Backup checksum | matches recorded fresh checksum |
| Backend/application writers started | No |
| Deployment, commit, push, credential change | None |

Keep the application stopped. Schema/business data were not migrated, but the
database maintenance default **was changed and remains read-only**. Do not describe
the database configuration as wholly unchanged or authentication as fixed.

### Files and verification

- `docs/security/execute_local_cutover.py`: owner-approved cutover runner with
  pinned source/server, rehearsal hashes, backup checks and held-connection guards.
- `backend/alembic/env.py`: supports a caller-supplied verified connection so a
  maintenance barrier need not be reopened to run migrations. No 0005–0008 script
  was changed. The new path passed read-only Alembic check on the isolated test
  database; no test-database migration was run.
- `docs/security/evidence/auth-cutover-result.json`: actual stages, failure,
  fresh backup checksum and post-stop read-only state.
- Runner syntax and git diff whitespace checks passed. Regression fixtures were
  not rerun after the failed final gate. Earlier 182/12-pass rehearsal results are
  historical evidence, not new cutover results.

The next attempt must correct the control-connection choice and explicitly handle
the retained read-only maintenance setting. Preserve the fresh backup, reverify
source/state/hashes and the effective barrier, and use a held read-write migration
connection only after that gate passes. Existing local migration approval remains
in force within its conditions; no new migration approval is requested. Do not
blindly rerun this single-use runner in its current form.

## Previous attempt — unidentified connection blocked maintenance

Date: 15 November 2026. **NO-GO; migration not executed.**

The owner's authorization was read from the attached Approved Local Database
Cutover request. It explicitly permits the original local 0004 → 0008 migration
and the two documented order conversions. That approval remains valid within its
stated conditions; no repeated migration approval is being requested.

The same request explicitly says: "Establish an effective write-free maintenance
window. A one-time session check alone is insufficient" and "If the maintenance
window or database identity cannot be verified, STOP."

## Completed evidence review

Read the root-cause, rehearsal and final rehearsal reports, and actual migration
scripts 0005–0008. Prior evidence records restored five users/three orders,
successful 0004 → 0008 rehearsal, exactly two LEGACY conversions with matching
audit events, registration 201/login 200/wrong-password 401, 182 passing database
tests and 12 passing guard tests. These are earlier rehearsal results, not results
of this cutover attempt.

Git HEAD is still 5da76c8, the recorded rehearsal baseline. No Alembic working-tree
differences were found. Each 0005–0008 script was independently compared with its
5da76c8 Git content after line-ending normalization; all match. Current normalized
SHA-256 values are retained in `docs/security/evidence/auth-cutover-preflight.json`.

## Current source and failed gate

Read-only PostgreSQL checks returned:

- Server **127.0.0.1:5432**, database **whatnot_app_dev**.
- Revision **0004**, **5 users**, **3 orders**: 2 DELIVERED and 1 PLACED.
- No prepared transactions.
- One other local client: backend PID **17628**, client port **59791**, state
  **idle**, no open transaction, using the application's role.
- Connections are allowed; database connection limit is unrestricted. No effective
  connection/write barrier has been established.

An idle connection alone is not evidence of a current writer or a reason to fail
a consistent-snapshot rehearsal backup. This approved original-database cutover
has a stricter requirement: prevent application writes from resuming while the
backup/migration boundary is established. The remaining session can resume writes,
and its owning client/process could not be identified through the available local
socket/process inspection. It was not presumed to be an authorized application
writer and was not automatically terminated.

No FastAPI listener was returned by the port inspection, but this is not sufficient
proof that every application/worker writer is stopped or cannot restart. No process
was stopped based on an unverified association.

## Actual execution results

| Item | Result |
| --- | --- |
| Original database migration command | Not executed |
| Migration exit status | Not applicable |
| Fresh cutover backup | Not created; stopped before this stage |
| Revision before/after inspection | 0004 / 0004 |
| User/order counts | 5 users, 3 orders; unchanged aggregates |
| Order conversions/audit inserts this attempt | None |
| Live authentication verification | Not run |
| Regression tests this attempt | Not run |
| Database/schema/credential changes | None |
| Sessions/processes terminated | None |
| Deployment/commit/push | None |

The previous backup was not overwritten. Its SHA-256 was rechecked and remains
`4e3ea42158673f1ee355150b083e41bd72f35ffd1d39006073e4a15d8135708b` at
`C:\Users\DELL\AppData\Local\Temp\WhatNotRecovery-321h5wu2\original-0004.dump`.
It is not a fresh cutover backup.

## Required next step

Identify and close the remaining local database client normally, and stop known
backend/worker writers and their automatic restarts. Establish an enforced
maintenance barrier that permits only the controlled backup/migration connections;
then verify it before taking the fresh cutover backup. Do not terminate unrelated
sessions automatically or infer quiescence from a single empty session snapshot.

Once that condition can be verified, continue under the existing approval with
fresh backup verification, the final source/data/script gate, pinned upgrade to
0008, read-only integrity checks, local server/authentication checks and isolated
regressions. No migration success or authentication fix is claimed here.
