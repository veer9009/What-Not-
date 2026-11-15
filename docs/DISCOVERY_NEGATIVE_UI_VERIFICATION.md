# Steps 41 and 42: negative discovery and location layout

15 November 2026. Positive Chrome product rendering is **PASS, owner-reported**. Manual negative Chrome acceptance remains **NOT VERIFIED** until the owner performs the sequence below. Synthetic manual coordinates are not GPS.

## Isolated database and HTTP evidence

Read-only inspection verified `whatnot_chrome_qa_20261115`, OID **50640**, revision **0008**, expected owner, `transaction_read_only=on`. The single seller **Chrome QA Maker** has the approved synthetic dispatch origin `(0,0)` and confirmed dispatch. QA Nearby Basket is APPROVED/active, stock 4, seller delivery radius 1 km. QA Nearby Vase is APPROVED/active, stock 5, seller delivery radius 2 km. QA Pending Sample remains PENDING and excluded. No listing or seller settings were changed.

The unsupported synthetic point **latitude 1, longitude 1** is far outside the seller's supported locality, including the existing coarse-locality privacy buffer. Do not use a near-boundary point for this acceptance test: discovery locality candidates are approximate; exact delivery eligibility remains checked at checkout.

The existing protected `verify_chrome_qa_http.py` independently correlated the port-8001 worker (PID 6224) to the QA database before authenticating the approved buyer. It exited **0**, observing actual authenticated `POST /api/v1/discovery/products` responses: `(0,0)` -> 2 products, `(1,1)` -> empty array, `(0,0)` -> 2 products; owned-address fallback -> 2. Requests returned HTTP 200. Pending listing excluded; cache no-store; private fields omitted. Business counts remained 2 users, 1 seller, 3 products, 1 address, 0 orders. Normal quota writes occurred only in QA. See `security/evidence/chrome-qa-http.json`.

## Implementation and changes

`src/pages/DiscoveryPages.tsx`: edits call `choose(null)`, unmounting the old results. Confirming a source mounts results keyed by the selected source and makes a fresh POST. `src/state/useResource.ts` discards responses after unmount. No discovery behavior or eligibility rule needed changing. Added a regression for manual supported -> unsupported -> supported selection, exact payloads and removal of old cards before confirmation and after an empty response.

The saved-address buttons previously inherited right-aligned `.form-actions`; clear-location used link styling. The PIN helper was visually adjacent but not programmatically associated. The location panel now groups saved-address controls, connects PIN guidance with `aria-describedby`, gives the clear button secondary styling and announces selected-location status.

Scoped styles preserve cream/orange/dark-text tokens: 48 px controls, 8 px label gap, responsive PIN width, aligned coordinate columns stacking on small screens, equal-width action buttons, left-aligned saved-address actions, consistent message spacing and aligned product-card content. Existing focus outlines, keyboard controls, button labels, permission behavior and source confirmation remain intact. Seller pages are unaffected by the new layout styles.

No QA shortcut, sample-location button, QA-mode flag or fixed coordinate was added to product code. Synthetic account/address/product labels exist only in the isolated QA database. Manual coordinate inputs remain the existing technical fallback, and are never labeled as browser GPS. No buyer-selectable radius feature was added.

Changed implementation/test tooling:

- `src/pages/DiscoveryPages.tsx`
- `src/styles/index.css`
- `src/LocationDiscovery.test.tsx`
- `scripts/discovery-layout.test.tsx` (Node-only export of actual rendered synthetic markup)
- `scripts/verify_discovery_pin_layout.mjs` (offline headless Chrome measurements)

## Commands and verification

From `backend`:

```powershell
& .\.venv\Scripts\python.exe ..\docs\security\verify_chrome_qa_http.py
& .\.venv\Scripts\python.exe ..\docs\security\run_existing_server_tests.py --location
```

Backend regression command exited 0: **76 passed**, no failures/errors/skips, 1,573 guarded SQL checks. Fixtures targeted only `whatnot_tests_20261115_a7e394c2`, OID **49265**, with rollback isolation. This existing harness performs read-only original/rehearsal identity/snapshot checks; no original/rehearsal writes, migrations, schema creation or quota cleanup ran. Both original and isolated-test row snapshots were unchanged. Evidence: `security/evidence/live-location-database-tests.json`.

From repository root:

```powershell
& 'C:\Program Files\nodejs\corepack.cmd' pnpm test run src/LocationDiscovery.test.tsx src/components/LocationPicker.test.tsx src/location/geolocation.test.ts scripts/discovery-layout.test.tsx --testTimeout=20000 --no-file-parallelism
& 'C:\Program Files\nodejs\node.exe' scripts/verify_discovery_pin_layout.mjs
& 'C:\Program Files\nodejs\corepack.cmd' pnpm build
```

Final focused frontend run: **43 passed in 4 files**, exit 0, 72.30 seconds. The initial red test demonstrated missing PIN accessible description. An initial run also hit two default five-second timeouts; the focused command explicitly permits 20 seconds and runs files serially. An initial build caught a Node filesystem import in a browser-project test; the exporter was moved outside `src`, without dependency/config changes.

Chrome geometry uses actual React-rendered synthetic fixtures and the real stylesheet, with all page networking blocked. It verifies 1440/1024/768/390/320 px: PIN spacing/size, helper placement, input/button containment, coordinate alignment, equal button widths, saved-action left alignment, 44 px minimum button targets, product-card alignment and no document horizontal overflow. It is not interactive owner acceptance or a physical-mobile test. Evidence: `security/evidence/chrome-pin-layout.json` and `discovery-layout-fixture.html`.

Final layout command exited **0**, all five widths passed. Final production build exited **0**: TypeScript + Vite, 1,939 modules, Vite build 11.34 seconds. No dependency installation or configuration broadening was needed.

| Required result | Status | Evidence / boundary |
| --- | --- | --- |
| Negative HTTP discovery | PASS | Actual QA POST at `(1,1)` returned 200 / empty array |
| Manual negative Chrome discovery | NOT VERIFIED | Owner must perform steps below |
| Stale-product clearing | PASS | Mocked manual positive/negative/positive and existing late-response regressions; owner Chrome check pending |
| PIN-code UI | PASS | Accessible helper, scoped spacing, secondary action test and Chrome geometry; owner visual check pending |
| Responsive layout | PASS | Network-blocked React fixture at five widths; physical device and owner interaction pending |
| Production build | PASS | Final command exit 0 |

## Exact owner Chrome acceptance

1. Use the isolated startup commands in [CHROME_DISCOVERY_ACCEPTANCE.md](CHROME_DISCOVERY_ACCEPTANCE.md). Backend must be `127.0.0.1:8001`; frontend must be `127.0.0.1:5174`. Use the separate QA Chrome profile and existing approved buyer. No registration or password reset.
2. Open `http://127.0.0.1:5174/buyer`; reload to load the new styles/code, then sign in again if needed. Open DevTools -> Network, filter `discovery/products`. Do not export a HAR or share bodies/headers containing credentials.
3. Enter **Latitude 0**, **Longitude 0** in the manual fields; click **Use for discovery**. Expect a fresh POST to `http://127.0.0.1:8001/api/v1/discovery/products`, HTTP 200, both QA cards, prices 250.00 and 125.50 and seller Chrome QA Maker.
4. Change Latitude to **1** and Longitude to **1**. Old cards should disappear immediately while the draft is unconfirmed. No discovery request should occur merely from typing.
5. Click **Use for discovery**. Expect a new POST with `{"location":{"latitude":1,"longitude":1}}`, HTTP **200**, response **[]**, **No products nearby**, and neither QA product card. This is a successful empty result, not a backend error.
6. Change both fields back to **0**, confirm, and verify a new HTTP 200 response with the two cards. The pending product must never appear. Also verify Clear discovery location removes cards and asks for a location.
7. Enter PIN **999999**, verify helper text below the input, then click the left-aligned **Use QA Home for discovery** action. Expect both products. This is an owned saved-address lookup, not PIN geocoding.
8. Inspect at desktop, tablet and Chrome device widths **390 and 320 px**. Check coordinate alignment/stacking, comfortable PIN spacing, equal-width primary/secondary actions, no clipping/overlap, tidy product cards and visible keyboard focus. Tab through the fields/buttons and confirm all actions remain operable.
9. Report only method/path/status, result counts and whether cards clear/reappear and layout fits. Synthetic points above are safe to discuss. Never share passwords, bearer tokens, signing keys or connection strings.

No migrations, deployment, commit or push. Real-device GPS movement/accuracy and HTTPS acceptance are outside these synthetic manual tests.
