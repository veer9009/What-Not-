# Client discovery rules — 26 November 2026

Only Homemade Products use a confirmed customer location and selected1/2/3km radius. Backend publication, active account/stock, seller public consent, public-point radius and product delivery-radius checks precede eligible pagination. Checkout independently checks exact saved-address delivery eligibility. Private seller coordinates and invented distances are not returned. Without location, Homemade prompts for confirmation.

Creative and Professional Services and Real Estate remain public approved catalogues without customer location or radius. Optional service remote/local and property locality/category filters remain independent. Protected actions retain authentication and ownership checks. Denied location must not block these catalogues.

Discover Picks round-robins bounded pages:30 records per source. View All exposes pagination rather than loading all records. Category product pages retain100-record bounds, service pages50, property pages30. Server search precedes pagination. Home caches public pages within the current query so a Homemade radius change does not re-request them; explicit Refresh fetches fresh pages.

Badges are derived from source domains: Homemade green, Creative purple, Professional blue, Real Estate teal. They overlay images or placeholders at top-left, preserving top-right save controls and uploaded originals. Listing metadata is genuine; absent photos, reviews or distances remain absent. Quotation listings show Request a Quote.

## Confirmed service availability failure

Read-only original-database inspection reproduced **SQLSTATE42703 / UndefinedColumn** for both service domains at revision0010: `creative_listings.domain` is absent. Migration0014 adds this column; current source head is0015. Original data/configuration were not migrated or modified. A release target needs a separately approved preparation through0015; mixing domains or fabricating listings is not a compatibility fix.

Public catalogue mounting also waits for authentication restoration to prevent API session-generation invalidation. This is separate from the schema error. Refer to the release report for completed verification and outstanding limitations.

Prepaid UPI remains disabled. No policy approval, bank verification, migration approval or deployment approval is granted by this document.
