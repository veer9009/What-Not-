# What Not? PostgreSQL foundation — Phase 3

This phase adds storage definitions and migrations. The frontend still uses mock
state, health is process-only, and marketplace routes still return 501. No routes
open database sessions, create tables, register users, authenticate, reserve stock,
or create orders. Importing the application does not connect to PostgreSQL.

## Four separate pieces

| Piece | Purpose | Location |
|---|---|---|
| SQLAlchemy ORM models | Python mapping of tables, relationships, constraints | `app/models/` |
| Alembic migrations | Versioned SQL schema changes applied explicitly | `alembic/versions/` |
| Pydantic API schemas | Validate request/response payloads | `app/schemas/` |
| FastAPI routes | HTTP entry points; marketplace behavior is still deferred | `app/api/routes/` |

Changing an ORM class does **not** change an existing database. Write/review a new
migration, then explicitly apply it. Never use `Base.metadata.create_all()` for
application startup or to bypass migrations. The initial migration is a fixed
schema definition independent of later model edits.

## Model relationships

```mermaid
erDiagram
    users ||--o| seller_profiles : has
    users ||--o{ addresses : owns
    users ||--o{ orders : buys
    seller_profiles ||--o{ products : lists
    seller_profiles ||--o{ orders : receives
    products ||--o{ product_images : has
    addresses ||--o{ orders : used_by
    orders ||--o{ order_items : contains
    products ||--o{ order_items : referenced_by
```

- Every table has an auto-incrementing `BIGSERIAL` ID, represented by Python `int`.
  Foreign-key ID columns are `BIGINT`.
- `users` stores name, unique required email/phone, **password_hash** only, role
  BUYER/SELLER/ADMIN, active state, and timestamps. Hash generation is not implemented.
- `seller_profiles` has a unique required `user_id`, shop details, phone, required
  coordinates and verification state. A user can have zero or one profile.
- `products` belongs to a seller profile and stores listing details, price, stock,
  category, radius, moderation state, rejection reason, activity and timestamps.
- `product_images` stores URL strings, primary flag, sort order and creation time.
  It stores no binary images and provides no upload service.
- `addresses` belongs to a user and stores label, address lines, locality, pincode,
  required coordinates, default flag and timestamps.
- `orders` references a buyer, seller profile and address, with status, subtotal,
  delivery fee, total amount and timestamps. It has no payment fields.
- `order_items` stores order/product/seller IDs, positive quantity, and the
  order-time `product_name` and `unit_price` snapshots. A later product edit does
  not rewrite these stored values. There is no order creation service yet, and
  the database does not prohibit explicit updates to a snapshot row.

## Types, constraints and deletion

All monetary columns use exact `NUMERIC(12,2)`/Python `Decimal`, supporting
0 through **9,999,999,999.99**. Negative values and NaN are rejected; bounded
numeric columns also reject infinity and overflow. PostgreSQL rounds excess
fractional digits on direct SQL assignment; current API schemas reject more than
two decimal places. Never use floating-point arithmetic for future order totals.

Named CHECK constraints enforce roles, product/order statuses, stock >= 0,
radius in 1/2/3, quantity > 0, money >= 0, latitude -90..90, longitude -180..180,
and image sort order >= 0. Statuses are strings plus CHECK constraints, avoiding
the extra migration lifecycle of PostgreSQL native enum types.

`OrderItem.seller_id` participates in **both** composite foreign keys:

```text
(order_id, seller_id)   -> orders(id, seller_id)
(product_id, seller_id) -> products(id, seller_id)
```

Consequently, a product from another seller cannot be attached to an order, even
through direct SQL. The ORM order relationship supplies the shared seller ID;
the product relationship writes only product ID. The database checks both pairs.
Each product can occur at most once per order.

Partial unique indexes permit **at most one** primary image per product and
default address per user. Zero is allowed; switching the flag must clear the old
row first, within a future service transaction.

Foreign keys restrict deletion of referenced users, sellers, addresses and ordered
products. Deleting an unreferenced product cascades to its images; explicit order
deletion cascades to its items. No delete endpoints are implemented. Product/seller
activity flags support future non-destructive workflows.

Database constraints do not enforce role-dependent profile/order ownership,
address ownership by the order buyer, moderation reason consistency, allowed
state transitions, nonempty orders, eligibility, inventory reservations, subtotal
arithmetic, or historical address snapshots. These need explicit future service
design and transactions. Category remains a stored string; the existing API
currently restricts it to six demo categories.

## Index choices

- Primary keys and unique email, phone, and profile-user constraints already
  create indexes; no duplicate standalone indexes are added.
- Foreign-key lookups use indexes on product seller, address user, order buyer,
  seller and address, and item product.
- Image `(product_id, sort_order)` supports ordered image retrieval and product
  foreign-key lookup. Item `(order_id, product_id)` uniqueness also supports
  fetching all items for an order.
- Composite unique indexes on product/order `(id, seller_id)` are deliberate:
  PostgreSQL needs these referenced keys for the two composite foreign keys.
- Partial unique indexes implement the primary/default flags. Their predicates
  mean they cannot replace indexes needed to find **all** child rows.
- No speculative status, full-text, spatial or redundant seller-ID indexes are
  added. Choose further indexes from real query patterns in a later phase.

## Time and sessions

`created_at` and `updated_at` use `TIMESTAMPTZ` with `now()` insert defaults.
Values represent timezone-aware instants; display them in UTC at API boundaries.
`now()` alone does not maintain modification times. ORM and SQLAlchemy table
updates explicitly include `updated_at = clock_timestamp()` via `onupdate`.
Direct SQL must set `updated_at` itself; no database trigger is installed.
Product images have only `created_at`; order items have no timestamp fields in
the approved design.

`app/db/session.py` provides an explicit lazy engine factory with connection
liveness checks and a transaction context that commits on success, rolls back on
failure, and closes its session. The caller owns engine disposal. Routes do not
use this factory yet, and startup does not migrate/create anything.

## Environment configuration

Use Python 3.10+ and PostgreSQL 17. From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If no `.env` exists, copy `.env.example` to `.env`. Preserve existing settings.
Create a **new, dedicated** development database, for example `whatnot_app_dev`,
and a suitable local role using your PostgreSQL administration workflow. Neither
`whatnot_db` nor `upsc_compass` should be used for this project’s migrations/tests.
This implementation does not create a development database or alter existing roles.

Set this value in ignored `backend/.env`, replacing placeholders with your local
role credentials and database:

```dotenv
DATABASE_URL=postgresql+psycopg://whatnot_app:REPLACE_ME@127.0.0.1:5432/whatnot_app_dev
```

URL-encode special characters in credential components. `postgresql+psycopg`
selects psycopg 3, not psycopg2. Environment variables override `.env` settings.
Configuration masks the URL representation and validation inputs; SQL echo is
disabled. Never commit `.env`, real URLs, passwords, database dumps, or private
test-cluster files. Only the placeholder example belongs in Git. The database
URL is optional for current HTTP contracts but required for explicit DB work.

## Alembic local workflow

First verify that your configured URL names the newly dedicated development
database. The following commands explicitly act on that configured target:

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

The initial revision `0001` creates seven tables and their constraints/indexes.
Alembic also creates its own `alembic_version` table. `alembic check` detects
unmigrated model differences. For future changes:

```powershell
.\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "Describe schema change"
# Review generated upgrade/downgrade code before applying it.
.\.venv\Scripts\python.exe -m alembic upgrade head
```

For a **disposable dedicated database only**, the reverse migration is:

```powershell
.\.venv\Scripts\python.exe -m alembic downgrade base
```

That command removes marketplace tables and their data; it is not a data backup.
Tests verify downgrade followed by re-upgrade solely in temporary test databases.
Offline SQL generation is supported with `alembic upgrade head --sql`.

## Isolated persistence tests

Put PostgreSQL 17 `initdb`, `pg_ctl` and `postgres` binaries on PATH. On Windows:

```powershell
$env:PATH = 'C:\Program Files\PostgreSQL\17\bin;' + $env:PATH
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -m compileall -q app alembic tests
.\.venv\Scripts\python.exe -m pip check
```

The persistence fixture ignores application `DATABASE_URL` and `.env` entirely.
It creates its own temporary cluster/data directory, generated test-only
credentials, loopback port, and database names. It verifies that the server's
data directory matches its generated directory before creating any databases.
Alembic receives an explicit test URL. Tables are created **only by migrations**.
Each constraint/relationship test runs inside a rolled-back transaction; migration
round trips use a separate database within that same temporary cluster.
The fixture checks its exact cluster even after failed startup, stops any surviving
server, and confirms shutdown before removing temporary files. If shutdown cannot
be confirmed, it fails visibly and retains the owned directory for diagnosis.
Missing PostgreSQL binaries cause a visible failure, not a SQLite substitute.
Do not run `initdb` tests as a Unix root user; PostgreSQL requires a normal account.

Windows sandbox token restrictions may require permission to run this local
test process outside the sandbox. Output is captured to files because a Windows
server child can inherit output pipes and delay EOF. This does not require access
to an existing PostgreSQL server. No manual database is inspected or tested.

From the repository root, frontend validation remains:

```powershell
npm.cmd test -- --run
npx.cmd tsc -b
npm.cmd run build
```

The repository currently has no configured frontend or backend lint command.
Python compilation, warning-strict tests, dependency checks and TypeScript/build
checks provide the existing validation paths.

## API integration gaps and Phase 4

See [CONTRACTS.md](CONTRACTS.md#phase-3-storage-mappings-and-contract-gaps) for
every known storage/API mismatch. Existing contracts are intentionally unchanged.
Agree on the phone/address contracts, money boundaries and response mappings
before implementing authentication or order services. Frontend string IDs require
mapping/refactoring when actual API integration begins, including BIGINT handling
beyond JavaScript's exact integer range. No payments or infrastructure are included.
