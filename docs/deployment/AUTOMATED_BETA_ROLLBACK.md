# Automated beta rollback preparation

**Rollback is deliberately unavailable.** `rollback-beta.sh` prints a dry-run
plan; `--apply` always returns nonzero with `BLOCKED`. Inventory fields, evidence
or a fabricated `PASS` report cannot unlock a live action. No rollback,
downgrade, restore, service restart or traffic change was performed by this task.
See [deployment prerequisites](AUTOMATED_BETA_DEPLOYMENT.md) and
[actual local verification](AUTOMATION_TEST_RESULTS.md).

The intended recovery mode is a tested application/artifact rollback that keeps
the live database at schema `0012`. Never automatically downgrade, restore over
the live database, delete recovery history, stamp a revision or weaken readiness
to make an older application start. A separate disaster-recovery decision must
address data loss, session validity, key retention and isolated restoration.

## Why an old commit alone is insufficient

The supplied live database context is `whatnot_pilot_beta` at `0010`, with a
proposed migration through `0011` to `0012`. Local migrations add password recovery
and encrypted recovery-delivery tables. Both guarded downgrades refuse retained
history. Even terminal delivery rows prevent downgrade. Do not delete rows to
bypass those guards.

The prior recovery runbook records an older build expecting exact revision
`0010`, while this candidate expects `0012`. That older build is not a usable
rollback candidate merely because its code is still on disk. Changing only an
expected-revision constant proves no functional compatibility. Require a reviewed
rollback build and its matching frontend/configuration, exercised against actual
migrated PostgreSQL-18 schema `0012` using Python 3.14.4.

Rollback evidence must bind the full immutable commit, paired artifact hashes,
schema, runtime/dependency versions, reviewed loader/configuration fingerprints,
isolated target identity, commands/results and UTC times. Require independently
reviewed SHA-256-bound protected evidence; a JSON success flag is only an
assertion. Keep personal data, passwords, tokens, keys, SMTP secrets and raw
connection strings out of reports and repository files.

## Evidence required before a future rollout

- Restore the specific encrypted backup into a uniquely identified isolated
  database; verify hashes, restore exit status, schema/constraints, ownership,
  grants and application usability. A listing/checksum alone is insufficient.
- Rehearse the real `0010 -> 0011 -> 0012` migration. Run both the deployment
  candidate and rollback candidate against the resulting database in isolation.
  Use no production credentials or live outbound integrations.
- Prove readiness and representative behavior on `0012`: authentication,
  admission/allowlist policy, refresh and logout, recovery expiry/replay/reset,
  all-session revocation, existing account/data access, seller/provider and
  moderation flows, images, location/privacy and checkout where supported.
  Include negative authorization cases and active/pending/terminal recovery work.
- Verify the rollback build safely handles existing recovery/delivery rows,
  key versions, queued/leased work, worker restart and disabled/enabled feature
  settings. Preserve independent signing, HMAC and encryption key contracts.
  Define whether sends remain suspended during rollback and how they resume.
- Prove matching frontend/backend artifacts, the encrypted loader and
  `LoadCredentialEncrypted` allowlist, service ownership/permissions and
  activation/reversion behavior. These EC2 contracts are currently missing.
- Rehearse interruption at each activation boundary and a second invocation.
  Capture actual artifact/service/schema state and recovery decisions. Never
  infer idempotence or successful activation from a prior report.

Historical manual EC2 tests supplied by the operator do not establish these fresh
contracts. Local automation guard tests and non-database application tests are
not functional schema-0012 rollback evidence.

## Dry-run interface

Run from the reviewed automation checkout on the intended Linux host. It does not
SSH or acquire a new remote session. First run the read-only preflight described
in the deployment document, using protected inventory/report paths:

```bash
bash deploy/automation/preflight.sh \
  --inventory /protected/inventory.json \
  --report-dir /protected/reports
bash deploy/automation/rollback-beta.sh \
  --inventory /protected/inventory.json \
  --preflight-report /protected/reports/report.json
```

Preflight stdout provides a generated report basename only when protected input,
Linux support and report writing permit it. Its directory must already exist,
be private `0700`, belong to the operator and sit outside live/release/rehearsal/
frontend/rollback/backup trees and the fixed excluded roots listed in the
deployment document; report files are `0600`. Use that actual path, rather than the
illustrative `report.json`. The deployment document specifies every inventory
and evidence field, ownership rule and test limitation.

Default behavior is dry run; dry-run and `--apply` both exit `2` with `BLOCKED`.
The printed plan executes no live stages. Preflight also normally exits `2`,
stops at the first failed gate and marks later gates blocked. Its final
`live_adapter` is always blocked, so no overall `PASS` is possible. Interrupted
preflight exits `130`. `--apply` is a permanently blocked placeholder in this
version. There is no confirmation prompt, because no live action exists. A later
implementation must require fresh independent human confirmation before its
first LIVE CHANGE, including maintenance controls or stopping workers. A preflight
report is never that confirmation.

The CLI checks the provided protected preflight report's format/version,
operation, full release SHA, inventory hash and UTC freshness (at most one hour,
never in the future). It requires `status: "FAIL"` because this version cannot
emit `PASS`. JSON reports `preflight_report: "BOUND_FAIL_REPORT"` when bound or
`"INVALID_OR_MISSING"` otherwise, alongside a UTC timestamp,
`steps_executed: false` and `BLOCKED`. Even a fresh correctly bound report cannot
enable rollback; a forged `PASS` is rejected. The rollback evidence path must
exactly match inventory `rollback_path`.

The history gate only accepts `deployment_state: "never_started"`, no existing
journal and different live/release commits. A recorded interruption or repeated
deployment state blocks; there is no automatic resume or journal overwrite.
Guard tests of these states do not implement full migration/startup failure
handlers. Inventory maintenance strings and reviewed evidence do not supply the
missing EC2 activation or writer-barrier integration.

READ-ONLY checks may write protected reports; ISOLATED TEST checks may write only
disposable test outputs. LIVE CHANGE includes maintenance, writer controls,
artifact/service activation and mutation-based smoke requests. Do not invent
shell hooks, source the inventory or place credential values in command arguments.

## Required future incident sequence; currently blocked

1. Keep or establish the separately reviewed maintenance/write barrier after
   independent human confirmation. Include `whatnot-pilot-api.service` on `8001`,
   `whatnot-api.service` on `8000` if it writes, all workers/timers and other
   clients. Drain active requests, sends and database writes. Do not restart a
   failed candidate automatically or admit users during uncertainty.
2. Preserve the failed release, sanitized logs, private reports and interrupted
   operation state. Identify the exact host/account, current backend/frontend,
   active Nginx configuration/root, loader/service fingerprints and actual
   database identity/revision. Do not assume migration failed atomically or that
   an activation completed. Dirty live checkout files remain untouched.
3. If schema is not exactly the rollback candidate's proven `0012` target, STOP.
   Resolve actual state through a separately reviewed incident plan. Do not
   downgrade, stamp, retry migration or restore automatically. If no proven
   rollback build exists, remain in maintenance and investigate a reviewed fix.
4. While quiesced, capture and protect a fresh consistent backup of current state
   and verify the exact recovery artifact and its isolated restore evidence.
   Preserve post-deployment writes and recovery history. Bind final evidence to
   the fresh state; an earlier preflight or pre-migration backup alone cannot
   prove the recovery point. Keep the barrier through the final consistency
   interval and activation.
5. Revalidate the immutable clean rollback worktree and matching backend/frontend
   hashes, real schema-0012 functional evidence, capacity, credential-loader
   contract, configuration and destination. Never modify the dirty live checkout
   or reuse/erase `/home/ubuntu/whatnot-predeploy-20261123`. Retain candidate and
   rollback artifacts separately under approved release paths.
6. Use the separately reviewed activation mechanism to select the paired rollback
   artifacts while retaining schema `0012`. Keep encryption keys required by
   retained ciphertext and backup retention policy. Do not replace active Nginx
   `/etc/nginx/sites-available/default` or `/var/www/html` with repository
   templates, or start the port-8000 service as an unreviewed substitute.
7. Verify actual unit/upstream readiness on `127.0.0.1:8001`, exact schema,
   hostname/TLS/proxy boundaries and frontend/backend pairing. Rehearse and then
   separately authorize controlled synthetic write flows and recipients before
   using them on live data. Record only sanitized results.
8. Admit traffic only after acceptance by the incident owner. Monitor errors,
   authentication/session behavior, worker/backlog and resource use. Define the
   observation period and escalation owner beforehand. If validation fails,
   retain maintenance and investigate; do not loop blindly between builds.

An isolated backup restoration is a distinct approved recovery operation. It
does not authorize overwriting `whatnot_pilot_beta`, replaying real mail or
discarding newer writes. The implemented tools intentionally stop before any of
these live operations until the missing contracts and a reviewed implementation
exist.
