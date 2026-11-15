# Restricted AWS pilot deployment runbook

15 November 2026. **Preparation only. No command in this document has been run against AWS.** Separate owner approval is required for infrastructure, costs, production configuration/credentials, DNS and deployment. This does not extend the completed local migration approval. Original `whatnot_app_dev` must never be a deployment/test/import target.

## Release inputs and stop conditions

Read [morning handoff](MORNING_DEPLOYMENT_HANDOFF.md), [architecture/cost design](AWS_PILOT_ARCHITECTURE.md), [DB/backup procedure](PRODUCTION_BACKUP_RECOVERY.md), [security gates](PRODUCTION_SECURITY_CHECKLIST.md), [monitoring](PRODUCTION_MONITORING_RUNBOOK.md) and [five-user UAT](FIVE_USER_PILOT_TEST_PLAN.md). Choose the minimum same-host private PostgreSQL option or private RDS explicitly. No container stack is introduced. Region, account, role, instance architecture, participant source networks/access gateway, five identities, support owner, domain/certificate, SMTP scope, budget and RPO/RTO require recorded owner choices.

The first command tomorrow is a **read-only identity gate**, after the operator selects an approved AWS profile/role in their own session:

```powershell
aws sts get-caller-identity
```

Compare account/ARN privately against the approved inventory; do not paste account identifiers or credentials into public evidence. This command is not a deployment. No honest EC2 creation/DNS command can be finalized until the missing inputs are approved. After identity review, use the approved architecture's provisioning plan; do not substitute an unreviewed `run-instances` command or create a default public DB. Do not open a public service to make testing convenient.

Stop on any wrong target, missing input, failed check, unresolved secret finding, failed migration, missing backup/restore proof, untested TLS/access gate or unsupported runtime. Do not blindly retry or automatically restore/downgrade/stamp/reset.

## 1. Local release verification and artifact

Use the reviewed working-tree snapshot, not just HEAD: current work is uncommitted. Do not run `git archive HEAD` and silently omit preparation fixes. Freeze a manifest of selected files and SHA-256 hashes; peer-review the complete diff. No commit/push is authorized here.

Windows verification from repository root:

```powershell
& 'C:/Program Files/nodejs/node.exe' node_modules/vitest/vitest.mjs run --config vite.config.ts --pool=threads --maxWorkers=1 --no-file-parallelism
& 'C:/Program Files/nodejs/npm.cmd' run build
Push-Location backend
& ./.venv/Scripts/python.exe -m pytest -q -W error tests --ignore=tests/persistence
Pop-Location
& backend/.venv/Scripts/python.exe docs/security/run_existing_server_tests.py --preparation
& backend/.venv/Scripts/python.exe -m pip check
git diff --check
```

Check `$LASTEXITCODE` immediately after **each** native command; stop on nonzero instead of continuing the block. The preparation DB harness verifies the pre-approved isolated DB name/OID and every SQL operation, refuses unknown/nonempty business targets, preserves quota rows, omits the four quota-mutating integration cases and compares original/test records afterward. Other tests write only rollback fixtures on that isolated DB. Do not run the full persistence directory unguarded; its default fixture creates an isolated cluster and failed with Windows restricted-token error 87 in this environment. Never redirect it to original data.

Run current approved JS/Python advisory and redacted secret scanners; unavailable tools are NOT VERIFIED. Preserve exact result/exit/count logs. Run frozen pnpm resolution only in the chosen build environment; do not regenerate the lock with npm. Project commands explicitly select `vite.config.ts` because ignored legacy generated JS configuration can otherwise take precedence; no legacy file was deleted. Build has production URL/NODE_ENV guards and defaults to `/api/v1`; root `.env.example` is development-only. If a developer copied its loopback override into `.env`, explicitly remove that override from the **build environment** or provide the approved `VITE_API_BASE_URL=/api/v1` setting for the build. Do not modify someone's credentials/env silently. Invalid overrides or development NODE_ENV production builds must fail.

Package only `dist/` as `frontend/`, backend application source/migrations/alembic.ini/requirements, `deploy/` and the reviewed operational docs/manifest. Exclude `.env*` except examples, `.venv`, `node_modules`, tests not required at runtime, dumps, raw logs, local records, caches and Git internals. Do not copy the Windows virtualenv. Produce a versioned artifact/digest locally; inspect contents before any authorized transfer. Do not upload the source workspace wholesale. Reproduce Linux runtime dependencies on the chosen architecture/Python version, with a private transitive inventory; exact direct pins are not a complete Python hash lock.

## 2. Approved host layout and service configuration

Proposed layout (choices, not claims of installed infrastructure):

```text
/opt/whatnot/releases/<approved-release-id>/frontend/
/opt/whatnot/releases/<approved-release-id>/backend/{app,alembic,.venv,...}
/opt/whatnot/current -> reviewed release directory
/etc/whatnot/backend.env                 protected root:whatnot 0640
/etc/whatnot/maintenance                 root-controlled maintenance marker
/etc/nginx/whatnot-pilot-access.conf     reviewed participant/VPN CIDRs, deny all last
```

The root-owned `/etc/whatnot` directory must not be writable by the application. Create a non-login `whatnot` OS user/group after approval, a root-owned immutable release tree readable by that user, and privately inject production settings from the approved secret store. No runtime secret/migration credential in the artifact or unit arguments. Same-host PostgreSQL is loopback/SCRAM; remote PostgreSQL needs verified TLS+CA, private networking and least privilege. Complete the DB procedure separately before admitting writers.

`backend/.env.production.example` is compatible with dotenv and systemd **when JSON arrays retain outer single quotes**, e.g. `WHAT_NOT_TRUSTED_HOSTS='["the-approved-hostname"]'`. Replace example values privately; do not literally use that placeholder. Keep exactly ten selected emails including admin. Set explicit production environment, strong dedicated JWT key, runtime DB URL, approved HTTPS origins (or empty CORS list for same-origin only), explicit trusted host and bounded connection settings. Disabled SMTP requires explicit approved in-app-only scope; otherwise inject provider settings with STARTTLS and verify real delivery privately. systemd `EnvironmentFile` is not a shell: no command substitutions, `export`, `$VAR` expansion or secrets on command lines. Pydantic's fallback `backend/.env` must not be shipped; the service environment supplies production values.

Templates: `deploy/systemd/whatnot-api.service`, `whatnot-worker@.service`, `whatnot-email.timer`, `whatnot-orders.timer`, `whatnot-properties.timer`. They use one Uvicorn process, private loopback 8000, proxy trust only from 127.0.0.1, no access log/body logging, non-root privileges, read-only system protection and journal output. Workers are bounded one-shot commands. No scheduling or installation occurred locally.

Before installing/enabling on the approved host:

```bash
sudo systemd-analyze verify /reviewed/path/whatnot-api.service \
  /reviewed/path/whatnot-worker@.service /reviewed/path/whatnot-email.timer \
  /reviewed/path/whatnot-orders.timer /reviewed/path/whatnot-properties.timer
```

Substitute actual reviewed file paths. Missing executable/user/env errors are failures to resolve, not warnings to suppress. Validate package/runtime imports and file permissions as `whatnot`; no app process should own release/service/env files. Resource capacity and PostgreSQL connection budget must be measured on Linux before pilot use. The read-only service does not perform migrations or install packages at startup.

## 3. Nginx, TLS and restricted ingress

No real domain/certificate path is invented. `deploy/nginx/whatnot.conf.template` has required render tokens. `deploy/render_nginx.py` validates DNS/path input, refuses configuration injection and exclusively creates a new output file; it does not install/reload or verify certificate contents.

After owner supplies real values, an example invocation using operator-selected shell variables is:

```bash
python3 deploy/render_nginx.py --domain "$PILOT_DOMAIN" \
  --certificate "$TLS_CERTIFICATE" --private-key "$TLS_PRIVATE_KEY" \
  --frontend /opt/whatnot/current/frontend \
  --access-file /etc/nginx/whatnot-pilot-access.conf \
  --output /private/review/whatnot.conf
```

All variables must be set to independently verified, approved values. No certificate/key is created, guessed or read by this renderer. Copy the access example into the reviewed host location and insert only approved participant/VPN CIDRs before `deny all;`. The unmodified example grants only loopback and denies everyone else. Mobile/dynamic IP participants need a reviewed stable access method; do not change the gate to `allow all`. Domain/TLS validation method and DNS changes need separate approval; prefer DNS-01 so port 80 can remain closed. Opening HTTP challenge paths is a separate access review.

The template is included inside Nginx's `http` context. Check existing site/default_server conflicts before installation; do not delete unrelated sites or keys. HTTPS serves static SPA/deep links; `/api/` proxies **without a trailing slash** to preserve FastAPI `/api/v1`. Upstream forwarding headers are overwritten from the immediate client, not appended to untrusted input. `/api/v1/ready` is restricted to loopback monitoring. API has 256 KiB body limit, 5s connect / 30s upstream limits and a conservative per-source edge limit; no file-upload feature exists. Review real valid payload sizes and rate behavior in staging.

Security headers include CSP, HSTS (no preload/includeSubDomains), nosniff, frame denial, no-referrer and geolocation self permission. CSP intentionally supports same-origin API, current inline styles and HTTPS images; an approved cross-origin API would also require explicit CSP `connect-src` review. API/no-store is supplied by FastAPI, hashed assets get long expiration and HTML gets no-cache. Access logs omit URI/query/body/token/IP; error logs still require private access, retention and synthetic redaction inspection. Nginx assigns a request ID for operator correlation; no full application correlation middleware is claimed.

Only after reviewed installation, before reload/start/admission:

```bash
sudo nginx -t
sudo systemctl daemon-reload
```

Do not run reload/start if syntax validation fails. Actual Nginx/systemd runtime validation is **pending**: neither was available as a runnable local service in this Windows preparation. Inspect actual TLS headers, deep links, API paths, role requests and nonparticipant denial over the approved HTTPS hostname before pilot access.

## 4. Maintenance, DB initialization and first administrator

For all DB initialization/migrations, create the root-controlled maintenance marker **before** stopping writers; stop timers, active worker instances and API and verify they are inactive. The marker blocks fresh unit starts, including failure restarts and timer launches; it does not stop an already running process. Stop commands are for the future approved host only:

```bash
sudo touch /etc/whatnot/maintenance
sudo systemctl stop whatnot-email.timer whatnot-orders.timer whatnot-properties.timer
sudo systemctl stop whatnot-worker@process-email.service whatnot-worker@auto-complete.service whatnot-worker@expire-properties.service
sudo systemctl stop whatnot-api.service
systemctl is-active whatnot-api.service whatnot-worker@process-email.service whatnot-worker@auto-complete.service whatnot-worker@expire-properties.service
```

Expected units inactive; inspect running processes, PostgreSQL sessions and external automation too. Do not terminate unrelated sessions. A momentary lack of a writer is not proof of a future write barrier. Maintain control of every writer/restart path and use the approved DB barrier for that server. Follow the clean-beta workflow in [database resolution](WHATNOT_DATABASE_RESOLUTION.md) for target identity/OID/role verification, an empty `whatnot_pilot_beta`, least-privilege grants and pinned `command.upgrade(cfg, '0009')`. Migration roles and dumps are separate from runtime credentials. No original local records or QA fixtures are transferred. Older 0008 examples in historical recovery documents do not apply to this release.

The operator tool `python -m app.bootstrap_admin` now prepares a single ADMIN through existing UserService/hash_password, without changing public registration. Run from the approved host's reviewed `backend`, with privately loaded production settings and five selected identities. This command requires the independently verified server address/OID:

```bash
.venv/bin/python -m app.bootstrap_admin --database whatnot_pilot \
  --server-address "$APPROVED_DB_SERVER_ADDRESS" --port 5432 --oid "$APPROVED_DB_OID"
```

It refuses development settings, original/non-pilot DB names, wrong DB/user/address/port/OID, schema other than 0009, an existing user or an admin outside the ten-email allowlist; the required DB role is `whatnot_runtime`. It prompts for exact target confirmation and private credentials, validates registration inputs, locks users against concurrent registration and commits one hashed ADMIN insert. Do not put passwords in shell arguments/history. The process must read the protected runtime environment through an approved operator session; **do not source the env as shell code or grant migration rights to the app**. Guard tests passed locally; successful PostgreSQL bootstrap on an empty staging pilot DB remains NOT VERIFIED. Rehearse it there before production execution. Initial user verification timestamps are not identity proof and must not be fabricated.

Pass the address exactly as returned by the tool's identity query `inet_server_addr()::text`, including a network suffix if PostgreSQL returns one; do not guess it from the DNS endpoint. OID/port/role must match the independently approved connection. On the authorized Ubuntu host, a root operator can load the protected environment into an interactive transient service rather than sourcing it or exposing it to command arguments:

```bash
sudo systemd-run --unit=whatnot-admin-bootstrap --wait --pty \
  --property=User=whatnot --property=Group=whatnot \
  --property=WorkingDirectory=/opt/whatnot/current/backend \
  --property=EnvironmentFile=/etc/whatnot/backend.env \
  /opt/whatnot/current/backend/.venv/bin/python -m app.bootstrap_admin \
  --database whatnot_pilot --server-address "$APPROVED_DB_SERVER_ADDRESS" \
  --port 5432 --oid "$APPROVED_DB_OID"
```

This is a future operator command, not a locally validated systemd invocation. Stop if environment/TTY/identity checks fail; do not relax file permissions or reuse another DB's credentials. The one-time service name must not already belong to unrelated work; record its exit and inspect only sanitized output.

Integrity/readiness/role checks must pass before a separately authorized operator clears the maintenance marker and starts API, then verifies health, then enables accepted worker timers. The marker is root-controlled state; clearing it is a deliberate approved operational action, never an automatic failed-migration fallback. No such action was performed here.

## 5. Admission, rollback and acceptance

With the perimeter still restricted, verify minimal health, private readiness 0008, safe headers, DB grants, five role flows and exact artifact hash; exercise [pilot acceptance](FIVE_USER_PILOT_TEST_PLAN.md), real alarm delivery and isolated backup restoration. Enable only approved mail/worker behavior and admit the five users gradually during staffed hours. Stop on security/integrity/privacy evidence failures. Monitor CPU/memory/disk/DB, quotas, 5xx, job failures and backlog age; record a release-owner GO separately.

Rollback preference: keep maintenance closed and diagnose. Code/static/config rollback is allowed only to a reviewed artifact compatible with the current schema and data. Do not downgrade 0008, reset quota history, restore over the live DB or retry a failed migration blindly. Preserve failed state/newer business and audit records; separately authorize isolated new-target restore and deliberate routing cutover if forward repair is insufficient. See [recovery plan](PRODUCTION_BACKUP_RECOVERY.md) and [incident runbooks](PRODUCTION_MONITORING_RUNBOOK.md).

CI/CD is currently a controlled **proposal**, not an installed Jenkins/GitHub pipeline: reviewed snapshot -> frozen dependencies -> static/tests/security scans -> production artifact/digest -> isolated HTTPS staging/UAT/restore -> human approval -> maintenance/migration/coordinated release -> health/monitoring -> compatibility-aware rollback. The [security checklist](PRODUCTION_SECURITY_CHECKLIST.md#ci-and-release-proposal--no-automatic-deployment) defines stage gates. No automatic production deploy or migration is configured.
