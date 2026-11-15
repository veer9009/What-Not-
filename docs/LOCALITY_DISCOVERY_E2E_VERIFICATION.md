# Locality discovery end-to-end verification — Step 36

Date: 15 November 2026 (Asia/Calcutta). Scope: explain the original empty result, independently identify the running backend database, demonstrate positive discovery safely and test negative cases without modifying original records.

| Required verdict | Result | Evidence |
| --- | --- | --- |
| Root cause | **CONFIRMED** | The owner's hidden-input check of the original Chrome request point found three eligible products before locality and zero afterwards. The diagnostic and production service use equivalent eligibility and locality rules. There are no qualifying products at that tested point; `200 []` is expected. |
| Backend database identity | **VERIFIED** | PostgreSQL sessions were correlated with the actual loopback port-8000 Uvicorn worker/parent, independently of the inventory connection. Target is `whatnot_app_dev`, OID `41069`, revision `0008`. |
| Zero-candidate exclusion | **CORRECT** | All three products fail the locality predicate at the original request point. No approval/stock/seller bypass or invented fallback is warranted. |
| Positive discovery test | **PASS** | Actual unchanged discovery service returned three products at each of two protected seller-supported points in read-only transactions. Isolated PostgreSQL-backed HTTP tests also returned an eligible product. |
| Negative discovery test | **PASS** | Isolated HTTP tests returned empty arrays and unavailable-detail responses for outside-locality, unapproved/inactive/out-of-stock and seller-ineligible cases. |
| Live buyer-selectable 1/2/3 km filtering | **NOT IMPLEMENTED** | Sample buttons and seller delivery radii exist; live discovery has no buyer radius parameter/control. |

**The complete real-device Chrome positive workflow is still NOT VERIFIED.** The owner demonstrated device acquisition plus a valid empty response. Positive results are demonstrated here through the actual read-only service and isolated HTTP tests; a new real-device Chrome run displaying an eligible listing was not performed. Neither a browser accuracy estimate nor synthetic coordinates prove physical GPS accuracy or movement.

## 1. Actual implementation

`POST /api/v1/discovery/products` calls `DiscoveryService.list` after request validation, active BUYER authorization and abuse limiting (`backend/app/api/routes/discovery.py:12`). It accepts exactly one transient coordinate or owned saved address; list defaults are offset 0 and limit 100 (`backend/app/schemas/discovery.py:12`). Browser confirmation sends named numeric latitude/longitude in JSON, not a coordinate query string (`src/components/LocationPicker.tsx:23`, `src/api/discovery.ts:12`).

`ProductRepository._discovery_query` (`backend/app/repositories/products.py:40`) requires:

- Product APPROVED, active and positive stock.
- Active seller user with role SELLER.
- Explicitly confirmed seller dispatch location.

Products inherit their seller profile's valid dispatch coordinates; there is no independent product location. The database has bounded non-null seller/address coordinate columns. Missing coordinates are not treated as zero or inferred from a PIN.

`DiscoveryService._eligible_view` (`backend/app/services/discovery.py:32`) maps the seller's point to a stable 0.01-degree cell centre, calculates Haversine distance in kilometres and excludes a product when:

```text
distance_km(buyer point, seller locality centre) > product.delivery_radius_km + 0.8
```

The 0.8 km margin bounds cell-centre displacement; this is a **locality candidate** rule. Pagination occurs after locality filtering (`discovery.py:46`). The minimal response omits private seller coordinates and exact distances. The frontend renders returned products or **No products nearby** for an empty array (`src/pages/DiscoveryPages.tsx:30`). It does not substitute sample listings. Exact delivery eligibility still uses the actual saved delivery address and dispatch point at checkout (`backend/app/services/orders.py:86`, `:97`).

## 2. Backend identity independently verified

Command, repository-root PowerShell:

```powershell
& .\docs\security\verify_discovery_backend.ps1
```

Fresh result: exit 0. Evidence: `docs/security/evidence/discovery-backend-identity.json`, captured at approximately **09:02 IST**.

- Loopback port 8000 belongs to Uvicorn PID `19728`.
- Its Python worker is PID `16412`, parent `19728`.
- Worker-owned PostgreSQL client ports `60148`, `60194`, `60262`, `60263` map to four `pg_stat_activity` sessions whose database is `whatnot_app_dev`.
- Inventory independently verifies original OID `41069`, revision `0008` and transaction read-only `on`.

The verifier reads socket ownership, process ancestry and a sanitized Uvicorn flag. It does not emit full command lines, credentials, query text or coordinates. PIDs/ports are execution-time evidence and may change after restart. This is independent runtime evidence, not an inference from the diagnostic's selected database name or `.env` alone. Earlier investigation recorded the same worker-to-database correlation during the Chrome investigation.

## 3. Diagnostic and production logic agree

The owner's check is retained in `docs/security/evidence/discovery-private-point-counts.json` at approximately **08:59 IST**:

```text
database: whatnot_app_dev
oid: 41069
revision: 0008
read_only: true
total_products: 3
eligible_before_locality: 3
locality_candidates: 0
coordinates_recorded: false
```

The owner confirms the hidden inputs came from the **original Chrome request**, rather than a newly detected point. That association is owner-provided evidence. The agent inspected the aggregate artifact and source, not the private point itself.

Comparison:

| Rule | Diagnostic | Production service |
| --- | --- | --- |
| Non-location eligibility | SQL joins product/seller/user; approved, active, stock > 0, active SELLER, confirmed dispatch (`inspect_discovery_inventory.py:115`) | Same joins/predicates in `ProductRepository._discovery_query` |
| Point validation | `Coordinate` validates hidden input | Same `Coordinate` type inside `DiscoverySource` / `DiscoveryQuery` |
| Seller locality centre | Imports `locality_center` directly from production discovery | Calls that same function |
| Kilometre calculation | Imports production `distance_km` | Calls that same function |
| Inclusion boundary | `distance <= radius + .8` (`inspect_discovery_inventory.py:124`) | Excludes only `distance > radius + .8` (`discovery.py:38`) |
| Pagination | Counts all matches | Paginates matching products; cannot turn zero total matches into a positive list |

For the valid finite inputs here, the two comparison expressions are complements and have the same inclusive boundary. Three nonnegative boolean eligibility outcomes summing to zero means **each of the three products is excluded**. Missing/invalid seller coordinate counts are zero. Therefore the zero-candidate result correctly explains the empty API result for the owner's original point and observed inventory. It does not establish that the point is the device's true physical position.

No production filtering defect was found. The cause is lack of eligible inventory in the tested supported locality, rather than a requirement to widen delivery areas or fabricate listings.

## 4. Positive location exists: actual service, protected read-only probe

Command from `backend`:

```powershell
& .\.venv\Scripts\python.exe ..\docs\security\verify_locality_support.py
```

The new script verifies loopback target/name/OID/revision, forces repeatable-read/read-only, selects an existing active BUYER solely for service authorization, loads the actual eligible candidates and calls the unchanged `DiscoveryService.list` at each eligible seller's own dispatch point. Those points and record identifiers remain in process memory and are never emitted, logged, saved or copied into test fixtures. It sends **no HTTP request**, so no production API quota write occurs. All own-seller eligible products must appear or the script fails closed. It also compares diagnostic membership with actual service results at those points.

Evidence: `docs/security/evidence/locality-supported-points.json`, final run at approximately **09:04 IST**, exit 0:

```text
eligible_before_locality: 3
seller_supported_points_checked: 2
points_returning_products: 2
minimum_results_at_supported_point: 3
maximum_results_at_supported_point: 3
all_own_eligible_products_returned: true
diagnostic_matches_service_at_supported_points: true
read_only: true
coordinates_or_record_ids_emitted: false
api_requests_sent: 0
```

No address, seller confirmation, product record or delivery radius is changed to manufacture this result. These are protected read-only service probes, distinct from the deterministic synthetic coordinates used in automated HTTP tests.

## 5. Isolated positive/negative HTTP tests

Command from `backend`:

```powershell
& .\.venv\Scripts\python.exe ..\docs\security\run_existing_server_tests.py --discovery
```

**Exit 0: 77 passed; zero failures/errors/skips; one historical migration test deliberately deselected; 34.501 s XML duration.** The deselected test creates databases and downgrades; creation/startup fixtures remain disabled. No migration ran.

Evidence: `docs/security/evidence/discovery-investigation-database-tests.json` and `docs/security/evidence/locality-e2e-http-cases.json`. Retained synthetic log: `C:\Users\DELL\AppData\Local\Temp\WhatNotLocationQA-mwp3ck4_\pytest.log`.

Tests target only `whatnot_tests_20261115_a7e394c2`, OID `49265`, revision `0008`. Name/OID/owner is checked before SQL; outer transactions roll back business fixtures. **1,678 guarded SQL statements; original rows unchanged; isolated test rows unchanged; no quota cleanup.** Source snapshot connections are read-only. Isolated test sequences may advance despite business-row rollback; no original sequence is touched.

| Scenario | Fresh asserted result |
| --- | --- |
| Positive transient point and owned address | `test_transient_and_owned_address_discovery_safe_responses`: HTTP 200, expected product returned by list/detail, no-store, private location fields omitted |
| Outside locality | `test_each_radius_and_unrounded_outside_point[1/2/3]`: nearby candidate returned; far synthetic point returns `[]` |
| Unapproved, rejected, inactive, zero stock | `test_all_availability_predicates_and_hidden_detail`: empty list; detail 404 |
| Unconfirmed dispatch / inactive seller / wrong seller role | Same predicate test: empty list; detail 404 |
| Buyer source differs from saved address / source changes | Device-location-change test verifies changed results without altering dispatch or saved points |
| Exact 1/2/3 delivery boundaries | Order-geography tests preserve exact checkout acceptance/rejection independently of coarse discovery |
| Private dispatch inference | Same-cell indistinguishability test passes; no exact private-point radius rule introduced |

Frontend command, repository root:

```powershell
& 'C:\Program Files\nodejs\node.exe' node_modules/vitest/vitest.mjs run --config vite.config.ts src/LocationDiscovery.test.tsx --pool=threads --maxWorkers=1 --no-file-parallelism
```

**Exit 0: 9 passed, 1 file, 31.07 s**, retained in `docs/security/evidence/locality-e2e-frontend.log`. These mocked API integration tests cover positive returned-product rendering, empty state, sanitized error, source confirmation, repeated detection, stale responses, logout and PIN fallback. They are not a positive real-device Chrome run. No build or dependency change is necessary for this verification-only task; prior build evidence remains in the preceding report.

## 6. Changes, limitations and remaining pilot blockers

Added `docs/security/verify_locality_support.py`, this report and aggregate verification artifacts. Existing application code, schema, coordinates, stock, approval, seller status and delivery settings are unchanged. No new permanent fixture or fake nearby listing was inserted anywhere. No AWS resources, deployment, migration, credential changes, commits or pushes occurred.

Remaining pilot gates:

1. Positive owner-visible Chrome discovery on a separately provisioned, synthetic manual QA environment. Do not seed the original or protected rehearsal database, and do not permanently populate the rollback-only automated test database. Keep device location and dispatch/delivery-address roles distinct.
2. Actual buyer-selectable live 1/2/3 km filtering is **NOT IMPLEMENTED**. Its exact-membership/privacy decision and proposed contract remain in `LIVE_DISCOVERY_RADIUS_DESIGN.md`. Current seller radii and sample controls are not equivalent.
3. Device-provider/OS/browser variation, unknown or imprecise accuracy, actual movement and HTTPS-domain behavior remain manual checks. About 206 m is a browser-reported estimate, not measured physical error.
4. The separate production-readiness gates remain: AWS/Linux/TLS/access controls, backup/restore and monitoring evidence, privacy/retention approval, complete pilot workflows and the unresolved intermittent full-suite frontend failure. These checks do not grant deployment GO.

**Outcome:** empty discovery at the original tested point is explained and correct; positive service and isolated HTTP discovery have been demonstrated. Complete positive real-device Chrome end-to-end acceptance remains outstanding.
