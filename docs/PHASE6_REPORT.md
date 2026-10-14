# Phase 6 report - real frontend/backend integration

Date: 2026-10-14 (project owner's Asia/Calcutta date).
Historical implementation report before checkpoint approval. See the
[approved checkpoint report](PHASE6_CHECKPOINT.md) for final verification.
Baseline: master, afe596cc7b732887eb328e488f2308b641f55df0.
All Phase 6 changes remain uncommitted and unstaged. No push or Phase 7 work.

The subsequent [Phase 6 scope correction](PHASE6_SCOPE_CORRECTION.md) updates the
business presentation to Homemade, Real Estate and Creative Services. That report
records the current UI boundaries and verification counts; the integration work
described here is preserved. The Phase 7 recommendation below is historical and
does not authorize or begin geography work or establish the verticals' data models.

## 1. Files created or changed

Created:

- `.env.example` (public API configuration only).
- `src/api/client.ts`, `client.test.ts`, `types.ts`, `auth.ts`, `products.ts`,
  `sellers.ts`, `admin.ts`, `addresses.ts`, `orders.ts`.
- `src/state/AuthContext.tsx`, `AuthContext.test.tsx`, `useResource.ts`,
  `useResource.test.tsx`, `useMounted.ts`.
- `src/components/ApiStates.tsx`.
- `src/pages/AddressPage.tsx`, `OrderPages.tsx`.
- `scripts/phase6_smoke.py`, `scripts/phase6_browser.mjs` (optional isolated live check).
- `docs/FRONTEND_INTEGRATION.md`, this report,
  `docs/superpowers/plans/2026-10-14-phase6-integration.md`.
- 21 intentional validation PNGs under `docs/phase6/screenshots/` (seven screens,
  desktop/tablet/mobile). No credential traces, videos or database artifacts.

Changed:

- `.gitignore`, `README.md`, `src/App.tsx`, `src/main.tsx`.
- `src/components/Shared.tsx`.
- `src/pages/LoginPages.tsx`, `SellerPages.tsx`, `AdminDashboard.tsx`,
  `BuyerPages.tsx`, `LandingPage.tsx`.
- `src/styles/index.css`, `src/App.test.tsx`, `src/Marketplace.test.tsx`.

No backend implementation, models, migration, dependencies, lockfile or Vite
configuration change. Legacy mock data/reducer tests remain for isolated sample UI.

## 2. Integration architecture

React -> resource-specific API functions -> centralized HTTP client -> FastAPI ->
current active database identity and authorization -> existing service -> repository
-> SQLAlchemy -> PostgreSQL. The existing Phase 4/5 rules and transactions remain
unchanged. The frontend never determines the authenticated actor for backend writes.

## 3. API client design

One fetch implementation in `src/api/client.ts`. It handles configurable URL, JSON,
Bearer headers, no-store/omitted cookies, safe parsing, empty responses, network and
HTTP errors, sanitized field feedback, protected 401 invalidation and old-session
response rejection. Resource modules supply explicit request payloads. BIGINT JSON
literals are preserved before parsing can round them; identifiers become exact
decimal strings. Identifier paths reject invalid/out-of-range values. Real decimal
prices/totals remain strings, without frontend financial arithmetic.

## 4. Environment configuration

Public `VITE_API_BASE_URL` includes `/api/v1`; the centralized development fallback
is `http://127.0.0.1:8000/api/v1`. `.env.example` has no private credentials. Local
frontend environment files are ignored. Backend secrets remain backend settings;
the integration guide explains Vite's public bundling and production HTTPS origins.

## 5. Authentication state

A lightweight AuthProvider holds user/loading/error state and login/logout actions.
Role comes from `/auth/me`, not the selected login link. An existing in-memory
credential is revalidated during provider restoration. Identity/role changes remount
resource/sample state; old operations have lifecycle tickets. No new state framework.

## 6. Token handling

Bearer token in JavaScript memory only. No localStorage/sessionStorage/cookie/URL/UI
storage. Full reload/new tab requires login again. Expiry clears state automatically;
protected 401 also clears it. This avoids persistent token storage but active-page
XSS can still steal a token. No cookie-auth redesign, refresh infrastructure or
server-side revocation is invented. Backend validity/role checks remain authoritative.

## 7. Registration

Real POST auth/register with required name/email/phone/password and BUYER/SELLER.
ADMIN is absent from public registration. Duplicate email/phone has clear feedback;
422 displays sanitized field hints. Password clears after each attempt and is never
logged/persisted. Successful SELLER signup explicitly instructs subsequent shop setup.

## 8. Login

Real POST auth/login -> memory token -> GET auth/me -> actual role's workspace.
Generic invalid/inactive-account failures match Phase 5. Network/configuration errors
remain safe. Failed identity loading cannot leave a partial authenticated session.
Old restoration and provider-unmount races are covered by regression tests.

## 9. Logout

Clears token, expiry and identity; remounts away cached page/sample data and basket.
Returns to a public sign-in page. In-flight operations cannot restore old credentials.
No backend logout/revocation endpoint was added.

## 10. Role routing

Public landing/login/registration; protected BUYER discovery samples/profile/
addresses/orders; SELLER profile/products/addresses/orders; ADMIN moderation/addresses.
A missing session redirects to login, loading has explicit feedback, and wrong roles
receive a usable permission page. Backend authorization is still the security boundary.

## 11. Seller profile

GET sellers/me decides whether a real profile exists. A 404 produces complete-profile
setup, not a fabricated shop. POST/PATCH supplies only shop details and coordinates;
owner/verification fields cannot be set. Stored coordinates do not enable geography.
Profile success feedback survives the subsequent backend refresh.

## 12. Seller products

Own listing, create, edit, activation and explicit resubmission use secure routes.
Statuses/rejection reasons come from the backend. No mock shop selector, fake seller
ID, fake earnings, local approval or unsupported delete/upload action remains.
PATCH sends changed fields only; image null explicitly clears it; no-op saves skip
PATCH. Approved edits therefore return to PENDING only after an actual edit. Rejected
edits keep their reason until resubmission. Activation never grants approval.

## 13. Admin moderation

Real authenticated pending queue, approval and rejection. Reason required; no fake
admin ID. Actions reload backend truth. Error handling covers 401/403/404/409/422,
network/service failure. Fake metrics and financial/commission controls were removed.
Approval never claims products are geographically discoverable.

## 14. Addresses

Own list/create/partial update/default switch. No user actor fields. Unchanged fields
are omitted, allowing a label edit without resending historical delivery fields.
Backend ownership/history conflicts are displayed and replacement guidance is shown.
No delete or history bypass. Address form stays available after rejected edits.

## 15. Orders

BUYER/SELLER owned history/details and existing status operations. UX suggestions
match the backend transition map; the service checks every action. Terminal actions
are hidden. Backend totals/item snapshots are displayed exactly. Route identity keys
and loader lifecycle checks prevent an old transition refresh overwriting a different
order page. Live smoke validates empty history; nonempty/actions are covered by
HTTP UI tests and the real PostgreSQL backend regression suite.

## 16. Buyer features intentionally deferred

Discovery/detail, sample location/distances/ratings/verification and basket remain
isolated mock views with a visible development notice. Seller/admin backend records
never populate that sample catalogue. No real GET products/detail request is sent.
Location selection is disabled and labelled as unavailable.

## 17. Checkout limitations

Checkout and Buy Now are disabled. No POST orders, production orders, payments or
eligibility shortcuts. The local basket and illustrative delivery estimate are
explicit samples. Real order placement stays 501 until geographic eligibility exists.

## 18. Warm Orange theme

Reusable primary/hover/soft/background/surface/text/muted/border/success/warning/error
tokens. Existing layout retained. Buttons, active navigation/radius controls, login,
notices and surfaces use the new palette; semantic badges retain distinct colors.
Screenshot review corrected sidebar/login copy contrast and seller edit-link sizing.
Mobile workspace help sits below the page so it cannot obscure form/listing actions.
Primary button contrast >=4.5 verified in browser; desktop/tablet/mobile layout checks
passed with no horizontal document overflow. Mobile navigation can scroll locally.

## 19. Asynchronous states

Explicit loading, empty, permission/missing record, conflict, field-validation,
network/server feedback and retry states. Busy buttons prevent duplicate submissions.
Accepted writes followed by failed refresh are reported as saved with refresh needed.
Unmounted/changed loaders reject late callbacks; cancelled forms cannot force late
navigation. Field names stay accessible when inline validation hints appear.

## 20. Security review

No plaintext password/JWT logging or persistence; no signing/database secrets added
to browser code. No JWTs in URLs/UI. No actor-ID write shortcuts or public ADMIN role.
React escapes backend text; raw errors/inputs/SQL/traces are not shown. Old-session
responses are rejected. Independent review identified/fixed auth restoration/unmount,
stale loader/order and product stock overwrite issues. Browser diagnostics are captured
and discarded on failure to avoid secret artifacts. Temporary smoke ADMIN creation is
through the existing trusted internal service in a fixture-owned database only.

## 21. CORS

Existing backend development origins/method/header restrictions suffice; no backend
CORS change. Documentation specifies exact production HTTPS origins and explicit
WHAT_NOT_CORS_ORIGINS JSON configuration. No wildcard/credentialed CORS introduced.

## 22. Frontend tests

91 passed across 9 files (final full run, exit 0). Baseline 41: the 16 obsolete mock
login/seller/admin/purchase UI tests were replaced by 43 authenticated/integration UI
tests; 16 API client, 5 auth lifecycle and 2 resource lifecycle tests were added. The
25 existing mock utility/reducer tests remain. Tests cover auth success/failure/roles/
restoration/logout/expiry, exact IDs/headers/HTTP errors, seller profile/product edits/
activation/review/resubmit, admin reasons/permissions/refresh failure, addresses/
history/ownership errors, order progression/cancellation/rejections, and deferred
checkout/discovery. New race/patch regressions were observed failing before fixes.

## 23. Backend regression

Full warning-strict suite: 363 passed in 31.02s, exit 0. Count unchanged from Phase 5.
Separate focused auth/security/schema/authentication/authorization/transactions,
marketplace/order services, concurrency and foundation: 189 passed in 72.04s, exit 0.
No backend tests weakened or backend implementation modified. Protected whatnot_db
and upsc_compass were never accessed. Existing fixture creates/verifies/stops its own
fresh PostgreSQL cluster; no application/protected database fallback was used.

## 24. Alembic validation

Existing isolated test performs upgrade -> metadata check -> downgrade -> re-upgrade
-> metadata check. Both comparisons reported no new upgrade operations. Included in
both full/focused regression. Browser smoke applies existing revision 0001 only to
its generated UUID test database. No application migration or schema change.

## 25. TypeScript/build/browser result

Installed TypeScript `tsc -b` passed. Current Vite production build passed with exit
0. Python compileall and pip check passed ('No broken requirements found'). Live
browser smoke passed against a fresh temporary PostgreSQL/FastAPI backend: real
seller/buyer registration/login, profile, product submission, admin approval,
activation, addresses/default and empty order history. Seven screens at 1280x900,
768x1024 and 390x844 produced 21 reviewed validation screenshots. No browser runtime
errors, no horizontal document overflow; primary contrast >=4.5. No discovery GET or
order placement POST. Browser tooling was already installed; no dependency added.

## 26. Issues discovered and fixed

- Session restoration clearing a newer login: operation tickets.
- Pending login after provider unmount: cleanup invalidates ticket.
- Old loader callback/order transition replacing another route's data: mounted/loader
  checks and order route keys.
- Product metadata PATCH overwriting concurrent stock: changed-field omission/no-op.
- Lost profile creation notice during refresh: parent-held feedback.
- Logout redirect contention: consistent public role sign-in destination.
- Inline hints changing accessible label names: stable explicit input names.
- Login discarded 422 field hints: sanitized field state now displayed.
- Windows pipe encoding replacing new currency/punctuation: explicit Unicode values;
  screenshot review caught it and final browser validation regenerated screenshots.
- A smoke fixture used a reserved email domain: switched to example.com test identities.
- Initial Vite invocation exited abnormally after emitting output: repeated current
  builds exited 0; no failed build is counted as validation success.

## 27. Known limitations

Memory sessions intentionally require login after reload. No refresh/revocation,
verification/recovery/social login. Product/moderation/order lists retain 100-record
backend limit and seller edit lookup shares that limit. No geographic calculations,
checkout, payments/refunds, uploads/deletion, user profile editing or fabricated
administrative metrics. Browser smoke blocks external fonts/images and uses temporary
non-secret test data; application development database setup remains an owner task.
No infrastructure technologies or deployment were added.

## 28. Recommended Phase 7

Design server geographic eligibility with explicit buyer location, distance rules and
secure discovery/detail contracts. Revisit address selection and eligibility before
activating order placement, preserving server-calculated prices, stock reservation,
ownership and transaction safety. Add isolated geography/checkout tests and useful
pagination/owned product detail. Keep payments and deployment separately scoped.
Phase 7 has not started.
