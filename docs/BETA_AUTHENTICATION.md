# Controlled beta authentication audit and operator handoff

Date: 2026-11-18. Local investigation only. No live requests, AWS/EC2 access,
deployment, service changes, infrastructure changes or production database work
were performed. The live site is not claimed fixed.

## Findings and evidence boundaries

- Supplied live evidence: registration returned 403 with the explicit controlled
  beta denial. In this checkout that response means the effective allowlist is
  nonempty and does not contain the normalized submitted email. A missing/empty
  list alone does **not** explain that response in this version: production
  rejects it at settings initialization; development/test allow an empty list.
- Supplied configuration evidence: `.env` and process environment lack the
  allowlist, and fresh production `Settings()` rejects configuration. This is a
  confirmed configuration blocker according to the supplied investigation.
  It does not identify the running process's effective in-memory settings.
- Supplied timestamps show the process predates the configuration code on disk.
  `app.main` constructs settings at application import. Editing files cannot
  update that object. A stale release/process is a supported hypothesis; exact
  deployed code/configuration and the account admission decision remain unverified.
- Supplied live `/auth/refresh` 404 conflicts with this checkout, which implements
  POST `/api/v1/auth/refresh` and `/logout`. A frontend/backend release mismatch or
  routing mismatch needs manual verification; the supplied 404 alone cannot
  distinguish them. Do not remove renewal or prolong JWTs to conceal a 404.
- Locally reproduced frontend defect: a known beta-denial response was replaced
  by a generic permission message. The client now maps that exact public denial
  on auth endpoints to approved-email/contact-organizer guidance. Other details
  remain sanitized. No layout or form design changes.

## Current authentication contract

`RegisterPage` sends name, email, phone, exact password and BUYER/SELLER role to
POST `/api/v1/auth/register`. Pydantic validates and lowercases email; whitespace
is stripped from ordinary fields while password whitespace is preserved.
Admission precedes account creation. Duplicate normalized email/phone returns
409, including database uniqueness conflicts. ADMIN cannot self-register.
Passwords are salted Argon2id hashes; legacy bcrypt login upgrades the hash.
Wrong, missing and inactive credentials share 401. No password/hash in public users.

Registration does not log in. Login sends JSON email/password to POST
`/api/v1/auth/login`, with browser Origin, `X-WhatNot-CSRF: 1`, and credentials
included. The server checks admission and durable auth quotas, verifies the
password, creates a session, sets a refresh cookie, and returns a bearer JWT plus
user and `expires_in: 900`. `AuthContext` then verifies `/auth/me`; the persisted
role determines `/buyer`, `/seller`, or `/admin`, regardless of selected login UI.
Seller accounts create their complete shop profile at POST `/sellers/me` after
login. A missing seller profile is an onboarding requirement, not failed login.

Access tokens are memory-only, HS256 signed, expire after 15 minutes for sessions,
and contain subject, issue/expiry timestamps and session ID. The server verifies
claims plus active database user, live session, current role and admission on
every authenticated request. The legacy `access_token_expire_minutes` setting
does not change session-bound JWT lifetime. Frontend route guards and backend
role/ownership dependencies remain enforced.

Refresh tokens are random opaque values stored only in an HttpOnly, Secure,
SameSite=Strict, host-only `wn_refresh` cookie at `/api/v1/auth`; only SHA-256
digests/history are stored server-side. Refresh rotates, detects replay and does
not extend the absolute session ceiling (8 hours buyer/seller; 15 minutes admin).
Reload restores through refresh; timed/focus renewal and a bounded one-retry 401
path continue the session. Logout revokes the family and clears the cookie and
in-memory token. Failed logout warns that server revocation was not confirmed.
All cookie mutations require an allowed/same Origin and the CSRF header.
HTTPS and the intended same-site frontend/API arrangement are required; use the
same-origin `/api/v1` deployment profile. No localStorage/sessionStorage tokens.

## Manual EC2 configuration instructions (not executed)

1. Privately edit the backend environment source used by the actual service.
   Default Python dotenv location is `backend/.env` resolved relative to
   `app/core/config.py`, independent of working directory. If the service uses
   another protected EnvironmentFile, make that source consistent. Keep owner-only
   access; never paste real identities, URLs with credentials, signing keys or
   settings dumps into Git, tickets, chat, screenshots or terminal history.
2. Set this syntax with the **actual approved identities** in the private file:

   ```dotenv
   WHAT_NOT_ENVIRONMENT=production
   WHAT_NOT_BETA_ALLOWED_EMAILS='["approved-buyer@example.com","approved-seller@example.com"]'
   WHAT_NOT_ABUSE_LIMITS_ENABLED=true
   WHAT_NOT_AUTH_QUARTER_HOUR_LIMIT=20
   WHAT_NOT_CORS_ORIGINS='["https://avetest.online"]'
   WHAT_NOT_TRUSTED_HOSTS='["avetest.online"]'
   ```

   These are placeholder emails, not real approvals. Include every approved
   operator/admin as well. Pydantic Settings decodes `list[str]` from a JSON
   array: double-quoted JSON strings inside optional outer dotenv single quotes.
   CSV, Python single-quoted list entries, blank values and invalid emails fail.
   See [Pydantic Settings parsing documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#parsing-environment-variable-values).
   For a process environment injection, the value itself is JSON, without literal
   outer single quotes. Do not add wildcards or an admission fallback.
3. Preserve the existing private strong signing key, explicit runtime database
   URL, approved host/origins and all other production settings. Production also
   validates database transport and configured SMTP TLS. Do not generate/rotate
   credentials as an incidental configuration repair. Process environment takes
   precedence over `.env`: correct stale overrides at their authoritative source.
4. From the reviewed backend release directory, under the service's exact user,
   interpreter and environment, validate settings without opening a DB connection
   or printing identities/secrets:

   ```bash
   .venv/bin/python - <<'PY'
   from app.core.config import Settings
   try:
       s = Settings()
       assert s.environment == 'production'
       assert s.beta_allowed_emails and s.abuse_limits_enabled
   except Exception:
       raise SystemExit('INVALID production settings; inspect privately') from None
   print('Production settings valid; allowlist nonempty; abuse controls enabled')
   PY
   ```

   An interactive shell does not automatically inherit a service's environment;
   this check is meaningful only with the same effective environment. Avoid
   printing raw validation exceptions (malformed JSON may expose inputs).
5. Settings changes need a separately authorized service reload/restart/release
   before they affect the running object. None is authorized or performed here.
   For that future release, match frontend and backend versions and confirm the
   database is already at reviewed revision `0010` with auth session tables. If
   not, stop for a separately approved schema upgrade/backup plan. Do not use
   `create_all` or bootstrap against an existing production user table.
6. Preserve `bootstrap_admin.py` safeguards: production pilot target, database
   name/address/port/OID/runtime-role/schema identity checks, exactly ten admitted
   identities including the selected admin, empty users table, interactive target
   confirmation and private password input. Normal application admission requires
   a nonempty list, not exactly ten; bootstrap has the stricter existing rule.
   Do not run bootstrap to fix existing accounts or bypass it by self-registration.
7. After a separately authorized release, verify admitted buyer/seller registration
   and login, mixed-case email, duplicates, wrong password, nonparticipant denial,
   `/me`, actual browser cookie rotation, reload/expiry/logout and cross-role
   rejection. POST refresh with allowed Origin and the CSRF header must reach the
   route (401 without a session cookie is expected; 404 is not). Compare versions
   and request routing if 404 persists. Never share tokens or credentials in logs.

## Release limitations

No auth endpoint mismatch was found between this frontend and backend checkout.
The reported live mismatch remains unresolved until coordinated manual deployment
and verification. Older audit documents describe earlier no-refresh versions;
use this contract and `REFRESH_SESSION_IMPLEMENTATION.md` for the current release.
The whole-site beta perimeter and public browsing policy are outside this change.
No infrastructure or business behavior is changed.

Local verification results and any remaining blockers are recorded in
`BETA_AUTHENTICATION_RESULTS.md`.
