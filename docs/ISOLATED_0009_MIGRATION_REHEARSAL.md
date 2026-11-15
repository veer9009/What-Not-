# Isolated 0008 → 0009 migration rehearsal

Date: 15 November 2026. **STOP / NO-GO: post-restore validation incomplete. Neither migration ran.**

The source was accessed with PostgreSQL-enforced read-only connections. No original or Chrome QA writes, service restarts, credential changes, migrations, deployments, commits or pushes were performed. Both administrator-created databases were independently verified empty before restore. No database or backup was deleted.

## Verified database state

Server: TCP `127.0.0.1:5432`, PostgreSQL 17 primary. Database names, OIDs and application-role ownership were checked through the actual connections.

| Database | OID | Final verified state |
|---|---:|---|
| `whatnot_app_dev` | 41069 | Protected source, revision `0008`; all 24 table fingerprints unchanged |
| `whatnot_0009_rehearsal_20261115_f24a8f87` | 51678 | Restored backup, revision `0008`; not migrated |
| `whatnot_0009_rollback_20261115_f24a8f87` | 51679 | Empty, zero public tables; not restored or migrated |

Restored and source counts: **6 users, 2 seller profiles, 3 products, 1 address, 3 orders**. Private server-side table fingerprints match for all 24 tables, including user IDs, roles, active statuses, password hashes and business records. No individual account values or password hashes were printed. Final original comparisons also matched all 24 tables.

## Fresh backup evidence

Fresh archive created after administrator database creation:

```text
C:\Users\DELL\AppData\Local\Temp\WhatNot0009Rehearsal-_danj7tx\whatnot_app_dev-0008-before-0009-d200cb1f.dump
```

Size: **96,098 bytes**. SHA-256:

```text
90f03b591b42dfb92110c80ad19c4bece3bb3885829470adc4f4e4099446c7b8
```

A matching `.dump.sha256` sidecar and private snapshot manifest are in the same user/SYSTEM-protected folder. The previous archive was retained. This folder contains sensitive database backups and private logs; do not publish or commit it. It is under TEMP and is not a durable production backup destination.

| Check | Result | Evidence |
|---|---|---|
| Consistent backup | PASS | Held `REPEATABLE READ READ ONLY` transaction; exported snapshot supplied to `pg_dump --snapshot` |
| Custom archive | PASS | `pg_dump` exit 0; magic/checksum verified |
| Archive listing | PASS | `pg_restore --list` exit 0; expected 24 table-data entries |
| Full archive decoding | PASS | `pg_restore --file NUL` exit 0 |
| Rehearsal restore command | PASS | `psql` exit 0, one transaction, identity guard on same connection, `ON_ERROR_STOP=1` |
| Restored data/revision | PASS | `0008`; all 24 table fingerprints match snapshot |
| Restored columns/indexes | PASS | Exact metadata comparison |
| Restored CHECK definitions | FAIL validation | 12 textual differences; operation stopped |

## Why execution stopped

The restore itself succeeded. The subsequent strict `pg_get_constraintdef()` string comparison rejected 12 CHECK definitions. For example, the source represents a status check as:

```sql
CHECK (((status)::text = ANY ((ARRAY['ACCEPTED'::character varying,
  'DELIVERED'::character varying, 'COMPLETED'::character varying])::text[])))
```

The restored definition is rendered as:

```sql
CHECK (((status)::text = ANY (ARRAY[('ACCEPTED'::character varying)::text,
  ('DELIVERED'::character varying)::text, ('COMPLETED'::character varying)::text])))
```

The inspected example moves casts from the array to its elements. This suggests expression normalization on dump/restore rather than lost data. **Semantic equivalence of all 12 constraints has not yet been established**, so the guard was not bypassed or loosened. The sanitized JSON evidence lists every affected constraint.

The driver exited **1**, reporting `RuntimeError` at `atomic restore: whatnot_0009_rehearsal_20261115_f24a8f87`; read-only follow-up localized it to the post-restore constraint comparison. No automatic retry occurred. The existing resume command intentionally rejects a nonempty destination and must not be rerun against this restored database.

## Migration and runtime verification

Reviewed migration: `backend/alembic/versions/0009_public_discovery.py`.

SHA-256:

```text
25f693303c54011f36ca282c017e03fccd097fe662719d7d6ae5c2f86261856d
```

It adds four nullable seller public-discovery fields and three CHECK constraints. It does not backfill consent or coordinates. Its downgrade refuses automatic reversal. Existing data must remain unchanged and new fields NULL when eventually rehearsed.

| Required gate | Result |
|---|---|
| Migration checksum review | PASS |
| Rehearsal migration `0008 → 0009` | NOT RUN |
| Four columns / three constraints / NULL public consent verification | NOT RUN |
| Rehearsal application readiness | NOT RUN |
| Rehearsal seller/discovery query compatibility | NOT RUN |
| Transaction rollback probe on OID 51679 | NOT RUN |
| Original account and business-data preservation | PASS |

## Exact commands and outcomes

From the repository root, safeguard tests:

```powershell
& .\backend\.venv\Scripts\python.exe -m pytest .\docs\security\test_0009_rehearsal.py -q
```

**28 passed in 3.89s.** These are guard unit tests, not evidence that the database migration succeeded.

Executed rehearsal orchestration:

```powershell
& .\backend\.venv\Scripts\python.exe -u .\docs\security\rehearse_0009_migration.py --resume 'C:\Users\DELL\AppData\Local\Temp\WhatNot0009Rehearsal-_danj7tx\manifest.json' --rehearsal-oid 51678 --rollback-oid 51679 --refresh-backup
```

Exit **1** after successful fresh backup and restore, at post-restore validation. Internally the restore used `pg_restore --no-owner --no-privileges --file -` followed by `psql --no-password --no-psqlrc --single-transaction --set ON_ERROR_STOP=1 --file -`. Connection credentials were provided privately, never in command arguments or report output. The planned migration call `alembic.command.upgrade(config, '0009')` was never reached.

Read-only follow-up checked actual identities, versions, counts, all table fingerprints, column/index metadata and constraint definitions. Evidence: `docs/security/evidence/0009-rehearsal.json`.

## Smallest safe next step

Review all 12 source/restored CHECK expressions with a conservative semantic comparison and focused regression tests for legitimate array-cast rewrites and genuinely different constraints. Do not simply ignore constraint differences. Prepare a continuation mode that accepts only the already-restored, privately verified OID 51678 at `0008`, without restoring over it, and still requires empty rollback OID 51679 before its separate restore. Recheck archive checksum, migration checksum, exact identities, source protection and private data preservation immediately before any later mutation.

Execution stopped as required by the explicit stop-on-validation-failure rule. **Owner direction is needed before resuming mutation after this failed gate.** No further database operation was attempted. A successful rehearsal, runtime checks and rollback probe remain prerequisites to recommending the original migration; applying it would require separate explicit approval.
