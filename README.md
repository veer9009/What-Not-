# What Not?

A local marketplace with three business verticals: **Homemade**, **Real Estate**,
and **Creative Services**. Homemade covers food, handmade products and crafts;
Real Estate covers sale properties; Creative Services covers creative work,
and editing for travellers and creators.

The controlled-beta implementation adds locality discovery, real per-seller orders,
buyer completion/disputes, notifications and a transactional email outbox, sale-only
property enquiries/visits, Creative Services quotes/engagements, and admin operations.
Exact delivery eligibility is checked at checkout; public discovery omits precise
seller distances. Admission is restricted to approved accounts in production.
No payments, escrow, legal ownership verification or private proof uploads are offered.
Public sample products remain illustrative and cannot be ordered.

Read the [beta runbook](docs/BETA_RUNBOOK.md) and
[implementation report](docs/BETA_IMPLEMENTATION_REPORT.md) before release.
Historical phase reports below describe earlier revisions, not current readiness.

[Phase 7 location guide](docs/PHASE7_LOCATION.md) | [Phase 7 report](docs/PHASE7_REPORT.md)

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

The frontend configuration is public `VITE_API_BASE_URL`, defaulting to same-origin
`/api/v1` through the Vite development proxy to `127.0.0.1:8000`. Preserve existing environment files. Configure the
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

Access tokens remain only in browser memory and last 15 minutes. An HttpOnly,
Secure refresh cookie restores eligible sessions after reload: up to eight hours
for buyers/sellers and 15 minutes for admins, without sliding extension. Logout
revokes the server session and clears local identity. See the
[refresh-session handoff](docs/REFRESH_SESSION_IMPLEMENTATION.md) for migration,
verification and browser requirements. Migration 0010 requires separate approval.

Default CORS permits only localhost/127.0.0.1 on port 5173. Other development or
production origins require an explicit `WHAT_NOT_CORS_ORIGINS` JSON list. Production
requires HTTPS and a same-site API (prefer same-origin `/api/v1`); no wildcard CORS
is used. Reliable concurrent-tab renewal requires browser Web Locks support.

## Current workflows

- Real registration, login, `/auth/me`, logout and role-protected routes.
- Complete own seller profile creation/update, own products, create/edit, activation,
  rejection reasons and resubmission. Sellers can upload up to five JPG/PNG/WebP
  product images, replace/remove them and choose a primary image. Existing hosted
  URLs and legacy API inputs remain supported. See [private image storage](docs/PRODUCT_IMAGE_UPLOAD.md).
- Real ADMIN pending queue, approval and rejection with required reason. Fake counts,
  earnings and commission controls are removed.
- Own addresses, partial edits and default selection; historical delivery fields
  remain protected by backend services.
- BUYER/SELLER owned order history/details and eligible cancellation/progression.
- Warm Orange design tokens, loading/error/empty states and responsive forms.
- Existing WhatsApp help destination remains available.

Buyer discovery/detail now use POST /discovery/products with an explicitly chosen
location. Eligible products require approval, activity, stock and the seller's radius.
The public examples and /buyer/samples catalogue/cart remain illustrative. Legacy
GET products/detail and POST orders remain 501; checkout is disabled. Seller,
moderation and order lists retain the first-100 backend limit; discovery applies
eligibility before pagination. See the location guide for current limitations.

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
migrations to either database. Revision 0002 adds nullable dispatch confirmation;
existing coordinate and radius fields are reused.

The location guide documents scripts/phase7_smoke.py, which uses installed Chrome
and Node 24's native WebSocket with no new dependency. It creates isolated PostgreSQL,
owned localhost servers and a temporary browser profile, then checks real location
workflows and responsive widths. Existing Phase 6 screenshots remain historical.

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

Manual coordinates are a Phase 7 technical fallback. A friendlier PIN/address search
or map picker is a future enhancement; no geocoding provider or map infrastructure
is included. Real purchasing requires a future checkout design and remains disabled.
