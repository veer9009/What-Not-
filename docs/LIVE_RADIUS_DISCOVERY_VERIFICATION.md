# Live 1/2/3 km discovery: schema and privacy review

## Approved implementation: current verified result

15 November 2026. **Backend live 1/2/3 km radius filtering PASS in isolated QA. Owner Chrome radius acceptance NOT VERIFIED.** The owner approved both the public discovery-point contract/QA-only additive migration and explicit confirmation of the existing synthetic QA seller public point `(0,0)` with rollback-only boundary tests. The historical pre-approval review follows the current results below.

### Migration and data safety

- Verified target: **whatnot_chrome_qa_20261115, OID 50640**, expected owner, loopback PostgreSQL 5432. No original/rehearsal connection or migration occurred in this implementation phase.
- Fresh full QA custom archive: `C:\Users\DELL\AppData\Local\Temp\WhatNotPublicRadiusQA-mk5yui93\chrome-qa-before-0009.dump`.
- SHA-256: **5310c63e5846c89cdd9337e4c33c8a4a6309de80b6943afebb0efdd374857363**. Archive listing exit **0** with TABLE DATA entries. pg_dump creates a consistent transaction snapshot. A restore was not performed: no overwrite/additional database was authorized.
- Executed `alembic.command.upgrade(config, '0009')` with the existing verified QA connection and a database-name/OID/owner SQL guard. Migration output: **Running upgrade 0008 -> 0009**, process exit **0**. Every migration statement was identity guarded; checksum, revision and business snapshot were rechecked immediately before upgrade.
- Four nullable public-point fields and range/all-present-or-all-null constraints added. All fields verified NULL immediately afterward; no backfill. Existing private/business values unchanged. Separate approved confirmation used the literal synthetic public point, never copied dispatch fields.
- Counts before/after migration, confirmation and HTTP checks: **2 users / 1 seller / 3 products / 1 address / 0 orders**. PostgreSQL tests changed existing QA fixture values only inside rollback transactions and verified exact business row snapshots afterward. Normal auth/discovery quota counters remain enabled and may persist in QA. No quota cleanup/reset occurred.
- No original/rehearsal modifications, new business rows, dependency installation, deployment, commit or push. Do not rerun one-time migration/confirmation scripts: their guards refuse unexpected revision/non-NULL public data. No automatic downgrade or restoration exists.

Evidence: `security/evidence/public-radius-qa-migration.json`, `qa-public-point.json`.

### Implemented contract and flow

Buyer live list and detail POSTs accept strict integer `radius_km` **1, 2 or 3**, default **3** for compatible clients. Invalid bool/string/fraction/out-of-range values are rejected. Frontend always sends the selected value, preserving exact BIGINT address IDs.

```text
public_distance = Haversine_km(buyer_point, confirmed_public_discovery_point)
candidate = approved + active + in_stock + active_SELLER + confirmed_private_dispatch
            + current_explicit_public_consent
            + public_distance <= buyer_radius
            + public_distance <= product_delivery_radius
            + existing_coarse_private_dispatch_locality_gate
```

Exact comparisons use Earth radius **6371.0088 km**, inclusive boundary with **1e-9 km** floating arithmetic tolerance. The private gate remains cell centre plus existing 0.8 km margin; no new exact private-dispatch membership is exposed. Private points in the same cell remain indistinguishable when public point and other fields stay fixed. Exact saved-delivery-address-to-private-dispatch enforcement remains at checkout. A public discovery point may differ from dispatch: discovery does not guarantee delivery.

Missing, unconfirmed, revoked, wrong-consent-version or invalid public points are excluded. Existing private coordinates are never substituted. No seller public point is inferred from login, GPS, private dispatch or PIN. Seller-owned PATCH confirmation requires literal consent true/current version; POST revocation clears all four fields. Seller UI explains inferability, starts with empty fields, resets consent when the draft changes, and requires an explicit checkbox before confirmation. Editing general/private shop fields cannot publish a point.

GPS, manually confirmed coordinates and owned saved addresses use the same radius rule. Radius selection is held in memory and included in list/detail keys and dependencies. A changed radius immediately unmounts old results and POSTs again when a source exists; it does not re-request GPS. Pending old responses are ignored; loading, empty and error states remain distinct. GPS accuracy remains displayed with uncertainty warnings; it does not widen either radius. Sample catalogue controls remain separate and no sample product enters live results. Buttons expose a labeled group/aria-pressed, keyboard focus and responsive touch targets.

This build requires schema **0009**. Readiness and guarded initial-admin bootstrap share `app/db/schema.py`; no admin was created. **The original database has not been approved/migrated to 0009 by this task. Do not run this build against it.** Existing original-backed services were not restarted or contacted. A later original/production migration requires its own approval and procedure.

### Actual HTTP proof

Fresh loopback worker: **127.0.0.1:8002, PID 19164**, independently correlated through PostgreSQL/socket metadata to QA OID **50640**, revision **0009** before login. The protected verifier decrypted only the approved synthetic buyer credential privately, issued real network HTTP requests, and exited **0**. No password/token/signing key/connection string is in the evidence.

| Synthetic source | Radius 1 | Radius 2 | Radius 3 |
| --- | --- | --- | --- |
| Latitude 0, longitude 0 | 200 / 2 products | 200 / 2 products | 200 / 2 products |
| Latitude 0, longitude 0.012 (~1.334 km) | 200 / [] | 200 / Vase only | 200 / Vase only |
| Latitude 1, longitude 1 | 200 / [] | 200 / [] | 200 / [] |

Basket's 1 km product radius excludes it at 1.334 km even when the buyer chooses 2/3 km. Vase has a 2 km product radius, so 2/3 km counts can legitimately match. No 3 km approved product was invented: the 3 km boundary was separately exercised with the approved temporary product-radius change inside rollback PostgreSQL tests. Default supported/unsupported/supported also returned **2/0/2**, and owned-address discovery returned **2**. Pending product excluded; minimal response fields and no-store verified. Source: `security/evidence/chrome-qa-http.json`.

### Tests and commands executed

From `backend`:

```powershell
# One-time scripts were executed once. DO NOT repeat upgrade/confirmation.
& .\.venv\Scripts\python.exe -c "import sys,runpy;sys.path.insert(0,'../docs/security');runpy.run_path('../docs/security/migrate_public_discovery_qa.py',run_name='__main__')"
& .\.venv\Scripts\python.exe -c "import sys,runpy;sys.path.insert(0,'../docs/security');runpy.run_path('../docs/security/confirm_qa_public_point.py',run_name='__main__')"

& .\.venv\Scripts\python.exe -m pytest tests --ignore=tests/persistence -q --junitxml=../docs/security/evidence/public-radius-unit.xml
& .\.venv\Scripts\python.exe -c "import sys,pytest;sys.path.insert(0,'../docs/security');raise SystemExit(pytest.main(['-q','../docs/security/test_public_radius_qa.py','--junitxml=../docs/security/evidence/public-radius-postgres.xml']))"
& .\.venv\Scripts\python.exe -m pytest ..\docs\security\test_chrome_qa_launcher.py -q

# Temporary verification worker; separate terminal ran verifier.
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py --serve --port 8002
& .\.venv\Scripts\python.exe ..\docs\security\verify_chrome_qa_http.py --port 8002
```

| Check | Final result |
| --- | --- |
| Backend unit suite, excluding persistence cluster fixtures | **329 passed**, exit 0, 16.13 s |
| QA PostgreSQL tests | **24 passed**, exit 0, 21.27 s; business snapshots unchanged |
| Launcher isolation unit tests | **15 passed**, exit 0, 4.00 s |
| Focused frontend | **49 passed / 7 files**, exit 0, 120.41 s |
| Network-blocked Chrome geometry | **PASS**, exit 0 at 1440/1024/768/390/320 px, including radius controls |
| TypeScript + production Vite build | **PASS**, exit 0; 1940 modules, Vite 7.32 s |
| Real network HTTP radius verification | **PASS**, exit 0; nine explicit radius cases above |
| Manual Chrome radius/GPS/physical movement acceptance | **NOT VERIFIED** |

Unit tests prove mathematically inclusive exact 1/2/3 km comparisons. Six-decimal persisted-coordinate tests straddle each boundary at longitude **0.008993/0.008994**, **0.017986/0.017987**, **0.026979/0.026980** from synthetic origin. Do not describe these rounded points as exactly one/two/three kilometres. Tests also cover dateline/poles, pagination across candidate batches, smaller product radii, approval/activity/stock/account/dispatch gates, source ownership/RBAC, saved-address/detail consistency, explicit consent/revocation, database constraints, private-cell indistinguishability, late response suppression and GPS denial/timeout/unavailable/accuracy/manual fallback. Legacy persistence fixtures were updated to explicitly consent synthetic points, but their cluster-creation harness was not executed: this task restricts DB work to existing QA.

From repository root:

```powershell
& 'C:\Program Files\nodejs\corepack.cmd' pnpm test run src/LocationDiscovery.test.tsx src/components/LocationPicker.test.tsx src/location/geolocation.test.ts src/components/PublicDiscoveryLocation.test.tsx src/components/DispatchLocation.test.tsx src/api/discovery.test.ts scripts/discovery-layout.test.tsx --testTimeout=20000 --no-file-parallelism
& 'C:\Program Files\nodejs\node.exe' scripts/verify_discovery_pin_layout.mjs
& 'C:\Program Files\nodejs\corepack.cmd' pnpm build
```

Failures encountered and resolved: initial tests demonstrated absent radius controls/consent schema; a transient dependency EBUSY occurred before frontend collection; old privacy test doubles required explicit public-point fixture fields. Actual `/ready` initially returned **503** due to its hardcoded 0008 check; regression tests failed before the shared 0009 revision fix. Intermediate Windows runtime-metadata helpers failed closed; final socket correlation and complete verifier passed without relaxing guards. Geometry initially passed but Chrome shutdown left an unsettled promise/nonzero exit; shutdown is now bounded and final command exits 0. No failed migration was retried, quota cleared, security guard disabled or original database used to bypass a failure.

A fresh-context read-only review found no substantive defects. Its two coverage suggestions (dateline/poles and multi-batch pagination) were added and passed in the final unit suite. Evidence files: `public-radius-unit.xml`, `public-radius-postgres.xml`, `chrome-qa-launcher-tests.xml`, `chrome-pin-layout.json`, `discovery-layout-fixture.html`, `chrome-qa-http.json` under `docs/security/evidence`.

### Changed files and responsibilities

- Database/backend contract: `backend/alembic/versions/0009_public_discovery.py`, `backend/app/models/seller_profile.py`, `backend/app/schemas/public_discovery.py`, `schemas/discovery.py`, `schemas/marketplace.py`.
- Server behavior: `backend/app/services/discovery.py`, `services/sellers.py`, `api/routes/sellers.py`, `api/routes/health.py`, `db/schema.py`, `bootstrap_admin.py` (schema gate only).
- Frontend: `src/api/discovery.ts`, `api/sellers.ts`, `api/types.ts`, `state/DiscoveryContext.tsx`, `components/Shared.tsx`, `components/PublicDiscoveryLocation.tsx`, `pages/DiscoveryPages.tsx`, `pages/SellerPages.tsx`, `styles/index.css`.
- Regressions: `backend/tests/test_public_discovery.py`, `test_beta_privacy.py`, `test_admin_bootstrap.py`, `persistence/test_discovery.py`, `persistence/test_beta_resume.py`; `src/LocationDiscovery.test.tsx`, `src/api/discovery.test.ts`, `src/components/PublicDiscoveryLocation.test.tsx`.
- QA tooling/docs: `docs/security/migrate_public_discovery_qa.py`, `confirm_qa_public_point.py`, `test_public_radius_qa.py`, `run_chrome_discovery_qa.py`, `verify_chrome_qa_http.py`, `scripts/verify_discovery_pin_layout.mjs`, plan `docs/superpowers/plans/2026-11-15-live-radius-discovery.md`, this report, acceptance guide and sanitized evidence. The pre-approval read-only inspector/evidence remain historical.

### Exact owner Chrome acceptance and remaining limitations

The temporary port-8002 process is stopped after verification. Existing port-8001 QA process was not restarted by the agent and may still serve old code. In its existing QA terminal, **Ctrl+C only that QA server**, then run:

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: QA identity/fixtures failed.' }
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py --serve
```

Expected preflight: QA **OID 50640**, revision **0009**, counts 2/1/3/1/0. API **http://127.0.0.1:8001/api/v1**, readiness **http://127.0.0.1:8001/api/v1/ready** -> schema 0009. Do not run raw Uvicorn against the original .env target or migration scripts.

In a separate frontend terminal (reuse 5174 if already correctly configured):

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8001/api/v1'
& 'C:\Program Files\nodejs\corepack.cmd' pnpm dev --host 127.0.0.1 --port 5174 --strictPort
```

1. Open **http://127.0.0.1:5174/login/buyer** in the separate QA Chrome profile. Reload and sign in with the existing private QA buyer credential; restarting the backend changes its independent signing key, so old tokens expire. Never share credentials/headers/HAR.
2. Manually enter Latitude **0**, Longitude **0**, click **Use for discovery**. Select each **1 KM / 2 KM / 3 KM** button. Expect a fresh POST carrying the selected radius and both approved cards; selected button has aria-pressed true.
3. Change manual source to Latitude **0**, Longitude **0.012**, then confirm. **1 KM -> HTTP 200 / [] / No products nearby. 2 KM -> HTTP 200 / Vase only. 3 KM -> HTTP 200 / Vase only.** Basket must stay excluded. Switching radius should clear old cards while loading without another GPS prompt.
4. Set **1,1**, confirm, switch all radii: each returns 200 / []. Return to 0,0: both return. Pending product never appears. PIN **999999** -> **Use QA Home for discovery** works with each selected radius through address_id plus radius_km.
5. Test keyboard/pressed states and widths 390/320 px. Separately click **Use current location**, grant permission, inspect displayed accuracy and confirm. Expect each radius sent with the acquired point; real-world results may legitimately be empty because these are synthetic seller fixtures. Do not move QA seller points to real device coordinates to force results.
6. Seller consent UI is available under the existing synthetic seller account; no browser seller-confirmation/revocation acceptance is claimed. Revoking would hide all QA products until explicitly reconfirmed. Do not change approved fixtures just for screenshots.

Owner Chrome radius acceptance, actual GPS accuracy/movement and HTTPS acceptance remain **NOT VERIFIED**. Exact public-point membership is intentionally inferable under consent; private dispatch remains coarse in discovery and exact at checkout. Public-point consent semantics/terms still need production product/privacy review. Existing QA approved products cap at 1/2 km, so there is no separate persistent 3-km-only card. Full frontend suite/intermittent unrelated failure and full deployment readiness are outside this focused verification. **QA feature PASS does not authorize original/production migration or AWS deployment.**

## Historical pre-approval review (superseded by approved implementation above)

At the original inspection, implementation was blocked pending the public-point privacy contract and QA migration approval. The following records that initial evidence and proposal; its NOT RUN/NOT IMPLEMENTED entries are historical.

## Verified current implementation

| Area | Evidence | Finding |
| --- | --- | --- |
| Sample controls | `src/pages/BuyerPages.tsx:21`, `:31`; `src/components/Shared.tsx:22` | 1/2/3 KM buttons filter sample product distances in browser memory; backend products are excluded from that sample catalogue |
| Live state/request | `src/state/DiscoveryContext.tsx:4`; `src/api/discovery.ts:11`; `backend/app/schemas/discovery.py:11`, `:22` | Exactly one confirmed location or owned address; no buyer radius state/field. Extra request fields are forbidden. |
| Live distance | `backend/app/services/discovery.py:13`, `:32`, `:38` | Coarse seller-cell centre and seller delivery radius + 0.8 km margin; locality candidates, not exact buyer-radius membership |
| Exact numeric primitive | `backend/app/services/geography.py:17`, `:27` | Existing bounded/finite Haversine, Earth radius 6371.0088 km, inclusive comparison with 1e-9 km arithmetic tolerance |
| Model | `backend/app/models/seller_profile.py:27`; `backend/app/models/product.py:20`; `backend/app/models/address.py` | Six-decimal dispatch coordinates and owned address coordinates; product delivery radius restricted to 1/2/3. No separate public listing point or publication-consent fields. |
| Availability | `backend/app/repositories/products.py:39` | APPROVED, active, in-stock product; confirmed dispatch; active SELLER account; these restrictions must remain |
| Privacy invariant | `backend/tests/persistence/test_beta_resume.py:89`, `:104` | HTTP probes must not distinguish private dispatch points within the same 0.01-degree cell |
| Prior design | `docs/LIVE_DISCOVERY_RADIUS_DESIGN.md` | Explicitly records the private-point inference issue and pending observable-point/privacy decision |

GPS, manual coordinates and saved addresses can all supply the buyer point. A PIN alone cannot. Accuracy is uncertainty, not permission to enlarge a radius or guarantee checkout eligibility. No new Google service or geospatial extension is necessary for Haversine.

## Fresh read-only QA evidence

Executed from `backend`:

```powershell
& .\.venv\Scripts\python.exe -c "import sys,runpy;sys.path.insert(0,'../docs/security');runpy.run_path('../docs/security/inspect_radius_readiness.py',run_name='__main__')"
& .\.venv\Scripts\python.exe -m pytest tests/test_discovery_schemas.py tests/test_geography.py -q
```

Read-only inspector exited 0. Target was **whatnot_chrome_qa_20261115, OID 50640, revision 0008**, expected owner; `transaction_read_only=on`. Counts were **2 users / 1 seller / 3 products / 1 address / 0 orders**. Existing service positive/negative checks returned 2 and 0. These are existing locality checks, not radius acceptance.

Actual QA seller location columns are only `latitude`, `longitude`, `dispatch_location_confirmed_at`. No public discovery point exists. Current Pydantic requests containing radius_km 1, 2 or 3 all fail with **extra_forbidden**. This is direct contract validation, not a claimed captured HTTP 422. No HTTP authentication/registration or quota-writing probe was run in this investigation.

Pure synthetic calculation proves the privacy conflict: seller points `(0.001,0.001)` and `(0.009,0.009)` share one currently indistinguishable cell. For each chosen buyer point, exact membership differs:

| Buyer radius | Synthetic distances to the two points (km) | Exact inclusion |
| --- | --- | --- |
| 1 km | 0.676373 / 1.850655 | included / excluded |
| 2 km | 1.449806 / 2.540509 | included / excluded |
| 3 km | 2.337743 / 3.376378 | included / excluded |

Thus merely omitting coordinates from JSON does not preserve the existing privacy behavior. Repeated observation of inclusion boundaries can reveal dispatch information. Authentication and rate limiting do not eliminate that inference. Filtering the cell centre and labeling it exact distance would also be incorrect.

Unit tests exited **0: 44 passed in 0.80 seconds**. They verify existing geography/schema behavior only. An initial inline inspector command failed with a Python SyntaxError before any database access; it was replaced with the standalone read-only script. Sanitized evidence: `docs/security/evidence/live-radius-readiness.json`.

## Proposed schema change — not applied

Recommended contract: exact buyer radius refers to an **explicitly consented public seller discovery/business point**, while private dispatch remains protected and exact delivery is validated at checkout. Seller must understand that exact product membership makes this point inferable even without returning numeric coordinates.

Proposed next Alembic revision, number to be confirmed against head before authoring:

1. Add nullable `public_discovery_latitude NUMERIC(9,6)` and `public_discovery_longitude NUMERIC(9,6)` to seller_profiles.
2. Add nullable `public_discovery_confirmed_at TIMESTAMPTZ` and `public_discovery_consent_version VARCHAR(32)`.
3. Add coordinate-range and all-present/all-null constraints. Validate non-finite values in application contracts as for existing coordinates.
4. Leave all existing rows NULL. **No automatic dispatch-to-public copy or backfill.** Existing private dispatch coordinates and confirmation remain unchanged. Sellers without a consented public point cannot qualify for the exact public-radius feature; onboarding must explain this rather than invent a point.
5. Add an authenticated seller-owned confirmation/edit/revocation flow. Each changed point requires explicit renewed confirmation. Never treat existing dispatch confirmation as publication consent.

This is additive DDL but still requires migration approval and rehearsal. Only the verified isolated QA database may be targeted under the present task; original/rehearsal migration remains prohibited. QA public-point fixtures also require approval; no synthetic point has been inserted into new fields because no fields were created.

Proposed enforcement after contract approval:

- Add strict integer radius_km in {1,2,3} to live list/detail contracts; decide explicit default (proposed 3 km) for old clients. Reject bool/string/fraction/unknown values. Filter before pagination and share the rule for list/detail.
- Calculate Haversine to the confirmed public discovery point, inclusive boundary. Enforce both buyer-selected radius and product radius about that public point, while retaining the existing coarse private-dispatch candidate restriction and all approval/stock/account checks. This is a discovery/business-point rule; it cannot prove delivery to a different saved address. Keep exact private-dispatch-to-owned-delivery-address validation at checkout.
- If the business instead requires exact private-dispatch eligibility during discovery, that is a different privacy contract. It needs explicit approval accepting the inference risk; do not silently remove or weaken the current invariant test. No schema change is mathematically necessary for that alternative.
- Store selected radius alongside source in frontend memory; include both in request and render keys. Radius changes unmount stale results and issue a fresh POST only when a confirmed source exists, without re-prompting GPS. Preserve draft invalidation, permission fallback, empty/error distinction, no-store and minimal responses.
- Reuse the visual selector with a labeled group, aria-pressed buttons, touch targets and focus styles. Keep sample and live catalogues separate. Accuracy warning remains visible; missing/unconfirmed points are excluded, never replaced with zero/PIN centres. Do not claim delivery guaranteed.

## Required verification after approval

| Required verification | Current result |
| --- | --- |
| Actual backend buyer 1/2/3 km filters | BLOCKED / NOT IMPLEMENTED |
| Inside/on/outside each boundary | NOT RUN for new feature; existing geography unit tests pass |
| Smaller seller radius, approval/stock/status exclusions | NOT RUN for new feature |
| List/detail consistency, pagination, missing public point, privacy invariant | NOT RUN for new feature |
| Positive/negative real HTTP radius requests | NOT RUN; no supported radius request exists yet |
| Frontend radius/source switching and late-response clearing | NOT RUN for new feature |
| Isolated PostgreSQL radius fixtures/tests | NOT RUN; stopped before schema/fixture changes |
| Production frontend build | NOT RUN in this investigation; no product code changed |

After implementation, test only identity-pinned QA targets using synthetic public/dispatch points. Cover all three radii, inclusive arithmetic and six-decimal storage boundaries, smaller seller radius, missing/unconfirmed points, dateline/poles, invalid radius/source, GPS/manual/saved-address selection, ownership/RBAC, eligibility, changing radius/source, late responses, empty/error states and exact checkout denial. Verify original/rehearsal are never targets. Do not run existing persistence fixtures directly against populated Chrome QA: they assume a separate rollback-isolated empty database and would need a reviewed QA-specific fixture strategy.

## Chrome acceptance plan — conditional, not executable yet

After approval, migration, implementation and HTTP proof: use isolated frontend 127.0.0.1:5174 and API 127.0.0.1:8001 with the approved QA buyer. Confirm the selected source, switch 1 -> 2 -> 3 km, and verify each fresh POST carries radius_km, stale cards disappear during loading, and returned cards match reviewed synthetic public-point boundary fixtures and seller-radius exclusions. Repeat with manual/GPS/owned address sources; inspect accuracy warnings, empty/error states, keyboard and mobile controls. Existing QA fixtures share one point and do not by themselves demonstrate all distance thresholds. Do not label these future checks PASS or ask the owner to use controls that do not exist.

**Next action:** approve the observable-point contract and, for the recommended public-point option, the additive QA-only migration and synthetic fixture plan. No migrations, original/rehearsal access, deployment, commit, push, dependency installation or security-rule change occurred.
