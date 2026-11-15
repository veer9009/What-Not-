# Prepared QA-only administrator provisioning

15 November 2026. **PREPARED — ACCOUNT CREATION NOT EXECUTED. Separate explicit owner approval is required before --execute.** No administrator exists in the currently inspected QA database. No password has been requested or account inserted by this preparation.

## Target and safeguards

The new tool is separate from production `backend/app/bootstrap_admin.py`, which was not modified. Only `whatnot_chrome_qa_20261115`, OID **50640**, schema **0009**, primary PostgreSQL **17** at **127.0.0.1:5432** is accepted. Database owner/current role must match the privately loaded expected connection role. The target URL is derived with the existing fail-closed QA target helper, pinned to IPv4 loopback; there is no target-name/OID/URL override flag. Configuration may be read privately; no original/development/rehearsal/staging/production database is connected to.

Execution also requires effective development settings, explicit `WHATNOT_QA_ENVIRONMENT=chrome-discovery-v1`, and an explicitly chosen `WHATNOT_QA_ADMIN_EMAIL` distinct from the existing two accounts. These are local QA-only operator settings; production configuration and public registration are unchanged.

Before any user query, the tool verifies database/server identity and revision. Preflight connection enforces read-only mode. Initial roster must be exactly the existing active synthetic BUYER and SELLER, with **zero ADMIN**; totals **2 users / 1 seller / 3 products / 1 address / 0 orders**. Unexpected or inactive users, existing admin, wrong schema/identity, role/owner or counts stop execution.

After approval, --execute requires an interactive terminal and exact confirmation `CREATE QA ADMIN OID 50640`. It prompts locally for name, email, phone and password twice. The prompted email must match explicit QA admission. Password entry uses getpass and fails closed if hidden entry is unavailable; it does not accept credentials in CLI flags, a file or piped stdin. Public registration validation preserves the password and validates contact inputs; the operator tool always supplies literal ADMIN internally, never changes public role rules.

The write uses existing **UserService**, **UserCreate**, **hash_password** and explicit active=True. One outer transaction rechecks identity/zero-admin state before and after acquiring bounded SHARE ROW EXCLUSIVE locks on the five business tables. A second operator or API writer cannot slip between final roster check and insertion. No sessions are terminated; lock timeout is 5 s, statement timeout 15 s. The runtime SQL guard checks physical database name, OID, role, owner, server/version and primary state before each SQL statement.

Before insertion, PostgreSQL computes opaque SHA-256 row-preservation digests for all existing business records. Raw stored password hashes, contact rows or precise locations are not returned for that comparison; digests remain only in memory and are not printed. Before commit, existing non-admin users and the four other business tables must match their original digests; final roster/counts must contain exactly one additional active ADMIN. Any error rolls back the outer transaction. Unique email/phone constraints remain in force. Rerunning --execute refuses any existing admin before prompting/hashing/inserting. A failed insert may advance a PostgreSQL sequence despite record rollback; this does not create an account or alter existing rows.

If commit/connection outcome is uncertain, **do not rerun --execute**. Run read-only verification first and investigate. The tool suppresses exception contents, SQL parameters, passwords, hashes and tokens.

## QA admission change

`run_chrome_discovery_qa.py` still defaults to exactly the original two synthetic accounts. With an explicitly configured QA admin email, startup requires exactly those same two accounts plus exactly one matching **active ADMIN**. It refuses missing/inactive/mismatched/extra administrators. It does not discover and admit arbitrary accounts automatically. Before provisioning, starting with the admin email set intentionally fails because the third account does not yet exist.

The child API allowlist becomes only buyer + seller + that verified admin. Authentication, RBAC, public registration restrictions, quotas, independent QA signing key, loopback binding and database guard remain enabled. Production bootstrap/allowlist protections are untouched. An existing running QA backend must be restarted to load the explicit new admission; its old token becomes invalid after restart.

## Proposed commands — approval pending

Use a normal local PowerShell terminal. Stop **only the QA backend on port 8001** in its own terminal before the approved write; do not stop or connect to original-backed services. Do not run migrations or initialization scripts.

Read-only preflight (no account creation):

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
$env:WHATNOT_QA_ENVIRONMENT = 'chrome-discovery-v1'
$env:WHATNOT_QA_ADMIN_EMAIL = Read-Host 'Approved QA administrator email (not password)'
& .\.venv\Scripts\python.exe ..\docs\security\provision_qa_admin.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: QA verification failed; do not execute provisioning.' }
```

**Only after separate explicit owner approval**, same terminal:

```powershell
& .\.venv\Scripts\python.exe ..\docs\security\provision_qa_admin.py --execute
if ($LASTEXITCODE -ne 0) { throw 'STOP: inspect read-only state; never blindly retry --execute.' }
```

Expected sanitized success: CREATED, QA name/OID/schema, admin_active true, admin_count 1, business counts **3 / 1 / 3 / 1 / 0**. No name/email/phone/password/hash/token is printed by success output; operator input remains local.

## Post-execution verification — also pending approval/execution

```powershell
# Read-only: verifies the sole admin matches the explicitly chosen admission.
& .\.venv\Scripts\python.exe ..\docs\security\provision_qa_admin.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: post-provisioning verification failed.' }
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: QA launcher verification failed.' }
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py --serve
```

Keep both explicit QA environment variables in this local terminal; in a new terminal, reenter them via Read-Host. No credential or admission file is written automatically. Use API `http://127.0.0.1:8001/api/v1`, frontend `http://127.0.0.1:5174/login/admin`, with frontend API base already pinned to 8001. Sign in locally, inspect method/path/status only: login 200, `/auth/me` 200 with role ADMIN, and a read-only pending-products GET 200. Do not approve/reject/delete products as part of provisioning verification. Never share login bodies, tokens, response headers or HAR. No actual admin browser acceptance is claimed yet.

## Verification performed during preparation

All new provisioning tests use mocked sessions/transactions only: **no account was inserted into any database, including temporary/rollback insertion into QA**. Coverage includes active ADMIN/UserCreate/Argon2 success, duplicate refusal, wrong name/OID/server/owner/role/version/primary identity, stopping before user queries, missing QA marker, explicit admission/inactive-account rejection, default read-only mode, service failure rollback, preservation failure rollback and refusal of echoed password fallback.

Executed from backend:

```powershell
& .\.venv\Scripts\python.exe -c "import sys,pytest;sys.path.insert(0,'../docs/security');raise SystemExit(pytest.main(['-q','../docs/security/test_qa_admin.py','../docs/security/test_chrome_qa_launcher.py','tests/test_admin_bootstrap.py','--junitxml=../docs/security/evidence/qa-admin-preparation-tests.xml']))"
```

Initial red run failed because the new provisioning module did not exist. **Final run: 45 passed, exit 0, 8.89 seconds**, including the hidden-prompt fallback test, launcher isolation tests and unchanged production bootstrap safeguard tests. Production bootstrap safeguards were tested without production DB connections.

A separate **read-only** QA inspection exercised the actual server identity, revision, counts and all five preservation-digest SQL queries: exit **0**, transaction_read_only **on**, OID **50640**, revision **0009**, admin_count **0**, business counts **2 / 1 / 3 / 1 / 0**. No digest or credential was emitted. This validates current preconditions/SQL syntax; it does not prove the write/commit path against PostgreSQL. That path remains unexecuted pending approval. No frontend product code changed, so frontend build/tests were not rerun for this Python-only operator preparation.

## Exact changed files

1. `docs/security/provision_qa_admin.py` — prepared read-only/default and guarded interactive write path.
2. `docs/security/qa_admin_policy.py` — explicit QA environment/admission, identity and roster policy.
3. `docs/security/test_qa_admin.py` — new mocked tests; no database connection.
4. `docs/security/run_chrome_discovery_qa.py` — optional verified sole-admin admission and three-user preflight; original two-user mode preserved.
5. `docs/security/evidence/qa-admin-preparation-tests.xml` — test evidence.
6. `docs/QA_ADMIN_PROVISIONING.md` — this procedure and execution/verification instructions.

**Awaiting explicit approval. No account creation, password reset, fixture mutation, migration, original/staging/production access, commit, push or deployment has been executed.**
