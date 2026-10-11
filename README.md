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

Frontend content and state remain mocked in the browser. The standalone backend provides health, API contracts, and a PostgreSQL schema/migration foundation; it is not connected to the frontend. There is no real authentication, geolocation, payment processing, or map integration.

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

The next integration step is to agree on the product and order API contracts with the separately developed database layer. Keep ownership, moderation, eligibility and seller-order validation on the future server as well as in the UI.

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

Health returns `{"status":"ok","service":"what-not-api"}`. All other route groups (`auth`, `products`, `orders`, `admin`) are contract placeholders: valid requests return **501 Not Implemented**, invalid requests return **422**. No data is saved and no tokens are issued. Success response models in the docs describe future contracts, not working persistence.

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
application startup never creates tables or connects to a database. Existing HTTP
routes and frontend behavior remain unchanged.

See [backend/DATABASE.md](backend/DATABASE.md) for the relationship diagram,
constraints/indexes, `DATABASE_URL`, beginner migration workflow, and tests that
use a separate temporary PostgreSQL cluster. Existing `whatnot_db` and
`upsc_compass` databases must not be used for migrations or tests. The implementation
does not provision a development database. Persistence tests require PostgreSQL
`initdb` and `pg_ctl` on PATH. API/storage mismatches are recorded explicitly in
[the contract gaps](backend/CONTRACTS.md#phase-3-storage-mappings-and-contract-gaps).
