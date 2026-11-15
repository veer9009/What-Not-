# What Not? pre-deployment security audit

Audit date: 14 November 2026 (Asia/Calcutta). Baseline commit: `5da76c8`.
Scope: local source, reachable Git history, installed dependencies, synthetic tests.
Target: initial five-user pilot on EC2/Nginx. No production access or deployment.

## Read-only baseline (completed before remediation)

The working tree was clean. No AGENTS.md was found in the repository inventory.
311 tracked files and 16 reachable commits were present. The architecture is:

- React 19/Vite/TypeScript SPA; Vitest/jsdom tests; tracked pnpm lockfile.
- Python 3.10.11/FastAPI, SQLAlchemy 2/psycopg, PostgreSQL, Alembic revisions
  0001–0008; request-scoped transactions; bounded command-line workers.
- Custom HS256 JWT authentication, Argon2id passwords, database role/activity
  checks, production account allowlist, durable PostgreSQL action quotas.
- Homemade orders with server pricing, inventory locks, idempotency, delivery
  confirmation/disputes; sale-property moderation/enquiries/visits; Creative
  provider listings, private briefs, quotations, engagements and reviews.
- Optional SMTP outbox delivery. No payment gateway, COD/direct-UPI collection or
  payment-status endpoint; no file upload/proof storage or password-reset flow.
- No tracked Nginx, EC2/IAM/security-group, systemd, Docker, Jenkins or CI
  deployment configuration. Hosting is a target, not a verified implementation.

Historical README/authentication documents contain obsolete statements that
checkout is 501 and rate limiting is absent. Current source/tests take precedence:
POST orders is implemented; only legacy GET products/detail remain placeholders.

| Baseline check | Status | Evidence |
| --- | --- | --- |
| Backend initial restricted run | FAIL | 281 passed, 373 setup errors; pg_ctl restricted-token error 87 |
| Backend identical isolated rerun outside sandbox | PASS | 654 passed in 381.08 seconds, warnings treated as errors |
| Frontend full baseline | FAIL | 236 passed, 3 failed out of 239; two timeouts and one alert lookup |
| Affected frontend files rerun unchanged | PASS | 33/33; failure cause not conclusively proven |
| Production build / TypeScript | PASS | Vite 8.3.1 build completed; TypeScript completed |
| Python package consistency / compilation | PASS | pip check: no broken requirements; compileall exit 0 |
| Custom secret scan | NEEDS MANUAL REVIEW | 311 files, 569 historical blobs; no confirmed tracked live secret; ignored local credential URL |
| Dependency advisory query | FAIL | npm reports 2 High packages: Vite 8.3.1, undici 8.11.2 |
| Python dependency advisory scan | NOT TESTED | pip-audit unavailable; pip check does not scan vulnerabilities |
| Local protected-route authentication probes | PASS | See authorization matrix and runtime evidence |
| Production infrastructure controls | NOT TESTED | No AWS/proxy/host evidence supplied |

The original npm query failed due to restricted network access; a read-only
elevated retry succeeded. npm advisories were compared with the tracked pnpm
versions, not assumed accurate solely from the ignored npm lockfile.

## Category-by-category assessment

1. **Secret leak prevention (Gitleaks-style):** tracked files, all reachable Git
   objects, local environment handling and public frontend configuration inspected.
   Gitleaks itself was unavailable. See SECRET_SCAN_REPORT.md.
2. **Personal data flow (Bearer-style):** collection, validation, DB storage,
   response projections, logging, browser recovery, SMTP and external links traced.
   No Bearer scanner execution is claimed. See PERSONAL_DATA_FLOW.md.
3. **Production readiness (ECC-style):** configuration fail-closed checks,
   error handlers, CORS/cache/headers/docs, dependencies and deployment evidence
   reviewed. EC2, Nginx, HTTPS, DB TLS/isolation, backups and permissions unverified.
4. **Deep application review (Trail of Bits-style):** protected route dependencies
   and service ownership/state transitions traced across every business vertical;
   tests cover permissions, transaction races and moderation. This is a manual
   methodology-inspired assessment, not a Trail of Bits engagement or certification.
5. **Attacker perspective (ECC-style):** bounded local missing/malformed/expired/
   forged bearer tests, all protected-route missing-token checks, existing cross-user
   and role/IDOR/mass-assignment/price/stock tests, local metadata exposure probes.
   No destructive, high-volume or live-infrastructure requests were made.

The referenced security guide's full text was not supplied. These category names
describe the requested scope; no proprietary checklist compliance is claimed.

## Standards and assessment limits

Use [OWASP ASVS 5.0](https://asvs.owasp.org/) as the verification framework, with
authentication, authorization, validation, browser security, data protection and
configuration coverage. This is not an exhaustive requirement-by-requirement ASVS
certification. [OWASP API Security Top 10 2023](https://api-security.owasp.org/editions/2023/en/0x00-header/)
informs object/function/property authorization, resource/flow abuse, configuration
and API inventory checks. [AWS EC2 best practices](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-best-practices.html)
inform least-permissive networking and host controls; no AWS state was inspected.

Status vocabulary: PASS / FAIL / NOT TESTED / NOT APPLICABLE / NEEDS MANUAL REVIEW.
PASS applies only to the specified check and environment, not the application as a
whole. Confirmed observations, configuration-dependent risks and unverified controls
are separated in SECURITY_FINDINGS.md and SECURITY_RISK_REGISTER.md.

## Deployment gate

**NO-GO.** Do not admit even the five-user pilot until unresolved High findings
and critical evidence gaps are closed. Final remediation/test results are recorded
in SECURITY_FIX_CHANGELOG.md and SECURITY_TEST_RESULTS.md. The deployment checklist
requires reviewed HTTPS/proxy settings, private DB access, least privilege, secret
delivery, backups/recovery, dependency evidence and real browser/operator sign-off.

Final local verification: **242/242 frontend tests**, **654 existing backend tests**,
**5 added backend attacker-input tests**, **3 included dependency guards**, production
build and **1 five-account Edge browser smoke test** passed. The three dependency
guards are part of the 242, not three additional frontend tests. The tracked pnpm
scan now has **0 High/Critical**, with **2 Moderate @vitest/mocker advisories** left
open. Three High package findings were patched (Vite, undici, source-map-js).
Missing critical production evidence independently keeps the result at NO-GO.
An independent read-only review found no material defect in these audit changes;
it did not certify uninspected production infrastructure or absent scanner results.

No deployment, push, commit, credential rotation, production database access,
schema change or infrastructure change was performed. Risks have not been accepted
on behalf of the owner.
