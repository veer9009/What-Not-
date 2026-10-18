# Phase 7 location and discovery guide

Phase 7 adds real, authenticated Homemade discovery while retaining the public
sample catalogue and sample basket separately. Checkout and payments remain
unavailable. Real Estate and Creative Services remain Coming Soon.

## Seller dispatch semantics

The existing seller_profiles.latitude/longitude are the business/dispatch point,
never a continuously tracked device point. New and migrated profiles start with
dispatch_location_confirmed_at = null and are excluded from buyer discovery.
Create a profile, then explicitly confirm its actual preparation/dispatch place.
The seller can populate a draft manually or press Use current location. Acquiring
GPS does not save anything. Confirm dispatch location saves both coordinates and a
server UTC timestamp through the authenticated owner operation. Signing in from
another device/location has no effect.

An actual coordinate edit through the legacy generic profile PATCH clears the
confirmation. Shop metadata edits and unchanged coordinate writes preserve it.
The dedicated dispatch operation confirms intentional changes immediately. Each
subsequent discovery request reads current dispatch state; already displayed results
can become stale and are not reservations or checkout guarantees.

## Buyer discovery semantics

Choose an owned saved address, or explicitly confirm a transient manual/device
coordinate. A default address is never implicitly selected. Address-backed requests
use that address row's current persisted latitude/longitude and recheck ownership.
Existing historical-order restrictions on address delivery-field edits remain.

Transient sources live only in an authenticated-identity-scoped React provider.
List/detail navigation shares the selected source; logout, expiry and identity
changes discard it. Reload/new tabs require login and a fresh explicit choice.
No precise coordinate is saved in browser storage or URLs. Saving an address is a
separate explicit operation through the existing address API.

Manual latitude/longitude is a Phase 7 technical fallback and testing mechanism,
not the intended final customer experience. Future PIN/address search or a map
picker can supply the same numeric Coordinates value to the confirmation boundary.
Geocoding, maps, providers, spatial extensions and additional infrastructure are
outside this phase. Entering address text does not geocode it automatically.

## API contracts

All operations use the existing /api/v1 prefix and bearer identity/RBAC.

| Method | Path | Role and behavior |
|---|---|---|
| PATCH | /sellers/me/dispatch-location | Active SELLER, own profile only; confirm both coordinates |
| POST | /discovery/products | Active BUYER, location-aware list |
| POST | /discovery/products/{product_id} | Active BUYER, eligible detail or generic 404 |

Dispatch body: `{"latitude":19.076,"longitude":72.8777}`. Both fields are required;
actor IDs, verification and client timestamps are rejected. GET /sellers/me and
seller profile write responses include the nullable confirmation timestamp.

Discovery body is exactly one location source:

```json
{"location":{"latitude":19.076,"longitude":72.8777}}
```

or `{"address_id":4}`. List requests also permit strict integer offset (0 through
2147483647, default 0) and limit (1 through 100, default 100). Detail requests do
not accept pagination. Neither/both sources and unknown fields return sanitized
422 errors. Foreign addresses return 403; missing addresses return 404. Anonymous
or inactive users receive 401; other roles, including ADMIN, receive 403. Admin
moderation does not grant seller impersonation or buyer discovery access.

The buyer response includes id, name, description, price, stock_quantity, category,
delivery_radius_km, image_url, shop_name, actual is_verified and approximate numeric
distance_km. It excludes seller coordinates, phone, owner identity, confirmation
timestamp, address coordinates and ORM relations. Coordinates are not placed in
query strings or normal access-log paths. Successful discovery responses use
Cache-Control: no-store; the frontend also requests no-store. Do not log request
bodies or add coordinate analytics. Existing sanitized errors omit input/ctx.

POST reads intentionally keep precise transient coordinates out of URLs. Legacy
GET /products and GET /products/{id} stay explicit 501 placeholders; real discovery
uses the new group. POST /orders remains 501. Internal pre-existing order creation
is not activated or changed by Phase 7; future checkout must independently recheck
geographic/inventory eligibility in its own transaction design.

The frontend preserves BIGINT IDs as decimal strings in memory. Discovery encodes
validated address IDs as exact JSON integer literals, including values beyond
JavaScript's safe-number range. It never converts sample IDs into database IDs.

## Geography and availability

Existing NUMERIC(9,6)/Decimal columns and finite six-place coordinate validation
are reused. Latitude bounds are [-90,90], longitude [-180,180]. Browser/manual
transient values are validated before rounding to six decimal places. No string
arithmetic is used: the server converts validated numeric values to floats for
Haversine trigonometry with a 6371.0088 km Earth-radius constant and a clamped
intermediate. Longitude wraparound is supported.

Eligibility requires APPROVED + active product + positive stock + confirmed
dispatch + active SELLER account + distance within product radius (strict integer
1, 2 or 3 km). Compare unrounded distance with radius, including an absolute
1e-9 km arithmetic tolerance, with no relative tolerance. This tolerance does not
compensate for GPS error or storage rounding. Display distance rounds to two decimal
km after eligibility. Locations and distances are approximate.

Repositories query focused candidates; DiscoveryService owns location resolution,
ownership, distance and response rules. Eligibility precedes pagination. Stable
product-ID batches avoid a first-100-candidates cutoff and an unbounded ORM result.
V1 scanning remains linear and large offsets can be expensive; no spatial index,
PostGIS, geocoder, additional table or dependency is introduced. UI lists show up
to 100 eligible results and do not yet expose pagination controls.

## Browser and UI states

Only Use current location calls getCurrentPosition; neither mount nor login does.
There is no watchPosition. Requests use a 10-second timeout and maximumAge 0.
The injected wrapper handles success, denied, unavailable, timeout, unsupported
and invalid coordinate responses. HTTPS (or browser-trusted localhost) and explicit
browser permission are necessary for real device acquisition.

Forms distinguish drafts, requesting permission, updating, confirmed/available and
errors. Manual entry and saved addresses remain available without GPS. Late GPS
callbacks cannot overwrite a newer manual draft or update an unmounted component.
Changing a buyer draft clears its active source/results; stale API responses are
ignored using the existing mounted/version resource guards. List/detail pages have
loading, sanitized error/retry and empty states, and no fabricated ratings/distances.

Real routes are /buyer and /buyer/products/:id. Phase 6 demonstrations remain at
/buyer/samples and /buyer/samples/products/:id, with /buyer/cart explicitly sample
only. Real products cannot enter that sample basket. Checkout is disabled everywhere.

## Migration and verification

Alembic 0002 depends on 0001 and adds only nullable TIMESTAMPTZ
seller_profiles.dispatch_location_confirmed_at with no default or backfill.
Upgrade does not rewrite existing coordinates. Downgrade removes only that column
and its confirmation data. Re-upgrade leaves profiles unconfirmed. Tests preserve
representative 0001 rows through the round trip and compare ORM metadata at head.

No application database was migrated. Only the existing generated/verified disposable
PostgreSQL harness may be used for these tests. Never point testing/migration work
at whatnot_db or upsc_compass. Application startup never calls create_all().

Run the full commands in README. Optional live browser smoke now requires installed
Chrome/Chromium and Node 24's native WebSocket, without a Playwright dependency:

```powershell
$env:PATH = 'C:\Program Files\PostgreSQL\17\bin;' + $env:PATH
# Browser used for the final successful Windows validation (override as needed):
$env:WHATNOT_BROWSER_EXECUTABLE = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
npm.cmd run build
backend\.venv\Scripts\python.exe scripts\phase7_smoke.py
```

The runner creates a fresh isolated cluster and browser profile, disables server
access logs, uses owned loopback servers and pipes generated credentials. It checks
real confirmation/discovery/detail, browser states, dispatch changes, checkout
guards, storage privacy and 1280/768/390/320 widths. It emits fixed diagnostic stage
labels, not raw API/browser payloads. See PHASE7_REPORT.md for actual results.
