# Phase 4 implementation report

Checkpoint: `b7c49ee46d4a443711d4ffe6fb46bb0eca4240e5`. This report records the
implementation and validation before the separately authorized release commit.
No ORM/migration change, dependency addition, or frontend source change.
Neither `whatnot_db` nor `upsc_compass` was accessed or inspected.

## 1. Files created/changed

Created (paths relative to backend):

- `app/repositories/`: `__init__.py`, `users.py`, `sellers.py`, `products.py`,
  `addresses.py`, `orders.py`, `validation.py`.
- `app/services/`: `__init__.py`, `inputs.py`, `errors.py`, `operations.py`,
  `validation.py`, `users.py`, `sellers.py`, `products.py`, `moderation.py`,
  `addresses.py`, `orders.py`, `mappers.py`.
- `app/api/dependencies.py`.
- `tests/test_service_inputs.py`, `test_service_revalidation.py`, `test_db_dependency.py`.
- `tests/persistence/test_services_marketplace.py`, `test_services_orders.py`,
  `test_service_concurrency.py`, `test_request_sessions.py`.
- `SERVICES.md`, this report; root `docs/superpowers/plans/2026-10-12-phase4-services.md`
  and `2026-10-12-phase4-progress.md`.

Changed: `app/main.py`, `app/db/session.py`, `app/api/contracts.py`,
`app/schemas/common.py`, `app/schemas/product.py`, `tests/persistence/conftest.py`,
`CONTRACTS.md`, `DATABASE.md`, root `README.md`.

## 2. Repository architecture

Focused repositories perform SQLAlchemy queries, inserts, relationship loading,
filtering, and row locking. Strict scalar ID validation occurs before SQL.
Repositories never commit. No generic repository framework or infrastructure.

## 3. Service architecture

Services apply business rules and coordinate repositories through one supplied
Session. Validated inputs, domain errors, and explicit response mappers support
Route -> Service -> Repository -> SQLAlchemy -> PostgreSQL. Actor IDs are trusted
internal/test inputs, never authentication.

## 4. Sessions and transactions

Lazy application engine; one session per database request; unfinished transaction
rollback, session close, and shutdown engine disposal. No startup connections/DDL.
Writes require an explicitly begun outer session transaction. Operation savepoints
protect caught failures; services flush, and the outer caller commits once.
`session_scope` handles commit/rollback/close for direct callers. Map responses while
the session is open. Avoid unrelated pending mutations before service savepoints.

## 5. Users

Create/read by ID/email/phone, bounded listing, activate/deactivate. Required unique
email/phone and valid BUYER/SELLER/ADMIN roles. Internal input accepts structurally
recognized precomputed bcrypt/Argon2id hashes, masked/excluded from serialization.
Public responses omit hashes. No plaintext password field, hashing, verification,
registration persistence, or login. Format validation is not cryptographic proof.

## 6. Sellers

Create only for an active existing SELLER; one profile per user. Read by profile/
user ID, update allowed shop fields, and list seller-owned products. Ownership and
verification are not seller-editable. No implicit accounts. Seller ID means profile ID.

## 7. Products

Always create PENDING. Seller-owned updates, activation/deactivation, and resubmission.
APPROVED edits return to PENDING; REJECTED edits retain reason until explicit
resubmission clears it. Validate stock/radius/price/text/category/URLs. Primary image
changes preserve secondary images. Buyer candidates require APPROVED + active +
stock > 0; the query explicitly omits geographic eligibility.

## 8. Moderation

Active ADMIN required for pending queue and moderation. Approve/reject only PENDING;
trimmed nonblank rejection reason required. Approval/resubmission clear reasons.
Moderation and product writes lock and refresh current rows.

## 9. Addresses

Create/get/list/update/set-default with ownership checks. Lock the owning user,
clear/flush the old default, then set the new default atomically. Zero defaults
allowed. Once referenced by an order, actual delivery-field edits fail; labels,
defaults, and unchanged delivery values remain allowed. Create replacement addresses
to preserve history. No snapshot schema change or deletion endpoint.

## 10. Orders

Require active BUYER, owned address, existing profile/active SELLER, one seller,
nonempty unique product IDs, positive quantities, approved/active/positive-priced
products, and sufficient stock. Snapshot names/prices, calculate exact Decimal
amounts, insert order/items, and reserve inventory atomically. Default fee **0.00**;
trusted injectable fixed-fee policy. No client monetary values or frontend ₹49 rule.

## 11. Stock/concurrency

SELECT FOR UPDATE locks refreshed product rows in ascending ID order. Shared
buyer/seller-user locks protect active roles while allowing concurrent purchases.
Cancellation/rejection locks the order before products and restores quantities once.
Late database errors and restoration overflow roll back the complete operation.
Real tests observe both buyers waiting on product locks and exercise competing
terminal transitions and default-address switches through independent transactions.

## 12. Order transitions

| Current | Allowed next |
|---|---|
| PLACED | ACCEPTED, CANCELLED, REJECTED |
| ACCEPTED | PREPARING, CANCELLED |
| PREPARING | OUT_FOR_DELIVERY |
| OUT_FOR_DELIVERY | DELIVERED |
| DELIVERED, CANCELLED, REJECTED | None |

Owning buyers may cancel before preparation; owning sellers perform allowed seller
transitions. Unrelated actors, arbitrary jumps, and repeated terminal changes fail.

## 13. Routes

Health remains database-independent **200**. All auth/product/order/admin marketplace
routes remain **501** for valid requests; invalid input remains **422**. Descriptions
now acknowledge internal services and deferred authentication/geography. Session
integration uses test-local routes only. No actor-ID HTTP shortcut or fake auth.

## 14. Tests added

89 new cases cover storage bounds, hashes, model mutation/nested revalidation,
explicit transactions, strict IDs, users/uniqueness, seller roles/ownership,
products/moderation/images/visibility, addresses/defaults/history, multi-item and
mixed-seller orders, snapshots/totals/fees, unavailable actors/products/stock,
late-flush rollback, transitions/restoration/overflow, request lifecycle, and three
real PostgreSQL concurrency scenarios.

## 15. Backend results

Complete warning-strict pytest: **272 passed**, 43.71s, exit **0**.
Separate persistence/service/concurrency selection: **134 passed**, 38.58s, exit **0**.
Python compileall passed. pip check: no broken requirements. Diff whitespace checks passed.

## 16. Alembic results

Upgrade to head, metadata check, downgrade to base, re-upgrade, and metadata check
passed through the isolated migration test. Both comparisons reported no new
upgrade operations. Revision 0001 and all seven ORM models are unchanged.

## 17. Frontend results

Vitest **41 tests passed across 6 files**. TypeScript `tsc -b` passed; production
Vite build passed. No frontend source/dependency changes. Lint remains unconfigured.

## 18. Issues found/fixed

- Added money and INTEGER stock/quantity storage limits.
- Began an explicit ORM transaction in the rollback-isolated fixture.
- Independent review found mutable-input bypasses, implicit transaction acceptance,
  and missing scalar ID validation. Failing regressions reproduced all three; fixes
  revalidate nested models/PATCH raw values, enforce transaction origin, and validate IDs.
- Stronger stock tests exposed seller-row serialization; shared placement actor
  locks now permit direct product contention while protecting active roles.
- PATCH raw-field validation avoids warnings during serialization of mutated values.
- Windows pg_ctl sandbox restriction required the same isolated harness outside the
  restricted token. Some PowerShell runner exits reported access violations despite
  Python success; final cmd.exe ordinary-pipe runs exited cleanly.
- A separate PTY run stalled during teardown and was interrupted. Its exact generated
  directory was verified, pg_ctl confirmed no server, and it was removed. Clean
  persistence revalidation passed.

## 19. Known limitations and implementation decisions

No authentication, geography, HTTP persistence activation, frontend integration,
payments, retries/distributed locking, or infrastructure. Public registration/order
contracts still omit required phone/address identity; internal inputs supply them.
Zero-price storage rows remain incompatible with positive-price API responses.
Client BIGINT precision remains an integration issue. Direct SQL can bypass service
roles/lifecycle/history and modify snapshots. Hash checking validates format only.
Stock restoration beyond INTEGER capacity fails atomically. Fee policy is provisional.

Connection/operational failures remain internal exceptions; authenticated HTTP
handlers must sanitize infrastructure failures. Constraint/domain errors are
translated now, and no marketplace HTTP route accesses storage. This is the deferred
minor from review.

Decisions during implementation: work in the requested existing checkout without commits; honor the
explicit complete-plan approval without further planning gates; use shared actor
locks for placement and exclusive locks for user/address/profile writes. No approved
architecture or schema change was needed.

## 20. Recommended Phase 5

Real authentication/authorization, trusted request identity, password-hashing
workflow, secure registration/login, and deliberate phone/address contracts. Then
activate appropriate service-backed routes with safe error mapping. Establish
geographic eligibility before presenting buyer discovery/checkout as delivery-ready.
Review frontend integration separately after those API boundaries are stable.
