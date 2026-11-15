# Proposed live buyer radius contract

Status: historical design, subsequently approved and implemented using the **public-point option**. See `LIVE_RADIUS_DISCOVERY_VERIFICATION.md` for QA-only migration 0009, explicit synthetic public-point consent and actual verification. The proposal below records the original alternatives; exact private-dispatch discovery was not selected.

## Existing model: what can actually be measured

`products.seller_id` references one `seller_profiles` row. A product has a delivery radius restricted to 1, 2 or 3 km (`backend/app/models/product.py:20`). The seller profile has non-null, bounded six-decimal latitude/longitude plus an explicit dispatch-confirmation timestamp (`backend/app/models/seller_profile.py:17`). A buyer can supply transient coordinates or an owned saved address with non-null coordinates. Product-specific independent locations do not exist.

Consequently, the current schema **can compute exact buyer-to-seller-dispatch distance without a migration**, if dispatch is the agreed listing location. It cannot represent a separate consented public discovery point, per-product location or multiple dispatch points. PIN alone is not a point. Browser accuracy is an estimate about the buyer point and cannot be used to guarantee eligibility or enlarge a delivery radius.

Current live discovery deliberately uses a seller-cell centre, not the exact dispatch point (`backend/app/services/discovery.py:13`). Seller points in the same 0.01-degree cell produce identical membership, tested in `backend/tests/persistence/test_beta_resume.py:89`. Current sample buttons use sample distances only.

## Privacy decision required before changing membership

There are two materially different approaches:

1. **Exact radius about existing private dispatch coordinates.** No schema change is needed. The server can calculate a distance and enforce both buyer and seller radii. However, a buyer can vary arbitrary input coordinates and observe whether a known product appears. Exact inclusion boundaries reveal information about the private seller point even if coordinates and distance are omitted from JSON. This breaks the existing same-cell indistinguishability requirement. A smaller number of radius choices, authentication or rate limiting alone does not eliminate that inference. Do not ship this change as a routine location fix.
2. **Exact radius about an explicitly public listing/business point.** Recommended if genuine exact discovery is required while private dispatch remains private. The model needs an approved public-point/consent lifecycle and explicit UI semantics; those fields do not exist today. Product discovery can enforce buyer distance to the public point while retaining the existing coarse dispatch candidate gate; checkout still strictly enforces actual delivery-address-to-private-dispatch distance. Do not expose private-dispatch exact eligibility through discovery as another hidden boolean oracle. If the public point differs from dispatch, state clearly that discovery proximity is not a delivery guarantee. Any needed schema design/migration requires separate approval and is outside this investigation.

Keeping today's coarse locality contract with a smaller displayed radius is not an acceptable implementation of **exact** buyer-radius filtering. Likewise, removing the 0.8 km margin alone still measures a cell centre rather than the actual listing point.

The requested numeric feature is technically possible with today's schema; a public, privacy-preserving exact-location contract is not present. Do not claim a missing spatial extension is the blocker. Resolve which point may be observable and obtain the product/privacy decision before implementation. No fields, extensions, SDKs or migrations were added.

## Proposed request and server semantics after that decision

Use a strict integer `radius_km` in `{1,2,3}` on live list and detail requests, along with exactly one location source. Reject booleans, numeric strings, fractional numbers, zero, unsupported radii and unknown fields with sanitized 422 responses. The UI always sends the chosen radius; a backward-compatible server default of 3 is a versioning choice to approve, not an implicit radius silently ignored by the server.

Example using **synthetic** coordinates:

```json
{"location":{"latitude":0,"longitude":0.005},"radius_km":1,"offset":0,"limit":100}
```

For the private-dispatch option only, define:

```text
d = Haversine_km(buyer point, confirmed seller dispatch point)
eligible = approved AND active product AND stock > 0
           AND active SELLER account AND confirmed valid dispatch
           AND within_radius(d, buyer radius)
           AND within_radius(d, product delivery radius)
```

Use `distance_km` and `within_radius` from `backend/app/services/geography.py`: radius 6,371.0088 km, inclusive boundary with only 1e-9 km arithmetic tolerance. Reuse numeric/range validation, longitude-wrap handling and finite checks. Do not enlarge either radius by browser accuracy or reuse the locality margin for an exact filter. This exact-private formula is a design option, **not** a change approved to replace current privacy behavior.

For the public-point option, measure buyer radius against the approved public point. Preserve product approval, activity, stock, seller/account/dispatch rules and the existing coarse dispatch gate. Preserve exact delivery enforcement at checkout using the selected owned delivery address, which can differ from the device discovery point. No client-supplied distance, seller point or eligibility flag is trusted. Apply filtering before offset/limit; list and detail must share the same source/radius rules. Continue minimal responses, generic ineligible detail 404, no-store headers and POST bodies rather than coordinate query strings.

Missing coordinates never become zero or a city/PIN centroid. The current database prevents missing dispatch points; a future public-point design must exclude missing/unconfirmed public points and provide an owner-facing correction workflow. Invalid historical rows should produce a sanitized operational signal, not fabricated distance or a permission bypass.

## Proposed frontend behavior

- Add the existing reusable 1/2/3 buttons to the **live** view with explicit selected state, initially 3 km; keep sample buttons separately labeled and unchanged.
- Store source and radius in session-memory discovery state. Include both in list/detail keys and effect dependencies. A radius change invalidates old results and pending callbacks and issues a new request only if a confirmed source exists. It does not request device permission again.
- Device acquisition remains explicit and one-shot. Re-detection/manual edits clear the active source, old results and obsolete accuracy, then require confirmation. Never make a PIN text change silently supply a coordinate.
- Show browser-reported accuracy and explain uncertainty near boundaries. Do not present a 206 m estimate as proof of actual positional error. Keep broad/unknown-accuracy warnings, saved-address fallback and manual coordinate entry.
- Display **No products nearby** for an actual empty eligible list; keep backend errors distinct. Detail/cart wording must distinguish proximity from delivery eligibility and the selected delivery address.
- Preserve PIN filtering of owned saved addresses; general postal geocoding is a separate feature. No Google SDK or paid API is needed for numeric radius filtering.

## Acceptance tests before shipping

Use only deterministic synthetic points in the identity-verified isolated test database. Test 1, 2 and 3 km inside/on/outside boundaries, dateline/poles, missing/invalid points, strict radius validation, buyer versus delivery-address differences, smaller seller radius, stock/moderation/account/dispatch exclusions, pagination after distance filtering, list/detail consistency, role/ownership denial and no coordinate response/logging. Preserve exact checkout and concurrent stock/price/idempotency checks.

Frontend tests must assert that the real selected radius reaches the API, changing it drops old results and ignores late responses, re-detection does not submit the old point, and denied/timeout/unavailable/manual/PIN paths remain usable. Keep empty/error states separate. Real Chrome permission testing and HTTPS re-testing remain separate from these mocks.

The existing private-point inference test must remain passing for the current privacy contract. If an approved public-point contract supersedes it, replace it with deliberate tests proving private dispatch remains indistinguishable while only consented public information affects exact proximity. Do not delete the test simply to make exact-private filtering pass.

Next implementation step: choose and approve the observable listing point and privacy contract. Then implement the strict source+radius request and shared server eligibility rule with focused regressions; stop for separate approval before any required public-point schema/migration work.
