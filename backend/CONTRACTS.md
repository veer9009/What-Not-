# What Not? API contracts — Phase 2

Health is implemented. Every marketplace endpoint remains a **501** placeholder; request validation returns **422** for invalid payloads. Phase 4 implements database repositories/services tested directly, while HTTP access awaits authentication and geographic eligibility. There is no authentication, password hashing workflow, payment processing, or frontend API wiring. See [SERVICES.md](SERVICES.md).

## Identifiers and JSON

- `id`, `buyer_id`, `seller_id`, `product_id` and route `order_id`/`product_id` are positive integers from 1 through 9223372036854775807 (PostgreSQL signed BIGINT).
- `seller_id` refers to `seller_profiles.id`, not `users.id`; `buyer_id` refers to `users.id`.
- PostgreSQL generates IDs. Product creation/editing cannot supply an ID or seller identity; future authenticated HTTP integration must derive seller identity. Orders declare one seller, but buyer identity will be server-owned.
- The frontend currently has string product IDs and shop names. Integration must replace/map these to integer database IDs; do not convert mock names into fabricated numeric identities now.
- JavaScript numbers cannot exactly represent every BIGINT value. Future client integration must account for this when parsing/transporting integer IDs; the API contracts remain integers as requested.
- Money uses finite decimal values with at most two decimal places. JSON requests can use strings such as `"250.00"`; response money is serialized as decimal strings to retain precision. Product prices must be positive; order amounts cannot be negative.
- Unknown payload fields are rejected. Text fields are trimmed and cannot be blank. Product names/user names are limited to 120 characters, descriptions to 5000, and rejection reasons to 2000.

## Auth and user contracts

`UserRegistration` accepts name, email, password (8–128 characters), and role `BUYER` or `SELLER` (default `BUYER`). Public registration cannot request `ADMIN`. `LoginRequest` accepts email and password; these schemas do not authenticate or hash anything. `SecretStr` masks passwords in model representations; it is not encryption or password hashing.

`PublicUserResponse` contains integer `id`, name, email, and role (`BUYER`, `SELLER`, `ADMIN`), with no password field. A token response is intentionally not defined until the authentication phase.

## Product contracts and review

`ProductCreate`: name, description, price, stock_quantity, category, delivery_radius_km, and optional image_url (HTTP(S)). Categories match the frontend: Handmade, Home Decor, Gifts, Fashion, Jewellery, Crafts. Stock is an integer at least zero; radius is strictly integer 1, 2 or 3.

`ProductUpdate` is a partial edit of the same fields. At least one field is required. Services preserve `model_fields_set` when revalidating and use `model_dump(exclude_unset=True)` after validation. Omitted fields remain unchanged. Explicit null is rejected except for image_url, where null clears the primary image reference. Frontend data-URL image previews are demo-only; actual image storage/upload will need a later contract.

`ProductResponse` also contains integer id/seller_id, status (`PENDING`, `APPROVED`, `REJECTED`), rejection_reason and is_active. Its defaults are `PENDING` and active. Rejected responses require a nonblank reason; other statuses cannot retain a reason.

`ProductActivation` accepts a strict boolean is_active. `ProductRejection` requires rejection_reason. Approval is a separate admin route, so seller payloads cannot set moderation fields.

Rules now implemented internally by Phase 4 services (HTTP integration remains deferred):

- Create → PENDING.
- Admin may approve/reject only PENDING products. Rejection requires a reason.
- Editing an approved product → PENDING, clearing any old rejection reason.
- Editing a rejected product retains REJECTED and its reason until explicit resubmission → PENDING, clearing that reason.
- Activation is independent of review. Reactivation cannot grant approval.
- Buyer listing, detail and checkout eligibility require APPROVED + active + stock_quantity > 0 + buyer within delivery_radius_km. No buyer coordinates or server-calculated distance are available yet.

## Order contracts

`OrderCreate` accepts one seller_id and a nonempty list of `OrderItem` values containing product_id and positive integer quantity. Duplicate product IDs are rejected. The client cannot supply buyer identity, prices, totals or status.

One seller_id expresses one seller per order. Schema validation cannot look up product ownership: Phase 4 services confirm every referenced product belongs to that seller and reject mixed-seller requests. The frontend already splits a mixed basket into seller-specific orders and will eventually send one request per seller.

`OrderItemResponse` includes product_id, seller_id, name, quantity and unit_price as a purchase snapshot. `OrderResponse` contains id, buyer_id, seller_id, items, status, subtotal, delivery_fee and total. It validates matching item sellers, unique products, subtotal arithmetic and total = subtotal + delivery_fee. The internal service uses a configurable provisional 0.00 delivery fee; the frontend's ₹49 mock fee is not a backend rule.

Statuses: PLACED (default), ACCEPTED, PREPARING, OUT_FOR_DELIVERY, DELIVERED, CANCELLED, REJECTED. `OrderStatusUpdate` validates these values only; Phase 4 services enforce allowed transitions and trusted actor ownership. No HTTP endpoint changes order state or reserves stock.

## Routes

All paths have the `/api/v1` prefix.

| Method | Path | Current behavior |
|---|---|---|
| GET | /health | 200 process health |
| POST | /auth/register | 501 registration contract |
| POST | /auth/login | 501 login contract, no token |
| GET, POST | /products | 501 list/create contracts |
| GET, PATCH | /products/{product_id} | 501 read/edit contracts |
| PATCH | /products/{product_id}/activation | 501 activation contract |
| POST | /products/{product_id}/resubmit | 501 review resubmission contract |
| GET, POST | /orders | 501 list/create contracts |
| GET | /orders/{order_id} | 501 read contract |
| PATCH | /orders/{order_id}/status | 501 lifecycle contract |
| GET | /admin/products/pending | 501 review queue contract |
| POST | /admin/products/{product_id}/approve | 501 approval contract |
| POST | /admin/products/{product_id}/reject | 501 rejection contract |

Future database integration must enforce ownership, authorization, review transitions, product visibility, atomic stock checks/reservation and order creation. Health currently checks only that this process is responding. Pydantic contracts do not themselves create SQL models, migrations or persistence.

## Phase 4 integration status

The internal services now enforce ownership, active roles, review transitions,
atomic order/item insertion, stock reservation/restoration, and address ownership.
Their explicit actor IDs are trusted application inputs, never authentication.
HTTP routes stay 501. No request actor-ID shortcuts were added.

API input refinements align existing contracts with storage: money is at most
9,999,999,999.99 and stock/quantity at most 2,147,483,647. Unknown fields, strict
IDs/booleans, positive prices, and decimal precision rules remain. Existing schemas
are revalidated when passed to services; PATCH omission semantics are preserved.

Internal user creation supplies required phone and precomputed encoded hash;
public registration still lacks phone and remains deferred. Internal order
placement supplies buyer/address IDs; OrderCreate's HTTP shape remains unchanged.
Response mappers use total_amount -> total, product_name -> name, and primary
ProductImage -> image_url. Direct zero-price storage rows remain incompatible with
positive-price responses and cannot be ordered through services. Geographic
eligibility, frontend mock ID/BIGINT handling, and authentication remain unresolved.

Order status transitions, address history protection, provisional zero fee, and
SQLAlchemy transaction boundaries are documented in [SERVICES.md](SERVICES.md).
No ORM schema change or new Alembic migration was needed. The Phase 3 gap table
below is retained as the original storage/API comparison; this section describes
the mappings now implemented internally.

## Phase 3 storage mappings and contract gaps

No existing Pydantic schema or HTTP behavior changed in Phase 3. These differences
must be resolved explicitly before services connect the contracts to storage:

| Contract | Database design / future integration action |
|---|---|
| Registration/public user omit phone | `users.phone` is required and unique. Define phone collection and response policy before authentication persistence. |
| Order creation/response omit address ID | `orders.address_id` is required. Define address selection and buyer-address ownership validation before order persistence. |
| Order response uses `total` | Map explicitly from `orders.total_amount`; do not rename the API silently. |
| Product exposes one optional `image_url` | Storage uses multiple `product_images`. Map the primary image, permitting none, and design upload/storage separately. Frontend data URLs remain mock-only. |
| Order item response uses `name` | Map from `order_items.product_name`, the stored order-time snapshot, rather than the current product name. |
| API prices/unit prices must be positive | Database prices/unit prices allow zero as approved. Zero-price rows cannot currently validate as these API responses; choose a policy before integration. |
| API decimals have no total precision bound | Storage is `NUMERIC(12,2)`, maximum 9,999,999,999.99. Introduce compatible API upper bounds before writing persisted amounts. Direct SQL rounds extra fractional digits while API validation rejects them. |
| Frontend IDs are mock strings | Replace/map them to database integers during integration. Also handle PostgreSQL BIGINT IDs beyond JavaScript's exact integer range. |
| Product API requires moderation reason consistency | Database checks status values but does not implement moderation semantics. Future services must validate reasons/transitions. |
| API limits categories/text and validates URLs | Storage category is a string, descriptions/reasons/image URLs are text. Future services must continue applying contract validation; database writes do not automatically run Pydantic. |

The two composite foreign keys on `order_items` now enforce matching order/product
seller ownership at database level, supplementing service checks.
`OrderItem.seller_id` is copied from the order; `product_name` and `unit_price` must
be copied from the product; Phase 4 services implement snapshots and atomic stock
transactions. There is still no active order HTTP endpoint.

Services now enforce role rules, buyer-address ownership, nonempty orders, total
arithmetic, lifecycle transitions, and address history protection. Geographic
eligibility and authenticated HTTP integration remain deferred. See [DATABASE.md](DATABASE.md)
for models, indexes, migrations and isolated tests.
