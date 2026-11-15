# Security risk register

Date: 14 November 2026. No risk is accepted by this report. Owner names/sign-off
remain unassigned; the role below indicates who must supply evidence.

| ID | Type / severity | Risk / evidence | Owner | Status / next action | Pilot blocking |
| --- | --- | --- | --- | --- | --- |
| SEC-001 | Confirmed dependency / High | Vite 8.3.1 advisory range; dev/tooling exposure | Engineering | PASS: 8.3.8; final tracked-graph scan | Resolved |
| SEC-002 | Confirmed dependency / High | undici 8.11.2 via jsdom; tooling exposure | Engineering | PASS: 8.12.2; final tracked-graph scan | Resolved |
| SEC-003 | Confirmed config gap / Medium | Production accepts incomplete DB/HTTP/SMTP TLS-off settings | Engineering/operator | NEEDS MANUAL REVIEW; approve concrete fail-closed transport policy | Yes: critical config evidence |
| SEC-004 | Confirmed local header gap / Medium | Direct app lacks browser controls; no perimeter evidence | Security/operator | NEEDS MANUAL REVIEW; approve and test HTTPS/proxy plan | Yes |
| SEC-005 | Confirmed quota coverage gap / Medium | Public reads/enquiry/visit/report paths unbudgeted; proxy behavior unknown | Product/security | NEEDS MANUAL REVIEW; action budgets and bounded low-count tests | Review required |
| SEC-006 | Confirmed residual storage / Medium | Private drafts survive logout in tab storage | Product/security | NEEDS MANUAL REVIEW; safe recovery/cleanup decision | Review required |
| SEC-007 | Confirmed lifecycle gap / Medium | Retention/erasure process absent | Privacy owner/operator | NEEDS MANUAL REVIEW; documented policy and request procedure | Yes before pilot PII |
| SEC-008 | Confirmed metadata exposure / Low | Public docs/readiness | Operator | NEEDS MANUAL REVIEW; access policy | Review required |
| SEC-009 | Confirmed preventive gap / Low | .env.production variants not ignored | Engineering | FAIL; broaden patterns with example exceptions | Review required |
| SEC-010 | Confirmed architecture limit / Low | Browser logout does not revoke copied JWT | Security | NEEDS MANUAL REVIEW; 15-minute replay window decision | Review required |
| SEC-011 | Confirmed dependency / High | source-map-js 1.2.1 in jsdom graph; tooling DoS advisory | Engineering | PASS: 1.2.2; final tracked-graph scan | Resolved |
| SEC-012 | Confirmed dependency / Medium | Two Moderate Vitest mocker advisories in 5.0.2 | Engineering | FAIL; reviewed patch upgrade recommended | Review required |
| ENV-01 | Unverified / High potential | HTTPS certificate/proxy, port exposure, DB private network/TLS/auth, host permissions | AWS/operator | NOT TESTED; supply actual redacted configurations and verification | Yes |
| ENV-02 | Unverified / High potential | IAM, IMDSv2, secret delivery, runtime privilege, patching | AWS/operator | NOT TESTED; least-privilege review and evidence | Yes |
| ENV-03 | Unverified / High potential | Backup/restore, rollback, monitoring, scheduler and real mail | Operator | NOT TESTED; recovery rehearsal and alert/delivery proof | Yes |
| TOOL-01 | Unverified / High potential | Python dependency CVE status; pip-audit absent | Security | NOT TESTED; approved isolated scanner and reviewed result | Yes |
| TOOL-02 | Incomplete evidence / Medium | Gitleaks/Bandit/Semgrep/Trivy unavailable; heuristic/manual review only | Security | NEEDS MANUAL REVIEW; run approved scanners before release | Review required |
| TEST-01 | Baseline instability / Medium | 3 baseline frontend failures retained; final full suite 242/242 | Engineering | PASS on final run; monitor timing stability; baseline cause not conclusively proven | Resolved for local suite evidence |
| SECRET-LOCAL | Suspected / unscored | Ignored local signing key and loopback credential URL; no proven leak/reuse | Operator | NEEDS MANUAL REVIEW; provenance/reuse check; rotate only if warranted and approved | Review required |
| DATA-01 | Unverified / Medium potential | Processors/regions/log retention/support ownership unresolved | Privacy owner | NEEDS MANUAL REVIEW; complete owner inventory | Yes before PII |

No confirmed production exploit or live leak was established. No confirmed Critical
application vulnerability was found in reviewed paths. Unknown controls have not
been marked PASS. Remediation of tooling findings alone cannot change the gate to GO.

Gate rules: GO requires passed required evidence and no deployment blockers;
CONDITIONAL requires documented risk review and explicit pilot approval;
NO-GO applies to unresolved High/Critical findings or missing critical evidence.
Current result: **NO-GO**. Reassessment requires linked proof for each blocking row
and a named approver; calendar urgency or five-user scale is not compensating evidence.
