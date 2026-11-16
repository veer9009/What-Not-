# Pre-deployment property UI and buyer navigation verification

Date: 16 November 2026. Work performed in the existing application; no deployment, commits, pushes, `.env` edits, development database migrations, or development data changes.

## Result and design

Property forms previously omitted the shared `product-form`, `form-grid`, button and checkbox styling. Several strings in `PropertyPages.tsx` contained literal mojibake. Manage Properties now uses named forms, consistent cards and controls, two desktop columns where useful, full-width descriptive fields, mobile single columns, and separate public-locality/private-address help. The shared property wrapper also fixes the confirmed form/button defect on browse, detail, requests and moderation pages. Public/private address fetching and moderation commands are unchanged.

Seller Shop Profile's recent GPS implementation was preserved without edits. Existing page and utility tests verify acquisition only on click, editable unsaved coordinates, denied/unavailable/timeout/unsupported failures, cancellation, manual entry, and separate dispatch confirmation. GPS acquisition does not publish a discovery point or confirm dispatch.

Buyer addresses already persist manually supplied latitude/longitude. Orders reference those addresses; `AddressService.update` prevents changing delivery fields once an order references an address. Checkout requires explicitly selecting a saved address. However, legacy addresses do not prove consent to sharing a precise point for seller navigation.

The smallest change adds an optional buyer review/confirmation action in order details. `POST /orders/{id}/delivery-location-confirmation` validates coordinates against the immutable saved delivery point, authorizes the owning buyer, checks eligible status, locks the order, and records a consent marker in the existing audit table. The marker contains no coordinates. It does not change the address, order status, inventory, pricing, or order-placement contract. No new schema or migration is needed.

The existing private fulfillment endpoint returns the saved point to its owning buyer for review. It returns coordinates to the owning seller only after buyer confirmation and only during the existing accepted/preparing/out-for-delivery/delivered/disputed fulfillment window. Completed/cancelled/rejected/placed orders remain unavailable to sellers. Unrelated accounts cannot read or confirm a point. Administrative fulfillment reads keep their reason/audit requirements and omit precise coordinates. Public order/listing/discovery responses do not gain coordinates.

After **View delivery details**, eligible seller order details show **Navigate to Buyer** if a confirmed valid point exists. The Google Maps destination is strictly checked for numeric syntax, finiteness, and latitude/longitude range, then URL encoded. The link uses `target="_blank" rel="noopener noreferrer"`. Otherwise the page explains postal delivery fallback. Status transitions clear loaded delivery data. The buyer review describes sharing with the assigned seller and Google Maps navigation; checkout explains where to perform this optional confirmation. No buyer GPS is collected, and no PIN/locality is converted into an exact location.

## Verification

Final verification results are recorded below; overlapping reruns are separate, not additive totals.

- Full frontend retry on final code: **349 passed, 0 failed**, **38 test files passed**, exit 0. Evidence: `security/evidence/predeploy-frontend.json`.
- Affected frontend suite: **105 passed, 0 failed**, including PropertyPages 9, OrderNavigation 16, SellerProfileLocation 13, geolocation 19, DispatchLocation 2, Checkout 23, BetaFlows 5, ProductImages 11 and uploads 7. Evidence: `security/evidence/predeploy-final-focused.json`.
- Final property markup/fixture rerun after mobile navigation spacing: **10 passed, 0 failed** across `PropertyPages.test.tsx` and `scripts/property-layout.test.tsx`.
- Backend non-persistence tests: **385 passed, 0 failed** using `.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence -q --tb=short` from `backend`.
- Relevant PostgreSQL integration suite: **91 passed, 0 failed** across buyer navigation, beta notifications/orders/admin, dispatch location, order geography and properties. Final privacy-log/unauthenticated assertions were then rerun in the navigation file: **12 passed, 0 failed**.
- Offline Chrome geometry: **5 viewport cases passed, 0 failed** at 1440, 1024, 768, 390 and 320 pixels. Checked column count, containment, styled controls, labels, checkbox sizing and horizontal overflow. Actual React output with synthetic data and network blocked; screenshots were also visually inspected.
- Final `npm.cmd run build`: **passed, exit 0**, TypeScript and Vite; 1,944 modules transformed.
- `git diff --check`: **passed**. No `.env` or Alembic changes. Limited credential-pattern scan of changed implementation files: **0 matches**. Reviewed ownership, lifecycle, consent, URL validation, public response boundaries, no-store behavior and sanitized error logging; navigation integration tests assert coordinates absent from audit reasons and error logs.
- Independent read-only code review: **no blockers found**, including authorization, consent, validation, privacy boundaries and existing property workflows.

The initial full frontend attempt reported **342 passed, 1 failed** (discovery test exceeded its 5-second timeout), plus **1 collection error** (`EBUSY` opening a dependency file). The stalled run was interrupted; the runner emitted its JSON report during interruption, and that report was preserved separately. The full retry with thread workers passed all 349 tests, including both affected files. No test timeout or production behavior was changed to hide the initial failures.

PostgreSQL tests use the existing harness's separately generated temporary cluster/databases and apply the existing migrations there only. They never consume the application's `DATABASE_URL`. The first sandboxed attempt failed at PostgreSQL startup before tests; an approved outside-sandbox rerun passed. `whatnot_app_dev` was not connected to or migrated, and this task makes no claim that it is at `0008`; the supplied latest verification was `0009 (head)`.

One early build and one early Chrome run completed their checks but encountered a Windows process-exit error. Both were rerun successfully with exit 0. The final successful build and Chrome evidence reflect the final code.

Reproduction commands (frontend from project root; Python commands from `backend`):

```powershell
npx.cmd vitest run src/pages/PropertyPages.test.tsx src/pages/OrderNavigation.test.tsx src/pages/SellerProfileLocation.test.tsx src/location/geolocation.test.ts src/components/DispatchLocation.test.tsx src/Checkout.test.tsx src/BetaFlows.test.tsx src/pages/ProductImages.test.tsx src/api/uploads.test.ts --maxWorkers=1
npx.cmd vitest run scripts/property-layout.test.tsx src/pages/PropertyPages.test.tsx --maxWorkers=1
node scripts/verify_property_layout.mjs
npx.cmd vitest run --pool=threads --maxWorkers=1 --reporter=default --reporter=json --outputFile=predeploy-frontend.json
npm.cmd run build
.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence -q --tb=short
.venv/Scripts/python.exe -m pytest tests/persistence/test_buyer_navigation.py tests/persistence/test_beta_notifications.py tests/persistence/test_beta_orders.py tests/persistence/test_dispatch_location.py tests/persistence/test_order_geography.py tests/persistence/test_beta_admin.py tests/persistence/test_properties.py -q --tb=short
.venv/Scripts/python.exe -m pytest tests/persistence/test_buyer_navigation.py -q --tb=short
git diff --check
```

## Exact implementation and test files changed by this task

Existing unrelated workspace edits were preserved, including product image upload and seller profile location work. In the already-dirty `src/api/types.ts`, this task changes only the delivery-location/fulfillment interfaces.

- `src/pages/PropertyPages.tsx`
- `src/pages/PropertyPages.test.tsx`
- `src/styles/properties.css` (new)
- `src/pages/OrderPages.tsx`
- `src/pages/OrderNavigation.test.tsx` (new)
- `src/pages/CartPage.tsx`
- `src/location/directions.ts` (new)
- `src/api/orders.ts`
- `src/api/types.ts`
- `backend/app/api/routes/orders.py`
- `backend/app/services/orders.py`
- `backend/app/services/inputs.py`
- `backend/app/schemas/order.py`
- `backend/app/schemas/location.py`
- `backend/app/schemas/common.py`
- `backend/tests/persistence/test_buyer_navigation.py` (new)
- `backend/tests/persistence/test_beta_notifications.py`
- `backend/tests/test_delivery_location.py` (new)
- `scripts/property-layout.test.tsx` (new)
- `scripts/verify_property_layout.mjs` (new)

Coordinate aliases moved unchanged from service inputs to shared schema definitions to avoid a circular import when the fulfillment response gained the shared coordinate model. Existing service imports remain compatible.

Documentation/evidence created: this report; `docs/security/evidence/property-layout-fixture.html`, `property-layout.json`, `property-layout-1440.png`, `property-layout-390.png`, `predeploy-focused.json`, `predeploy-final-focused.json`, `predeploy-initial-full.json`, and `predeploy-frontend.json` (all evidence files under `docs/security/evidence/`).

## Remaining limitations and manual browser checklist

No real browser GPS permission prompt, physical-device accuracy, live buyer/seller session, or real Google Maps navigation was exercised. GPS/frontend API tests use mocks; Chrome checks use offline synthetic markup. Existing addresses/orders remain readable without consent, and sellers get postal fallback until each order's buyer confirms its point. Incorrect historical delivery fields remain immutable; contact the seller for that order and create a replacement address for future orders.

1. As seller, visit `/seller/properties` at desktop and mobile widths. Check labels/cards, two-column desktop rows, single-column mobile fields, multiline inputs, readable punctuation and public/private guidance. Create/edit a test listing and verify moderation and saved profile/contact preference behavior.
2. Open related property browse/detail/request/moderation pages with the appropriate role. Verify styled controls and existing private appointment-address access rules.
3. Open Shop Profile and verify no GPS prompt on load. Click **Use Current Location**; exercise allow/deny and manual correction. Confirm dispatch explicitly and verify no automatic public-discovery consent.
4. As buyer, select an existing saved delivery address and place a test order. Open its details, choose **Review delivery location**, check the actual point and privacy text, then explicitly confirm it. Check a second unconfirmed order remains private.
5. As the assigned seller, accept the order and choose **View delivery details**. Confirm **Navigate to Buyer** appears only for the confirmed point. Open it and verify Google Maps shows the intended destination in a new tab. This step remains untested here.
6. Check unconfirmed/missing-point fallback, status changes and unrelated seller access. Verify completed/cancelled/rejected orders do not expose seller delivery navigation and normal seller-managed status transitions still work.
7. Smoke-test existing product image upload, reorder/primary-image selection and listing display in the browser.
