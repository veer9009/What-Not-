# Deployment security checklist

Date: 14 November 2026. Five-user pilot. **NO-GO until blocking evidence is closed.**
This is a verification plan, not authorization to deploy, migrate or change AWS.

| Control / required evidence | Current status | Owner / gate |
| --- | --- | --- |
| Reviewed source, clean baseline, no automatic commits | PASS | Engineering |
| Backend isolated authorization/business/race/migration tests | PASS | Engineering; 654 baseline passes |
| Full frontend suite and production build after remediation | PASS | 242 tests; final build; test report |
| High dependency findings remediated and fresh advisory results retained | PASS | SEC-001/002/011; 0 High/Critical; 2 Moderate SEC-012 advisories remain |
| Python dependency CVE scan plus reviewed exceptions | NOT TESTED | Security; blocking evidence |
| Full redacted history/artifact secret scan | NEEDS MANUAL REVIEW | Heuristic only; Gitleaks unavailable |
| Dedicated production identity, explicit production environment, 5 admitted accounts including recovery operator | NOT TESTED | Operator; do not use test mode |
| Required DB URL, strong unique JWT key, exact production CORS origin | NEEDS MANUAL REVIEW | SEC-003; no private VITE_ variables |
| Secrets from approved server store, restrictive environment-file ownership/access, no repo keys | NOT TESTED | Operator/AWS; blocking |
| HTTPS certificate/renewal, HTTP redirect, real frontend API HTTPS URL | NOT TESTED | Nginx/operator; blocking |
| CSP tested against real assets/API, nosniff, framing, referrer policy on HTML/errors | NOT TESTED | Nginx/security; SEC-004 |
| HSTS only after HTTPS/subdomain correctness; staged max-age | NOT TESTED | Do not blindly enable includeSubDomains/preload |
| Restrict docs/OpenAPI/readiness to approved operational access | NEEDS MANUAL REVIEW | SEC-008 |
| Proxy source attribution, forwarded header trust, low-count auth 429 test | NOT TESTED | Only known proxy addresses trusted |
| Per-action quotas, body size, timeouts and bounded connection limits | NEEDS MANUAL REVIEW | SEC-005; no load attacks |
| Nginx serves only dist public assets; deny dotfiles/Git/env/source maps/source trees | NOT TESTED | Test actual public host; blocking |
| EC2 security groups expose only required HTTPS and controlled management | NOT TESTED | DB 5432 and app 8000 must not be public |
| App bound to loopback/private interface behind proxy, no dev/preview production server | NOT TESTED | Operator |
| PostgreSQL private network/authenticated least-privilege runtime user | NOT TESTED | DB operator; no superuser runtime |
| DB certificate-verifying TLS for remote transport; encrypted DB/backups/volumes | NOT TESTED | DB/AWS; blocking |
| IAM instance role least privilege; no static AWS keys; IMDSv2 required | NOT TESTED | AWS operator |
| OS patches, non-root service account, restrictive file/directory permissions | NOT TESTED | Host operator |
| Approved, rehearsed migration using backup of dedicated target, schema 0008 | NOT TESTED | Separate explicit approval; no production migration performed |
| Restorable encrypted backup, restore exercise, rollback and incident contacts | NOT TESTED | Blocking; restore must preserve new events for investigation |
| Worker scheduler/leases/retry handling, real SMTP TLS and delivery evidence | NOT TESTED | Outbox counts are not scheduler/delivery proof |
| Sanitized access/error logging, correlation IDs and actionable alerts | NEEDS MANUAL REVIEW | SEC-004; do not log tokens/bodies/query PII |
| Retention/erasure/data request owner and processor inventory | NEEDS MANUAL REVIEW | SEC-007; approve before collecting pilot PII |
| Shared-device draft cleanup/recovery decision | NEEDS MANUAL REVIEW | SEC-006 |
| Logout/revocation threat decision and admin access recovery | NEEDS MANUAL REVIEW | SEC-010; auth changes need approval |
| Real browser buyer A/B, seller A/B, admin walkthrough and mobile/operator UAT | NEEDS MANUAL REVIEW | Automated smoke is not human UAT |
| COD/direct-UPI status and collection | NOT APPLICABLE | Absent; new payment logic requires approval |
| Upload/proof storage and password reset | NOT APPLICABLE | Absent; do not promise these controls |
| Named final release approver and documented unresolved-risk review | NOT TESTED | No silent acceptance; no pilot approval recorded |

Manual perimeter verification after a separately approved deployment (not run here):

```powershell
curl.exe -sS -I https://PILOT_HOST/
curl.exe -sS -I https://PILOT_HOST/api/v1/health
curl.exe -sS -o NUL -w "%{http_code}" https://PILOT_HOST/.env
curl.exe -sS -o NUL -w "%{http_code}" https://PILOT_HOST/.git/config
curl.exe -sS -o NUL -w "%{http_code}" https://PILOT_HOST/openapi.json
```

Replace PILOT_HOST only with the approved target. Do not print metadata response
bodies or live authorization tokens. Dotfiles must be denied, and content must not
contain secrets even if a SPA fallback returns 200. Inspect Nginx with `nginx -t`
before approved reload, and `ss -lntp` on the server for actual listeners. Read-only
AWS/DB checks must use approved access and capture redacted evidence, not credentials.
