# Controlled beta authentication repair

Scope authorized by the supplied task: investigate, make minimal repository fixes,
run local tests, and provide manual configuration instructions. No deployment,
service changes, infrastructure access, production DB access, commits or pushes.

1. Trace registration, login, normalized identities, password hashing, JWTs,
   refresh cookies, logout, protected routes and roles. Separate supplied live
   evidence from locally reproducible defects.
2. Keep existing production allowlist validation and session architecture. Add
   settings tests for JSON environment/dotenv input, normalization, precedence,
   missing/empty allowlists and disabled abuse controls. No permissive fallback.
3. Add PostgreSQL HTTP regression coverage for admitted buyer/seller registration,
   login, duplicate/wrong credentials, removal from admission, role boundaries,
   expiry, refresh rotation and logout. Use generated test data only.
4. Reproduce the frontend's loss of the beta denial reason with failing tests.
   Map only the known denial to a safe, actionable message; preserve generic
   handling of other server errors and the existing UI.
5. Document placeholder JSON configuration, settings source precedence, process
   lifetime, bootstrap restrictions, and coordinated frontend/backend/schema
   release requirements. Do not run any operational changes.
6. Run backend/frontend suites, TypeScript and production build; report exact
   outcomes and any blocked environment-dependent tests. Review the final diff.

Approach: fix the observed message defect and configuration guidance, retaining
the already implemented refresh/logout endpoints. Adding a second refresh system
or disabling admission would conflict with the requested architecture/security.
