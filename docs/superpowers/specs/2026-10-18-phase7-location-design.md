# Phase 7 hyperlocal location system: proposed design

Date: 2026-10-18, Asia/Calcutta.
Status: proposed for owner review; implementation has not started.

## Goal and scope

Make Homemade discovery authoritative on the backend: APPROVED, ACTIVE,
positive stock, and within the product's 1/2/3 km radius of the seller's
explicitly confirmed business/dispatch location. Preserve the completed
authentication, moderation, inventory, address-history and order workflows.

Seller dispatch coordinates must persist independently of device movement.
Buyer discovery coordinates represent the place the buyer chooses to shop
from. Neither login nor page mounting requests geolocation. Payments, checkout
activation, Phase 8, deployment and unrelated redesign are excluded. No commits
or pushes are authorized.

## Baseline and inspection

- Starting branch: master; checkpoint e96c87c, Separate admin authentication
  from public login. Initial working tree clean.
- master and the local origin/master reference have zero commits of divergence.
  No remote fetch was performed; this is a local-reference comparison.
- Backend full warning-strict suite: 363 passed in 104.09 seconds.
- Frontend: 114 passed across 10 files.
- Standalone TypeScript, production build, Python compilation, pip check and
  git diff --check passed.
- The first sandboxed backend run had 183 passes and 180 setup errors because
  pg_ctl could not create a restricted Windows token (error 87). The identical
  suite passed outside that execution restriction. No harness changes were made.
- The passing suite includes authentication/authorization, persistence/services,
  transactions/concurrency and Alembic upgrade, metadata comparison, downgrade
  and re-upgrade. Both metadata comparisons reported no upgrade operations.
- Browser/e2e checks have not been run for this design-only stage.

Inspected README, database/service/auth/API documentation, Phase 6 checkpoint
and integration guidance, relevant ORM models and migration, route dependencies,
error handling, repositories/services, contract and persistence tests, frontend
API client, buyer/seller/address pages, resource lifecycle handling and browser
smoke harness. No repository AGENTS.md was found by the project file search.

## Existing concepts to reuse

SellerProfile.latitude/longitude and Address.latitude/longitude already use
NUMERIC(9,6)/Decimal, with database latitude/longitude bounds. Existing service
inputs reject non-finite values and limit precision to six decimal places.
Product.delivery_radius_km already permits only integer 1, 2 or 3 in the
database and request schemas. Do not duplicate any of these fields.

Seller profile writes derive the user from JWT identity. AddressService already
enforces ownership and protects delivery fields referenced by historical orders.
ProductRepository.buyer_candidates_without_geography already filters APPROVED,
active and positive stock. Services require explicit caller transactions and
use savepoints; repositories never commit.

Buyer pages currently use illustrative products/distances. GET /products,
GET /products/{product_id} and POST /orders are explicit 501 placeholders.
The buyer/cart sample flow must not become a purchase path for real products.

## Alternatives considered

1. Reuse coordinates and add one dispatch-confirmation timestamp (recommended).
   This preserves existing fields while requiring an explicit dispatch decision.
   Existing profiles remain undiscoverable until confirmed.
2. Treat every existing profile coordinate as a dispatch location. No migration,
   but legacy profile inputs did not establish the new dispatch semantics.
3. Add separate seller/buyer location tables or spatial infrastructure. This
   duplicates available storage or adds lifecycle/dependency costs without a V1
   requirement. PostGIS and geocoding providers are unnecessary here.

## Seller dispatch model

Reuse seller latitude/longitude. Add nullable
dispatch_location_confirmed_at TIMESTAMPTZ to seller_profiles. Null means the
seller has not explicitly established dispatch semantics. Do not backfill
confirmation or infer it from login, an existing address, or browser location.

PATCH /api/v1/sellers/me/dispatch-location accepts exactly latitude and longitude.
Both coordinates are required together. The authenticated active SELLER's profile
is resolved on the backend, locked and updated through SellerService. The server
sets the confirmation timestamp. No seller/user ID or client timestamp is accepted.
GET /sellers/me includes the confirmation timestamp for the owner.

Existing profile creation remains compatible and initially unconfirmed. After
creating a shop, the UI offers a separate explicit Confirm dispatch location action.
If confirmation fails after profile creation, show that the profile exists but
dispatch remains unconfirmed; never report the entire operation as saved.

Existing generic profile PATCH keeps its current contract. An actual coordinate
change through that route clears dispatch confirmation; metadata-only and unchanged
coordinate saves preserve it. The frontend uses the dedicated operation for
intentional dispatch changes. This closes a bypass via an older client.

The seller form labels this as the place products are prepared/dispatched from,
offers manual numeric coordinates and a Use current location button, and requires
explicit confirmation to persist the acquired point. GPS populates a draft; it
does not save automatically. Warn that saving changes geographic availability.
Login, reload and other devices only read the persisted setting.

## Buyer discovery model

Use one of two explicit inputs per discovery request:

- address_id: resolve through AddressService for the authenticated BUYER; use
  the address's current stored coordinate. Never accept an address owner ID.
- location: a transient coordinate pair entered manually or obtained through
  an explicit browser-location action.

Reject requests supplying neither or both. Default addresses are not silently
selected: the buyer selects an address and chooses Use for discovery. Existing
Address CRUD/default behavior and historical-address protections remain intact.
Saving an address is a separate explicit existing operation.

Keep a transient choice in an auth-scoped React provider so list/detail navigation
uses the same point. Clear it on logout, expiry or identity change; do not write
precise coordinates to localStorage, sessionStorage or URLs. Reload requires a new
explicit choice. Saved addresses remain available across sessions.

## Proposed discovery API

Introduce a focused /api/v1/discovery route group:

- POST /discovery/products: body containing address_id or location, plus bounded
  offset/limit; return eligible products in stable product-ID order.
- POST /discovery/products/{product_id}: same location source without pagination;
  return the eligible detail or generic 404 when absent/ineligible.

These are authenticated active-BUYER reads using POST to keep precise transient
coordinates out of query strings/access-log URLs. Responses use Cache-Control:
no-store. Unknown fields, actor IDs, client distances and client eligibility
flags are rejected. Existing GET product placeholders remain documented as
unsupported legacy contracts; the frontend uses the new explicit-location API.
POST /orders remains 501. No order-creation service behavior is changed.

Responses expose listing fields needed by buyers, shop name, actual verification
state and a backend-computed approximate distance. They omit seller latitude,
longitude, phone, confirmation timestamp and buyer/address coordinates. Use a
dedicated buyer response schema instead of serializing ORM relations. No fabricated
ratings, verification, stock or distance values are added.

## Service, repository and distance rules

DiscoveryService validates/revalidates input, checks the active BUYER, resolves
owned addresses, applies dispatch/availability rules and maps safe results.
Repository query work composes the existing candidate predicates with a confirmed
dispatch location and active SELLER account, loading only the required related data.
Keep the old geography-free candidate method explicitly internal and unchanged.

Apply geography before final pagination. An early out-of-range candidate must not
hide an eligible later product. For V1, scan candidates in bounded stable-ID batches,
apply the shared service distance predicate and count eligible rows for pagination.
Do not load an unbounded ORM result or apply a first-100 candidate cutoff. This
is linear scanning; document it and defer spatial/index optimization until needed.

Use one pure, tested Haversine function, with Earth-radius constant 6371.0088 km.
Validate finite numeric latitude/longitude and bounds before float conversion.
Convert Decimal to numeric float for trigonometry; never calculate on strings.
Clamp the Haversine intermediate to [0,1] before inverse trigonometry. Longitude
wraparound follows the formula and must be covered by antimeridian tests.

Eligibility uses the unrounded computed distance: distance_km <= radius_km,
including equality within an absolute 1e-9 km arithmetic tolerance and no relative
tolerance. This is numerical tolerance, not an expansion for GPS accuracy. Round
only the public display distance, proposed to two decimal km; never use that
rounded value for eligibility. Coordinates have six-place storage precision;
GPS acquisition is rounded to six places before submission, and all eligibility
decisions use the submitted/stored point. Show that location and distance are
approximate and do not promise surveying accuracy.

Each discovery request reads current seller dispatch state. A seller update affects
subsequent requests; an already rendered result can become stale. Refresh after
changing the buyer point and recheck detail with the same selected source. No
frontend-computed value can grant eligibility.

## Frontend and browser behavior

Preserve Warm Orange styling and existing layout patterns. Replace the authenticated
Homemade sample catalogue/detail with real eligible results. Keep public marketing
samples clearly illustrative and Real Estate/Creative Services Coming Soon. Remove
sample distances/cart actions from the real product flow. Keep checkout disabled;
the old sample basket must not accept backend product IDs or imply real ordering.

Provide location-not-set, manual-entry, requesting-permission, acquired-draft,
location-available, updating, denied, unavailable, timeout, unsupported, API-error,
loading and no-nearby-products states. An error or point change hides stale results.
Preserve the previous saved seller location if acquiring or saving a new draft fails.
Use mounted/operation-version guards so late GPS/API callbacks cannot overwrite
newer choices or another user's state.

Wrap navigator.geolocation in a small injected/testable abstraction. Only explicit
button actions call getCurrentPosition; never watchPosition. Use a finite timeout,
maximumAge 0 and finite-coordinate checks. Return bounded, sanitized error categories
instead of displaying raw browser errors. Manual coordinate entry and saved-address
selection remain available without device geolocation. An address-to-coordinate
lookup or map picker is not included; do not pretend address text is geocoded.

## Migration and privacy

Revision 0002 depends on 0001 and adds only the nullable timestamp with no backfill,
server default, coordinate rewrite or new table/index/dependency. Downgrade removes
only the new column. Existing records survive upgrade and re-upgrade. Test both the
existing full round trip and 0001 -> 0002 -> 0001 -> 0002 with representative rows.
Compare ORM metadata at head. Execute only through the existing verified isolated
PostgreSQL harness. Never migrate an application database or use create_all().

Review IDOR/BOLA for saved-address discovery and seller dispatch writes. Do not add
admin impersonation or a role bypass. Test anonymous, wrong-role, inactive and
cross-owner requests. Preserve generic sanitized error handlers; neither validation
errors nor logs should echo coordinates. Do not log request bodies, add analytics
for precise locations, or expose coordinates in public product responses. Document
HTTPS/browser secure-context requirements without adding frontend secrets.

## Implementation outline and required proof

This is an outline for design review; a detailed implementation plan follows
written-spec approval. Every meaningful behavior uses the existing red/green
testing conventions before implementation.

1. Add pure coordinate/distance/boundary tests, then the shared calculation.
   Cover identical points, known short distances, all three radii, boundaries,
   just-inside/outside, invalid/non-finite input, poles and longitude wraparound.
2. Add migration/confirmation/service and authenticated ownership tests, then the
   additive model/migration and seller operation. Verify stable persistence,
   confirmation clearing, rejected identity fields, rollback and login independence.
3. Add discovery service/API tests, then focused repository queries and service
   orchestration. Cover every existing status/stock/active predicate, seller account
   activity/confirmation, each radius, location changes, address ownership, privacy,
   generic unavailable detail and pagination after geographic filtering.
4. Add geolocation abstraction tests, then implement the wrapper. Cover success,
   denied/unavailable/timeout/unsupported, bad coordinates, rounding, explicit-only
   invocation and late callbacks.
5. Add frontend seller/buyer lifecycle tests, then location forms and real discovery.
   Cover manual and owned-address choices, GPS drafts, saved/failed updates,
   loading/error/empty states, logout/session changes and absence of sample distances
   or enabled checkout in the real flow. Preserve auth/moderation/order regressions.
6. Update contracts/integration/README and reproduce the browser checks with only
   disposable PostgreSQL and installed browser tooling. Add no dependencies merely
   to obtain screenshots. Exercise dispatch changes, buyer location methods,
   radius exclusion and desktop/tablet/mobile layouts.
7. Run full backend and frontend suites, migration checks, TypeScript, production
   build, Python compilation/dependency check and whitespace checks. Review the
   final diff for coordinates in public responses/logs and owner-ID trust. Provide
   the requested final report with actual counts and any unavailable browser checks.
   Do not label Phase 7 complete with required failures outstanding.

## Current review state

No application code, tests, ORM metadata, migration or API behavior has changed.
This design is the only intended tracked change. Validation logs and build outputs
are ignored artifacts. whatnot_db and upsc_compass were untouched; baseline database
work used only the generated, verified disposable test cluster. No commit, push or
deployment occurred. Phase 7 remains incomplete pending design review and execution.
