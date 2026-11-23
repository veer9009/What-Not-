# Local beta fixes: Tasks A, B and C

Scope: local checkout `ui/sage-premium-redesign`, starting HEAD `15a8430`. All prior uncommitted recovery/registration work was preserved. No commits, pushes, migrations, existing database changes, real email, AWS, EC2 or live endpoint access.

## Findings and implementation

### A: Seller location and readiness

Dispatch coordinates, dispatch confirmation, public coordinates and consent were already stored on SellerProfile. Products reference that profile; ordinary product creation never requested repeated location confirmation. No product-level location record or migration is needed.

Shop profile setup now offers device location first, with manual coordinates inside an expandable fallback. A seller explicitly confirms dispatch before saving a new/unconfirmed/moved point. A separate, unchecked consent allows using that selected point for public discovery. A private dispatch point is never copied publicly without this consent. Sellers can leave it private and choose a separate public point using the existing controls. A PIN code is not converted to coordinates.

The profile, dispatch confirmation and optional public consent reuse the existing APIs in one save flow. Successful intermediate writes are retained for safe retries; failures do not create another shop or claim completion. The last successful server snapshot updates consent status after partial failure without discarding the retry form.

Confirmed privacy defect: both dispatch mutation paths could retain prior public-location consent after the private dispatch moved. Both now clear all four public fields on an actual coordinate change. Numerically unchanged coordinates and ordinary profile edits preserve consent. The seller can explicitly select and consent to a public point again.

Dashboard readiness requires confirmed valid dispatch, confirmed valid public coordinates with current consent version, product APPROVED status, active listing and positive stock. The display explains that buyer radius, account authorization and checkout checks remain authoritative. Incomplete shops have a Complete shop location action. No private coordinates are added to buyer responses.

**Unchanged policy gap:** SellerProfile.is_verified is currently a badge, not a separate seller approval gate. This task does not invent a seller approval workflow, change the flag or silently hide unverified sellers. Owner policy approval remains required before changing this behavior.

### B: Images

The Nginx template now allows 5 MiB for anchored positive-ID upload/replacement URI patterns. Uploads send raw File bytes, not multipart encoding, so there is no multipart body overhead. Headers are not part of client_max_body_size. The backend remains authoritative at exactly 5 MiB and preserves streaming, decode, type, dimensions, animation and metadata checks. Other URIs retain the server's 256 KiB limit. GET image metadata shares the upload URI and therefore its location limit; no allowed methods were removed. Rate limits, access restrictions, forwarding headers and timeouts remain intact.

Confirmed preview defect: the frontend creates blob: URLs for selected-file previews, but the template's CSP prohibited them. Only img-src gains blob:; the remaining CSP directives are unchanged.

Image upload/replacement API paths, managed references, object keys, signed URL generation, primary-image card/detail rendering and image fallback required no application changes. Existing responsive 4:3/contain behavior was retained. No substitute images or maps were added.

**Unresolved deployment conditions:** Production intentionally forbids local image storage; valid production storage and delivery origin must already be configured by the operator. Incorrect origin, missing objects/permissions, expired image capabilities or proxy configuration can still produce image errors. No production storage configuration was changed and no live image fix is claimed.

### C: Frontend isolation

The fixed session BroadcastChannel name allowed native Node channels to deliver logout messages across unrelated Vitest workers. Test setup now installs a per-file in-memory transport before application imports. It retains static application singleton listeners across cases, closes test-created peers, restores baseline handlers and invalidates pending deliveries when resetting.

Dedicated integration tests load two actual client modules and verify same-context cross-tab logout and isolation from another simulated browser context. Production client/auth code is unchanged. Expiry, unauthorized routing and location assertions are retained; no arbitrary sleeps were added.

The helper models the message/close behavior used by this app with microtask delivery. It does not establish native browser task timing or cross-process behavior. The earlier historical Longitude failure is consistent with cross-worker invalidation, but its original sender was not recorded.

## Independent review

Read-only agent review found no actionable defects in the Nginx/test-transport changes. A separate reviewer found inaccurate consent status after partial existing-profile saves; this was fixed with the snapshot callback and a fail-first regression. Re-review found no further actionable findings. Reviews do not replace browser, PostgreSQL or EC2 validation.

## Verification

All commands below are local. Counts are per command; overlapping test executions are not additive.

From `backend`:

```powershell
.venv/Scripts/python.exe -B -m pytest tests --ignore=tests/persistence --ignore=tests/session_integration -q -p no:cacheprovider --tb=short
```

Result: **503 passed, 0 failed, 0 skipped**. Existing database-backed suites were excluded rather than connected. The new onboarding integration uses only a disposable in-memory SQLite database and real services/commits across fresh sessions. Its copied-table SQLite adaptations do not validate PostgreSQL row locks, concurrency or migration execution.

From repository root:

```powershell
node node_modules/vitest/vitest.mjs run src/pages/SellerReadiness.test.tsx src/pages/SellerProfileLocation.test.tsx src/Marketplace.test.tsx --pool=threads --maxWorkers=2 --testTimeout=15000 --no-cache --reporter=dot
```

Result after all seller fixes: **50 passed, 0 failed, 0 skipped**.

```powershell
node node_modules/vitest/vitest.mjs run src --pool=threads --maxWorkers=2 --testTimeout=15000 --no-cache --reporter=dot
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build --config vite.config.ts
```

Broader frontend result: **458 passed, 0 failed, 0 skipped, across 49 files** (411.63 seconds). This includes location discovery, authentication/session lifecycle, related APIs, recovery, image handling and seller workflows. TypeScript and the final production rebuild both passed after the final application changes (exit 0). Source tests exclude five existing scripts that overwrite earlier HTML evidence.

Independent final run of the three new backend regression files:

```powershell
.venv/Scripts/python.exe -B -m pytest tests/test_seller_location_consent.py tests/test_seller_onboarding_flow.py tests/test_image_proxy_limits.py -q -p no:cacheprovider --tb=short
```

Result: **29 passed, 0 failed, 0 skipped**.

Expected fail-first evidence was observed before fixes: seller consent 7 failures/4 passes; new readiness UI 6 failures/2 passes; proxy limit 2 failures/14 passes; CSP preview 1 failure/16 passes; native channel regression 1 failure; partial-move status 1 failure/8 filtered skips. Existing seller GPS/marketplace fixtures were updated for explicit dispatch confirmation after their failures were observed. Final results supersede these development runs.

## Operator verification on EC2 this evening (not performed)

1. Confirm the exact reviewed release and actual schema revision; these fixes need no new migration. The pre-existing uncommitted recovery migration remains outside this task.
2. Review/render the Nginx template, run nginx -t before any separately authorized reload, verify access restrictions/rates/CSP, then check raw upload and replacement below/at/above 5 MiB and that unrelated endpoints retain tighter limits.
3. Verify the existing approved image provider, HTTPS delivery origin, object permissions and persistence without exposing credentials. Check returned image HTTP status and expiry behavior. Do not expose the private bucket or disable image capabilities.
4. Exercise one seller onboarding, explicit public consent (or separate public point), two products, pending moderation exclusion, admin approval, stocked/active nearby buyer visibility, consent revocation and moved-location re-consent. Confirm private coordinates are absent from buyer JSON.
5. Verify GPS denial/manual fallback, image previews/cards/details/fallback, and seller/buyer layouts at 390, 768 and 1440 pixels in real browsers. Confirm intended cross-tab logout and expiry behavior.

No Nginx executable was available locally. An optional isolated Chrome/CDP check against an ephemeral local static server stalled during startup before completing any layout assertions: **0 browser layouts verified**. No EC2, native browser layout, PostgreSQL concurrency or migration execution verification is claimed. The live discovery/image incident remains unverified until sanitized server/browser evidence is collected by an authorized operator.

Final Git status: branch `ui/sage-premium-redesign`, HEAD `15a8430`; **26 modified tracked files and 25 untracked files**, with nothing staged. The starting 20 modified/14 untracked files remain present; this task modifies six additional tracked files and adds eleven files. `git diff --check` passed (exit 0). No commit, push, merge or deployment was performed.

## Exact files changed by this task

| File | Purpose |
| --- | --- |
| `backend/app/services/sellers.py` | Revoke public consent on actual dispatch moves. |
| `backend/tests/test_seller_location_consent.py` | Focused move/same-point/privacy regressions. |
| `backend/tests/test_seller_onboarding_flow.py` | Real service persistence/moderation/discovery flow in disposable SQLite. |
| `backend/tests/test_image_proxy_limits.py` | Scoped upload limits, inherited controls and preview CSP contracts. |
| `deploy/nginx/whatnot.conf.template` | Image-route 5 MiB limit and blob image previews. |
| `src/components/ShopProfileForm.tsx` | One-save seller setup, explicit consent, fallback and safe partial retry. |
| `src/location/shopReadiness.ts` | Shared seller setup-readiness guidance. |
| `src/pages/SellerPages.tsx` | Readiness display and profile integration/current consent snapshot. |
| `src/pages/SellerReadiness.test.tsx` | Onboarding, privacy, partial retry, dashboard and repeated product creation. |
| `src/pages/SellerProfileLocation.test.tsx` | Existing GPS tests now assert explicit dispatch confirmation and no automatic public sharing. |
| `src/Marketplace.test.tsx` | Profile fixtures/requests reflect explicit confirmation; actor/verification restrictions retained. |
| `src/test/setup.ts` | Install and reset deterministic test channel transport. |
| `src/test/broadcastChannel.ts` | Isolated transport and singleton-safe lifecycle. |
| `src/test/broadcastChannel.test.ts` | Delivery, context isolation, reset and listener regressions. |
| `src/api/crossTabSession.test.ts` | Actual client shared-context logout and unrelated-context isolation. |
| `docs/superpowers/plans/2026-11-23-local-beta-fixes.md` | Focused implementation and verification plan. |
| `docs/security/LOCAL_BETA_FIXES_2026-11-23.md` | Results, policy gap and operator follow-up. |
