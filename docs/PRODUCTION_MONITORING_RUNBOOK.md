# Production monitoring and incident runbook

Prepared 15 November 2026 for a restricted five-person pilot. **PROPOSAL / NOT VERIFIED on a production host. Deployment remains NO-GO.** This document authorizes no infrastructure, deployment, migration, credential change or production write. Hostnames, service identities, alert recipients and approval records must be completed before use.

Use with [production audit](PRODUCTION_READINESS_AUDIT.md), [deployment gates](AWS_PILOT_DEPLOYMENT_CHECKLIST.md), [backup and recovery plan](PRODUCTION_BACKUP_RECOVERY.md), [security checklist](PRODUCTION_SECURITY_CHECKLIST.md), [five-user acceptance plan](FIVE_USER_PILOT_TEST_PLAN.md) and [existing worker semantics](BETA_RUNBOOK.md). The five-person limit supersedes the older beta runbook's suggested 10–15 testers. Reviewed deployment templates are preparation material; their presence does not prove installation or a healthy host.

## Ownership and release record

| Field | Required value / current status |
| --- | --- |
| Release owner / deputy | OWNER INPUT REQUIRED; NOT VERIFIED |
| Staffed pilot hours and timezone | OWNER INPUT REQUIRED; record UTC timestamps and display Asia/Calcutta |
| Incident operator / security escalation / DB recovery owner | OWNER INPUT REQUIRED; NOT VERIFIED |
| Exact artifact hash, configuration revision, expected schema | Record before release; schema expected `0008` |
| Actual API, proxy, worker timer and certificate renewal unit names | Map templates to installed names; NOT VERIFIED |
| Alert destination / acknowledgement / fallback channel | Named human and tested private delivery required; NOT VERIFIED |
| Recovery objectives | See [backup plan](PRODUCTION_BACKUP_RECOVERY.md) for numeric proposals; owner approval and measured restore evidence pending; no objective achieved by this document |
| Whole-site perimeter access / maintenance control | Document tested operator procedure, including public browse routes; NOT VERIFIED |

Proposed staffed-hours incident response: acknowledge a critical page within 5 minutes, stop admission immediately for integrity/privacy risk, and give the release owner an update within 15 minutes. These are proposed targets, not an existing staffed service or SLA. Outside staffed hours the pilot must remain closed unless an owner accepts an explicit on-call arrangement.

## Small monitoring design

Use a single HTTPS Nginx proxy, loopback supervised Python API and bounded systemd worker/timer units; do not add Docker, Kubernetes or a public development server for this plan. A CloudWatch agent/log destination and alarms are proposed, not provisioned. Retain journald locally with a disk cap and private operator access; send only sanitized necessary events to a private CloudWatch log group. Use Nginx aggregate status/latency metrics and host disk/memory metrics, plus private DB capacity/backup metrics when the actual DB service is chosen. Restrict agent IAM to the exact approved metrics/log destinations; validate costs and retention before installation.

Poll process liveness and storage readiness separately from a trusted private/perimeter-authorized monitor. `/api/v1/health` proves that the process responds; it does not touch PostgreSQL. `/api/v1/ready` checks DB access, revision `0008` and returns aggregate pending/leased/failed email counts and oldest pending timestamp. A successful readiness response does not prove SMTP delivery, worker scheduling, order completion or fresh backups. The admin Operations endpoint provides aggregate outbox state; do not place an admin token in a public uptime service.

No metrics exporter, alert wiring, request correlation pipeline or scheduler heartbeat should be assumed to exist. Install/configure and prove each selected control only after separate authorization. The minimum pilot dashboard should show external HTTPS status, liveness/readiness separately, 5xx count, latency, CPU/memory/disk/inodes, DB connections/free storage, last successful backup, outbox state/age, and last start/success/exit of every worker. An absent signal is a failed monitoring gate.

## Logging, privacy and retention

Proposed retained fields: UTC time, severity, trusted/generated correlation ID, release ID, HTTP method, route template (for example `/orders/{id}`), status, response duration, worker command name/count/exit, sanitized error class/code and aggregate counters. Validate correlation support before promising request tracing; current source does not establish an end-to-end correlation system. Avoid high-cardinality user IDs in metrics. Restrict incident evidence to the minimum private reference needed for investigation.

Do not collect request/response bodies, Authorization/Cookie headers, JWTs, passwords, database URLs, secrets, raw query strings, email recipients, notification/mail content, names, phone numbers, postal addresses, precise coordinates, briefs or quote terms in proxy, application, worker or alert output. A route may carry identifiers; normalize it for routine telemetry. Disable default access-log fields that retain IP/user-agent/path query detail unless the owner approves a specific necessary use and retention. Hashes/pseudonymous quota scopes remain sensitive. Unexpected tracebacks can expose parameters: inspect synthetic failure logs before release and restrict raw error logs until verified sanitized.

Proposed retention: 14 days for sanitized operational logs, 30 days for aggregate metrics; incident evidence and application audit retention need a separate approved policy. Set journald/CloudWatch bounds and verify deletion/expiry. Do not remove business/audit records as log cleanup. Inspect a synthetic login failure, invalid coordinate request, checkout failure and SMTP error; retain only redacted evidence that forbidden content is absent. No public paste, issue attachment, alert email or chat message may contain raw logs/backups/env files.

## Proposed alerts — owner approval and safe staging tests required

These conservative five-user thresholds are starting proposals, not measured baselines or configured alarms. Use counts with rate alerts so a single low-volume failure is visible. Acknowledging an alarm does not disable it. Record recipient, test trigger, received time, acknowledgement and recovery time.

| Signal | Proposed warning / critical | First response |
| --- | --- | --- |
| HTTPS / liveness / readiness | Poll every 60s; critical on 2 consecutive failures of any probe | Separate edge, API and DB failures; stop admission if readiness fails |
| API/proxy 5xx | Warn on any unexpected 5xx; critical on 3 in 5 min or >5% with at least 20 requests | Use sanitized statuses and deployment timestamp; do not replay writes blindly |
| Latency | Warn p95 >2s for 10 min with at least 20 requests; critical >5s for 5 min | Check DB/host saturation and dependency timeouts; small sample caveat |
| Disk / inodes | Warn used >75%; critical >85% or <2 GiB free; inode >85% critical | Freeze releases, examine growth privately, preserve DB files |
| Memory / CPU | Warn memory >80% or CPU >80% for 10 min; critical OOM/process restart loop | Inspect service limits, DB pool and recent changes |
| DB storage / connections | Warn storage >75%, connections >70% approved max; critical >85% storage or >85% connections for 5 min | Check capacity, long transactions and approved limits; no casual parameter/size changes |
| Email outbox | Warn oldest pending/leased >5 min; critical >15 min or any FAILED | Check provider-enabled flag, worker exits and SMTP codes |
| Worker heartbeat | Proposed email every 1 min, completion every 5 min, property expiry hourly; alert after 2 missed scheduled successes | Verify timer and exit; a zero processed count can be a successful run |
| Backup | Any failed scheduled backup critical; missed expected successful backup critical after schedule +15 min | Stop release changes; recovery owner confirms recoverable point |
| TLS certificate | Warn <30 days remaining; critical <14 days, any expired/hostname/chain failure immediate | Check renewal path privately, never bypass TLS |
| Abuse / authorization | Warn any unexpected cross-account access; critical any confirmed data exposure; warn 5 unexpected 429s/5 min or clustered 401/403s | Stop admission for exposure; distinguish expected negative UAT from abuse |

Do not stress the pilot to trigger alarms. Inject faults on an isolated staging host/data set, use synthetic metrics for delivery tests, and use only read-only probes on production. Threshold tuning requires recorded owner approval and preserved original alert evidence.

## Operator command reference

The following are read-only Linux diagnostics for an approved host. Substitute reviewed installed unit names and paths; do not paste env values. Run them only through the approved private operator channel. `journalctl` output is private until reviewed/redacted.

```sh
systemctl status <api-unit> --no-pager
systemctl status nginx --no-pager
systemctl list-timers --all --no-pager
journalctl -u <api-unit> --since '-15 minutes' --no-pager
journalctl -u <worker-unit> --since '-30 minutes' --no-pager
nginx -t
df -h
df -i
free -m
curl --fail --silent --show-error --max-time 10 https://<approved-host>/api/v1/health
curl --fail --silent --show-error --max-time 10 https://<approved-host>/api/v1/ready
```

A perimeter may require a private probe path or approved monitor identity; never remove the perimeter to make `curl` pass. Do not put credentials in command arguments/history. A local readiness request to loopback can help distinguish proxy failure only if actual trusted-host configuration permits its reviewed Host header. No command here installs services or changes DB state.

## Incident procedures

For every incident: record UTC detection time, release ID and sanitized symptoms; name an incident lead; stop new admissions; notify the approved owner through the pre-agreed channel. Choose maintenance/stop-writer controls appropriate to the actual host, including workers/timers and automatic restarts. Do not continue mutating actions when target identity, backup safety or integrity is uncertain. Record timeline, approvals, checks and reconciliation before reopening. State-changing steps below require the previously approved incident authority; this document grants none.

### Backend unavailable or restart loop

1. Check external TLS/proxy, then process liveness and the API unit state. Inspect bounded sanitized journal entries, disk/inodes, OOM events and last release/configuration change.
2. Check configured loopback bind/port and service working directory/permissions without displaying secrets. Production startup can fail closed on invalid DB/TLS/origin/host configuration; do not weaken guards to start it.
3. Keep traffic gated. After identifying a transient cause, permit one controlled restart under the approved procedure and check both probes. Repeated restarts without a cause require escalation.
4. For a bad release follow failed-deploy procedure. Reopen only after readiness and role smoke checks pass and worker state is known.

### Database unavailable / readiness 503

1. Liveness 200 with readiness 503 is an outage for business traffic. Gate writes and worker runs; preserve errors as classes/codes, not connection strings.
2. Check private DB service status, storage/connections, connectivity from the application network, DB hostname, certificate CA/expiry and configured TLS verification. Validate exact target identity through approved read-only diagnostics.
3. Distinguish connectivity from wrong revision/missing schema. Do not run migrations as a connectivity fix, disable certificate checks, point at the original local DB or widen public 5432 ingress.
4. DB owner repairs the confirmed cause. Verify revision `0008`, application projections, readiness and a synthetic approved-target smoke test before enabling writers. Suspected corruption follows restore procedure.

### Nginx 502 / application 503

1. Classify responses: Nginx 502 usually indicates upstream reachability/protocol/timeout; application 503 can indicate storage failure. Use proxy status and sanitized error class, not status alone.
2. Compare proxy health, direct loopback API health, readiness and service bind/port. Check API-prefix forwarding, socket access, timeout and upstream restarts; validate reviewed config with `nginx -t`.
3. Revert only the identified reviewed config/artifact under release authority. Do not increase timeouts indefinitely, expose 8000 publicly or retry an uncertain checkout with a new idempotency key.
4. Verify SPA deep links, `/api/v1` routing and readiness through HTTPS before reopening.

### Failed migration

1. Keep maintenance barrier active across API, workers, timers and restarts. Record command exit, script hashes, expected/current revision and target identity without secrets.
2. Stop immediately. Inspect read-only revision/schema/constraint and transaction outcome; a failed command is not proof that no effect occurred. Preserve the pre-migration backup and evidence.
3. Migration owner chooses a reviewed forward repair or new-target restore after reconciling partial effects. Never blindly rerun, `stamp`, `create_all`, downgrade or reset tables.
4. Pin reviewed expected revision `0008` rather than an unreviewed moving head. Verify business/audit invariants for the approved data set and coordinated application compatibility before starting writers.

### Disk full / inode exhaustion

1. Gate writes and scheduled work; check filesystem and inode usage. Identify largest categories with approved private diagnostics, including logs, artifacts and DB storage.
2. Do not delete DB files/WAL, backups, audit evidence or arbitrary directories. Never run recursive cleanup based on an unchecked path.
3. Storage owner approves bounded log retention/rotation, removal of confirmed disposable artifacts or capacity change after checking safe absolute paths and backup status.
4. Verify DB health, log writing, free space headroom and workers before reopening. Track the growth cause and alarm recovery.

### TLS expired / chain or hostname invalid

1. Close pilot access; tell participants to stop attempts. Do not offer HTTP, browser bypasses or `curl -k` as recovery.
2. Verify certificate hostname, expiry, chain, host time, renewal-unit history and domain-validation path. Preserve whole-site access restrictions.
3. Authorized certificate operator renews/replaces and validates Nginx configuration before controlled reload. No private keys in evidence or tickets.
4. Validate from participant devices and approved monitor, including redirect/chain/hostname, renewal alarm and remaining lifetime before reopening.

### Failed deployment / incompatible artifact

1. Stop admissions and preserve previous immutable artifacts, config revision and pre-release DB backup. Check whether a migration or any post-release write occurred.
2. If schema/data compatibility is proven unchanged, authorized release owner may switch frontend/backend together to the retained compatible artifact and configuration, then validate probes and smoke tests.
3. If schema changed, traffic wrote data or compatibility is uncertain, keep maintenance and choose forward repair or approved recovery. Code rollback is not database rollback; never run an automatic downgrade.
4. Reconcile uncertain checkouts using their original keys and current order state. Record release rejection and rerun the gates on the repaired artifact.

### Restore required

1. Recovery owner declares the incident and obtains cutover approval after stating anticipated data loss against approved RPO/RTO. Stop writers, workers and automatic restarts; preserve newer business/audit/outbox evidence privately.
2. Select a verified encrypted backup/PITR point and verify checksums/catalog and exact source/target identity. Restore to a new isolated target, never overwrite the original or active DB during diagnosis.
3. Follow the [backup/restore plan](PRODUCTION_BACKUP_RECOVERY.md); recover roles/grants/configuration separately where the backup does not contain them. Verify revision, constraints, counts, sequences, application projections and scoped synthetic smoke tests.
4. Measure restore duration and recovered point. Reconcile post-backup orders, disputes, audits, quotas and mail; restoring cannot unsend emails or reverse direct arrangements. Do not claim duplicate-free SMTP delivery.
5. Only the recovery/release owner approves coordinated connection/artifact cutover and reopening after integrity checks. Retain old target protected for investigation according to the approved retention policy.

### Security incident / suspected cross-account exposure

1. Stop admission and affected access immediately through the approved perimeter; preserve minimal evidence, timestamps and release ID privately. Do not test exposure with real user data.
2. Security lead determines affected routes/accounts/data and contains using approved service/access controls. Account suspension blocks active-user checks, but admin suspension requires a trusted operator process. Browser logout does not revoke a copied JWT before expiry.
3. Credential rotation, token invalidation strategy, forensic collection and external notices require explicit incident authority and a concrete reviewed plan. Do not print, send or casually replace secrets. Do not delete audit records or restore over evidence.
4. Owner evaluates participant communication and applicable reporting obligations with appropriate advisers; this runbook is not legal advice. Track scope, cause, repair, verification and required follow-up.
5. Reopen only after authorization/privacy regression checks, approved recovery/reconciliation and release-owner sign-off. A suspected data leak is a NO-GO until assessed.

## Worker and mail operation

The implemented entry points are `python -m app.workers process-email`, `auto-complete` and `expire-properties`, from `backend` with the approved target configuration. They perform writes and are **not diagnostic commands**. This preparation does not run them against the original DB. Proposed timer cadences appear in the alert table; installed timers, mutually safe maintenance controls, exit capture and missed-run alerts need witnessed evidence.

Disabled mail returns zero without consuming attempts and leaves backlog pending. SMTP uses TLS and bounded leases/attempts/backoff. An expired crash lease can recover; an exhausted lease becomes FAILED. Diagnose provider configuration, private network and sanitized failure codes before deliberate retry; no dead-letter reset UI exists. SMTP send/ack failure can yield a bounded duplicate: Message-ID is not a delivery guarantee. A successful worker exit/count proves processing, not inbox receipt; use consenting pilot mailboxes and record a redacted receipt timestamp.

Auto-completion only processes eligible undisputed delivered orders; default grace is 24 hours and the deadline is persisted at delivery. Do not shorten production deadlines for testing. Property expiry hides listings in queries immediately; a worker run emits reconfirmation evidence and preserves confirmed appointments. Quota cleanup is not implemented: monitor growth and approve retention before designing cleanup.

## Evidence before opening or reopening

- Named operator receives a safe test alarm and a recovery notification; delivery/acknowledgement timestamps recorded.
- External HTTPS, liveness and readiness tested independently; DB failure and worker missed-run detection rehearsed on isolated staging.
- Actual sanitized logs inspected, retention/disk caps configured, no sensitive bodies/coordinates/tokens collected.
- Restorable encrypted backup/PITR, measured new-target restore, numeric owner-approved recovery objectives and reconciliation checklist accepted.
- Five-user HTTPS acceptance evidence and all Critical/High gates accepted; release owner signs the exact artifact/configuration.

All items above are **NOT VERIFIED for production** until linked evidence, owner and date are added. Local automated test passes are supporting regression evidence only.
