# Automated beta deployment: implementation and safety plan

The attached request is the specification. Work stays on the user's clean
`feature/automated-beta-deployment` branch; no staging, commits, EC2 access or
deployment is authorized. Preserve application, migration and server templates.

## Design decision

Implement Bash entrypoints backed by a Python standard-library read-only checker.
Use a protected JSON inventory, immutable commit/hash bindings and fixed probes;
never source inventory as shell code or execute operator-supplied hooks. Reports
contain fixed gate codes, statuses and commit/hash metadata, never subprocess
output, connection strings, credential contents or business records.

A generic SSH deployer would invent the encrypted loader, writer barrier and
activation mechanism. Instead, honor the request's fail-closed fallback: deployment
and rollback produce ordered dry-run plans, but `--apply` is an explicit BLOCKED
placeholder. No inventory field or report can unlock live operations. A later
reviewed implementation is required, even after evidence is supplied.

Preflight checks Ubuntu/operator/machine identity, clean approved release, observed
live state, six-file reconciliation, PostgreSQL read-only identity/revision,
reviewed Nginx and systemd fingerprints, capacity, protected backup/restore and
rollback evidence. It runs only isolated non-database backend and frontend tests
from a tracked-file snapshot. Database integration and mutation-based smoke tests
remain separate isolated/approved work. Missing inputs fail closed.

## Tasks

1. Write failing mock/temporary-fixture tests for identity, revision, dirtiness,
   evidence, backup, rollback, credentials, artifact, interruption, repetition,
   redaction, command restrictions and permanently blocked live entrypoints.
2. Implement `deploy/automation/{preflight,deploy-beta,rollback-beta}.sh`,
   `beta_automation.py` and an intentionally incomplete inventory example.
3. Document exact commands, approvals, evidence provenance and remaining EC2
   contracts in the three requested `docs/deployment` documents. Distinguish tests
   of fail-closed guards from unavailable live migration/startup/activation tests.
4. Run script tests, Bash syntax, existing backend/frontend tests and build;
   inspect Git scope and obtain an independent safety review. No live commands.

## Review focus

- Forged/stale PASS reports must never authorize live changes.
- Subprocess errors and inventory failures must never echo secrets.
- Tests must not consume live environment settings or a live database.
- Dirty live checkout must be preserved; dirty release must fail.
- Rollback evidence must cover schema 0012 behavior, not just revision text.

## Execution record

- Initial repository: clean, commit `678a7e04fc9b6cb0bb19e1ea1553234f5c6e5aed`.
- EC2-only file `backend/tests/test_open_beta_registration.py` is absent locally.
- Existing local production settings still require a beta email allowlist.
- Verified maintenance/writer, loader and schema-compatible rollback contracts
  have not been supplied. Live implementation remains deliberately blocked.
- Added three Bash entrypoints, a standard-library checker, protected inventory
  example, offline safety tests and the three requested deployment documents.
- Independent safety review findings were reproduced and fixed: release identity
  precedes executable probes; dependency copies isolate Vite writes; fixed report
  exclusions survive bad inventory; effective Git configuration includes worktree
  filters; explicit temporary roots ignore ambient live-directory overrides.
- 68 automation cases and all 1,026 backend cases pass. Both TypeScript projects,
  production build and Bash syntax checks pass. All 458 frontend cases across
  49 files pass. Total: 1,552 passed, zero failed/skipped.
- Ruling: no generic shell hooks or live adapter were added. Missing EC2 contracts
  make a working deployment sequence unsafe to invent; the requested blocked
  fallback remains mandatory, regardless of report or inventory assertions.
