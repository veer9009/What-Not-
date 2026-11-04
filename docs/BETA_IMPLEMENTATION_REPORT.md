# Controlled-beta implementation handoff — 4 November 2026

Continued the existing uncommitted tree at HEAD `861c2cb`. The approved design and
policies were retained. No reset, deployment, commit, push, real credential edit or
application-database migration was performed. The initial 3 November audit remains
historical evidence; this report supersedes its implementation status.

1. **Exact files changed.** **131 changed/new source and documentation files**; see
   [the complete working-tree manifest](BETA_CHANGED_FILES.md).
   It includes inherited changes and this continuation, relative to HEAD. Ignored
   `.superpowers/beta-progress.md` records the handoff assessment, rulings and evidence.
   Ignored test logs and generated `dist/` are verification artifacts, not source changes.

2. **Migrations added/modified.** Four new migrations relative to HEAD:
   `0005_beta_foundation.py`, `0006_properties.py`, `0007_creative.py`,
   `0008_beta_abuse.py`. Existing tracked migrations 0001–0004 are unchanged.
   During continuation, new unapplied 0007's category constraint was aligned to the
   approved editing/VFX examples. 0008 was inspected and tested without modification.
   If an operator has already applied 0007 elsewhere, stop and create an additive
   category migration there instead of treating modified migration text as applied.

3. **Database schema changes.** Add audit_events, notifications, email_outbox;
   orders gain delivered_at, confirmation_deadline, completed_at, completion_source,
   a deadline index and revised lifecycle CHECK. Add property_profiles,
   property_listings, property_enquiries, property_visits, saved_properties,
   property_reports. Add creative_providers, creative_listings, creative_rfqs,
   creative_responses, creative_engagements, creative_reviews. Add request_quotas
   with composite scope/window key and window index, plus nullable users.phone_verified_at
   and email_verified_at. Domain FKs, checks, unique request/engagement/review and
   event-recipient keys enforce ownership relationships and duplicate prevention.

4. **Completed features.** Orders/disputes/timeout completion; owned fulfillment;
   expected-price validation and replay; persisted notification APIs/UI; transactional
   SMTP outbox and bounded runners; sale-only property workflows; Creative
   enquiry-to-review flow; operational admin tools; locality privacy, admission,
   durable quotas, no-store API responses, queue pagination, current public copy,
   readiness/backlog reporting and operator documentation.

5. **Remaining incomplete features.** No private proof uploads, property legal
   verification, payment, escrow, refund, after-preparation buyer cancellation request,
   password recovery/self-service verification challenge, cross-device Creative draft
   recovery, dead-letter replay UI, automatic quota cleanup or installed scheduler.
   Food-specific listing/compliance tools also remain unavailable, as labelled in UI.
   The approved beta explicitly excludes proofs/payments/legal work; these are not
   silently advertised as implemented. Broader household-service categories remain
   out of scope. Required release-environment checks are listed under item 20.

6. **Security/privacy fixes.** Actual database roles and active accounts remain
   authoritative; participant and notification ownership checks protect IDs. Sellers
   see minimal order fulfillment fields only from acceptance through active handling,
   losing access on terminal states. Admin sensitive reads require investigation
   reasons and audit records. Private property addresses require authorized reads;
   no coordinates or proof URLs are exposed. Material-edit/sold/takedown rules revoke
   appointment access. Public API payloads/errors are sanitized and responses are
   no-store. Durable quotas survive business rollback; production requires admission
   allowlist plus enabled limits. Account verification records a trusted operator's
   check, not inferred phone/property ownership.

7. **Location-inference mitigation/results.** Stable ~0.01-degree locality cells
   replace exact-point discovery distance/membership. Numeric distance/private
   coordinates are absent; checkout alone enforces exact radius with admission and
   durable address/attempt budgets. Unit and real HTTP regression tests pass: eight
   query origins cannot distinguish two seller points in the same cell. Offline
   diagnostic reproduces the old contract's 2.68-metre synthetic reconstruction and
   passes current locality invariance. This mitigates rather than eliminates inference:
   coarse cell inference and bounded exact-checkout probing remain possible.

8. **Order lifecycle.** PLACED -> ACCEPTED -> PREPARING -> OUT_FOR_DELIVERY ->
   DELIVERED -> COMPLETED; buyer can dispute DELIVERED. Seller cannot confirm buyer
   receipt; no backward jumps or cancellation after preparation through ordinary
   actions. Grace defaults to 24 hours and is persisted at delivery. Bounded locked
   SKIP LOCKED completion rechecks state/deadline; dispute/timeout races have one
   winning transition. Stock restoration remains locked/once for eligible cancellation.
   Legacy terminal delivery maps to COMPLETED/LEGACY without invented buyer consent
   or actual completion time; old awaiting orders get a rollout grace deadline.

9. **Notifications.** Transaction-local event publication creates one recipient-owned
   in-app record and outbox event per event-recipient key. List/count/read-one/read-all
   filter the current recipient; UI supports paging, safe domain links and refresh.
   Order delivery prompts buyer confirmation/dispute; property/service events use
   the same publisher. Messages omit private locations and contacts.

10. **Email/outbox.** SMTP adapter plus fake test provider; disabled configuration
    preserves pending records. Claim commits before network I/O. Token leases,
    SKIP LOCKED, a session send guard, exponential retry and finite attempts handle
    restart, slow send and stale acknowledgments. Permanent failures/dead letters are
    observable. Review fixed 450/451/452 recipient refusals to retry; 550 is permanent.
    Stable Message-ID does not guarantee SMTP deduplication. Send-success/ack-crash
    can produce bounded duplicates; there is no exactly-once claim or live SMTP test.

11. **Real Estate.** SELLER-owned OWNER/AGENT profiles and Residential/Commercial/
    Land/Plots sale listings; moderation/rejection/resubmission and stale-version
    protection; material edits return to review. Enquiries/replies, opt-in contact,
    visit acceptance/rejection/counterproposal, explicit reconfirmation, saved listings,
    frozen report reasons and audited disposition/takedown are implemented. Expiry
    blocks new work while preserving confirmed appointments; bounded expiry notices
    dedupe per reconfirmation cycle. Sale/takedown cancels visits and closes enquiries.
    Review fixed future rescheduling/rejection after a suspended appointment's old
    time passes. Precise address stays private until an active confirmed future visit.

12. **Creative Services.** Provider profiles, moderated listings, portfolio HTTP(S)
    links, FIXED/STARTING/HOURLY/QUOTATION and remote/locality scope. Frozen categories:
    Video Editing, Travel Video Editing, Influencer Reel Editing, VFX. BUYER RFQ ->
    provider quote -> buyer acceptance -> provider delivery -> buyer completion ->
    one legitimate engagement review. Accepted terms/amount are immutable snapshots.
    Request fingerprints and uniqueness protect replay and changed payloads. Review
    fixed reload recovery: private pending payload/key persists in account/entity-scoped
    per-tab sessionStorage before transmission; storage errors fail closed. Close
    shared-device tabs; no tokens/precise coordinates are stored in this recovery data.

13. **Admin.** Paginated product/property/creative moderation, reviewed-version
    approval, product takedown, reports, orders/disputes, suspension/reactivation,
    reasoned manual verification, audited private reads, audit feed and outbox counts.
    Investigated dispute completion/cancellation and stranded-order cancellation use
    explicit actions. Prepared/dispatched cancellation never automatically restocks;
    eligible suspended-party pre-preparation cancellation restores once. No refunds
    or arbitrary status assignment are introduced.

14. **Backend tests.** Full `python -m pytest -q -W error`: **648 passed**, no skips,
    failures or errors, 201.79 seconds. Includes direct authorization/security,
    notification ownership, order state machine, stock/idempotency, independent
    transaction races, failure/retry/lease tests, dispute/auto-completion, property and
    Creative workflows, migrations and privacy regressions. All persistence used
    generated isolated PostgreSQL 17, ignoring application DATABASE_URL. The initial
    restricted sandbox could not start PostgreSQL (Windows error 87); the unchanged
    harness was run with the required execution permission. Historical contract
    assertions were updated only for explicitly replaced approved behavior; original
    ownership/inventory/count assertions remain. A leaked test user was cleaned up.

15. **Frontend tests.** Full `vitest run --pool=vmThreads --maxWorkers=1`:
    **227 passed across 27 files**, no skips/failures, 52.61 seconds. One overlapping
    backend/build run had a login-test timeout and subsequent test contamination
    (225 passed/2 failed); the unchanged serial rerun passed. No assertion or timeout
    was weakened to hide it. Additional explicit Edge integration test:
    **1 passed**, 40.60 seconds, against the production build and generated PostgreSQL,
    with five authenticated tabs. Verified outsider denial, order progression and
    fulfillment, buyer completion/dispute, investigated admin resolution, notifications,
    sale enquiry/reply/visit/address gating and sale revocation, Creative RFQ through
    buyer completion/review, locality discovery, and real cart checkout with saved
    address/current prices. Early driver failures concerned hidden sidebar text,
    same-route refresh and selecting the wrong amount field; corrected the driver,
    without changing product behavior. No browser framework/dependency was installed.

16. **Production build/types/lint.** `npm run build` passes (`tsc -b && vite build`),
    final build 4.91 seconds. Python compileall and pip check pass. No dedicated
    ESLint/Ruff/mypy/type-check command is configured beyond the TypeScript build.
    Final diff whitespace validation is recorded in the ledger.

17. **Migration verification.** Single head 0008 and linear 0001->...->0008.
    Full isolated suite passes fresh upgrade, ORM metadata checks, populated legacy
    0005 consent mapping, historical 0001–0004 round trips, Creative empty rollback/
    re-upgrade and populated refusal, and explicit populated 0008 upgrade/check/
    downgrade/re-upgrade plus verified-account downgrade refusal. 0008 adds nullable
    timestamps without falsely verifying existing users; quota model/index matches.
    Its locked downgrade refuses verification loss; otherwise it removes counters
    and resets budgets. 0006 deliberately refuses destructive downgrade even empty.
    No production/application database was inspected or migrated.

18. **Known limitations.** SMTP send/ack duplicates; operator/scheduler dependency;
    aggregate readiness is not worker-liveness proof; residual coarse/checkout location
    inference; fixed-window quotas and reverse-proxy source sharing; no quota cleanup;
    public approved listing reads; per-tab drafts can contain private text; separate
    per-seller checkout with possible partial basket success; normal monetary browser
    display uses Number while backend Decimal remains authoritative. Generic audit
    entity references are service-authorized rather than domain-specific FKs. Append-only
    audit behavior is enforced by application write paths, not a DB immutability trigger.
    Other actors' changes require refresh/leave-and-return; no real-time push revokes
    information already displayed in a browser. Subsequent sensitive reads recheck
    permission, and refreshed terminal appointments discard the address view.

19. **Required environment/services.** PostgreSQL/psycopg, Python API, built frontend,
    trusted ADMIN, HTTPS/reverse proxy, SMTP provider and external one-shot worker
    scheduling. Required server settings: DATABASE_URL, production environment,
    strong WHAT_NOT_JWT_SECRET_KEY, explicit CORS origins, nonempty
    WHAT_NOT_BETA_ALLOWED_EMAILS (including operators), enabled quotas. SMTP needs
    WHAT_NOT_EMAIL_PROVIDER=smtp, EMAIL_FROM, SMTP_HOST, SMTP_PORT, SMTP_STARTTLS,
    SMTP_TIMEOUT_SECONDS and provider-required username/password (all prefixed
    WHAT_NOT_). Grace/reconfirmation/quota/worker bounds are in backend/.env.example.
    Only VITE_API_BASE_URL is public frontend configuration.

20. **Beta blockers/release gates.** No known uncorrected Critical/Important code
    finding remains after review and local verification. Automated real-browser smoke
    passes, but it covers seeded-account happy paths, not the entire human UAT matrix.
    Live SMTP delivery, target-environment HTTPS/CORS/proxy behavior, scheduled worker
    execution/monitoring and backup restore rehearsal have not been exercised here.
    Require human buyer/seller/admin UAT for full mobile/accessibility/error/reload
    coverage and explicit approval of the final diff before admitting real testers.
    Do not interpret local unit/build success as permission to deploy.

21. **Recommended deployment/migration sequence.** After review/approval and release
    gates: verify restorable backup and representative restored-data rehearsal;
    drain writers/workers; coordinate API/frontend contract release; operator verifies
    intended target then upgrades 0004->0005->0006->0007->0008 and runs alembic check;
    start API/frontend; inspect health/ready, smoke all roles; enable monitored bounded
    workers; admit only 10–15 approved identities. Full commands are in [runbook](BETA_RUNBOOK.md).

22. **Rollback.** Prefer forward fix. 0005/0006/0007/0008 intentionally refuse lossy
    history removal. Never blindly downgrade through these guards. If restore is
    necessary, stop traffic/workers, preserve post-backup business/audit data, restore
    verified backup and roll backend/frontend back together. Reconcile post-backup
    purchases and emails: restore cannot unsend mail and loses newer writes. Keep
    LEGACY completion distinct from actual buyer consent.

Independent Principal Engineer review found three Important issues and no Critical
issue; the fix pass reproduced each with failing tests and verified the corrected
behavior. Final author review additionally reconciled categories/contracts and cache
privacy. All code remains uncommitted for human/ChatGPT review.

Rulings carried from the ledger:

- Continue the current shared tree without worktree/branch/commit: explicitly requested
  by the user. Cost: no isolation from concurrent manual edits; preserve all changes.
- Prior design approval authorizes implementation without another design/plan approval.
  Cost: any misunderstood policy must be resolved in the final human review.
- Update historical assertions only for approved replaced discovery/lifecycle/price
  contracts. Cost: historical exact-discovery compatibility ends; coordinated rollout
  is mandatory. Security/inventory assertions are retained.
- Persist private Creative pending payload/key in actor/entity-scoped per-tab storage.
  Cost: private text remains on that tab until cleared; no cross-device recovery.
- Freeze Creative categories to the four existing editing/VFX examples and fix the
  new unapplied 0007 accordingly. Cost: broader categories are unavailable; already
  applied external 0007 installations require an additive migration.

Deferred review minors: none formally raised. The operating and product limitations
above remain explicit; no claim of production perimeter or live-provider verification
is made.

Release classification: **NOT READY FOR BETA** until item20's operational verification
and human review gates are closed. Implementation is locally verified; real tester
admission is not authorized by this report.
