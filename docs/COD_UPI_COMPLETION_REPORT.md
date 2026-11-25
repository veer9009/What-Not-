# COD and direct UPI completion — 25 November 2026

**Latest investigation: expected local app activity confirmed; business-table snapshots match. GO for the authorized 57-file feature-branch commit/push.** The user confirmed the seller sign-in around 08:38:45 IST. SELECT-only auth/quota projections reproduce all three earlier fingerprints using unchanged current business tables. The isolated recheck left the original database unchanged. The temporary stop and its resolution are documented below; no production action is authorized.

Branch: `ux/permanent-sidebar-step1-20261124`

Baseline HEAD: `9db87f1a10fe1f3d0985d0c44bc57cc2aaa98320`

This report supersedes the earlier statement that authenticated payment behavior had not been exercised. The resumed verification run had matching original-development fingerprints; the later investigation explains all recorded fingerprint differences as auth/quota snapshot differences, with the morning seller login now confirmed by the user. Exact historical browser/PID logging was unavailable and is not claimed. The authorized migration and workflow verification use a separate owned local PostgreSQL cluster. No commit, push, merge, deployment, production migration or actual money transfer was performed.

## Incremental files

| File | Change in this completion task |
|---|---|
| `backend/app/services/payments.py` | Reject conflicting confirmation retries after checking the original reviewed state; preserve identical retries. |
| `backend/tests/persistence/test_payments.py` | Two real-PostgreSQL regressions for both conflicting retry directions, identical retry timestamps and single audit event. |
| `src/components/PaymentPresentation.tsx` | Shared COD truck/UPI phone icons and accurate recorded-status labels, including “Payment reported.” |
| `src/pages/PaymentsPage.tsx` | Native labelled COD/UPI radio cards and short descriptions; shared method/status presentation; explicitly unverified buyer report; page-matched layout-time focus restoration after saves/pagination. Existing request payloads and permissions remain. |
| `src/pages/SellerPayments.tsx` | All Payments/COD/UPI filters for loaded records, unchanged summary scope, method icons, visible reported reference, unverified status, View details label and summary accent hooks. |
| `src/styles/payments.css` | Payment-scoped blue/green/amber accents, responsive labelled choices, radio sizing protected from the existing full-width input selector, filter controls, wrapping and focus styles. |
| `src/pages/PaymentsPage.test.tsx` | Explicit method choice/icon/description/payload coverage and asynchronous pagination-focus assertions. |
| `src/pages/SellerPayments.test.tsx` | Loaded-page filtering, unchanged totals and no-match/reset coverage. |
| `docs/superpowers/plans/2026-11-24-cod-upi-completion.md` | Approved scope, execution plan and evidence ledger. |
| `docs/COD_UPI_COMMIT_INVENTORY.md` | Every normal modified/untracked file, inherited versus incremental changes, and proposed exclusions. |
| `docs/COD_UPI_COMPLETION_REPORT.md` | This report. |

214 of 216 checkpointed backend files match their task-start hashes. A read-only reviewer identified one backend retry-contract defect: an already-confirmed payment accepted any expected_status. Two parameterized real-PostgreSQL regressions first failed (DID NOT RAISE), then a narrow service correction required the original reviewed state for a duplicate confirmation. Identical retries retain their timestamp and single audit event; conflicting retries return 409. The existing routes, schema, migration, authentication, location source, imagery, brand assets and global theme remain unchanged. Earlier uncommitted UX/backend work remains intact and is separately inventoried.

## Exact API failure and isolated migration

The seller calls `GET /api/v1/payments?offset=0&limit=50`, using the existing same-origin client. The normal Vite development proxy targets `http://127.0.0.1:8000`. The existing configured development database is strictly loopback PostgreSQL on port 5432, named `whatnot_app_dev`, at revision `0010`; `order_payments` is absent. The app/payment schema expects revision `0013`.

The isolated reproduction used valid local credentials: at `0010`, Payments returned HTTP **503** with sanitized `{"detail":"Storage operation is unavailable"}` and the actual backend logged **`sqlstate=42P01`**, PostgreSQL's undefined-table error. The server was running and authentication succeeded. This establishes missing migrated storage, rather than a connection or authorization failure, for the reproduced payment error. Unauthenticated requests correctly return 401 separately.

A new physical PostgreSQL cluster was bound only to `127.0.0.1`, on a free port distinct from the existing cluster. Its actual `data_directory` was verified before use. A randomly named development database used a least-privilege app role without superuser, CREATEDB, CREATEROLE, replication or BYPASSRLS privileges. Only that database received the existing migration chain: `0010 → 0011 → 0012 → 0013`. No migration script was rewritten. Five seeded isolated test accounts survived the upgrade; `order_payments` exists; Alembic schema check reported no new upgrade operations; readiness and authenticated Payments both returned **200**.

Owned FastAPI and Vite servers used process-local configuration and a temporary ignored proxy config. The original `.env`, port-8000 backend, existing port-5173 servers and original database configuration were not repointed. The normal original development service therefore still needs a separately reviewed operator migration if it is to serve Payments; this task proves the fix in the requested isolated environment.

Final preservation, shutdown and workflow evidence: [local-results.json](security/evidence/cod-upi-completion-2026-11-24/local-results.json). Private credentials and retained local database files are ignored and excluded from the proposed commit; they are not included in this report.

## Real backend workflows and limits of the evidence

**Passed against the actual isolated backend**, using two server-priced INR250.00 orders (COD order #1, UPI order #2). Buyer method choices persisted after reload. UPI reference reporting produced BUYER_REPORTED with no confirmation timestamp; only the owning seller's separate receipt action produced SELLER_CONFIRMED. Seller and buyer final views and Admin final metrics agree: order value INR500.00; COD INR250.00; UPI INR250.00; confirmed collections INR500.00; platform revenue INR0.00.

Actual negative checks: unauthenticated read401; buyer self-confirm403; another buyer/seller read403; another seller confirm403; COD confirmation before delivery409. Both confirmations were replayed through the actual API: timestamp unchanged, status SELLER_CONFIRMED, and exactly one PAYMENT_CONFIRMED audit row per order. Both supported delivery transitions and the method/report/confirm persistence path were exercised. COD/UPI filters showed only the matching loaded record while the summary remained INR500.00. Native keyboard Tab from Cancel to Confirm collected and Enter activated receipt confirmation.

Browser execution resumed the same persisted orders after tooling failures and a real auth-rate-limit429; no quota was cleared and no policy was weakened. Completed stages were checked against actual backend state before resuming. Browser logins ultimately used the normal authentication API plus real refresh-cookie restoration; the UI sign-in form itself is not claimed as independently verified by this dedicated browser run. Existing frontend/auth/backend suites cover it separately.

The resumed run's original development database public-table row/count/content fingerprint was unchanged before/after verification. The interrupted run had reported a different fingerprint; its evidence is retained as `interrupted-local-results.json`. Read-only investigation could not reconstruct that earlier baseline by excluding new quota windows. Its cause remains unproven, and this report does not claim the database was unchanged throughout the previous session. No original database repair, quota deletion, migration or rollback was performed. Owned servers and the separate PostgreSQL cluster are stopped; isolated database files are retained privately for review.

The dedicated browser script never fulfills an API request with a synthetic response. Order placement and supported seller delivery transitions use authenticated calls to the existing API; method selection, buyer reference reporting, seller review/confirmation, history refresh and role screenshots use the actual React UI against FastAPI/PostgreSQL. Accounts, shop, product and address are explicitly labelled local test fixtures. The recorded UPI reference is a local test reference; no bank transaction or actual transfer is claimed.

Buyer reporting and seller attestation are distinct records. COD confirmation is eligible only after delivery/completion; delivery alone does not confirm payment. Repeated authorized confirmations use the existing idempotent behavior, retaining the original confirmation timestamp rather than creating another financial event. Audit multiplicity is checked independently in PostgreSQL.

## Financial scope

Seller summary cards cover **all records on the currently loaded page, up to 50**, independently of the COD/UPI record filter. Filtering never fetches all seller orders and never turns these into account earnings or lifetime revenue.

- **Displayed Orders Value:** gross order amounts for every loaded record, including cancelled/rejected orders.
- **Confirmed Received:** loaded SELLER_CONFIRMED amounts, including later-cancelled orders; external refunds are not deducted. This is seller-recorded collection, not bank verification.
- **Awaiting Collection:** loaded PENDING/BUYER_REPORTED COD/UPI amounts, excluding CANCELLED/REJECTED orders and unrecorded methods. Buyer reports remain unverified.

The exact-decimal calculator is unchanged. Genuine successful empty pages show zero page totals. Loading, failed requests, unsupported summary input and page transitions show **Unavailable** and withhold stale financial records. There is no invented Needs Review state/card. Admin metrics are the existing authorized aggregate endpoint, distinct from the seller's page-level calculation. Platform revenue remains zero under the no-commission model.

## Verification

| Check | Actual result |
|---|---|
| Backend complete suite | **1,055 passed in 363.53s** (see `cod-upi-resume-backend-final.log`); includes payment ownership, idempotence, concurrency and migration tests. |
| Frontend new-feature RED run | 4 expected failures / 15 passes before implementing radios and filters. |
| Frontend focused payment/API/route/summary run | **33 passed**, 5 files. |
| Final focused buyer/seller run after focus correction | **19 passed**, 2 files. |
| Complete final frontend suite | **522 passed**, all **63** normal test files, in 490.89s; exact file list obtained from normal tracked/untracked source files, project config preserved. |
| TypeScript | Standalone `tsc -b --pretty false`: passed; also passed in production build. |
| Production build | Passed; existing main-chunk >500kB warning remains. |
| Isolated migration / authenticated endpoints | Actual 0010 503/42P01 reproduction; 0013 readiness200/payment200; accounts preserved; schema check clean. |
| Real browser and viewport checks | Passed, 40 distinct screen/width combinations at **320, 375, 390 and1280px**; no horizontal overflow/main-boundary collision. 30 review PNGs; native receipt keyboard action passed. Desktop/mobile seller frames visually inspected. Full-page capture omits the scrollbar gutter at some widths, so PNG content width can be 15px smaller than the emulated viewport. |
| Git diff | `git diff --check` passed; existing Windows LF/CRLF notices only. |
| Fresh read-only review | One material CSS-specificity finding; corrected with scoped radio sizing after the actual browser overflow failure. One additional Important retry-contract finding fixed with RED/GREEN persistence tests; one pagination minor deferred, described below. |
| Backend preservation | 214/216 checkpoint hashes unchanged; only the reviewed retry service correction and its tests differ. |
| Focused secret scan | No private-key/AWS-access-key/GitHub-token pattern match in inventoried files; ignored credentials/runtimes/dumps/logs excluded. This scan does not guarantee absence of every possible secret format. |

Commands, run using the existing project tools:

```text
backend: .venv\Scripts\python.exe -m pytest -q --tb=short  (fresh final log: cod-upi-resume-backend-final.log)
npm.cmd test -- --run src/pages/PaymentsPage.test.tsx src/pages/SellerPayments.test.tsx src/PaymentRoutes.test.tsx src/api/payments.test.ts src/utils/paymentSummary.test.ts --pool=vmThreads --maxWorkers=1 --testTimeout=60000
npm.cmd test -- --run src/pages/PaymentsPage.test.tsx src/pages/SellerPayments.test.tsx --pool=vmThreads --maxWorkers=1 --testTimeout=60000
node node_modules/vitest/vitest.mjs --config .superpowers/cod-upi-vitest.config.mts --run --pool=vmThreads --maxWorkers=1 --testTimeout=60000 --reporter=verbose
npx.cmd tsc -b --pretty false
npm.cmd run build
backend\.venv\Scripts\python.exe .superpowers/cod-upi-local.py
git diff --check
backend\.venv\Scripts\python.exe .superpowers/cod-upi-inventory.py
```

Initial backend fixture startup inside the restricted sandbox failed with PostgreSQL restricted-token error87. The completed full suite ran outside that restriction against the existing guarded disposable test infrastructure. Early frontend full-suite attempts were interrupted after a focus failure or slow discovery; the final ignored Vitest wrapper imports the existing project config and enumerates all63 normal frontend tests explicitly, and are not reported as passing. Browser helper attempts encountered a real CSS overflow (fixed) and separate Chrome/protocol/DOM-serialization failures in verification tooling (corrected); only the final successful browser evidence can establish workflow completion.

Frontend unit/route/API tests use mocks, as in the existing infrastructure. Prior before screenshots are also labelled mocked-layout evidence. Migration/readiness checks, the complete backend persistence suite and the dedicated browser workflow use actual local PostgreSQL/FastAPI. No mocked payment is claimed as a verified transfer.

## Visual review

[30-screenshot index](security/evidence/cod-upi-completion-2026-11-24/SCREENSHOT_INDEX.md) · [Before/after visual comparison](security/evidence/cod-upi-completion-2026-11-24/comparison.html) · [Actual browser assertions](security/evidence/cod-upi-completion-2026-11-24/browser-results.json). Buyer, Seller and Admin captured at1280/390/320;375 checked for layout. Fixed bottom navigation appears partway down full-page PNGs at the original viewport bottom; it stays fixed at the bottom during normal scrolling. No new sidebar or payment-control overlap was observed in the inspected frames. Screen readers and physical touch devices were not tested.

Earlier seller before/after captures show the shift from long primary disclaimers/blank error content to summary-first records and inline unavailable states. Those historical captures use labelled mocked APIs and are for layout comparison only. New COD/UPI filters, icons, semantic accents and actual persisted status/reference views are captured from the isolated real backend. Test amounts in the new captures are server-priced orders, not fake responses or real customer data.

## Remaining limitations and decisions

- Payment method selection remains the supported **post-order** Payments action, not an unsupported checkout/payment-gateway step.
- No verified seller UPI directory, fabricated UPI ID, generated QR, bank verification, gateway, wallet, escrow, commission, partial payments, automatic refunds or payment-specific dispute settlement.
- References and seller confirmations are attestations; refunds outside the app are not netted from gross collections. Seller-wide totals have no dedicated backend endpoint.
- Automated Chrome emulation and keyboard checks do not replace physical devices or screen-reader testing. Manual assistive-technology testing remains outstanding.
- Existing unrelated forgot-password/Creative Save defects remain outside this completion task. No location/manual-coordinate or Professional Services change was made.
- Build chunk size remains a performance follow-up. Existing production data, schema readiness, external payment settlement and deployment configuration were not verified or changed.

**Feature-branch commit/push: GO under the user's authorization.** The user confirmed the observed morning seller sign-in; the snapshot differences are accounted for by expected login/refresh/quota activity. Business-table snapshot equality and test isolation are verified. The approved scope is exactly 57 files, with all 11 excluded files preserved. This document is the pre-commit verification record; the final Git commit/push result is reported separately. **Production deployment: NO-GO**: production schema/migration, deployment configuration and operational acceptance were neither authorized nor verified. This is a verified local direct-payment record implementation, not bank settlement verification.

Suggested commit message: `feat: complete marketplace sidebar UX and COD UPI payment workflows`.

## Resumed review decisions and limits

- Fixed the Important confirmation-retry contract issue; both parameterized regression cases failed first, then passed in the final complete backend suite. Browser workflows used the running pre-correction process; the final service correction is verified against fresh real-PostgreSQL fixtures in that suite.
- Deferred minor: buyer/admin pagination can briefly show prior-page rows with the new page label before the loading effect starts (`PaymentsPage.tsx`). Seller already guards against this. It does not change persisted records or financial amounts, but the transient presentation should be tightened in follow-up.
- Reviewer set aside mutable-server/device checks, database preservation, pending report placeholders and production readiness. Ruling: actual local browser/fixture evidence and the finalized report cover the authorized local checks; physical-device/screen-reader and production acceptance remain unverified. Treating them as verified would overstate readiness.
- Ruling: user instructions to preserve this dirty branch and await approval override generic worktree, automatic commit and finishing-menu defaults. Cost: the broad inherited diff needs explicit review before staging.
- Ruling: keep the earlier fingerprint failure visible while separately reporting the successful fresh preservation check. Cost: the earlier discrepancy remains an open historical limitation.

Fresh logs: `cod-upi-resume-frontend.log` (522/522), `cod-upi-resume-backend-final.log` (1055/1055), `cod-upi-resume-build.log`, `cod-upi-resume-retry-red.log` and `cod-upi-resume-local.log`. These are ignored local evidence, not commit candidates. The first restricted backend run failed at fixture startup; an intermediate complete-suite run was interrupted when the regression fix became necessary. Neither is claimed as passing.

User subsequently authorized committing and pushing the verified scope to `ux/permanent-sidebar-step1-20261124`. Final pre-commit checks gate that action; merge, force push, deployment and production infrastructure changes remain prohibited.

## Initial pre-commit review and temporary stop — 25 November 2026

All 68 inventory entries were reviewed. The reviewed commit includes 54 application/source/test files and three current payment documents, including migration 0013. The 10 historical/next-phase documents and known temporary browser helper are excluded and preserved byte-for-byte. No secrets, actual credentials, database dumps or generated runtime/release artifacts were identified for inclusion; known ignored local credential values were compared in memory without printing them.

The initial read-only transaction against the verified original loopback development database found revision `0010` and the same public-table fingerprint as the successful resumed verification. A second read-only transaction during this review found a different fingerprint. Revision `0010` and ignored environment-file content hashes are unchanged. Preservation throughout this review interval cannot be confirmed. No direct writes, migration, seed, quota cleanup or repair were performed by the review checks against the original development database.

The buyer/admin pagination display issue remains deferred as described above. This review authorizes no production operation. Excluded historical documents retain their original claims as historical work; this completion report is the current authority. Local screenshot/evidence links refer to retained ignored review artifacts and will not be available in a clean Git clone.

### New preservation failure observed during pre-commit review

- Initial review fingerprint: `ea9cb3384b33d0418696cf509de1dfd6ea6a7df56556b7f72696933015069a8c`.
- Second review fingerprint: `6a93c1d746926ddd77af8ae1252ea9b66db2534d89aa3eab7ef6833c91e701d4`.
- Compared with the previous preserved observation, authentication refresh-token rows increased from 23 to 24, authentication sessions from 5 to 6, and request-quota rows from 62 to 64. Other public-table row counts match that observation; matching counts alone do not prove unchanged row contents.
- These observations are consistent with authentication activity, but the initiating client/process has not been established. Neither the new discrepancy nor the earlier interrupted-session mismatch is declared resolved. No quota was cleared, session deleted, rollback performed or database state restored to conceal the difference.
- Asked whether the local development app was used during this review; the user answered "Not sure." This does not establish the cause or clear the preservation blocker.
- Source/credential review found no security issue or unexpected source change. Fresh pre-commit frontend verification passed **522 tests across 63 files in 695.56s**; TypeScript/build passed (Vite 23.72s) with the existing bundle-size warning. The already-running backend suite completed with **1,055 passed in 1115.71s**, exit 0. These passing results do not clear the original-database preservation blocker.
- No staging, commit, push, merge, force push, deployment or production operation was performed. All 68 working-tree entries remain, including the 11 excluded files. The original database cannot be certified untouched over the full interval; further attribution/investigation is required before reconsidering integration.

Git state at the temporary stop (before the later confirmation): branch `ux/permanent-sidebar-step1-20261124`; HEAD remains `9db87f1a10fe1f3d0985d0c44bc57cc2aaa98320`. No new commit hash exists. Push was not attempted. The target remote branch is `origin/ux/permanent-sidebar-step1-20261124` (absent at the read-only remote check). The index is empty: **28 modified tracked files and 40 untracked files**. Only the two current review documents changed during this review; application sources/tests and all excluded files retain their review-start hashes. `git diff --check` passed.

## Read-only database investigation — 25 November 2026

### Processes and database targets

Elevated, sanitized Windows process enumeration and listener inspection at approximately 08:54 IST found no running Python/Uvicorn backend or Node/Vite frontend and no listeners on 8000/5173. PostgreSQL PID 7084 was listening on 5432; its server start time is 22 November, 21:38:55 IST. `pg_stat_activity` found no other connections to `whatnot_app_dev` during the database inspection. No application process was stopped or restarted by this investigation.

| Process/configuration | Database target | Evidence and limit |
|---|---|---|
| Original PostgreSQL cluster | Contains `whatnot_app_dev` on 127.0.0.1:5432, revision 0010 | Verified server/database identity in a read-only transaction; schema and environment-file content hashes unchanged. |
| Manually launched Uvicorn `app.main:app`, loopback port 8000 | Repository defaults select `whatnot_app_dev` on 5432 | Startup commands found in shell history; they have no database override. The exited process's actual inherited environment cannot be recovered, so this is its configured default target, not a recovered runtime environment. |
| Manually launched Vite (`npm run dev`) | No direct database connection; default `/api/v1` proxy targets 127.0.0.1:8000 | Repository Vite configuration; process is no longer running. |
| Retained isolated verifier runtime 6 | Separate random `whatnot_payments_dev_*` database on 127.0.0.1:49989; API 49990/UI 49991 | Sanitized private-runtime manifest; credentials were neither printed nor committed. |
| Retained isolated verifier runtime 7 | Separate random `whatnot_payments_dev_*` database on 127.0.0.1:54414; API 54415/UI 54416 | Sanitized private-runtime manifest; this verifier stopped at approximately 08:17 IST, before the new 08:38 login. |
| Backend persistence tests | Generated disposable PostgreSQL cluster/databases on a free loopback port | Fixture ignores application `DATABASE_URL`, checks owned data directory and injects the explicit migration/test URL. |
| Backend session integration tests | Designated test database with fixed database-name/OID guard and generated private schema | Guard refuses the original application database; no fallback to it. |
| Generic API/auth unit fixtures | Explicit test Settings without `.env`; auth tests override sessions with isolated fixture sessions | No original-development connection is supplied. |

### Timestamp and log correlation

- A seller session and its initial token were created together at **08:38:45.421038 IST on 25 November**. Their timestamps and eight-hour lifetime match `RefreshSessionService.create`, the ordinary successful-login flow.
- New quota rows classify, by in-memory scope comparison, as the existing seller account's auth scope and loopback auth source in the **08:30–08:45 IST** window. A later source-only auth quota is in the **08:45–09:00 IST** window. No account identity, scope hash, session ID, token or credential was output.
- PowerShell history contains loopback `uvicorn app.main:app --reload --port 8000` and frontend startup commands. Its last-write time is **08:37:47 IST**, shortly before the login. No `DATABASE_URL` override appears in the trailing startup history. Individual history entries do not carry timestamps, so file mtime is supporting context, not proof of a specific command's execution time.
- The interrupted night's additional token timestamps are **23:44:03 and 23:58:19 IST on 24 November**, with matching older-token `used_at` changes and auth quota windows. This is the normal refresh-rotation record pattern.
- PostgreSQL has connection/disconnection logging off, statement logging set to none, duration logging disabled and commit-timestamp tracking off. No contemporaneous attributable HTTP access log was available for the exited manually launched server. The investigation did not enable logging or alter any database/server setting.

### Business-record comparison and exact reconstruction

The investigation used `REPEATABLE READ` plus `SET TRANSACTION READ ONLY`. It recomputed the same per-table row-count/sorted-row-JSON digest and overall SHA-256 used by the original verifier. In SELECT projections only, it excluded later auth rows/quota windows and projected later token-use/session-revocation timestamps to their earlier NULL values. **No stored row was deleted, updated or restored. All 23 non-auth/quota tables were used verbatim from the current snapshot.**

Those projections reproduce all three recorded fingerprints exactly:

| Recorded snapshot | Exact reproduced fingerprint | Changes sufficient to reproduce it |
|---|---|---|
| Interrupted verification | `3168f77e983ac69c425610ce86dc46eabc720fc06a55149609e26b8dafcb0874` | Project auth state before the late-night rotations and omit subsequent auth quota windows. |
| Successful resumed/pre-commit baseline | `ea9cb3384b33d0418696cf509de1dfd6ea6a7df56556b7f72696933015069a8c` | Omit the morning login/session/token and morning quota windows. |
| Second pre-commit observation | `6a93c1d746926ddd77af8ae1252ea9b66db2534d89aa3eab7ef6833c91e701d4` | Keep the morning login but omit the later 08:45 auth-source quota window. |

The current fingerprint is `ff1a51aee9ae4fd180b506fe0834fb57caf3c24fae00f283e2e522b42d1ea96f`. **No persistent business-record difference was found against any recorded baseline snapshot**, including users, sellers, products/images, addresses, orders/items, Creative/Property records, notifications, outbox, audit events and schema revision. Snapshot comparison does not prove that no transient change-and-reversal occurred between observations; it establishes equality of the observed non-auth contents. The earlier failed reconstruction checked only quota windows; it missed token-use/rotation changes. Its historical failure is retained above but is no longer the current finding.

### Verification isolation and conclusion

The real-browser verifier explicitly passes its random isolated database URL to an owned FastAPI process using Settings without `.env`, and its temporary Vite proxy targets that owned API. Its only original-development connection is the read-only preservation snapshot. The payment browser therefore did not run against the original database. Source inspection also confirmed the disposable persistence fixtures and guarded session-integration database.

A fresh focused run removed application database/WHAT_NOT/PG environment variables before invoking the payment, concurrency and migration tests. It passed **18 tests in 38.51s**, exit 0. The original development database's complete public-table fingerprint was `ff1a51…ea96f` both before and after. This directly verifies isolation of that test run. Subsequent verification should use the same disposable fixtures and explicit isolated server/proxy configuration; do not point a browser verifier at a manually started port-8000 service.

The database and code evidence account for the differences as ordinary login/refresh/quota activity, and no verification path inspected writes to the original application database. An independent read-only evidence reviewer validated the reconstruction and required confirmation of the login or attributable request logs before clearing the gate. **The user then confirmed: "Yes, I signed in around then"**, in response to the question identifying the seller sign-in at 08:38:45 IST. This supplies the missing confirmation of expected manual application use. The exact historical browser/PID remains unrecoverable because contemporaneous logs are unavailable; no claim of forensic client/PID attribution is made. The user confirmation, exact business snapshot matches, checked isolated verification targets and passing isolated recheck clear the conditional integration gate.

The 54 application/test files still match their reviewed hashes; all 11 excluded files are byte-identical. Only this report and the inventory changed. The previously complete 1,055-backend/522-frontend suites and build remain applicable to the unchanged application tree. Investigation helpers, sanitized evidence and raw verification logs are ignored and excluded from the 57-file candidate scope. No database records, schema, environment files or production infrastructure were modified by this investigation; no credentials/session tokens were exposed.

### Authorized integration decision

GO for the exact 57 approved candidate files and a normal push to `ux/permanent-sidebar-step1-20261124`, using commit message `feat: complete marketplace sidebar UX and COD UPI payment workflows`. Preserve all 11 excluded files byte-for-byte. User confirmation supersedes the earlier uncertain answer and temporary stop. No original database row was repaired, removed or altered by the investigation; the authentication rows generated by ordinary app use remain present. The original schema remains 0010. No migration against that database, merge, force push, deployment or production infrastructure change is authorized.

Deferred minor: buyer/admin pagination can briefly pair previous-page rows with the newly selected page label; it remains documented and unchanged. The fresh 18-test isolated recheck and earlier complete 1,055-backend/522-frontend suites/build validate the same unchanged application files. Final staging must match the reviewed 57-path manifest exactly; ignored credentials, clusters, logs, screenshots and forensic helpers remain excluded.
