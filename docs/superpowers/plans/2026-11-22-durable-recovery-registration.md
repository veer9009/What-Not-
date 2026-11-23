# Durable recovery and registration implementation plan

**Goal:** Implement the approved encrypted delivery and focused registration journeys.
**Spec:** `docs/superpowers/specs/2026-11-22-durable-recovery-registration-design.md`, approved by user with bounded SMTP, DB connection-loss tests, no buyer role changes and no encryption substitutes.
**Architecture:** Separate encrypted PostgreSQL outbox, existing SMTP/worker conventions, existing single-role SELLER/CreativeProvider services. Live recovery disabled by default.
**Execution:** Inline; no commits, worktree changes, deployments or migration execution. Preserve original untracked files.

## Tasks

- [x] Recovery delivery: write failing configuration/AEAD/job/worker tests; add AES-GCM key-ring helper, RecoveryDelivery mapping and additive 0012; atomic enqueue/cancellation in recovery service; bounded SMTP adapter; leased worker with user/recovery/job ordering, fencing, retries/cleanup and documented crash window. Verify offline DDL, synthetic PostgreSQL ORM fixtures, existing recovery/proxy/session tests. Missing dependency is a blocker, never a reason to replace encryption.
- [x] Registration: write failing journey tests; hide selector on fixed seller/buyer/services entries, preserve generic registration; allowlist services login continuation; retain existing signed-in users; reuse studio with explicit unsupported buyer enrollment. Test seller/buyer intent payloads, VFX/categories, moderation and authorization.
- [x] Verification: focused backend/frontend regressions, TypeScript/build, browser at 390/768/1440. Log exact commands/counts and failures. Exclude migration-executing runners against existing DBs.
- [x] Independent read-only security review; fix concrete findings with tests; document activation, keys, backup/rollback, service capability gaps, modified files and final status.

## Interfaces and risk focus

Issuance consumes `enqueue_recovery(session, settings, row, email, otp)` inside its existing savepoint and returns no live plaintext delivery tuple. Worker consumes encrypted rows only after a committed lease. SMTP uses an overall deadline in addition to per-socket bounds; DB loss rolls back acknowledgement and cannot retract SMTP acceptance. Holding account locks across a bounded send serializes supersession; no transaction claims a job and then waits for user locks without releasing its claim transaction first.

Tests must cover tampering/wrong keys, rollback after supersession, concurrent claims, in-flight expiry/supersession and connection loss, erased terminal payloads and no sensitive exception logs. A default-false flag plus validated key configuration controls future activation; no flag or credential is set locally. Provider registration creates only SELLER accounts and then uses the existing moderated studio; BUYER enrollment remains unsupported.

## Progress

Starting HEAD `15a8430`; only pre-existing untracked `codex-auth-review.txt` and the approved design document. Plan approved through user's instruction to proceed with the named design and safeguards. No additional design gate required.

Dependency installation succeeded through the authorized network path; real
cryptography 49.0.0 is installed. Independent review's encoded-key reuse and
orphan-child deadline defects were reproduced RED and fixed GREEN. Added leased
state/index checks and services continuation cases. Self-review reproduced and
fixed near-expiry send and expiry-cleanup batch behavior. Final backend command
passes 534 tests; browser passes 36 cases. Full command history, earlier fixture
and EBUSY failures, operational risks and files are in
`docs/security/COMBINED_IMPLEMENTATION_2026-11-23.md`.

Ruling: do not execute existing DB migration suites; offline PostgreSQL DDL and
guarded synthetic-schema ORM integration provide local evidence, not runtime
migration/rollback evidence. Ruling: preserve unsupported buyer enrollment and
single-role authorization; no new role or verification system. Ruling: accept
SMTP's unavoidable send/ack duplicate window, but bound both parent and orphan
child duration, retain stable Message-ID and never extend OTP lifetime. No
deferred code-review security finding is being treated as deployment approval.

Final frontend aggregate: 448 passed / 1 failed (unchanged LocationDiscovery
Longitude case); isolated location retry 12/12 passes without edits. Earlier
Sage mock defect was fixed and passes in the final full run. No single clean full
frontend run is claimed; intermittent aggregate stability remains a beta blocker.
TypeScript, production build, all 534 applicable backend tests and 36 browser
cases pass. Runtime migration and live SMTP checks remain separately unauthorized.
