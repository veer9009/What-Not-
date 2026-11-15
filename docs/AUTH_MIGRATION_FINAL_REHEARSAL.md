# Protected authentication migration rehearsal

Date: 15 November 2026. Original database migration is not authorized by this report.

## Targets and controls

- Original: `whatnot_app_dev`; all diagnostic connections enforce PostgreSQL
  default_transaction_read_only=on. No original schema/data writes were executed.
- Restored rehearsal: `whatnot_rehearsal_20261115_a7e394c2`, verified OID **49264**.
- Separate tests: `whatnot_tests_20261115_a7e394c2`, verified OID **49265**.
- Both targets were verified empty and owned by the same role as the original.
- No server startup, database creation/drop, unrelated cleanup, credential change,
  deployment, commit or push was performed in this continuation.

Restore was one psql transaction with ON_ERROR_STOP, an in-session name/OID/owner
guard and an explicit approved database. Archive SQL was generated with pg_restore
--no-owner --no-privileges, without --clean or --create. No original database name
was used as a restore or migration target. The trusted archive checksum was checked
before restore, and restored rows matched the read-only source snapshot in memory.

Alembic receives a programmatic explicit target URL. A SQLAlchemy statement listener
verifies database name/OID/ownership before SQL execution. The separate test runner
accepts only the test database. In an aborted transaction, PostgreSQL rejects even
SELECT: the test guard permits only savepoint rollback on the already verified
physical test connection to recover; it permits no business write in that state.

## Backup and restore evidence

Archive, **31,480 bytes**:

```text
C:\Users\DELL\AppData\Local\Temp\WhatNotRecovery-321h5wu2\original-0004.dump
```

SHA-256, independently reverified:

```text
4e3ea42158673f1ee355150b083e41bd72f35ffd1d39006073e4a15d8135708b
```

pg_restore archive listing exited **0**. SQL extraction and transactional psql
restore succeeded; psql restore exit **0**. Restored revision **0004** with exact
original table-row agreement:

| Table | Rows |
| --- | ---: |
| users | 5 |
| orders | 3 |
| order_items | 3 |
| addresses | 1 |
| products | 3 |
| product_images | 1 |
| seller_profiles | 2 |
| alembic_version | 1 |

The backup is a full single-database archive, not a cluster-wide role/tablespace
backup. Ownership/ACLs remain in the archive but were intentionally omitted during
restore into the preowned target. Keep this access-restricted archive; TEMP cleanup
can remove it. Source data can change after backup; it is not a future cutover backup.

## Rehearsal migration and validation

Executed only against the rehearsal database:

```text
Running upgrade 0004 -> 0005
Running upgrade 0005 -> 0006
Running upgrade 0006 -> 0007
Running upgrade 0007 -> 0008
```

Migration completed in **1.578 seconds**. Final rehearsal revision **0008**.
Alembic check: **No new upgrade operations detected.**

- request_quotas and both nullable user verification timestamp columns are present.
- All **five original users**, including existing identity/password fields, match
  the original; verification fields remain NULL. No private values were reported.
- Exactly **two DELIVERED orders → COMPLETED / LEGACY**; no buyer consent or
  lifecycle timestamps were fabricated. The **one PLACED order is unchanged**.
- Exactly **two matching ORDER_MIGRATION audit events** have MIGRATION actor,
  DELIVERED/COMPLETED statuses and reason 0005_LEGACY_MAPPING.
- All other original business rows match. All mapped tables/columns are present;
  **0 invalid constraints**, **0 invalid indexes**, **22 sequences checked**.

Development-mode API smoke checks used the explicit rehearsal URL, enabled quotas,
a new ephemeral signing key, SMTP disabled and no workers. Actual statuses:

| Check | HTTP |
| --- | ---: |
| Readiness | 200 |
| Synthetic buyer registration | 201 |
| Duplicate registration | 409 |
| Invalid registration body | 422 |
| Synthetic buyer login | 200 |
| Authenticated identity | 200 |
| Wrong password | 401 |
| Invalid token | 401 |

Two quota rows were created. The rehearsal now contains **six users**: five restored
originals plus the synthetic smoke account. Existing-user lookup queries passed;
existing users' plaintext passwords were not available or requested, so their
individual browser logins were not attempted. No precise identity/password/token
values were printed.

## Test harness history and scope

The selected nine persistence files cover authentication, transaction commit/
rollback, abuse controls/concurrency, authorization, constraints, order creation,
discovery, prior security audit checks and request-session handling. This is not
the full backend suite. Test files were copied to the protected recovery directory;
source tests and source fixtures were not changed. Only the copied database fixture
was replaced. Server-start and database-create fixtures fail if requested.

The initial in-process pytest call stopped before collection on an assertion-rewrite
warning. The tests-only runner uses --assert=plain, preserving Python assertions,
and -W error. Subsequent harness attempts exposed:

- **18 passed, 1 fixture error**: missing parent HTTP-client fixture after relocation;
  the temporary harness now includes that fixture.
- **87 passed, 1 failure, 1 teardown error**: the guard tried SELECT during an
  intentionally aborted constraint-test transaction, preventing rollback. Recovery
  rollback was corrected as described above. The failed run is retained in
  `docs/security/evidence/auth-database-tests-harness-failure.json`.
- A tests-only launch stopped before collection on an UnboundLocalError from a
  local name shadowing the SQL helper; that harness name was corrected.

Only four test quota counters survived the rollback fixtures. They were cleared
through the guarded test connection before rerunning. No original or rehearsal
data was reset. Final test logs/XML use separate protected directories.

Commands used, from repository root:

```powershell
& .\backend\.venv\Scripts\python.exe docs/security/rehearse_existing_server.py
& .\backend\.venv\Scripts\python.exe docs/security/run_existing_server_tests.py
& .\backend\.venv\Scripts\python.exe docs/security/verify_existing_rehearsal.py
```

The restore runner is intentionally single-use: it refuses populated targets.
An attempted repeat was refused at preflight without writes. No restore or migration
was repeated. Use the tests-only and read-only verifier commands for their stated
purposes; do not automatically rerun the restore command.

## Final outcome and recommendation

**GO for a separately approved local original-database migration**, subject to
fresh cutover checks below. This is not approval to execute it or to deploy to AWS.

- **182 passed**, **0 failures**, **0 errors**, **0 skipped**, in **55.278 seconds**;
  test command exit **0**, **2,034 SQL statements guarded**, approved test OID 49265.
- The original's complete public-table row snapshot matched before/after the final
  test run. It remains at **0004**, with five users, two DELIVERED orders and one
  PLACED order. The original authentication schema mismatch therefore still exists.
- Targeting/preflight unit tests: **12 passed in 2.82 seconds** before the rehearsal;
  final repeat with warnings treated as errors: **12 passed in 1.74 seconds**.
- Fresh final read-only verification: `docs/security/evidence/auth-rehearsal-verified.json`.
- Final database test evidence: `docs/security/evidence/auth-database-tests.json`.
- Combined final evidence: `docs/security/evidence/auth-rehearsal-final.json`.
- Final protected log:
  `C:\Users\DELL\AppData\Local\Temp\WhatNotRecovery-321h5wu2\guarded-tests-1794682546258805500\pytest.log`
  and adjacent `tests.xml`.

Before approving the original migration: stop application/worker writers for the
cutover, reconfirm revision/data counts and intended backend configuration, take a
fresh protected backup, explicitly approve the two LEGACY order conversions, and
pin the reviewed upgrade target to 0008. Check runtime grants, revision/readiness
and browser login/registration afterward. No browser-level verification against the
unchanged original was claimed. Do not rely on an automatic downgrade: 0005 records
lifecycle evidence, and 0006 refuses downgrade without an explicit retention plan.

The rehearsed development schema/authentication behavior passes. Production HTTPS,
AWS configuration and the separate security-audit deployment blockers are outside
this rehearsal; it does not establish deployment readiness.
