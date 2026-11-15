# Final private beta release gate — avetest.online

Audit date: **15 November 2026**. Intended audience: **10 selected private-beta users**.
Decision: **NO-GO**. This is an audit, not deployment authorization.

## Executive finding

The current checkout regression suite fails, the original running backend is not
schema-ready, the running QA backend exposes an older discovery contract, and the
production administrator bootstrap rejects a ten-account allowlist. HTTPS/AWS,
private ingress, recovery and operational acceptance are not evidenced. Successful
local logins and a successful production build do not close these gates.

No application fixes, credentials, original/QA records, original/QA migrations,
AWS resources, commits, pushes or deployments were performed. Existing application
data was queried through PostgreSQL-enforced read-only connections. Write tests
used only new synthetic data in a unique schema inside the independently verified,
empty isolated **test** database. Application services were not restarted or stopped.

**Execution deviation:** the audit runner initialized that new test schema with
Alembic migrations despite the user's explicit no-migrations instruction. That
was a scope error, not an authorized exception. It was confined to test database
OID 49265 and the unique schema named below; original and QA were not migrated,
and the test database's public revision remained 0008. No further database changes
or cleanup followed. The runner now refuses execution by default; any future
test-schema initialization requires separate explicit approval. The synthetic
schema is retained for review, not automatically removed. This deviation must be
considered alongside the technical results; the audit was not entirely read-only.

Classification: **PASS** = specified check executed successfully; **FAIL** = observed
defect or unmet implemented contract; **NOT VERIFIED** = insufficient current
evidence; **NOT APPLICABLE** = explicitly outside documented feature scope. A PASS
for a service test is not a PASS for the deployed browser workflow. No Critical
exploit was demonstrated; multiple High release blockers remain.

## 1. Fresh database and running-process evidence

Evidence: `docs/security/evidence/beta-final-readonly.json`; command:

```powershell
& .\backend\.venv\Scripts\python.exe -u docs/security/audit_beta_readonly.py
```

Exit **0**. All three identities verified **before business-table queries**:
IPv4 loopback `127.0.0.1:5432`, PostgreSQL **17.11**, primary, expected OID and
configured-role ownership. Every connection enforced `transaction_read_only=on`.

| Database | OID | Actual revision | Users / sellers / products / addresses / orders | Public-point columns |
| --- | --- | --- | --- | --- |
| `whatnot_app_dev` | 41069 | **0008** | **6 / 2 / 3 / 1 / 3** | All four absent |
| `whatnot_chrome_qa_20261115` | 50640 | **0009** | **2 / 1 / 3 / 1 / 0** | All four present |
| `whatnot_tests_20261115_a7e394c2` | 49265 | **0008 in public** | **0 / 0 / 0 / 0 / 0** | Absent in public; separate new test schema migrated to 0009 |

Six original users match the earlier documented post-cutover smoke account; this
audit created no original account. No user identities, coordinates or hashes were
exported. These are read-only snapshot counts, not a guarantee that an independently
running application cannot write later.

`netstat -ano -p TCP` confirmed listeners: original frontend **5173/PID14636**,
QA frontend **5174/PID6048**, original API **8000/PID19728**, QA API **8001/PID6224**.
They bind loopback. Local PostgreSQL listens on `0.0.0.0:5432`; that observation
does not establish firewall reachability and must not be copied into an exposed
AWS security group.

**Original backend database identity: VERIFIED.** Five PostgreSQL source-session
client ports (53623, 53633, 53681, 53682, 53697) matched OS sockets owned by worker
PID7576. A read-only elevated CIM check verified its parent as API listener
PID19728. No process command lines or connection strings were printed.

Read-only HTTP observations (`curl.exe --noproxy '*' --max-time 10`):

| Method / endpoint | Original port 8000 | QA port 8001 |
| --- | --- | --- |
| GET `/api/v1/health` | **200** | Not independently repeated in the final curl set |
| GET `/api/v1/ready` | **503** | **503** |
| GET `/openapi.json` | DiscoveryQuery/DiscoverySource **include radius_km** | Both **lack radius_km** |

Both readiness errors were the sanitized category `Database schema is not ready`.
The original API is serving the new contract against the old schema. QA is serving
an old contract despite its database being 0009; it needs controlled artifact/runtime
reconciliation, not another assumed migration. No authentication/discovery/checkout
request was sent against existing data: these can persist quota or business writes.

GET of the Vite-transformed API client confirmed 5173 has no explicit API override
and retains the development fallback to 8000; 5174 explicitly targets 8001. No
browser storage, passwords or tokens were inspected or extracted.

### Why 0008 and 0009 differ

The source has one linear Alembic head, **0009**, descending from 0008. Revision 0009
adds nullable seller `public_discovery_latitude`, `public_discovery_longitude`,
`public_discovery_confirmed_at`, `public_discovery_consent_version`, plus geographic
and all-present/all-null constraints. It deliberately does **not** copy private
dispatch coordinates into public fields. `backend/app/db/schema.py:2` requires
0009; `backend/app/models/seller_profile.py:37` maps the added columns. Login can
succeed through the unchanged users mapping while seller/discovery queries fail.
Readiness explicitly rejects the mismatch (`backend/app/api/routes/health.py:25`).

**FAIL / HIGH:** this release cannot be certified against original schema 0008.
Do not migrate the original to fix this audit. Establish an explicitly approved,
compatible release/schema pair on an isolated staging or future pilot target.
Existing sellers will still require explicit public-point consent on a 0009 target.

## 2. Executed verification ledger

Root is `C:\Users\DELL\OneDrive\Desktop\What-Not`; commands specifying Python
`-m pytest` below ran from `backend`. Raw ignored logs are private diagnostic
artifacts; do not publish their synthetic tokens, payloads or DOM dumps.

| ID | Exact command / check | Fresh result |
| --- | --- | --- |
| V1 | `git status --short`; `git rev-parse --short HEAD`; `git diff --check` | HEAD **5da76c8**, substantial pre-existing tracked modifications/untracked implementation and deployment files; no immutable reviewed release identified. Whitespace exit **0**, line-ending warnings retained in `beta-final-audit-diff.log`. |
| V2 | `& .\.venv\Scripts\python.exe -m pytest -q -W error tests --ignore=tests/persistence` | **329 passed**, 25.32s, exit **0**; `beta-final-audit-backend.log`. |
| V3 | `& .\backend\.venv\Scripts\python.exe -u docs/security/audit_beta_isolated_tests.py` | **379 passed, 19 failed, 28 skipped, 0 errors** / 426, 106.16s console, exit **1**. Executed once before the refusal guard was added; do not rerun under this audit's no-migrations authorization. See deviation/isolation/failures below. |
| V4 | `& 'C:\Program Files\nodejs\node.exe' node_modules/vitest/vitest.mjs run --pool=threads --maxWorkers=1 --no-file-parallelism` | **281 passed, 18 failed, 0 skipped** / 299; 31 passing + 2 failing files; 507.13s; exit **1**. `beta-final-audit-frontend.log`. |
| V5 | Same Node/Vitest command with `src/Checkout.test.tsx src/DeliverySupport.test.tsx` before pool flags | **33 passed, 17 failed, 0 skipped** / 50, 64.17s, exit **1**. All 27 DeliverySupport cases passed in this rerun. `beta-final-audit-frontend-focused.log`. This overlaps V4. |
| V6 | `& 'C:\Program Files\nodejs\npm.cmd' run build` | TypeScript + Vite **PASS**, exit **0**, 1,940 modules, Vite 8.58s. `beta-final-audit-build.log`. JS 430.74kB / gzip 128.73kB. PowerShell records npm stderr notices as NativeCommandError text; the actual process exited 0 and completed the build. |
| V7 | `& .\backend\.venv\Scripts\python.exe docs/security/audit_runtime.py` | Exit **0**, synthetic unbound-session app: **79/79 protected routes return 401**, 88 routes inventoried; missing/malformed/expired/forged JWTs 401; allowed CORS 200, unapproved origin 400/no ACAO; production docs/OpenAPI and secret-file probes 404. `beta-final-audit-runtime.log`. |
| V8 | `& .\backend\.venv\Scripts\python.exe docs/security/audit_secret_scan.py --artifacts` | Exit **0**; 311 tracked files, 16 commits, 759 history blobs, 698 workspace artifacts. Redacted candidates: **14 tracked, 55 historical, 41 workspace**, credential-URL/literal-secret rules; zero private-key/AWS-key/service-token rule hits. Local backend env ignored. Heuristic scan is not comprehensive secret clearance. `beta-final-audit-secrets.log`. |
| V9 | `& .\.venv\Scripts\python.exe -m pip check`; `-m alembic heads`; `-m alembic history` | Exit **0**, no broken Python requirements; single linear head **0009**. Heads/history are source-only; no Alembic upgrade/current command was executed against the original. |
| V10 | Offline `Settings` + `bootstrap_admin.validate_target()` with synthetic five/ten email rosters | Five accepted; **ten rejected**, no database connection. `docs/security/evidence/beta-final-command-summary.json`. |
| V11 | `Resolve-DnsName avetest.online -Type A -DnsOnly`; `curl.exe --noproxy '*' --connect-timeout 5 --max-time 10 -s -o NUL -w 'avetest HTTPS status=%{http_code} TLS_verify=%{ssl_verify_result}\n' https://avetest.online` | DNS returned **3.87.92.64**; curl status **000**, exit **7**. No TLS session/certificate was verified. Browser-tool fetch was also inaccessible. This audit environment's failure to connect does not prove the remote server is down. |
| V12 | `Get-FileHash -Algorithm SHA256` and `pg_restore.exe --list` for retained cutover archive | SHA/list pass; details below. No restore or backup creation. |

The fresh built JS `dist/assets/index-BzDVmGBv.js` SHA-256 is
`b8472a433b3d477a22254e3393449c06d99e3b5f8ab9330a82f57d2e8057b960`.
Artifact inspection found `/api/v1`, no original/QA loopback API literal and no
private-key marker. This is routing evidence, not full bundle secret clearance.

### Isolated database test safety and coverage

The application role has **no CREATEDB**, but owns the empty test database and can
create schemas. The audit did not retry the previously failed pg_ctl method, alter
privileges, reuse populated Chrome QA fixtures, or migrate public/original schemas.

V3 verified test DB name/OID/server/ownership and empty public business tables first.
It generated a new, previously absent schema:
`whatnot_audit_611467829c0c414897b5bc3b7f49f5a6`, applied the actual migration chain
0001–0009 there, and ran copied, unchanged persistence tests. Only the fixture
adapter changed: pinned migrated engine and explicit skips for tests requiring
additional databases/clusters. Every SQLAlchemy statement had database/OID/owner/
server/search-path checks; **10,384 guarded statements** were counted. Original,
rehearsal and Chrome QA were not test targets.

Afterward public business tables remained empty, public revision remained **0008**,
and the public table-name inventory was unchanged. The synthetic schema and test
logs were retained; no DROP/reset/cleanup was performed. Evidence:
`docs/security/evidence/beta-final-persistence.json`; detailed log and JUnit XML:
`C:\Users\DELL\AppData\Local\Temp\WhatNotFinalAudit-xnnd3s65\pytest.log` and
`tests.xml`. XML suite timing is 105.709s; console elapsed is 106.16s.

Passing module evidence includes authentication **29**, authorization **53**,
discovery **27**, order creation **14**, idempotency **16**, order services **23**,
marketplace services **39**, constraints **56**, beta orders **7**, beta admin **5**,
abuse **4**, property **11**, Creative **9**, notifications **3**, workers **3**.
Other passing tests account for the total 379; these are not additional unique runs.
The **28 skips** cover migration/harness/independent-transaction and concurrency
cases needing a separate database/cluster. Their behavior remains NOT VERIFIED by
this rerun; the successful empty-schema upgrade is not a populated migration rehearsal.

### Confirmed test regressions

**FAIL / HIGH — checkout test contract:** 17 failures reproduce unchanged in V5.
`src/Checkout.test.tsx:45` strictly expects discovery body `{address_id:4}`.
`src/api/discovery.ts:15` now always emits `radius_km`, default 3; checkout invokes
that client at `src/pages/CartPage.tsx:78`. The mock assertion throws before the
order POST. Representative outcomes: `expected [] to have a length of 1`, missing
`View order 10`, and generic service-unavailable text instead of the expected
403/409/422/session message. This demonstrates broken regression coverage, not that
all 17 real-world order paths independently failed. Do not declare checkout PASS.

**FAIL / HIGH — geography fixtures/contract:** all 19 database failures are in
`backend/tests/persistence/test_order_geography.py`. Its fixture at line 22 confirms
only private dispatch; it never sets the four consented public-point fields. New
discovery correctly excludes those products (`services/discovery.py:35`), yielding
404 or `ProductNotFound: Product is unavailable`. Assertions at lines 48 and 82 also
still expect coarse discovery to admit points outside the new exact public radius.
Smallest correction: update synthetic consent fixtures and assert public discovery
and private checkout contracts separately. Keep direct checkout and boundary/stock
rollback assertions; do not remove public consent or relax delivery restrictions.

**NOT VERIFIED / MEDIUM — intermittent frontend timing:** the full run additionally
failed `src/DeliverySupport.test.tsx:83`, unable to find `Need help with this order?`.
Its entire 27-case file passed unchanged in V5. Existing source renders the link
after the order loads (`src/pages/OrderPages.tsx:106`); no causal timing trace was
established. Earlier AdminOperations timing failures did not recur in V4. A focused
pass does not turn the failed full suite green; capture load/DOM timing if it recurs.

## 3. Application and business gate matrix

Every browser/API production column below refers to the actual intended HTTPS
release. No new write UAT was run against the original or populated QA databases.

| Flow | Current implementation / fresh automated result | Browser / release status and evidence |
| --- | --- | --- |
| Buyer registration/login; seller login | **PASS (isolated API)**: auth 29 and request transaction test pass; Argon2id, duplicate handling, BUYER/SELLER-only registration. `services/auth.py:18`, `schemas/auth.py:14`. | **NOT VERIFIED** for final HTTPS artifact. Owner-reported original buyer/seller/admin logins and admin recovery accepted as prior manual evidence, not repeated here. |
| Seller shop and product create/edit | **PASS (isolated services/API)**: ownership, dispatch confirmation, pending creation, approved edits return to PENDING. `services/products.py:39`, `:68`; `services/sellers.py:35`. | **NOT VERIFIED** on final runtime; original seller mapping is schema-incompatible. |
| Admin approval/rejection/takedown | **PASS (isolated)**: ADMIN role, pending-only/stale-review checks, rejection reasons/audits. `services/moderation.py:17`, `:28`, `:38`; `services/admin.py:45`. | **NOT VERIFIED** full browser lifecycle on the release. |
| Live discovery / 1,2,3km / empty states | **PASS (isolated API + unit tests)**: discovery 27, geography/public-radius unit cases pass. Haversine kilometres, inclusive 1e-9km tolerance, selected and seller radii, approval/active/stock/account filters, pre-pagination geography. `services/geography.py:17`, `services/discovery.py:33`, `repositories/products.py:40`. | **FAIL current runtime readiness**; complete release E2E **NOT VERIFIED**. Owner-reported prior positive QA cards/radius acceptance does not validate current 8000/0008 or stale 8001. |
| GPS/manual/saved-address source changes | **PASS (mocked frontend/source)**: current-location success/errors/confirmation, radius/source result keys and no stale cards; `location/geolocation.ts:20`, `pages/DiscoveryPages.tsx:30`, `state/DiscoveryContext.tsx:7`. No fabricated fallback; accuracy is metres, not a radius guarantee. | Real device HTTPS/movement/permissions **NOT VERIFIED** here. Owner previously confirmed Chrome acquisition; not re-exercised. PIN only selects owned saved addresses, not arbitrary PIN geocoding. |
| Cart and checkout UI | **FAIL regression gate**: V4/V5; sample items remain non-orderable in source, real checkout revalidates via discovery before order POST (`pages/CartPage.tsx:68`). | **NOT VERIFIED** complete buyer browser checkout; no payment promise. |
| Order creation, price, quantity, stock | **PASS (isolated API/services)**: authoritative Decimal prices and expected-price check, locked inventory, mixed-seller/overflow/stock rejection, transactional rollback, idempotent replay. `services/orders.py:58`, `:89`, `:114`; 14 creation, 16 idempotency, 23 service tests pass. | Independent transaction races partly skipped; final HTTP/browser purchase **NOT VERIFIED**. |
| Seller order processing / buyer receipt/dispute | **PASS (isolated)**: party ownership, allowed transition graph, cancel/reject restock, only buyer completes/disputes, timeout provenance and audits. `services/orders.py:28`, `:147`, `:173`. | **NOT VERIFIED** complete final browser lifecycle and real scheduled timeout worker. |
| Admin order visibility/totals | **PASS (source + isolated RBAC/serialization)**: ADMIN-only `/admin/orders`, server `total_amount` mapping; UI displays per-order `order.total`. `api/routes/admin.py:61`, `services/mappers.py:34`, `src/pages/AdminOperations.tsx:44`. | **NOT VERIFIED** witnessed multi-seller browser reconciliation. No aggregate revenue/settlement dashboard was verified; displayed totals are order amounts. |
| Property sale listings/enquiries/visits | **PASS (isolated subset)**: 11 property tests, moderation/expiry/suspension, owned requests and confirmed-appointment precise-address gates. `services/properties.py:108`, `:148`; 3 independent-transaction cases skipped. | **NOT VERIFIED** final browser workflow. Scope from `FIVE_USER_PILOT_TEST_PLAN.md:17`: connections/appointments, not property purchase/title verification. |
| Creative / professional services | **PASS (isolated subset)**: 9 Creative tests; moderated listing/RFQ/quote/acceptance/delivery/buyer confirmation/review; 2 concurrency cases skipped. `services/creative.py`, `tests/persistence/test_creative.py:25`. | **NOT VERIFIED** HTTPS UAT and owner reaffirmation of ten-user scope. Do not generalize Creative to every regulated professional service. |
| Platform payments, settlement, refunds | **NOT APPLICABLE** to the documented no-platform-payment scope. `app/main.py:29`, `src/pages/LegalPages.tsx` explicitly disclaim these functions. | No settlement demonstration exists and none is claimed. |
| COD/direct-UPI payment **recording** | **FAIL if required by beta**: no payment method/state/reference fields or recording endpoint in `models/order.py`, `schemas/order.py`, `api/routes/orders.py`; tests reject injected `payment_status` (`test_security_audit.py:33`). | Ten-user payment scope **NOT VERIFIED**. Owner must explicitly exclude recording or approve a separate feature; an order completion is not proof of cash/UPI receipt. No automatic feature development. |

Discovery still preserves private-dispatch locality restrictions and exact private
delivery checks at checkout. Public-radius eligibility is measured from a separately
consented public business point, not a guaranteed doorstep delivery distance.
`PublicDiscoveryLocation.tsx:12` warns that buyers can infer that point and offers
revocation. No auto-backfill, exact seller location response or Google SDK was added.

## 4. Security and operations gates

| Gate | Status / severity | Evidence, limit and correction |
| --- | --- | --- |
| Authentication / RBAC / cross-account isolation | **PASS / LOW** for executed isolated checks | 79 missing-token denials, 53 authorization tests, forged/expired-token rejection; current active account/role and admission rechecked from DB (`api/dependencies.py:60`). ADMIN cannot self-register; sellers cannot approve themselves. Keep HTTPS multi-user IDOR UAT pending. |
| Password reset revokes existing JWTs | **FAIL / MEDIUM** for revocation expectation | Tokens contain sub/iat/exp, no password-version/revocation check (`core/security.py:52`, `:59`). Password hash changes do not invalidate a copied token. Suspension does deny existing tokens (isolated beta-admin test passed). Accept bounded lifetime with documented incident procedure, or separately approve revocation; never claim reset logs out all devices. |
| Validation / CORS / safe errors | **PASS / LOW** locally | Strict extra-field/ID/money contracts, safe 422 input omission and generic storage 503 (`schemas/common.py`, `api/errors.py:47`). Production configured origin test 200; foreign origin 400/no ACAO. Actual avetest origin/proxy rules **NOT VERIFIED**; CORS is not access control. |
| Rate limiting | **PASS / LOW** for implemented actions; coverage **NOT VERIFIED / MEDIUM** for whole beta | Four isolated abuse tests include committed counters, concurrent quota and 429 behavior (`services/abuse.py:17`, `:34`). Test environment bypasses normal quotas deliberately; dedicated tests switch it on. Limits cover auth/address/discovery/checkout, not every public read/enquiry/report. Verify real proxy source trust and agreed budgets; do not disable limits. |
| Production configuration | **PASS / LOW** for local rejection tests | Requires DB, key, nonempty allowlist, abuse controls, trusted hosts, HTTPS CORS and verified remote DB TLS (`core/config.py:124`). No effective AWS configuration inspected. Dedicated pilot secrets and runtime/migration-role separation remain required. |
| Secret exposure | **NOT VERIFIED / HIGH** for release clearance | V8 is redacted heuristic evidence; tracked candidates are example/test/form contexts consistent with prior review. No private-key/AWS/service-token hit, but that is not proof every credential/log/history blob is safe. No passwords/tokens/DSNs printed by audit. Gitleaks/Bandit/Semgrep/Trivy absent; no exhaustive current scanner clearance. |
| Dependency security | **NOT VERIFIED / HIGH** | `pip check` passes but is not a CVE scan; pip-audit module/tool absent, pnpm absent on PATH, no fresh matching-lockfile advisory report. Prior advisories are historical. Run approved current JS/Python advisory scans on the frozen exact release graph; do not install tooling/dependencies silently. |
| Ten-user admission / bootstrap | **FAIL / HIGH** | `bootstrap_admin.py:26` explicitly requires `len(beta_allowed_emails)==5`; offline check rejects ten. Runtime admission itself uses membership, not a hardcoded five cap (`services/abuse.py:45`). Backend template line 6 and runbooks still say five. Approve exact ten-person roster/roles, including whether admin counts, then adapt/test the strict bootstrap count and documents without relaxing identity/empty-DB/ADMIN safeguards. |
| Whole-site private perimeter | **NOT VERIFIED / HIGH** | Nginx deny-by-default include exists (`deploy/nginx/pilot-access.conf.example:4`); public property/Creative reads are outside auth email admission (`api/routes/properties.py:12`, `creative.py:22`). No reviewed participant CIDRs/gateway or denied-outsider HTTPS evidence. Protect HTML/assets/API/public listings, not just login. |
| Nginx / HTTPS / DNS | **NOT VERIFIED / HIGH** | DNS resolves, HTTPS connection unavailable in V11. Template covers TLS1.2/1.3, headers, same-origin proxy, SPA routes, private readiness and rate limits (`deploy/nginx/whatnot.conf.template:25`, `:47`, `:79`). Nginx unavailable locally; no `nginx -t`, certificate/renewal or actual proxy/header evidence. Do not use `-k` or publish Vite. |
| AWS IAM / network / environment separation | **NOT VERIFIED / HIGH** | Architecture is a proposal (`docs/AWS_PILOT_ARCHITECTURE.md`). No AWS account, IAM policy, SG, route, instance or production DB attested. Require private DB, no public 8000/5432, scoped instance/operator roles, protected dedicated secrets, host patching/encryption and external deny evidence. No AWS CLI mutation or resource creation occurred. |
| Supervision / Docker / automation | Templates **PASS static**, runtime **NOT VERIFIED / HIGH**; Docker **NOT APPLICABLE** | Non-root systemd units, restart/maintenance markers and hardening (`deploy/systemd/whatnot-api.service:5`, `:17`, `:23`), bounded worker timers exist. Static template tests pass within V2. No installed Linux validation, actual schedules or CI workflow found. No Docker/Compose release path is in use. Need reviewed immutable artifact/configuration and manual controlled release gates, even without CI. |
| Backup / recovery / rollback | **NOT VERIFIED / HIGH** | Old cutover archive revalidated below; no current production backup or timed restore. Runbooks still pin 0008. Approve numeric RPO/RTO/retention, encrypted durable off-host backups and first actual pilot restore into a new isolated target; rehearse compatible app rollback/forward repair. No blind downgrade/reset/live restore. |
| Logging / health / monitoring / mail | **NOT VERIFIED / HIGH** | Sanitized API errors and health/readiness exist. Nginx access format omits bodies/query/IP/token; backend access log disabled in unit template. No installed alerts, received page, log retention/rotation, worker heartbeat or real SMTP delivery demonstrated. Disabled mail requires explicit in-app-only beta scope and backlog handling. `docs/PRODUCTION_MONITORING_RUNBOOK.md:26` is proposal and stale about revision. |
| Privacy / support / real-user notice | **FAIL / HIGH** for documented prerequisites | `src/config/business.ts:5` still has empty legal/operator/privacy/grievance details; LegalPages displays owner-review draft. No approved retention/deletion/support/incident ownership evidence. Tab recovery drafts can survive logout (`state/checkoutRecovery.ts`, `state/creativeRecovery.ts`); external images expose visitor network metadata. Approve a proportionate ten-user notice and handling process; this is a technical release gate, not a legal opinion. |

Remote PostgreSQL TLS verification must include server identity/CA validation, not
only encryption; see [AWS RDS TLS guidance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html).
This is a requirement to verify later, not evidence of an existing RDS deployment.

### Retained backup evidence

```text
Path: C:\Users\DELL\AppData\Local\Temp\WhatNotCutover-lmyzuezk\whatnot_app_dev-0004-cutover.dump
Bytes: 31700
SHA-256: 75cbb960eb64b61ebe9aba5f377efe7d4c96018b556502ad43ade30951a08025
pg_restore --list: exit 0; users table data entry present
```

This historical pre-cutover 0004 archive is older than current accounts/admin
recovery. Hash/list does not prove a full restore, current recovery point or durable
storage. No production data should be imported from it. No new backup or restore
was executed. Proposed RPO/RTO values in `PRODUCTION_BACKUP_RECOVERY.md:206` are not
achieved objectives or an approved operational guarantee.

## 5. Smallest corrections and exact closure checks

These are proposals only; no fix was applied. Preserve the original database.

| Priority / blocker | Smallest required correction | Verification procedure |
| --- | --- | --- |
| P0 / release-schema pair and stale QA | Review a single 0009-compatible artifact and approved isolated staging DB; reconcile QA worker code separately. Do not migrate original. Update deployment/backup/readiness instructions that still pin 0008. | Verify name/OID/server, Alembic 0009, four columns/constraints, loaded OpenAPI radius fields and **GET `/api/v1/ready` 200** on the approved target. Confirm no public points were auto-copied; explicitly consent synthetic seller points. |
| P0 / failing checkout/geography regressions | Correct the strict synthetic request expectations and public-point fixtures/old coarse-discovery assertions after confirming the intended contract. Keep stock, idempotency, ownership and privacy checks intact. | Rerun V2–V5; require zero failures and explicit disposition of all skips. Exercise HTTP positive/negative 1/2/3km, every boundary and smaller seller radius, then browser cart-to-order and replay on isolated fixtures. Do not waive errors because most tests passed. |
| P0 / ten-person bootstrap/access | Approve ten identities/roles and update exact-count bootstrap guard/tests plus five-user docs/template assumptions. Add no accounts during this audit. | Synthetic 10 accepted/9 and 11 rejected, wrong DB/OID/role/schema refused, duplicate bootstrap refused; approved empty staging bootstrap transaction succeeds. Separately prove invited login and uninvited denial; approve how admin is counted. |
| P0 / private HTTPS/AWS configuration | Review/render avetest host/TLS/perimeter inputs and inspect actual target IAM/SG/secrets/DB configuration under separate authorization. | On approved Linux target: `nginx -t`; `systemd-analyze verify` for reviewed units. From authorized/outsider clients verify HTML, SPA deep links, APIs and public listing access; correct TLS chain/hostname, HTTP redirect/renewal, headers/CORS, forged forwarding denial and no reachable 8000/5432. No deployment is authorized by these examples. |
| P0 / operational recovery and monitoring | Approve and implement actual backup/restore, RPO/RTO, responders, log retention, timers and alert delivery. Reconcile 0009 in every runbook. | Restore the actual pilot backup to a new verified isolated target, reconcile rows/audits/schema, time validated app recovery; demonstrate backup-failure/5xx/worker/mail/cert alert receipt and recovery. Keep outbox/mail effects controlled. |
| P0 / privacy and business scope | Supply owner-approved contact/notice/data handling and expressly confirm property/Creative and no-payment scope for ten users. | Witness complaint/access/deletion and incident procedures; review shared-device draft handling and public-point consent/revocation. Explicitly exclude COD/UPI recording or scope a separately approved implementation; never claim settlement. |
| P1 release gate / security and artifact | Review existing diff and scan frozen runtime/tooling graph and artifacts with current tools; retain a source/artifact/configuration manifest. | Zero untriaged High/Critical dependency or live-secret findings; bounded accepted residual risks with owner/expiry. Verify a clean reproducible build against reviewed manifest, no development secrets/QA controls, and rerun full suites. Do not commit/push as part of this audit. |
| P1 release gate / ten-user HTTPS UAT | Execute witnessed buyer/seller/admin, property and Creative acceptance on the approved HTTPS release with synthetic staging data first. | Register invited buyer/seller; create/edit/reapprove/reject; GPS allow/deny/timeout/manual/saved address; 1/2/3km positive/empty/source switch; cart, authoritative order totals/stock, seller transitions, buyer receipt/dispute, admin visibility and cross-account denial. Record browser/OS/release/schema/role/status/redacted evidence. No real-user data or payment credentials in reports. |

The existing five-user plan also describes sample-only buyer radius and fixed
0008 bootstrap/readiness; these statements are superseded by source and fresh
evidence, but their documents were deliberately not rewritten by this audit.
`FIVE_USER_PILOT_TEST_PLAN.md:19`, `AWS_PILOT_DEPLOYMENT_RUNBOOK.md:112`,
`PRODUCTION_BACKUP_RECOVERY.md:117` and `PRODUCTION_MONITORING_RUNBOOK.md:14`
must not be followed literally for this current release.

## 6. Changes and limitations

Added only audit/report material:

- `docs/BETA_FINAL_READINESS_AUDIT.md` — this release decision.
- `docs/security/audit_beta_readonly.py` — reusable read-only identity/schema/count checks.
- `docs/security/audit_beta_isolated_tests.py` — guarded disposable test-schema adapter; now refuses by default following the scope error.
- `docs/security/evidence/beta-final-readonly.json`, `beta-final-persistence.json`,
  `beta-final-command-summary.json` — sanitized observations and results.

Ignored `beta-final-audit-*.log` diagnostics, normal build outputs/TypeScript cache
and the retained synthetic test schema/TEMP fixture copy were generated. Existing
application/configuration/test sources and all prior dirty-tree work were preserved.

Not executable/complete here: additional fresh-database migration/race tests (no
CREATEDB; no retry of failed isolated-server startup), actual Linux Nginx/systemd,
current CVE scanner clearance, AWS resource/configuration attestation, TLS/private
ingress, production restore/alert/mail proof and final real-device HTTPS UAT.
An initial combined read-only diagnostic stalled; it supplied no passing evidence
and was replaced by the successful file-based read-only helper and bounded curl
probes. Its audit-owned Python process was terminated; no application service or
unrelated PostgreSQL session was terminated.

**Exact next implementation step:** after owner review, reconcile the intended
0009 release/staging schema contract and correct its failing regression fixtures,
without changing the original database. In the same separately approved preparation
scope, remove the strict five-user bootstrap/runbook mismatch while retaining all
security guards. Rerun the gates above before any deployment/admission decision.

**NO-GO — critical release gates remain unsatisfied.**
