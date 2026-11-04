# Controlled beta operating runbook

Prepared 4 November 2026. These are proposed operator steps after human release
approval; no deployment, scheduler, credential change or application DB migration
was performed during implementation.

## Prerequisites and configuration

Use PostgreSQL with the existing psycopg/SQLAlchemy/Alembic backend, existing Python
and Node dependencies, an SMTP service, an HTTPS reverse proxy and a trusted operator.
Keep DATABASE_URL and all WHAT_NOT_* secrets on the server. Only VITE_API_BASE_URL
is public frontend configuration. See backend/.env.example for every beta setting.

Set WHAT_NOT_ENVIRONMENT=production, DATABASE_URL, a securely generated
WHAT_NOT_JWT_SECRET_KEY (at least 32 bytes), explicit WHAT_NOT_CORS_ORIGINS, and
WHAT_NOT_BETA_ALLOWED_EMAILS as a JSON list including operators. Production refuses
an empty allowlist or disabled WHAT_NOT_ABUSE_LIMITS_ENABLED. Admission applies at
registration, login and authenticated requests. Public approved listing reads remain
public. Test environment bypasses action quotas; never run a beta server in test mode.

Default quotas: authentication 20 per 15 minutes per source and per email, discovery
60/hour/account, address writes 10/day/account, new checkout attempts 20/day/account.
Counters commit independently of failed business transactions. Trusted proxy source
address handling must be tested: a proxy seen as one source can exhaust the shared
authentication budget. Do not trust arbitrary forwarded headers.

Configure WHAT_NOT_EMAIL_PROVIDER=smtp, WHAT_NOT_EMAIL_FROM, SMTP_HOST, SMTP_PORT,
SMTP_STARTTLS, SMTP_TIMEOUT_SECONDS and provider-required SMTP_USERNAME/SMTP_PASSWORD
(all SMTP names prefixed WHAT_NOT_). Use TLS and authenticate where required. The
default disabled provider leaves events pending with no attempt consumption. No
live provider credentials or sends were used in local tests.

Verification timestamps record a trusted operator's actual out-of-band email/phone
check and required reason. They do not prove property ownership or legal validity.
Do not use the verification button without completing and recording that check.
Proof uploads remain unavailable until private storage and retention are approved.

## Release and migration sequence

1. Review the implementation report and resolve all release blockers, including
   browser UAT and real mail/perimeter checks. Confirm an operator can recover access.
2. Take and verify a restorable database backup. Rehearse on a restored isolated
   copy of representative legacy data; estimate locks/runtime and available storage.
3. Stop/drain API writes and all workers. Deploy backend/frontend as a coordinated
   maintenance release; old and new order states/contracts cannot be mixed.
4. With the approved target explicitly checked by the operator, run from backend:
   `python -m alembic current`, `python -m alembic heads`, then
   `python -m alembic upgrade head` and `python -m alembic check`.
   Expected chain is 0004 -> 0005 -> 0006 -> 0007 -> 0008, single head 0008.
5. Start the coordinated API/frontend. Check `/api/v1/health` (process) and
   `/api/v1/ready` (schema 0008, DB and aggregate outbox backlog). Readiness reports
   backlog, not scheduler liveness or successful end-to-end email delivery.
6. Smoke-test real buyer/seller/admin login and cross-account denial, checkout price
   consent/replay, fulfillment permissions, dispute and notification isolation,
   property appointment privacy and Creative buyer-confirmed completion/review.
7. Enable operator/scheduler runs below only after smoke tests. Admit 10–15 approved
   testers; monitor failures, backlog and disputes closely.

## Bounded workers

From backend with the approved server configuration:

```text
python -m app.workers process-email
python -m app.workers auto-complete
python -m app.workers expire-properties
```

These are one-shot bounded commands, not installed daemons. Arrange external runs,
for example every minute for email, every five minutes for delivery completion and
hourly for property expiry. No scheduler is installed by this branch. Capture exit
status and structured logs; alert on missed runs, any FAILED emails, increasing
pending age or disputes awaiting investigation. Use admin Operations for counts and
oldest pending timestamp. Do not log message bodies, recipients, tokens or addresses.

Creative pending enquiry/quote drafts are stored before sending in per-account,
per-entity sessionStorage and recovered in the same tab after navigation/reload.
They include private scope/quote text; successful replay or an explicit new-request
action clears the old draft. Close the tab on shared devices. Tokens and precise
coordinates are not stored there. This is not cross-tab/device recovery.

Email leases use SKIP LOCKED and tokens; expired crash leases recover with a finite
attempt budget. Backoff is exponential; exhausted/permanent failures become FAILED.
Investigate configuration/provider issues before any deliberate operator retry.
There is no UI to reset dead letters; preserve attempt/error history. SMTP does not
provide provider-side idempotency: send success followed by acknowledgment failure
can cause a bounded duplicate email. A stable Message-ID does not guarantee dedupe.

Delivery grace defaults to 24 hours. Deadline is persisted at seller delivery and
does not change when configuration changes. Disputes exclude auto-completion. Admin
must investigate; dispute cancellation and cancellation after preparation never
automatically restock. Suspended-party PLACED/ACCEPTED cancellation restores once.

Property expiry hides listings immediately in queries, even if the command is late.
The command emits one reconfirmation notice/audit per expiry cycle; it preserves
confirmed appointments. Expiry blocks new requests; sale/takedown cancels active
visits and closes enquiries. Material edits suspend confirmations until explicit
reconfirmation. Private address reads require an active confirmed future visit.

Quota counters contain hashed scopes, not raw source/email/location data. There is
no automated quota retention cleanup yet; monitor growth and approve a retention
policy before adding cleanup. SHA-256 scopes are pseudonymous, not anonymized.

## Rollback

Prefer a forward repair. Do not blindly run `alembic downgrade base`.
0005 refuses loss of lifecycle/events; 0006 always refuses destructive downgrade;
0007 refuses removal of populated creative records; 0008 refuses removal of account
verification evidence. An unverified 0008 downgrade drops quota counters and therefore
resets their budgets; do not use this as an operational reset.

For a backup restore, stop all traffic/workers first, preserve/export newer business
and audit data for investigation, restore the verified pre-release backup, then roll
back backend and frontend together. Restoring loses post-backup writes and cannot
unsend emails. Reconcile externally delivered messages and purchase outcomes before
resuming writes. Never relabel historical LEGACY completion as buyer consent.

## Required browser UAT before release

A dependency-free Windows/Edge smoke harness is included. After the normal build,
run from backend with PostgreSQL 17 binaries on PATH:

```text
python -m pytest -q -s ../scripts/beta_browser_smoke.py
```

It uses the same generated isolated PostgreSQL harness and synthetic identities,
serves the production bundle on an otherwise-unused localhost port 8000, opens five
disposable headless Edge tabs, and stops/cleans the test server, cluster and profile.
It refuses an occupied port and never uses application DATABASE_URL. Node 24+ and
installed Microsoft Edge are required; no browser library is installed. Restricted
Windows execution may require permission to start the test cluster/browser.
This smoke test complements the backend/frontend suites; it does not certify the
deployed proxy, SMTP, mobile devices or a human accessibility/usability review.

Use distinct real browser sessions for buyer A, buyer B, seller A, seller B and admin.
Exercise all three workflows with successful, failed and lost-response/reload paths;
verify notifications and email; contest delivery against the timeout runner; test
sold/takedown/edit/expired appointments and address revocation; test suspended actor
tokens; confirm quotes/reviews cannot cross ownership or bypass buyer completion.
Verify mobile layouts, timezone labels, navigation, accessibility and safe errors.
Automated jsdom/HTTP tests do not replace this browser pass.
