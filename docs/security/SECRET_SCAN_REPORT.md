# Secret scan report

Date: 14 November 2026. Baseline `5da76c8`.

## Execution and coverage

`backend/.venv/Scripts/python.exe docs/security/audit_secret_scan.py` performed a
read-only, redacted heuristic scan of 311 tracked files and 569 distinct reachable
Git blobs across all local refs (16 commits). It uses `git ls-files -z`,
`git rev-list --objects --all` and `git cat-file --batch`, without changing Git.
Rules cover common private-key headers, AWS/service token formats, credential URLs
and literal secret assignments. Output records rule/path/line, never matched values.

**Gitleaks was unavailable.** This is not Gitleaks, entropy analysis or an exhaustive
secret-detection result. Unreachable objects, reflog-only data, remote branches not
present locally, deleted server/CI logs and cloud secret stores were not assessed.
No Bearer/Bandit/Semgrep/Trivy execution is claimed.

## Results and triage

| Location | Observation | Status / disposition |
| --- | --- | --- |
| backend/.env.example:12 | Commented placeholder database URL | PASS: documented placeholder, not a live credential |
| backend/DATABASE.md:171 and historical variants | Placeholder setup examples | PASS: examples; historical matches reviewed |
| backend/tests/persistence/test_foundation.py:16,20,34,37; backend/tests/test_db_dependency.py:17 | Synthetic fixture URLs | PASS: isolated tests; never production access |
| backend/tests/test_beta_settings.py:38; scripts/beta_browser_smoke.py:57 | Test-only credentials | PASS: synthetic settings, not production identity |
| scripts/phase6_scope_browser.mjs:37; src/App.test.tsx:47,61,92 | Synthetic test inputs/tokens | PASS within test scope |
| src/pages/LoginPages.tsx:35 and earlier versions | Form field syntax matched assignment heuristic | PASS: no embedded login password |
| backend/.env:12 | Populated credential URL, loopback destination; ignored by Git | NEEDS MANUAL REVIEW: private local configuration, not a confirmed leak |
| backend/.env:4 | Populated private signing-key setting, not printed | NEEDS MANUAL REVIEW: random generation/source and reuse cannot be established |
| Frontend configuration | Only VITE_API_BASE_URL observed; no private key intended for browser | PASS for reviewed source |
| .gitignore environment patterns | .env.production variants not ignored | FAIL: SEC-009 |

Fourteen tracked heuristic matches and 29 historical matches were recorded; those
counts include repeated versions/examples, not 43 secret leaks. No tracked live
credential was confirmed. Local environment values were inspected only for presence,
placeholder classification and loopback destination, never reported or used to connect.

Password hashing, JWT key loading, SMTP SecretStr use, sanitized handled exceptions,
no-store API responses, schema rejection of credential-bearing image/portfolio URLs
and browser-memory tokens were reviewed. A private server variable must never use
a VITE_ prefix: Vite configuration is part of the public client bundle.

## Rotation and prevention

No confirmed leaked credential currently mandates rotation based on this audit.
The operator must verify whether the local database password/signing key was reused,
shared or uploaded elsewhere; rotate through an approved process if exposure/reuse
is established. Do not copy development credentials into production. Nothing was
rotated, and history was not rewritten.

Production rejects a missing signing key, an empty allowlist and disabled abuse
controls. It does not require DATABASE_URL at startup (SEC-003). Environment-file
permissions, secure server delivery, backup encryption and secret-store access were
**NOT TESTED**. SecretStr masks representations; it does not encrypt secrets at rest.

## Manual scanner follow-up (not executed)

On a trusted workstation with the approved tool installed:

```powershell
gitleaks version
gitleaks git --redact --report-format json --report-path gitleaks-redacted.json .
gitleaks dir --redact --report-format json --report-path gitleaks-files-redacted.json .
```

Install Gitleaks from its verified official release or approved Windows package
source, checking its checksum; do not execute a downloaded installer script.
Keep reports outside the scanned directory, review redaction and limit artifact
access. Add reviewed pre-commit/CI scanning after deciding the delivery workflow.
Re-run history and artifact checks before release, including built assets and CI logs.

## Local artifact follow-up

`audit_secret_scan.py --artifacts` also inspected 483 current workspace/artifact
files, including ignored logs, dist and untracked audit files, excluding installed
dependencies/Git internals/caches and files over 10 MB. It found 17 heuristic
candidates: the previously triaged source/examples, local credential URL and audit
script regex syntax. No candidate appeared in dist. One ignored historical log
match at `backend/phase5-collection.log:140` matched a synthetic test URL and did
not match the current local environment credential. No real values were printed.
This bounded heuristic still does not replace an approved full artifact secret scan.
