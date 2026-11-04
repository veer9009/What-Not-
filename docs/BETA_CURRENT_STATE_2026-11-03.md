# What Not? current-state audit — 3 November 2026

**Classification: NOT READY FOR BETA.**

This is the initial audit requested before implementation. The implementation request
is still open. Passing tests establish the existing contract; they do not establish
that all requested business workflows exist. No product code, migrations, credentials,
application database, AWS resources, commits or remote branches were changed.

## Short current-state report

1. **Working:** registration/login, database-backed roles and ownership, seller shops,
   product submission/moderation/resubmission, saved addresses, confirmed dispatch
   points, exact-radius discovery, real single-seller checkout, order history,
   inventory transactions, buyer-scoped idempotency and eligible cancellation.
2. **Partial:** Homemade delivery ends with buyer-confirmed `DELIVERED`; there is no
   grace-period completion or persisted dispute. Admin supports pending products only.
3. **Missing:** notification persistence/APIs/UI, email provider/outbox/worker,
   transition audit records, Real Estate persistence/workflows, Creative Services
   persistence/workflows, admin reports/disputes/account-action tools and verification.
4. **Security concerns:** discovery permits precise dispatch-location inference;
   login/registration/discovery have no application rate limits or beta admission gate.
   No new direct IDOR or role-escalation defect was identified in inspected routes.
5. **Integrity/concurrency:** existing order locking/idempotency is substantial and
   tested. Multi-seller checkout is separate atomic orders with possible partial
   success. There is no database-enforced nonempty-order/total invariant; services
   enforce these. No durable business event history exists.
6. **UX/business gaps:** seller order responses omit delivery address/contact;
   buyer price-change consent is absent; landing/admin copy and README are stale;
   property previews still advertise rentals despite the new sale-only requirement.
7. **Coverage gaps:** no tests for absent notifications, workers, new delivery states,
   either new vertical, admin case management, spatial inference, or abuse controls.
   Existing frontend tests predominantly mock HTTP; no fresh browser UAT was run.
8. **Beta blockers:** location privacy, fulfillment address access, delivery timeout/
   disputes, notifications/email, admin operational controls and both missing verticals.

## Verified baseline

Workspace started clean at `861c2cb` (`Add buyer delivery confirmation and support`).
No repository `AGENTS.md` was found outside ignored dependencies/virtualenv/git data.

| Check | Observed result |
| --- | --- |
| Backend `python -m pytest -q -W error` | **552 passed**, 129.79 seconds, no skips/failures |
| Frontend `vitest run --pool=vmThreads --maxWorkers=1` | **202 passed**, 21 files, 98.71 seconds |
| `npm.cmd run build` | Passed; TypeScript build and Vite production bundle |
| `python -m compileall -q app alembic tests` | Passed |
| `python -m pip check` | No broken requirements |
| `python -m alembic heads` | Single head `0004` |
| Migration execution | Existing isolated tests cover upgrade, metadata check, downgrade, re-upgrade, legacy data and refused lossy downgrade |
| `git diff --check` before report edits | Passed |
| Dedicated lint command | None configured in package scripts; no backend lint/type configuration found |

Backend commands ran in `backend` with its existing `.venv` and PostgreSQL 17 tools
on PATH. The first sandbox run produced 240 passes and 312 setup errors because
`pg_ctl` could not create a Windows restricted token (error 87). The same unmodified
suite passed using approved execution outside that restriction. Its harness creates
a generated localhost cluster, ignores application `DATABASE_URL`, validates the
owned data directory, and shuts it down. No application database was queried or migrated.

Ignored evidence logs: `audit-backend-baseline.log`, `audit-backend-verified.log`,
`audit-frontend-baseline.log`, `audit-build.log`. npm emitted a notice rendered by
PowerShell as NativeCommandError text; the build process exited zero and produced
the bundle. The initial backend wrapper did not propagate pytest's exit code; its
failure is explicitly recorded above. The verified rerun propagated the exit code.

## Architecture and contracts inspected

- React/Vite/TypeScript, React Router, memory-held authentication; shared API client
  preserves BIGINT identities as decimal strings. Recovery requests use per-buyer
  session storage; tokens and precise address coordinates are not stored there.
- FastAPI routers call services/repositories. Pydantic rejects extra write fields.
  SQLAlchemy request transactions commit before the response; nested savepoints
  protect service writes. PostgreSQL/psycopg and Alembic are established dependencies.
- Seven domain tables: users, seller profiles, products, product images, addresses,
  orders and order items. No property/service/notification/event/outbox table exists.
- `POST /orders` is live and requires UUID4 `Idempotency-Key`. Legacy `GET /products`
  and `GET /products/{id}` still intentionally return 501; discovery uses authenticated
  POST endpoints with owned addresses or transient coordinates.
- `/admin/products/pending` and approve/reject require actual active database ADMIN.
  ADMIN cannot currently read orders through the buyer/seller order endpoints.
- Audited models, schemas, repositories and services; all route modules; settings,
  JWT/password helpers, transaction/error boundaries; all four migrations; frontend
  auth/discovery/cart/recovery/order/admin/seller flows and related test coverage.
  Existing reports were treated as historical evidence, not current implementation.

## Findings and evidence

### B01 — High: dispatch location can be inferred

`backend/app/services/discovery.py::_eligible_view` returns distance rounded to two
decimal kilometres. The discovery schemas accept arbitrary buyer-supplied coordinates.
Public registration enables a buyer to obtain access without verification. Three
synthetic observations generated using the actual geography helper and response
rounding reconstructed a synthetic dispatch point within **2.68 metres**, with all
observations within the one-kilometre eligibility radius. No real seller was queried.
See `scripts/audit_location_inference.py` for the reproducible offline diagnostic.

Even removing distance is insufficient: exact-radius inclusion/exclusion remains a
location oracle under repeated queries. Coarser output alone does not solve this.
Changing to coarse locality discovery affects the existing exact-radius contract;
that privacy/product decision must be explicit. Checkout eligibility also needs
verified beta identities and bounded address/query changes. This diagnostic uses
the same primitive and rounding, not an end-to-end HTTP exploit test.

### B02 — Blocker: sellers cannot fulfill orders from current API data

`schemas/order.py::OrderResponse` and `services/mappers.py::order_response` expose
items/totals/identities/status but no delivery address, recipient or contact data.
The seller UI likewise has none. Seller calls to the buyer address resource are
correctly denied. A dedicated order-scoped fulfillment view is needed, with minimal
fields, ownership checks and an explicit policy for when access begins/ends. Do not
solve this by granting sellers general access to buyer addresses.

### B03 — Blocker: delivery contract differs from the requested lifecycle

Actual lifecycle:

`PLACED → ACCEPTED → PREPARING → OUT_FOR_DELIVERY → AWAITING_BUYER_CONFIRMATION → DELIVERED`

Only the owning buyer can perform the final transition. There is no `COMPLETED` or
`DELIVERY_DISPUTED`, delivery timestamp/deadline, event history or auto-completion
runner. The delivery-problem UI opens WhatsApp without writing a dispute. A buyer
can disappear indefinitely. Historical `DELIVERED` includes earlier seller-finalized
orders, so it must not be relabeled as proven buyer consent. Migration 0004 preserves
these rows and refuses downgrade while awaiting-confirmation orders exist.

### B04 — Blocker: notification/email reliability infrastructure is absent

No recipient-owned notification store/API/UI, outbox, mail provider configuration,
retry/lease/dead-letter support or worker exists. New orders are visible only by
opening order history. Build notification/outbox events in the order transaction;
external delivery must occur after commit. A DB outbox alone cannot promise exactly
once external email: a successful send followed by a crash requires provider-side
idempotency or a documented bounded duplicate risk. No credentials were invented.

### B05 — Blocker: Real Estate has presentation only

No owner/agent profile, sale listing, moderation, enquiry, visit negotiation,
reconfirmation/expiry, sold handling, save/report, verification or private-document
storage exists. `ExploreVerticals.tsx` correctly disables the action, but still uses
rent/sale examples. The new sale-only requirement supersedes historical preview copy.
Privacy/contact reveal and proof handling require an explicit policy before exposure.

### B06 — Blocker: Creative Services has presentation only

No provider profile, portfolio, service/pricing model, remote/service-area matching,
enquiry/RFQ, response, engagement, delivery/completion or verified review relationship
exists. Existing product categories cover crafts, not these services or food-specific
workflows. Do not force property/service records into product/inventory/order tables.

User decisions received during this audit:

- Preserve BUYER/SELLER/ADMIN; use separate vertical profiles for owners/agents/providers.
- Creative beta flow: enquiry → provider response → buyer accepts → provider marks
  work delivered → buyer confirms completion; reviews only after buyer confirmation;
  no payment or escrow.

### B07 — Blocker: admin operations and auditability are incomplete

Only pending-product moderation is available. No order/dispute visibility, report
queue, suspension/reactivation endpoint/UI, approved-listing takedown, seller/provider/
property moderation or actor/reason audit trail. Internal `UserService.set_active`
exists but is not an authorized admin workflow. Suspension stops the actor logging
in; it also strands their active orders without an admin recovery process.

### B08 — High: abuse and account-verification controls are absent

No application login/registration throttling, controlled-beta allowlist/invite gate,
phone/email verification challenge, recovery flow or durable abuse quota was found.
Phone values are length-validated text, not verified ownership. No proxy/WAF policy
was inspected, so external protection must not be assumed. Argon2 password checks
also need admission/rate controls before public exposure. A verification badge must
not be inferred from having a phone field or a confirmed dispatch point.

### B09 — Medium: checkout can silently use a changed price

Server prices are authoritative and snapshotted, which is correct. The frontend
preflight checks seller and stock but does not compare current price with the basket
or obtain buyer consent to a changed total. The order request carries no expected
price/quote revision. Moderation normally hides an edited approved product, but a
later reapproval still permits the stale basket to order at a new price. Add a
server-validated quote/expected-price contract, included in the idempotency fingerprint.

### B10 — Medium: misleading copy and bounded lists

README and API description still say checkout is unavailable. Landing-page and
admin text say discovery awaits geography. Nearby discovery/checkout are live.
Lists return the first 100 rows ordered oldest-first and expose no route pagination
for orders/pending products. With enough historical orders, new orders are invisible
in history. Frontend estimated money uses JavaScript Number; backend Decimal remains
authoritative. Correct copy and add bounded pagination before relying on these tools.

### B11 — Medium: incident diagnostics and readiness checks are inadequate

SQLAlchemy/validation failures are sanitized correctly, but application exception
handlers do not emit structured operational events. There is no order-transition
history or moderation audit. Health checks only the process, not storage/schema or
worker backlog. Add safe event/error codes and resource references; never log
exception payloads, credentials, JWTs, exact locations or verification documents.

### B12 — Integrity limits to preserve and harden deliberately

- Product locks are acquired in ID order. Stock and order/items share one explicit
  transaction; stock has a nonnegative CHECK. Buyer idempotency uses a transaction
  advisory lock, unique constraint and payload fingerprint. Existing replay returns
  the purchase snapshot even if product/location availability later changes.
- Cancellation before preparation and rejection restore stock under locks once.
  Direct buyer cancellation after PREPARING is denied. No post-preparation seller
  approval/cancellation-request workflow exists; report this as missing, not supported.
- Composite foreign keys enforce one seller per order/item; referenced products and
  addresses cannot be silently deleted. Ordered address delivery fields are immutable.
- Nonempty orders, matching item totals and address ownership are service/response
  guarantees, not complete database constraints against arbitrary internal SQL.
  Existing migration fixtures intentionally construct empty historical orders.
- Email uniqueness is case-sensitive at DB level; normal public registration lowercases
  email. Legacy mixed-case internal records can still collide; login fails closed on
  multiple normalized matches. A future normalized unique index needs data preflight.
- No per-stage timestamps. `updated_at` alone cannot reconstruct a delivery deadline.

## Security review matrix

| Area | Current evidence / limit |
| --- | --- |
| Authentication/JWT | Argon2id, legacy bcrypt upgrade; fixed HS256; required subject/issued/expiry claims; expired/bad signatures/algorithms rejected in tests |
| Roles/escalation | Database role is authoritative; public ADMIN registration rejected; forged token role cannot grant admin |
| IDOR/ownership | Existing order/product/address/seller routes check ownership; direct unauthorized-call tests exist |
| Mass assignment/enums | Extra fields forbidden; write DTOs omit actor/verification/status authority; invalid state tests exist |
| SQL injection | Inspected repositories bind values through SQLAlchemy; advisory-lock SQL uses parameters; no user-built SQL found; no external penetration test performed |
| XSS | No dangerous HTML/eval sink found in inspected source; React renders text; external image URLs use HTTP(S) schemas; no full browser payload/security-header test performed |
| Private data/errors | Explicit response mappers omit hashes/secrets; safe validation/storage errors tested; distance inference remains a high-risk exception |
| Notifications/property/service access | Absent functionality; cannot claim isolation/security tests for nonexistent routes |
| Secret handling | Settings use SecretStr; example files have placeholders; real .env contents were not printed/read; no secret-history scanner was run |
| Deployment perimeter | HTTPS/CSP/HSTS, reverse proxy limits, AWS access, secret-store integration and backup restore not verified; no infrastructure was changed |

## Adversarial case disposition

| Case | Existing protection or explicit gap |
| --- | --- |
| Final unit bought twice | Row locks + stock CHECK + independent transaction race test |
| Double click / retry / lost response | Required idempotency key, DB uniqueness/advisory lock; UI pending ref; per-tab durable replay; new keys intentionally represent new purchases |
| Multi-seller basket | Separate seller orders; partial results explicit; no basket-wide atomicity promised |
| Halfway DB failure | Transaction/savepoint rollback tests; order/items/stock remain atomic |
| Duplicate cancellation / cancel vs progression | Locked order and transition graph; stock restored once; no post-preparation cancellation request |
| Buyer disappears | No timeout; blocker B03 |
| Seller disappears / suspended with orders | No admin recovery; blocker B07 |
| Wrong state / guessed IDs | Backend transition, role and ownership checks tested |
| Product deleted/inactive/out of stock | FK RESTRICT for referenced product; locked placement revalidates active/approved/stock |
| Cart price changes | Server snapshot valid; informed-price acceptance missing, B09 |
| Buyer disputes delivery | WhatsApp only; no durable dispute, B03 |
| Repeated worker / restart / email timeout | No worker/outbox exists; B04 |
| Expired/sold property enquiry or visit | No domain implementation; B05; new service must recheck under locks |
| Private location probing | Reproduced synthetic inference; B01 |
| Login/session change during checkout | Existing client generation/session guards and recovery tests; no globally unique purchase intent across independent new browser tabs |

## Proposed sequence and decision boundary

See the companion proposed design. Extend the existing monolith and PostgreSQL;
avoid a broker/new distributed runtime for a 10–15-person beta. Preserve existing
order/idempotency/stock safeguards, add domain tests before changing contracts, and
coordinate frontend/API/migration changes. A fresh independent review should follow
implementation, then all existing suites/build/migrations and real browser UAT.

**Decision still needed:** private-location discovery policy. Exact-radius discovery
and strict location secrecy conflict under arbitrary repeated location queries.
Changing this is a material contract decision; the user's instruction explicitly
requires stopping and explaining such architectural/privacy decisions rather than
silently choosing. Contact reveal and private-document access policy also need to
be settled in the design before adding those endpoints.

## Change/deployment/rollback accounting for this audit

- Files added: this report, the proposed design in `docs/superpowers/specs`, and the
  synthetic offline location diagnostic in `scripts`.
- Migrations added: **0**. Product features/bug fixes/security fixes implemented: **0**.
  Tests added/modified: **0**; one offline diagnostic added. Findings above are open.
- Existing dependencies and environment examples unchanged. Current runtime requires
  `DATABASE_URL`, `WHAT_NOT_JWT_SECRET_KEY`, correct `WHAT_NOT_CORS_ORIGINS` and
  public `VITE_API_BASE_URL`; environment/algorithm/token lifetime use current settings.
  Future mail/worker/grace-period variables in the design are proposals, not supported
  settings yet.
- No deployment, migration against application data, EC2/port/security-group changes,
  commits or pushes. No user/secret files were edited. No production readiness claim.
- Audit rollback consists only of removing the added documentation/diagnostic files;
  ignored build outputs/logs were generated by verification. No data rollback needed.
- Current 0004 rollback limitation remains: downgrade refuses while awaiting buyer
  confirmations. Do not use downgrade-to-base as a data recovery mechanism.

**NOT READY FOR BETA** — implementation and verification against the requested
three-vertical business workflows remain outstanding.
