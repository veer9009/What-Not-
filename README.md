# What Not? — Hyperlocal Marketplace Demo

A polished frontend-only concept demo for a local marketplace connecting buyers with nearby makers, artisans, and small businesses.

## Run locally

```bash
corepack pnpm install
corepack pnpm dev
```

Open the local URL shown by Vite. Use any non-empty email and password on the buyer, seller, or admin login screens.

## Verify

```bash
corepack pnpm test -- --run
corepack pnpm build
```

## Demo scope

- Buyer discovery, search, category and 1/2/3 KM radius filtering
- Product details, seller-area eligibility, cart and UI-only checkout
- Seller dashboard, add/edit/delete listing interactions and approval states
- Admin metrics, product approval/rejection and commission placeholder
- WhatsApp contact link for `+91 80800 98882`

Frontend content and state remain mocked in the browser. The standalone backend now provides real authentication, role/ownership authorization, PostgreSQL persistence, and marketplace services. It is not connected to the frontend. Geography, payments, and map integration remain deferred.

## Authentication and authorization (Phase 5)

Public BUYER/SELLER registration hashes passwords with Argon2id; ADMIN registration
is forbidden. Login issues a short-lived JWT. Protected requests load the active
user and role from PostgreSQL, then enforce resource ownership through services.
Seller registration creates only the account; complete shop profiles are created
separately. Product writes, seller profiles, own addresses/orders, and admin
moderation are active. Buyer discovery/detail and checkout remain 501 until geography.

See [backend/AUTHENTICATION.md](backend/AUTHENTICATION.md) for setup, required signing
secret, Bearer tokens, roles, ownership, routes, HTTP errors and Ravi's concrete flow.
No schema migration or frontend integration was introduced.

## Database-backed services (Phase 4)

User/seller/product/moderation/address/order services now enforce marketplace rules
through focused SQLAlchemy repositories. Atomic order creation reserves stock with
PostgreSQL row locks; eligible cancellation/rejection restores inventory once.
No schema change was needed. Phase 5 activates secure service-backed routes;
buyer geographic workflows remain 501. Health still works without a configured database.
The backend's provisional delivery fee is 0.00, independently of the demo's ₹49.

See [backend/SERVICES.md](backend/SERVICES.md) for beginner explanations, operations,
transaction ownership, order transitions, remaining contract gaps, and isolated
PostgreSQL tests. No tests access `whatnot_db` or `upsc_compass`.

## Product review workflow

- The seller's **Demo shop** selector switches mock shop identity. Inventory and edit actions belong to the selected shop. It is a demo control, not authentication.
- New products start `PENDING`. Editing an approved product sends it back to review. Sellers cannot set approval status through add/edit actions.
- Admin reviews the image, shop, category, description, price, stock and delivery radius. Rejection requires a nonblank reason.
- Rejected products retain the reason while the seller edits them. **Save Changes** saves the draft; **Resubmit for Review** returns it to `PENDING` and clears the old reason.
- Deactivation is independent of approval. Reactivation never bypasses review.
- Discovery, featured listings, buyer detail links, cart additions and checkout require `APPROVED`, active, in-stock products within their delivery radius. Distance remains the existing mock distance.
- Checkout groups the basket by seller, creates one mock order per shop, snapshots the purchased products, decreases stock and clears the cart. Delivery is ₹49 per seller order, shown before checkout.
- Product images are previewed locally (JPG/PNG, up to 5 MB). Listings, image previews and orders reset when the page reloads.

Run all tests with `npm.cmd test -- --run` on Windows, check TypeScript with `npx.cmd tsc -b`, and build with `npm.cmd run build`. No lint script or lint configuration is currently installed.

The next phase should establish server geographic eligibility before activating
buyer discovery and checkout. Frontend integration needs its own plan and contracts.

## Backend foundation (Phase 2)

`backend/app/main.py` creates **What Not? API**, version **0.1.0**. Routes live in `app/api/routes/`, Pydantic request/response contracts in `app/schemas/`, and environment settings in `app/core/config.py`. Tests live in `backend/tests/`.

Use Python 3.10 or newer. From the repository root, open PowerShell and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The virtual environment keeps backend dependencies separate from your system Python. These commands call its Python directly, so activation and PowerShell execution-policy changes are unnecessary. Copy `.env.example` only during initial setup; preserve any existing `.env` settings. Stop the server with Ctrl+C.

For macOS/Linux, use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`, and `cp .env.example .env` to create the configuration file.

- Interactive API docs: http://127.0.0.1:8000/docs
- OpenAPI contract: http://127.0.0.1:8000/openapi.json
- Working health check: http://127.0.0.1:8000/api/v1/health

Health returns `{"status":"ok","service":"what-not-api"}`. Configure a dedicated
application database and `WHAT_NOT_JWT_SECRET_KEY` before using authentication or
protected routes. See the [authentication guide](backend/AUTHENTICATION.md) for active
routes and the three geographic contracts intentionally remaining 501.

Local CORS allows `http://localhost:5173` and `http://127.0.0.1:5173`. If Vite uses a different port, edit `WHAT_NOT_CORS_ORIGINS` in `backend/.env` as a JSON array of exact origins, then restart the server. Environment variables override `.env`. The `.env` file and virtual environment are Git-ignored.

Run backend tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

From the repository root, the frontend checks remain `npm.cmd test -- --run`, `npx.cmd tsc -b`, and `npm.cmd run build`.

API IDs are positive **integers** aligned with PostgreSQL `BIGSERIAL`/`BIGINT`; string IDs and booleans are rejected in JSON bodies. Existing frontend mock/string IDs remain unchanged and must be mapped or refactored when real API integration begins. See [backend API contracts](backend/CONTRACTS.md) for fields, routes, business rules and integration boundaries.

## PostgreSQL persistence foundation (Phase 3)

SQLAlchemy 2 typed models now define users, seller profiles, products, images,
addresses, orders and order items. Alembic revision `0001` owns schema creation;
application startup never creates tables or connects to a database. Phase 5 uses
this unchanged schema for authenticated HTTP routes; frontend behavior is unchanged.

See [backend/DATABASE.md](backend/DATABASE.md) for the relationship diagram,
constraints/indexes, `DATABASE_URL`, beginner migration workflow, and tests that
use a separate temporary PostgreSQL cluster. Existing `whatnot_db` and
`upsc_compass` databases must not be used for migrations or tests. The implementation
does not provision a development database. Persistence tests require PostgreSQL
`initdb` and `pg_ctl` on PATH. API/storage mismatches are recorded explicitly in
[the contract gaps](backend/CONTRACTS.md#phase-3-storage-mappings-and-contract-gaps).
