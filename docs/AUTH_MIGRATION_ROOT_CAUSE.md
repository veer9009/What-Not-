# Login/registration 503: root cause and migration safety review

Date: 14 November 2026. Repository baseline: 5da76c8 plus the existing uncommitted
security/location work. Status: diagnosis complete; remediation awaiting approval.

## Conclusion and confidence

**Confirmed:** the current backend and its currently configured local database
are incompatible. This is more than an Alembic version-number mismatch: read-only
queries prove that current ORM projections reference missing schema objects, and
the actual application exception handler maps those exceptions to HTTP 503.

**Not independently confirmed:** the exact database/settings snapshot used by the
previously running FastAPI process. No listener on port 8000 was observed during
this investigation. The reported historical requests were not replayed. Once the
server is started, its target/configuration must be checked before declaring the
historical issue fully resolved.

No schema/data/credential changes, migrations, backups, restores, live auth requests,
server restarts or deployments were performed. Existing application/migration files
were left unchanged. No current user records, password hashes, emails or database
connection strings were returned by the diagnostic.

## Read-only evidence

`docs/security/diagnose_auth_schema.py` uses the same Settings class as the app,
loads backend/.env with process-environment precedence, refuses non-loopback targets
and sets PostgreSQL default_transaction_read_only=on at connection startup. It
checks transaction_read_only before probing. Statements have a 5-second timeout
and a 2-second lock timeout. Failing probes use separate connections/transactions.

| Check | Actual result |
| --- | --- |
| Configured environment | development |
| Authentication quotas | enabled |
| Beta email allowlist | empty in current local development settings; no email values printed |
| JWT signing key | present; value never printed |
| Database read-only enforcement | on |
| Connected database name matches configured target | true; name not printed |
| Applied revisions | 0004 |
| Repository head | 0008, single linear chain |
| Default-schema table count | 8 |
| User count | 5; no rows/identities retrieved |
| Existing order status aggregate | 2 DELIVERED, 1 PLACED; no IDs/contact data retrieved |
| Current User projection, LIMIT 0 | ProgrammingError / UndefinedColumn / SQLSTATE 42703 |
| Current RequestQuota projection, LIMIT 0 | ProgrammingError / UndefinedTable / SQLSTATE 42P01 |
| Installed storage-error handler, invoked in memory with each actual exception | HTTP 503, generic Storage operation is unavailable |
| Running API listener on local port 8000 | none observed |

The diagnostic does not INSERT a quota or submit a registration/login. LIMIT 0
validates column/table references without fetching user records. Its handler check
does not involve an HTTP request or change the database. Retained redacted evidence:
`docs/security/evidence/auth-schema-diagnosis.json`.

## Request failure chain

1. `backend/app/api/routes/auth.py:24` and `:33` check the signing key and call
   `admit_auth` before AuthService registration/login.
2. `auth.py:12–17` checks admission, then source/email quotas.
3. `backend/app/services/abuse.py:34–42` enables quotas in development/production;
   `:17–29` performs an upsert into request_quotas on an independent connection.
4. request_quotas is absent at 0004. It is created by
   `backend/alembic/versions/0008_beta_abuse.py:12`. With the observed configuration,
   this is the first schema failure expected for an admitted, valid auth request.
5. `backend/app/api/errors.py:49–52` catches SQLAlchemyError, emits
   storage_operation_failed with its exception class, and returns sanitized 503.

There is a second independent failure even if quotas are bypassed:

- `backend/app/models/user.py:25–26` maps phone_verified_at/email_verified_at.
- `backend/app/repositories/users.py:28` selects the complete User entity for email
  lookup, including those columns, in both login and registration.
- Both columns are absent at 0004 and added by `0008_beta_abuse.py:18–19`.
- That query raises UndefinedColumn, which follows the same 503 handler path.

Thus SELECT 1 and TCP connectivity can pass while authentication fails. The
process-health endpoint does not access the DB; OPTIONS is handled by CORS before
the failing business path. A valid signing key does not establish schema readiness.
The frontend message is its sanitized fallback for 503, not evidence of a frontend
geolocation or CORS failure.

The logger currently omits exception SQLSTATE/object names from ordinary console
formatting. Its generic event alone cannot distinguish missing schema from other
SQLAlchemy failures. No verbose SQL/parameter logging was enabled for diagnosis.

## Pending migration review

| Revision | Upgrade changes | Existing-data impact / locking | Rollback limitations |
| --- | --- | --- | --- |
| 0005 | Creates audit_events, notifications, email_outbox and indexes; adds four nullable order lifecycle columns and deadline index; replaces order-status check | Updates existing order states and inserts migration audit rows. ALTER TABLE/constraint/index work can block concurrent requests. | Downgrade locks related tables and refuses populated lifecycle/events; planned transformation itself creates evidence that blocks downgrade. |
| 0006 | Creates six property tables, constraints/indexes; adds capacity to the newly created, empty property_listings table | No intentional rewrite of existing users/orders. Adding a non-null column is to a new empty table, not an existing populated property table. Unexpected pre-existing object names or insufficient DDL privileges can fail the upgrade. | downgrade always raises until an explicit retention/export plan exists. |
| 0007 | Creates six Creative tables, constraints/indexes | No intentional rewrite of existing users/orders. New tables reference existing users through foreign keys. | Downgrade locks tables and refuses when any Creative records exist. |
| 0008 | Creates request_quotas and its window index; adds two nullable user verification timestamps | Existing user rows receive NULL verification timestamps; existing credential/identity values are not intentionally changed. Auth thereafter needs quota table write privileges. | Refuses when verification evidence exists; otherwise drops columns/counters and resets abuse history. |

Upgrade bodies do not intentionally delete existing business rows or drop populated
business tables. This does not make them risk-free. Revision 0005 deliberately
changes business meaning, and all DDL needs a tested backup/recovery path. The
current migration scripts do not provide a safe automatic full downgrade to 0004.

### Exact 0005 effect on the currently observed data

`0005_beta_foundation.py:57–63` would:

- Map the **two DELIVERED orders to COMPLETED**, with completion_source=LEGACY.
  It does not fabricate buyer consent or delivered/completed timestamps.
- Add two ORDER_MIGRATION audit rows with actor_type=MIGRATION and the original/new
  status mapping. Users must not interpret LEGACY as buyer-confirmed completion.
- Leave the one PLACED order's status unchanged.
- Map any AWAITING_BUYER_CONFIRMATION orders to DELIVERED with a deadline of migration
  time plus 24 hours and source MIGRATION. None were found in this read-only snapshot.

These counts are a snapshot, not a reservation. Recompute them after writers are
stopped and before migration. The two existing order conversions require review
and explicit approval. The current code and workers expect the new lifecycle;
leaving them on an old schema or mixing old/new releases is not a safe workaround.

## Configuration consistency review

- The app constructs Settings once during app creation (`backend/app/main.py:13–14`).
  Its engine is initialized lazily and cached (`api/dependencies.py:19–24`).
- Both app and Alembic normally use `core/config.py:12` backend/.env and the
  DATABASE_URL alias at `:77–78`. Environment variables override file settings.
- `backend/alembic/env.py` can instead receive an explicit programmatic URL in
  config.attributes; isolated tests use this deliberate override.
- The fresh diagnostic confirmed its target name equals its resolved configuration.
  This does not prove equality with the stopped server's past process environment.
- Before an approved change, verify the exact project/venv/process command and
  effective DB target privately. Do not paste a connection URL/password into logs.
  Restart only the user's own reviewed backend process after configuration/schema
  alignment; changing .env does not update an already-created app/engine in memory.

## Safe remediation plan — approval gates

### Gate A: approve backup and restored-copy rehearsal first

1. Confirm the intended local application DB privately and verify its current
   revision/status counts again. Record server/client versions, object owners and
   runtime/migration privilege requirements without exposing credentials.
2. Stop/drain app writers and any workers for a coherent cutover snapshot; the
   observed port was idle, but do not assume that excludes every writer.
3. Create a full custom-format pg_dump backup to an access-restricted location
   outside the repo/cloud-synced source tree. Protect the archive because it contains
   personal data and password hashes. Do not place credentials on the command line.
4. Check dump exit status/archive listing and restore it to a separately named,
   isolated disposable PostgreSQL target. An archive listing alone is not a restore
   test. A single-database dump does not back up cluster-wide roles/tablespaces;
   record what recovery needs. See [pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html)
   and [pg_restore](https://www.postgresql.org/docs/17/app-pgrestore.html).
5. With its target explicitly verified, rehearse the exact 0004 → 0008 chain only
   on that restored copy. Keep SMTP/workers disabled there. Use explicit test/clone
   configuration so no inherited original DATABASE_URL can redirect the rehearsal.
6. Validate table/column/constraint/index changes, preservation of existing user
   identities/password hashes, the expected two LEGACY conversions/audit records,
   unchanged PLACED order, and sequence/foreign-key integrity. Measure locks/runtime.
7. Exercise synthetic registration/login and ownership/quotas on the clone in
   development-style quota-enabled configuration. Run existing isolated migration,
   authentication, authorization and full backend tests after migration execution
   is authorized. Do not use test mode as proof of production quota behavior.

### Gate B: separately approve the original-database upgrade

Only after backup restore/rehearsal results and the two order conversions are
reviewed, approve applying the reviewed chain to the original intended DB.

1. Take the final verified cutover backup and reconfirm there are no writers.
2. Confirm applied revision 0004 and repository head 0008. Apply the pinned approved
   target revision 0008, not an unreviewed future head.
3. Verify revision 0008, Alembic metadata agreement, required runtime privileges,
   preserved data and the approved lifecycle mapping before reopening writes.
4. Start/restart the exact backend with reviewed target settings; check readiness,
   then complete authentication/registration/browser and rate-limit verification.
5. If verification fails, keep writers stopped. Prefer a forward repair or restore
   to a separately validated recovery target. Do not blindly downgrade or overwrite
   the original with a restore; that requires its own explicit approval. Preserve
   any post-backup writes and account for already-sent email if applicable.

Do not stamp head without executing the schema changes, hand-create only the quota
table, disable abuse controls, or rename/remove mapped columns to hide this mismatch.
These would leave other current modules incompatible or weaken security.

## Verification commands and expected results

Read-only commands actually used, from the repository root:

```powershell
& .\backend\.venv\Scripts\python.exe docs/security/diagnose_auth_schema.py
& .\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads
& .\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini history
```

heads/history inspect revision scripts; they do not execute upgrade/downgrade.
Diagnostic success means the check completed, not that the schema probes passed.
Current expected output is revision 0004 and both FAIL probes/503 mappings. After
an approved correct upgrade, expect revision 0008, no model column/table drift,
five original users preserved (before approved new registrations), and PASS probes.

Proposed migration command, **NOT EXECUTED; only after Gate B approval and target
verification**, from backend: `.\.venv\Scripts\python.exe -m alembic upgrade 0008`.
Follow with read-only `alembic current`, `alembic heads`, `alembic check` and the
diagnostic against that same reviewed target. The expected chain is documented by
the repository and [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

After approved writes/restart:

- GET /api/v1/health → 200 (process only); GET /api/v1/ready → 200 (DB/schema).
- Valid existing-user login → 200; wrong credentials → 401 rather than 503.
- Approved synthetic registration → 201; duplicate identity → 409; invalid body → 422.
- GET /auth/me with the returned bearer → expected own identity; expired/invalid
  token → 401. Do not copy live tokens/passwords into reports.
- A bounded quota test on an isolated target → 429 with Retry-After; never run a
  high-volume abuse test or exhaust the original users' quotas for verification.
- No new storage_operation_failed event during the successful scenarios; no raw
  SQL parameters or exception inputs exposed to the client.

The full backend/persistence suite was **not rerun in this investigation** because
its fixtures execute migrations. Previous 659-pass results were on fresh isolated
head schemas and do not certify this existing 0004 DB. Only the inspected non-DB
auth/security/schema/settings tests were run in this investigation: **38 passed
in 3.26 seconds**. No persistence fixtures or migrations were executed.

## Command training

| Command | WHAT | WHY | WHEN | HOW | EXPECTED OUTPUT | COMMON FAILURES / verify success | Category |
| --- | --- | --- | --- | --- | --- | --- | --- |
| git status --short / focused Get-Content and rg | Inspect existing edits/source | Preserve work and trace failure | Before action | Read Git/file content; no DB statements | Existing location/security changes and actual auth/migration code | Wrong path/glob; check exact filenames and source lines | UNDERSTAND / LOOK UP |
| diagnose_auth_schema.py | Runs constrained read-only schema checks | Prove missing objects without auth writes | Before remediation and after approved upgrade | Same Settings resolution; loopback only; PG-enforced read-only; LIMIT 0 ORM projections | Redacted revision/drift/SQLSTATE and handler status | Connection/config/privilege/timeout errors; inspect safeguards and per-probe status, not exit alone | PROJECT-SPECIFIC / DON'T MEMORIZE |
| alembic -c backend/alembic.ini heads / history | Reads repository revision graph | Verify pinned migration chain | Before planning | -c selects config; commands inspect scripts without upgrade | Single 0008 head and linear 0004→0008 | Wrong venv/config/path; confirm printed revision graph | UNDERSTAND / LOOK UP |
| Get-NetTCPConnection -LocalPort 8000 -State Listen | Looks for local API listener | Determine whether live runtime can be verified | During config investigation | OS socket metadata; process path inspected without full command-line/credential output | Listener/process or no listener observed | Permissions/platform limitations; cannot infer past server settings | UNDERSTAND / LOOK UP |
| pytest -q -W error tests/test_auth_security.py tests/test_auth_schemas.py tests/test_beta_settings.py | Runs only inspected non-DB tests | Check auth contracts/settings without migrations | During read-only phase | Explicit files avoid persistence fixtures; warnings fail | Passing summary; no migration/DB writes | Environment/test failures; read exact summary and don't claim full persistence coverage | PROJECT-SPECIFIC / DON'T MEMORIZE |

No approvals have been inferred from this report. Backup/rehearsal and any original
database upgrade remain pending the user's explicit authorization.
