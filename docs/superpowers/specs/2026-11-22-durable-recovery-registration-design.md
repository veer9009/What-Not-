# Durable recovery, seller registration and Creative Services design

Status: approved by the user for local implementation, with bounded SMTP,
connection-loss tests, unchanged BUYER roles, and no encryption substitutes.
Checkpoint inspected: `15a8430`, branch `ui/sage-premium-redesign`.
Spec: user attachment `ef40e254-c9c4-4fb8-ab5b-b866be7728bf/Pasted text.txt`.

## Intent and boundaries

Deliver recovery messages durably without storing plaintext OTPs, make seller
registration unambiguous, and expose the existing professional-services journey.
Preserve marketplace transactions, roles, approval boundaries, sessions, original
artwork, Sage styling and City/Town/Village. No maps or replacement images.
Do not commit, push, merge, deploy, change infrastructure, configure credentials,
send real mail, migrate existing databases, or alter real accounts. Leave the
pre-existing untracked `codex-auth-review.txt` untouched.

## Inspection and root causes

1. `auth_recovery.py` correctly implements challenge supersession, quotas,
   password binding and session revocation, but passes plaintext delivery data to
   a post-commit in-process task. This cannot survive process termination. Its
   live 503 gate is intentional and must remain effective by default.
2. `EmailOutbox.payload` is ordinary JSON containing notification title/body.
   Its worker already has transactional claims, expiring leases, bounded retries,
   exponential backoff and session advisory send guards. Putting OTP mail in that
   payload would violate the storage requirement.
3. `RegisterPage` initializes SELLER from `?role=seller`, but always renders the
   generic title and Buyer/Seller selector. Thus the entry-point intent is not
   reflected in the actual registration presentation.
4. The database user constraint, registration schema, authorization dependencies
   and frontend identity checks implement exactly one BUYER/SELLER/ADMIN role.
   There is no membership table or buyer-to-provider enrollment workflow. Do not
   overwrite a buyer role or silently create a second account.
5. Creative Services already uses SELLER accounts and a unique CreativeProvider
   per user. The existing studio has profile/bio, portfolio links, listing
   categories (including VFX), pricing, remote/local service area, enquiries,
   quotations, delivery/completion and reviews. Listings require administrator
   moderation and return to PENDING after edits. A profile itself has no separate
   provider-verification status. Dedicated experience, availability calendar,
   multi-role enrollment, and provider-specific verification are absent.
6. The clear public Offer Your Services entry point and direct provider journey
   are missing. No new studio or authentication system is needed.

## Approaches

The recommended approach is a small recovery-specific encrypted PostgreSQL
outbox, using the existing SQLAlchemy/worker lifecycle and SMTP adapter. This
keeps OTP payloads isolated from ordinary notification APIs and JSON fields.
Extending the generic outbox would require making all existing consumers aware
of a new sensitive payload type. An external queue adds deployment infrastructure
without solving encryption, transactional enqueue or SMTP acknowledgement loss.
The user's PostgreSQL-first requirement makes the separate encrypted table the
smallest coherent approach. The user approved this document and its safeguards.

## Recovery delivery

- Add a recovery-delivery mapping and additive revision `0012`, following `0011`.
  One job per challenge, foreign keys, state/attempt constraints, due/lease indexes.
  Store ciphertext, nonce/key version, attempts, due time, lease token/expiry and
  fixed error codes. No ordinary notification or audit message contains the OTP.
- Use the established `cryptography` AES-GCM implementation with an independent
  256-bit managed key, fresh 96-bit random nonce per encryption, and authenticated
  associated data binding challenge, account and expiration. Encrypt recipient
  and OTP together; never implement encryption primitives by hand.
- Challenge creation, supersession/cancellation and encrypted enqueue occur in
  the same business transaction. Encryption/enqueue failure rolls everything
  back, including retirement of a previous usable challenge. Suppression and
  ineligible identities create no deliverable job.
- Remove the real delivery responsibility from Starlette background tasks.
  Tests inject a fake SMTP adapter into the worker; never send real email.
- Claim with FOR UPDATE SKIP LOCKED and commit the lease before network I/O.
  Fence acknowledgement by lease token; reclaim expired crash leases; cap
  attempts and use the existing exponential backoff settings.
- Before each send revalidate account eligibility, password binding, challenge
  expiry/attempts/used/verified state and current lease ownership. Expired,
  superseded, consumed or otherwise invalid work is cancelled and erased.
- Reuse user → recovery → delivery row ordering. After lease commit, the send
  transaction holds those locks through bounded SMTP send and acknowledgement.
  Issuance therefore waits for an active send, then supersedes the challenge.
  Other workers skip the locked job even if its lease expires. This trades a
  short account-lock wait for a clear supersession boundary. SMTP timeout and DB
  transaction/connection limits must be reviewed together before activation.
- SMTP acceptance followed by process/DB failure can still cause a later retry
  of the same message. Use a stable Message-ID and document at-least-once retry
  semantics, not exactly-once delivery. Database connection loss while SMTP is
  in flight also cannot retract a message already accepted by the server.
  Previously invalidated codes must remain unusable regardless of delivery order.
- Erase ciphertext/nonce after success, cancellation or terminal failure. Expiry
  cleanup must also cover jobs whose next retry is in the future. Worker downtime
  delays erasure until cleanup resumes; backup retention needs explicit policy.
- Keep activation disabled by default. A later authorized staging procedure must
  verify migration, separate keys, TLS mail configuration, worker supervision,
  crash/retry tests and operational limits before opting in. Missing keys,
  disabled delivery or invalid activation prerequisites fail closed.
- Rotation uses a key identifier and a small key ring: new jobs use the active
  key; old keys remain available only until outstanding jobs expire/drain. Never
  reuse JWT/HMAC keys. Emergency rotation cancels and erases outstanding payloads.

## Registration journeys

- Keep generic `/register` compatibility. Add buyer-specific entry intent and
  enforce SELLER submission from the seller-specific journey regardless of
  generic selector state. Seller form: Create Seller Account, no role selector,
  no buyer switch, existing fields/validation and login return link.
- Login exposes Create Buyer Account, Become a Seller and Offer Your Services.
  Buyer-specific registration fixes BUYER and hides irrelevant selection.
- Service registration reuses SELLER account creation, labels it Service Provider
  Registration, hides the selector and explains that listings need review.
  After registration, the sign-in continuation points to `/seller/creative`
  using an allowlisted local destination, not an arbitrary redirect URL.
- Existing signed-in sellers go directly to their existing creative studio.
  Existing buyers see a precise unsupported-enrollment message and retain their
  account and role. Do not encourage duplicate-account creation. Administrators
  retain their separate entry and existing permissions.
- Category, portfolio, pricing and service area remain in the existing studio
  onboarding/listing form; VFX is already supported. Do not collect fields during
  public registration that the backend cannot persist safely.
- Preserve listing moderation and restricted participant operations. Report the
  missing standalone provider-verification capability explicitly; do not describe
  account creation or profile saving as provider approval.

## Verification and delivery evidence

Write regression tests before product changes. Cover encrypted persistence,
authenticated-data/tamper rejection, no plaintext in ordinary fields/logs,
enqueue rollback, simultaneous requests/claims, expired/superseded jobs, active
send supersession policy, restart and expired leases, exhausted attempts,
temporary/permanent SMTP failures, erasure, reset/session revocation, and existing
buyer/seller/admin authorization. Add offline PostgreSQL DDL and revision-chain
tests. Any execution of a migration must use a newly created disposable test
database/schema, never an existing application database.

Frontend tests cover each entry point, hidden selectors, enforced payload roles,
safe continuation, existing-account boundaries, provider categories/moderation
and existing authentication/recovery. Check 390/768/1440px, TypeScript and the
production build. Record every command and failed/skipped/interrupted/not-run
case, plus complete final Git status. Request an independent read-only review.

## Dependency history

Initially the backend virtual environment did not contain `cryptography`. A dependency
installation attempt for `cryptography==49.0.0` failed because sandbox network
access was denied (WinError 10013); the error is not evidence that the version is
unavailable. No dependency was installed and no requirements file was changed.
After approval, the authorized network-enabled installation succeeded and the
runtime reports `cryptography` 49.0.0. Real AES-GCM tests now run, without any
substitute encryption. The original failed installation remains in the evidence.

## Migration and activation operations

Review database identity, current revision and schema ownership; take an encrypted
backup and rehearse restoration before separately authorizing application of
0012. Prefer application rollback while retaining additive tables. Downgrade
must refuse retained delivery history rather than delete it. Do not run migration,
key provisioning, SMTP or activation steps as part of implementation verification
against existing development/staging/beta/production databases.

Implementation/verification evidence and unresolved operational blockers belong
in the final implementation report. Design approval does not authorize deployment,
real credentials, real emails or migration execution against existing databases.
