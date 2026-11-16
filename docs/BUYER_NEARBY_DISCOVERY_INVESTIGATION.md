# Buyer cannot discover nearby seller

Investigated 16 November 2026 against the current working tree and configured local PostgreSQL database `whatnot_app_dev`.

## Root cause and evidence

The existing records lack separately consented public discovery locations. This is an unmet visibility requirement, not a confirmed geographic calculation or discovery code defect.

PostgreSQL-enforced read-only inspection found revision **0009**, all four required public-discovery columns, 8 users, 3 seller profiles, 4 products and 1 buyer address. All four products are APPROVED, active and in stock; their seller accounts are active SELLER accounts with valid, confirmed private dispatch locations. Products 1/3 have a 2 km delivery radius; products 2/4 have a 3 km radius. All three sellers have NULL public-discovery coordinates, NULL public confirmation and NULL consent version. All are unverified, which does not exclude them from discovery.

`backend/app/services/discovery.py:34` returns no view whenever public coordinates, confirmation, or the current `public-discovery-v1` consent are absent. This applies to every existing product, regardless of buyer position. The repository admits all four products before that check. No precise dispatch coordinates or account identities were recorded.

Fresh real-PostgreSQL verification through the actual `DiscoveryService` found:

- The existing active buyer's saved address validates successfully.
- Three address/product pairs are within the products' private delivery radii. This aggregate confirms that physical proximity alone does not establish public eligibility.
- Saved-address and equivalent transient-coordinate requests agree at 1, 2 and 3 km: all return zero products.
- All four candidates lack current public consent.
- Coordinate column precision/scale and the public-consent completeness constraint are present.

Evidence: [read-only PostgreSQL verification](security/evidence/buyer-discovery-readonly.json). The earlier report of schema revision 0008 in `LOCAL_BETA_DIAGNOSIS.md` is historical; the current database is 0009. No migration was needed or run.

## Full path checked

| Boundary | Current behavior and finding |
| --- | --- |
| Buyer entry point | `/buyer` renders `BuyerDiscoveryPage`. `/buyer/samples` is the separate sample catalogue and does not establish live discovery. |
| GPS/manual input | `LocationPicker` requests GPS only on click, clears the previous selection, validates finite latitude/longitude and ranges, rounds to six decimal places, then requires **Use for discovery**. Empty fields fail validation. Browser accuracy is shown as an estimate. Real physical-device GPS was not exercised. |
| Stored versus selected location | Transient points remain in React state. A saved address is used only after explicit selection. PIN entry filters saved addresses; it does not geocode or fabricate coordinates. Existing buyer address coordinates are valid. |
| Request | `src/api/discovery.ts` sends `POST /api/v1/discovery/products` with either `location: {latitude, longitude}` or `address_id`, plus integer `radius_km` 1/2/3; default 3. List and detail share the source and radius. Coordinates are not placed in URLs. |
| Backend source | `DiscoverySource` requires exactly one location source. `DiscoveryService._location` requires an active BUYER; saved addresses must belong to that buyer. |
| Seller/product gates | `ProductRepository._discovery_query` requires APPROVED, active, positive stock, active SELLER user and confirmed dispatch. All four current products pass. There is no separate seller approval field/gate in this flow. `is_verified` only supplies a badge. |
| Public consent | `_eligible_view` separately requires public coordinates, confirmation timestamp and current consent version. Every current seller fails this gate. Dispatch confirmation does not populate these fields. |
| Geography | `distance_km(latitude_a, longitude_a, latitude_b, longitude_b)` uses Haversine and Earth radius 6371.0088 km. No reversed arguments or metre/km mismatch was found. Public distance must satisfy both buyer discovery radius and product delivery radius. |
| Private geography | A further private locality-cell check uses the dispatch cell centre and product radius + 0.8 km. Checkout independently confirms exact private delivery distance. A newly consented public point alone does not guarantee delivery. |
| Empty/error states | Missing selection shows **Choose your discovery location**. Location failures show explicit errors. API/network/validation/rate-limit failures show sanitized errors, not **No products nearby**. A successful empty response or a search with no matches shows the empty state. |
| Cache/state | Requests use `cache: 'no-store'`; successful discovery responses send `Cache-Control: no-store`. Source/radius changes remount results, `useResource` rejects late/stale responses, and the provider resets on account change. No live auto-polling exists: a seller update requires **Refresh nearby products** or a fresh visit. Clear any product-search filter. |

## Changes and verification

No application code was changed: no genuine code defect was confirmed, so no behavior fix or new defect regression test was justified. Existing tests already cover consent exclusion, explicit consent, GPS/manual acquisition, source/radius requests, invalid coordinates, distance boundaries, stale responses, session clearing and error states.

Added `docs/security/verify_discovery_readonly.py` to make the current-data PostgreSQL diagnosis repeatable. It permits only a local `whatnot_` database, enforces read-only/repeatable-read transactions, suppresses exception details, and writes only coordinate-free evidence to the repository. It calls services directly, avoiding HTTP discovery's persistent quota counters. It performs no data/schema writes or migrations.

Verification results:

- Frontend full attempt: **355 tests passed**, 39 suites passed; one suite failed collection because a Windows `EBUSY` lock prevented opening an `aria-query` dependency. No assertion failed. Targeted retry of that suite (`src/pages/SellerProfileLocation.test.tsx`): **13 passed**, exit 0. Across the full attempt plus the targeted retry, all 40 suites were exercised successfully (368 tests); there was no second clean full-suite run. Evidence: `security/evidence/buyer-discovery-frontend.json` and `security/evidence/buyer-discovery-frontend-retry.json`.
- Backend non-persistence suite: **385 passed**, exit 0, 43.40 seconds. Evidence: repository-root `buyer-discovery-backend.log`.
- PostgreSQL read-only verification: **passed**, exit 0; current schema/constraint checks, four actual candidates, three saved/transient source comparisons at 1/2/3 km, all empty. Evidence: `security/evidence/buyer-discovery-readonly.json`.
- Production build retry: **passed**, exit 0; TypeScript and Vite, 1,946 modules. Evidence: repository-root `buyer-discovery-build-retry.log`. The initial PowerShell invocation produced assets and a successful Vite message but returned exit 1; the retry through `cmd.exe /d /c` established a clean exit without code changes.
- Whitespace check: `git diff --check` passed; existing LF/CRLF normalization warnings were informational.

The normal `backend/tests/persistence` fixtures were deliberately excluded because they automatically run Alembic migrations and create/change test records. The real PostgreSQL read-only checks replace those tests for this investigation; they do not establish mutation/transaction/concurrency coverage.

Commands from repository root:

```powershell
backend/.venv/Scripts/python.exe docs/security/verify_discovery_readonly.py
npx.cmd vitest run --pool=threads --maxWorkers=1 --reporter=default --reporter=json --outputFile=docs/security/evidence/buyer-discovery-frontend.json
npx.cmd vitest run src/pages/SellerProfileLocation.test.tsx --pool=threads --maxWorkers=1 --reporter=default --reporter=json --outputFile=docs/security/evidence/buyer-discovery-frontend-retry.json
npm.cmd run build
```

Backend unit tests from `backend`:

```powershell
.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence -q --tb=short
```

No existing database records were modified/reset, private coordinates published, sellers fabricated, moderation bypassed, `.env` changed, migration run, deployment performed, or commit/push made. Existing unrelated working-tree changes were preserved. Build output under `dist` was regenerated.

## Requirements still unmet

All three sellers must independently choose and explicitly consent to a public business discovery point. Only the seller can decide whether to reveal an inferable location; do not copy private dispatch GPS automatically. If a seller declines public-location consent, their products correctly remain absent from radius discovery.

After that consent, the chosen buyer point must satisfy both public radius checks and the private locality check. Public distance cannot be verified for the current sellers because no public points exist. Product approval, availability, stock and dispatch confirmation currently pass, but must continue to pass. Changing an approved listing can reset its status to PENDING and require normal moderation again.

The task did not exercise a signed-in physical browser/device or a running server's authenticated discovery HTTP route. API transport/error/state behavior is covered by frontend mocks and backend unit checks; the current-record reproduction used the real service and PostgreSQL. This does not prove which database a separately running backend process uses, nor the accuracy of a buyer's actual GPS selection. No account credentials were requested or changed.

## Exact manual account verification

These are instructions for the account owners; the investigation did not perform the consent or record-changing steps.

1. Seller: sign in to the existing SELLER account and open `/seller/profile`. Verify the shop loads and dispatch is confirmed. Saving general profile coordinates and confirming private dispatch are separate actions. If dispatch needs correction, use its own private confirmation flow; verify the public discovery section remains separate.
2. Seller: in **Public discovery point**, observe **No public discovery point confirmed**. Select **Set or change public discovery point**. Choose a business location you intend buyers to infer, using GPS or valid manual coordinates. GPS remains an unsaved draft until confirmation. Do not select a private home unless you intend to make that location discoverable.
3. Seller: after selecting/editing the point, check **I agree that this selected business point can be inferred publicly through discovery results.** Editing coordinates clears this consent checkbox. Press **Confirm public discovery point** and verify **Public discovery point confirmed** persists after reload. The request is `PATCH /api/v1/sellers/me/public-discovery-location` with `consent: true` and `consent_version: public-discovery-v1`. Never send private dispatch coordinates merely to satisfy this check.
4. Seller: open `/seller` and verify the target product remains APPROVED, active and in stock with the intended 1/2/3 km delivery radius. If PENDING or REJECTED, follow the normal moderation/resubmission process. Do not change approval in the database. The verified badge is not required by discovery.
5. Buyer: sign in separately to the existing BUYER account and open `/buyer`. Use **Use current location**, review accuracy/coordinates, then **Use for discovery**; alternatively explicitly select the known saved address. A PIN by itself is insufficient. Confirm **Location available for discovery**. Do not share a screenshot or exported request containing precise private coordinates.
6. Buyer: start with **3 KM**, clear **Search products**, then press **Refresh nearby products**. In browser Network tools, inspect the discovery POST locally: confirm exactly one source, correct named latitude/longitude values (or owned address ID), `radius_km: 3`, and the expected API host. Expect HTTP 200; inspect errors separately from an empty JSON array. Check `/api/v1/ready` on that same backend reports schema 0009. Do not export authorization headers or private location bodies.
7. Buyer: if all public/private distance and availability conditions pass, confirm the approved product appears and opens at `/buyer/products/{id}`. Switch 1/2/3 KM without reacquiring GPS and confirm each request has the selected radius. A product with a 2 km delivery radius is still excluded beyond 2 km even with a 3 km buyer radius. **Refresh nearby products** is necessary after a seller changes eligibility; there is no push update.
8. Buyer: edit the draft coordinates or clear the location; old cards should disappear. Deny GPS permission or temporarily block the discovery request in browser developer tools and verify an explicit error/selection state rather than a misleading empty result. Restore the request afterward. A stale/late response must not restore old cards.
9. Optional consent lifecycle check, only if the seller chooses it: seller revokes public consent; buyer refreshes and sees the product disappear. Seller must select/review the public point and consent again to restore discovery. Private dispatch must remain unchanged. No such revocation was performed during this investigation.
