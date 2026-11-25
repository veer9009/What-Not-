# Direct payments and transaction records

What Not? records cash on delivery (COD) and direct buyer-to-seller UPI payments for Homemade orders. Delivery remains seller-managed. It does not process money, verify bank transfers, charge commission, hold balances or settle funds. Creative and Property workflows remain unchanged.

## Recording flow

Order placement, checkout recovery keys, price calculations and order-state APIs are unchanged. Buyer Payments lists the buyer's persisted orders. The buyer explicitly records COD or direct UPI after placing an order; the method is immutable. Existing orders have no payment record and display **Not recorded** until an explicit selection. Nothing is inferred from legacy delivery/completion states.

For UPI on an accepted-or-later order, the buyer can report having paid, optionally providing a bounded reference. This produces **Buyer reported · unverified**, never confirmed payment. The seller independently checks receipt, reviews the order amount/method/reference and confirms collection. COD confirmation requires a delivered/completed order. A seller may confirm independently checked UPI receipt without a buyer report. Dates are report/confirmation timestamps, not bank transaction dates. Requests never accept caller-supplied totals, identities, bank credentials or dates.

Payment lifecycle: `PENDING -> BUYER_REPORTED -> SELLER_CONFIRMED`, or `PENDING -> SELLER_CONFIRMED`. Only UPI can be buyer-reported. Identical retries are no-ops; conflicting methods/references or stale reviewed states return 409. A seller can confirm only their own order's collection. Admins inspect, but cannot impersonate a buyer or seller through these mutation endpoints.

Cancellation/rejection blocks new reports/confirmations but never erases prior claims or collections. Delivery disputes remain separate from payment status. No partial-payment, bank-verification, payment-dispute arbitration or automated refund functionality is introduced. Whether/how to record external refunds, resolve payment disputes, retain references or verify seller UPI details requires business-owner policy; no such policy is invented here.

## Persistence and security

Migration 0013 adds only `order_payments`, keyed by the existing order ID, with method/state/reference and timestamps. It does not change or backfill orders, users or authentication. Foreign keys and checks enforce allowed methods/states, reference format and state/date consistency. There is no duplicated monetary amount; lists and metrics use the order's server-calculated `total_amount`.

Writes lock actor then order, matching existing order transitions. The order lock serializes first-record creation, buyer report and seller confirmation, including opposite-role races. Every actual mutation writes an `order_payment` audit event in the same transaction/savepoint. Audit reasons never include references. Participants and existing authenticated admins can read references; React escapes them. Validation output excludes submitted values. Payment APIs inherit no-store, nosniff, referrer and bearer/session protections. No UPI PINs, passwords or bank credentials are requested or modeled.

Admin aggregates are calculated over all persisted orders, independent of pagination. Gross order value includes cancelled/rejected orders; those amounts are separately shown. COD/UPI values mean method-attributed order value, not collections. Buyer-reported totals include reports subsequently confirmed. Seller-confirmed totals mean gross attested collections; external refunds are not recorded/subtracted. Collections on cancelled/rejected orders are separately displayed. Pending confirmations exclude cancelled/rejected orders. Unrecorded-method value is explicit. Platform revenue is zero under the no-commission launch policy, never the sum of seller payments. All monetary arithmetic uses PostgreSQL numeric/Python Decimal and JSON decimal strings; the frontend does not re-sum with binary floats.

## API additions

- `GET /payments`: own buyer/seller orders, or all for an existing admin; offset/limit with `has_more`.
- `GET /payments/orders/{order_id}`: same ownership rules.
- `GET /payments/metrics`: existing ADMIN role only.
- `POST /payments/orders/{order_id}/method`: owning BUYER; `{method: COD|UPI}`.
- `POST /payments/orders/{order_id}/report`: owning BUYER; optional `{reference}`.
- `POST /payments/orders/{order_id}/confirm`: owning SELLER; `{expected_status: PENDING|BUYER_REPORTED}`.

This build expects schema revision 0013. Existing deployment readiness checks continue to reject mismatched schemas. **No migration, deployment, production credential change or production-data operation is authorized by this document.** An operator must separately approve migration application, take the existing approved backup precautions and verify readiness before release. Downgrade refuses to remove populated payment history. Local migration verification uses generated isolated PostgreSQL only.

## Verification limits

Frontend/API-client tests and Chrome interception use synthetic responses. Payment API, role/ownership, state, concurrency, decimal metrics and migration tests use real FastAPI/SQLAlchemy/PostgreSQL in the fixture's temporary cluster. No real COD collection, bank transfer, SMTP, live EC2 or production database is used. Device/browser/screen-reader coverage and unresolved findings belong in the final report.
