# Current location beta fix

Date: 14 November 2026. Scope: existing browser geolocation and buyer fallback UI.
The user confirmed that no application is currently running on localhost or AWS.
This is a source/test diagnosis, not a claim to have reproduced a deployed failure.
Previous security-audit changes in the working tree were preserved.

## Confirmed code-level causes and changes

1. The helper relied only on getCurrentPosition's 10-second acquisition timeout.
   Waiting for permission/visibility is excluded from that browser timeout, so the
   UI could remain pending indefinitely. A separate 30-second interaction deadline
   now rejects with the timeout state. This is bounded while the browser event
   loop is running; a suspended/background tab can defer JavaScript timers.
2. The picker allowed repeated device requests and submission of old coordinates
   while a new request was pending. It now displays Locating, disables duplicate
   acquisition/confirmation, and clears the old draft. Manual editing remains
   available and abandons the device request; unmount also abandons it.
3. Insecure HTTP was misclassified as unsupported; access to navigator.geolocation
   occurred outside the error boundary. The helper now identifies an insecure
   context, handles unavailable APIs and catches browser security exceptions.
4. The helper did not request high accuracy for nearby discovery. Acquisition
   now requests high accuracy and a fresh position. This is a browser hint, not a
   guarantee of GPS availability or positional accuracy. The existing finite/range
   validation and six-decimal coordinate representation remain unchanged.

The original code already called navigator.geolocation; it was not missing an SDK.
Location is still requested only by a button click. Successful coordinates remain
an unsaved draft until explicit confirmation. All success/failure/abort paths clear
the deadline/listener, and late browser callbacks cannot overwrite a newer draft.
Native getCurrentPosition itself is not cancellable: abort discards callbacks and
application state, rather than promising to stop the browser location provider.

Permission denied, unavailable, timeout, unsupported, insecure context and invalid
coordinates have separate sanitized messages. No browser diagnostic/coordinate is
logged. No Google SDK/key, paid service or permanent coordinate storage was added.

Browser timing/security behavior is described in the
[W3C Geolocation recommendation](https://www.w3.org/TR/2026/REC-geolocation-20260324/).

## PIN fallback and geographic correctness

The repository had PIN entry on saved-address forms and manual latitude/longitude;
it did not have a PIN-to-coordinate lookup. Buyer discovery now accepts a PIN to
filter the authenticated user's already-loaded saved addresses. The user must
select a matching address. The existing API receives its exact address_id and
checks ownership before using stored coordinates. An unknown PIN does not send a
discovery request or invent a centroid. Manual coordinates and address PIN entry
remain available. A new PIN without a saved address still requires an address with
its correct coordinates; this is not general postal geocoding.

Device discovery sends validated numeric latitude/longitude in an authenticated
POST JSON body, never query strings. Transient location and PIN filtering stay in
React memory; no new browser storage or precise-location logging was introduced.

The server's existing 1/2/3 km delivery radii, Haversine calculations, approval/
activity/stock rules and ownership checks are unchanged. Discovery deliberately
uses a coarse seller-locality cell with its existing candidate margin, rather
than leaking exact seller points or distances. Checkout remains authoritative for
exact delivery eligibility. A location fix does not remove these privacy rules or
promise that every displayed candidate is deliverable.

Readable/reverse-geocoded addresses are unnecessary for this fix. Google Maps and
Geocoding were not integrated or called. General PIN/address geocoding would need
a separately approved design covering coordinate precision, provider disclosure,
API restrictions, server-side credential handling, quotas, billing and retention
before any paid integration.

## Files changed for this task

- src/location/geolocation.ts and geolocation.test.ts
- src/components/LocationPicker.tsx and LocationPicker.test.tsx
- src/pages/DiscoveryPages.tsx
- src/LocationDiscovery.test.tsx
- scripts/beta_browser_smoke.mjs (synthetic native-browser geolocation and PIN checks)
- docs/CURRENT_LOCATION_BETA_FIX.md

No backend application, database schema, marketplace pricing/payment, dependency
version, production hosting or secret configuration was changed by this task.

## Verification

| Check | Result |
| --- | --- |
| Existing focused baseline | 22 passed |
| New core regressions against old implementation | 6 failures reproduced before fix |
| PIN regressions before fallback implementation | 2 expected failures |
| Final focused geolocation/picker/discovery/dispatch/API suite | 36 passed |
| Full backend suite (isolated PostgreSQL only) | 659 passed in 296.67 seconds |
| TypeScript + production Vite build | PASS |
| First full frontend run alongside browser smoke | 250 passed, 4 existing login/registration failures (three timeouts, one alert lookup) |
| Unchanged login/registration file rerun | 29 passed; contention is possible, not conclusively established |
| First updated native-browser smoke | Failed while buyer tab was backgrounded; harness now explicitly foregrounds it |
| Final full frontend run with unchanged assertions/timeouts | 254 passed across 29 files in 109.37 seconds |
| Final Edge native-geolocation/PIN smoke | 1 passed in 62.48 seconds; explicit CDP permission/position, foreground buyer tab |
| Browser script syntax / final diff whitespace | PASS |

The final browser run exercised native navigator.geolocation with an explicitly
emulated position, unsaved draft confirmation, accurate API discovery, manual PIN
saved-address selection, locality privacy and checkout. An independent read-only
review found no material location-code defect. Earlier failed runs are retained;
no assertions/timeouts were loosened to produce the passing run.
Fixtures use synthetic accounts, locations and a disposable database. Device-level
Windows/macOS/mobile location services and a real user's permission remain manual
checks; browser emulation cannot certify the hardware's location provider.

Commands executed (logs retained locally as ignored location-beta-*.log files):

```powershell
# Repository root: focused and complete frontend checks
node node_modules/vitest/vitest.mjs run src/location/geolocation.test.ts src/components/LocationPicker.test.tsx src/LocationDiscovery.test.tsx src/api/discovery.test.ts src/components/DispatchLocation.test.tsx --pool=vmThreads --maxWorkers=1
node node_modules/vitest/vitest.mjs run --pool=vmThreads --maxWorkers=1
npm.cmd run build
node --check scripts/beta_browser_smoke.mjs
git diff --check
```

```powershell
# Backend directory: only the fixture-owned temporary PostgreSQL cluster
$env:PATH = 'C:\Program Files\PostgreSQL\17\bin;' + $env:PATH
& .\.venv\Scripts\python.exe -m pytest -q -W error
& .\.venv\Scripts\python.exe -m pytest -q -s ../scripts/beta_browser_smoke.py
```

These run tests/build/syntax/whitespace checks rather than installing tools. pytest
creates and verifies its own synthetic cluster, never consuming application
DATABASE_URL. Restricted execution may block its PostgreSQL/browser processes;
the successful runs used approved execution outside that sandbox. The initial
frontend failures and failed background-tab smoke are not removed from the record.

## Start locally: exact PowerShell commands

Use two separate PowerShell windows. Dependencies and backend/.env already exist
in this checkout; preserve them. Functional login/discovery needs the configured
dedicated development database, a valid signing key and schema 0008. These startup
commands do not initialize/migrate a database or seed accounts. A healthy process
alone does not prove that the database is ready.

Backend window:

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not\backend'
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Expected API: http://127.0.0.1:8000/api/v1
Health: http://127.0.0.1:8000/api/v1/health
Readiness: http://127.0.0.1:8000/api/v1/ready
Local API docs: http://127.0.0.1:8000/docs

Frontend window:

```powershell
Set-Location -LiteralPath 'C:\Users\DELL\OneDrive\Desktop\What-Not'
corepack.cmd pnpm dev --host 127.0.0.1 --port 5173 --strictPort
```

Expected app: http://127.0.0.1:5173
Buyer sign-in: http://127.0.0.1:5173/login/buyer
Buyer discovery after sign-in: http://127.0.0.1:5173/buyer

The existing frontend default targets http://127.0.0.1:8000/api/v1. If an existing
local VITE_API_BASE_URL overrides that, ensure it points to this local API. Do not
place private settings in frontend variables. Port 5173 must remain fixed because
the backend's default CORS allows that port. --strictPort refuses an occupied port
instead of silently moving the frontend to an unapproved origin.

Optional health/readiness verification from a third PowerShell window:

```powershell
curl.exe -i http://127.0.0.1:8000/api/v1/health
curl.exe -i http://127.0.0.1:8000/api/v1/ready
```

Health should return 200; readiness must return 200 against the correctly configured
development DB/schema. A 503 means resolve the DB/settings issue before testing
marketplace discovery. Do not redirect tests or migrations at an unrelated DB.

| Command | WHAT / HOW | WHY / WHEN | EXPECTED OUTPUT / success verification | COMMON FAILURES | Category |
| --- | --- | --- | --- | --- | --- |
| Set-Location -LiteralPath | Sets cwd using the exact path | Run before each server to resolve its config/imports | Prompt location matches named directory | Typo or missing directory; use Get-Location | MEMORIZE |
| backend .venv python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload | Runs existing ASGI app via project interpreter, loopback listener and development reload | Start local backend after reviewing DB settings | Uvicorn running on 127.0.0.1:8000; health/readiness requests verify | Port busy, missing venv/dependencies, invalid settings, DB unavailable | PROJECT-SPECIFIC / DON'T MEMORIZE |
| corepack.cmd pnpm dev --host 127.0.0.1 --port 5173 --strictPort | Runs Vite development script on exact loopback origin | Start local UI with existing CORS/API configuration | Vite reports port 5173; sign-in route loads | Missing Corepack/deps; occupied port; wrong VITE_API_BASE_URL/CORS | PROJECT-SPECIFIC / DON'T MEMORIZE |
| curl.exe -i local health/ready URLs above | Makes HTTP request and prints status/headers | Verify process and DB separately before browser checks | Both expected 200; ready verifies schema/storage | Connection refused if stopped; ready 503 if DB/config/schema unavailable | UNDERSTAND / LOOK UP |

Stop local servers with Ctrl+C in their own windows. --reload and Vite dev are
local development settings; these are not AWS deployment commands.

## Manual browser and HTTPS checks

1. On this computer open the exact 127.0.0.1 frontend URL, sign in as a BUYER, then
   press Use current location. Enable OS location services and allow site permission.
   Verify loading becomes an acquired draft, then explicitly confirm discovery.
2. Deny site permission and retry; verify the message and manual coordinates/PIN
   fallback. To retry GPS, reset site permission in the browser's site settings.
3. An existing address PIN should filter owned choices. An unknown PIN must show
   no matching address and must not create a discovery location.
4. Repeat as SELLER when explicitly confirming the real dispatch point. Do not
   save test coordinates as a real business address.
5. If debugging is needed, inspect only the boolean window.isSecureContext,
   geolocation availability and navigator.permissions.query({name:'geolocation'})
   state in DevTools. Permission query support varies; no coordinate logging is needed.

Loopback development is a trustworthy-context exception under
[Secure Contexts](https://www.w3.org/TR/secure-contexts/#is-origin-trustworthy).
A phone visiting an HTTP LAN IP is not the same as localhost on the development
computer: use a separately approved HTTPS origin for that test.

After a separately approved deployment, verify valid HTTPS at the frontend, HTTPS
API URL, exact CORS origins, no mixed content, and a Permissions-Policy that permits
same-origin geolocation. In an iframe, the ancestor policy and iframe allowance
also apply. HTTPS alone does not grant OS/site permission or supply GPS hardware.
No browser code can override a denied permission or a blocking deployment policy.

No deployment, commit, push, credential change, application-database migration or
production infrastructure modification was performed. This location fix does not
override the separate pre-deployment security audit's unresolved release blockers.
