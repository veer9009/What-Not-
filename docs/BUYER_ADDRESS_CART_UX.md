# Buyer address GPS and cart layout

16 November 2026. Local pre-deployment changes only; no migration, `.env` edit, deployment, commit or push. Existing unrelated working-tree changes were preserved.

## Address form

`/buyer/addresses` previously required visible manual coordinate entry without a GPS action. It now shows **Use Current Location**, requests the browser only on click, displays detection/success/errors, and fills only an unsaved coordinate draft. The existing shared geolocation utility supplies finite/range validation, six-decimal precision, permission/unavailable/timeout/unsupported/insecure-context messages and request cancellation.

Postal fields remain editable and required as before; GPS does not geocode or invent street/city/state/PIN information. Latitude/longitude move into **Advanced location details**, initially closed and opened automatically on location failure or invalid coordinates. Manual entry is retained; no map picker was implemented. Both GPS and manual coordinates require an explicit **Save address**. The optional disclosure is optional to open, not permission to omit the valid location required by the existing API.

Detection failure preserves previously entered/saved draft coordinates. Editing manual coordinates cancels detection; unmount/cancel prevents late callbacks. Postal edits during detection remain intact because GPS updates only coordinates. Saving is disabled while detection is pending. Address creation, changed-fields-only edit patches, default selection, order-referenced address restrictions and address API contracts remain unchanged.

The backend contract was inspected in `backend/app/services/inputs.py` (`AddressCreate`/`AddressUpdate`) and `backend/app/models/address.py`. Existing coordinate range/precision and postal field limits are preserved. No backend file was changed by this task.

Saving an address does not invoke delivery-location confirmation or give sellers new access to precise coordinates. The form explains the existing optional per-order confirmation. Order authorization and fulfillment privacy rules are unchanged.

## Cart defect and fix

The original `1fr 330px` grid allowed intrinsic child widths to force overflow: long native-select options and the product card's five-column layout did not shrink to the available main width. Existing dashboard overflow clipping could conceal that internal overflow. Unscoped summary `<div>` styling also applied to API error blocks. The new scoped styles use `minmax(0, 1fr)` with a 350px desktop summary, constrain the address select, keep Manage saved addresses directly below it, and stack the cart below 1100px. Product cards use two compact rows on desktop and three on small phones, wrap names/prices, and give quantity/remove buttons at least 40px targets.

Checkout's seller grouping, subtotal/delivery/total computations, stock and price checks, address-selection requirement, idempotency/recovery, order submission, and button disabled conditions were not changed. Existing buyer-confirmed delivery-point instructions remain present. The summary button is full width with a minimum height of 48px.

## Verification

- Test-first address check: **10 failed, 1 passed** on the original form because GPS/disclosure/validation behavior was missing. Log: `buyer-address-red.log`.
- Initial implementation check: **12 passed** across the 11 new address checks and real React layout/checkout-selection fixture. Log: `buyer-address-green.log`.
- Final focused rerun after strengthening manual-fallback visibility and fixture selection checks: **12 passed**, exit 0. Evidence: `security/evidence/buyer-checkout-final-focused.json`.
- Full frontend suite: **380 passed, 0 failed; 42 files passed**, exit 0. This includes existing address/default, seller, discovery, checkout/stock/idempotency/recovery, order navigation/confirmation, and privacy tests. Evidence: `security/evidence/buyer-checkout-frontend.json`; log: `buyer-checkout-frontend.log`.
- Production build: **passed, exit 0**, TypeScript and Vite, 1,947 modules. Final unchanged-asset rerun also completed TypeScript/Vite successfully; log: `buyer-checkout-build-final.log` (initial log: `buyer-checkout-build.log`).
- Chrome geometry: **6/6 viewports passed**, 1440, 1280, 1024, 768, 390 and 320px. Checks cover responsive columns/stacking, desktop summary width, document and component overflow, form control containment, address dropdown width, manage-link placement, touch targets and full-width checkout button. The comparison run with the old CSS failed all six cases on internal containment/controls; the new CSS passes. The comparison uses the same new React markup to isolate CSS behavior, not an untouched historical browser session.
- Desktop/mobile screenshots were visually inspected. Evidence: `security/evidence/buyer-layout.json`, `buyer-layout-baseline.json`, `buyer-layout-1440.png`, `buyer-layout-390.png` and the synthetic `buyer-layout-fixture.html`.
- Read-only code review: no blocking findings. Native select popup/keyboard behavior and physical GPS remain manual checks.
- Whitespace: `git diff --check` passed with existing informational LF/CRLF warnings.

Backend tests were not rerun because this task changes no backend code, schema, endpoints or contracts. No PostgreSQL persistence harness was invoked, since it runs migrations and changes test records.

Chrome initially failed before geometry with a GPU-process startup error in this environment. The isolated synthetic test launcher uses `--no-sandbox`/`--disable-gpu-sandbox` and disables background networking/component updates; the test page's network requests are blocked. Product browser settings are unchanged. This browser run does not authenticate, call live APIs, collect real GPS, or change account records.

## Files changed by this task

- `src/pages/AddressPage.tsx`: GPS/draft lifecycle, disclosure, validation, labels/privacy and form markup.
- `src/pages/CartPage.tsx`: scoped cart classes, product-copy/placeholder classes, delivery selector section. Existing unrelated delivery-confirmation help and checkout logic preserved.
- `src/styles/buyer-checkout.css`: new scoped address/cart responsive styles.
- `src/pages/AddressLocation.test.tsx`: new GPS/fallback/validation/save/edit/cancellation coverage.
- `src/Marketplace.test.tsx`: existing address creation test opens Advanced and uses the new PIN label; pre-existing unrelated changes preserved.
- `scripts/buyer-layout.test.tsx`: real React markup, explicit cart address-selection assertions and synthetic layout fixture.
- `scripts/verify_buyer_layout.mjs`: offline Chrome geometry/screenshots with optional old-CSS comparison.
- `docs/superpowers/plans/2026-11-16-buyer-address-cart.md`: scoped implementation/verification plan.
- This report and the coordinate-free/synthetic evidence files cited here. `dist` was rebuilt and remains ignored.

## Reproduction commands

From the repository root:

```powershell
npx.cmd vitest run src/pages/AddressLocation.test.tsx scripts/buyer-layout.test.tsx --pool=threads --maxWorkers=1
npx.cmd vitest run --pool=threads --maxWorkers=1 --reporter=default --reporter=json --outputFile=docs/security/evidence/buyer-checkout-frontend.json
node scripts/verify_buyer_layout.mjs --baseline-css
node scripts/verify_buyer_layout.mjs
npm.cmd run build
git diff --check
```

The baseline command deliberately returns exit 1 when it reproduces the CSS defects. Chrome requires the installed local Chrome path in the script. Screenshots use synthetic records only.

## Remaining manual checks

1. Sign in as the existing buyer, open `/buyer/addresses`, click **Add address** and verify no GPS prompt appears until **Use Current Location** is clicked. On HTTPS or localhost, allow location and verify detection then success; postal fields must remain blank/editable. Review accuracy and choose the delivery location deliberately, especially if the device is away from the destination.
2. Deny location permission; verify the error and open Advanced manual fallback. Retry after restoring permission. On a device/browser that can reproduce timeout/unavailable/unsupported behavior, verify recovery and manual entry. Enter invalid latitude/longitude and verify saving is blocked, then enter a known valid delivery point.
3. Fill required postal details and save. Verify the saved address, edit its label, switch default, reload and check persistence. For an address already used by an order, verify the existing backend refuses delivery-field changes and explains creating a replacement. The investigation did not write live address records.
4. Add an approved/eligible real product through `/buyer`, open `/buyer/cart`, and verify no address is silently selected. Confirm Place orders is disabled until an address is selected. Use the native dropdown with keyboard and touch, including a long address; check the manage link, quantity limits, removal, seller grouping and free delivery. Test at desktop/tablet/phone widths and 200% zoom.
5. Place an authorized beta test order only when desired. In order details, verify the buyer can review and optionally confirm the saved delivery point. Verify the assigned seller has no precise navigation point before confirmation and only authorized fulfillment access after it. GPS/address saving must not confirm this automatically.
6. Verify GPS permission prompts and OS accuracy on real mobile devices. Automated GPS tests use callbacks, and geometry screenshots do not test native select popups, physical GPS accuracy or signed-in end-to-end account sessions.
