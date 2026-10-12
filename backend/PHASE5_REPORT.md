# Phase 5 report

Checkpoint: master at b5e5cfda32136de35d9a9bf1a2040efb26ff6c0b.
This report records validation before the separately authorized release commit.
No schema, migration or frontend source change.
Protected databases whatnot_db and upsc_compass were never accessed.
See [AUTHENTICATION.md](AUTHENTICATION.md) for detailed explanations and Ravi's flow.

1. Files: created this report, AUTHENTICATION.md; core/security.py, services/auth.py,
   api/errors.py, routes/addresses.py and sellers.py, schemas/marketplace.py;
   test_auth_security.py and persistence authentication/authorization/transaction tests;
   root Phase 5 plan. Changed README, backend environment example/dependencies/
   CONTRACTS/DATABASE/SERVICES, config/main, API dependencies/contracts and auth/
   product/order/admin routes, users repository, auth schemas and API/schema/harness tests.
2. Architecture: FastAPI -> auth service -> existing services/repositories -> PostgreSQL.
   Token -> active database identity -> role/ownership -> service. One shared explicit
   request transaction commits before response; failures roll back.
3. Hashing: Argon2id via argon2-cffi RFC 9106 low-memory profile, random salt.
   Exact Unicode/whitespace passwords. No plaintext storage/logging or hash output.
   Existing bcrypt verifies and upgrades to Argon2id at successful login.
4. Registration: required name/email/phone/password; BUYER/SELLER only. Lowercase email,
   trim phone, duplicates 409, privileged fields 422. SELLER creates only User;
   complete own profile creation is separate. No public ADMIN creation.
5. Login: verify exact password/current activity. Unknown/wrong/inactive/ambiguous
   accounts share generic 401; dummy verification reduces obvious timing differences.
6. JWT: PyJWT HS256; required sub/iat/exp only, no personal data/role in issued tokens.
   Signature/algorithm/expiration/issued-at/types/positive BIGINT checked.
   Default 15 minutes, configurable 1..60; no refresh tokens.
7. Dependencies: get_access_subject, get_current_user, require_active_user,
   require_role/buyer/seller/admin; shared function-scoped TransactionSession.
8. Roles: current database role/activity authoritative; frontend/body/query/header/
   token role cannot grant privilege. Disabled/deleted users lose access.
9. Ownership: derive seller profile and address/order actor IDs from current user.
   Existing locks/savepoints/history/lifecycle checks remain. ADMIN is not an order owner.
10. Activated: auth register/login/me; seller product writes; own complete shop/profile/
    listings; own addresses/default; owned order reads/list/transitions; ADMIN moderation.
11. Remaining 501: GET products, GET products/{id}, POST orders, because geographic
    eligibility is absent. No geographic promises or discovery/checkout storage work.
12. HTTP: 401 credentials, 403 role/ownership, 404 missing, 409 conflicts, 422 input;
    sanitized 500 mapping/503 storage/config errors. Validation omits inputs/context/
    unknown property names. No SQL/secrets/traces/hashes. Login/me no-store;
    401 includes WWW-Authenticate: Bearer.
13. Environment: DATABASE_URL, WHAT_NOT_JWT_SECRET_KEY (secure random, >=32 bytes),
    WHAT_NOT_JWT_ALGORITHM=HS256, WHAT_NOT_ACCESS_TOKEN_EXPIRE_MINUTES=15,
    WHAT_NOT_ENVIRONMENT. Production requires secret; dev auth fails closed.
    Tests use isolated key/storage, example file contains placeholders only.
14. Tests: registration/hash/salts/duplicate/boundary/legacy identities; login safety;
    JWT claim/signature/time/deletion/inactivity; protected routes, role/actor spoofing;
    seller/address/buyer+seller order ownership; moderation/shop workflows; real outer
    commit rollback and sanitized errors; isolated harness lifecycle regressions.
15. Full warning-strict backend: 363 passed, 788.34s, exit 0.
    Non-persistence: 144 passed, 32.02s. Harness: 5 passed, 0.11s.
    Compilation, pip check (no broken requirements) and whitespace checks passed.
    Separate persistence/service/concurrency: 136 passed, 306.49s, exit 0.
16. Focused authentication/authorization: 113 passed, 484.90s, exit 0.
17. Alembic: isolated upgrade, metadata check, downgrade, re-upgrade, metadata check
    passed; both comparisons no new operations. Models and revision 0001 unchanged.
18. Frontend: 41 passed across six files, 363.97s, exit 0, using the installed
    VM-thread pool (node node_modules/vitest/vitest.mjs run --pool=vmThreads --maxWorkers=1).
    Earlier default/thread/reusable-worker runs timed out during worker startup.
    TypeScript and production build passed. No frontend source/dependency/config edits.
19. Fixed: password whitespace stripping; validation secret echoes; ambiguous legacy
    identity handling; explicit authentication transaction boundaries; failed initdb
    cleanup race. Independent review found no concrete auth/ownership bypass.
    Outer commit fault test targets outer commit only. Failed initdb retains files
    when child exit is unconfirmed. Generated cluster shutdown uses tested immediate
    fallback after fast-stop failure and confirms exit before deletion. Test-only
    no-sync, 20 connections, 16MB buffers and bounded longer waits preserve isolation.
20. Limits: no geography/frontend integration/payments/infrastructure/refresh/social
    login/verification/recovery; no per-token revocation or abuse/audit pipeline.
    Legacy bcrypt >72 UTF-8 bytes rejected; zero-price/client BIGINT gaps remain.
    Local process-start/shutdown failures caused intermediate validation failures;
    unconfirmed failed-cluster directories are retained safely.
21. Phase 6: geographic eligibility with truthful discovery/detail/checkout contracts
    and isolated tests, then separately planned frontend integration.

Implementation was completed in the requested checkout without commits, following
the original authorization. Release follows a separately authorized final security
and Git review. Reusable test passwords are generated at runtime; no plaintext
account credentials are embedded in the Phase 5 tests.

Final release review: exactly 33 intended Phase 5 files; reusable test passwords generated at runtime; no live credentials or generated artifacts staged. Full warning-strict pre-commit backend rerun: 363 passed, 694.08s, exit 0. Protected databases remained untouched.
