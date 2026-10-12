# What Not? database services — Phase 4

Database-backed marketplace operations are exposed through selected authenticated
Phase 5 routes. Buyer geographic workflows remain **501**.
Health remains **200**, needs no database, and does not check database readiness.
The frontend remains an independent browser demo.

## Route -> Service -> Repository -> SQLAlchemy -> PostgreSQL

A **repository** knows how to query, insert, filter, load relationships, and lock
rows. It never commits and does not decide business rules. A **service** coordinates
repositories and applies ownership, roles, stock, and lifecycle rules. Phase 5
routes validate input, obtain authenticated identity, call a service, and map
its result. Keeping rules in services lets tests and HTTP use the same logic.

Explicit actor IDs are **trusted internal inputs**, not authentication. No actor
headers, fake login dependencies, or development persistence endpoints exist.
User creation, user listing, and activation are privileged internal operations.

## Session, transaction, commit, rollback

A **session** tracks objects and borrows a connection when needed. The application
engine is created lazily, shared between requests, and disposed at shutdown.
`get_session` gives each database request one session, rolls back unfinished work,
and closes it. Startup/import does not connect or create tables. Alembic owns DDL.

A **transaction** groups changes. **Commit** makes the group permanent;
**rollback** abandons it. **Flush** executes SQL inside a transaction without
committing it. The caller opens the outer transaction and commits once:

```python
from app.db.session import session_scope
from app.schemas.product import ProductCreate
from app.services.products import ProductService

with session_scope(engine) as session:
    product = ProductService(session).create(
        trusted_seller_user_id, trusted_seller_profile_id,
        ProductCreate(name="Clay vase", description="Made locally", price="250.00",
                      stock_quantity=5, category="Crafts", delivery_radius_km=2),
    )
    # Map responses while the session is open.
# Commit once on success; rollback and close on failure.
```

Phase 5 request dependencies explicitly use `with session.begin():`. A session
with no transaction, or a transaction started implicitly by a read/add, is rejected
by write services. Put the complete workflow, including reads, inside its scope.

Each write operation also has a **savepoint**, an inner rollback boundary.
Caught service failures cannot leave partial items or stock changes. Successful
savepoints do not commit the outer transaction. Let errors escape the outer scope
when the entire workflow must roll back. SQLAlchemy flushes already pending
changes before a savepoint: do not pass unrelated dirty objects into service calls.

Uniqueness/constraint failures become safe domain errors such as `DuplicateUser`,
`DuplicateSeller`, and `PersistenceConflict`. Read/connection failures remain
internal exceptions; eventual HTTP handlers must sanitize infrastructure errors.
Phase 5 HTTP error handlers sanitize database failures.

## User and seller operations

`UserService` creates, gets by ID/email/phone, lists with bounded pagination, and
changes active state. Internal `UserCreate` requires phone and an already encoded
bcrypt or Argon2id hash. Its hash is masked and excluded from serialization; public
user responses omit it. Structural checking rejects ordinary plaintext but cannot
prove the supplied value was cryptographically derived. Trusted callers own that
responsibility. Phase 5 `AuthService` supplies securely generated Argon2id hashes
for public registration and verifies passwords for login. See
[AUTHENTICATION.md](AUTHENTICATION.md) for JWTs and identity normalization.
Database email/phone uniqueness constraints are preserved.

`SellerService` creates a profile only for an active existing SELLER; one profile
per user. It reads profiles, lists seller-owned products, and permits shop name,
description, phone, and coordinate edits. Ownership and verification are not
editable. `seller_id` refers to a seller-profile ID, not a user ID.

## Product and moderation workflow

Seller adds product -> FastAPI -> service -> repository -> SQLAlchemy -> PostgreSQL.
Phase 5 seller/admin routes implement this flow with authenticated database actors.
Creation always sets PENDING. Active ADMIN callers approve/reject only
PENDING products. Rejection requires a trimmed nonblank reason; approval clears it.
Editing APPROVED returns it to PENDING. Editing REJECTED keeps its reason until
explicit resubmission returns it to PENDING and clears the reason. Activation is
independent of review and cannot grant approval. Seller writes enforce ownership.

Product updates, moderation, activation, and inventory changes lock product rows
and refresh current values. One API image maps to the primary `ProductImage`;
replacing/clearing it preserves secondary images. No uploads are implemented.

`list_buyer_candidates_without_geography` requires APPROVED + active + stock > 0.
These are **candidates**, not geographically eligible products. Neither this query
nor order creation calculates distance or implements the 1/2/3 km rule.

## Addresses

`AddressService` creates, gets, lists, updates, and sets defaults with ownership
checks. Zero defaults are allowed. Default changes lock the owning user, clear and
flush the old default, then set the new one within the same transaction. The parent
lock protects simultaneous first defaults; the partial unique index is a safeguard.

After any order references an address, actual changes to lines, city, state,
pincode, or coordinates fail. Label/default changes and unchanged delivery values
are allowed. Create a replacement address to move house. There is no historical
address snapshot table; service restrictions protect history. Direct SQL can bypass
these restrictions. Address deletion is not exposed.

## Atomic orders and stock locking

Buyer places order -> validation -> outer transaction -> buyer/address/seller
checks -> locked stock check -> order -> snapshot items -> stock reduction ->
flush -> commit once.

`OrderPlacement` accepts buyer, seller-profile, address, and unique product IDs
with positive quantities. It accepts no client price, fee, total, or status.
An active BUYER, owned address, existing profile, and active SELLER are required.
Every product must belong to that seller, be APPROVED and active, have a positive
price, and have sufficient stock. No geographic check exists yet.

Order items snapshot product name and unit price. Later product edits cannot
change purchase snapshots through services. Subtotal and total use exact Decimal
arithmetic. `DeliveryFeePolicy` defaults to **0.00**, independently of the frontend's
₹49 mock fee. A trusted caller may supply `DeliveryFeePolicy("7.50")` to
`OrderService`; this is a configurable provisional fixed fee, not shipping logic.

PostgreSQL `SELECT ... FOR UPDATE` locks requested products in ascending ID order
until the outer transaction finishes. Competing purchases wait and read the new
stock, preventing duplicate purchase of the final unit. Order creation uses shared
user locks so purchases can compete on product rows without unnecessarily
serializing through the seller. User writes use exclusive locks to prevent
deactivation during writes. Keep transactions short and avoid external calls while
holding locks. No distributed locking is needed.

Creation is **atomic**: a late database error rolls back order, items, and inventory.
Stock is reserved at placement, not acceptance. Snapshot rows have no edit service;
direct SQL can still change them.

## Order transitions

| Current | Allowed next |
|---|---|
| PLACED | ACCEPTED, CANCELLED, REJECTED |
| ACCEPTED | PREPARING, CANCELLED |
| PREPARING | OUT_FOR_DELIVERY |
| OUT_FOR_DELIVERY | DELIVERED |
| DELIVERED, CANCELLED, REJECTED | None |

The owning buyer can cancel PLACED/ACCEPTED orders. The owning seller performs
allowed seller transitions. ADMIN is not automatically an order owner. Repeated
status changes fail. Cancellation/rejection locks the order, checks current state,
then locks products in ascending ID order and restores quantities atomically.
Competing terminal requests cannot restock twice. If restoration exceeds the stock
integer limit, the whole operation fails without changing status. No refunds/payments.

## Validation, limits, and remaining gaps

Services revalidate supplied models, including mutated nested order items. PATCH
inputs preserve omitted fields and intentional nullable fields. Scalar IDs are
strict positive BIGINTs. Money has two decimal places and a maximum of
9,999,999,999.99; calculated amounts must fit. Stock/quantity are at most
2,147,483,647. Service prices are positive while the existing database permits
zero. Direct zero-price rows cannot validate as API responses or be ordered.

Response mappers preserve API `total` from `total_amount` and item `name` from
`product_name`. Registration now requires phone. Address selection for public
checkout remains deferred with geography. See [CONTRACTS.md](CONTRACTS.md).
No ORM changes or new migrations were required. Geography, frontend integration,
payments, and infrastructure remain deferred; selected authenticated HTTP routes
are active. See [AUTHENTICATION.md](AUTHENTICATION.md).

## Safe tests

The existing harness ignores application DATABASE_URL/.env, starts a generated
temporary PostgreSQL cluster, verifies its data directory, and passes explicit
generated test URLs to Alembic. It never accesses whatnot_db or upsc_compass.
Service tests use rolled-back transactions. Concurrency tests use separately
generated databases in the owned cluster, committed fixtures, independent sessions,
bounded waits, and observed lock contention. Missing binaries fail visibly.

From `backend/`, with PostgreSQL 17 binaries on PATH:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -m pytest tests/persistence -q -W error
.\.venv\Scripts\python.exe -m compileall -q app alembic tests
.\.venv\Scripts\python.exe -m pip check
```

The persistence suite includes Alembic upgrade/downgrade/re-upgrade and metadata
comparison. Do not run manual migration commands against existing databases.
Windows restricted tokens can block pg_ctl; use the same owned-cluster harness
outside that restriction when needed. From the repository root, run frontend tests,
TypeScript checks, production build, and `git diff --check`. No lint configuration exists.
