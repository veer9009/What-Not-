# Production configuration preparation — 15 November 2026

## Design and authorized execution plan

The owner's autonomous preparation request authorizes local code, configuration, tests and documentation. It explicitly excludes deployment, paid infrastructure, credential changes, original database writes, deletion/reset and commits/pushes. Existing working-tree changes must remain intact. Routine design/execution approval is already supplied; infrastructure, identities, domain/certificate and budget remain owner decisions.

Keep React/Vite, FastAPI/SQLAlchemy/PostgreSQL and `/api/v1`. Choose same-origin production requests over a separately hosted API because this keeps one TLS origin and avoids unnecessary cross-origin configuration. Preserve loopback development. Reject malformed/insecure production API overrides at both build and request configuration boundaries. No uploads or WebSockets exist in inspected application consumers; do not introduce either.

Keep systemd/Nginx rather than adding Docker, since the repository has no container deployment. Templates must refuse unresolved site/TLS/access inputs rather than guess a domain or certificate. FastAPI stays loopback-only. PostgreSQL may be loopback-only on a minimum single-host pilot; remote PostgreSQL must use verified TLS and a CA. Separate AWS design evaluates RDS against this cost/availability tradeoff.

Implementation tasks, executed with regression tests first:

- [x] Frontend: reproduce production loopback behavior in `src/api/productionConfiguration.test.ts`; add shared API-base validation, preserve development, wire build validation, verify auth/API consumers, test invalid overrides, inspect production assets.
- [x] Backend: add production settings/host/docs/transport tests; require DB and explicit production hosts, HTTPS origins and SMTP TLS; require verified remote DB TLS, bound pool/connect timeouts; apply TrustedHostMiddleware, production metadata restriction and safe headers without changing auth/business rules.
- [x] Deployment: prepare secret-free production env examples, Nginx TLS/static/API/access templates, non-root systemd API and bounded worker units/timers. No install/restart/deploy execution. Test static contracts; mark unavailable Nginx/systemd runtime validation pending.
- [x] Operations: prepare architecture/costs, empty production DB procedure, least privilege, backup/isolated restore, monitoring/incidents, five-user UAT and controlled release process. Preserve unresolved owner inputs and gates.
- [x] Verification executed: focused tests RED then GREEN; frontend full suite/build; backend non-persistence and guarded isolated DB tests; existing secret/dependency checks; syntax/static checks. No original DB writes. Independent review completed. Failed runs, intermittent timing risk and unavailable production/scanner checks remain explicit in the handoff; this checkbox does not certify production readiness.

Review focus: production env override bypasses; IPv4/IPv6 loopback/credential URLs; `/api/v1` duplication; proxy forwarding and host matching; default restart behavior during maintenance; migration/runtime grants; unknown PIN versus saved-address fallback; no fabricated payment or upload support; recovery consistency versus merely readable archives.

## Verification ledger

Results, changed files and remaining limitations are recorded here and in `MORNING_DEPLOYMENT_HANDOFF.md` after actual commands complete. The prior readiness audit is historical evidence and will receive a preparation addendum; missing cloud evidence cannot become PASS through local tests.

Verified implementation evidence: frontend routing RED 20 failures then focused GREEN 40 tests; backend production RED 18 failures then full GREEN 304 non-persistence tests; deployment missing-file RED 6 failures then static contracts GREEN, including the later operational-assertion safety guard. Actual build guards reject development NODE_ENV and loopback API overrides. Normal build passes and the loopback API literal is absent. Current JS advisory query reports 0 High/Critical, 2 Moderate; Python advisory tools remain unavailable. Guarded isolated persistence tests passed 178 with original/test rows unchanged and no quota cleanup.

Design refinements from evidence: explicitly pin all project Vite/Vitest commands to `vite.config.ts` to avoid ignored generated JS precedence; import the shared validator explicitly as TypeScript and include it in the node TS project. Reject both process and Vite dotenv development NODE_ENV when building. Production settings allow private loopback DB transport but require remote verify-full plus CA and reject query overrides. systemd/dotenv JSON arrays use outer single quotes. Added operator bootstrap guards without changing registration roles. Independent review's Important finding (optimizable assertions in the migration procedure) was reproduced and corrected to explicit RuntimeError guards. Original database remains outside every write target.

Frontend runtime timing failures remain a separate investigation: earlier LocationDiscovery timeout under concurrent work, then two registration tests exceeded 5s in the serial full run. Retain these failures and timing diagnostics; no timeout/assertion is relaxed to obtain a pass. Final classification appears in the handoff. No unsupported application fix is claimed.

Latest diagnostic full frontend: **283/283 passed, 31 files, 320.15s**, including all five build-selection/NODE_ENV tests and 24 routing tests. Registration timing showed the input phase dominating a passing 1.5–2.9s case, with response/render about 0.1–0.2s. Temporary output was removed. This does not prove why previous 5s timeouts or the historical admin lookup failed. Evidence preserves all outcomes rather than resetting the failed-suite history.

Restored original `App.test.tsx` afterward: **29/29 passed, 31.37s**, no remaining Git diff in that file. No skipped test, assertion relaxation, global fake-timer switch or timeout increase was used as a fix.

Scope classifications: Docker/container checks **NOT APPLICABLE** to the chosen host-service deployment; upload/WebSocket/payment-processing checks **NOT APPLICABLE** because those features are absent. Static proxy/service contracts **PASS** locally; native Nginx/systemd, Linux runtime compatibility and AWS/HTTPS/UAT/recovery execution remain **NOT VERIFIED**. Current two Moderate JS tooling advisories remain **FAIL** for clean advisory clearance; no production GO is implied by passing local regressions.
