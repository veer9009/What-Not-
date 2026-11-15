# Security findings

Date: 14 November 2026. Baseline `5da76c8`. Only observations demonstrated locally
are called confirmed. Severity describes potential impact; deployment exposure is
stated separately. No production compromise or successful exploit is alleged.

## SEC-001 — High — Vulnerable Vite development tooling

- **Component / reference:** `package.json:15`; baseline `pnpm-lock.yaml:785` and
  `pnpm-lock.yaml:1456` resolve Vite 8.3.1. Line positions change after regeneration.
- **Description:** npm advisory data identifies affected Vite/tooling versions,
  including launch-editor command execution risks and file access restrictions.
- **Business impact:** developer/build-host compromise or local-file exposure if
  vulnerable development middleware is reachable under advisory prerequisites.
  This does not demonstrate an exploit in an Nginx-served static bundle.
- **Evidence / reproduction:** `npm audit --json` returned High for Vite; installed
  package and tracked pnpm lock both contained 8.3.1. Full advisory ranges and
  links are retained in `evidence/npm-baseline.json`.
- **Recommendation:** same-major patched Vite; never expose Vite dev/preview as
  production hosting. Keep static build and Python runtime separate.
- **Fix status / retest:** **PASS**, fixed at 8.3.8; final tracked-graph scan no
  longer reports Vite. Baseline **FAIL**. See SECURITY_FIX_CHANGELOG.md. No dangerous
  editor execution or file disclosure exploit run.

## SEC-002 — High — Vulnerable undici test dependency

- **Component / reference:** baseline `pnpm-lock.yaml:781`, `pnpm-lock.yaml:1241`,
  `pnpm-lock.yaml:1454`; jsdom 30.1.1 depends on undici, installed at 8.11.2.
- **Description:** affected dependency includes published TLS-validation, denial
  of service and redirect/cache disclosure advisories. Prerequisites vary; e.g.
  the custom TLS callback advisory requires function-valued TLS options.
- **Business impact:** Node test/tooling processes consuming hostile network
  responses could lose availability or confidentiality. The browser SPA uses
  browser fetch; this finding does not prove production FastAPI exposure.
- **Evidence / reproduction:** npm audit reported High; the installed dependency
  and tracked pnpm lock match affected versions. See baseline JSON and
  [upstream TLS advisory](https://github.com/nodejs/undici/security/advisories/GHSA-2m5v-pch6-74hx).
- **Recommendation:** override to patched 8.12.2 within the existing major and
  jsdom-compatible range; validate test suite and refreshed advisory data.
- **Fix status / retest:** **PASS**, fixed at 8.12.2; final tracked-graph scan no
  longer reports undici. SECURITY_FIX_CHANGELOG.md; baseline **FAIL**. No live-network
  exploit or customer-data test was attempted.

## SEC-003 — Medium — Production configuration permits incomplete/unsafe choices

- **Component / reference:** `backend/app/core/config.py:17`, `:32`, `:49`, `:73`,
  `:77`, `:80`, `:96`; `backend/app/db/session.py:10`.
- **Description:** production permits a missing database URL, HTTP origins,
  default development CORS origins and SMTP STARTTLS disabled, including when
  credentials are supplied. Database certificate verification is not enforced.
  Environment defaults to development, making a correctly set launch environment
  essential. Missing DB fails requests with 503 rather than failing startup.
- **Business impact:** misdeployment can produce unavailable business APIs or
  expose credentials/personal data over an unprotected transport. These are
  accepted configurations, not proof of a live unencrypted connection.
- **Evidence:** `audit_runtime.py` prints accepted missing DB, HTTP CORS and
  SMTP-without-TLS production settings. Production with no signing key is rejected.
- **Recommendation:** review required settings; fail production startup on missing
  DB/explicit HTTPS origins; require verified TLS for remote DB and SMTP with a
  deliberately reviewed local-relay exception. Validate deployment mode explicitly.
- **Fix status:** **NEEDS MANUAL REVIEW**; no configuration change. Security-sensitive
  deployment/transport policy needs approval under the user's fix policy.
- **Retest:** **FAIL** for fail-closed configuration expectations; actual DB/SMTP
  network TLS **NOT TESTED**.

## SEC-004 — Medium — No demonstrated production browser/perimeter controls

- **Component / reference:** `backend/app/main.py:25`, `:35`, `:41`; `vite.config.ts:4`;
  no tracked reverse-proxy configuration.
- **Description:** direct FastAPI responses omit CSP, nosniff, framing/referrer
  policies, HSTS and request IDs. No HTTPS/proxy evidence supplies these controls.
- **Business impact:** weaker browser containment and incident traceability;
  a missing verified TLS perimeter would expose authenticated traffic.
- **Evidence:** local `/api/v1/health` response includes no-store but no listed
  headers; production mode does not alter this. This is not an assertion about
  headers on the uninspected deployed frontend.
- **Recommendation:** review a concrete HTTPS/Nginx design; CSP must account for
  frontend API/image/portfolio needs and framing policy. Set HSTS only after
  HTTPS and relevant subdomains are validated; test normal and error responses.
- **Fix status:** **NEEDS MANUAL REVIEW**, infrastructure approval required.
- **Retest:** direct application headers **FAIL**; public HTTPS perimeter **NOT TESTED**.

## SEC-005 — Medium — Abuse controls cover only selected actions

- **Component / reference:** `backend/app/services/abuse.py:34`;
  `backend/app/api/routes/properties.py:17`, `:69`, `:71`, `:75`;
  `backend/app/api/routes/creative.py:22`, `:58`;
  `backend/app/api/routes/auth.py:15`.
- **Description:** auth/discovery/address/checkout have durable limits, while
  public property/Creative reads and enquiry/report/visit/quote writes lack action
  quotas. Public reads bypass pilot admission by design. Proxy source handling
  uses request.client; real trusted-forwarder behavior is unknown.
- **Business impact:** cheap requests can consume DB resources or generate rows,
  notifications and email backlog; a shared proxy source can lock out testers.
- **Evidence:** route/service trace; no quota calls in these paths. Existing tests
  prove selected quotas persist despite rollback. No high-volume attack performed.
- **Recommendation:** agree per-action budgets and body/connection/time limits;
  validate trusted proxies and low-count 429 behavior in production mode.
- **Fix status:** **NEEDS MANUAL REVIEW**; business quotas require design approval.
- **Retest:** coverage gap **FAIL**; load resilience **NOT TESTED**.

## SEC-006 — Medium — Private recovery drafts survive logout

- **Component / reference:** `src/state/creativeRecovery.ts:9`, `:21`, `:25`;
  `src/state/checkoutRecovery.ts:10`; `src/state/AuthContext.tsx:17`, `:44`;
  `src/pages/LegalPages.tsx:16`.
- **Description:** account-scoped sessionStorage contains Creative briefs/quote
  terms and order/address/product references. Logout clears credentials and React
  identity, but leaves these drafts until success, explicit clearing or tab closure.
  Namespaced browser keys do not enforce confidentiality from same-origin scripts
  or a person inspecting storage on a shared tab.
- **Business impact:** residual private enquiry text or purchasing context on
  shared devices. No token or full address/password storage was found here.
- **Evidence:** save/clear functions and logout implementation; existing notice
  accurately discloses persistence. No attempt to read real customer content.
- **Recommendation:** design a visible clear-private-drafts action and bounded TTL
  with safe reconciliation for uncertain writes; preserve idempotency semantics.
- **Fix status:** **NEEDS MANUAL REVIEW**, recovery tradeoff; no destructive clearing.
- **Retest:** persistence behavior confirmed; confidentiality expectation **FAIL**.

## SEC-007 — Medium — No implemented retention/erasure process

- **Component / reference:** `backend/app/models/user.py:14`;
  `backend/app/models/events.py:11`, `:26`, `:42`;
  `backend/app/models/abuse.py`; `docs/BETA_RUNBOOK.md` quota-retention section;
  `src/pages/LegalPages.tsx` privacy/contact sections.
- **Description:** no account deletion/export workflow or bounded purge of personal
  records, outbox, audit events or quota identifiers. Foreign keys restrict ad hoc
  deletion. Quota SHA-256 scopes are linkable pseudonyms, not anonymization.
- **Business impact:** indefinite data growth and inability to reliably fulfill
  approved privacy requests. Legal obligations require separate qualified review.
- **Evidence:** route/model inventory and documented open owner decisions;
  PERSONAL_DATA_FLOW.md traces retention across all data classes.
- **Recommendation:** approve retention, identity verification, legal holds,
  processor/backups handling and a tested request workflow before pilot access.
- **Fix status:** **NEEDS MANUAL REVIEW**; schema/retention changes require approval.
- **Retest:** implemented erasure/purge control **NOT TESTED** because absent.

## SEC-008 — Low — API documentation and operational readiness are public

- **Component / reference:** `backend/app/main.py:25`;
  `backend/app/api/routes/health.py:19`.
- **Description:** production-mode `/docs`, `/redoc` and `/openapi.json` return 200;
  `/api/v1/ready` has no role dependency and returns schema/backlog aggregates.
- **Business impact:** unauthenticated API discovery and limited operational
  metadata exposure; documentation is not an authorization bypass.
- **Evidence:** runtime HTTP probes; readiness source trace (no production DB read).
- **Recommendation:** restrict docs/readiness at reviewed proxy or production app
  policy; keep minimal process health available to approved health checks.
- **Fix status:** **NEEDS MANUAL REVIEW**; no production visibility-policy change.
- **Retest:** docs exposure **FAIL** against restricted-pilot expectation;
  deployed readiness reachability **NOT TESTED**.

## SEC-009 — Low — Environment ignore rules miss common deployment filenames

- **Component / reference:** `.gitignore:18` and subsequent environment patterns.
- **Description:** `.env`, `.env.local` and `.env.*.local` are ignored, but
  `.env.production` and `backend/.env.production` are not.
- **Business impact:** a future operator could accidentally stage production secrets.
- **Evidence:** `git check-ignore` returns only .env.local and backend/.env for
  the four tested names. No production environment file was found tracked.
- **Recommendation:** approve broad `.env.*` ignore coverage with explicit example
  exceptions, plus CI/pre-commit Gitleaks and reviewed server secret injection.
- **Fix status:** **FAIL**, open; outside automatic Critical/High-only fix scope.
- **Retest:** ignore-gap reproduced; no confirmed tracked leak.

## SEC-010 — Low — Logout does not revoke a copied access token

- **Component / reference:** `src/state/AuthContext.tsx:17`, `:44`;
  `backend/app/core/security.py:54`; `backend/app/api/dependencies.py:72`.
- **Description:** logout is browser-only; JWT has subject/issued/expiry claims,
  no session ID/revocation list. A copied token remains valid until its 15-minute
  default expiry unless account activity/role/admission changes block it.
- **Business impact:** bounded replay window after logout on token theft.
- **Evidence:** token creation/validation and route inventory; no server logout or
  reset endpoint. Existing tests verify activity/role changes take effect immediately.
- **Recommendation:** review acceptable pilot session risk; if immediate revocation
  is required, design server sessions/token versioning and regression tests.
- **Fix status:** **NEEDS MANUAL REVIEW**; authentication architecture requires approval.
- **Retest:** source-confirmed limitation; copied-token logout scenario **NOT TESTED**.

## SEC-011 — High — Vulnerable source-map-js in test tooling

- **Component / reference:** baseline `pnpm-lock.yaml:738` and `:1400`,
  source-map-js@1.2.1 package/snapshot; css-tree dependencies in the jsdom graph. Locate with
  `rg -n 'source-map-js@1.2.1' pnpm-lock.yaml` on baseline `5da76c8`.
- **Description:** the tracked-graph pnpm advisory scan identified an event-loop
  denial of service through indexed source-map section offsets, affecting versions
  >=1.0.0 and <1.2.2. The ignored npm lockfile query did not expose this finding.
- **Business impact:** a Node tooling process parsing attacker-controlled source
  maps could become unavailable. This does not establish a public FastAPI or
  browser SPA exploit path.
- **Evidence:** retained intermediate pnpm advisory response and original lock;
  [upstream advisory](https://github.com/lydell/source-map-js/security/advisories/GHSA-68fv-2mgg-jv7q).
- **Recommendation:** compatible patch override to 1.2.2, rerun tracked-graph audit
  and dependency-floor/frontend/build checks. No resource-exhaustion exploit run.
- **Fix status / retest:** **PASS**, fixed at 1.2.2; final tracked-graph scan no
  longer reports source-map-js. Baseline **FAIL**; details in fix changelog.

## SEC-012 — Medium — Vulnerable Vitest mocker development middleware

- **Component / reference:** baseline `pnpm-lock.yaml:1139` @vitest/mocker@5.0.2,
  reached through Vitest 5.0.2. No application source imports this middleware.
- **Description:** pnpm reports two Moderate advisories: unauthenticated manual
  mock registration code injection and Windows backslash allowlist bypass.
- **Business impact:** reachable test/development middleware can expose developer
  environments under advisory prerequisites. No such production service was verified.
- **Evidence:** pnpm advisory IDs GHSA-qxg6-89mg-rqv8 and GHSA-xp26-3454-mjgp;
  fixed versions >=5.0.3; final advisory artifact records affected paths/ranges.
- **Recommendation:** reviewed Vitest patch upgrade and rerun suite; bind development
  services to loopback and never expose test middleware in production.
- **Fix status:** **FAIL**, open; Medium finding outside automatic High/Critical fix scope.
- **Retest:** advisory presence confirmed, no code-injection exploit attempted.

## Separate unverified deployment risks (not confirmed vulnerabilities)

No EC2/Nginx/DB TLS, security group, IAM/IMDSv2, secret-manager, filesystem ownership,
backup/restore, monitoring, real SMTP or public frontend URL evidence was available.
Python package CVE status is unverified because pip-audit is absent. Full Gitleaks,
Semgrep, Bandit and Trivy results are unavailable. These gaps are tracked in the
risk register and independently keep the deployment gate at **NO-GO**.

No confirmed application IDOR, privilege escalation, SQL injection, stored XSS,
payment-status manipulation or upload vulnerability was found in the tested paths.
That statement is bounded by the test evidence and manual coverage, not a guarantee.
