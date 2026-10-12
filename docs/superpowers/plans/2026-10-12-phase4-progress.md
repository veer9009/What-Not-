# Phase 4 execution ledger

Plan: 2026-10-12-phase4-services.md

Ruling: execute in the user's existing checkout and leave changes uncommitted, as explicitly requested; do not create a separate checkout that hides the result.
Ruling: user approval covers the complete written in-chat design and implementation sequence; no further planning approval gate.
Pre-flight: all repositories share a Session supplied by services; all write services require an outer transaction and protect the operation with a savepoint. No repository commit. ORM return values are mapped while the session is open.
Tasks 1-5: implemented; first complete backend run 255 passed, including initial concurrency tests and migration metadata checks. Frontend 41 passed.
Review: independent read-only review identified mutated Pydantic instances, implicit transaction acceptance, and scalar ID validation. Regression tests reproduced all three; unit fixes 20 passed.
Ruling: shared buyer/seller-user locks during order creation protect active roles while allowing independent buyers to contend on product locks. Exclusive user locks remain for user/profile/address writes. Stronger concurrency test observed the original seller serialization and is being verified after this change.
Final: minor (deferred): connection/operational errors are internal exceptions until authenticated HTTP handlers can sanitize them; constraint/domain failures are translated now, and all marketplace routes remain 501.
Tasks 1-7: complete. Final backend 272 passed (43.71s, exit 0); explicit persistence/service/concurrency 134 passed (38.58s, exit 0); frontend 41 passed; tsc/build/compileall/pip check/diff check passed. Alembic round trip and both metadata comparisons passed within isolated generated databases.
Final: fixed model mutation bypasses, implicit transaction acceptance, and unvalidated scalar IDs with RED->GREEN regressions. PATCH raw-field revalidation avoids serializer warning leaks. Independent product-lock concurrency test passes with shared actor locks.
Runner diagnosis: Python returned 0 despite some PowerShell exit reports; final cmd.exe ordinary-pipe runs exited 0. PTY subset stalled in cleanup and was interrupted; its exact retained generated directory was verified, pg_ctl confirmed no server, and directory removed. Clean subset rerun passed.
Final report: backend/PHASE4_REPORT.md. No protected database accesses, model/migration changes, frontend source changes, commits, or pushes.
