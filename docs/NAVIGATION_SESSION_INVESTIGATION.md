# Seller navigation and session investigation

16 November 2026. Existing working tree preserved. No application behavior, environment, schema, real customer record, infrastructure, deployment, commit or push was changed by this investigation.

## Status

Navigation: existing code implements the requested consent/ownership/status policy. The current records do not satisfy it. No safe code defect was confirmed and no authorization bypass was made.

Session continuity: **unresolved pending security/schema approval**. A valid session survives tab changes and three minutes of inactivity, but the application has only a 15-minute, non-renewable access-token session. The user confirmed the issue occurs in the same tab after approximately 15 minutes or longer since login. That matches the actual configured expiry and frontend expiry/401 paths. An eight-hour renewable beta session is not implemented.

## Navigation root cause

PostgreSQL-enforced read-only inspection of `whatnot_app_dev`, schema 0009, found four orders:

| Order | Status | Valid saved point | Buyer point confirmation | Seller navigation outcome |
| --- | --- | --- | --- | --- |
| 1 | PLACED | Yes | No | Seller fulfillment is forbidden until acceptance. |
| 2 | COMPLETED | Yes | No | Seller fulfillment is no longer available. |
| 3 | COMPLETED | Yes | No | Seller fulfillment is no longer available. |
| 4 | DELIVERED | Yes | No | Seller may read postal delivery details; precise navigation is withheld. |

No order has a `DELIVERY_LOCATION_CONFIRMED` audit marker from its owning buyer. Valid saved coordinates alone do not establish consent. Evidence: `security/evidence/navigation-session-inventory.json`; no precise coordinates, names, phones, credentials or tokens were recorded.

The existing flow is:

1. Buyer opens an order in PLACED, ACCEPTED, PREPARING or OUT_FOR_DELIVERY, clicks **Review delivery location**, reviews the saved point, then explicitly confirms it.
2. `OrderService.confirm_delivery_location` requires the owning active BUYER, eligible status and equality with the immutable saved order address. It stores only a consent marker, not coordinates, in the audit event.
3. Seller opens an owned order in ACCEPTED, PREPARING, OUT_FOR_DELIVERY, DELIVERED or DELIVERY_DISPUTED and clicks **View delivery details**. The authenticated fulfillment endpoint exposes a point only after buyer confirmation.
4. `deliveryDirections` validates numeric coordinate strings/ranges and URL-encodes a Google Maps destination. The link uses a new tab and `noopener noreferrer`.

Unrelated sellers/buyers are denied. Public order reads omit precise coordinates. PLACED, CANCELLED, REJECTED and COMPLETED remain unavailable for seller fulfillment even if a prior consent marker exists. The user referred to pending orders; this order model calls that status **PLACED**, not PENDING. The existing policy does not allow first-time confirmation after DELIVERED; reopening completed/delivered orders or retroactively granting consent would be a policy change. No such change was made.

## Session root cause

- The current configured lifetime is **15 minutes**. `Settings.access_token_expire_minutes` defaults to 15 and is bounded to 1–60. `create_access_token` issues `sub`, `iat`, `exp`; the login response reports the same TTL in seconds.
- `AuthProvider` sets an absolute frontend deadline at login. Its timeout clears the session when that deadline is reached; protected JSON/upload 401s also clear it. Background timer throttling can delay the callback until the tab is active again; the backend expiry remains effective regardless.
- There is no visibility/focus handler that logs users out. Simulated hidden/visible, blur/focus and 180 seconds of elapsed time preserve valid SELLER, BUYER and ADMIN sessions. Seller/buyer requests retain their bearer header on order reads after returning; ADMIN uses its identity endpoint rather than the buyer/seller order endpoint in the final lifecycle check.
- Access tokens are held only in module memory. Reloading/opening a new tab requires login; however the user explicitly confirmed a same-tab case, so reload is not the explanation for this report.
- There are no refresh tokens, session-renewal endpoints, auth-session tables, server logout endpoints or per-session revocation state. JSON fetch uses `credentials: 'omit'`; uploads use `withCredentials=false`; CORS has `allow_credentials=False`. No auth cookie is configured.
- Logout clears the current browser token and guards against late responses. It does **not** invalidate a copied access token on the server. Active-user checks and current database roles still apply on each authenticated request, but this is account-level enforcement, not refresh-session revocation.
- The same session architecture applies to all roles. Tokens contain no role claim; authorization loads the role from the database. Existing generation guards reject late responses from old credentials; public login failures do not clear a valid protected session. No incorrect 401 handling was reproduced in the tested code.

The confirmed cause of expiry after the reported total login time is the short non-renewable session. It is not safe to satisfy eight-hour continuity by lengthening a bearer token, caching passwords, storing a token in localStorage, ignoring expiry/401, or silently reissuing tokens from an expired bearer.

## Proposed renewal design — NOT implemented; approval required

This is the concrete proposed implementation scope, not a change to existing policy:

1. Add a reviewed next migration for an `auth_sessions` table: random session ID, user ID, refresh-token digest/family, creation time, absolute expiry, rotation state and revocation timestamp. Store only a cryptographic digest of a high-entropy opaque refresh credential. Do not store plaintext refresh tokens or personal delivery data. No migration file or table has been created.
2. Retain the existing 15-minute access-token TTL. Add a session identifier to newly issued access JWTs and check that session's active/revoked/absolute-expiry state on every protected request. This enables immediate server-side logout/revocation rather than waiting for access expiry. Existing JWT signing configuration can be reused; no additional signing secret is proposed.
3. Use an approximately **eight-hour absolute login session for buyer/seller beta accounts**, subject to owner approval. Keep ADMIN at the existing short session limit initially; extending administrative sessions requires its own explicit policy decision. Expiry must not slide indefinitely.
4. Implement refresh and logout endpoints. Issue the refresh credential in an HttpOnly, Secure production cookie with SameSite restrictions and a narrow auth path. Refresh must recheck user activity, beta admission and session validity; rotate credentials atomically, detect reuse and revoke the affected session/family. Logout revokes server state and clears the cookie. No localStorage access/refresh token or password persistence.
5. Prefer the existing production same-origin `/api/v1` deployment. Review development proxy behavior separately. If deployment truly requires cross-origin credentialed cookies, approve explicit origin allowlisting, credentialed CORS and CSRF/origin protections before enabling them; never use a wildcard credentialed origin. Cookie refresh/logout must have CSRF/origin defenses even when using SameSite.
6. Frontend keeps the access token in memory, restores it through a refresh request after reload, and uses a single shared refresh promise to deduplicate concurrent requests. Each original request gets at most one renewal/retry. Failed or expired refresh stops the loop and clears auth. Do not replay non-idempotent order mutations blindly: retain existing idempotency keys/reconciliation, verify session generation and owner, and use the same original order request. Upload retry must preserve cancellation/session guards and must not silently duplicate a file.
7. Serialize rotation and handle concurrent tabs deliberately (browser refresh lock plus server rotation rules); broadcast logout without broadcasting credentials. Never clear a new session because an older request finishes late.
8. Add isolated PostgreSQL tests for refresh rotation/reuse, concurrency, expired/revoked sessions, logout invalidation, suspension/current roles, failed-refresh limits and eight-hour boundaries. Add frontend tests for one concurrent renewal, one retry maximum, buyer/seller/admin sessions, cookie restore, stale logout responses, orders/uploads after renewal and logout across tabs. Rehearse and approve the migration separately before applying it to any existing database.

Compatibility: binding access JWTs to sessions changes the token contract. The rollout must decide whether to require a fresh login for existing beta sessions (recommended) or provide a short, explicitly bounded transition; do not silently accept legacy stateless tokens indefinitely. Cookie/CSRF configuration, the buyer/seller lifetime and unchanged admin lifetime are security-policy decisions for approval. No implementation begins until that approval is supplied.

## Verification and limits

- Relevant frontend: **98 passed**, 6 files, exit 0. Includes the new 5 lifecycle checks, existing AuthContext/client, application role routing, order navigation and delivery support. Evidence: `security/evidence/navigation-session-frontend.json`; log: `navigation-session-frontend.log`.
- Final lifecycle-only rerun after narrowing the ADMIN probe to its identity endpoint: **5 passed**, exit 0. These overlap the initial 98 and are not an additional five distinct tests. Evidence: `security/evidence/navigation-session-lifecycle-final.json`.
- Relevant backend final: **102 passed**, exit 0. Includes 21 new synthetic policy cases, auth security/schemas, delivery-location/order schemas and API contracts. Log: `navigation-session-backend-verified.log`.
- The first new policy test attempt had **5 failures / 97 passes** because the test incorrectly expected JSON coordinate strings at the direct service boundary. The service correctly returns Decimals before HTTP serialization. Only the assertion was corrected; final 102 passed. That initial log is retained as `navigation-session-backend-final.log`. Earlier baseline selection: 81 passed (`navigation-session-backend.log`).
- PostgreSQL integration using the actual FastAPI auth/order GET routes and PostgreSQL-enforced read-only connections: **8 identity checks, 28 fulfillment checks, 23 denied reads**, expired/anonymous credentials rejected, unconfirmed seller destinations withheld, public orders coordinate-free, exit 0. Evidence: `security/evidence/navigation-session-readonly.json`; log: `navigation-session-readonly.log`. Tests use a separate ephemeral signer in an in-process test app and do not sign into or alter accounts.
- Those read-only tests exercise current records, not synthetic database mutations. They cannot test creation/confirmation/status changes, revocation or renewal transactions. Existing migration-running persistence fixtures were not run because migrations are not approved. New status/consent combinations are tested through real policy logic on synthetic in-memory objects instead.
- Frontend production build: **passed**, exit 0; TypeScript/Vite, 1,947 modules, including a final rerun after the lifecycle-test adjustment (`navigation-session-build-final.log`; initial `navigation-session-build.log`). The generated application asset names match the prior UX build because this investigation changes tests/diagnostics/docs only.
- Diff/security checks: `git diff --check` passed (existing informational line-ending warnings only); targeted credential-pattern scan of the added tests/scripts/report found no matches. No real bearer tokens, connection URLs, passwords or coordinates were written to evidence. Independent read-only review found no blockers.
- No live browser GPS, Google Maps navigation, signed-in customer order action, login mutation, physical tab/timer reproduction, logout/revocation implementation or renewal-after-expiry test was claimed. Existing product uploads, buyer GPS, addresses, checkout and discovery runtime files were untouched.

## Exact files added

- `src/state/SessionLifecycle.test.tsx`
- `backend/tests/test_navigation_policy.py`
- `docs/security/inspect_navigation_session.py`
- `docs/security/verify_navigation_session_readonly.py`
- This report.
- Evidence: `docs/security/evidence/navigation-session-inventory.json`, `navigation-session-readonly.json`, `navigation-session-frontend.json`, `navigation-session-lifecycle-final.json`. Logs are ignored files in the repository root. Existing unrelated edits remain unchanged.

## Commands

From repository root:

```powershell
backend/.venv/Scripts/python.exe docs/security/inspect_navigation_session.py
backend/.venv/Scripts/python.exe docs/security/verify_navigation_session_readonly.py
npx.cmd vitest run src/state/SessionLifecycle.test.tsx src/state/AuthContext.test.tsx src/pages/OrderNavigation.test.tsx src/api/client.test.ts src/App.test.tsx src/DeliverySupport.test.tsx --pool=threads --maxWorkers=1 --reporter=default --reporter=json --outputFile=docs/security/evidence/navigation-session-frontend.json
npm.cmd run build
git diff --check
```

From `backend`:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_navigation_policy.py tests/test_auth_security.py tests/test_auth_schemas.py tests/test_delivery_location.py tests/test_order_schemas.py tests/test_api_contracts.py -q --tb=short
```

## Remaining manual browser checks

1. For navigation, use the existing PLACED order only when the buyer/seller intentionally choose to continue that order. Buyer reviews and explicitly confirms the saved delivery point before DELIVERED; seller accepts the order normally, opens its details, then clicks View delivery details. Verify Navigate to Buyer opens the intended buyer-confirmed destination. The investigation did not modify that order.
2. Verify a different seller is denied, unconfirmed orders show postal fallback, and PLACED/CANCELLED/COMPLETED/REJECTED do not expose seller fulfillment. Do not reset old orders to manufacture a test case. Use authorized synthetic beta orders if mutation testing is later approved.
3. Fresh seller login: record only the login time and `expires_in` value locally, without exporting passwords, bearer tokens or private responses. Switch away for 2–3 minutes while the total login age is below 15 minutes; return and read the dashboard/order details. Repeat after the total login age exceeds 15 minutes; current behavior requires login again. This distinguishes inactivity duration from total credential lifetime.
4. If logout happens before the issued deadline, record the first failing request's endpoint/status and whether the browser system clock changed, with secrets and personal data removed. Check the running API host/build/lifetime against the inspected source/config. Do not export a HAR containing credentials or precise delivery points. Such an early-expiry case was not reproduced here.
5. After renewal is approved and implemented, repeat with simultaneous dashboard/order requests across expiry, two tabs, cookie restrictions, refresh failure, expired/revoked sessions, logout and all three roles. Verify no refresh loop or duplicate order/upload occurs. These checks cannot pass as renewal acceptance criteria on the current architecture.

Overall: the navigation visibility investigation is complete with unmet consent/status requirements documented. The requested longer renewable session remains unimplemented; no overall resolution is claimed. Approval is required for the proposed session schema, cookie/CSRF changes and beta lifetime policy before implementation.
