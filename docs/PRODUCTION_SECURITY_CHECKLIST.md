# Production security checklist and release proposal

Prepared 15 November 2026 for exactly five selected identities including one administrator. **Current decision: NO-GO.** Local checks and source controls support preparation; no actual AWS account, host, network, TLS endpoint, IAM policy, backup service, SMTP delivery or deployed browser acceptance is certified here. This document authorizes no deployment, provisioning, credential changes, migration, original-database writes, commit or push.

Use [audit evidence](PRODUCTION_READINESS_AUDIT.md), [deployment sequence](AWS_PILOT_DEPLOYMENT_CHECKLIST.md), [backup and recovery plan](PRODUCTION_BACKUP_RECOVERY.md), [monitoring/incident procedures](PRODUCTION_MONITORING_RUNBOOK.md) and [witnessed five-user plan](FIVE_USER_PILOT_TEST_PLAN.md). Add private evidence references with date/reviewer, never secrets or personal records.

## Status rules

LOCAL EVIDENCE means inspected source or recorded local regression evidence; it does not mean production verified. NOT VERIFIED means missing actual configuration/execution evidence. OPEN means a confirmed unresolved decision/control gap. PROPOSED means prepared design needing review and execution. Historical isolated-DB results are historical, not a new production test. The parent preparation report must record the final actual test commands/results for this artifact; do not copy earlier counts into a fresh-success claim.

| Control | Current evidence / status | Required production gate |
| --- | --- | --- |
| Authentication | LOCAL EVIDENCE: Argon2id, legacy rehash, pinned HS256/claims, generic denial, active DB-role/admission checks | Witness invalid/expired/forged token denial, suspension, expiry and secure operator recovery on approved target |
| Authorization | LOCAL EVIDENCE: server roles, party ownership, lifecycle access, reasoned admin audit and server-side ordering invariants | Buyer2/seller2 cross-object denial and no victim mutation for orders, addresses, notifications, property and Creative |
| Regression | Recorded audit has passing local frontend/build/non-persistence evidence and historical isolated persistence evidence | Fresh reviewed-artifact build/full relevant suites and guarded isolated DB integration; preserve failed runs and limits |
| Secret scan | LOCAL EVIDENCE: redacted heuristic source/history/artifact scan; no confirmed live tracked leak established | Approved full scanner/artifact review and candidate triage; heuristic scan is not exhaustive clearance |
| Production configuration | Preparation includes reviewed source hardening and deployment templates; exact final verification belongs in preparation report | Fail closed on missing DB/signing/admission, unsafe transport/origin/host/mail settings; actual host proof still NOT VERIFIED |
| Browser session | LOCAL EVIDENCE: token in memory; no application-cookie workflow observed; short expiry | Explain logout/copied-token expiry and tab-draft persistence; no password-reset/upload promise |
| Privacy/business | OPEN: draft pages, owner identity/contact/retention/eligibility/acceptance inputs missing | Owner-approved accurate notices, support/recovery/rights handling and pilot acknowledgement |
| Cloud/HTTPS/recovery/mail | NOT VERIFIED | Actual reviewed infrastructure/config, safe tests, restore and delivered-alarm/mail evidence |

## Release-blocking security gates

- [ ] Release owner and deputy named; exact reviewed artifact/configuration hashes and supported runtime versions recorded. Working tree alone is not a release.
- [ ] Exactly B1/B2/S1/S2/A1 admitted, including the recovery/admin operator. No sixth imported smoke account; admin not self-registerable. Trusted recovery process works without password sharing or an invented reset feature.
- [ ] Whole-site private pilot gate covers static HTML and all APIs, including unauthenticated property/Creative listing reads. Verify from unauthorized clients. Email allowlist and CORS do not make public reads private.
- [ ] Valid HTTPS chain/hostname and renewal test, only intended ingress, no public 8000/dev server/5432. DB private and reachable only from intended application network; operator access restricted through reviewed private management.
- [ ] Actual IAM policies, MFA/temporary operator access, scoped instance secret/log permissions, IMDSv2, encrypted disks/DB/backups, region/cost ownership reviewed. No AWS evidence currently establishes these controls.
- [ ] Dedicated runtime DB role cannot migrate/drop schema; separate controlled migration identity; verified remote DB TLS hostname and trusted CA (`verify-full`), server TLS and bounded pool/statement/connection settings proven. Do not disable verification to recover connectivity.
- [ ] Fresh consistent encrypted backup/PITR and restore to a new isolated target demonstrated, including roles/grants and business/audit integrity; owner-approved numeric RPO/RTO and measured results recorded.
- [ ] Monitoring operator receives safe test alerts; logs exclude sensitive content; workers/timers and mail scope are tested and documented. CLI entry points are not installed schedules.
- [ ] No unresolved Critical/High issue; required owner/privacy decisions and five-user HTTPS/mobile acceptance complete. Bounded lower-severity exceptions have mitigation, named owner and expiry.
- [ ] Explicit release-owner GO for the exact artifact/configuration and concrete reviewed deployment/migration plan obtained separately. Preparation does not grant it.

## Application and browser configuration review

- [ ] Build public frontend configuration uses reviewed same-origin `/api/v1` (or an explicitly approved HTTPS origin), contains no loopback fallback in the production artifact and no server credentials. Check generated JS/maps and actual browser network routing/deep links; a source change alone is insufficient.
- [ ] Backend is production mode with dedicated strong signing secret, explicit nonempty five-person allowlist and abuse controls. DB URL is required; remote DB certificate/hostname verification and trusted CA are required. Do not print connection URLs to validate them.
- [ ] Exact HTTPS CORS origins and trusted hosts match deployment. Reject arbitrary hosts/origins. Restrict trusted forwarded headers to the loopback proxy; prove source-IP spoofing cannot bypass quotas and distinct users behind proxy are not unintentionally one auth source.
- [ ] Production docs/OpenAPI disabled or behind reviewed operator-only access; readiness restricted as needed because it exposes operational aggregates. Minimal process health is not a DB gate.
- [ ] Nginx validated on actual host: HTTPS redirect, TLS parameters, body/time bounds, correct API prefix, SPA fallback, no directory listing/env/git/backup access. Apply nosniff, frame/referrer protections and appropriate CSP/HSTS after HTTPS verification. External product images/portfolio hosts require an accurate CSP and privacy review.
- [ ] API private responses use no-store; HTML and immutable hashed assets have separate reviewed cache policies. Prove shared browser/CDN caches cannot return private data across users.
- [ ] Service non-root, loopback bind, bounded supervision, no reload/preview development process. Protected env/config files have least OS permissions; secrets supplied through approved private runtime mechanism, not VITE variables, command history, repository or service logs.
- [ ] Production env filenames are ignored with explicit template exceptions; release package excludes raw envs, dumps, local evidence, logs and source maps unless specifically approved. Never copy local credentials into production.

## Data, business rules and abuse

- [ ] Confirm server computes prices, enforces exact delivery boundary, stock/quantity, current-price consent, idempotent retry and allowed transitions. Sellers see scoped fulfillment only in eligible lifecycle states without coordinates; buyers and other sellers cannot enumerate private orders.
- [ ] Reasoned admin action/audit verified for suspension, verification, product takedown, order dispute/fulfillment investigation, property moderation/report handling and Creative review. Manual phone/email verification means actual out-of-band check only; it establishes no legal identity, property title or quality guarantee.
- [ ] Property precise-address/phone policy tested across confirmed future visit, cancellation, material-edit suspension/reconfirmation, sold/takedown, listing expiry and inactive participants. Preserve implemented distinction: expiry hides listing/new requests but can preserve an existing confirmed future appointment.
- [ ] Creative party-only enquiry/quote/engagement and immutable accepted scope verified; seller delivery cannot substitute for buyer completion/review permission. Stale moderation approval version rejected. No private briefs/terms in public listings.
- [ ] Address ownership and historical-order immutability verified. Discovery returns locality candidates without precise seller dispatch coordinates; PIN selects own saved addresses, not geocoding. Owner explicitly accepts live/sample radius distinction.
- [ ] Auth/discovery/address/checkout durable budgets configured and bounded 429/recovery verified on isolated production-mode data. Public reads and several enquiry/visit/report/RFQ actions still need reviewed edge/action budgets; do not claim complete abuse coverage.
- [ ] Query/body size, pagination, external URL validation and error redaction reviewed against actual proxy/application behavior. No load/stress/quota exhaustion tests on original DB or production pilot.
- [ ] Quota scope hashes are treated as pseudonymous sensitive data; growth monitored. No automated retention cleanup assumed. New cleanup needs approved retention and implementation review.
- [ ] Notification read/update scoped to recipient; disabled mail/backlog decision explicit; actual SMTP TLS/receipt/retry/FAILED monitoring verified if mail enabled. Duplicate SMTP send/ack window disclosed; no automatic dead-letter reset or delivery guarantee claimed.

## Privacy and owner decisions

- [ ] Supply and verify operator legal identity, office/business disclosures, monitored support/privacy/grievance contact, escalation ownership, eligibility/child-data policy, processors/regions and retention schedule. Draft pages are not evidence of adoption or compliance.
- [ ] Decide and evidence participant terms/privacy acknowledgement; current registration does not record acceptance. Define verified manual correction/export/erasure/withdrawal handling without promising absent self-service deletion or invented deadlines.
- [ ] Explain location collection only on explicit action, manual/saved alternatives, seller fulfillment data, appointment-only precise property address and access revocation limits after disclosure. Never place private contacts/addresses in public listing text.
- [ ] Explain account-scoped same-tab sessionStorage drafts/retry records may persist after logout; shared-device users close the tab or explicitly clear supported drafts. Tokens/precise discovery coordinates must not be persisted by this flow.
- [ ] Explain external product/sample images, portfolio links and WhatsApp support traffic accurately. Confirm support ownership/monitoring and do not send messages as part of preparation.
- [ ] State payment scope accurately: no processing, escrow, direct UPI/COD verification/status, payouts or refund processing. Cancellation/completion changes workflow records, not money. Property title checks and Creative file delivery/direct arrangements occur outside platform facilities.
- [ ] Routine logs/alerts contain no bodies, tokens, passwords, precise coordinates, private addresses, raw query strings, recipient details or briefs. Synthetic success/failure log inspection, private access and approved retention tested.

## CI and release proposal — no automatic deployment

This is a reviewable proposal, not an installed CI workflow or authorization to contact a remote service. Do not install tools, change lockfiles, create cloud resources, upload artifacts or enable deployment without separate approval. Use the existing supervised Python/Nginx model; a container build is not required.

| Stage | Proposed gate / artifact | Failure behavior |
| --- | --- | --- |
| 1. Reviewed snapshot | Freeze source/lock/config-template hashes, toolchain versions and clean reviewed diff; prohibit env/dump/log inclusion | Stop on unexplained change or sensitive artifact |
| 2. Reproducible resolution | Existing pnpm lock with `pnpm install --frozen-lockfile`; exact reviewed Python requirement pins in isolated environment; capture transitive resolution/version inventory | Stop on lock mismatch, unsupported runtime or unreproducible dependencies; never silently upgrade |
| 3. Static checks/build | TypeScript plus Vite production build; Python compile/static tool selected by reviewer; production bundle API/secret check; `git diff --check` | Preserve failure output privately; no artifact promoted |
| 4. Tests | Complete frontend regression, backend non-persistence tests, guarded isolated PostgreSQL persistence/integration; current HTTPS/browser staging smoke separately | Never run fixtures against original DB; record actual counts/skips/failures; unresolved intermittent failures remain investigated |
| 5. Security checks | Approved JS lock-graph and Python runtime advisory scan; redacted secret/history/artifact scan; selected Python/static security checks | Missing scanner is NOT VERIFIED, not PASS; Critical/High findings block; reviewed lower-risk exception expires |
| 6. Package | Immutable built SPA + backend source/requirements/migrations + reviewed deployment templates + hashes + evidence manifest; exclude secrets/local DB/logs | Verify artifact contents privately; sign/hash using approved available process, do not invent signing infrastructure |
| 7. Isolated staging | Approved target identity, fresh restore/backup, exact production settings/perimeter/TLS, same artifact; execute five-user acceptance and alert/restore drills | Any security/integrity/UAT blocker keeps NO-GO |
| 8. Human release approval | Reviewer accepts evidence, owners sign migration/recovery plan, actual IAM/network/costs and five identities; explicit GO | No automatic deploy, migration, resource creation or credential change |
| 9. Coordinated maintenance release | After separate authority only: stop writers/workers/timers/restarts, verified backup, checked target, one controlled migration to reviewed `0008`, coordinated frontend/backend | Failed migration stops; no blind retry/stamp/downgrade; forward repair or approved new-target restore |
| 10. Observe / rollback | Private health/readiness, role smoke, worker/mail evidence and staffed gradual admission; retain previous compatible artifact | Roll back code/config only when schema/data compatibility proven; otherwise maintenance and recovery-owner decision; preserve/reconcile post-backup writes |

The audit reported Gitleaks, pip-audit, Bandit, Semgrep and Trivy unavailable; no later installed status is asserted here. A heuristic secret scan, `pip check`, successful compiler or dependency pins do not establish vulnerability clearance. Use an already approved scanning environment or arrange a separately authorized review; do not mark missing security tooling passed to meet a time budget. Pinning direct dependencies is not a full Python transitive lock/hash guarantee; review that reproducibility gap before declaring the release reproducible. `package.json` includes `latest` declarations, so the frozen reviewed pnpm lock is essential.

## Sign-off record

| Required reviewer | Evidence / accepted exceptions / UTC date | Status |
| --- | --- | --- |
| Application/security reviewer | Pending final local verification and cross-role staging evidence | NOT VERIFIED |
| Infrastructure/network/TLS/IAM owner | Actual cloud review pending | NOT VERIFIED |
| DB/backup recovery owner | Restore rehearsal and approved numeric objectives pending | NOT VERIFIED |
| Operations owner | Real alert, worker/mail, maintenance/recovery procedures pending | NOT VERIFIED |
| Business/privacy owner | Unresolved disclosures, support, eligibility, retention and acceptance | OPEN |
| Release owner | Exact artifact + five-user UAT + all gates + separate deployment authority | NO-GO |
