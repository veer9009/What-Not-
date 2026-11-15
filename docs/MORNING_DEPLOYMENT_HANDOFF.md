# Morning deployment handoff — What Not?

Prepared 15 November 2026, Asia/Calcutta. **NO-GO for AWS deployment or participant admission until the remaining gates below are satisfied.** Local preparation fixes/configuration/runbooks are ready for owner review. No AWS resource was created, no public service started, no original database modified, no credentials changed/exposed, no real-user data transferred, no files/data deleted as cleanup, and no commit/push performed. Normal local build output was regenerated. Existing working-tree changes were preserved.

## Answers for the owner

| Question | Result and evidence |
| --- | --- |
| 1. Frontend production API URL fixed? | **PASS locally.** Defaults to same-origin `/api/v1`, retaining backend version prefix. Development retains HTTP loopback. Production rejects HTTP/loopback/credential/query/wrong-prefix overrides; request paths cannot duplicate `/api`. `src/api/config.ts`, `src/api/client.ts`, `vite.config.ts`, configuration tests. No upload/WebSocket consumer exists to update. |
| 2. Production build verified? | **PASS locally.** Final `npm.cmd run build` exits 0, Vite 8.3.8, 1,939 modules, 5.99s. JS 426.88 kB / gzip 127.75 kB. Loopback API literal absent from built JS. Unsafe NODE_ENV/URL builds both exit 1 as intended. Release commands explicitly select TypeScript config, avoiding ignored generated JS precedence. |
| 3. Nginx prepared? | **PASS static preparation; runtime NOT VERIFIED.** `deploy/nginx/whatnot.conf.template`, deny-by-default access example and injection-resistant renderer. Domain/TLS paths supplied by owner, not invented. No trailing-slash proxy rewrite, SPA routes, forwarding overwrite, body/time/rate bounds, TLS/security headers and private readiness. Nginx unavailable locally; `nginx -t` required on approved Linux target before activation. |
| 4. Backend production configuration prepared? | **PASS locally.** DB required; remote verified TLS+CA; HTTPS CORS; explicit trusted hosts; TLS for enabled SMTP; bounded pool/connect resources; production docs disabled; safe API headers. Existing auth, role/ownership and business rules preserved. See production review and tests. |
| 5. AWS architecture documented? | **YES, proposal only.** Minimum same-host loopback PostgreSQL vs private RDS upgrade, Ubuntu/ARM/x86 gates, network/IAM/secrets/SSM/storage/TLS/costs. Region and allowances are examples, not approved tariff quotes or deployed resources. |
| 6. Database initialization/migrations documented? | **YES, not executed.** Empty `whatnot_pilot`, separate roles/grants, verified identity, explicit confirmation and pinned 0008. No original local records copied. Added guarded one-time operator ADMIN tool; actual staging bootstrap/grants remain NOT VERIFIED. |
| 7. Secrets/IAM documented? | **YES, actual AWS controls NOT VERIFIED.** Dedicated runtime secret/role, restricted delivery, operator/migration/backup separation; no production credentials in templates. Production env variants now ignored, examples remain reviewable. |
| 8. HTTPS/ingress planned? | **YES, actual domain/certificate/perimeter NOT VERIFIED.** Whole-site restricted ingress covers public listing reads; five-email allowlist alone is insufficient. Stable participant CIDRs or reviewed gateway/VPN required. No public 8000/5432. Certificate issuance/renewal awaits real owner inputs. |
| 9. Backups/restoration prepared? | **PROCEDURE ONLY.** Consistent private dump, encrypted off-host generations, checksum/archive validation, separately approved isolated restore and reconciliation. Owner must approve numeric objectives and witness measured recovery. The old local TEMP cutover archive was not restored by this preparation and must not be exported to AWS. |
| 10. Monitoring planned? | **YES, NOT INSTALLED.** Proposed CloudWatch/journal/proxy signals, numeric alert starting points, private logs, named responders, worker/mail/backlog/backup/cert alerts and incident steps. Real delivery/alerting still NOT VERIFIED. |
| 11. Rollback documented? | **YES, not rehearsed on Linux/AWS.** Compatibility-reviewed code/config rollback or forward repair; no blind downgrade/stamp/reset/restore. Keep maintenance closed on failure, preserve newer business/audit records; isolated new-target recovery needs separate approval. |
| 12. Remaining unverified? | Listed below: Linux runtime/dependencies, Nginx/systemd, actual AWS/IAM/network/TLS/secrets, Python CVEs, bootstrap/grants/restore, mail/jobs/alerts and five-user HTTPS UAT/privacy sign-off. |
| 13. Exact first command tomorrow? | After choosing the approved operator AWS session: **`aws sts get-caller-identity`**. This is an identity preflight, not a deployment. Stop unless account/role matches the approved plan. No mutating provisioning command is released before missing owner inputs/costs/access choices are approved. |
| 14. Approval required first? | Owner reviews this handoff, complete working-tree diff and architecture; selects account/region/domain/ingress/five roles/budget/recovery objectives/data/mail scope, then separately authorizes the concrete infrastructure/deployment plan. Previous approval covers local migration only. No automatic deployment follows review. |

## Review package

1. [Production configuration review and verification ledger](PRODUCTION_CONFIGURATION_REVIEW.md)
2. [AWS pilot architecture and qualified cost allowances](AWS_PILOT_ARCHITECTURE.md)
3. [Deployment runbook, rendering/service/maintenance commands](AWS_PILOT_DEPLOYMENT_RUNBOOK.md)
4. [Production security and controlled release checklist](PRODUCTION_SECURITY_CHECKLIST.md)
5. [Production database, backup and recovery procedure](PRODUCTION_BACKUP_RECOVERY.md)
6. [Monitoring and incident runbooks](PRODUCTION_MONITORING_RUNBOOK.md)
7. [Five-user acceptance plan](FIVE_USER_PILOT_TEST_PLAN.md)
8. This handoff. Existing readiness audit/checklist retain historical results and receive preparation addenda; source/current evidence wins over older statements.

## Changes and why

- `src/api/config.ts`, `client.ts`, production/build configuration tests, `vite.config.ts`, `package.json`, TypeScript config files: fix production routing, enforce URL and NODE_ENV guards, preserve local development, and explicitly select reviewed config despite ignored legacy `.js` artifacts. No legacy file deleted.
- `backend/app/core/config.py`, `db/session.py`, `main.py`, production tests and existing beta settings test: close confirmed unsafe production settings, apply host/metadata/header controls and bound connection resources. No JWT/password/session redesign or unrelated feature change.
- `backend/app/bootstrap_admin.py`, guard/service tests: create an initial ADMIN only through an explicit operator tool on an identity-checked empty pilot DB. Public registration role restrictions remain unchanged. Nothing invoked it against a real DB.
- `.gitignore`, root/backend production env examples: prevent accidental production env tracking; retain secret-free examples. JSON arrays use outer single quotes for systemd/dotenv compatibility.
- `deploy/nginx/*`, `deploy/render_nginx.py`, `deploy/systemd/*`, static contract tests: reviewed deployment candidates with explicit site/TLS/access inputs and a maintenance marker; no install/start/network action.
- `docs/security/run_existing_server_tests.py`: new `--preparation` mode preserves quota counters, excludes four independently quota-mutating tests, reuses strict isolated target guards and verifies original/test rows unchanged. Existing recovery modes are retained. `audit_runtime.py` now probes the hardened production config on the correct trusted synthetic host with no DB binding.
- Eight required docs plus readiness addenda: architecture, least privilege, recovery, monitoring, operations, acceptance and handoff. No Docker or public CI/deployment workflow introduced; CI gate sequence is an explicit controlled proposal.

## Executed evidence — do not add overlapping focused counts

All commands from repository root unless stated; full outputs retained in private ignored `production-prep-*.log` files. Nonzero RED/negative tests below are intentional evidence, not passing release suites.

| Check | Command / output | Classification |
| --- | --- | --- |
| Frontend regression RED | New production routing tests: **20 failed / 4 passed**, exit 1 before implementation | Confirmed bug, corrected |
| Backend regression RED | New production settings: **18 failed / 2 passed**, exit 1 | Confirmed gaps, corrected |
| Deployment template RED | Six template/renderer security tests failed before files existed | Expected missing implementation, corrected |
| Build-guard RED | Actual development NODE_ENV build succeeded and emitted loopback; corrected automated test reproduced missing guard. Initial test import accidentally selected legacy JS; retained/corrected before meaningful RED. Explicit config-selection test then failed before scripts were pinned. | Corrected; failures retained |
| Migration procedure review RED | Static safety test found optimizable Python assertions in operational snippet, exit 1 | Reviewer finding corrected to explicit RuntimeError guards |
| Focused routing/client GREEN | **40 passed**, 2 files; no app/API weakening | PASS; included in full frontend coverage |
| Focused backend GREEN | **52 passed**; production/config/auth/dependency boundary subset | PASS; included below |
| Template/config GREEN | **26 passed** before one additional review guard | PASS; included below |
| Initial complete frontend attempt | **277 passed / 1 failed of 278**, 30 files, 462.15s, exit 1; `LocationDiscovery.test.tsx` first workflow exceeded 5s while another frontend job ran | FAIL retained; no root cause proven, no timeout/assertion weakened |
| Affected files serial rerun | **14 passed**, 3 files, 38.14s, exit 0 (build guard, AdminOperations, LocationDiscovery at that revision) | PASS subset; not full-suite proof |
| Complete serial frontend before diagnostics | Same explicit-config serial command; `production-prep-frontend-final.log`: **281 passed / 2 failed of 283**, 31 files, 357.88s, exit 1. Both registration rejection cases exceeded the unchanged 5s timeout. | FAIL retained; no assertion/API error proved |
| Complete diagnostic frontend | `node node_modules/vitest/vitest.mjs run --config vite.config.ts --pool=threads --maxWorkers=1 --no-file-parallelism --silent=false --disableConsoleIntercept`: **283 passed / 283**, **31 files**, **320.15s, exit 0**; `production-prep-frontend-diagnostic-full.log` | PASS with timing-only instrumentation; no assertion/timeout changes. Temporary output removed afterward; restored-file verification below |
| Restored original registration test file | Same explicit-config serial runner restricted to `src/App.test.tsx`: **29 passed, 31.37s, exit 0**; `production-prep-registration-restored.log`. Git diff for this file is empty after removing temporary output. | PASS subset, not additional unique full-suite coverage |
| Final non-persistence backend | From backend: `.venv/Scripts/python.exe -m pytest -q -W error tests --ignore=tests/persistence`: **304 passed in 17.14s, exit 0**; `production-prep-backend-final.log` | PASS, not all persistence tests |
| Guarded isolated DB | `backend/.venv/Scripts/python.exe docs/security/run_existing_server_tests.py --preparation`: **178 passed**, 0 failures/errors/skips, **49.839s, exit 0**, 2,021 guarded SQL statements; target `whatnot_tests_20261115_a7e394c2` OID 49265 | PASS; source and test rows unchanged, no quota cleanup. Evidence `security/evidence/production-preparation-database-tests.json` |
| Final production build | `npm.cmd run build`: **exit 0**, Vite 8.3.8, **5.99s**, active loopback API literal absent in JS | PASS local artifact; not deployed |
| Negative build checks | `npm.cmd run build` with NODE_ENV=development, then production with VITE_API_BASE_URL loopback: **exit 1 each** | PASS expected rejection; env changes process-local and restored |
| Runtime security probes | `backend/.venv/Scripts/python.exe docs/security/audit_runtime.py`: unsafe production flags False; health 200; docs/OpenAPI 404; missing/malformed/expired/forged bearer 401; configured CORS 200/unconfigured 400; **77 protected routes 401**, no DB connected | PASS scoped; no cloud perimeter claim |
| Dependency consistency | `.venv/Scripts/python.exe -m pip check`: No broken requirements | PASS compatibility only |
| Current JS advisories | `corepack.cmd pnpm audit --json`: initial restricted network socket 10013 failed; read-only approved network retry returned **0 High/Critical, 2 Moderate**, exit 1 for advisories | FAIL unresolved Moderate tooling advisories; review/patch or bounded exception; no dependency installed/changed |
| Python advisory / SAST | pip-audit/Bandit/Semgrep/Gitleaks/Trivy unavailable in existing environment | NOT VERIFIED; no scanner silently installed |
| Secret and env checks | Existing redacted scanner exits 0: **311 tracked files, 16 reachable commits, 644 history blobs, 613 workspace artifacts**. Local env remains ignored; `.env.production` and `backend/.env.production` now ignored, examples visible. Artifact has no loopback API URL. | PASS scoped prevention/inspection; heuristic not exhaustive clearance. Synthetic/example candidates and unresolved historical local-log candidate remain private review items |
| Nginx/systemd | Renderer/static security contracts and Python syntax checked; `nginx -t` / `systemd-analyze verify` unavailable locally | Static PASS / runtime NOT VERIFIED |

Fresh backend results comprise **304 non-persistence + 178 selected persistence checks**, disjoint categories. They are not the complete backend persistence suite. Four quota-mutating integration checks were deliberately excluded to preserve stored test counters; existing unit quota tests and retained prior 182-case evidence remain available, not fresh extra coverage. No success is claimed for unexecuted production tests.

## Independent review and remaining gates

Independent read-only review found an Important failure mode: Python `assert` guards in the documented migration procedure disappear under optimization. Replaced all operational safety assertions with explicit `require`/RuntimeError checks; the reproducing static test is part of the 304 passing tests. Also corrected stale bootstrap documentation. No additional confirmed Critical/Important runtime flaw was reported in reviewed files. Review did not certify Linux/runtime/cloud operation.

**Blockers:**

1. Actual AWS account/region/IAM/network/secrets/perimeter/TLS configuration and cost approval do not exist as verified deployment evidence. Pick stable participant ingress; do not open public access to bypass that decision.
2. Validate Ubuntu 24.04/Python 3.12 and native dependencies on selected CPU architecture. Local Python 3.10.11 is not a production runtime recommendation; Python 3.10 is upstream end-of-life as of this audit. Verify Nginx/systemd and real trusted proxy/headers/quotas before activation.
3. Obtain current Python CVE review and resolve/accept dated Moderate Vitest tooling advisories with a named owner/expiry; never run test tooling publicly. No assertion of zero vulnerabilities.
4. Rehearse empty pilot migration/grants/admin bootstrap, actual encrypted off-host backup/restoration and approved numeric RPO/RTO. No original data transfer. Single-host cost minimum has a shared failure domain; acceptance is explicit.
5. Prove worker schedules, SMTP or approved in-app-only scope, alert delivery and incident operator coverage. Complete five-user HTTPS/mobile/role/privacy acceptance and owner business/privacy/contact decisions.
6. Prior AdminOperations failure and this run's timeouts are not proven fixed root causes. Keep their evidence; diagnostic full pass establishes current behavior only. Timing sample: registration input setup 1.36–2.73s, response-to-alert around 0.1–0.2s; serial diagnostic full run passed both around 1.5s. This supports timing pressure, not a proven causal trace of the failed runs. Temporary logging was removed and assertions/timeouts remain unchanged. Review the live locality radius scope and PIN-owned-address limitation honestly.

**Decision: NO-GO for AWS deployment/admission.** The local preparation is reviewable; no automatic deployment follows passing tests. Once owner choices and independent staging gates have evidence, reassess for controlled infrastructure setup and later pilot admission separately.

## Completion evidence

All eight required documents exist and their local links/Markdown fences were checked. Python renderer/bootstrap syntax and operational migration AST checks passed. Independent review's Important correction is covered by the passing backend suite. `git diff --check` passed with existing Windows line-ending warnings only. Current JS audit completed over the approved read-only network retry; scanners not installed were not claimed as executed. Selected production source/template hashes and machine-readable result classification are retained in `security/evidence/production-preparation-verification.json`; this is verification evidence, not a complete frozen release artifact.

No product code or test expectation was changed to make intermittent tests pass. The restored original registration-file check is recorded with its command/output in that evidence. A future release still needs reproducible Linux/HTTPS acceptance and the owner decisions above.

**OVERNIGHT PREPARATION COMPLETE — AWAITING OWNER REVIEW BEFORE AWS DEPLOYMENT.**
