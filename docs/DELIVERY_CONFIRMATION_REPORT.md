# Buyer delivery confirmation and Help & Support

Implemented incrementally on checkpoint `552b63d`. Work is uncommitted.

## Architecture and behavior

The existing `PATCH /api/v1/orders/{order_id}/status` endpoint, `OrderService`,
ownership checks, transaction wrapper and locked repository reads remain the single
order transition path. No separate order store, receipt endpoint, dispute service,
or optimistic status mutation was introduced. Placement, geography, price calculation,
idempotency, checkout recovery, and stock restoration code paths are unchanged.

Successful lifecycle before:

`PLACED → ACCEPTED → PREPARING → OUT_FOR_DELIVERY → DELIVERED` (seller progression).

Successful lifecycle after:

`PLACED → ACCEPTED → PREPARING → OUT_FOR_DELIVERY → AWAITING_BUYER_CONFIRMATION → DELIVERED`.

The seller performs progression through handover. Only the owning buyer performs
the last transition. Existing cancellation and rejection transitions are preserved.

Buyer details show six understandable tracking stages and one accessible current
stage. No stage timestamps are fabricated. Cancelled/rejected orders show an ended
state instead of a successful-delivery tracker. Historical delivered orders remain
readable without being rewritten or requiring new confirmation.

Seller details offer **Mark as handed over**. Buyer details offer **Yes, I received
it** only while awaiting confirmation. The confirmation uses the existing API client.
A synchronous ref blocks duplicate calls even before React renders disabled buttons;
the pending state spans the request and backend reload. A successful write followed
by failed reload reports that distinction and offers the existing retry path.
Errors use the existing sanitized client messages.

Buyer navigation includes **Help & Support** at `/buyer/help`. The page explains
order/delivery, seller/order, account, product/listing, and general marketplace help.
General support, order support, and the existing floating WhatsApp action share
one encoded URL builder for **+91 80800 98882** (`https://wa.me/918080098882`).
The order-specific message includes only the validated public order reference,
preserving full BIGINT precision. Tokens, coordinates, account details and seller
IDs are not passed to WhatsApp. **I haven't received it / Delivery problem** opens
order-specific support and makes no status request. It does not record a dispute.

## Authorization and API contract

- Existing authentication checks the active database identity and role.
- Existing order routes accept BUYER/SELLER; ADMIN is denied (403).
- Service ownership checks still require the actual order buyer or seller owner.
- Only a BUYER whose ID matches `order.buyer_id` may request final delivery.
- That buyer can set DELIVERED only from AWAITING_BUYER_CONFIRMATION.
- Sellers cannot request DELIVERED from any status (403), including after handover.
- Other buyers/sellers cannot read or transition another owner's order (403).
- Unauthorized requests receive 401; wrong role/ownership receives 403; permitted
  actors requesting invalid or repeated transitions receive 409; malformed requests
  retain validation behavior (422); successful status updates return 200/OrderResponse.
- User and order row locks serialize competing writes. Only one concurrent handover
  or receipt confirmation succeeds. Delivery updates never restore stock.
- Buyer cancellation remains limited to PLACED/ACCEPTED. Seller cancellation and
  rejection rules and atomic, once-only stock restoration are unchanged.

## Migration

New revision `0004`, parent `0003`, widens `orders.status` from VARCHAR(20) to
VARCHAR(32) and replaces `ck_orders_status` to include AWAITING_BUYER_CONFIRMATION.
The schema enum and model constraint agree. Previous migrations are unchanged.
Upgrade does not update any order rows or historical delivery status.

Downgrade takes an ACCESS EXCLUSIVE table lock, checks for awaiting-confirmation
orders, and refuses with a clear error if any exist. No statuses are rewritten to
make downgrade possible. Resolve those orders through the current application
before retrying downgrade. Without pending confirmations it restores the old check
constraint and VARCHAR(20), preserving all orders. PostgreSQL transactional DDL
keeps a refused downgrade at revision 0004 with data/schema unchanged.

Tests exercise legacy-data upgrade, accepted/rejected status constraints, refused
downgrade and unchanged revision/data, successful downgrade after resolution,
re-upgrade, and Alembic metadata checks in disposable databases. No application
database was migrated by this implementation session. Migration deployment must
precede the backend/frontend rollout; it requires a schema lock.

## Tests added or updated

- New backend service/API tests cover seller handover, seller finalization denial,
  owning buyer success, every invalid starting status, unrelated BUYER/SELLER/ADMIN,
  unauthenticated requests, duplicate handover/receipt, HTTP status contracts,
  legacy delivered reads/listing, stock preservation and forbidden post-handover
  cancellation/rejection. Two real concurrent-transaction tests verify once-only
  handover and receipt confirmation.
- New migration integration test covers the upgrade/downgrade behavior above.
- Existing schema/OpenAPI and PostgreSQL constraint tests include the new status.
  Existing lifecycle tests require buyer finalization; invalid seller delivery
  asserts the new authorization error while retaining status/stock assertions.
- New frontend integration tests cover all six current stages, cancellation and
  rejection, conditional confirmation, real PATCH and subsequent GET, seller
  handover, delivery-problem links without mutation, exact encoded URLs and BIGINT
  order references, navigation, buyer-only help access, pending duplicate guards
  for both roles, safe errors, failed refresh, and reconciliation from backend truth.
- Existing frontend order tests retain their assertions using customer-facing
  labels and the revised seller handover action.

## Verification

Backend: from `backend`, `.venv/Scripts/python.exe -m pytest -q` —
**552 passed, no failures or skips**. This includes 29 cases in the two new
delivery/migration files and the expanded existing schema/constraint coverage.

Frontend: `npm.cmd test -- --run` — **202 passed across 21 files**, including
26 cases in the new delivery/support integration file. No failures or skips.

Production build: `npm.cmd run build` (`tsc -b && vite build`) — **passed**.

Alembic source graph: `backend/.venv/Scripts/python.exe -m alembic -c backend/alembic.ini heads`
— **0004 (head)**, a single head. Database revision and metadata are checked by
the isolated migration tests, without reading or migrating the application database.

`git diff --check` — **passed**, with only Git's existing LF/CRLF conversion
notices. `git status --short` was inspected: **18 modified and 8 new files**, exactly
the list below. Previous migrations, .env files and credential files are absent
from the diff. HEAD remains at `552b63d`; nothing was committed or pushed.

The initial backend attempt could not launch PostgreSQL under the sandbox's Windows
token; the existing disposable-cluster harness ran with the required execution
permission. The initial full backend run exposed one old assertion expecting an
invalid-transition error instead of the newly required seller authorization denial;
that assertion was updated without reducing coverage. The frontend runner emits
an informational jsdom performance suggestion; it is not a failed test.

A read-only code review found no actionable issues in authorization, migrations,
tracking, support URLs, pending handling or coverage. This does not replace manual
security and end-to-end review.

## Exact changed/new files

Modified:

- `backend/CONTRACTS.md`
- `backend/SERVICES.md`
- `backend/app/api/routes/orders.py`
- `backend/app/models/order.py`
- `backend/app/schemas/order.py`
- `backend/app/services/orders.py`
- `backend/tests/persistence/test_constraints.py`
- `backend/tests/persistence/test_services_marketplace.py`
- `backend/tests/persistence/test_services_orders.py`
- `backend/tests/test_api_contracts.py`
- `backend/tests/test_order_schemas.py`
- `docs/FRONTEND_INTEGRATION.md`
- `src/App.tsx`
- `src/Marketplace.test.tsx`
- `src/api/types.ts`
- `src/components/Shared.tsx`
- `src/pages/OrderPages.tsx`
- `src/styles/index.css`

New:

- `backend/alembic/versions/0004_buyer_delivery_confirmation.py`
- `backend/tests/persistence/test_delivery_confirmation.py`
- `backend/tests/persistence/test_delivery_confirmation_migration.py`
- `docs/DELIVERY_CONFIRMATION_REPORT.md`
- `src/DeliverySupport.test.tsx`
- `src/components/OrderTracking.tsx`
- `src/pages/HelpPage.tsx`
- `src/utils/support.ts`

Ignored local verification logs: `delivery-backend-focused.log`,
`delivery-backend-full.log`, `delivery-frontend-focused.log`,
`delivery-frontend-full.log`, `delivery-build.log`. The build also refreshes existing
ignored dist and TypeScript build artifacts. No dependencies, secrets, .env files,
credentials, previous migrations, commits or remote branches were changed.

## Remaining limitations

- No automated disputes, tickets, refunds, timeout completion, or buyer reminders.
  An order stays awaiting confirmation until its buyer confirms; delivery problems
  are handled through the external WhatsApp support path.
- Existing order responses provide no per-stage timestamps; the tracker communicates
  current lifecycle position only and does not create a historical event log.
- Historical DELIVERED orders retain their existing meaning; this change cannot
  establish retrospective buyer consent.
- No live WhatsApp message was sent or support-account availability verified.
- Browser/mobile visual review, live-account E2E and the user's security review
  remain manual. No application database migration or deployment was performed.

## Manual E2E checklist

1. On a review database with historical delivered orders, apply migration 0004 and
   confirm historical statuses, totals and items are unchanged and readable.
2. Sign in as a buyer, choose an owned eligible address, discover an available
   product, add it to cart, and place an order. Confirm authoritative totals,
   once-only stock decrement, one order per seller and checkout recovery/replay.
3. As its owning seller, accept, prepare and dispatch. Check buyer tracking after
   each step. Choose Mark as handed over; verify both accounts show awaiting buyer
   confirmation and seller controls cannot finalize delivery.
4. Attempt direct seller PATCH to DELIVERED from OUT_FOR_DELIVERY and from awaiting
   confirmation. Expect 403 with no status or stock change. Repeat with unrelated
   buyer, unrelated seller and admin credentials; expect denial. Missing/expired
   credentials must be rejected.
5. As the owning buyer, choose the delivery-problem action. Inspect WhatsApp's
   recipient/message: +91 80800 98882 and only the public order reference. Close
   WhatsApp and reload; the order must still await confirmation.
6. Choose Yes, I received it. Verify persisted DELIVERED through a fresh GET,
   seller details, buyer history and a browser reload. Repeat the API request;
   expect 409. Confirm stock stays unchanged by handover/receipt.
7. Throttle requests and double-click seller/buyer transitions; verify one pending
   request, disabled controls, and eventual backend reconciliation. Simulate a
   conflict, network failure and successful write followed by failed GET; verify
   safe messages and working refresh without a fabricated final state.
8. Cancel eligible orders as buyer/seller and reject as seller. Verify restoration
   happens once; repeated invalid requests cannot restore inventory twice. Buyer
   tracking must show ended delivery for cancelled/rejected orders.
9. Open Help & Support from buyer navigation, including on a narrow phone screen.
   Inspect the general WhatsApp message and all order-specific support URLs for
   correct encoding and absence of tokens, coordinates or personal details.
10. Review keyboard focus, tracker current-step semantics, wrapped long order IDs,
    confirmation actions and support navigation on mobile/tablet/desktop.
11. On a disposable review database, try downgrade with a pending confirmation:
    it must refuse and retain 0004/data. Complete the buyer confirmation, retry
    downgrade and re-upgrade; verify all historical orders remain unchanged.
