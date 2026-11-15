# Chrome positive discovery acceptance — Step 37

**Current radius feature update:** QA is now **revision 0009**, OID **50640**, with the separately approved synthetic public discovery point. Follow [LIVE_RADIUS_DISCOVERY_VERIFICATION.md](LIVE_RADIUS_DISCOVERY_VERIFICATION.md) for current 1/2/3 km HTTP evidence, the required QA-backend restart and radius Chrome acceptance. Earlier 0008 observations below are historical; do not rerun initialization or migrations.

**Steps 41–42:** the owner has now verified positive Chrome rendering of both approved QA products (PASS). Negative Chrome acceptance and owner review of the polished UI remain NOT VERIFIED. See [DISCOVERY_NEGATIVE_UI_VERIFICATION.md](DISCOVERY_NEGATIVE_UI_VERIFICATION.md) for the verified synthetic `(1,1)` negative point, current automated evidence and exact positive/negative/positive Chrome sequence. Earlier NOT VERIFIED entries below describe their historical step unless explicitly updated.

## Step 40: authentication permission investigation

15 November 2026. Verified listeners: QA frontend 127.0.0.1:5174 (PID 6048), QA backend 127.0.0.1:8001 (PID 6224), unrelated backend 127.0.0.1:8000 (PID 19728); no 5173 listener. No services were restarted. The served Vite client module embeds API base `http://127.0.0.1:8001/api/v1`; a previously opened tab's cached module was not inspected.

The QA worker's database connection was independently correlated through socket metadata and read-only PostgreSQL session metadata: **whatnot_chrome_qa_20261115, OID 50640, revision 0008**. `verify_chrome_qa_http.py` exited 0: approved buyer login succeeded, discovery returned **2 / 0 / 2**, saved-address fallback returned 2, business counts remained **2 users / 1 seller / 3 products / 1 address / 0 orders**. Original/rehearsal databases were not connected to or modified. Only normal QA quota counters were written.

| Method | Endpoint | HTTP status | Sanitized category |
| --- | --- | --- | --- |
| POST | /api/v1/auth/login | 200 | Approved QA buyer authenticated |
| POST | /api/v1/auth/login | 403 | QA_EMAIL_ADMISSION_DENIED; non-allowlisted synthetic probe |
| OPTIONS | /api/v1/auth/login | 200 | CORS_PREFLIGHT_ALLOWED |
| GET | /api/v1/auth/me | 401 | UNAUTHENTICATED_OR_INVALID_TOKEN; synthetic invalid-token probe |

Additional probes allowed origin `http://127.0.0.1:5174`. No registration was attempted, credentials reset, real tokens extracted or access policies changed. `pnpm test run src/api/client.test.ts src/state/AuthContext.test.tsx` exited 0: **21 tests passed in 2 files**. An initial invocation duplicated the config option and failed before tests; the corrected command above passed.

Code evidence: `backend/app/services/abuse.py:45` denies non-allowlisted email with 403; `backend/app/api/routes/auth.py:12` applies admission before login/registration business operations. `docs/security/run_chrome_discovery_qa.py:93` allows only the two approved synthetic emails. `src/api/client.ts:14` maps every 403 to the reported generic permission message. `src/api/auth.ts:4` and `:5` omit tokens from registration/login; `src/state/AuthContext.tsx:32` clears previous credentials before login. Tokens remain in module memory (`src/api/client.ts:3`), not local/session storage. Reload clears them. Invalid-token authentication was observed to return 401, not 403. Approved authenticated buyer discovery passed; no CORS or CSRF rejection was observed.

**Root cause:** QA admission denial is a confirmed reproducible cause of this message and the likely explanation when another email is attempted. **The owner's exact failing endpoint/status/account category remains NOT VERIFIED**, pending the requested sanitized Chrome Network evidence. The probe is not the owner's captured request. No implementation defect requiring a security-rule change is confirmed.

**Safe correction / resume:** use `http://127.0.0.1:5174/login/buyer` in the separate QA profile, reload and sign in as the existing `chrome-buyer@example.com` using the private DPAPI credential instructions below. Do not register another account or change admission/security settings. A QA server restart changes its independent signing key and requires a new sign-in. Chrome acceptance may resume with this approved buyer; actual owner UI acceptance remains NOT VERIFIED. If this buyer still fails, pause and provide only failed method, endpoint, status and whether the approved buyer was used; never export bodies, headers, tokens or a HAR.

Date: 15 November 2026, Asia/Calcutta. **Step 39 status: schema PASS, fixtures PASS, real QA discovery API PASS, Chrome readiness PASS. Owner Chrome acceptance remains NOT VERIFIED.** The owner approved the fixture plan and the administrator created the destination; initialization and independent verification are complete. No complete real-device end-to-end acceptance is claimed.

The initial provisioning process printed final verified results, then exited with Windows native error **0xC0000005**. It was **not rerun**. Two independent read-only preflights and the real API verifier subsequently exited 0 and verified committed state. This process anomaly remains an unresolved implementation/runtime issue; it is not hidden as an exit-0 provisioning result.

## Step 39 initialization evidence

| Item | Verified result |
| --- | --- |
| Exact schema source | Loopback PostgreSQL port 5432, `whatnot_tests_20261115_a7e394c2`, OID **49265**, revision **0008**, zero business rows |
| Exact destination | Same local server, `whatnot_chrome_qa_20261115`, OID **50640**, expected application-role ownership |
| Empty-target protection | Name/OID/owner checked before restore; no public relations/functions/types or unexpected user schema/extensions; no overwrite/recreation |
| Schema copy | `pg_dump --schema-only` under a consistent exported read-only snapshot; `pg_restore --single-transaction --exit-on-error --no-owner --no-privileges`, no clean/create/drop option |
| Archive listing | Exit 0; **zero TABLE DATA and zero SEQUENCE SET entries**. Existing empty public namespace retained, schema objects copied. |
| Revision metadata | Source revision 0008 verified; metadata initialized after schema-only restoration inside the fixture transaction. No migration or stamp command ran. |
| Fixtures | **2 users, 1 seller profile, 3 products (2 APPROVED, 1 PENDING), 1 owned address, 0 orders**; all approved synthetic relationships/statuses and confirmed `(0,0)` dispatch verified |
| Service checks | Synthetic `(0,0)` returns 2; `(1,1)` returns 0 |
| Actual HTTP checks | Runtime DB identity independently correlated to port-8001 worker; supported/unsupported/supported **2 / 0 / 2**, owned-address fallback **2**; names/prices/shop correct, pending product excluded, no-store, private fields omitted |
| After HTTP | Exact business fixture counts unchanged; normal API quota counters were written only in QA |
| Original/rehearsal access during Step 39 | **None**. Initializer connects only to the approved isolated source and destination; original credentials/settings are read privately to derive connection parameters, without connecting to the original database. |

Schema archive: `C:\Users\DELL\AppData\Local\Temp\WhatNotChromeQA-rxn1r3ss\empty-isolated-0008.dump`.
SHA-256: `8364d29b304c96a9b094956eca8fddbdff2b97f309a667e4f4bb6a4a0264a42e` (independently matched).

Commands actually executed from `backend`:

```powershell
# Executed ONCE after approval/admin creation. Do not repeat restore/seeding.
& .\.venv\Scripts\python.exe ..\docs\security\provision_chrome_discovery_qa.py
# Initial process exit: -1073741819 / 0xC0000005 after committed state/final output.

# Independent read-only checks: both exited 0, exact fixtures/identity verified.
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py
& .\.venv\Scripts\python.exe -X faulthandler ..\docs\security\run_chrome_discovery_qa.py

# Temporary loopback QA server, then real HTTP verifier: verifier exited 0.
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py --serve
# Separate terminal:
& .\.venv\Scripts\python.exe ..\docs\security\verify_chrome_qa_http.py
```

The initializer refuses an existing provisioning manifest or nonempty destination. No retry, reset, data repair, migration, credential reset or original/rehearsal operation was attempted after the native exit. The temporary QA server is stopped after checks; use the repeatable startup below for the owner session.

Evidence: `docs/security/evidence/chrome-qa-provisioning.json`, `chrome-qa-initialization-verification.json`, `chrome-qa-http.json`. None contains a password or token. Actual QA password JSON is encrypted to the provisioning Windows user's DPAPI context, outside the repository.

## 1. Current result and safety boundary

Initial read-only inspection found no manual QA database. The owner then approved the manifest, the administrator created `whatnot_chrome_qa_20261115`, and Step 39 initialized it as recorded above. Original/rehearsal data and the rollback-only automated test database were not reused as manual business fixtures.

The exact approved fixtures are in [CHROME_DISCOVERY_QA_FIXTURES.md](CHROME_DISCOVERY_QA_FIXTURES.md). The real provisioning manifest pins OID 50640. No further approval is needed to use this approved environment. Do not replace the manifest or rerun initialization.

The isolated QA backend will bind **127.0.0.1:8001**, frontend **127.0.0.1:5174**. Existing original-backed ports 8000/5173 are outside this test. The new launcher refuses a missing/wrong manifest, original/rehearsal/test OIDs, unexpected server/connection options and incorrect fixtures. Before serving, it verifies actual QA database name, pinned OID, current-role ownership, revision 0008 and synthetic fixture readiness using a read-only transaction. While serving, an SQL guard verifies the QA database name/OID/owner before each SQLAlchemy statement. QA authentication uses its own ephemeral child-process signing key, so QA tokens cannot authenticate against the original backend. Original `.env`, signing key and processes remain unchanged.

Login/discovery legitimately write quota counters. Therefore **do not point these tests at the original database even for apparently read-only HTTP discovery**. All commands below are conditional on completed, separately approved QA provisioning.

## 2. Test matrix: current evidence, not expected results presented as passes

| Test | Current result | Evidence / remaining action |
| --- | --- | --- |
| Read-only initial inventory | PASS | Historical `discovery-inventory.json`; initially absent, subsequently approved and initialized |
| QA startup refuses missing provisioning | PASS | Launcher exited 1 with `Manual QA provisioning manifest missing; fixture approval/provisioning required`, before connecting to any database |
| Launcher isolation unit checks | PASS | 15 tests: wrong/missing manifest, protected OIDs, remote/wrong-port/unrelated/query-overridden target rejected; synthetic config only |
| Manual QA database identity/readiness | PASS | OID 50640, expected owner, revision 0008, exact fixtures; independent read-only preflights exited 0 |
| Actual QA login and HTTP positive/negative discovery | PASS | Real QA API returned 2 / 0 / 2; runtime QA database identity correlated before login; no original API POST |
| Product cards, prices and seller data in buyer UI | NOT VERIFIED | Owner Chrome check below; focused mocked UI coverage is separate |
| Supported → unsupported → supported, no stale cards | NOT VERIFIED | Owner Chrome check below; focused mocked regression exists |
| PIN saved-address fallback in actual QA UI | NOT VERIFIED | Requires QA Home fixture and owner check |
| Desktop/mobile-width PIN CSS geometry | PASS | Static headless Chrome at 1440, 390 and 320 px; no app/API/database used |
| Full buyer PIN layout on desktop/mobile Chrome | NOT VERIFIED | Owner must inspect the actual application, wrapping, keyboard and touch behavior |
| Focused frontend tests | PASS | 43 tests, 5 files; mocked APIs/synthetic coordinates |
| Production frontend build | PASS | TypeScript + Vite exited 0 |
| Real-device positive GPS discovery | NOT VERIFIED | This plan intentionally uses manual synthetic points, not a fake GPS override |
| Live buyer-selectable 1/2/3 km filter | NOT VERIFIED / absent | NOT IMPLEMENTED; no radius feature was added |

No actual QA HTTP/UI test is marked FAIL simply because it has not been run. An unmet fixture/provisioning prerequisite blocks execution and remains NOT VERIFIED.

## 3. Required fixture approval and expected inventory

The approved, initialized manifest specifies exactly **2 synthetic users, 1 confirmed seller profile, 3 products, 1 buyer-owned address, 0 orders**. No administrator account, real account, real point or external image was inserted.

| Fixture | Expected value |
| --- | --- |
| Buyer | `chrome-buyer@example.com`, role BUYER, active; private new QA password |
| Seller | `chrome-seller@example.com`, role SELLER, active; shop **Chrome QA Maker**, verified false |
| Dispatch | Synthetic `(0,0)`, explicitly confirmed |
| Positive product | **QA Nearby Vase**, **₹250.00**, stock 5, APPROVED, active, seller radius 2 km |
| Positive product | **QA Nearby Basket**, **₹125.50**, stock 4, APPROVED, active, seller radius 1 km |
| Excluded product | **QA Pending Sample**, ₹99.00, PENDING; must not appear in buyer discovery |
| Owned address | **QA Home**, synthetic `(0,0)`, test PIN **999999**; PIN is not geocoded |

Supported manual point is `(0,0)`; unsupported manual point is `(1,1)`. These are explicitly synthetic inputs, not device positions. The existing manual Latitude/Longitude inputs provide the manual-location QA path. No new GPS mock, auto-selection or production QA-mode toggle was added. The synthetic account/shop/product names identify the QA session visibly.

`docs/security/evidence/chrome-qa-provisioning.json` records actual OID 50640, database name, revision 0008 and fixture version `chrome-discovery-v1`, with no password/token. The startup preflight checks stored fixture values, role/hash properties, prices/stock/status, confirmed dispatch, address ownership, two positive service results and zero unsupported-point results. It fails closed on any mismatch. No create/seed/migrate/cleanup operation exists in the launcher.

## 4. Exact Windows PowerShell startup commands

Provisioning is complete. Run these in new terminal windows. Existing dependencies are sufficient. Do not edit or copy private URLs into frontend variables.

### Backend window

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: QA identity/fixtures are not verified.' }
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py --serve
```

Expected current preflight: `status: PASS`, database `whatnot_chrome_qa_20261115`, pinned OID **50640**, revision **0009**, business counts 2/1/3/1/0, positive products 2, negative products 0. `--serve` repeats preflight immediately before startup. Any mismatch must stop; do not substitute an original-database Uvicorn command.

The launcher derives the **explicit QA target name only** from the existing local connection settings and uses credentials privately in memory. It never connects to the original for preflight or serving. It changes only the new child's environment: development profile, CORS origin `http://127.0.0.1:5174`, two synthetic allowlisted emails, abuse limits enabled, email delivery disabled and a separate ephemeral QA signing key. It binds only loopback, disables access logging, starts no reload watcher/worker and sends no email. A restart changes QA tokens; sign in again. Stop with Ctrl+C. Do not automatically stop unrelated listeners if port 8001 is occupied.

Expected URLs:

- API: `http://127.0.0.1:8001/api/v1`
- Health: `http://127.0.0.1:8001/api/v1/health`
- Readiness: `http://127.0.0.1:8001/api/v1/ready`
- Development API docs: `http://127.0.0.1:8001/docs`

### Frontend window

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8001/api/v1'
Write-Host 'ISOLATED MANUAL-LOCATION QA: use synthetic (0,0) and (1,1); these are NOT browser GPS.'
& 'C:\Program Files\nodejs\corepack.cmd' pnpm dev --host 127.0.0.1 --port 5174 --strictPort
```

App: `http://127.0.0.1:5174`; buyer login `/login/buyer`; buyer discovery `/buyer`. Keep `127.0.0.1`, port 5174 and the API prefix exactly as shown. Do not use the original application's port 5173. Closing this separate terminal discards its environment override.

### Separate visible Chrome QA profile

```powershell
$qaChromeProfile = Join-Path $env:TEMP ('WhatNotChromeAcceptance-' + [guid]::NewGuid().ToString('N'))
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' --user-data-dir="$qaChromeProfile" --no-first-run --new-window 'http://127.0.0.1:5174/login/buyer'
```

This creates a separate local Chrome profile; no existing profile or data is deleted. It is an interactive owner test, not an automated claim of browser acceptance.

## 5. Real HTTP API check before Chrome discovery

Only after the verified QA server is running, use a third PowerShell window. New QA passwords are generated, hashed and protected with Windows-user DPAPI; existing user credentials are unchanged. To load them **locally under the same Windows account**, with no plaintext console output:

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not'
$qaManifest = Get-Content -LiteralPath .\docs\security\evidence\chrome-qa-provisioning.json -Raw | ConvertFrom-Json
$qaProtected = Get-Content -LiteralPath $qaManifest.private_credentials_path -Raw
$qaSecure = ConvertTo-SecureString -String $qaProtected
$qaCredentials = [System.Net.NetworkCredential]::new('', $qaSecure).Password | ConvertFrom-Json
```

For manual Chrome sign-in, view only the new buyer credential in a private local dialog (do not screenshot/share it):

```powershell
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show(('Email: ' + $qaCredentials.buyer_email + [Environment]::NewLine + 'Password: ' + $qaCredentials.buyer_password), 'Isolated QA buyer credentials - private')
```

Never print/export the login response or Authorization header. Alternatively, the automated safe HTTP verifier above decrypts the password privately in memory and reports only results. The following manual check uses `$qaCredentials` already loaded in this same window:

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
& .\.venv\Scripts\python.exe ..\docs\security\run_chrome_discovery_qa.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: QA identity/fixtures are not verified.' }
Invoke-RestMethod 'http://127.0.0.1:8001/api/v1/ready'
$qaLoginBody = @{email=$qaCredentials.buyer_email; password=$qaCredentials.buyer_password} | ConvertTo-Json
$qaLogin = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8001/api/v1/auth/login' -ContentType 'application/json' -Body $qaLoginBody
$qaLoginBody = $null
$qaHeaders = @{Authorization=('Bearer ' + $qaLogin.access_token)}
$qaPositive = Invoke-WebRequest -UseBasicParsing -Method Post -Uri 'http://127.0.0.1:8001/api/v1/discovery/products' -Headers $qaHeaders -ContentType 'application/json' -Body '{"location":{"latitude":0,"longitude":0}}'
$qaProducts = @($qaPositive.Content | ConvertFrom-Json)
if ($qaPositive.StatusCode -ne 200 -or $qaProducts.Count -ne 2) { throw 'Positive QA discovery failed.' }
if ((($qaProducts.name | Sort-Object) -join '|') -ne 'QA Nearby Basket|QA Nearby Vase') { throw 'Unexpected QA products.' }
$qaProducts | Select-Object name,price,shop_name,stock_quantity,delivery_radius_km
$qaNegative = Invoke-WebRequest -UseBasicParsing -Method Post -Uri 'http://127.0.0.1:8001/api/v1/discovery/products' -Headers $qaHeaders -ContentType 'application/json' -Body '{"location":{"latitude":1,"longitude":1}}'
if ($qaNegative.StatusCode -ne 200 -or $qaNegative.Content.Trim() -ne '[]') { throw 'Negative QA discovery failed.' }
Write-Host 'QA HTTP checks passed: supported 200 with two products; unsupported 200 [].'
```

Expected positive response: only the two approved fixture products, their prices/stock, `shop_name: Chrome QA Maker`, `is_verified: false`, delivery radii 1/2 and `delivery_eligibility: CONFIRMED_AT_CHECKOUT`. Do not interpret seller radii as buyer-selected filters. No pending product, precise seller point, private contact/address or exact distance should be returned. Expect `Cache-Control: no-store`. Stop on 401/403/422/429/503 or unexpected data; do not weaken authentication, admission, validation, rate limits or availability rules.

The startup SQL guard prevents original-database writes even if an app connection is misconfigured. For independent runtime attribution, compare the pinned QA OID and `pg_stat_activity` database/client ports with the Windows worker owning port 8001, as in the Step 36 verifier, before recording identity acceptance. The existing `verify_discovery_backend.ps1` is specifically for original port 8000; do not use it to certify QA port 8001.

## 6. Exact owner Chrome acceptance steps

1. Confirm startup preflight PASS and the real HTTP checks above. In the separate Chrome profile, open the QA login URL and sign in as **Chrome QA Buyer**. Verify the browser origin is `127.0.0.1:5174`. DevTools Network must show the API origin `127.0.0.1:8001`; stop immediately if it targets port 8000 or any non-QA host.
2. Open `/buyer`, clear text search if present, open DevTools Network and filter `discovery/products`. Keep Preserve log off; never export tokens, login payloads or real locations. There should be no discovery request until a location source is explicitly selected.
3. **MANUAL SYNTHETIC POSITIVE TEST — NOT GPS:** do not click **Use current location** or enable a Sensors geolocation override. Enter Latitude `0`, Longitude `0` in the existing manual inputs. Press **Use for discovery**. Inspect the resulting POST body privately: `{"location":{"latitude":0,"longitude":0}}`. Expect HTTP 200 and two fixture products.
4. Verify two actual buyer product cards: **QA Nearby Vase / ₹250.00** and **QA Nearby Basket / ₹125.50**, both with **Chrome QA Maker** and View links. The seller is not verified; no verified badge should be invented. The pending sample must be absent. No sample-distance badges or exact seller distance should appear. Images are optional and deliberately absent from these fixtures.
5. **MANUAL SYNTHETIC NEGATIVE TEST:** change Latitude to `1`. As soon as the draft changes, the old cards should disappear and the location become unselected. Change Longitude to `1`; do not submit until both are correct. Before confirmation, there must be no automatic discovery POST. Press **Use for discovery**. Expect HTTP 200 `[]` and **No products nearby**, with neither old card visible.
6. Change both inputs back to `0`, confirm and verify the same two cards return. Repeat quickly with Slow 3G throttling in DevTools: a late response for an abandoned location must not bring old cards back. Reset throttling after the test. Do not compare precise device movement; this test deliberately changes synthetic manual inputs.
7. PIN fallback: type test PIN `999999`; confirm old source/results clear, choose **Use QA Home for discovery** and inspect a POST containing only its owned `address_id`. Expect the two approved cards. Enter unmatched test PIN `000000`: expect no matching address and no discovery call; an arbitrary PIN must not generate a coordinate or listing.
8. Desktop layout: at about 1440 px viewport width, check PIN label above its input, readable spacing, comfortable padding, visible focus outline and no overlap with the saved-address button/help text. The field is intentionally capped at 28 rem rather than stretched across the whole panel.
9. Mobile layout: use DevTools responsive viewport widths **390 px and 320 px**. Confirm no horizontal page scrolling or clipped PIN field; label/input/help/button wrap cleanly; input is at least 48 px tall. On a real mobile Chrome browser, repeat keyboard/touch checks if a safely reachable HTTPS QA environment is later available. A desktop emulated viewport is not a real-mobile-device pass. Do not open the local QA API publicly to achieve this.
10. Error separation: while keeping only QA tabs open, stop the QA backend with Ctrl+C, refresh discovery, and expect an unavailable/unreachable API notice rather than old cards or a false **No products nearby** success. Restart with the verified launcher, sign in again (ephemeral key changed) and repeat the manual positive check. Do not stop the original backend.

No buyer radius selector is expected on the live page; none was added. The sample route's 1/2/3 buttons are outside this acceptance test. The existing browser location button remains an independent real-device check; using it may legitimately produce zero QA products because real coordinates differ from synthetic `(0,0)`. Do not call that a GPS failure or label the manual synthetic positive case as GPS.

## 7. Evidence checklist

- [ ] Approval and provisioning record for exactly the new QA database/fixtures; actual OID, owner check and revision 0008, no secrets.
- [ ] Fresh preflight PASS before HTTP and Chrome tests; QA API/frontend URLs and runtime DB attribution.
- [ ] Real API positive HTTP 200, two expected names/prices/shop, no pending product or private point.
- [ ] Real API negative HTTP 200 `[]`, no original API requests.
- [ ] Owner Chrome screenshot showing the QA origin, two cards/prices/shop and manual-synthetic label in the test record. Crop/redact DevTools headers/login/password/token; these coordinates are synthetic only.
- [ ] Unsupported point shows empty state, old cards clear before confirmation and cannot reappear from a late response; supported point restores two cards.
- [ ] PIN owned-address and unmatched-PIN results, with no postal precision claim.
- [ ] Desktop 1440 px and mobile-width 390/320 px layout evidence; separately identify emulation versus actual mobile device.
- [ ] Error notice is distinct from a valid empty result.
- [ ] Record browser/version, viewport, timestamp (IST), manual input source and PASS/FAIL for each step. Do not attach unredacted HAR files or console dumps.
- [ ] Explicit final verdict: manual Chrome positive discovery PASS/FAIL/NOT VERIFIED. Real-device GPS acceptance is a separate verdict.

## 8. Changes and fresh automated verification

Confirmed PIN issue: the standalone saved-address label was outside `.product-form`, so shared form spacing/padding did not apply. A narrowly scoped selector in `src/styles/index.css` now supplies a grid label with 8 px gap, a full available-width input capped at 28 rem, 16 px horizontal padding and a 48 px minimum height. It changes no location/query/radius behavior.

`scripts/verify_discovery_pin_layout.mjs` launches an owned isolated headless Chrome profile, blocks all page network requests and loads static synthetic markup with the actual stylesheet. It does not start an application/API or connect to a database. Before the correction all three widths failed: height 24 px, padding 2 px, label gap 0. After correction all three passed: height 48 px, padding 16 px, gap 8, label above input and no page/input overflow. Input widths: 448 px desktop, about 311 px at 390, about 241 px at 320. This establishes CSS geometry for the representative fragment, not full-application owner acceptance.

| Check | Fresh result | Evidence |
| --- | --- | --- |
| Read-only inventory | Exit 0; no manual QA database/fixtures | `docs/security/evidence/discovery-inventory.json` |
| Chrome layout reproduction | Exit 1, three expected geometry failures before fix | `docs/security/evidence/chrome-pin-layout-before.json` |
| Chrome layout after fix | Exit 0, all three widths passed | `docs/security/evidence/chrome-pin-layout.json` |
| QA launcher fail-closed check | Expected exit 1, missing provisioning manifest | Command output; no DB connection |
| Launcher isolated-config tests | Exit 0, **15 passed**, 9.90 s | `docs/security/evidence/chrome-qa-launcher-tests.xml` |
| Focused location/discovery frontend | Exit 0, **43 passed**, 5 files, 82.50 s | `docs/security/evidence/chrome-acceptance-frontend.log` |
| Production frontend build | Exit 0, TypeScript + Vite, 1,939 modules, Vite 12.13 s | `docs/security/evidence/chrome-acceptance-build.log` |

Frontend command: `node node_modules/vitest/vitest.mjs run --config vite.config.ts src/LocationDiscovery.test.tsx src/location/geolocation.test.ts src/components/LocationPicker.test.tsx src/components/DispatchLocation.test.tsx src/api/discovery.test.ts --pool=threads --maxWorkers=1 --no-file-parallelism`.

Launcher tests, from backend: `.venv/Scripts/python.exe -m pytest -q -W error ../docs/security/test_chrome_qa_launcher.py --junitxml=../docs/security/evidence/chrome-qa-launcher-tests.xml`. These use mocked synthetic settings and temporary manifests, never a real DB. Step 36's 77 PostgreSQL-backed business tests remain historical evidence; they do not certify this not-yet-provisioned manual environment. No broad backend business regression was repeated for this CSS/preparation change.

Added preparation tools: `run_chrome_discovery_qa.py` and its isolation tests, the layout check, this acceptance guide and fixture manifest. No original records, schema, migrations, credentials or source API settings were modified. No deployment, commit or push occurred.

## 9. Remaining issues / first next action

Approval, administrator creation, schema initialization and fixtures are complete. Real QA API checks passed. **First remaining acceptance step: the owner starts the isolated frontend/backend and performs the Chrome checks.** Original-backed, mocked, static-layout and actual QA HTTP evidence remain separate from owner UI acceptance.

The launcher and real serving path were exercised with the populated approved fixtures. Startup commands repeat only read-only readiness checks and serving; no automatic schema creation, migration, insertion or destructive cleanup is included. Do not rerun restore/seeding. Investigate the initializer's post-result native exit separately; it did not recur in the two independent read-only preflights or the successful HTTP verifier, but its root cause is not established.

Live buyer radius filtering remains NOT IMPLEMENTED. Positive actual GPS/device accuracy/movement, complete mobile-device acceptance and HTTPS-domain acceptance remain NOT VERIFIED. Broader production-readiness/privacy/backup/monitoring gates and the intermittent full-suite frontend issue remain outside this scoped preparation. Deployment is not authorized.
