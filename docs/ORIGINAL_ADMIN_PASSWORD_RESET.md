# Existing original administrator password reset — preparation only

Status: **PREPARED; RESET NOT EXECUTED.** Separate owner approval is required
before using `--execute`. No QA provisioning script is involved.

## Verified target and implementation

On 2026-11-15, the script's default read-only check exited **0**:

```text
READ-ONLY VERIFIED: 127.0.0.1:5432 / whatnot_app_dev / OID 41069 / revision 0008
Account verified: admin@example.com / active ADMIN. No password was read.
CHECK ONLY: no reset executed.
```

An independent read-only schema inspection verified PostgreSQL 17.11, primary
server, database owner matching the configured application role, revision 0008,
and exactly one matching active ADMIN. `public.users.password_hash` is a non-null
`varchar(255)`. Its other columns are id, name, email, phone, role, is_active,
created_at, updated_at, phone_verified_at and email_verified_at. There are no
non-internal triggers on this table. No stored password hashes were fetched.

The existing `backend/app/core/security.py:hash_password()` uses Argon2id with
`RFC_9106_LOW_MEMORY`. The prepared script imports this function directly. Password
length 8–128 matches registration validation; whitespace and Unicode are preserved.
It does not use ORM UPDATEs: `TimestampMixin.updated_at` has an SQLAlchemy on-update
expression, so parameterized SQL updates only password_hash and preserves timestamps.

## Safeguards

- No database, server, email or role overrides. Configuration must specify local
  development, loopback port 5432 and the original database. Connection is pinned
  to IPv4 loopback; database OID, server major version, primary status and ownership
  are verified before reading account records and immediately before writing.
- Default mode uses a PostgreSQL-enforced read-only transaction. It never asks for
  a password and never executes the reset transaction.
- Write mode requires `--execute`, backup path, previously trusted SHA-256, an
  interactive terminal, the exact typed phrase below and two hidden password
  entries. Hidden-input fallback that could echo a password is rejected.
- Before writing, validate backup magic, full-file SHA-256 and successful
  `pg_restore --list`, including original database name and users table data.
  Backup verification repeats immediately before UPDATE. The existing backup's
  path/checksum were not supplied for this preparation; its integrity is not
  independently claimed here. Archive listing does not replace a test restore.
- One write transaction locks every existing public base table against concurrent
  writes, then selects the account `FOR UPDATE`. Five-second lock timeout and
  fifteen-second statement timeout fail closed. Stop application writers before
  an approved execution. The script never terminates processes or sessions.
- Check exact revision, users column set, hash column type and absence of custom
  users triggers. Recheck exact email, ADMIN role, active status and preflight ID.
  Only one parameterized `UPDATE ... SET password_hash` is permitted; require
  exactly the expected returned ID and a successful new-hash equality check.
- Before commit, compare opaque database-side SHA-256 digests of all public base
  table contents. Exclude only the target password_hash; include its timestamps,
  profile fields and all other accounts' hashes. No digest or hash is printed.
  The read-only digest SQL was exercised successfully against **24 public tables**.
- Any mismatch or exception rolls back. Errors suppress driver details that could
  contain secrets. If connection/commit outcome is uncertain, stop and investigate;
  do not blindly rerun. No user creation, migration, restoration or QA access.

## Commands

Safe read-only verification, usable now:

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
& .\.venv\Scripts\python.exe ..\docs\security\reset_original_admin.py
if ($LASTEXITCODE -ne 0) { throw 'Read-only verification failed; stop.' }
```

**Proposed execution, only after separate explicit approval:**

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
$adminBackupPath = Read-Host 'Previously verified original custom-format backup path'
$adminBackupSha256 = Read-Host 'Previously recorded trusted SHA-256'
& .\.venv\Scripts\python.exe ..\docs\security\reset_original_admin.py --execute --backup $adminBackupPath --backup-sha256 $adminBackupSha256
if ($LASTEXITCODE -ne 0) { throw 'Reset did not complete successfully; verify outcome before any retry.' }
```

At the local confirmation prompt type exactly:

```text
RESET EXISTING ADMIN whatnot_app_dev OID 41069
```

Enter and confirm a new unique password at the two hidden prompts. Never pass it
through command arguments, environment variables, files, screenshots or chat.
The script reads the existing private database configuration without displaying it.
Do not launch under the QA environment or a SQL-parameter-logging debugger.

## Automated verification

From `backend`:

```powershell
& .\.venv\Scripts\python.exe -c "import sys,pytest;sys.path.insert(0,'../docs/security');raise SystemExit(pytest.main(['-q','../docs/security/test_original_admin_reset.py']))"
& .\.venv\Scripts\python.exe -m pytest -q tests/test_auth_security.py tests/test_auth_schemas.py
```

Reset-specific tests: **32 passed**, exit 0. The reset tests mock transactions and connections; they do not connect to any
database. They cover incorrect identity, wrong/missing/duplicate/inactive account,
account-ID change, one-account success with the actual password hasher, exception
and preservation-check rollback, wrong update counts/IDs, failed hash readback,
backup failures, hidden-input safety, read-only default and execution guards.
Existing authentication security/schema tests: **30 passed**, exit 0. No database
fixture tests were run; real PostgreSQL password-update/rollback is not claimed.

## After an approved execution

1. Require exit 0 and the `COMMITTED` message, which is emitted only after commit.
   The transaction checks exact one-account change and preservation before commit.
2. Rerun default read-only verification. Database identity, revision and account
   metadata must remain unchanged. No stored password or hash needs to be printed.
3. When the original backend is confirmed compatible with revision 0008, the owner
   can privately sign in as admin@example.com with the new password. Do not capture
   request bodies or response tokens in shared evidence. A reset does not resolve
   any separate schema/application mismatch; the current radius implementation has
   QA-only revision 0009 requirements. No original migration is authorized here.
4. Existing JWT access tokens are stateless and are **not revoked** by a password
   reset. Their issuance configuration permits 1–60 minute lifetimes; allow existing
   sessions to expire or separately approve a revocation strategy before treating
   the reset as session invalidation. Do not change signing keys automatically.

No password reset, new account, schema change, QA/production connection, commit,
push or deployment occurred during preparation.
