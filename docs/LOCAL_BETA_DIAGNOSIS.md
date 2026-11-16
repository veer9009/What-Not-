# Local beta diagnosis — 15 November 2026

The existing local seller-profile flow remains blocked by a schema mismatch.
No migration or business-data write was performed against the application database.
No environment files, credentials, existing migrations, infrastructure, commits,
or remote repositories were changed.

## Confirmed evidence

A PostgreSQL-enforced read-only connection (`SHOW transaction_read_only` = `on`)
reported revision `0008`. Comparing the actual seller table with the ORM showed
four missing columns: `public_discovery_latitude`, `public_discovery_longitude`,
`public_discovery_confirmed_at`, and `public_discovery_consent_version`.
`SellerService.get_by_user()` raised SQLAlchemy `ProgrammingError`, wrapping
psycopg `UndefinedColumn`, SQLSTATE `42703`, with the primary diagnostic:
`column seller_profiles.public_discovery_latitude does not exist`.

An ephemeral locally signed access token for an existing active seller reproduced
HTTP 503 from the running `GET http://127.0.0.1:8000/api/v1/sellers/me`. No token,
password, account identity, query parameters, or private profile values were printed.
`require_user()` succeeds; the subsequent full ORM seller SELECT fails. The lazy
session factory connects correctly. Process health and `/docs` do not validate
schema readiness; `/api/v1/ready` is the relevant schema-readiness endpoint.

## Changes

- `backend/app/api/errors.py`: print the exception class and strictly validated
  five-character SQLSTATE in console logs and structured log fields. Preserve the
  sanitized HTTP 503 response; never log driver text, SQL, parameters, or traceback.
- `backend/tests/test_storage_diagnostics.py`: regression for safe diagnostics.
- `backend/tests/persistence/test_seller_schema_compatibility.py`: reproduce the
  authenticated 503 on a synthetic populated `0008` database, apply `0009` only
  there, check profile reads/edits and absence of automatic public consent.
- This report.

Generated verification artifacts: `local-beta-frontend-results.json` and
`local-beta-frontend-recheck.json` in the project root. The pre-existing untracked
`docs/security/evidence/` directory was preserved.

The diagnostic test failed before the logging change because SQLSTATE was absent.
This logging change does not repair an unmigrated application database.

## Image investigation

There is no file-upload implementation to repair. `SellerPages.tsx` explicitly
states uploads/storage are deferred. The frontend sends JSON `image_url` in
`POST /api/v1/products` or `PATCH /api/v1/products/{id}`. The backend accepts optional
HTTP(S) URLs, rejects credentials in URLs, and stores the primary image URL in
`product_images`. Setting the URL to null removes the primary image. Seller identity
comes from authentication; service ownership checks protect changes. Approved edits
return to PENDING. The browser loads the external URL directly, including the seller
dashboard's `<img>` with `referrerPolicy="no-referrer"`.

There are no supported upload file formats, byte-size limits, upload endpoint,
storage credentials, or generated object-storage URLs. A file-upload attempt to
`/api/v1/uploads` is expected to return 404 (also covered by an existing security
test). URL validation does not verify remote MIME type, size, availability, or
image decoding. A hosted URL must point to an image the browser can load. Actual
file upload remains an unimplemented feature; no storage system was invented.

## Migration plan — not executed against the application database

Migration `0009_public_discovery.py` adds precisely the four missing nullable
columns and three CHECK constraints; it does not backfill private coordinates or
public consent. Keeping the current ORM on `0008` cannot support the seller flow.
Removing the mapped fields or silently fabricating consent would bypass the
current application contract.

1. Stop local writes/workers. Verify the exact intended database identity and
   revision using the existing private connection configuration.
2. Create a fresh backup outside the repository in a durable private directory;
   verify its checksum, archive readability, and restore into a separate database.
3. Resolve the outstanding restored-constraint validation gate documented in
   [the prior rehearsal report](ISOLATED_0009_MIGRATION_REHEARSAL.md). This task did
   not resume or change those existing rehearsal databases. A synthetic test
   cluster does not establish preservation of the user's real restored dataset.
4. Rehearse `0008` → `0009` on that verified restored copy. Compare business data,
   constraints, four initially NULL public fields, readiness, and seller flows.
5. Only after successful rehearsal and separate user authorization, apply the
   reviewed migration to the intended application database. The eventual command,
   from `backend`, is `.\.venv\Scripts\python.exe -m alembic upgrade 0009`.
   **It was not run on the application database.** Verify `alembic current` =
   `0009`, `alembic check`, and `/api/v1/ready` before resuming writes.
6. The migration refuses automatic downgrade. Recovery requires a verified backup
   and coordinated code/database restore; account for any writes after backup.

## Executed checks

Backend commands below ran from `backend`; frontend commands ran from the root.

| Command | Result | Database / transport |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/persistence` | PASS, 334 tests on final code (43.53 seconds); earlier baseline 333 passed | Unit tests, stubs/mocks; no live PostgreSQL |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_storage_diagnostics.py` before fix | Expected RED: 1 failed because `record.sqlstate` was absent | Synthetic SQLAlchemy/driver error; TestClient |
| `.\.venv\Scripts\python.exe -m pytest -q tests/persistence/test_authorization.py tests/persistence/test_authentication.py tests/persistence/test_security_audit.py tests/persistence/test_services_marketplace.py tests/persistence/test_foundation.py` in restricted sandbox | FAIL at fixture startup: 34 passed, 103 setup errors; `pg_ctl: could not create restricted token: error code 87` | Disposable cluster initialization; no application database |
| `.\.venv\Scripts\python.exe -m pytest -q tests/persistence/test_seller_schema_compatibility.py` in restricted sandbox | 1 fixture setup error, same Windows token restriction | Disposable cluster initialization |
| `.\.venv\Scripts\python.exe -m pytest -q tests/persistence/test_authorization.py tests/persistence/test_authentication.py tests/persistence/test_security_audit.py tests/persistence/test_services_marketplace.py tests/persistence/test_foundation.py tests/persistence/test_seller_schema_compatibility.py --tb=short` outside sandbox | PASS, **138 tests**, 403.04 seconds | Real PostgreSQL 17, freshly generated temporary cluster and synthetic databases; harness ignores application DATABASE_URL |
| `npm test -- --run` | Could not start: PowerShell blocks npm.ps1; 0 tests | No database |
| `npm.cmd test -- --run` | FAIL: 13 failed assertions and 2 EBUSY suite-import failures; complete test count not retained in captured output | Browser/jsdom tests, mocked API; no live backend/database |
| `npm.cmd test -- --run --maxWorkers=2 --reporter=json --outputFile=local-beta-frontend-results.json` | FAIL: **299 tests, 292 passed, 7 failed** | Browser/jsdom tests, mocked API; no live backend/database |
| `npm.cmd test -- --run src/App.test.tsx src/BetaResume.test.tsx src/pages/AdminOperations.test.tsx --maxWorkers=1 --testTimeout=20000 --reporter=json --outputFile=local-beta-frontend-recheck.json` | FAIL: **33 tests, 32 passed, 1 failed**; AdminOperations could not find Suspend Buyer | Isolated recheck of failing files, mocked API; timeout override applies only to this invocation |
| `npm.cmd run build` | PASS, TypeScript + Vite production build (1940 modules); not a test suite | No database |
| `git diff --check` | PASS (only Git's LF/CRLF informational warning) | No database |

The reduced-worker full frontend run passed all 28 `Marketplace.test.tsx` tests,
12 location-discovery tests, and 16 API-client tests, including seller profile
creation/editing, image URL requests/clearing, ownership request contracts, and
sanitized 503 error handling. These are mocked HTTP tests, not live browser proof.

Its seven failures were:

- `App.test.tsx`: `reports login failure 401 and clears the password`;
  `highlights sanitized backend login validation errors`;
  `offers only public buyer/seller registration and explains profile setup`;
  `reports registration rejection 409`; `reports registration rejection 422`.
  All five hit the 5000ms test timeout.
- `BetaResume.test.tsx`: `submits the exact product revision reviewed by the administrator`
  could not find the Approve button while the page was loading.
- `pages/AdminOperations.test.tsx`: `requires an investigation reason and sends only authorized account action fields`
  could not find Suspend Buyer while the page was loading.

The first unrestricted-worker frontend run also reported EBUSY locks opening
`aria-query` dependency files. No dependency, application, or test timeout settings
were changed to conceal these results. Full frontend machine-readable evidence:
`local-beta-frontend-results.json` at the project root.

The isolated recheck passed the five authentication/registration cases and the
product-revision case. The AdminOperations button lookup still failed. This is a
remaining frontend verification failure outside the seller-profile/image scope;
its cause is not established. The full suite is not claimed green. No actual
browser-driven end-to-end test or existing-dataset migration rehearsal was run.

Remaining local blockers: the application database is still at `0008`; actual file
upload is unimplemented; the admin frontend test above remains red. The safe code
change improves diagnostics, and disposable tests verify the required migration
repair, but the user's existing local seller flow is not repaired until the
separately authorized migration is performed after its backup/rehearsal gates.

## Restart commands

Stop the existing server in each terminal with Ctrl+C. Restart backend:

```powershell
# From the repository root:
Set-Location backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Restart frontend in another terminal:

```powershell
# From the repository root in a separate terminal:
npm.cmd run dev -- --host localhost --port 5173
```

Use `npm.cmd` because this machine blocks the PowerShell `npm.ps1` shim.
Restarting does not apply migrations or remove the existing schema mismatch.

## Manual checklist after schema readiness

- Log in as seller; load the existing profile, edit shop details, save, and reload.
- With a fresh seller, verify missing profile prompts creation; create it once;
  duplicate creation must return 409. Buyer access must return 403; anonymous or
  invalid-token access must return 401. Owner/verification fields must be rejected.
- Confirm dispatch and public discovery separately; public consent must start unset.
- Create a product with an accessible hosted HTTPS image URL; reload the seller
  dashboard and verify the image. Edit the URL, then clear it; verify persistence.
- Check credential-bearing and non-HTTP(S) URLs are rejected. Verify another seller
  cannot edit the product. An approved product edit must return it to PENDING.
- Confirm sanitized errors and retry behavior when storage is unavailable.
- File selection/upload cannot be tested until that feature is implemented.
