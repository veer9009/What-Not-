# Durable recovery: operator review and later activation

This is a procedure for a later separately authorized staging exercise, not
authorization to run these operations now. Local implementation does not enable
recovery. No real mail, credentials or migration execution is part of this task.

## Architecture and bounded concurrency

Revision 0012 adds `recovery_deliveries`; it does not rewrite users, sessions,
transactions or existing notification outbox data. Each job references one
digest-only recovery challenge. AES-256-GCM encrypts recipient and OTP; a fresh
96-bit nonce is stored with the ciphertext/tag. Associated data binds protocol
version, challenge, account and UTC expiration. Keys are selected by version.
No ordinary JSON, notification, audit or log field contains a plaintext OTP.

Issuance, retirement of older OTP/reset proofs, cancellation/erasure of older
jobs and new encrypted enqueue use the same user-locked transaction/savepoint.
Failures roll back all of them. Cooldown, quota and ineligible requests do not
enqueue deliverable mail. The generic response and CSRF protections remain.

Worker claims use FOR UPDATE SKIP LOCKED; the lease transaction commits before
I/O. A new send transaction locks user, recovery and job, rechecks ownership,
lease token, eligibility, password binding, OTP attempts, verification/used state
and expiry, then holds the locks through send and acknowledgement. Issuance and
verification wait behind an active send. Other workers skip its locked job.
At least the entire SMTP deadline plus two seconds must remain on the lease and
OTP lifetime before sending starts. A near-expiry OTP is cancelled, never renewed.

The existing worker settings bound batch size, leases, attempts and exponential
backoff. Expired crash leases can be reclaimed with a new token. Stale claim
tokens cannot send or acknowledge. Expired payloads are erased even when their
retry time is in the future. SENT, CANCELLED and FAILED rows retain identifiers
and safe state only; their ciphertext/key identifier and lease fields are erased.

SMTP uses the existing adapter in a private subprocess. Socket timeouts are
bounded by `WHAT_NOT_SMTP_TIMEOUT_SECONDS` and the recovery deadline. The parent
enforces `WHAT_NOT_RECOVERY_SMTP_DEADLINE_SECONDS` (default 10, maximum 20).
The child also arms an independent watchdog using the parent's absolute
monotonic deadline before stdin parsing or network work; it checks again before
send. Killing the worker does not remove that deadline. Credentials/message
travel in an anonymous stdin pipe, never command-line arguments or files.
Only the non-sensitive monotonic deadline is an argument. Child output is
discarded. Timeout/adapter exceptions become fixed safe error categories.

### Database connection and lock behavior

One worker uses one checked-out DB connection during the send transaction;
claim and send transactions are sequential. Batches are bounded. Worker
concurrency must be budgeted separately from web concurrency; every worker
process has its own engine/pool. No session advisory locks can leak into pools.

Holding account locks across I/O is deliberate. Configure/verify worker pool
capacity and DB `lock_timeout`, `statement_timeout` and
`idle_in_transaction_session_timeout` before activation. The idle transaction
allowance must exceed the total child deadline plus startup/ack margin; lock
waits must be bounded. A web request may fail/retry when its lock wait expires;
it must never bypass account locks or weaken quota enforcement. Test this with
the actual staging pool, proxy/request timeouts and worker supervision. Do not
copy local test-fixture timeouts blindly into production.

Connection loss releases PostgreSQL locks and rolls back acknowledgement. If
SMTP accepted first, the persisted job remains leased and may later retry.
Reserving an SMTP budget before lease expiry and the orphan-child watchdog limit
overlap; they cannot retract an email accepted by a remote server. DNS/socket
faults, CPU suspension and real deployment timing still require staging tests.

### SMTP duplicate window

Delivery is **not exactly once**. SMTP acceptance followed by process/DB failure
can yield the same message twice after lease expiry. Message-ID is stable per
challenge; SMTP is not required to deduplicate it. Retries never issue a new OTP
or extend its expiry. A superseded, verified, exhausted, password-invalidated or
expired code remains unusable even if its email arrives late. Stop workers before
emergency key cancellation and quiesce active sends before bulk maintenance.

## Key provisioning and rotation (not performed)

- Provision independent random HMAC and AES keys through the approved secret
  manager. AES keys are exactly 32 random bytes, base64 encoded. Do not copy JWT
  or HMAC values into the AES ring; validation rejects identical raw or encoded
  secrets and duplicate AES versions. Generation quality remains operator work.
- `WHAT_NOT_RECOVERY_ENCRYPTION_KEYS` is a JSON mapping of version identifiers to
  base64 secrets; `WHAT_NOT_RECOVERY_ACTIVE_KEY` names the encryption version.
  Do not paste actual values into docs, shell history, logs or committed env files.
- For rotation, distribute a ring containing old and new keys to all API/worker
  instances first, then switch the active version for new jobs. Retain the old
  decryption key until old work expires/drains and payload erasure is verified.
  Missing/unknown keys cause safe terminal failure and erasure, not fallback.
- Emergency retirement requires stopping sends, cancelling/erasing pending
  payloads and requiring new recovery requests. Define access control, key
  recovery, revocation and alerting in the operational runbook.
- Database backups may retain encrypted payloads and require their own retention
  and key-destruction policy. Worker downtime delays expiry cleanup. No retention
  job or production data deletion is authorized by this implementation.

## Backup, migration and rollback (not performed)

Confirm intended DB identity, schema/search_path, ownership and current revision
0011. Take an encrypted consistent backup, record verification/checksums and
rehearse restore into a newly created isolated database before requesting approval
to apply 0012. The build's health/bootstrap schema expectation is now 0012; an
unmigrated deployment will fail readiness. This prevents treating an unreviewed
schema as ready. No startup migration runs automatically.

The old application at commit 0a85de5 expects schema 0010; this build expects
0012. Readiness requires an exact revision match, so a simple code rollback while
retaining schema 0012 may fail readiness. Retain additive tables only with a
rollback build tested against that schema, including readiness and authentication.
Before rollback, verify the actual revision, preserve matching backend/frontend
artifacts and configuration, and quiesce application writes and workers. Require
an encrypted consistent backup and a restore rehearsal in an isolated database.
If returning to schema 0010, separately review and rehearse each downgrade or
restore a verified schema-0010 backup with its matching application. Do not blindly
downgrade a populated database.
Downgrade 0012 obtains an exclusive lock and refuses any retained delivery
history, including terminal rows. Do not delete history to force downgrade.
0011's own guarded downgrade remains. Stop recovery writes/workers before any
approved downgrade; separately decide backup restoration, lost writes and session
invalidation. Existing database upgrade/rollback execution remains untested here;
DDL/revision verification is offline and behavior uses ORM test DDL only.

## Activation checklist for a later authorized staging test

1. Obtain review approval for the code, test evidence, migration and runbook.
2. Separately authorize and rehearse backup/restore and apply 0012 to staging.
3. Provision independent keys and TLS SMTP sender/authentication through the
   secret manager. Verify TLS, provider timeout behavior, sender policy and
   controlled test recipients. No credential provisioning was done locally.
4. Arrange supervised repeated execution of the bounded command
   `python -m app.workers process-recovery-email`; size pools, define restart
   behavior and alert on failed/stuck/expired work using safe state/metrics only.
5. Only then opt in with `WHAT_NOT_RECOVERY_DELIVERY_ENABLED=true` on the staging
   API and workers. It defaults false. SMTP configuration alone does not enable
   recovery. Missing dependency, key or provider prerequisites fail closed.
6. With explicit permission, send staging messages and exercise successful reset,
   all-session revocation, resend, expiry, failure/retry, killed worker/orphan
   child, DB disconnect and concurrency under actual deployment limits.
7. Keep beta activation blocked until these deployment-specific checks and the
   independent review are accepted. Local synthetic tests are not production
   readiness evidence.

## Creative Services scope

The single-role account system remains BUYER/SELLER/ADMIN. Service registration
creates a SELLER identity through the existing endpoint, then sign-in opens the
existing creative studio. Provider profile saving creates/reuses the unique
CreativeProvider row. Categories remain Video Editing, Travel Video Editing,
Influencer Reel Editing and VFX; other professional categories require a separate
schema/product change. Portfolio links, pricing and remote/local service area
remain in the studio. Listing creation/edits require admin moderation before
public availability or restricted enquiry/quote participation.

There is no separate provider-verification status, availability calendar,
dedicated experience field, or multi-role enrollment. The profile bio can describe
experience; it is not verification. Existing BUYER accounts are never changed or
duplicated by this flow and see a clear unsupported-enrollment message. Existing
SELLER accounts open their current studio. Existing ADMIN entry stays separate.
Payments and escrow remain unavailable for Creative Services.
