# Recovery security audit and approved authentication artwork

**Goal:** Correct confirmed recovery security problems and consistently reuse identifiable approved artwork without disturbing existing uncommitted work.

**Spec:** User-supplied combined security/UI request, attachment `7085a433-8740-4937-b336-ffb6d3087866/Pasted text.txt`.

**Architecture:** Preserve server-managed single-role authentication, user-before-recovery/session locks, keyed digests and separate admin entry. Supersede older recovery credentials when a real new challenge is issued. Retain `request.client.host` behind the existing restricted Uvicorn trust boundary; prove forwarded-header handling with in-memory tests. Reuse the shared decorative panel for public registration and all recovery steps. Never regenerate artwork or introduce geographic outlines.

## Constraints

- No commits, pushes, merges, deployment, AWS/DNS or production Nginx changes.
- No production connections, real SMTP, secret output or database migrations. Integration tests may use only the existing guarded synthetic-schema fixture and ORM test DDL, never Alembic execution. Migration validation stays offline.
- Preserve all pre-existing edits and unrelated business logic. Work in the requested dirty branch without reset/stash/worktree changes.
- If reliable delivery needs an operational design decision, stop that part and safely disable live recovery pending the decision.
- If an original illustration cannot be established confidently, leave the current illustration unchanged and document the limitation.

## Tasks

- [ ] Audit security and migration/session architecture; add regression tests and fix overlapping challenges under the user lock.
- [ ] Assess durable mail against existing database/outbox/worker capabilities; implement only if safe within the existing infrastructure, otherwise fail closed and document the exact decision needed.
- [ ] Review repository proxy templates read-only; add tests proving spoofed headers cannot select rate-limit buckets and trusted proxy clients remain distinct.
- [ ] Identify original artwork from files/provenance/history; use it consistently on public login, registration and recovery while preserving seller defaults and admin behavior.
- [ ] Run focused backend/auth/migration-offline/frontend suites, TypeScript/build and actual browser checks at 390/768/1440px, including later recovery steps.
- [ ] Independently review the result; report security findings, operational blockers, every task-modified file and complete final Git status.

## Review focus

New requests must invalidate both unused OTPs and already verified reset proofs; suppressed resends must not disable a useful existing code. Locking must serialize request/verify/reset. Background mail must not silently advertise durability or leak/stale-send secrets. Proxy trust must remain at the server boundary. Artwork provenance must distinguish the user's original illustration from generated replacements. Registration must preserve field labels, role selection, notices and API payloads.
