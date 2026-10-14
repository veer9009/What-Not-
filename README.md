# What Not?

A local marketplace with three business verticals: **Homemade**, **Real Estate**,
and **Creative Services**. Homemade covers food, handmade products and crafts;
Real Estate covers rent and sale; Creative Services covers video editing, VFX,
and editing for travellers and creators.

Phase 6 connects React account, seller product management, moderation, address
and order-history workflows to the authenticated FastAPI API. Homemade discovery
and the buyer cart are explicitly labelled samples. Real Estate and Creative
Services show illustrative coming-soon previews with no operational listing,
enquiry or booking tools. Real geographic discovery and checkout remain deferred.

[Integration guide](docs/FRONTEND_INTEGRATION.md) | [Phase 6 report](docs/PHASE6_REPORT.md)
| [Phase 6 scope correction](docs/PHASE6_SCOPE_CORRECTION.md)
| [Approved Phase 6 checkpoint](docs/PHASE6_CHECKPOINT.md)

## Run locally

Use the existing Node/pnpm frontend and Python 3.10+ backend dependencies.

```powershell
# Repository root: first setup only
corepack pnpm install
Copy-Item .env.example .env.local
# Start React/Vite
corepack pnpm dev --host 127.0.0.1
```

The frontend configuration is public `VITE_API_BASE_URL`, defaulting centrally to
`http://127.0.0.1:8000/api/v1`. Preserve existing environment files. Configure the
backend separately with a dedicated application database and private signing key,
following [database setup](backend/DATABASE.md) and
[authentication setup](backend/AUTHENTICATION.md). No database is provisioned or
migrated automatically.

```powershell
# backend directory, after configuration
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Use real registered credentials. Public registration offers BUYER and SELLER;
SELLER must then create a complete shop profile. ADMIN accounts come from the
existing trusted operator workflow. Workspace selection never grants a role.

Tokens remain only in browser memory. A reload/new tab requires login again;
logout and expiry clear identity, credentials, mounted records and the sample cart.
See the integration guide for the strategy, examples and security tradeoffs.

Default CORS permits only localhost/127.0.0.1 on port 5173. Other development or
production origins require an explicit `WHAT_NOT_CORS_ORIGINS` JSON list. Production
requires HTTPS and a configured frontend API URL; no wildcard CORS is used.

## Current workflows

- Real registration, login, `/auth/me`, logout and role-protected routes.
- Complete own seller profile creation/update, own products, create/edit, activation,
  rejection reasons and resubmission. HTTP(S) image URLs are supported; uploads and
  deletion are not available.
- Real ADMIN pending queue, approval and rejection with required reason. Fake counts,
  earnings and commission controls are removed.
- Own addresses, partial edits and default selection; historical delivery fields
  remain protected by backend services.
- BUYER/SELLER owned order history/details and eligible cancellation/progression.
- Warm Orange design tokens, loading/error/empty states and responsive forms.
- Existing WhatsApp help destination remains available.

Buyer discovery/detail/cart use sample data with illustrative distances, locations,
ratings and seller labels. Checkout is disabled. Backend GET products/detail and
POST orders remain 501; there are no eligibility bypasses, payments or real orders
from the sample basket. Product/moderation/order lists retain the first-100 backend
limit. See the guide for edit lookup and pagination limitations.

## Product review and order rules

Products start PENDING. ADMIN approves or rejects pending products; rejection needs
a reason. Approved edits return to PENDING; rejected edits preserve the reason until
explicit resubmission. Activation never bypasses review. Product PATCH sends only
changed fields to preserve untouched inventory; an unchanged save sends no request.

React suggests the existing order transitions for the owning role. FastAPI and
services remain authoritative for roles, ownership, stock and state transitions.
Real totals and item snapshots come from the backend. The sample delivery estimate
is unrelated to the backend's provisional fee.

## Verify

```powershell
# Repository root
node node_modules/vitest/vitest.mjs run --pool=vmThreads --maxWorkers=1
node node_modules/typescript/bin/tsc -b
npm run build
git diff --check
```

```powershell
# backend directory: isolated temporary PostgreSQL only
$env:PATH = 'C:\Program Files\PostgreSQL\17\bin;' + $env:PATH
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -m compileall -q app alembic tests
.\.venv\Scripts\python.exe -m pip check
```

The full backend suite includes authentication, authorization, persistence, services,
concurrency and Alembic upgrade/check/downgrade/re-upgrade validation. Tests never use
`whatnot_db` or `upsc_compass`, and have no protected-database fallback. Do not apply
migrations to either database. The schema remains the existing revision 0001.

The integration guide documents the optional live browser smoke runner with an
already installed Playwright module/browser. It creates fresh isolated PostgreSQL,
starts owned localhost servers and checks real workflows plus desktop/tablet/mobile
layouts. [Screenshots](docs/phase6/screenshots/) contain only temporary test data.

## Backend references

- [Authentication and authorization](backend/AUTHENTICATION.md)
- [API contracts](backend/CONTRACTS.md)
- [Services and business rules](backend/SERVICES.md)
- [Database and isolated testing](backend/DATABASE.md)
- [Phase 5 checkpoint](backend/PHASE5_REPORT.md)

API docs: `http://127.0.0.1:8000/docs`; health: `/api/v1/health`. Health does not
connect to PostgreSQL. Backend JSON IDs are integers; the client preserves them as
exact decimal strings and uses them in path parameters. Real money remains decimal
strings. Sample IDs never become fabricated database identities.

Phase 7 should define geographic eligibility and secure discovery/detail/checkout
contracts, with isolated tests, before activating real buyer purchasing. It has not
been started.
