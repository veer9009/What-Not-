# Live location and empty discovery investigation

Date: 15 November 2026. Scope: local read-only diagnosis, deterministic regression checks and a radius-design proposal. No deployment, commit, push, original-database write, schema change or migration was performed. No application API requests were sent to the running original-backed backend during this investigation.

**Step 36 follow-up:** the owner completed the hidden-input check using the original Chrome point and obtained zero locality candidates. The [locality E2E verification](LOCALITY_DISCOVERY_E2E_VERIFICATION.md) now confirms the expected empty result, reverifies runtime database identity, demonstrates nonempty actual-service results at protected supported points and records fresh positive/negative isolated HTTP tests. Statements below that the private count is pending describe the earlier investigation baseline and are superseded by that verification.

## Findings first

- **Owner-reported device acquisition succeeded:** Chrome returned a position, displayed about 206 m reported accuracy, accepted confirmation, and received `200 []`. This is owner-provided evidence, not an agent-observed real-device run, proof of 206 m physical error, or evidence of movement. An empty product array is not a geolocation error.
- **The running backend uses the original `whatnot_app_dev`, not an isolated QA database.** This was independently verified using PostgreSQL session client ports, Windows socket ownership and the Uvicorn worker/parent relationship, not merely the `.env` filename.
- **Three products currently pass every non-location discovery predicate** in that database. Approval, product activity, stock, active SELLER role and confirmed dispatch do not explain an empty result against the current snapshot. Both seller profiles have valid coordinates. Locality remains the normal remaining exclusion for a standard UI request.
- **The isolated automated-test database has no persistent business records.** It would correctly return no candidates after a valid authenticated request unless a rollback-isolated test has installed its synthetic fixture. The proposed manual QA database `whatnot_location_qa_20261115` does not exist on this server. These facts must not be used to attribute the owner's original-backed request to an empty QA database.
- **The original buyer point and Network payload have not been captured by this agent.** Transient discovery location is intentionally not stored. Until the private point-count check below is completed, geographic exclusion is a supported hypothesis, not a confirmed location-specific root cause. No historical payload, pagination value or exact device position is inferred from HTTP 200 alone.
- **No new application defect has been reproduced.** The correct empty-state UI, accurate coordinate mapping, re-detection/cancellation and candidate/checkout behavior pass the focused tests. No fabricated listing, sample fallback or weakened filter was added to make the array nonempty.
- **Actual buyer-selectable live 1/2/3 km filtering remains absent.** Its design is in `LIVE_DISCOVERY_RADIUS_DESIGN.md`; it is not implemented by this investigation. The current data model supports numeric distance to private dispatch, but shipping that exact membership would change the tested privacy contract.

## 1. Verified backend identity and read-only inventory

Commands executed from the repository, using existing installed tools:

```powershell
& .\docs\security\verify_discovery_backend.ps1
```

That script runs `inspect_discovery_inventory.py`, then correlates only loopback sockets. It never emits a connection URL, password, full process command line, request body, account identity or coordinate. PostgreSQL inventory connections use `default_transaction_read_only=on`; each database inventory transaction explicitly uses repeatable-read/read-only and checks its database name/OID. Ordinary idle connections are observed, not terminated or treated as writers.

Verified identity evidence:

| Evidence | Observed value |
| --- | --- |
| Uvicorn listener | Loopback port 8000, PID 19728 |
| Python worker | PID 16412, parent PID 19728 |
| PostgreSQL client ports owned by worker | 60148, 60194, 60262, 60263 |
| PostgreSQL database reported for those four sessions | `whatnot_app_dev` |
| Original database OID / revision | `41069` / `0008` |
| Inventory access | PostgreSQL transaction read-only `on` |

PIDs/ports are execution-time evidence and may change after restart. The script independently verifies them on each run. Existing Uvicorn has `--reload`; no application writer was started, stopped or reconfigured by this task. A source row snapshot comparison during tests is evidence of unchanged rows, not a claim to prevent unrelated future application activity.

Inventory aggregate evidence (`docs/security/evidence/discovery-inventory.json`):

| Database | Users | Sellers | Products | Addresses | Orders | Eligible before locality |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original `whatnot_app_dev` | 6 | 2 | 3 | 1 | 3 | 3 |
| Protected rehearsal `whatnot_rehearsal_20261115_a7e394c2` | 6 | 2 | 3 | 1 | 3 | 3 |
| Isolated tests `whatnot_tests_20261115_a7e394c2` | 0 | 0 | 0 | 0 | 0 | 0 |

`whatnot_db` exists without the expected application schema; it is not queried as a marketplace. No manual QA database with the documented name was found. The current original-data funnel is `3 total → 3 approved → 3 active → 3 in stock → 3 active seller accounts → 3 confirmed dispatch candidates`. Missing seller coordinate count is zero. Coordinate column metadata is also inspected without reading coordinate values into the report.

No records were copied from the original into QA fixtures. No seeds, moderation actions, stock edits, seller confirmation, cleanup, creation/deletion of databases or permanent business records were executed.

## 2. Actual end-to-end implementation

| Stage | Implementation / evidence | What this establishes |
| --- | --- | --- |
| Acquire | `src/components/LocationPicker.tsx:15` calls `src/location/geolocation.ts:21` only from **Use current location**. The helper uses `navigator.geolocation.getCurrentPosition`, validates finite/bounded values and rounds named latitude/longitude to six decimal places. | No automatic GPS request or fixed fallback. Named fields are not swapped. |
| Browser states | Secure-context check, unsupported/error classification, 10 s provider timeout, 30 s interaction deadline, fresh-position/high-accuracy request; UI-only accuracy estimate. | Granted/prompt/denied/provider timing remain distinct; high accuracy is a hint, not a guarantee. |
| Confirm/source | Picker submit constructs a fresh `{latitude,longitude}` and invokes confirmation. `src/pages/DiscoveryPages.tsx:18` chooses `{location:point}`; manual/PIN edits clear the selected source. `src/state/DiscoveryContext.tsx:6` holds it in React memory. | Draft acquisition alone sends no discovery request. Accuracy is not transmitted as a coordinate field. |
| Request | `src/api/discovery.ts:12` POSTs source JSON via `src/api/client.ts:42`; bearer authorization, no-store, no coordinate query string. List default offset/limit are supplied by the backend, not a sample catalogue. | Deterministic tests verify exact numeric body mapping, including a negative synthetic latitude on re-detection. The owner's actual payload remains private/uninspected. |
| Validation/auth | `backend/app/api/routes/discovery.py:12`; `backend/app/schemas/discovery.py:12` requires exactly one point or owned address, rejects extras/invalid coordinates; active BUYER required. Normal API calls consume a quota counter. | 200 means the request passed those boundaries; it does not prove that the point matches the user's intended physical location. |
| Availability | `backend/app/repositories/products.py:40` joins product → seller profile → user and requires approved, active, positive stock, active SELLER, confirmed dispatch. | Valid but unavailable inventory correctly produces no candidate. No client approval/stock bypass. |
| Locality | `backend/app/services/discovery.py:13`, `:33`, `:46`: Haversine kilometres from buyer to a stable 0.01-degree seller-cell centre, include if distance ≤ product radius + 0.8 km. Pagination is applied after this filter. | This is intentional locality membership, not an exact buyer-selected radius or an exact seller-point distance. |
| Response | Minimal `BuyerProduct`, no seller point, exact distance, phone/private address. | Location information is minimized; an approved product is not automatically nearby. |
| Render | `src/pages/DiscoveryPages.tsx:30` calls the backend and applies only text search; 200 `[]` becomes **No products nearby**. Nonempty arrays render returned products. Errors use a separate sanitized notice. | No sample records or sample distances are substituted when the backend is empty. |
| Change handling | Source-keyed result components (`DiscoveryPages.tsx:28`), request/version guards (`src/state/useResource.ts:8`), abort/version guards in the picker. | Explicit re-detection clears the active source/results, waits for a new fix and requires confirmation. Stale callbacks/responses cannot overwrite the new draft. |
| Delivery | `backend/app/services/orders.py:86`, `:97` uses actual owned delivery-address and dispatch coordinates with `within_radius`. | Selected delivery address may differ from device location. Checkout remains exact and authoritative. |

One-shot location is not background tracking. **Refresh nearby products** reuses the confirmed source; navigation in the same account can retain it. No expiry or movement detection is implemented. PIN entry filters the buyer's saved addresses, then sends an owned `address_id`; an arbitrary PIN is not geocoded or treated as precise. Saved addresses require their own valid coordinates.

## 3. Concluding the empty-response diagnosis privately

The current read-only funnel eliminates non-geographic filters as the reason for zero results **now** in the original database. It does not prove the dataset or request was identical at the time of the owner's Chrome test. A changed point, an old confirmed source, a different request body or locality exclusion must be distinguished using the actual request, not assumptions.

The owner can run this read-only command in a normal interactive PowerShell terminal:

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
& .\.venv\Scripts\python.exe ..\docs\security\inspect_discovery_inventory.py --database whatnot_app_dev --check-point
```

At the hidden prompts, enter the numeric latitude/longitude from the **already confirmed Network request**. Do not send them to the agent, pass them as command arguments, pipe them, paste them into a report, capture a HAR or enable a transcript of the values. The script refuses noninteractive input and never prints/records coordinates. It reads the same availability predicates and locality formula and saves only aggregate counts to `docs/security/evidence/discovery-private-point-counts.json`. It does not send a POST, consume an API quota, change credentials or modify the database.

- `eligible_before_locality: 3`, `locality_candidates: 0`: confirms the currently selected point has no eligible locality products. Empty discovery is expected for that point and current inventory; do not “fix” it by inventing listings or widening delivery eligibility.
- `locality_candidates > 0`: does not match a current standard zero-offset request returning `[]`. Privately compare the confirmed draft with the request fields, verify backend identity/revision and frontend API URL, source type, pagination and time of the observations. Do not assume code failure or replay a write-producing API request against the original. Reproduce any discrepancy with synthetic points in isolated QA.
- Original request unavailable: historical point-specific cause remains **NOT VERIFIED**. A newly detected point is a different observation, not proof about the earlier request.

The agent did not run this private-point check because the coordinates were deliberately not supplied. Owner result is pending; no geographic diagnosis is presented as confirmed without it.

## 4. Corrections and test coverage

There is no confirmed new application bug justifying a product-code change at this stage. Existing approval, stock, seller/ownership checks and locality privacy remain unchanged. Added:

- A frontend regression for two explicit device detections: old results/draft clear, second synthetic negative latitude and accuracy display update, no request before re-confirmation, body contains only the new latitude/longitude, and valid empty response renders correctly (`src/LocationDiscovery.test.tsx`).
- A read-only inventory/private-point diagnostic and effective backend identity verifier (`docs/security/inspect_discovery_inventory.py`, `verify_discovery_backend.ps1`). These use no real coordinates in fixtures/logs/reports.
- A guarded `--discovery` test-runner selection that adds the existing same-cell private-point inference test, retaining test name/OID/owner checks, disabled database creation fixtures, outer rollback isolation and zero quota cleanup (`docs/security/run_existing_server_tests.py`).
- The radius proposal and this report. The earlier location verification report receives a dated follow-up pointer, preserving its historical results.

Fresh automated results:

| Verification | Command / result | Evidence |
| --- | --- | --- |
| Focused frontend | `node node_modules/vitest/vitest.mjs run --config vite.config.ts src/location/geolocation.test.ts src/components/LocationPicker.test.tsx src/components/DispatchLocation.test.tsx src/LocationDiscovery.test.tsx src/api/discovery.test.ts src/utils/products.test.ts --pool=threads --maxWorkers=1 --no-file-parallelism` — **exit 0; 50 passed, 6 files, 94.06 s** | `docs/security/evidence/discovery-investigation-frontend.log` |
| Numeric/schema backend | From backend: `.venv/Scripts/python.exe -m pytest -q -W error tests/test_geography.py tests/test_discovery_schemas.py --junitxml=../docs/security/evidence/discovery-investigation-unit.xml` — **exit 0; 44 passed, 2.72 s console duration** | `docs/security/evidence/discovery-investigation-unit.xml` |
| Database-backed | From backend: `.venv/Scripts/python.exe ../docs/security/run_existing_server_tests.py --discovery` — **exit 0; 77 passed, 1 historical migration test deselected; zero failures/errors/skips, 34.652 s XML duration** | `docs/security/evidence/discovery-investigation-database-tests.json` |
| Production build | `npm.cmd run build` — **exit 0; TypeScript + Vite passed, 1,939 modules, Vite 6.88 s** | `docs/security/evidence/discovery-investigation-build.log` |

`git diff --check` returned exit 0, with only LF/CRLF notices. PowerShell presents npm stderr notices as `NativeCommandError` formatting in the build log; the actual build process exited 0 and completed both steps. A verifier re-run exposed a PowerShell regex automatic-variable collision in its initial diagnostic script; the array was renamed and the verifier rerun. This was a diagnostic-script issue, not a marketplace/database failure, and no write operation was involved.

Database evidence: target `whatnot_tests_20261115_a7e394c2`, OID `49265`, revision `0008`, **1,678 guarded SQL statements**; `original_rows_unchanged: true`, `isolated_test_rows_unchanged: true`, `quota_cleanup_performed: false`. Test business fixtures roll back; isolated test sequences can advance despite row rollback. Original connections remain transaction-read-only. The one deselected historical dispatch migration test would create databases/downgrade; its fail-closed fixture is retained. The selected private-inference test does not invoke those migration fixtures.

| Requested scenario | Fresh coverage / qualification |
| --- | --- |
| Granted, denied, timeout, unavailable | Helper/picker mocked callbacks; owner separately reports actual granted acquisition. Mocked callbacks are not a real provider test. |
| Accuracy, confirmation, repeated detection, manual point | Picker/helper + new repeated-detection integration regression; no automatic submission or fabricated point. |
| Stale clearing and old responses | Picker version/abort and discovery result tests; no background movement tracking claim. |
| PIN/saved address | Permission-denied → manual PIN → explicit owned address selection; unknown PIN makes no discovery request. |
| Valid request, empty and eligible product | Frontend exact body/array rendering; PostgreSQL-backed discovery supplies deterministic eligible fixtures and returns genuine empty results when excluded. |
| Ineligible/outside locality | Parameterized stock/moderation/seller/confirmation and far-location tests; generic ineligible detail 404. |
| Missing coordinates | Request validation rejects incomplete/null point; database rejects null seller/address coordinates; no `(0,0)` fallback. |
| 1/2/3 boundaries | Numeric helper and real PostgreSQL checkout boundary cases; sample selectors tested separately. These are **not** tests of a nonexistent live buyer selector. |
| Backend failure / frontend empty state | Distinct mocked 503 error and 200 empty array cases, with sanitized UI. |
| Private dispatch confidentiality | Current response fields and same-cell indistinguishability test pass. |

No full-suite production-readiness claim is made. Existing broader production audit and intermittent frontend failure gates remain separate.

## 5. Radius implementation decision

See `LIVE_DISCOVERY_RADIUS_DESIGN.md` for model evidence, strict 1/2/3 request design, actual kilometre calculations, inclusive boundaries, server enforcement, buyer/seller radius intersection, missing-data handling, frontend change behavior and acceptance tests.

The model can compute exact distance to dispatch without a schema change, but exposing exact inclusion based on arbitrary buyer points contradicts the current tested private-dispatch locality contract. A public, consented discovery-point model is not present. The design distinguishes those options; it does not claim that a spatial extension, Google Maps or fabricated PIN centre is required. No privacy contract or schema was silently changed.

## 6. Current decision / owner next action

**Owner-reported device acquisition: succeeded. Automated discovery paths: PASS. Historical point-specific empty-result cause: NOT VERIFIED pending the private count. Genuine live buyer-radius controls: NOT IMPLEMENTED; design only.**

First, run the hidden-input read-only check using the original confirmed request point and report **only** `locality_candidates`. Do not continue browser write-producing tests against the original database as part of this investigation. For new visible fixture/listing experiments, provision a separate synthetic manual QA database; do not seed the original or protected rehearsal database, and do not permanently populate the automated-test database used by rollback-only fixtures. Then resolve the public/private listing-point decision before radius implementation.
