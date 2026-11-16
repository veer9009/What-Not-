# Seller profile current location

Goal: implement the user's supplied twelve requirements in the existing shop form.
Reuse `acquireLocation` and `coordinates`; do not change APIs or database state.

- [x] Add focused page tests for click-only acquisition, loading, success without
  saving/consent, all browser errors, invalid coordinates, manual fallback and
  explicit save, cancellation on manual edits and unmount.
- [x] Run tests before implementation and confirm the missing button causes failure.
- [x] Add the existing-design button above coordinates, accessible status/error
  messages, draft updates, cancellation, and submit validation in SellerPages.tsx.
- [x] Run focused and relevant frontend suites and production build. Report all
  remaining failures. No database operations, migrations, deployment or commits.

Verification: 13 tests failed before implementation; all 74 focused and related
tests passed after implementation. A stronger explicit-save assertion caught a
stale unsaved-status message; production code now clears that message after a
successful save. All 13 page tests passed on the final rerun. One intermediate
rerun failed waiting for the initial render; the new page fixture now allows up
to five seconds for that render. No production or global test timeouts changed.
TypeScript + Vite production build passed on final code. Focused code review
completed without remaining findings.

The full-suite invocation began before the final save-status correction and
finished with 312 tests: 310 passed, 2 failed. One was the now-corrected
`SellerProfileLocation.test.tsx` unsaved-status assertion; the final page rerun
passed 13/13 after the correction. The other was the previously observed
`AdminOperations.test.tsx` test `requires an investigation reason and sends only
authorized account action fields`, unable to find the Suspend Buyer button.
That unrelated failure remains unresolved. The full suite was not rerun after
the final correction; final page tests and production build were rerun and passed.

Commands (from project root):

```powershell
npm.cmd test -- --run src/pages/SellerProfileLocation.test.tsx src/components/LocationPicker.test.tsx src/components/DispatchLocation.test.tsx src/location/geolocation.test.ts src/Marketplace.test.tsx --maxWorkers=1 --testTimeout=20000 --reporter=json --outputFile=local-profile-location-focused.json
npm.cmd test -- --run src/pages/SellerProfileLocation.test.tsx --maxWorkers=1 --testTimeout=20000 --reporter=json --outputFile=local-profile-location-final.json
npm.cmd test -- --run --maxWorkers=1 --testTimeout=20000 --reporter=json --outputFile=local-profile-location-full.json
npm.cmd run build
```

All frontend tests use simulated browser location and mocked API responses; no
database or live-server writes. Existing changes from the preceding diagnostic
task remain untouched. Browser permission UX on a real device still needs manual
checking once the existing backend/schema blocker permits loading the form.
