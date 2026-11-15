# What Not? — five-user AWS pilot deployment checklist

Prepared 15 November 2026. **Current gate: NO-GO. This checklist authorizes no deployment, infrastructure spend, production migration or credential change.** Use with [Step 25 audit](PRODUCTION_READINESS_AUDIT.md). Check a box only with dated redacted evidence, an owner and a PASS result; record approved scope exceptions explicitly. Never store credentials, precise coordinates, private addresses or raw database records in checklist evidence.

Preparation update: local API routing/production guards, env examples, Nginx/systemd candidates, admin bootstrap guards and operational docs are now implemented; see [morning handoff](MORNING_DEPLOYMENT_HANDOFF.md). Unchecked release gates still require exact-release review and actual Linux/AWS/UAT evidence; template existence does not mark them passed. Use the new [deployment runbook](AWS_PILOT_DEPLOYMENT_RUNBOOK.md) and `--config vite.config.ts` for explicit Vite/Vitest commands; legacy generated JS files are deliberately preserved.

## 1. Freeze scope and establish owners

- [ ] Name release approver, engineering operator, security reviewer, privacy/support owner and backup/incident owner; define pilot dates and staffed support window.
- [ ] Confirm exactly five selected accounts including the admin/recovery operator, roles and invitation/registration process. Keep actual email allowlist in protected server configuration, not this document.
- [ ] Decide enabled verticals and workflows. No payments, escrow, uploads or password-reset capability may be implied. Document secure operator account recovery and fraud/dispute handling.
- [ ] Approve AWS account/region, domain, whole-site restricted access method and spending limit before any paid action. Decide stable-IP restrictions versus VPN/private ingress/access gate based on real participant devices.
- [ ] Approve a pilot data notice, monitored privacy/support contact, processor/region inventory, retention/deletion/access request process and incident escalation. Resolve blank owner fields in `src/config/business.ts` with approved public facts.
- [ ] Decide shared-device private-draft handling without breaking uncertain-write idempotency. Tell participants how to close/clear private tab drafts; test the approved behavior.
- [ ] Record numeric **RPO ___ / RTO ___**, backup retention ___ and recovery evidence owner ___. Unfilled/unmeasured objectives fail the recovery gate.

## 2. Prepare a reviewable release locally — no deployment

- [ ] Review the complete working-tree diff and choose an immutable release snapshot/identifier. Current HEAD alone excludes important uncommitted recovery/location/security work. Do not commit/push under this audit's authorization.
- [ ] Implement/test production configuration requirements: explicit production environment, nonempty five-account allowlist, abuse controls on, strong dedicated JWT key, required PostgreSQL URL, verified remote DB TLS, HTTPS CORS and TLS for enabled SMTP. No production secret defaults.
- [ ] Make the frontend API destination an approved same-origin `/api/v1` or explicit HTTPS endpoint; reject accidental production loopback/HTTP builds. Inspect resulting assets without printing secret matches. The current build contains `http://127.0.0.1:8000/api/v1` and is unsuitable for pilot distribution.
- [ ] Add reviewed secret-free production templates, environment ignore coverage (including `.env.production` variants), Nginx and supervised non-root service/job definitions. Keep real secrets outside Git and frontend VITE variables.
- [ ] Reproduce/investigate the retained `AdminOperations.test.tsx:21` failure; preserve reason-denial and exact PATCH-field assertions. Obtain and retain a complete green frontend run plus stable affected tests; do not replace full-suite proof with a focused subset.
- [ ] Run TypeScript/production build and applicable backend tests on that snapshot. Run DB fixtures only against an independently isolated test database with identity guards; never original or rehearsal data. Preserve failures and report suite coverage accurately.
- [ ] Re-run a current JS lock-graph advisory check and isolated Python runtime vulnerability scan; triage/resolve High/Critical findings and review the retained Vitest Moderate advisories. `pip check` is not CVE clearance.
- [ ] Run approved redacted secret scanning on release source/history/artifacts; investigate candidates privately. Verify no server secret appears in JS, source maps, logs or config downloads.
- [ ] Use frozen pnpm resolution and exact reviewed Python dependencies; record Node/Python/PostgreSQL versions and OS support/patch status. Install no public development/test server on the eventual host.

## 3. Review infrastructure and obtain separate deployment authorization

- [ ] Produce a reviewed diagram, actual IAM policies, security-group/routing plan and cost review. Single EC2 + private RDS is a proposal; no AWS resources have been verified by this audit.
- [ ] Verify operator MFA/temporary credentials and least-privilege roles. Scope instance secret/log access to required resources; no wildcard administrative instance role. Require IMDSv2.
- [ ] Verify encrypted EBS/RDS/backups and protected secret delivery, log permissions/retention and recovery access. Use dedicated production credentials; do not reuse local envs or modify credentials without approval.
- [ ] Restrict all pilot site/API paths, including unauthenticated property/Creative reads, to the chosen participant access gate. Application email allowlist and CORS alone are insufficient.
- [ ] Verify DB is non-public with inbound 5432 only from application SG, no public 8000 and no unrestricted administrative access. Prefer private operator management rather than open SSH.
- [ ] Verify runtime DB role cannot migrate/drop schema; use a separately controlled migration identity. Validate RDS CA and hostname with `sslmode=verify-full`, enforce server TLS, set pool/connection/statement limits appropriate to the approved capacity.
- [ ] Review certificate issuance/renewal, domain ownership and HTTPS ingress. Plan how access restrictions accommodate validation without opening unrelated paths.
- [ ] **Stop for the release owner's explicit authorization of the concrete deployment/provisioning/migration plan and costs.** Previous local cutover approval covers no AWS action. Do not treat this checklist as authorization.

## 4. Provision/verify only after that separate authorization

- [ ] Capture redacted actual account/region/resource identities, IAM/SG/subnet rules and runtime configuration; verify they match the reviewed plan.
- [ ] Test from approved and unauthorized clients: only intended HTTPS ingress reachable; 5432/8000/admin access denied externally. Verify the whole-site access gate, not only login.
- [ ] Validate Nginx configuration, certificate chain/hostname/expiry, HTTPS redirect and SPA deep links. Verify API prefix routing and no dev/preview server exposure.
- [ ] Verify HSTS after HTTPS is correct, CSP suited to approved asset/image hosts, nosniff, frame protection, referrer policy and no-store private API responses; use a separate sensible cache policy for hashed static assets/HTML.
- [ ] Verify exact CORS origins and host allowlist. Test forwarded-IP spoofing denial; accept proxy headers only from the actual trusted proxy. Demonstrate auth limits work independently for distinct users without a shared-proxy lockout.
- [ ] Verify time/body limits and edge/application rate budgets for public reads and enquiry/visit/report/RFQ writes. Test bounded 429/Retry-After behavior on isolated test data; never stress production.
- [ ] Restrict docs/OpenAPI/readiness to the operator/pilot perimeter and expose only necessary minimal health information.
- [ ] Verify service is non-root, secrets unreadable to unauthorized OS users, no reload mode, bounded graceful restart, and maintenance stops API, workers, schedulers and auto-restarts together.

## 5. Recovery and database release gate

- [ ] Approve the initial production data plan: synthetic staging data first; import only specifically approved minimal pilot data. Never default to exporting local customers or the synthetic smoke account.
- [ ] Establish encrypted durable backups/PITR with approved retention and least-privilege restore access. Confirm settings and alarm on backup failure; do not rely on the local TEMP cutover dump.
- [ ] Restore a representative backup to a **new isolated target**; verify revision/schema/constraints/counts/sequence behavior and application projections with redacted evidence. Measure recovery duration and recoverable point against approved RPO/RTO. Include role/grant provisioning absent from single-DB dumps.
- [ ] Prepare a coordinated release/forward-repair plan. Preserve post-backup business/audit records; never automatically overwrite a database or blindly downgrade/stamp/reset. Define who may approve deliberate recovery cutover.
- [ ] Before any approved migration, verify exact target identity, current revision, script hashes and a write-free maintenance barrier covering application, workers and restarts. Obtain a fresh consistent backup, checksum and archive verification; stop on failed safeguards.
- [ ] Pin reviewed target **0008**, capture migration command/exit/log, and never blindly retry a failure. New production databases need the full reviewed migration chain; do not use `create_all`/stamp as a substitute.
- [ ] Verify 0008, `request_quotas`, verification columns, expected data counts and migration audit/status invariants for the **approved imported dataset**. Do not assume production has the local five/six users or two legacy orders.
- [ ] Confirm original local DB remains untouched by AWS/staging test tooling; all destructive fixtures guarded to a separate test DB/schema. Enable writers only after integrity/readiness checks pass.

## 6. Operations before admitting users

- [ ] Configure private sanitized access/error logs with request correlation, retention and access controls. Do not log tokens, request bodies, full query strings containing PII, mail recipients/bodies or precise location. Inspect actual generated logs with synthetic requests.
- [ ] Install bounded email, order completion and property expiry schedules as approved; capture exits, missed-run heartbeat and lease recovery. CLI commands alone are not a scheduler.
- [ ] Configure/test TLS SMTP delivery, bounded retries, FAILED/dead-letter investigation and duplicate-send expectations. Alternatively obtain explicit in-app-only scope approval and verify backlog handling/user expectations before disabling mail.
- [ ] Configure alarms for sustained 5xx/storage failures, readiness failure, disk/DB capacity, backup failure, outbox age/FAILED events, missed jobs and certificate expiry. Trigger a safe test alarm and verify the named operator receives it.
- [ ] Verify `/api/v1/health` and restricted `/api/v1/ready`; readiness 0008 does not prove mail delivery or job liveness. Document stop-admission/maintenance/incident escalation commands for the actual supervised environment.

## 7. Witnessed HTTPS UAT with synthetic accounts/data

- [ ] Buyer, seller and admin can log in; selected registration succeeds, duplicates reject, nonparticipants cannot enter and cannot browse outside the gate. Verify wrong password, suspension, expiry, logout and approved operator recovery.
- [ ] Buyer/seller cross-account address/product/order/notification access and role escalation denied; admin actions require a real reason and produce scoped audit evidence. Test no unnecessary delivery/private address data is returned.
- [ ] Geolocation after explicit click: success, permission denied, unsupported/unavailable, timeout and cancellation. Manual coordinates and PIN lookup of an owned saved address work; an unknown PIN invents no coordinates. Resolve audit K2: the 1/2/3 km selector is currently for samples, seller radii support those values, and live buyer discovery uses locality candidates without that selector. Approve/disclose this scope or implement/test the required live filter. Verify valid API coordinates and exact checkout boundaries on actual target desktop/mobile browsers over HTTPS; no fabricated fallback or persistent discovery coordinates.
- [ ] Seller dispatch/profile/product creation -> admin review -> buyer discovery/detail -> checkout; verify server price/stock/quantity, price-change consent, exact delivery boundary and idempotent uncertain-response retry.
- [ ] Seller accepts/prepares/dispatches/delivers; buyer confirms/disputes; dispute excludes automatic completion; worker completes eligible undisputed deliveries. Verify allowed cancellation/restock and lifecycle-controlled fulfillment access.
- [ ] Notifications are recipient-scoped and actual mail/job/alert behavior matches the accepted scope.
- [ ] If enabled: property review/expiry/enquiry/visit confirmation and precise-address privacy, including unauthorized/expired/cancelled/suspended access denial.
- [ ] If enabled: Creative provider/listing review, private enquiry/quote, buyer acceptance, delivery, buyer-confirmed completion and review; deny other accounts and stale moderation versions.
- [ ] Verify privacy/contact links, external-link disclosures, shared-device draft policy and support route. Do not describe manual verification as identity/title proof or imply platform payment/refund facilities.

## 8. Final release decision and controlled pilot

- [ ] Every required item has evidence/owner/date; no unresolved Critical/High blocker. Named reviewer approves any bounded Medium/Low exception with mitigation/expiry.
- [ ] Release owner signs **GO** for the exact artifact/configuration and only five identities after build/regression, infrastructure/TLS, recovery, operations, privacy and UAT gates pass. A passing unit test or local migration cannot satisfy this gate.
- [ ] Admit participants gradually during staffed hours; monitor errors, quotas, job/backlog/disputes and user reports. Define measurable stop conditions and who can stop admission/writers.
- [ ] Record pilot outcome and access revocation/data retention actions at pilot end; do not widen access or public-launch without a new review.

Current first action: review the [morning handoff](MORNING_DEPLOYMENT_HANDOFF.md), resolve its failed/unverified gates and approve the concrete account/region/ingress/domain/budget/recovery choices. Local production preparation is implemented; no cloud deployment is authorized. **Do not deploy yet.**
