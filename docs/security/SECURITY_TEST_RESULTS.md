# Security test results and command training

Date: 14 November 2026, Asia/Calcutta. Baseline commit `5da76c8`.
Only local synthetic data and fixture-owned PostgreSQL clusters were used.

## Actual baseline and audit results

| Check | Actual result | Status |
| --- | --- | --- |
| Initial Git status | Empty short status; baseline clean | PASS |
| Backend restricted full suite | 281 passed, 373 setup errors; PostgreSQL restricted-token error 87 | FAIL (environment) |
| Same backend suite with temporary-cluster execution allowed | 654 passed in 381.08s, -W error | PASS |
| Frontend baseline | 236 passed, 3 failed, 28 files, 230.37s | FAIL |
| Unchanged affected frontend files | 33 passed, 2 files, 58.01s | PASS; root cause of full-run failures not proven |
| TypeScript baseline / production build | Successful; Vite 8.3.1 bundle built | PASS |
| pip check | No broken requirements found | PASS for consistency, not CVEs |
| compileall of app/Alembic/tests | Exit 0 | PASS for syntax, not security |
| Secret heuristic | 311 files, 569 historical blobs, 16 commits; no confirmed tracked live secret | NEEDS MANUAL REVIEW; full Gitleaks absent |
| Local metadata routes | /.env and /.git/config both 404 | PASS only for direct FastAPI; Nginx unknown |
| Missing/malformed/expired/wrong-signature bearer | All 401 | PASS |
| All protected route missing-token checks | 77/77 returned 401; inventory 86 business routes | PASS |
| CORS preflight | Configured origin 200; unconfigured origin 400 without ACAO | PASS for explicit-origin enforcement |
| Production missing JWT | Settings validation rejects | PASS |
| Production missing DB / HTTP CORS / SMTP TLS off | All accepted | FAIL for strict production configuration; no network exploit claimed |
| Production docs | /docs, /redoc, /openapi.json 200 | FAIL against restricted-pilot expectation |
| Direct response headers | no-store present; CSP/HSTS/nosniff/framing/referrer/request ID absent | FAIL locally; deployed headers NOT TESTED |
| npm baseline advisory scan | 2 High package findings; ignored npm graph cross-checked for affected pnpm versions | FAIL |
| pnpm tracked-graph intermediate scan | 1 High source-map-js and 2 Moderate mocker advisories after initial two patches | FAIL; prompted SEC-011/012 |
| Added backend attacker-input tests | 5 passed in 95.01s | PASS |
| First dependency-floor TypeScript attempt | Type errors from unavailable Node types in browser tsconfig | FAIL; test moved to JavaScript, no app type suppression |
| Offline frozen install attempts | Store lock access denied, then missing offline registry metadata | FAIL (environment); not a lock consistency pass |

Frontend baseline failures: `Marketplace.test.tsx` “creates an address without user
identity” (5000ms timeout), “preserves address edit and reports backend rejection
403” (alert lookup), and `LocationDiscovery.test.tsx` “requires an explicit source,
uses backend list/detail and adds real products to the cart” (5000ms timeout).
No timeout settings or assertions were weakened to hide these failures.

The baseline full backend suite includes test_authentication, test_authorization,
test_beta_abuse, test_beta_account_locks, test_beta_orders, test_beta_order_race,
test_order_creation/idempotency/geography, test_delivery_confirmation, test_properties,
test_creative, migration and concurrency cases. This is stronger than a no-token
probe alone; it is not exhaustive coverage of every role/state combination.

Added backend tests in `backend/tests/persistence/test_security_audit.py` verify
SQL-like text remains literal data, SQL-like IDs are rejected, client totals/payment
state cannot be assigned, validation does not echo synthetic secrets, and an upload
route does not exist. They never issue destructive SQL or write to application DBs.

No high-volume DoS, arbitrary editor/code execution, live third-party mail, AWS
attack or real-customer test was performed. XSS/SQLi/deserialization/CSRF conclusions
combine source review and bounded tests: no unsafe HTML/eval/pickle/shell sink found;
SQLAlchemy expressions bind values; browser fetch omits cookies and requires an
Authorization header, so ambient-cookie CSRF does not apply to reviewed mutations.
File-upload validation is NOT APPLICABLE because uploads are absent. HTTP URL/image
validation was reviewed; server-side media fetching is absent, so no media SSRF
endpoint was exercised. Remote image privacy/HTTP content still need owner review.

## Tools and versions actually available

Python 3.10.11; pytest 9.1.1; FastAPI 0.143.0; Starlette 1.7.0; Pydantic 2.14.0;
SQLAlchemy 2.0.54; PyJWT 2.15.1; argon2-cffi 25.1.0; pip 23.0.1;
Node v24.20.0; npm 12.0.2; Corepack pnpm 12.8.1; baseline Vitest 5.0.2;
baseline Vite 8.3.1. PostgreSQL binaries used from Program Files/PostgreSQL/17/bin.
No global installation was performed. Exact PostgreSQL/Git/Edge versions are
recorded in final verification when collected, otherwise not claimed.

Gitleaks, pip-audit, Bandit, Semgrep and Trivy were not available on PATH; Python
pip_audit/bandit/semgrep modules were also absent. They did not run. No official
ECC/Bearer/Trail of Bits scanner or proprietary engagement was performed.

## Commands executed: purpose, mechanics and verification

Commands below omit routine output redirection to ignored `audit-security-*.log`
files. PowerShell `*>` captures all streams and can mix diagnostics with JSON;
retained JSON evidence was parsed/normalized separately. `$LASTEXITCODE`, not the
success of a following Get-Content, is the native program's exit status.

| Exact important command / group | WHAT | WHY | WHEN | HOW / key parts | EXPECTED OUTPUT | COMMON FAILURES | HOW TO VERIFY SUCCESS | MEMORIZATION CATEGORY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `git status --short` | Shows tracked/untracked edits | Preserve existing work and inspect scope | Before/after audit | --short gives compact file states | Empty baseline; final intended edits only | Wrong directory, ignored artifacts hidden | Compare baseline and final; inspect diff | MEMORIZE |
| `git rev-parse --show-toplevel`; `git log -5 --format="%h %s"` | Identifies repo and recent commits | Bind evidence to revision | Start of assessment | rev-parse resolves root; log formats hash/subject | Expected root and baseline 5da76c8 | Not a repo, wrong checkout | Confirm root/current commit | UNDERSTAND / LOOK UP |
| `rg --files -g '!node_modules' -g '!.venv' -g '!venv'`; `rg --files -g AGENTS.md -g '!node_modules' -g '!.venv' -g '!venv'` | Inventories source/instructions | Discover real architecture and rules | Before assumptions | --files lists files; -g filters paths | Source/test/config paths; no repository AGENTS match | Hidden/ignored files omitted; exit 1 means no matches | Cross-check Get-ChildItem -Force and git ls-files | UNDERSTAND / LOOK UP |
| `Get-Content package.json`; `Get-Content backend/requirements.txt`; `Get-Content backend/pytest.ini` and targeted source reads | Reads manifests/config/source | Establish implementation and test setup | Before execution/review | Literal local file reads; no env value dumps | Actual scripts/pins/settings | Missing file, output truncation | Re-read focused ranges and trace callers | PROJECT-SPECIFIC / DON'T MEMORIZE |
| `git ls-files '*env*' '*Docker*' '*nginx*' '*Jenkins*' '*yml' '*yaml'` | Lists tracked config candidates | Separate targets from committed deploy configuration | Architecture/secret review | Git pathspec matching | Env examples, lockfile, Alembic env; no deploy config | Pattern quoting, untracked configs omitted | Compare complete tracked inventory | UNDERSTAND / LOOK UP |
| `git check-ignore .env.production backend/.env.production .env.local backend/.env` | Tests ignore rules | Prevent accidental environment commits | Secret review | Prints only ignored names | Both real local names ignored; production variants reveal gap | Exit 1 for no matches; not a scan of values | Observe specific names printed/missing | UNDERSTAND / LOOK UP |
| `backend/.venv/Scripts/python.exe docs/security/audit_secret_scan.py` | Redacted heuristic plus history scan/tool inventory | Find candidate leaks without disclosure | Baseline/pre-release | Python regexes; Git ls-files/rev-list/cat-file batch; tool/module lookup | Counts and locations, no values | Missing interpreter/Git, heuristic false negatives | Review candidates privately; confirm counts/coverage; run Gitleaks separately | PROJECT-SPECIFIC / DON'T MEMORIZE |
| `node --version`; `npm.cmd --version`; `corepack.cmd pnpm --version`; `backend/.venv/Scripts/python.exe -m pip --version` | Records runtimes/toolchain | Reproducible evidence | Before tests/scans | --version prints installed tool | Exact versions above | PATH or Corepack unavailable | Match resolved executable and version | UNDERSTAND / LOOK UP |
| `node node_modules/vitest/vitest.mjs run --pool=vmThreads --maxWorkers=1` | Runs complete frontend tests | Detect auth/privacy/UI regressions | Baseline and after fixes | run is one-shot; one VM worker bounds concurrency | Every test passed; exit 0 | 5-second timing failures, DOM lookup, worker restrictions | Full summary and native exit, not focused rerun alone | PROJECT-SPECIFIC / DON'T MEMORIZE |
| `node node_modules/vitest/vitest.mjs run src/Marketplace.test.tsx src/LocationDiscovery.test.tsx --pool=vmThreads --maxWorkers=1` | Repeats failed files unchanged | Diagnose stability | After reading failures | Two explicit file filters, same worker settings | 33/33 | Timing/resource contention; underlying UI race | Inspect summary; keep original failure evidence | PROJECT-SPECIFIC / DON'T MEMORIZE |
| `node node_modules/typescript/bin/tsc -b`; `npm.cmd run build` | Typechecks and builds production assets | Catch integration/build errors | Baseline/final | -b follows tsconfig references; build runs tsc then vite | Exit 0 and dist asset summary | Missing Node types in new test, native binding/tool errors | Exit and bundle output; no suppressed diagnostics | UNDERSTAND / LOOK UP |
| `$env:PATH = 'C:\Program Files\PostgreSQL\17\bin;' + $env:PATH`; `.venv/Scripts/python.exe -m pytest -q -W error` (cwd backend) | Runs complete backend suite | Verify security/business/transaction rules | Baseline; relevant changes | PATH exposes initdb/pg_ctl; -q concise; -W error fails warnings; fixture owns temporary cluster | 654 baseline passed | Sandbox token error, missing binaries, test assertions | Confirm counts, fixture-generated DB and clean shutdown; never use app DB fallback | PROJECT-SPECIFIC / DON'T MEMORIZE |
| `.venv/Scripts/python.exe -m pytest -q -W error tests/persistence/test_security_audit.py` (cwd backend, same PATH) | Runs added bounded attacker-input tests | Verify injection/mass assignment/error handling | After adding security checks | Explicit file on isolated fixture | 5 passed | Test setup permissions, real assertion failure | Full summary and no application DB connection | PROJECT-SPECIFIC / DON'T MEMORIZE |
| `backend/.venv/Scripts/python.exe -m pip check`; `backend/.venv/Scripts/python.exe -m compileall -q backend/app backend/alembic backend/tests` | Checks package consistency and Python compilation | Catch broken env/syntax | Baseline | pip checks dependency declarations; compileall writes only bytecode caches | No broken requirements; quiet exit 0 | Incompatible package/syntax; not a CVE detector | Inspect native exits, do not call this pip-audit | UNDERSTAND / LOOK UP |
| `npm.cmd audit --json`; `npm.cmd audit --json --cache .audit-npm-cache` | Queries npm advisories | Baseline package security signal | Before changes | Lockfile graph sent to registry; --json machine output; local cache | JSON and 0 if clean, 1 for findings | Restricted network; ignored npm lock can differ from pnpm | Parse JSON and compare actual tracked versions | UNDERSTAND / LOOK UP |
| `corepack.cmd pnpm audit --json` | Scans tracked pnpm graph | Authoritative graph check | Intermediate/final | Corepack invokes existing pnpm; audit uses lockfile and registry | Advisory JSON; nonzero for unresolved advisories | Network, stale/incomplete npm graph assumptions | Parse vulnerabilities/paths; don't treat exit 1 as tool crash automatically | UNDERSTAND / LOOK UP |
| `backend/.venv/Scripts/python.exe docs/security/audit_runtime.py`; `backend/.venv/Scripts/python.exe docs/security/audit_inventory.py` | Probes local controls and renders matrix | Evidence for every protected route | Baseline | TestClient; random synthetic signing key; unbound session; AST inventory | 86 routes, 77 missing-token 401; explicit gap observations | Import mismatch, missing evidence file | Inspect retained JSON and unexpected statuses; no DB reachable | PROJECT-SPECIFIC / DON'T MEMORIZE |
| `corepack.cmd pnpm install --ignore-scripts --prefer-offline` | Installs selected local dependency graph | Apply patch remediation | After baseline and version constraints | --ignore-scripts disables lifecycle scripts; prefer cache then registry | Target versions; successful install | latest refreshes unrelated versions; package.json overrides ignored by pnpm 12 | Compare direct versions and lock diff; workspace overrides are required | PROJECT-SPECIFIC / DON'T MEMORIZE |
| `corepack.cmd pnpm install --frozen-lockfile --ignore-scripts --offline` | Attempts locked local reinstall | Detect manifest/lock mismatch | After restoring ranges | Frozen prohibits lock updates; offline requires cached metadata/artifacts | Exit 0 without lock mutation | Store lock permission; missing offline metadata | A failed environment attempt is not a consistency PASS | UNDERSTAND / LOOK UP |
| `git diff --check`; `git diff --stat`; targeted `git diff -- package.json pnpm-lock.yaml` | Checks whitespace and actual changes | Preserve narrow scope | Before completion | --check flags whitespace; --stat summarizes; pathspec focuses diff | No whitespace errors; only intended changes | CRLF warnings, unrelated graph changes | Read actual final diff and status | MEMORIZE |

Temporary dependency constraint commands used (helper removed after finalization)
`docs/security/prepare_dependency_fix.py prepare` and `finalize`: WHAT constrained
unrelated direct versions during lock resolution then restored original ranges;
WHY avoid unapproved major refresh; WHEN patching a manifest with latest ranges;
HOW reads baseline Git objects and restores manifest specifiers, preserving patched
snapshots; EXPECTED only selected direct change and transitive patch graph;
COMMON FAILURES incomplete process or running install before preparation finishes;
VERIFY lock diff plus frozen install and tests; category
**PROJECT-SPECIFIC / DON'T MEMORIZE**. These are maintenance operations, not app runtime.

## Unavailable-tool installation and manual verification (not executed)

Install only into an approved isolated tool environment; do not alter the app venv
or run downloaded remote scripts:

```powershell
py -3 -m venv .audit-tools
.\.audit-tools\Scripts\python.exe -m pip install pip-audit bandit
.\.audit-tools\Scripts\python.exe -m pip_audit --version
.\.audit-tools\Scripts\python.exe -m pip_audit -r backend/requirements.txt
.\.audit-tools\Scripts\python.exe -m bandit --version
.\.audit-tools\Scripts\python.exe -m bandit -r backend/app -f json -o bandit-redacted.json
```

Use approved, reviewed/pinned scanner versions in the actual release pipeline.
For Gitleaks and Trivy, obtain matching Windows binaries/checksums from their
[official Gitleaks](https://github.com/gitleaks/gitleaks/releases) and
[official Trivy](https://github.com/aquasecurity/trivy/releases) releases; add only
their verified directory to the current shell PATH. Then run `gitleaks version`,
the redacted commands in SECRET_SCAN_REPORT.md, `trivy --version` and
`trivy fs --scanners vuln,secret .` with restricted/redacted report handling.
For Semgrep use a supported isolated Linux/WSL environment and approved package:
`python3 -m venv /tmp/whatnot-audit-tools`, then that venv's pip to install semgrep;
run `semgrep --version` and a locally reviewed ruleset with
`semgrep scan --config /path/to/reviewed-rules backend/app src`. Do not fetch/execute
unreviewed remote rules or claim these commands ran here.

Before release, re-run dependency and full secret/artifact scans, inspect actual
HTTPS/perimeter responses and DB/IAM/backup evidence, and retain redacted results.
Manual public-host commands appear in DEPLOYMENT_SECURITY_CHECKLIST.md.

## Interview connection

Why did passing tests not establish deployment readiness? Tests proved specified
local application behavior on isolated data. They did not verify public TLS, AWS
network/IAM policy, DB certificate verification, backups or every current CVE.
The release decision therefore combines local regression evidence with explicitly
owned infrastructure and operational verification; missing critical proof is NO-GO.

## Final verification

| Check | Result | Status |
| --- | --- | --- |
| Final tracked-graph pnpm advisory scan | 0 High, 0 Critical; 2 Moderate @vitest/mocker advisories remain | FAIL overall; High findings resolved |
| Final frozen install with scripts disabled | Lock up to date; resolution skipped; exit 0 | PASS |
| Final complete frontend suite | 242 passed across 29 files in 86.00s; includes three dependency guards | PASS |
| Dependency-floor focused tests | 3 passed | PASS |
| Final Vite 8.3.8 production build / TypeScript | Exit 0, 1938 modules, bundle produced | PASS |
| Five-user real Edge browser smoke | 1 passed in 66.85s | PASS |
| Added isolated backend attack-input checks | 5 passed in 95.01s | PASS |
| Full backend baseline | 654 passed; backend app source unchanged | PASS |

Browser smoke confirmed seller order progression, scoped fulfillment, buyer
completion/dispute and admin resolution; notifications/outsider denial; property
enquiry/visit/address revocation; persisted contact-sharing withdrawal; Creative
RFQ/quote/accept/deliver/complete/review; locality privacy and real checkout; legal
routes/keyboard controls at responsive widths. It uses test mode and fake accounts,
so production admission/quotas and real mail/perimeter remain separate checks.

The browser command was `.venv/Scripts/python.exe -m pytest -q -s
../scripts/beta_browser_smoke.py` from backend with PostgreSQL 17 on PATH.
WHAT: executes Edge against the actual built bundle; WHY: verifies real browser
integration beyond jsdom; WHEN: after final build; HOW: isolated DB, five synthetic
accounts, owned loopback port and disposable Edge profile; EXPECTED OUTPUT: one
passing test and workflow PASS messages; COMMON FAILURES: occupied port 8000,
missing Edge/Node/native WebSocket, sandbox process restriction; HOW TO VERIFY
SUCCESS: test summary plus successful cleanup of owned server/profile/cluster;
MEMORIZATION CATEGORY: **PROJECT-SPECIFIC / DON'T MEMORIZE**.

Final frozen command: `corepack.cmd pnpm install --frozen-lockfile --ignore-scripts`.
WHAT: checks/install final graph; WHY: enforce manifest/lock consistency; WHEN: after
patch finalization; HOW: frozen lock prohibits resolution changes, scripts disabled,
registry metadata allowed; EXPECTED OUTPUT: lock up to date/exit 0; COMMON FAILURES:
store permissions, missing registry metadata or specifier mismatch; HOW TO VERIFY
SUCCESS: read native exit and confirm no subsequent lock mutation; MEMORIZATION
CATEGORY: **UNDERSTAND / LOOK UP**.

Focused guard command: `node node_modules/vitest/vitest.mjs run
src/utils/securityDependencies.test.js --pool=vmThreads --maxWorkers=1`.
WHAT: checks actual installed vendor security floors; WHY: prevent vulnerable
resolution recurrence; WHEN: after lock changes; HOW: resolves jsdom's real pnpm
path and checks Vite/undici/source-map-js; EXPECTED OUTPUT: 3 passed; COMMON FAILURES:
unresolved symlink base, old dependency versions, missing install; HOW TO VERIFY
SUCCESS: 3 passing assertions and fresh advisory scan; MEMORIZATION CATEGORY:
**PROJECT-SPECIFIC / DON'T MEMORIZE**.

Final metadata: PostgreSQL initdb 17.11, Git 2.51.0.windows.1. These were obtained
with `initdb --version` and `git --version`: WHAT print tool releases; WHY bind test
evidence; WHEN verify environment; HOW no state mutation; EXPECTED OUTPUT version
strings; COMMON FAILURES missing PATH; VERIFY actual executable path and output;
MEMORIZATION CATEGORY: **UNDERSTAND / LOOK UP**. Edge's exact version was not collected.

Independent read-only review found no material implementation/report defect and
confirmed the final frontend summary. It did not re-run tests or claim production,
Python-CVE or exhaustive secret/exploit clearance. Report status synchronization
was completed against actual logs. Final diff whitespace verification passed.

## Retained evidence

`evidence/npm-baseline.json` is the original npm graph advisory response;
`pnpm-intermediate.json` captures the extra High source-map-js and Moderate findings;
`pnpm-final.json` is the final authoritative tracked-graph response;
`runtime-baseline.json` contains redacted control observations and all 86 routes.
Selected successful command transcripts are retained as UTF-8 text under evidence.
Original ignored local audit-security-*.log files retain baseline failures and
diagnostics. The npm query is not substituted for the tracked pnpm scan.
