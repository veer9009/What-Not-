# Phase 4 database services implementation plan

Goal: implement the approved database-backed marketplace workflows without authentication, geography, HTTP marketplace activation, schema changes, commits, or pushes.

Authority: the user's approved design and explicit Phase 4 requirements in this conversation. Execute inline in the existing checkout; preserve the user's reviewable uncommitted changes.

Architecture: FastAPI -> services -> focused repositories -> SQLAlchemy -> PostgreSQL. A caller-owned outer transaction commits once; repositories never commit. Service writes use operation savepoints so caught failures cannot leave partial changes. Services require an explicit active transaction.

Global constraints: never access whatnot_db or upsc_compass; tests use only the owned temporary PostgreSQL cluster, explicit generated URLs, and Alembic. No JWT, hashing workflow, payments, geography, infrastructure, frontend changes, startup DDL, or runtime dependency additions.

- [x] Task 1: validated internal inputs, domain errors, money/integer bounds, and lazy request session lifecycle. Tests assert invalid inputs, cleanup, rollback, and health without configuration.
- [x] Task 2: user/seller repositories and services. Tests assert CRUD lookups, uniqueness, role protection, active state, allowed updates, and relationships.
- [x] Task 3: product/moderation repositories and services and response mappings. Tests assert ownership, transitions, reasons, activation, image behavior, and candidates explicitly without geography.
- [x] Task 4: addresses. Tests assert ownership, update restrictions after order reference, and transactional single-default switching with a parent user lock.
- [x] Task 5: orders. Tests assert one seller, active actors, address ownership, quantities, atomic inserts/decrements, immutable snapshots, exact totals/overflow, transitions, and exactly-once restocking.
- [x] Task 6: PostgreSQL concurrency. Separate committed test database; independent sessions verify final unit, default addresses, and competing terminal transitions, with bounded waits.
- [x] Task 7: documentation, whole-change review, complete backend/frontend and migration validation, final report.

Transition policy: PLACED -> ACCEPTED/CANCELLED/REJECTED; ACCEPTED -> PREPARING/CANCELLED; PREPARING -> OUT_FOR_DELIVERY; OUT_FOR_DELIVERY -> DELIVERED. All other transitions fail. Buyer cancellation before preparation; owning seller progression/rejection/cancellation. Terminal changes atomically restore stock once.

Fee policy: trusted configurable Decimal fixed fee, default 0.00. Product prices positive through services; storage's zero-price compatibility gap remains documented. Money maximum 9999999999.99; quantities/stock maximum 2147483647. API mappings retain total and name. Internal user input requires phone and structurally recognized precomputed password hashes. Referenced address delivery fields cannot change.

Verification: warning-strict full pytest, explicit persistence/service/concurrency selection, compileall, pip check, migration round trip and metadata comparison within isolated fixtures; frontend vitest, tsc, Vite build; git diff --check. No lint configuration exists.
