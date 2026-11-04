# Controlled Beta Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task. Independent verticals may use superpowers:dispatching-parallel-agents with exclusive file ownership; integration and mutation of shared files remain sequential.

**Goal:** Implement the approved controlled-beta marketplace workflows locally.

**Architecture:** Extend the existing FastAPI/PostgreSQL services and React application. Reuse authentication, transactions and inventory locks. Add separate vertical domains and common persisted events/notifications; bounded worker commands replace in-memory timers.

**Tech Stack:** Existing Python/FastAPI/SQLAlchemy/Alembic/PostgreSQL and React/TypeScript/Vitest.

**Spec:** docs/superpowers/specs/2026-11-03-controlled-beta-design.md (approved).

## Global Constraints

- No deployment, commits, pushes, application-database migrations or credential edits.
- Preserve BUYER/SELLER/ADMIN roles, ownership checks, safe responses and existing functionality.
- Tests first for changed business contracts. Existing assertions change only for deliberately replaced approved contracts.
- Additive migrations 0005 shared/order foundation, 0006 property domain, 0007 creative domain, 0008 abuse/privacy support if needed; never modify 0001–0004.
- Provider failures never roll back business writes; no payments/escrow.
- Private proof uploads remain unavailable; clearly document beta limitation.

## Review Focus

- Crash after email provider success but before acknowledgment: bounded retries and explicit duplicate caveat, no exactly-once claim.
- Dispute versus auto-completion race: locked state/deadline recheck, one transition/event.
- Suspended seller with active fulfillment: authorized investigated admin cancellation, no post-preparation automatic restock.
- Sold listing during visit confirmation: same listing lock and private-address revocation.
- Lost checkout response after price/stock change: original idempotency replay returns snapshot before current checks.

### Task 1: Shared order, notification and worker foundation

**Files:** models/order.py, models/events.py, schemas/order.py, schemas/notifications.py, services/orders.py, services/notifications.py, services/mail.py, services/workers.py, api/routes/orders.py, api/routes/notifications.py, alembic/versions/0005_beta_foundation.py; corresponding persistence/security/migration tests.

**Interfaces:** `publish_event(session, recipient_id, event_key, kind, entity_type, entity_id, title, body)` persists in-app plus outbox without committing. `OrderService.transition` remains authoritative. New states DELIVERED/COMPLETED/DELIVERY_DISPUTED; grace deadline persisted. Worker processes bounded due orders/outbox, restart-safe leases.

- [ ] Write failing tests for new state/ownership/deadline/dispute rules, notification isolation and provider failure/retry.
- [ ] Run focused tests; verify expected missing-behavior failures.
- [ ] Implement models/migration/services/routes and fake/configured email provider interface, investigated admin resolution service and fulfillment view.
- [ ] Verify focused tests, independent races and populated migrations. Preserve replay/stock/cancellation guarantees.

### Task 2: Sale-only property domain

**Files:** models/property.py, schemas/property.py, services/properties.py, api/routes/properties.py, alembic/versions/0006_properties.py, src/api/properties.ts, src/pages/PropertyPages.tsx; corresponding tests.

**Interfaces:** user-owned SELLER property profiles; BUYER enquiry/save/visit/report; ADMIN moderation/report disposition. Shared event publisher from Task 1. Responses exclude private fields except explicit authorized confirmed-appointment endpoint. Route prefix `/properties`.

- [ ] Write/run failing tests for owner/agent sale listing, moderation/rejection/resubmit, expiry, save/report, enquiry and visit negotiation.
- [ ] Implement services with listing locks, approved sold/expiry rules, exact private-data permissions and reusable events.
- [ ] Implement working React forms/lists/detail/workflow actions using established API client.
- [ ] Verify domain permission/IDOR/state/race tests and frontend critical flows.

### Task 3: Creative Services domain

**Files:** models/creative.py, schemas/creative.py, services/creative.py, api/routes/creative.py, alembic/versions/0007_creative.py, src/api/creative.ts, src/pages/CreativePages.tsx; corresponding tests.

**Interfaces:** `/creative` routes; SELLER provider profiles/moderated listings/pricing/portfolios; BUYER RFQ and engagement; immutable accepted quote, buyer-confirmed completion and one legitimate review. Shared Task 1 publisher.

- [ ] Write/run failing tests for pricing, ownership, RFQ/provider response/acceptance/delivery/completion/review restrictions.
- [ ] Implement isolated tables/services/routes/migration and event integration; no payments or stock semantics.
- [ ] Implement frontend workflows and error/pending handling.
- [ ] Verify permission/state/retry/legitimate-review tests and frontend critical flows.

### Task 4: Privacy, admission, admin and shared frontend integration

**Files:** core/config.py, services/discovery.py, services/abuse.py, api/dependencies.py, api/routes/auth.py, api/routes/admin.py, main.py, models/__init__.py, migration 0008 if required; src/App.tsx, components/Shared.tsx, pages/OrderPages.tsx, components/OrderTracking.tsx, pages/AdminDashboard.tsx, pages/DiscoveryPages.tsx, state/demoReducer.ts, api/types.ts, pages/LandingPage.tsx, components/ExploreVerticals.tsx, pages/CartPage.tsx and tests.

**Interfaces:** stable coarse locality discovery, server exact checkout eligibility, DB-backed quotas/admission and admin audited tools. No public numeric point-distance. New route wiring and navigation combine Tasks 1–3. Shared config changes owned by integrator.

- [ ] Add/run privacy/admission/fulfillment/admin tests before changes; include synthetic distance/boundary regression.
- [ ] Implement coarse discovery, exact-price consent/replay, safe address and investigated admin controls.
- [ ] Integrate routes/models/settings, notification navigation, lifecycle and vertical screens; correct stale copy and pagination.
- [ ] Run focused tests and reconcile deliberate old-contract assertions while retaining security/stock coverage.

### Task 5: Whole-system verification, review and runbooks

**Files:** docs/BETA_IMPLEMENTATION_REPORT.md, docs/BETA_RUNBOOK.md, environment examples, README/contracts/services/database docs and tests for review findings.

- [ ] Run full backend suite, frontend suite, production build/type checks, migration upgrade/check/downgrade/re-upgrade on isolated PostgreSQL, compileall/pip check and diff checks.
- [ ] Fresh independent code/security review; reproduce and fix material findings with regression tests.
- [ ] Exercise browser workflows when tooling permits; otherwise document exact unverified UAT cases as blockers.
- [ ] Record exact test counts, changed files/migrations/configuration, worker operation, residual limitations, rollback and readiness classification. No deployment or commits.
