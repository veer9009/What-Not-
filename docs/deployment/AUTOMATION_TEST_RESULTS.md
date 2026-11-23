# Beta stabilization verification: 2026-11-23

## Current release decision: BLOCKED

Release-preparation branch: `release/beta-stabilization-20261123`, based on
`5e2d70f9b7367005de44370a25b4740ff90df338`. This is WIP engineering work,
not an approved deployable release. The final handoff supplies the full resulting
commit SHA and the verified GitHub push receipt; a report cannot embed its own
containing commit's SHA. No merge, EC2 access or deployment was performed.

`git fetch origin --prune` succeeded. The fetch refspec covers all branches;
`origin/feature/automated-beta-reconciled` is absent. The connected GitHub branch
API independently returned an empty result for that exact branch name. This is
the request's mandatory reconciliation blocker. The six authentication files
were left unchanged; `backend/tests/test_open_beta_registration.py` remains
absent locally. No replacement open-registration implementation was invented.

## Reviewed engineering change

The reconciliation gate previously accepted different release and EC2 rehearsal
source when each file matched its own separately recorded hash. It now requires
equal hashes as well as verifying the actual bytes. Seven new cases cover an
identical six-file set and a divergence in each individual file. Before the fix,
the divergent cases failed with `DID NOT RAISE Blocker`: 6 failed, 1 passed,
68 deselected. After the fix all 75 automation cases pass. An independent reviewer
reported no findings and independently reran the same 75 cases successfully.

Files modified (no new framework or application redesign):

- `deploy/automation/beta_automation.py`: reject unequal reconciliation hashes.
- `deploy/automation/tests/test_beta_automation.py`: seven regression cases.
- `docs/deployment/AUTOMATED_BETA_DEPLOYMENT.md`: clarify identical-copy contract.
- `docs/deployment/AUTOMATION_TEST_RESULTS.md`: this consolidated current handoff.

## Fresh local checks for this branch

Windows, Python 3.10.11, Node 24.20.0, PostgreSQL 17.11. Existing dependencies
were reused. Local logs are ignored and are not part of the commit. Commands
run from the repository root unless the table specifies `backend`.

| Check | Exact command | Current result |
| --- | --- | --- |
| Automation, including Bash syntax and blocked entrypoints | `backend/.venv/Scripts/python.exe -m pytest deploy/automation/tests -q --tb=short` | 75 passed, 0 failed, 0 skipped; independent rerun also 75 passed |
| Backend non-PostgreSQL | From `backend`: `.venv/Scripts/python.exe -m pytest tests --ignore=tests/persistence --ignore=tests/session_integration -q --tb=short` | 503 passed, 0 failed, 0 skipped |
| PostgreSQL persistence | From `backend`: `.venv/Scripts/python.exe -m pytest tests/persistence -q --tb=short --maxfail=1` | 461 passed, 0 failed, 0 skipped; PostgreSQL 17 temporary cluster |
| PostgreSQL sessions | From `backend`: `.venv/Scripts/python.exe -m pytest tests/session_integration -q --tb=short --maxfail=1` | 62 passed, 0 failed, 0 skipped |
| Frontend full retry | `node node_modules/vitest/vitest.mjs run src --config vite.config.ts --pool=vmThreads --maxWorkers=1 --no-file-parallelism --no-cache --reporter=verbose` | 458 passed across 49 files, 0 failed, 0 skipped |
| Focused admin retry | Same Vitest command, replacing `src` with `src/pages/AdminWorkspace.test.tsx` | 11 passed, 0 failed, 0 skipped |
| Both TypeScript projects | `node node_modules/typescript/bin/tsc -b` | Passed |
| Production build | `node node_modules/vite/bin/vite.js build --config vite.config.ts` | Passed; ignored local `dist` output, not a target-approved artifact |
| Installed backend dependency consistency | `backend/.venv/Scripts/python.exe -m pip check` | No broken requirements found |
| Scope and whitespace | `git diff --check`; diff of all six protected authentication paths against HEAD | Passed; protected paths unchanged |

Final distinct-suite total: **1,559 passed, 0 failed, 0 skipped**. The focused
admin retry and independent automation rerun are additional confirmations and
are not double-counted. Initial failed attempts are disclosed below.

The first persistence run encountered one setup error and stopped before running
a test: Windows `pg_ctl` could not create a restricted token (error 87). The retry
used the inspected fixture outside that restriction: its own newly initialized
temporary cluster, synthetic records and shutdown/cleanup, never the application
database. The separate session suite uses the existing designated test database
with exact name/OID/owner/endpoint guards and disposable schemas, as inspected in
its fixture. Neither is a restored copy of the live PostgreSQL 18 database.

The first frontend run used `--pool=threads` and reported one failure in
`AdminWorkspace.test.tsx::preserves service pagination offsets and refresh
requests` before stalling after that file (10 passed, 1 failed). It was stopped.
The focused retry passed without application or test modifications. The full
cache-disabled `vmThreads` retry is recorded separately above; the interrupted
run is not counted as a successful suite. No timeout or security control was
weakened. These are mocked-API frontend tests, not public browser smoke tests.

## Security, migration and rollback limits

The existing backend suites include authentication/role/object authorization,
session, abuse, recovery, upload and migration regressions. Source review covered
password hashing/token validation, role dependencies, upload ownership, CORS and
trusted-host middleware, automation and migrations. Passing these tests is not
an exhaustive security audit or proof of live configuration. Existing Argon2id,
JWT checks, database-backed roles, recovery and abuse controls were preserved.

`0011` creates password recovery records and indexes; `0012` creates encrypted
recovery delivery records, restrictive foreign keys, indexes and state/payload/
lease constraints. The upgrade functions contain additive DDL. Both downgrades
lock their new table and refuse to drop it if history exists. No migration,
downgrade, backup or restore was run against live data. Offline DDL regression
tests are part of the backend suite; any local persistence evidence is PostgreSQL
17 synthetic-data evidence only. PostgreSQL 18 migration of a protected restored
0010 database and rollback on 0012 remain BLOCKED.

## Required EC2 evidence and remaining work

1. Commit and push the existing six-file reconciliation from EC2 as
   `feature/automated-beta-reconciled`, after reviewing that it contains no secrets.
   Preserve both dirty EC2 worktrees. Then inspect and incorporate that commit
   into a new candidate and rerun the applicable suites. This WIP branch does not
   satisfy that prerequisite and must not be treated as the release base.
2. Supply protected, reviewed inventory and evidence for machine/operator and
   database identity, current live Git state, effective Nginx configuration,
   both systemd units, encrypted loader fingerprint and accepted settings.
3. Demonstrate a fresh protected backup, archive integrity and isolated restore
   with business counts; rehearse 0010 -> 0011 -> 0012 under PostgreSQL 18 and the
   actual target Python/dependencies. Verify all roles and preserved records.
4. Demonstrate traffic maintenance, every database writer and restart barrier,
   credential-loader-compatible activation, health checks, failure recovery and
   an application rollback that works on 0012 without losing new records.
5. Verify buyer/seller/admin flows on Ubuntu, image upload/delivery, recovery
   provider and worker configuration, mobile layouts and public HTTP behavior.

Full backend release: **BLOCKED**. The source-inspected Bash wrappers and inventory
are retained; live deploy and rollback are intentionally unavailable, including
with `--apply`. Dry-run outputs are ordered plans, not executed stages. The new
fix does not bypass or complete an unverified EC2 adapter.

Frontend-only release: **BLOCKED**. The local frontend builds, but the actual live
backend contract/source and recovery/session behavior have not been supplied or
compared. A live 0010 revision alone cannot establish compatibility. Therefore
no frontend activation, backup/replacement/restore command is approved or
implemented here. Compatibility, a protected current frontend backup, a reviewed
atomic publication mechanism and failure restoration must be demonstrated first.

## EC2 fetch and preflight commands (not executed)

These commands preserve the existing EC2 worktrees and only prepare a separate
candidate for review/preflight. First review this WIP commit and match the fetched
SHA against the exact full SHA in the final handoff. The protected inventory,
report directory and candidate dependencies must already be prepared according
to `AUTOMATED_BETA_DEPLOYMENT.md`; placeholders are not valid evidence.

```bash
set -euo pipefail
git -C /home/ubuntu/whatnot-automation-20261123 fetch origin
candidate_commit=$(git -C /home/ubuntu/whatnot-automation-20261123 rev-parse origin/release/beta-stabilization-20261123)
printf '%s\n' "$candidate_commit"
# STOP unless this equals the reviewed full SHA from the handoff.
```

Only after that explicit SHA review, in a separate shell step:

```bash
set -euo pipefail
read -r -p 'Full reviewed SHA from the handoff: ' candidate_commit
[[ "$candidate_commit" =~ ^[0-9a-f]{40}$ ]]
test "$(git -C /home/ubuntu/whatnot-automation-20261123 rev-parse origin/release/beta-stabilization-20261123)" = "$candidate_commit"
candidate_path="/home/ubuntu/What-Not-releases/$candidate_commit"
git -C /home/ubuntu/whatnot-automation-20261123 worktree add --detach "$candidate_path" "$candidate_commit"
bash "$candidate_path/deploy/automation/preflight.sh" \
  --inventory /home/ubuntu/.config/whatnot/beta-inventory.json \
  --report-dir /home/ubuntu/whatnot-protected-reports
```

An existing destination causes `worktree add` to fail; do not reset or remove it.
Preflight is expected to exit 2 and cannot certify this unreconciled WIP release.
No deployment commands are supplied because activation has not been verified.

Expected downtime from this work: none; no live endpoint or infrastructure was
changed. Future deployment downtime is unknown until writer quiescence,
migration duration, activation and rollback have been rehearsed. Remaining
operator effort includes one reviewed EC2 reconciliation commit/push, protected
inventory/evidence collection and target rehearsals plus engineering of the
verified adapter; it is not reduced to a single deploy command and cannot be
timed responsibly with the required inputs missing.

---

## Historical record: earlier automation implementation (not this run)

Local Windows verification only. No EC2 access, deployment, live migration,
credential decryption, service operation or infrastructure change was performed.
Base: `678a7e04fc9b6cb0bb19e1ea1553234f5c6e5aed`, branch
`feature/automated-beta-deployment`. All new work remains unstaged.

## Scope and current decision

Read-only preflight and descriptive deployment/rollback plans are implemented.
Live deployment and rollback are fail-closed placeholders, always returning
`BLOCKED`, even with `--apply` or a fabricated PASS report. Preflight always
includes a blocked live-adapter gate. This is not a working live deployer and
cannot be approved for live execution by filling out inventory alone.

## Fresh verification

All commands below are ISOLATED TEST unless marked READ-ONLY. Backend commands
run from `backend`; other commands run from the repository root.

| Check | Command | Result |
| --- | --- | --- |
| Automation safety and Bash entrypoints | `backend/.venv/Scripts/python.exe -B -m pytest deploy/automation/tests -q -p no:cacheprovider --tb=short` | 68 passed, 0 failed, 0 skipped |
| Backend non-PostgreSQL | `.venv/Scripts/python.exe -B -m pytest tests --ignore=tests/persistence --ignore=tests/session_integration -p no:cacheprovider -q -ra --tb=short` | 503 passed, 0 failed, 0 skipped |
| PostgreSQL sessions | `.venv/Scripts/python.exe -B -m pytest tests/session_integration -p no:cacheprovider -q -ra --tb=short` | 62 passed, 0 failed, 0 skipped |
| PostgreSQL persistence | `.venv/Scripts/python.exe -B persistence_schema_runner.py -p no:cacheprovider -ra` | 461 passed, 0 failed, 0 skipped |
| Frontend | `node_modules/.bin/vitest.cmd run src --config vite.config.ts --pool=threads --maxWorkers=1 --no-file-parallelism --no-cache --reporter=verbose` | 458 passed across 49 files, 0 failed, 0 skipped |
| Frontend TypeScript | `node_modules/.bin/tsc.cmd -p tsconfig.app.json --noEmit` | Passed |
| Tooling TypeScript | `node_modules/.bin/tsc.cmd -p tsconfig.node.json --noEmit --tsBuildInfoFile <temporary-file>` | Passed |
| Production build | `node_modules/.bin/vite.cmd build --config vite.config.ts --outDir <temporary-directory> --emptyOutDir false` | Passed; output outside repository |
| Bash syntax | Git for Windows Bash `--noprofile --norc -n` on each of the three entrypoints | Passed; also covered by three automated cases |
| Git scope/whitespace (READ-ONLY) | `git diff --check`, `git diff --cached --quiet`, `git status --short` | No tracked edits or staged changes; only intended new files |

The PostgreSQL fixtures were independently checked against the existing designated
local test database's exact name, OID, owner and loopback endpoint before running.
They create disposable guarded schemas and synthetic records, not application or
EC2 data. Public business tables remained empty and the public revision remained
`0008` afterward. The session/persistence suites use real PostgreSQL; the top-level
backend suite includes mocked checks and in-memory SQLite onboarding tests.
Frontend tests mock backend calls. Recovery delivery uses fake SMTP.

Tests/builds ran sequentially to limit memory. No dependency installation or
upgrade was needed. Initial failing tests established missing guards; focused
tests then reproduced the review findings before correction. Final counts above
refer to the final passing runs, not intermediate development runs.
The combined final total is **1,552 passed, 0 failed, 0 skipped**. This is local
evidence only; it does not establish Ubuntu, EC2 or live deployment readiness.

## What the 68 automation cases establish

- Wrong host/operator, database identity, OID, schema and read-only state fail.
- Dirty/unapproved source and executable Git filters fail; effective configuration
  includes worktree filters, and source is checked before virtualenv execution.
- Missing/unbound/tampered evidence, backup/archive problems, missing rollback,
  maintenance or credentials, and missing frontend artifacts fail closed.
- Rollback evidence must cover schema-0012 behavior and cannot assert only a
  revision-constant change. These fixtures are synthetic evidence, not a real
  demonstration of compatibility.
- Repetition, interruption and recorded migration/backend-start/Nginx failures
  block; no automatic retry, resume or rollback is implemented.
- Subprocess stdout/stderr, timeout details, CLI errors and malformed inventory
  cannot leak test credential sentinels into output.
- Tests cannot use an ambient live temporary path or write through a shared
  dependency link. Dependency copies keep writes disposable.
- Fixed live/report root exclusions hold even with incorrect inventory.
- Reports bind inventory/commit/time; they never authorize a live operation.
- Real Bash wrappers parse and return BLOCKED in dry-run and apply modes.

## Checks not performed / blockers

- No Ubuntu/EC2 execution, `sudo nginx -T`, systemd credential-loader inspection,
  effective runtime credential validation or production HTTP smoke tests.
- No fresh PostgreSQL-18/Python-3.14.4 target rehearsal. Historical EC2 test and
  restore results supplied by the operator are not independently reverified.
- Six EC2-only open-beta files were not supplied; one is absent locally and local
  settings still enforce a controlled-beta allowlist. Reconciliation is blocked.
- No demonstrated writer/restart barrier, maintenance integration, release
  activation mechanism or functionally tested schema-0012 rollback was supplied.
- Actual failed-migration, backend-start and interrupted-activation recovery
  handlers are deliberately unimplemented. Tests of recorded failure states and
  permanently blocked entrypoints do not exercise those handlers.
- Repository layout-export/browser scripts were not run; they write evidence
  under the repository and are unrelated to this automation change. Responsive
  and full browser flows remain unverified.
- ShellCheck is unavailable locally. Bash syntax checks are not Ubuntu runtime
  tests. No secret-advisory or OS security certification is claimed.
- Independent read-only safety review found no remaining high-priority issues
  after the focused corrections; that review did not access EC2 or execute tests.

## Remaining approvals and operator effort

Review/commit/push of this scaffolding is separate from release approval. No
staging, commit, push, fetch or deployment was performed. Use an explicitly
reviewed new full commit containing automation and reconciled EC2 changes;
`678a7e0` predates this work.

Estimated review, commit/push, fetch and initial blocked preflight: 20-40 minutes
after protected inputs exist. Inventory/reconciliation and loader/barrier/
rollback implementation plus real target rehearsals likely require several
hours; this cannot be estimated accurately without the missing contracts.
There is no honest current time estimate for a safe live deployment.

**NO-GO for live deployment/rollback.** Filling placeholders cannot change that.
