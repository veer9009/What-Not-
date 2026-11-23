# Automated beta deployment preparation

This implementation supplies read-only preflight checks and ordered deployment
plans. **Live deployment is deliberately unavailable.** `deploy-beta.sh --apply`
always returns nonzero with `BLOCKED`; completing inventory, editing evidence or
supplying a forged `PASS` report cannot enable it. There is no confirmation prompt
because no live operation is implemented. A future reviewed implementation must
require an independent human confirmation before its first mutation.

No EC2 inspection, live database connection, migration, service restart, Nginx
reload, or runtime all-flow verification was performed to prepare these tools or
this document. Historical operator-supplied EC2 results are historical evidence,
not fresh verification. See [local automation results](AUTOMATION_TEST_RESULTS.md)
for checks actually run and [rollback requirements](AUTOMATED_BETA_ROLLBACK.md).

## Target and unresolved contracts

The following is operator-supplied context to verify on EC2, not discovered state:

| Item | Expected target |
| --- | --- |
| Public host | `avetest.online` |
| Existing checkout / branch | `/home/ubuntu/What-Not-`, `feature/open-beta-registration` |
| Existing rehearsal directory | `/home/ubuntu/whatnot-predeploy-20261123` |
| New release directory convention | `/home/ubuntu/What-Not-releases/<approved-full-commit>` |
| Database / transition | `whatnot_pilot_beta`, exactly `0010` to `0012` through `0011` |
| Runtime | PostgreSQL 18, Python 3.14.4; verify exact installed versions |
| Pilot service / upstream | `whatnot-pilot-api.service`, `127.0.0.1:8001` |
| Additional service | `whatnot-api.service`, port `8000`; establish whether it writes |
| Active Nginx configuration / web root | `/etc/nginx/sites-available/default`, `/var/www/html` |
| Encrypted credential loader | `/usr/local/lib/whatnot-pilot/pilot_asgi.py`, `LoadCredentialEncrypted` |

Repository templates use a different service/root arrangement and port `8000`.
Do not install them over the observed pilot configuration. The checker does not
modify source, migrations, service configuration, Nginx configuration or web root.

The loader's reviewed source/fingerprint, accepted credential-name allowlist,
ownership, permissions and exact activation contract have not been supplied. Do
not decrypt credentials for a report, copy plaintext into `.env`, invent a
loader, dump a service environment, or print credential files. Obtain reviewed
non-secret fingerprints and references through a protected channel.

Reconcile all six EC2 files against a reviewed release, recording hashes and
provenance. Resolve intended differences before preflight: the release and
rehearsal copies must be byte-identical for every listed file. Separately valid
but unequal digests fail the reconciliation gate:

- `backend/app/core/config.py`
- `backend/app/services/abuse.py`
- `backend/tests/persistence/conftest.py`
- `backend/tests/persistence/test_beta_authentication.py`
- `backend/tests/test_beta_auth_configuration.py`
- `backend/tests/test_open_beta_registration.py`

The last file is absent from this local checkout. Local production settings still
require an explicit beta account allowlist and abuse controls. These tools do not
implement or prove open registration. Do not weaken those settings to make a gate
pass. Reviewed source reconciliation and behavioral acceptance remain necessary.

## Command classes and handling

**READ-ONLY** means no mutation of live application/data/configuration. Preflight
reads host/Git/database metadata and writes private reports; its isolated tests
also write temporary artifacts. **ISOLATED TEST** means disposable code, databases
and outputs, with no live credentials, SMTP delivery, uploads or worker access.
**LIVE CHANGE** includes maintenance controls, migrations, service changes,
activation and synthetic requests that write production data. No LIVE CHANGE is
implemented by the entrypoints.

Run Linux Bash entrypoints from the reviewed automation checkout on the intended
host using its intended operator account. They do not SSH to EC2. Do not run the
entire checker as root or relax permissions to satisfy a failed gate. Review code
before execution: tests execute candidate code. An approved immutable clean
release and sanitized test environment are required even for isolated tests.

Start from `deploy/automation/inventory.example.json`. Its placeholders
intentionally block. Put the completed inventory outside the repository at an
approved absolute protected path, and keep its parent directory and report
directory private to the authorized operator (directory mode `0700`, files
`0600`). Inventory/evidence must use absolute canonical regular paths owned by
root or the operator; parent directories must prevent replacement by another
user (sticky shared parents are permitted by the checker). The report directory
must already exist, belong to the operator, and be outside release, live,
rehearsal, frontend, rollback and backup trees. Fixed exclusions also forbid
reports anywhere under `/home/ubuntu/What-Not-`,
`/home/ubuntu/whatnot-predeploy-20261123`, `/home/ubuntu/What-Not-releases`,
`/var/www`, `/etc` and `/usr/local/lib/whatnot-pilot`, even with invalid inventory.
Do not commit inventory, credentials, backup archives or private evidence. Do not source JSON or
add executable shell hooks. Supported checks are fixed in reviewed code.

Bind inventory/evidence to the exact full release commit, machine/operator,
database identity, schema, configuration/loader fingerprints and UTC collection
times. Evidence references need SHA-256 checksums, protected regular files,
reviewed provenance, freshness and the applicable target identity. A hash detects
changed bytes; it does not establish that a claim is true. An operator-written
JSON success flag or reported revision is not a restore or compatibility test.
Reports intentionally contain gate/status metadata and hashes, not raw command
output, secrets, connection strings or business records. Keep diagnostic details
in a separately protected operator channel; never paste them into public logs.

READ-ONLY preflight (with private report and temporary-test writes):

```bash
bash deploy/automation/preflight.sh \
  --inventory /protected/inventory.json \
  --report-dir /protected/reports
```

Normal invocation always exits `2`. Preflight stops at the first `FAIL`, marks
later gates `BLOCKED`, and always appends `live_adapter: BLOCKED`; overall status
is `FAIL`, even if earlier gates pass. No preflight `PASS` is possible in this
version. Interruption exits `130`. Review failures without replacing results.

With valid protected input on supported Linux, stdout JSON contains fixed checks
and a generated report basename, `whatnot-preflight-<UTC>-<id>.json`. The saved
report is mode `0600` and binds inventory hash and release SHA. Invalid input,
unsupported hosts or report-write failure produce a fixed failure message and
may produce no report. Use the actual generated path below; `report.json` is
illustrative.

Dry-run deployment plan:

```bash
bash deploy/automation/deploy-beta.sh \
  --inventory /protected/inventory.json \
  --preflight-report /protected/reports/report.json
```

Dry-run and `--apply` both exit `2` and report `BLOCKED`. Neither performs a
deployment, including when a report claims `PASS`. The printed ordered plan is
descriptive; the CLI does not execute its stages. JSON includes a UTC timestamp,
`steps_executed: false`, and `preflight_report: "BOUND_FAIL_REPORT"` or
`"INVALID_OR_MISSING"`. Report binding requires protected inventory/report files,
`format_version: 1`, `operation: "preflight"`, matching full release SHA and
inventory SHA-256, timezone-aware creation within the last hour (not in the
future), and `status: "FAIL"`. This version never emits `PASS`, so a fabricated
`PASS` report is rejected. Binding a failure report establishes association and
freshness only; it cannot authorize mutation or unlock live operations.

Preflight covers fixed host/operator checks, clean approved release, observed live
state, reconciliation, read-only PostgreSQL identity/revision, configuration
fingerprints, capacity and backup/restore/rollback evidence. Tests use temporary
`git archive` tracked-file snapshots, reject real `.env` files, scrub live
environment settings and copy installed `node_modules` into the temporary
snapshot. Copies allow at most 1 GiB of real-file bytes and preserve only relative
symlinks resolving inside that dependency tree; absolute/escaping links block.
Vite's temporary writes stay in the copy. Release Python runs backend
`pytest tests` excluding `tests/persistence`
and `tests/session_integration`, without pytest cache. Frontend Vitest runs `src`
with threads, one worker, no file parallelism and no cache. Artifact hashes are
checked separately; preflight does not run a production build. This is environment
isolation, not an OS network/filesystem sandbox: reviewed candidate code remains
trusted and can access the host. The test review must establish no live network
or database access.
On Ubuntu, probe captures and test snapshots use the explicitly checked `/tmp`,
ignoring ambient `TMPDIR`, `TEMP` and `TMP`. Test subprocess temporary paths point
inside the snapshot. Git filter inspection includes effective worktree settings.
The clean approved release is validated before its virtualenv is executed.
Configured Git filters are rejected, and Git optional locks are disabled. Tool
checks require Python 3.14.4, successful `pip check`, and installed package metadata
matching every exact pin in the release's `backend/requirements.txt`; these checks
do not install or upgrade dependencies.
It does not run PostgreSQL integration suites or mutation-based live smoke tests.
Local mock tests establish guard behavior; they do not establish the EC2 runtime
contracts or prove a successful upgrade.

The Nginx gate hashes the complete effective `sudo -n nginx -T` output and checks
the active `default` symlink. It conservatively requires every `proxy_pass` to
target `http://127.0.0.1:8001`, plus `avetest.online`, `/var/www/html`, `blob:` and
`client_max_body_size 5m`. Regex checks do not parse inheritance and may reject
unrelated sites. They require image/CSP changes already installed: a current
configuration awaiting that planned change fails. Resolve this through separate
review of an approved Nginx change or checker revision; no automatic installation
occurs. Repository port-8000 templates remain unchanged.

## Inventory and evidence fields

Use JSON `format_version: 1`. Replace example placeholders only with independently
reviewed facts, never values invented to progress a gate:

| Inventory fields | Required meaning |
| --- | --- |
| `operator`, `machine_id` | `ubuntu`, exact 32-character lowercase hex machine ID |
| `release_commit`, `release_path`, `release_python` | Full 40-character lowercase hex SHA, canonical separate release directory, Python executable inside it; Python exactly 3.14.4 and successful `pip check` |
| `live_path`, `live_commit`, `live_state_sha256` | Exact live directory, observed full commit and checker-compatible digest of status, binary diff and untracked names/content; preserve dirty files |
| `rehearsal_path`, `domain`, `upstream`, `frontend_root` | Fixed target values listed above |
| `nginx_sha256` | Reviewed SHA-256 of exact effective `sudo -n nginx -T` output |
| `pilot_unit_sha256`, `secondary_unit_sha256` | SHA-256 of each unit's `systemctl show` output with properties `FragmentPath,DropInPaths,User,WorkingDirectory,ExecStart,LoadCredentialEncrypted` |
| `loader_sha256` | Reviewed existing loader hash; loader is never invoked |
| `minimum_free_bytes`, `backup_directory` | Integer at least 5368709120 and existing private backup directory; capacity checked on release, backup and frontend filesystems |
| `deployment_state`, `journal_path` | Exactly `never_started`; absolute journal path that does not exist |
| `rollback_path` | Reviewed separate rollback worktree path, exactly matching rollback evidence `path` |
| `database` | Exact `name`, positive integer `oid`, cluster `system_identifier`, `server_addr`, integer `server_port`, existing approved `role`, `revision: "0010"`, `major: 18`, `service`, `service_file`, `pass_file` |
| `evidence` | Entries `reconciliation`, `credentials`, `backup`, `rollback`, `maintenance`, `frontend`, `isolated_tests`, each with protected absolute `path` and lowercase 64-character `sha256` |

Use existing approved read-only PostgreSQL service/password files, protected as
above. Service names allow letters, digits, `_` and `-` (1–64 characters). The
fixed `psql` probe forces read-only transactions and short timeouts and checks
database/role/server/OID/cluster identity and exact revision. `pg_control_system()`
needs an existing suitably authorized role; missing permission blocks. Do not
grant broad privileges or create unsafe credentials to bypass it. `psql` and
`pg_restore` must be version 18. Windows is rejected before any database probe.
Systemd credentials are never decrypted.

Every evidence JSON object requires matching `release_commit`, `status: "PASS"`
and nonempty `review_id`. Additional checked fields are:

| Evidence | Required additional fields |
| --- | --- |
| `reconciliation` | `files` contains exactly the six paths above, each with matching `release_sha256` and `ec2_sha256` for release/rehearsal copies; `open_beta_registration_reviewed: true`, `abuse_protection_reviewed: true` |
| `credentials` | `loader_unchanged: true`, `recovery_email_enabled: false` |
| `backup` | `database` equals the entire inventory database object; `revision: "0010"`, `restore_status: "PASS"`, `restored_database` differs from live name, `business_counts_match: true`, `archive_integrity_verified: true`; timezone-aware `created_at`, `restored_at`, with creation within 24 hours and creation ≤ restore ≤ current UTC; protected `archive_path` directly inside `backup_directory` and matching `archive_sha256` |
| `rollback` | Canonical clean separate `path` exactly matching inventory `rollback_path`, matching full `commit`, `schema: "0012"`, `revision_only_change: false`, `isolated_database` differs from live name; `passed_checks` includes `readiness`, `authentication`, `sessions`, `buyer`, `seller`, `admin`, `business_preservation`, `audit_preservation`, `recovery_preservation`; protected `test_evidence_path` and matching `test_evidence_sha256` |
| `maintenance` | `writer_units` includes both API units; nonempty reviewed strings `traffic_barrier`, `all_writers`, `restart_paths`, `quiescence_probe`, `resume_procedure` |
| `frontend` | Canonical artifact `path` differing from live frontend root, `production: true`, `api_base: "/api/v1"`; `files` maps every artifact-relative path to SHA-256 including `index.html`, at least one `.js` and `.css`; no symlinks or extra/missing files |
| `isolated_tests` | `no_live_network_or_database: true` based on actual candidate test review |

These fields validate assertions, not their truth. Maintenance strings implement
no barrier; credential evidence does not prove loader compatibility. The backup
gate lists the archive but does not restore it: review must substantiate the
restore. The history gate requires fresh `never_started` state, no journal and
distinct live/release commits. Interrupted/repeated deployment states block;
there is no automatic resume, journal overwrite, or implemented migration/startup
failure handler.

## Release preparation before any future live implementation

The current local base `678a7e04fc9b6cb0bb19e1ea1553234f5c6e5aed` predates these
automation files. It is not an approved automation release. After review, the user
must commit the intended changes, inspect the full commit and choose its immutable
SHA. Require a clean source checkout and a clean detached release worktree.
Do not use a moving branch name as release identity.

On EC2 only, after separately authorizing repository access, credential scope and
the approved source/commit, a future operator may prepare a dedicated release.
The following is a preparation example, not a command run by this task. Validate
the literal full SHA and trusted remote before substituting it:

```bash
# READ-ONLY for live application; fetch writes the repository Git object store.
case "$(git -C /home/ubuntu/What-Not- remote get-url origin)" in
  'https://github.com/veer9009/What-Not-.git'|'git@github.com:veer9009/What-Not-.git') ;;
  *) printf '%s\n' 'STOP: origin requires private review'; exit 2 ;;
esac
git -C /home/ubuntu/What-Not- status --porcelain=v1 --untracked-files=all
git -C /home/ubuntu/What-Not- fetch origin feature/automated-beta-deployment
git -C /home/ubuntu/What-Not- rev-parse --verify FETCH_HEAD
# STOP unless FETCH_HEAD equals the independently approved full commit.
# ISOLATED TEST preparation: replace both placeholders with that same full SHA.
git -C /home/ubuntu/What-Not- worktree add --detach \
  /home/ubuntu/What-Not-releases/<approved-full-commit> <approved-full-commit>
git -C /home/ubuntu/What-Not-releases/<approved-full-commit> status --porcelain=v1 --untracked-files=all
git -C /home/ubuntu/What-Not-releases/<approved-full-commit> rev-parse HEAD
```

The angle-bracket placeholders are not executable Bash values; replace them only
after review. Choose the approved branch explicitly if it changes. Inspect dirty
live files without altering them. Never `pull`, `reset`, `clean`, checkout another
branch in, or overwrite `/home/ubuntu/What-Not-`. Do not reuse/erase the rehearsal
directory. Refuse an existing release path, mismatched SHA, dirty candidate or
unknown remote. Fetch changes repository metadata even though it preserves live
working files; it requires its own reviewed credentials and scope.

## Required future sequence; currently blocked

1. Independently verify host/account, live branch/commit/dirtiness, service and
   listener mapping, active Nginx target/root, database name/address/port/OID/role,
   PostgreSQL 18 tools and Python 3.14.4. Record non-secret fingerprints. Resolve
   every discrepancy, including the six files and encrypted loader contract.
2. Prepare the clean immutable detached release and matching backend/frontend
   artifacts. Run sanitized unit/build checks. Separately rehearse the real
   `0010 -> 0011 -> 0012` migrations against an isolated restored database using
   PostgreSQL 18 and the real Python runtime, without live keys or outbound mail.
3. Exercise restoration and schema-0012-compatible rollback behavior in isolation;
   see the rollback document. Verify adequate disk/memory for backup, restore,
   artifact retention and both runtime candidates. Keep the old paired artifacts.
4. Review a concrete change plan and evidence; obtain independent human
   confirmation **before the first LIVE CHANGE**, including enabling maintenance
   or stopping a writer. Implemented automation currently stops before this point.
5. Establish the reviewed maintenance/write barrier for every API, worker, timer,
   scheduled job and other client, including the service on port `8000`. Confirm
   in-flight work and database writers have drained. A maintenance web page or
   stopping just the pilot unit is insufficient. Keep the barrier on failure.
6. With all writers quiesced, capture the final consistent PostgreSQL-18 backup,
   encrypted and protected, with bytes/hash/snapshot times and database identity.
   Verify private off-host storage and restore the exact backup into an isolated
   target. Validate constraints, grants, schema and application behavior. If a
   pre-maintenance rehearsal was used, explicitly resolve its recovery point and
   obtain final-backup restore evidence; no checksum-only substitute. Keep the
   barrier throughout the final consistency interval. Do not permit writes
   between the recovery snapshot and migration/activation.
7. Recheck identity, revision exactly `0010`, source/artifact/configuration hashes,
   writer barrier and backup evidence immediately before mutation. A stale
   preflight report cannot authorize this. Use the reviewed migration identity
   and exact target `0012`; never `stamp`, `create_all`, unreviewed `head` or
   startup auto-migration. On uncertain/interrupted migration inspect actual
   transaction/schema state; never retry blindly.
8. Activate through the separately reviewed encrypted-loader/service/web-root
   mechanism. Preserve credential protections and existing proxy boundaries.
   Test Nginx configuration before any authorized reload. Verify backend/frontend
   pairing, readiness on `8001`, TLS/proxy headers and the public hostname.
9. Under a controlled maintenance exception, perform separately authorized
   synthetic flows: registration/admission, login/refresh/logout, recovery and
   revocation, seller/provider onboarding, location/consent, images and limits,
   moderation/discovery, checkout where supported, authorization and admin flows.
   Verify privacy, negative cases and worker supervision. These requests write
   data and may send mail; define approved records, recipients and cleanup first.
10. Admit traffic only after reviewed acceptance. Monitor sanitized health/error,
    worker/backlog and capacity signals with a defined observation window and
    incident owner. If acceptance fails, preserve evidence and use only a proven
    schema-compatible rollback under the barrier. Do not restore/downgrade live.

Any missing contract or failed gate leaves deployment blocked. This document is
preparation for a later reviewed implementation, not evidence of a working live
deployer or a completed beta rollout.
