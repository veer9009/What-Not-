# Phase 7 Location Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, task by task, with red/green tests. The owner explicitly authorized autonomous planning and execution on 2026-10-18. No further plan handoff or commits.

**Goal:** Authoritative hyperlocal Homemade discovery with intentional seller dispatch and buyer location selection.

**Architecture:** Reuse Decimal coordinates, address ownership, candidate predicates and explicit service transactions. Add seller dispatch confirmation, a pure distance module and a focused discovery service/API. React stores transient discovery choices only in auth-scoped memory.

**Tech Stack:** Existing FastAPI/Pydantic/SQLAlchemy/Alembic/PostgreSQL and React/TypeScript/Vitest. No new dependencies.

**Spec:** ../specs/2026-10-18-phase7-location-design.md (approved).

## Global constraints

- Preserve Phase 1–6 auth, RBAC, moderation, stock, address history and orders.
- No silent GPS, seller coordinates in buyer responses, client-authoritative eligibility or repository commits.
- Only verified disposable PostgreSQL testing; never touch whatnot_db or upsc_compass.
- No checkout activation, payments, Phase 8, deployment, commit or push.
- Manual coordinates are the technical fallback; friendly address/PIN/map selection is a future enhancement. Keep a coordinate-source interface without provider dependencies.
- Work in the requested checkout on master; preserve the approved untracked design document.
- Baseline: backend 363, frontend 114; migration round trip, TypeScript/build, compilation/dependencies and whitespace passed (see spec).

## Review focus

- Late GPS/API responses after logout or source changes must not restore another location/result (Task 5).
- A coordinate changed through generic profile PATCH must invalidate confirmation (Task 2).
- Eligibility must precede pagination even beyond 100 rejected candidates (Task 3).
- A displayed rounded boundary distance must not grant access outside the radius (Tasks 1/3).
- Partial profile-create/dispatch-confirm failures must leave truthful UI state (Task 5).

## Task 1: Coordinates and Earth distance

**Files:** create backend/app/services/geography.py and backend/tests/test_geography.py.

**Interface:** distance_km(latitude_a, longitude_a, latitude_b, longitude_b) -> float;
within_radius(distance: float, radius: int) -> bool. Accept numeric Decimal/int/float, reject bool/string/non-finite/out-of-bounds. Radius integer 1/2/3 only.

- [x] Write tests: identical -> 0; equatorial 0.001 degrees -> approximately 0.111195 km; antimeridian 179.999/-179.999 -> approximately 0.22239 km; poles; invalid values; radii 1/2/3 at boundary, +/-1e-6 km, absolute tolerance 1e-9 km.
- [x] Run .venv/Scripts/python -m pytest tests/test_geography.py -q; confirm missing implementation failure.
- [x] Implement clamped Haversine, radius constant 6371.0088, finite/bounds validation and unrounded predicate.
- [x] Run focused tests plus existing coordinate/input tests.

## Task 2: Confirmed dispatch persistence and ownership

**Files:** seller_profile.py, schemas/marketplace.py, services/sellers.py,
api/routes/sellers.py; create schemas/location.py and migration 0002; create
tests/persistence/test_dispatch_location.py.

**Interface:** Coordinate(latitude: existing Latitude, longitude: existing Longitude);
SellerService.set_dispatch_location(actor_id, Coordinate) -> SellerProfile.
PATCH /sellers/me/dispatch-location, owner response includes nullable timestamp.

- [x] Test initial confirmation null, explicit confirmation persists with both coordinates, unrelated profile edit preserves it, generic changed coordinate clears it; login does not change it.
- [x] Test anonymous 401, other roles 403, inactive 401; spoofed user/seller IDs, partial/non-finite/out-of-bounds coordinates -> sanitized 422; another seller's profile stays unchanged.
- [x] Test 0001 rows survive upgrade/downgrade/re-upgrade, nullable timestamp, metadata check. Run new tests red against the disposable harness.
- [x] Add nullable timezone-aware timestamp with no default/backfill and dedicated service operation under existing locks/savepoint. Resolve actor-owned profile; repositories do not commit.
- [x] Run dispatch tests and existing profile/authorization/migration tests green.

## Task 3: Geographic discovery API

**Files:** create schemas/discovery.py, services/discovery.py, api/routes/discovery.py;
modify repositories/products.py and main.py; create tests/persistence/test_discovery.py
and tests/test_discovery_schemas.py.

**Interfaces:** DiscoverySource exactly one address_id or Coordinate location;
DiscoveryQuery adds offset >=0 and limit 1..100 (strict integers).
DiscoveryService.list(actor_id, query) -> list[BuyerProduct];
DiscoveryService.get(actor_id, product_id, source) -> BuyerProduct.
ProductRepository.discovery_candidates(after_id, limit) -> bounded products with sellers/images;
eligible_detail(product_id) -> current candidate or None.

- [x] Test XOR source, malformed IDs/coordinates, unknown fields and pagination validation red.
- [x] Test POST /discovery/products and /discovery/products/{id}: proper BUYER, owned address, transient numeric pair, confirmed active seller, APPROVED+active+stock; no location or seller fields leaked; no-store headers.
- [x] Test every excluded state, out-of-radius rounded distance, changing dispatch, wrong owners/roles/inactive users; generic 404 detail, stable eligible pagination beyond 100 rejected candidates. Confirm red before implementation.
- [x] Implement focused repository predicates/eager loads; service computes distance before pagination using ID batches. Revalidate service inputs and preserve old candidate query/GET placeholders/orders.
- [x] Run geography/discovery plus existing marketplace, API-contract and auth regressions green.

## Task 4: Explicit browser location acquisition

**Files:** create src/location/geolocation.ts and geolocation.test.ts.

**Interface:** Coordinates {latitude:number;longitude:number};
acquireLocation(geolocation?: Pick<Geolocation,'getCurrentPosition'>) -> Promise<Coordinates>;
LocationError with sanitized code denied/unavailable/timeout/unsupported/invalid.

- [x] Write success, six-place rounding, all error codes, invalid bounds/non-finite, missing browser API tests red.
- [x] Implement one getCurrentPosition call with timeout 10000, maximumAge 0, no watchPosition. Keep injected provider compatible with future coordinate selection.
- [x] Run focused Vitest green.

## Task 5: Seller and buyer UI

**Files:** create api/discovery.ts, state/DiscoveryContext.tsx, components/LocationPicker.tsx,
components/DispatchLocation.tsx, pages/DiscoveryPages.tsx and related tests;
modify App.tsx, SellerPages.tsx, Shared.tsx, API types, ApiStates.tsx, AddressPage.tsx,
ExploreVerticals.tsx and scope/integration tests where discovery expectations change.

**Interfaces:** DiscoverySource = {location:Coordinates}|{address_id:Id}; auth-keyed
DiscoveryProvider exposes source/choose/clear. LocationPicker obtains a draft and
commits only on explicit use/save. Discovery API client sends POST JSON; never URLs.

- [x] Add real workflow tests red: no mount-time GPS/discovery; manual source, address selection (no implicit default), GPS success/denial/unsupported/error, loading/empty/error, real list/detail with disabled checkout and no fake metrics/cart additions.
- [x] Add dispatch component tests red: confirmed/unconfirmed, acquired draft does not persist until confirm, update failure retains saved point; late GPS responses after unmount/input change ignored.
- [x] Add context/API lifecycle tests: navigation preserves source, logout/identity remount clears it, old discovery response cannot replace newer source. Manual input rejects empty/non-finite/out-of-bounds before request.
- [x] Implement location abstractions/components and real pages using existing styling/resource lifecycle guards; integrate explicit dispatch below profile form (create first, then confirmation). Keep sample cart isolated; raw coordinates clearly technical fallback.
- [x] Update only obsolete sample-discovery assertions while preserving independent business/auth/order tests. Run focused then complete frontend suite green and TypeScript.

## Task 6: Documentation and live browser validation

**Files:** README.md, backend/CONTRACTS.md, backend/SERVICES.md, backend/DATABASE.md,
docs/FRONTEND_INTEGRATION.md; create scripts/phase7_smoke.py, scripts/phase7_browser.mjs,
docs/PHASE7_REPORT.md.

- [x] Update authoritative current behavior, endpoint bodies/privacy, dispatch confirmation migration, boundary rule, session location, future friendly picker and linear-scan limitations. Preserve historical phase reports.
- [x] Adapt the existing smoke runner to a new Phase 7 entry point and isolated generated cluster; disable server access logs, pipe generated credentials, never application DB settings. No production DB migration commands.
- [x] Exercise real registration/login/profile/confirmation/product/moderation, buyer manual/address/GPS discovery, near/far dispatch changes, denied/unsupported browser behavior and viewport overflow checks. Report exact browser availability/results without fabricating checks.

## Task 7: Final validation and report

- [x] Full backend: .venv/Scripts/python -m pytest -q -W error with PostgreSQL 17 PATH, using established outside-sandbox execution if required.
- [x] Frontend: node node_modules/vitest/vitest.mjs run --pool=vmThreads --maxWorkers=1.
- [x] TypeScript: node node_modules/typescript/bin/tsc -b; production: npm run build.
- [x] Python compileall app alembic tests; pip check; git diff --check and source whitespace review. Full suite includes persistence/auth/concurrency/migration checks.
- [x] Review complete diff against the spec; obtain code review using the applicable review skill and resolve required findings with focused red/green tests.
- [x] Record test counts, migration/e2e result, all known limitations, changed files/status and protected-database/no-commit confirmations in full Phase 7 report. Stop for owner review.

## Execution ledger

Plan self-review: spec sections map to Tasks 1–7; no schema duplication or extra dependency.
User's approved clarification is included in Tasks 4–6. Baseline and starting state
are inherited from the immediately preceding design review; no application edits intervened.
Execution complete without commits. Task 1 RED missing geography module -> 48 input/geography passes.
Tasks 2–3 RED missing dispatch/discovery routes and schema -> combined 81 passes;
full backend 444 passes, including all migration/auth/concurrency regressions.
Task 4 RED missing abstraction -> 10 geolocation passes.
Task 5 RED missing picker/dispatch and five real UI flows -> focused green;
auth regression caught/corrected; final complete frontend 139 passes in 16 files.
Review fixes: network isolation and pending-save editing each reproduced RED;
focused 7 passes, independent re-review no remaining Critical/Important findings.
Task 6 final live Edge/Chromium smoke exited 0; all browser assertions and owned
server/disposable PostgreSQL cleanup confirmed. Chrome failures were not counted
as final success. Rendering waits were added to native browser actions.
Task 7 TypeScript/build, compilation, pip check, migration metadata and whitespace
passed. Full report: docs/PHASE7_REPORT.md. HEAD remains e96c87c; all 51 files
uncommitted for review. No protected database, commit, push or deployment touched.
