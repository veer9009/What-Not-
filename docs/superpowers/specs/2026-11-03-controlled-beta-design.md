# What Not? controlled-beta hardening — proposed design

Status: approved by the user on 3 November 2026, including the proposed privacy,
address access, visit disposition and investigated admin resolution policies.
Implementation is in progress. Audit evidence is in
`docs/BETA_CURRENT_STATE_2026-11-03.md`. Do not deploy, commit or push during this work.

## Intent and scope

Support 10–15 real beta testers across Homemade, sale-only Real Estate and Creative
Services. Preserve the FastAPI/SQLAlchemy/PostgreSQL/React architecture, authoritative
backend authorization, order snapshots, inventory locking and idempotency. No payment,
escrow, property legal verification or new broker infrastructure. Missing workflows
must remain explicitly unavailable until their backend and frontend pass verification.

## Approaches and decisions

1. **Extend the existing monolith and PostgreSQL (recommended).** Separate domain
   tables/services, common notifications/outbox/audit, bounded worker commands run by
   an operator or scheduler. Smallest operational change; worker scheduling needs an
   explicit beta runbook and monitoring.
2. Introduce a message broker and distributed workers now. Adds deployment/failure
   modes without resolving missing business rules; unnecessary for the beta volume.
3. Implement only UI/support workarounds. Cannot satisfy durable disputes, email
   retry, transaction safety or functional verticals; unsuitable.

The user selected existing BUYER/SELLER/ADMIN roles plus separate vertical profiles,
rather than a multi-role authorization migration. The user also approved the Creative
completion flow described below. Other implementation choices here are proposals.

## Privacy decision — must resolve before implementation

Arbitrary-source, exact-radius discovery leaks a home seller's location through
numeric distances and the eligibility boundary. Removing numeric distance alone
is not sufficient. Recommended direction: discover by a stable coarse seller-locality
cell, do not return exact point-based distance, and state that delivery is confirmed
at checkout. Preserve exact eligibility only inside order placement, restrict beta
admission to approved identities, and bound address changes/eligibility attempts
through PostgreSQL-backed quotas. This changes the current exact discovery contract.

Alternative: keep private-home listings unavailable until the privacy policy and
controls are settled. Neither direction may be silently selected. Coarse discovery
plus quotas mitigates inference; it does not mathematically eliminate every inference
from exact checkout decisions. Private property location must likewise stay separate
from public locality views.

Proposed contact policy for review: precise property address only to the requesting
buyer after a confirmed visit, the owner/agent, and authorized investigating admin;
contact sharing opt-in by creator and restricted to legitimate owned enquiry/visit.
Verification proofs must use a separate private store with authorized retrieval,
size/type limits, retention rules and no public URLs. If private storage is unavailable,
do not implement uploads with ordinary product image URLs or advertise proof checking.
Proposed beta boundary: omit document upload/retrieval until private storage and
retention are approved; admin can flag proof as required and withhold approval, but
the application must not claim that account/phone verification proves ownership.

Proposed Homemade fulfillment policy: minimal recipient/address/contact view only
for the owning seller after acceptance and while fulfillment needs it; no arbitrary
buyer address lookup. Existing immutable ordered address reference remains valid.
Confirm the access/retention policy before adding this private-data endpoint.
Proposed access window: owning seller sees delivery fields from ACCEPTED through
active fulfillment/dispute handling; seller access ends on terminal completion or
cancellation. Buyer retains their own record. Admin sensitive reads require a
case/order reason and an audit event. For properties, CONFIRMED means an accepted
appointment, not evidence that a visit actually occurred. Address access is revoked
on cancellation, sale or takedown, and after the scheduled appointment ends; a new
appointment requires renewed confirmation. No endpoint returns precise coordinates
where a postal address suffices. These are proposed policies, not current behavior.

## Homemade lifecycle and migration

New successful lifecycle: PLACED → ACCEPTED → PREPARING → OUT_FOR_DELIVERY → DELIVERED
→ COMPLETED. Owning seller marks DELIVERED; owning buyer confirms COMPLETED or
reports DELIVERY_DISPUTED. Buyer cancellation stays PLACED/ACCEPTED only; seller
rejection/cancellation follows existing rules. No direct state jump or cancellation
after preparation. A later cancellation-request mechanism needs its own explicit
approval/resolution state rather than silently cancelling prepared orders.

Add delivered marker/deadline/completion metadata and append-only transition events
with previous/next status, actor or system identity, reason code and timestamp.
Grace duration is one validated setting, initially 24 hours. Deadline is persisted
when seller marks delivered; changing configuration must not move existing deadlines.
Disputes cancel eligibility for automatic completion. Admin resolution is audited.

Auto-completion uses a bounded PostgreSQL selection of due DELIVERED orders with
row locks/SKIP LOCKED. Recheck status/deadline under lock; status, event and notification
commit together. Concurrent buyer confirmation/dispute and repeated/restarted worker
runs must yield one winning transition. No in-memory timer.

Migration must preserve the difference between historical delivery and buyer consent.
Proposed mapping: historical terminal DELIVERED → COMPLETED with completion source
LEGACY and a migration audit record, leaving unknown actual completion time null;
AWAITING_BUYER_CONFIRMATION → DELIVERED with a newly recorded grace deadline and
migration source (not a fabricated historical delivery timestamp). Other states,
items, totals and stock unchanged. Document a coordinated API/frontend rollout and
refuse downgrade if new states/events cannot be represented without data loss.
Do not edit existing migrations. Test populated upgrade and refused rollback.

Creation remains atomic per seller. Add expected price/quote validation before
inventory decrement and include it in the request fingerprint. Replays must return
the original committed snapshot before current availability/price checks. Never
couple inventory/business commit to sending mail. Multi-seller UI must explain
independent orders/partial success and retain separate original replay keys.

## Reusable notifications, outbox and worker

Notification: recipient FK, type, entity type/ID, safe title/body, created/read times,
and unique event-recipient key. List/count/read-one/read-all always filter by current
recipient. Generic entity references require explicit type/permission handling; order
relationships should use real foreign keys where possible. No PII in links/messages.

Create seller in-app and email events atomically with each new order. Add buyer
delivery-confirmation reminders and relevant domain/status events. Common service
is reusable for enquiry, visit and service engagement events.

Outbox: stable event key, recipient, template/type, minimal payload, state, attempt
count, next-attempt time, lease expiry/token, last safe error code, sent timestamp
and provider message reference. Unique deduplication keys prevent duplicate event
creation. Claim a bounded batch with SKIP LOCKED and commit the lease; perform
network I/O outside the business transaction with timeouts; acknowledge/retry only
with the matching lease token. Expired leases recover after restart. Exponential
backoff and finite attempts lead to an observable failed/dead-letter state.

Provider interface accepts a stable idempotency key. Test with a fake provider;
without configured credentials events remain pending/observable, not falsely sent.
Provider choice stays configurable. Prefer a provider with supported idempotent sends.
SMTP cannot guarantee exactly once after send-success/ack-crash; stable Message-ID,
finite attempts and a documented duplicate window are required if chosen. Do not
claim that Message-ID alone deduplicates mail. Invalid recipients become bounded
permanent failures. Repeated worker runs cannot reset the attempt budget.

Use one-shot bounded CLI commands for outbox processing, delivery completion and
property expiry. Document operator execution and future scheduler integration;
do not install/start infrastructure or deploy scheduler configuration in this task.
Structured logging uses event IDs/error codes; no credentials, arbitrary exception
strings, documents or precise locations. Add backlog/oldest-event checks to runbook.

## Real Estate

Separate SELLER-owned property profile, with OWNER/AGENT clearly recorded. Sale only;
categories Residential, Commercial, Land/Plots. Property public locality/content and
private address/location are separate response contracts. Optional proof metadata
must never become public. Account/phone verification needs an actual challenge or
explicit trusted-beta operator verification; a checkbox is not phone verification.

PENDING → APPROVED/REJECTED; required rejection reason; creator edits/resubmits;
approved material edits return to review. SOLD is immediate and terminal for active
enquiries/visits; creator can reconfirm stale unsold listings without bypassing review.
Persist reconfirmation/expiry time, default ~30 days; public queries exclude expired
listings even before worker execution. Sold/expired/hidden checks occur under locks
when enquiries or visits are created/changed. Define rejection handling for already
scheduled visits rather than leaving contradictory confirmed records.
Proposed existing-request policy: SOLD/takedown cancels pending and confirmed visits
with a system reason and notifications, closes enquiries to new replies and revokes
private address access; participants retain non-sensitive conversation history.
Expiry blocks new enquiries/visits, preserves already confirmed appointments and
their time-limited access, and pauses unconfirmed requests until reconfirmation.
A material edit returning a listing to PENDING or rejection cancels unconfirmed
proposals and suspends confirmed appointments/address access until the listing is
approved and the appointment is explicitly reconfirmed. No visit restarts silently.

BUYER-owned enquiry, creator response, preferred visit datetime, creator acceptance/
rejection/counterproposal, buyer acceptance of proposal → CONFIRMED. Store aware UTC
times; display explicit local timezone. Prevent arbitrary users from reading messages,
proposals or precise locations. No property payments/token/legal document workflow.
Saved-property uniqueness per buyer/property; report reasons from the frozen list,
private reporter details, admin investigation/disposition and audited takedown.
Frozen report reasons: fake/misleading; wrong information; already sold; suspicious
owner/agent; inappropriate content; other (with bounded explanation).

## Creative Services

Separate SELLER-owned provider profile, moderated service listing, portfolio and safe
HTTP(S) external links. Pricing FIXED/STARTING/HOURLY/QUOTATION with validated amount/
currency requirements. Remote availability or configured service area; do not reuse
product stock/delivery radii as service booking semantics. Household-service scope
is not frozen; keep categories limited to the approved creative examples initially
unless the user supplies the additional requirements.

Approved flow: BUYER enquiry/RFQ → provider response → buyer acceptance → provider
marks delivered → buyer confirms COMPLETED. Persist actor/ownership/state/events.
One immutable agreed response/quote belongs to an engagement, preventing later listing
edits from changing accepted terms. No payment/escrow. Reviews require an actual
engagement completed by that buyer, at most one review per buyer/engagement; provider
cannot review itself or mark buyer confirmation. Repeated writes must not duplicate
engagements/reviews/notifications. Quotation changes must be explicitly accepted.

## Admin and cross-cutting controls

Backend ADMIN checks and active-actor checks at every sensitive boundary. Add
paginated queues for moderation/reports/disputes/orders and account suspension with
required reasons/audit events. Keep legitimate suspended-party orders accessible to
authorized admin resolution; do not automatically cancel all orders or restore all
stock. Recheck active seller/provider/account under transaction locks when accepting
new work. Define admin dispute resolutions as explicit permitted actions with reasons,
not arbitrary state assignment. No inferred refund or compensation system.
Proposed admin resolution rules: DELIVERY_DISPUTED may become COMPLETED after an
investigated delivery finding, or CANCELLED with a required investigation reason;
neither resolution automatically restocks dispatched goods. For suspension-stranded
PLACED/ACCEPTED orders, admin may cancel and restore reserved stock once. After
PREPARING, admin may cancel only through an explicit investigated case, without
automatic restock; continuing fulfillment requires reactivation and normal owning
seller actions. No arbitrary backward transition, refund or automatic resale of
returned/prepared goods. Admin actions must preserve the same row-lock/idempotent
event guarantees and record the inventory disposition explicitly. Require product
approval of these exceptional actions before implementing them.

Add safe structured domain/worker failures, database-backed abuse quotas and a
controlled-beta admission mechanism. Preserve sanitized public responses. Readiness
must distinguish process health, DB/schema availability and worker backlog.

## Configuration proposal

No new variable is supported yet. Proposed validated settings: delivery grace hours
(24), property reconfirmation days (30), worker batch/lease/attempt/backoff limits,
mail provider/from address/timeouts and private SecretStr credentials, beta admission
and DB-backed request/address quotas. Provider-specific variables follow the chosen
provider; examples contain placeholders only. Existing DATABASE_URL/JWT/CORS/public
API-base settings remain. Never expose worker/provider keys through VITE variables.

## Verification and implementation boundary

Implement incrementally after the design/privacy decisions, with failing tests for
each new contract and independent review of sensitive changes. Keep existing
assertions unless a deliberately replaced contract requires a documented update.
Prove true independent PostgreSQL transaction races for stock, duplicate placement,
cancel/prepare, dispute/timeout, outbox leases and sold/visit races.

Add direct FastAPI role/IDOR/mass-assignment tests for every new route, notification
isolation, restart/retry/send-failure tests, populated migration round trips and safe
rollback refusal. Frontend must cover workflow actions, pending/error/reload recovery,
privacy boundaries and all three verticals. Run full backend/frontend suites,
production build/types, migration metadata check, compile/dependency checks and diff
review. Browser UAT must exercise buyer/seller/admin across all required workflows.

## Independent builder check

The check identified privacy/discovery, private-data access, admin resolution and
sold/expired visit disposition as material decisions. Concrete proposed policies are
now written above for a single review; none has been silently treated as approved.
The requested frozen report-reason list is copied explicitly from the user's brief.

No beta-ready classification until this evidence exists. Report exact test counts,
new migrations/configuration, residual privacy/email limitations, unresolved product
rules and rollback constraints. Audit findings remain open until fixes are verified.
