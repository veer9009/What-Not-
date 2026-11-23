# Automation verification: 2026-11-23

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
