# Phase 6 frontend integration plan

Goal: Connect existing What Not? React workflows to Phase 5 authenticated APIs without changing storage, authorization, or business rules.

User specification: Phase 6 request supplied on 2026-10-14. Direct implementation after inspection is authorized. All work stays uncommitted in the existing checkout.

Architecture: Typed centralized HTTP client; memory-only Bearer credential; AuthProvider obtains identity from auth/me and handles expiry/401/logout; protected role routes; pages reload backend truth after successful mutations. Mock discovery/cart are explicitly labelled sample data and never enter real order APIs. Checkout is disabled. Existing layout receives reusable accessible Warm Orange tokens.

Constraints: No migrations, protected databases, actor IDs in writes, refresh tokens, geographic calculations, checkout, payments, infrastructure, commits or pushes. APIs continue to enforce security. Preserve BIGINT precision using decimal string identifiers. Existing CORS already restricts development origins.

Review focus: late responses after logout/account change; unsafe BIGINT rounding; failed auth/me after login; historical address conflicts; successful writes followed by failed refresh.

- [x] API contracts/client: test authorization headers, exact BIGINT parsing, safe JSON/errors, 401/403/404/409/422/network failures; implement resource modules and configurable URL.
- [x] Authentication/routes: test login/register/restoration/logout/expiry and role guards; implement memory session, login/register screens, protected routes and logout clearing mounted resources/demo state.
- [x] Seller/admin: test complete profile setup/update, listing/create/edit/activation/resubmit and moderation/reasons/error refresh; replace mock seller/admin pages.
- [x] Addresses/orders: test own list/create/update/default, conflict/ownership failures, order detail/actions and transition rejection; add secure resource pages.
- [x] Demo/theme: label sample discovery consistently, disable checkout, apply orange tokens and responsive form/error styles; update UI tests for new authenticated behavior.
- [x] Verify/document: complete frontend tests/TypeScript/build; full isolated PostgreSQL backend regression including authentication/persistence/concurrency and Alembic cycle; compilation/dependencies/whitespace/security review; document integration and detailed Phase 6 report.

Verification: installed Vitest VM threads with one worker; backend .venv Python warning-strict pytest with PostgreSQL 17 binaries and existing isolated-cluster fixture only. Alembic validation runs through test_foundation, never configured development databases.


Execution record: implemented in the explicitly requested master checkout, with
no commits/pushes and no worktree/schema/auth architecture changes. HTTP client tests failed
before the module existed, then 16 passed. Auth/resource/product-patch regressions
were observed failing before their fixes. Final frontend suite: 91 passed. Backend:
363 full and 189 focused passed; Alembic comparisons, compilation and pip check
passed. Browser smoke uses only fixture-owned temporary PostgreSQL.

Rulings: memory-only credential means intentional login after full reload; logout
returns to public role sign-in; edit lookup uses first-100 owned products because
public detail remains 501; no-op product saves skip moderation; unchanged product
and address fields are omitted to preserve concurrent stock/history. A static
TypeScript API-inspection probe was unavailable; installed tsc -b provides the
required compiler validation. The first Vite build exited abnormally after writing
its outputs; subsequent current builds exited 0. Windows stdin Unicode corruption
was caught in screenshots and corrected with explicit Unicode codepoints.
