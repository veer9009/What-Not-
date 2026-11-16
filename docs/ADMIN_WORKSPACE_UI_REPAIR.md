# Admin workspace UI repair

16 November 2026. Scope: `/admin/creative` and `/admin/operations`, plus confirmed pagination styling defects on product moderation and Notifications.

## Root cause

The global stylesheet resets control fonts but intentionally does not turn every HTML input, textarea or button into a styled marketplace control. Most form styling belongs to `.product-form` and specialized components. These two admin pages rendered plain controls directly under `DashboardShell`, outside those selectors; most action buttons also lacked `.btn` classes. Accounts and orders were unstructured adjacent articles, and `.form-actions` alone supplied neither button styling nor safe long-label wrapping. The shell's clipped main content could conceal overflow rather than make controls fit.

Product moderation already has styled approve/reject actions and a dedicated rejection form. Its two pagination buttons still omitted `.btn`, as did the shared Notifications pagination. Those four buttons received only the established button classes. Property moderation and address forms already have their own styled wrappers; they were not redesigned.

## Changes

- Added a scoped `AdminWorkspace` wrapper and stylesheet using the existing cream, neutral, terracotta, typography, surface, border and focus tokens. Other workspaces keep their existing layouts.
- Styled the investigation/rejection reason fields with associated help, multiline input, existing 1,000-character limit and disabled state during actions/confirmation.
- Service moderation uses responsive cards, status/category badges, pricing/provider/location details, portfolio links, explicit actions and consistent pagination/refresh. Empty, loading, error/retry and success states are present.
- Operations uses responsive account and order cards. Roles, active/suspended status, contact details and phone/email verification status are separate readable fields. Administrator account mutations remain unavailable.
- Email Processing is a compact operational-status card using only the returned provider status, outbox counts and oldest-pending value. It does not start workers or configure email delivery.
- Added inline, nonmodal destructive-action confirmation for suspension, service rejection/takedown, product takedown and order resolutions. Cancel receives focus, cancel restores the trigger, and mutation controls/reason fields lock while reviewing. Cancellation sends no request. Account reactivation and verification retain their immediate, reason-gated flow.
- Long names, emails, audit text and action labels wrap inside their cards. Mobile actions stack; desktop cards share rows where space permits.

## Functionality preserved

The interface still uses the real existing API client and endpoints. No mock interfaces were added to application code. Approval still submits the reviewed `expected_updated_at`; rejection/takedown still submits the reason. Account action payloads still contain only the supported action fields and trimmed investigation reason. Order resolution enums, status-dependent actions, private-delivery investigation, audit display, 50-record pagination and refresh remain connected to the same APIs.

No backend files or behavior changed in this task. Existing backend authorization, audit records and reason validation were preserved. Frontend route tests verify buyer/seller accounts cannot load either admin workspace or request protected data. No backend test rerun or database migration was needed for this presentation change.

No `.env` edits, deployments, commits, pushes, database operations, or account/service creation were performed. Existing uncommitted location and product-image work was preserved.

## Verification

- Regression tests before implementation: **2 passed, 7 failed**. Failures reproduced missing empty states, default controls, unstructured account information and absent confirmations. Evidence: [red report](security/evidence/admin-ui-red.json).
- First focused run after repair: **11 passed, 0 failed**, including original API contract tests. Evidence: [focused report](security/evidence/admin-ui-focused.json).
- Expanded admin tests: **17 passed, 0 failed** in the first full-suite attempt, including four buyer/seller route restrictions, preserved approval version, account reason/confirmation, audit/private-delivery investigation and pagination.
- Offline rendered screenshot fixtures: **4 passed, 0 failed**. These export actual React component output using test-only HTTP doubles; no records are persisted.
- Chrome geometry: **20 passed, 0 failed** across four scenarios at 1440, 1024, 768, 390 and 320 pixels. Checked document/control/card containment, button classes and touch height, styled form controls, labels, responsive columns and compact Email Processing. Screenshots were visually inspected. Evidence: [layout measurements](security/evidence/admin-layout.json).
- Final `npm.cmd run build`: **passed, exit 0**; TypeScript and Vite, **1,946 modules transformed**. Production JavaScript contained **0 screenshot-fixture string matches**.
- `git diff --check`: passed. Limited credential-pattern scan of changed admin implementation: **0 matches**.
- Independent read-only code review: **no blockers found**; endpoints, payloads, version checks, investigation requirements and confirmation accessibility preserved.

The initial full frontend attempt encountered a five-second timeout in the existing product-creation test and was stopped. No complete aggregate is claimed for that interrupted attempt. The full retry used a command-only 20-second test limit with the same assertions and unchanged project configuration; the product-creation test passed in that retry.

The completed full retry reported **340 passed, 1 failed test, and 1 collection error**, with **38 passed and 2 failed test files**. `BetaResume.test.tsx` could not find the product Approve button within its asynchronous wait while the queue was still loading. `DeliverySupport.test.tsx` failed collection because Windows returned `EBUSY` opening `aria-query/.../graphicsSymbolRole.js`; its 27 tests were not executed in that run. The full run is **not** claimed clean. Evidence: [full frontend JSON report](security/evidence/admin-ui-frontend.json).

The final single-worker recheck passed **46 tests, 0 failed**, across all four files: DeliverySupport 27, BetaResume 2, AdminWorkspace 11, and AdminOperations 6. Exit 0. Both full-run problem files and all admin regressions passed without further source changes. Evidence: [final isolated recheck](security/evidence/admin-ui-final-recheck.json). Overlapping reruns are not additive totals; full-suite timing/file-lock instability remains a verification limitation.

Commands, from the project root:

```powershell
npx.cmd vitest run src/pages/AdminWorkspace.test.tsx src/pages/AdminOperations.test.tsx --pool=threads --maxWorkers=1 --reporter=default --reporter=json --outputFile=docs/security/evidence/admin-ui-focused.json
npx.cmd vitest run scripts/admin-layout.test.tsx --pool=threads --maxWorkers=1
node scripts/verify_admin_layout.mjs
npx.cmd vitest run --pool=threads --maxWorkers=2 --testTimeout=20000 --reporter=default --reporter=json --outputFile=docs/security/evidence/admin-ui-frontend.json
npx.cmd vitest run src/DeliverySupport.test.tsx src/BetaResume.test.tsx src/pages/AdminWorkspace.test.tsx src/pages/AdminOperations.test.tsx --pool=threads --maxWorkers=1 --testTimeout=20000 --reporter=default --reporter=json --outputFile=docs/security/evidence/admin-ui-final-recheck.json
npm.cmd run build
git diff --check
```

## Screenshots

All images are labeled **offline UI test fixtures**. They show the real components/styles with synthetic data from test doubles; they are not screenshots of live accounts or services.

| Scenario | Desktop | Mobile |
| --- | --- | --- |
| Populated service moderation | [1440px](security/evidence/admin-creative-populated-1440.png) | [390px](security/evidence/admin-creative-populated-390.png) |
| Empty service moderation | [1440px](security/evidence/admin-creative-empty-1440.png) | [390px](security/evidence/admin-creative-empty-390.png) |
| Populated operations | [1440px](security/evidence/admin-operations-populated-1440.png) | [390px](security/evidence/admin-operations-populated-390.png) |
| Empty operations | [1440px](security/evidence/admin-operations-empty-1440.png) | [390px](security/evidence/admin-operations-empty-390.png) |

## Exact files changed in this task

- `src/pages/AdminOperations.tsx`
- `src/pages/AdminOperations.test.tsx`
- `src/pages/AdminWorkspace.test.tsx` (new)
- `src/components/AdminWorkspace.tsx` (new)
- `src/styles/admin-workspace.css` (new)
- `src/pages/AdminDashboard.tsx` (two pagination button classes only)
- `src/pages/NotificationsPage.tsx` (two pagination button classes only)
- `scripts/admin-layout.test.tsx` (new, offline fixture export)
- `scripts/verify_admin_layout.mjs` (new, offline Chrome checks)
- `docs/ADMIN_WORKSPACE_UI_REPAIR.md` (this report)

Generated evidence files, all under `docs/security/evidence/`: `admin-ui-red.json`, `admin-ui-focused.json`, `admin-ui-frontend.json`, `admin-ui-final-recheck.json`, `admin-layout.json`; `admin-creative-populated.html`, `admin-creative-empty.html`, `admin-operations-populated.html`, `admin-operations-empty.html`; and the eight PNG files linked above. Existing unrelated changes remain in the workspace.

## Manual verification and limits

Automated interactions use mocked HTTP. Chrome checks use offline React markup with network blocked. No real administrative action was performed against live records. A live session with authorized real data still needs a short browser check:

1. Open both pages as an administrator at desktop and mobile widths. Confirm labels, reason-field focus, wrapped actions, contact/verification fields and empty/loading/error states.
2. With an appropriate test account/listing authorized for action, check that blank reasons block writes, canceling confirmation performs no action, and confirming sends the intended action and records the normal backend audit trail. Do not alter real accounts merely to populate the UI.
3. Review an existing pending service, verify version-protected approval, and exercise rejection/takedown only when operationally authorized.
4. Check filters, previous/more controls and refresh. Review an existing audit entry and verify private delivery details still require a reason.
5. Verify a buyer/seller cannot access either admin URL. Check product moderation and Notifications pagination styling.
