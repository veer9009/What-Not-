# Live location verification

Date: 15 November 2026. Scope: current working tree, local automated verification.

**Follow-up:** the owner subsequently reported successful Chrome acquisition (about 206 m browser-reported accuracy) and `200 []`. The fresh [empty-discovery investigation](LIVE_LOCATION_EMPTY_DISCOVERY_INVESTIGATION.md) independently verifies the running backend database, records current aggregate inventory, adds a repeated-detection regression and provides a private read-only point check. The results below remain the earlier verification baseline; owner-reported acquisition is distinct from an agent-observed real-device run and from measured physical accuracy.

**LIVE LOCATION: NOT VERIFIED on an actual device.** Deterministic browser-API mocks and PostgreSQL-backed HTTP/service tests verify the software paths below. No real Chrome permission grant or device location provider was exercised during this task. The older Edge/CDP run in `CURRENT_LOCATION_BETA_FIX.md` used an emulated position and is not real GPS evidence.

**Live buyer-selectable 1/2/3 km discovery: FAIL / absent.** Those buttons exist in the sample catalogue. Live discovery instead uses each product's seller-configured radius and a coarse locality margin. Exact delivery eligibility is enforced at checkout. Do not certify precise buyer-radius discovery from the sample buttons or from passing checkout tests.

No deployment, AWS resource creation, credential change, original-database mutation, commit or push was performed. Automated database fixtures targeted only the verified existing test database. No application server was started against the original database.

## 1. Actual implementation and evidence

Paths and line numbers refer to this working tree, including existing uncommitted recovery changes.

| Area | Actual behavior | Evidence | Result |
| --- | --- | --- | --- |
| User action | Buyer `/buyer` has **Use current location**, not “Detect My Location.” Clicking starts acquisition; **Use for discovery** confirms the draft. Seller dispatch uses the same picker with a separate persistence confirmation. | `src/components/LocationPicker.tsx:15`, `:23`, `:32`; `src/pages/DiscoveryPages.tsx:14`; `src/components/DispatchLocation.tsx:8` | PASS, source + mocked UI |
| API/provider | `navigator.geolocation.getCurrentPosition`; no SDK, fixed-coordinate fallback, address reverse lookup or Google request. | `src/location/geolocation.ts:21` | PASS, source + mocks |
| Coordinates | Finite/range checks; latitude ±90, longitude ±180; numbers rounded to six decimal places. Rounding is representation, not proof of six-place accuracy. | `src/location/geolocation.ts:17`; `backend/app/services/inputs.py:14`; `backend/app/schemas/location.py:5` | PASS |
| Secure context | Explicit error when `isSecureContext === false`; absent provider has an unsupported error. HTTPS or a browser-trusted loopback context is needed. Ordinary LAN-IP HTTP is not an equivalent substitute. | `src/location/geolocation.ts:24`; helper tests | PASS in mocks; actual hosting NOT VERIFIED |
| Permissions | Browser owns prompt/granted/denied behavior. The app does not call `navigator.permissions.query`, request on mount, or repeatedly poll permission. Denied callback / `SecurityError` gets sanitized guidance. Already-granted permission still requires the app button. | `src/location/geolocation.ts:29`; `src/components/LocationPicker.test.tsx:29` | PASS in mocks; Chrome prompt/granted/denied NOT VERIFIED |
| Timing/loading | High-accuracy hint, `maximumAge: 0`, 10 s acquisition timeout plus 30 s whole-interaction deadline. “Locating...” prevents duplicate requests and confirmation. Errors distinguish denied, unavailable, timeout, unsupported, insecure and invalid values. | `src/location/geolocation.ts:35`, `:46`; `src/components/LocationPicker.tsx:15` | PASS in mocks |
| Accuracy | Browser estimate is retained only in picker memory and displayed in metres, rounded upward. At least 1,000 m triggers advice to retry/use a known saved address, because the smallest delivery radius is 1 km. It does not guarantee accuracy or block deliberate manual confirmation. Missing/invalid estimate is labeled unknown. | `src/location/geolocation.ts:40`; `src/components/LocationPicker.tsx:9`, `:32` | PASS after focused fix |
| Changed/stale location | One-shot acquisition, not tracking. New acquisition/manual edits clear the old discovery source and accuracy; abort/version checks ignore late callbacks. Result components are keyed by source, and resource version checks ignore old responses. Logout/account changes reset discovery context. | `src/components/LocationPicker.tsx:13`; `src/pages/DiscoveryPages.tsx:18`, `:28`; `src/state/useResource.ts:8`; `src/App.tsx:24` | PASS for explicit changes; automatic movement detection NOT IMPLEMENTED |
| Transmission/storage | Confirmed device point goes in authenticated POST JSON to `/api/v1/discovery/products`; detail also uses POST. No precise coordinates in the URL or BuyerProduct response. Discovery source is React memory, with no permanent device-location storage. The discovery route does write an abuse-quota counter in normal development/production; “transient location” does not mean the entire request is read-only. | `src/api/discovery.ts:12`; `src/state/DiscoveryContext.tsx:6`; `backend/app/api/routes/discovery.py:12`; `backend/app/services/abuse.py:33` | PASS, source + tests |
| PIN/manual fallback | PIN filters the authenticated user's saved addresses. User must choose a matching address; API receives `address_id` and enforces ownership. An arbitrary PIN is not geocoded. Unknown PIN does not fabricate a centre or call discovery. Manual coordinate entry also works. New saved addresses require coordinates. | `src/pages/DiscoveryPages.tsx:19`; `backend/app/services/discovery.py:25`; `backend/app/services/inputs.py:68` | PASS; general PIN-only discovery unavailable |
| Nearby listings | Approved, active, in-stock products from active sellers with confirmed dispatch locations. Backend uses Haversine kilometres against a 0.01-degree seller-cell centre, accepting distance up to product radius + 0.8 km. Maximum first page is 100; current UI does not paginate beyond that. | `backend/app/repositories/products.py:40`; `backend/app/services/discovery.py:13`, `:38`, `:46`; `src/pages/DiscoveryPages.tsx:32` | PASS for documented locality contract |
| Exact distance | Backend uses actual saved delivery-address and seller dispatch coordinates at order creation; it does not trust device position or client distance/eligibility. Inclusive 1/2/3 km boundary with 1e-9 km floating arithmetic tolerance. Buyer moving does not change seller dispatch or delivery address. | `backend/app/services/geography.py:5`, `:17`, `:27`; `backend/app/services/orders.py:86`, `:97` | PASS in numeric + database tests |
| Sample selector | Sample route `/buyer/samples` uses stored sample `distance`, independently of device coordinates. Buttons 1/2/3 remain unchanged. | `src/components/Shared.tsx:22`; `src/pages/BuyerPages.tsx:21`; `src/utils/products.ts:8`; `src/utils/products.test.ts:7` | PASS for samples only |
| Privacy/logging | Discovery responses omit seller coordinates, exact distances, private address and phone. Error handler logs event/class, not submitted location; validation omits input values. Proposed Nginx format omits paths/query/body/IP. Saved delivery addresses and confirmed seller points intentionally persist, and authorized owner UI displays them. Proxy/production logging and broader lifecycle disclosure are not certified by this task. | `backend/tests/persistence/test_discovery.py:21`; `backend/app/api/errors.py:30`, `:49`, `:54`; `deploy/nginx/whatnot.conf.template:3` | PASS for inspected discovery path; deployed logs NOT VERIFIED |

Browser geolocation can use network-based estimates; it does not promise satellite GPS or the device's true location. High accuracy is a request the browser may ignore. Permission/visibility waits differ from acquisition timeout, and suspended tabs can delay JavaScript timers. See the primary [W3C Geolocation specification](https://www.w3.org/TR/geolocation/). No Google Maps or Geocoding integration is required here.

## 2. Confirmed bugs, fixes and limitations

1. **Fixed: missing accuracy information.** Previously `coords.accuracy` was discarded, so a broad network estimate looked like a precise fix. Now the picker shows the estimate or explicitly says it is unavailable, warns at 1 km, clears stale estimates on edit/re-detection and preserves the API's latitude/longitude-only contract. Seven expected failures were observed before the fix; the focused suite then passed.
2. **Clarified: one-time location can age.** The picker now tells the user to detect again after moving. There is no watch, acquisition-time display, expiry, or refresh of location when pressing **Refresh nearby products**. Returning to discovery in the same session can reuse the last confirmed source. This is a remaining freshness limitation, not automatic tracking.
3. **Unchanged product gap:** no live buyer-radius selector. Existing audit rows K2/L1 already document this. Adding one needs an agreed privacy-preserving query/response contract; this verification did not change discovery semantics or disclose seller points. If exact selectable live radii are mandatory for pilot acceptance, that requirement remains FAIL.
4. **Expected privacy behavior:** a candidate may appear outside the exact delivery boundary. A listing is not a guarantee of delivery; checkout is authoritative using the selected saved address. No frontend Haversine filter is applied to private seller coordinates.
5. **Expected missing-data behavior:** seller/address coordinate columns are non-null and bounded. A locationless seller or PIN-only saved address cannot be persisted as a valid marketplace location. Unconfirmed seller dispatch is excluded. There is no fallback to `(0,0)`; an explicitly entered valid `(0,0)` remains legitimate synthetic input.
6. **No actual provider failure reproduced.** This task found and fixed an observable code gap; it cannot identify an unobserved device/OS/network failure as the cause of a real user's GPS problem.

Files changed for this task (other pre-existing working-tree changes preserved):

- `src/location/geolocation.ts`, `src/location/geolocation.test.ts`
- `src/components/LocationPicker.tsx`, `src/components/LocationPicker.test.tsx`
- `src/utils/products.test.ts`
- `backend/tests/persistence/test_discovery.py`
- `docs/security/run_existing_server_tests.py` (location-only selection, fresh temporary fixture folder, sanitized failure-stage diagnostics)
- This report and `docs/security/evidence/live-location-*` verification artifacts (logs are ignored by Git).

No backend application behavior, schema, dependency or authorization change was made.

## 3. Automated verification

All coordinates/accounts/listings in tests are deterministic synthetic fixtures. No fake listing was added to the application or original database.

| Check | Command / fresh result | Evidence |
| --- | --- | --- |
| Location UI/helper/dispatch/discovery | `node node_modules/vitest/vitest.mjs run --config vite.config.ts src/location/geolocation.test.ts src/components/LocationPicker.test.tsx src/components/DispatchLocation.test.tsx src/LocationDiscovery.test.tsx --pool=threads --maxWorkers=1 --no-file-parallelism` — **exit 0; 41 passed, 4 files; 46.36 s** | `docs/security/evidence/live-location-frontend.log` |
| API contract + sample 1/2/3 boundaries | Same Vitest options with `src/api/discovery.test.ts src/utils/products.test.ts` — **exit 0; 8 passed, 2 files; 20.28 s** | `docs/security/evidence/live-location-api-sample.log` |
| Backend numeric/schema | From `backend`: `.venv/Scripts/python.exe -m pytest -q -W error tests/test_geography.py tests/test_discovery_schemas.py --junitxml=../docs/security/evidence/live-location-backend-unit.xml` — **exit 0; 44 passed; 0.86 s console duration** | `docs/security/evidence/live-location-backend-unit.xml` |
| PostgreSQL-backed location integration | From `backend`: `.venv/Scripts/python.exe ../docs/security/run_existing_server_tests.py --location` — **exit 0; 76 passed, 1 historical migration test deselected; 0 failures/errors/skips; 25.751 s XML duration** | `docs/security/evidence/live-location-database-tests.json`; retained pytest log below |
| Production frontend build | `npm.cmd run build` — **exit 0; TypeScript + Vite production build passed; 1,939 modules, Vite 4.65 s** | `docs/security/evidence/live-location-build.log` |
| Whitespace | `git diff --check` — **exit 0**, only LF/CRLF notices | Command output |

Final integration evidence: **1,573 guarded SQL statements**, `original_rows_unchanged: true`, `isolated_test_rows_unchanged: true`, `quota_cleanup_performed: false`. Retained synthetic pytest output: `C:\Users\DELL\AppData\Local\Temp\WhatNotLocationQA-u83yhnmf\pytest.log` (`76 passed, 1 deselected in 25.77s` console output). Total focused checks: **49 frontend + 44 backend numeric/schema + 76 PostgreSQL-backed tests**. No test was skipped in those executed selections; the one explicit deselection is described below. PowerShell formats npm's stderr notices as `NativeCommandError` records in the build log; the process exit was **0**, and both TypeScript and Vite completed successfully.

The dedicated database target is `whatnot_tests_20261115_a7e394c2`, OID `49265`, schema `0008`. The runner checks name/OID/ownership immediately before each SQL statement, disables database-creation fixtures, forces source connections to transaction read-only, skips quota cleanup and uses outer rollback transactions. Original and isolated-test business-row snapshots are compared before/after. PostgreSQL sequences can advance in the test database despite row rollback; unchanged row snapshots do not imply an identical test database sequence state.

The historical dispatch migration test is deliberately deselected: it creates fresh databases and performs a downgrade and is outside this task. No downgrade, reset or migration was run. Other relevant discovery, seller dispatch, authorization and order-geography tests are included.

Earlier attempts are not counted as passes: two stopped before fixture copying because the old recovery directory was unwritable; a subsequent run had 19 passes and a new test's string/Decimal comparison failure; after correcting the baseline, 76 passed but the historical migration test's fixture was blocked because an absolute-path exclusion did not match its collected name. Selection now excludes that test by name while retaining the fail-closed fixture guard. Both executed failed runs verified original/test business rows unchanged. No assertion or timeout was loosened to force a pass.

Coverage includes permission-denied, unavailable, timeout, unsupported/insecure contexts, no callback, late callback, no request on mount, explicit confirmation, invalid coordinates, inaccurate/unknown accuracy, PIN fallback, unknown PIN, numeric POST bodies/no URL/storage leakage, stale discovery responses, logout reset, empty results and sanitized backend failure. Database checks cover 1/2/3 km candidates, far-away exclusion, near-exact and arithmetic boundaries at checkout, unconfirmed dispatch, missing coordinates, ownership/roles, moved buyer vs saved address, seller dispatch updates and spoofed geography rejection.

The complete frontend suite and its intermittent registration timeout were not re-certified here; see `MORNING_DEPLOYMENT_HANDOFF.md` and `PRODUCTION_READINESS_AUDIT.md`. Focused location passes are not production readiness or five-user end-to-end acceptance.

## 4. Exact local startup without writing the original database

Use a **separate local QA database**, named `whatnot_location_qa_20261115`, provisioned at revision `0008` with synthetic accounts/products and a separate authorized QA administrator if seller moderation is to be tested. Do not clone real personal data for these checks. Provisioning/QA seeding was not performed during this verification. If this database does not exist, have the owner/DB administrator provision it using the isolated-database procedure before running these commands. Do not substitute `whatnot_app_dev`, the protected rehearsal database or the automated-test database.

This prerequisite matters: normal login/discovery consumes durable quota counters, and registration/saved-address/dispatch/order actions write data. Merely starting with the existing backend `.env` and then browsing would therefore not preserve the original database's read-only constraint. These commands refuse that target. Do not run database-backed tests concurrently with a browser QA session.

Backend PowerShell window (URL is entered privately, never pasted into a report):

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
$qaUrl = Read-Host 'Enter the PostgreSQL SQLAlchemy URL for whatnot_location_qa_20261115' -AsSecureString
$env:DATABASE_URL = [System.Net.NetworkCredential]::new('', $qaUrl).Password
$env:WHAT_NOT_ENVIRONMENT = 'development'
$env:WHAT_NOT_EMAIL_PROVIDER = 'disabled'
$env:WHAT_NOT_CORS_ORIGINS = '["http://127.0.0.1:5173"]'
@'
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.core.config import Settings
url = make_url(Settings().database_url.get_secret_value())
if (url.database != 'whatnot_location_qa_20261115'
        or url.host not in {'localhost', '127.0.0.1', '::1'}
        or (url.port or 5432) != 5432 or url.query):
    raise SystemExit('STOP: target is not the dedicated loopback QA database')
engine = create_engine(url, hide_parameters=True, connect_args={
    'options': '-c default_transaction_read_only=on -c statement_timeout=5000'})
try:
    with engine.connect() as connection:
        name = connection.scalar(text('SELECT current_database()'))
        revision = connection.scalar(text('SELECT version_num FROM alembic_version'))
        if name != 'whatnot_location_qa_20261115' or revision != '0008':
            raise SystemExit('STOP: QA identity/revision mismatch')
    print('Dedicated QA database identity and revision 0008 verified')
except Exception:
    raise SystemExit('STOP: QA preflight failed; connection details suppressed') from None
finally:
    engine.dispose()
'@ | & .\.venv\Scripts\python.exe -
if ($LASTEXITCODE -ne 0) { throw 'Do not start the backend: QA isolation is not verified.' }
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Keep existing credentials/signing key unchanged. No automatic migration, reload watcher, background worker or seed command is included. If an allowlist is configured, use only synthetic accounts already authorized for that QA environment. Never switch off admission controls to work around a 403. After stopping with Ctrl+C, close this window to discard its private environment.

Expected API `http://127.0.0.1:8000/api/v1`; health `http://127.0.0.1:8000/api/v1/health`; readiness `http://127.0.0.1:8000/api/v1/ready`; local development docs `http://127.0.0.1:8000/docs`.

Frontend in a second PowerShell window:

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api/v1'
& 'C:\Program Files\nodejs\corepack.cmd' pnpm dev --host 127.0.0.1 --port 5173 --strictPort
```

Expected app `http://127.0.0.1:5173`; buyer sign-in `/login/buyer`, discovery `/buyer`. Use this loopback origin consistently; Chrome permissions are origin-specific. `--strictPort` prevents Vite moving to a port outside the CORS list. No installation is needed for this checkout.

Optional third PowerShell window:

```powershell
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/health'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/ready'
```

A healthy endpoint is not evidence of working authentication, valid listings or actual device location.

## 5. Owner Chrome verification

1. Enable Windows Location services and allow desktop apps/browser access. Open Chrome directly at `http://127.0.0.1:5173/login/buyer`, not inside an iframe or over a LAN-IP HTTP URL. Sign in with the synthetic QA buyer. Open DevTools, clear Network, filter `discovery/products`; keep the tab foregrounded.
2. In Console, inspect **only capabilities/permission**, not precise coordinates:

   ```javascript
   ({ secure: window.isSecureContext, geolocationAvailable: !!navigator.geolocation })
   navigator.permissions.query({name: 'geolocation'}).then(p => console.info({permission: p.state}))
   ```

   Expect `secure: true`, `geolocationAvailable: true`. `prompt`, `granted`, and `denied` describe the browser permission, not success of its provider. Permission inspection itself does not acquire a position. If the Permissions API is unsupported, use Chrome Site settings; acquisition does not depend on that API.
3. With permission reset to Ask in Chrome Site settings, reload `/buyer`. There must be no geolocation prompt or discovery request on page load. Press **Use current location**. Allow location when Chrome asks. Expect **Locating...**, then filled latitude/longitude and a browser-reported accuracy estimate (or an honest unknown message). Inspect the point privately for plausibility. Do not paste it into logs, screenshots, HAR files or this report. No discovery POST should occur before confirmation.
4. Press **Use for discovery**. Network must show POST `http://127.0.0.1:8000/api/v1/discovery/products`, JSON `location` containing numeric `latitude`/`longitude` matching the draft rounded to six decimals. It must not send the accuracy field or put coordinates in the URL. Expect an authenticated 200 array, `Cache-Control: no-store`, and either real eligible QA listings or **No products nearby**. An empty array is a valid result, not proof that geolocation failed. Inspect response fields privately: no exact seller coordinates/distance/address/phone. Do not export Authorization headers or payloads.
5. Keep permission Granted and press **Use current location** again. It should request a fresh fix without another prompt, clear old listings/accuracy while pending, require confirmation again and use the newly confirmed point. Move location only where safe, then repeat; merely refreshing listings reuses the existing point. While pending, edit Latitude manually; a later browser callback must not overwrite that new draft.
6. Set site Location to Block and repeat. Expect permission-denied guidance and no fabricated point/request. Enter a saved QA address's PIN, select **Use [label] for discovery**, and verify the POST contains only `address_id`. Unknown PIN must show no matching saved address and make no discovery request. Manual coordinates remain another explicit fallback. If the buyer has no saved address, PIN-only lookup cannot work; add a correctly located synthetic QA address first.
7. Unavailable/timeout are not reliably forced by permission denial. With a new request foregrounded, ignoring the prompt should reach the 30 s application deadline; system/browser suspension can delay timers. DevTools Sensors **Location unavailable** can exercise a provider error. Sensors custom locations/accuracy, including a broad >1 km estimate, can check deterministic UI and coordinate-change behavior, but record those runs as **EMULATED**, never device GPS. Restore Sensors to **No override** before the real-device run.
8. To test backend failure, temporarily stop only this QA backend, then confirm/refresh. Expect sanitized unreachable-service guidance, not old successful listings presented as fresh. Restart using the verified QA setup. For empty results use a synthetic point with no eligible QA listings; do not create fake application listings to disguise an empty result.

### What “test 1/2/3 km” actually means

- On `/buyer/samples`, 1/2/3 buttons filter sample distances. Record this only as **sample UI**, never GPS evidence.
- On live `/buyer`, there is no buyer-radius button. Use controlled QA products with seller-configured delivery radii 1, 2 and 3 km, approved/active/in stock and dispatch explicitly confirmed. A QA admin must moderate through authorized workflows. Use actual numeric coordinates in that isolated QA environment. No seller-coordinate disclosure to buyer is needed.
- For deterministic boundaries, automated tests already use synthetic seller `(0,0)` and buyer longitude pairs: 1 km `.008993/.008994`, 2 km `.017986/.017987`, 3 km `.026979/.026980`, latitude `0`. The first is just inside and the second just outside each radius. These are **test coordinates, not live GPS**. Discovery can include both because of locality privacy; checkout using the saved address must accept inside and reject outside with `DELIVERY_INELIGIBLE`. Exact inclusive and 1e-9 km arithmetic tolerance cases are separately tested; six-decimal coordinate storage cannot represent micrometre offsets, so those cases inject only a synthetic distance result.
- Do not expect real device uncertainty to distinguish these centimetre-scale boundary pairs. Actual real-device testing establishes acquisition, honest accuracy, transmission and sensible locality results; controlled fixtures establish numeric boundary correctness.

## 6. Failure diagnosis and release decision

| Symptom | Check / action |
| --- | --- |
| No prompt | Confirm button was pressed; inspect origin permission and secure-context capability. Granted permission normally produces no prompt; denied permission often requires resetting Site settings. No automatic prompt on mount is correct. |
| Denied | Check Chrome Site settings, Windows Location privacy and any enterprise policy. Allow permission, then click again. This error can also reflect browser policy, not just an explicit denial. |
| Unavailable | Check OS location/provider connectivity; desktop Wi-Fi/network positioning may have poor coverage. A high-accuracy hint does not create a GPS sensor. |
| Timeout | Retry foregrounded; distinguish 10 s acquisition from the 30 s interaction bound. Do not silently substitute a city centre. |
| Broad accuracy / wrong apparent locality | Read the displayed estimate; disable Sensors overrides for real testing; retry or select a known saved address. Six coordinate decimal places do not mean six-place accuracy. VPN/network-based estimates can be poor. |
| 401 / 403 | Verify synthetic login/session/admission and buyer role; reauthenticate if expired. Never weaken role or address-ownership checks. |
| 422 | Inspect only sanitized validation fields; ensure finite numeric latitude/longitude in range, both present, and no accuracy/pincode/extra field sent as location. |
| 429 | Respect Retry-After/rate limits; stop repeat clicks. Do not disable abuse controls. |
| 503 / API unreachable / CORS | Check backend/readiness and exact API URL/CORS origin. Storage configuration or schema problems are separate from browser location; use sanitized server events. Do not migrate the original database as a location-test workaround. |
| No products / checkout rejects candidate | Confirm seller dispatch, moderation, stock, saved delivery address and documented coarse locality contract; no invented results. Device discovery does not replace delivery address. |

Remaining gates: actual owner Chrome/OS permission and provider evidence; a properly provisioned synthetic manual-QA database; HTTPS-domain re-test with valid TLS and production headers/policies; confirmation whether coarse locality is accepted for pilot or exact live buyer radius is mandatory; the separate production-readiness blockers and intermittent full-suite frontend failure. Deployed proxy logging and retention remain operational verification items.

**Recommendation: NO-GO for claiming verified real-device live location or exact selectable live-radius discovery.** The tested software paths can proceed to controlled local Chrome acceptance. Overall **LIVE LOCATION NOT VERIFIED** until the owner completes the real-device steps with Sensors overrides disabled; successful mocked or emulated runs cannot change that verdict.

The owner must test in Chrome: grant actual location permission, click **Use current location**, inspect the accuracy, confirm **Use for discovery**, privately verify the POST and genuine/empty results, repeat after a change, then deny permission and verify PIN/saved-address fallback. Test 1/2/3 km via the controlled QA/checkout scenarios above; do not treat sample buttons as live filters.
