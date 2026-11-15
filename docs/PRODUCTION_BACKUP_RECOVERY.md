# Proposed production database initialization and recovery

Prepared 15 November 2026. **Commands below are reviewed preparation for a future authorized operator; none were executed against AWS or a database in this task.** Production starts with an **empty new pilot database**. Do not copy the local development database, its five original accounts, orders, personal data or synthetic sixth smoke account. No credentials are selected or changed by this document.

## Existing evidence and limits

Read [readiness audit](PRODUCTION_READINESS_AUDIT.md), [overnight recovery](OVERNIGHT_RECOVERY_REPORT.md), [local cutover history](AUTH_LOCAL_CUTOVER.md), [final rehearsal](AUTH_MIGRATION_FINAL_REHEARSAL.md) and [beta runbook](BETA_RUNBOOK.md). Historical isolated rehearsal restored a 31,480-byte 0004 archive and successfully migrated it to 0008; migration time **1.578 seconds** is not a production recovery-time measurement. The successful overnight cutover's later 31,700-byte archive SHA-256 `75cbb960eb64b61ebe9aba5f377efe7d4c96018b556502ad43ade30951a08025` passed listing/hash checks but **has not been restore-tested**. The older stopped-attempt archive (`eccda308...`) is a different file and must not be confused with it. TEMP is not durable backup storage. Those archives are private local recovery artifacts and must not be uploaded into the pilot. No production backup, restore, RPO or RTO evidence exists yet.

## Database identity and least privilege

### Installation/provisioning gate

For the same-host option, Ubuntu's generic `postgresql` package follows the distribution's selected major; do not assume it installs 17. On the **new approved Ubuntu 24.04 host only**, approve the PostgreSQL project's signed PGDG repository and patch source first, following its [official Ubuntu instructions](https://www.postgresql.org/download/linux/ubuntu/) (supports Noble amd64/arm64). Review the provided key/repository configuration; do not pipe an unreviewed download into a shell. After repository approval, the versioned package step is:

```bash
sudo apt update
sudo apt install postgresql-17 postgresql-client-17
pg_dump --version
psql --version
```

Capture installed package/server versions and updates; confirm selected major/architecture. Package installation can start a default cluster: keep ingress closed, establish operator maintenance controls and inspect listener/auth settings before use. Do not attach existing local volumes or modify the Windows database. For private RDS, instead provision the separately approved supported engine major/private subnet group/SG/encryption/backup parameters and install only matching client tools on the operator/backup host. No installation/provisioning command was executed by this preparation.

Use PostgreSQL 17 with current security fixes and matching PostgreSQL 17 client tools. Pin reviewed migrations through revision **0008**, never `stamp`, `create_all`, `downgrade` or an unreviewed future `head`. Verify release hashes, `alembic heads` and model compatibility before use. Same-host production DB may use loopback with SCRAM; a remote DB requires DNS hostname, `sslmode=verify-full` and nonempty readable `sslrootcert`. Never allow remote plaintext or public 5432.

Future Linux operator example: approved new database name `whatnot_pilot`, migration login `whatnot_migrate`, application login `whatnot_runtime`, backup login `whatnot_backup`. These are **proposed names**, not existing resources. Migration role owns DB/schema/objects; runtime has no ownership, CREATE, SUPERUSER, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS or membership in migration role. Backup role reads only this application's tables/sequences. Do not run migrations using the runtime login or RDS master login. On RDS use a separately authorized admin connection rather than the local `sudo` command.

After explicit provisioning authorization, confirm that this is the **new approved host**, not the original Windows DB, then use an interactive administrator psql session. `\password` prompts avoid SQL-literal/command-line secrets; choose credentials through the approved secret process and do not record them in a transcript.

```bash
sudo -u postgres psql -X --set=ON_ERROR_STOP=1 --dbname=postgres
```

```sql
SELECT current_database(), current_user, inet_server_addr(), inet_server_port(), version();
-- STOP unless server/account identity is approved and all proposed names are absent.
SELECT datname FROM pg_database WHERE datname = 'whatnot_pilot';
SELECT rolname FROM pg_roles WHERE rolname IN
  ('whatnot_migrate','whatnot_runtime','whatnot_backup');
CREATE ROLE whatnot_migrate LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE whatnot_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE whatnot_backup LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
\password whatnot_migrate
\password whatnot_runtime
\password whatnot_backup
CREATE DATABASE whatnot_pilot OWNER whatnot_migrate;
REVOKE ALL ON DATABASE whatnot_pilot FROM PUBLIC;
GRANT CONNECT ON DATABASE whatnot_pilot TO whatnot_runtime, whatnot_backup;
\connect whatnot_pilot
ALTER SCHEMA public OWNER TO whatnot_migrate;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO whatnot_runtime, whatnot_backup;
-- Future-object grants apply only to objects CREATED BY this migration role.
ALTER DEFAULT PRIVILEGES FOR ROLE whatnot_migrate IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO whatnot_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE whatnot_migrate IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO whatnot_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE whatnot_migrate IN SCHEMA public
  GRANT SELECT ON TABLES TO whatnot_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE whatnot_migrate IN SCHEMA public
  GRANT SELECT ON SEQUENCES TO whatnot_backup;
```

Limit `pg_hba.conf` to the exact database/roles and loopback clients with `scram-sha-256`; use `hostssl` for remote clients. Inspect rules/order and reject broad trust rules. RDS manages authentication/network differently; review its parameter/SSL settings and SG instead of editing host files. Runtime role must not receive schema CREATE or role membership as a workaround for missing grants. [PostgreSQL privileges](https://www.postgresql.org/docs/17/ddl-priv.html) distinguish ownership from grants.

## Initialize the empty pilot to 0008

Stop API and every worker/timer before initialization. No service should start automatically on failure. From the reviewed release's `backend` directory, use its validated Linux virtualenv. This Python block prompts through the terminal, constructs an escaped SQLAlchemy URL in memory, prints no credentials and passes an already-verified connection to Alembic (supported by `backend/alembic/env.py`). It **refuses populated databases** and does not read local `.env` for its target. For RDS supply its DNS endpoint and CA path; for local host type exactly `127.0.0.1`. Verify the printed DB OID/server address against the approved inventory before typing confirmation.

```bash
.venv/bin/python - <<'PY'
from getpass import getpass
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic import command

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def ask(prompt):
    # stdin contains this script; prompts must read the operator's terminal.
    with open('/dev/tty', 'r+') as terminal:
        terminal.write(prompt)
        terminal.flush()
        answer = terminal.readline()
        if not answer:
            raise RuntimeError('An interactive operator terminal is required')
        return answer.rstrip('\n')
host = ask('Approved DB DNS hostname or 127.0.0.1: ').strip()
require(host and host.lower() not in {'localhost', '::1'}, 'Use the approved explicit DB endpoint')
query = {}
if host != '127.0.0.1':
    from pathlib import Path
    ca = ask('Approved absolute CA bundle path: ').strip()
    require(Path(ca).is_absolute() and Path(ca).is_file(), 'Verified remote CA bundle is required')
    query = {'sslmode': 'verify-full', 'sslrootcert': ca}
url = URL.create('postgresql+psycopg', username='whatnot_migrate',
    password=getpass('Migration DB password: '), host=host, port=5432,
    database='whatnot_pilot', query=query)
engine = create_engine(url, echo=False, hide_parameters=True,
                       connect_args={'connect_timeout': 5})
with engine.connect() as connection:
    identity = connection.execute(text('''SELECT current_database(), current_user,
        inet_server_addr()::text, inet_server_port(),
        (SELECT oid FROM pg_database WHERE datname=current_database())''')).one()
    require(identity[0] == 'whatnot_pilot' and identity[1] == 'whatnot_migrate', 'Wrong pilot identity/role')
    require(connection.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")) == 0,
            'Target must be empty; no migration attempted')
    print('Verify target name/user/address/port/OID:', tuple(identity))
    require(ask('Type INITIALIZE EMPTY whatnot_pilot after independent identity check: ') == 'INITIALIZE EMPTY whatnot_pilot',
            'Initialization not confirmed')
    connection.rollback()
    cfg = Config('alembic.ini')
    require(ScriptDirectory.from_config(cfg).get_heads() == ['0008'], 'Unexpected migration head')
    cfg.attributes['connection'] = connection
    command.heads(cfg)  # must show the reviewed single head 0008
    command.upgrade(cfg, '0008')
    command.current(cfg)
    command.check(cfg)
    require(connection.scalar(text('SELECT version_num FROM alembic_version')) == '0008', 'Revision verification failed')
    require(connection.scalar(text('SELECT count(*) FROM users')) == 0, 'Unexpected users')
    require(connection.scalar(text('SELECT count(*) FROM orders')) == 0, 'Unexpected orders')
engine.dispose()
PY
```

Independently verify identity/revision, 24 application-schema tables including Alembic version (review against the release metadata), `request_quotas`, both nullable `users.email_verified_at` and `users.phone_verified_at`, valid constraints/indexes, ownership and no unexpected business rows. Every application object should be owned by `whatnot_migrate`. Capture aggregate/redacted output only. No successful initialization is claimed until those commands are actually run on the approved target.

Default grants above also cover the newly created version table; remove runtime mutation access to it explicitly. In an approved migration-role psql session on this DB:

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO whatnot_runtime;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO whatnot_runtime;
REVOKE ALL ON public.alembic_version FROM whatnot_runtime;
GRANT SELECT ON public.alembic_version TO whatnot_runtime;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO whatnot_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO whatnot_backup;
```

Verify via runtime connection: readiness reads succeed; application transaction/sequence writes succeed using disposable synthetic pilot acceptance data; DDL, access to unrelated DBs and updating `alembic_version` fail. Do not use the original local database for this check. Recheck grants after every migration. Full-table runtime DML is required by current application services; the application still enforces user-level authorization, not DB row-level isolation.

## Admin bootstrap and exactly five identities

The preparation now supplies `backend/app/bootstrap_admin.py`, invoked as `python -m app.bootstrap_admin`; see the [deployment runbook](AWS_PILOT_DEPLOYMENT_RUNBOOK.md#4-maintenance-db-initialization-and-first-administrator). Public `UserRegistration.role` still accepts BUYER/SELLER only; never weaken it to register ADMIN. The operator tool uses `UserService.create(UserCreate(...role='ADMIN', password_hash=hash_password(...)))` inside an explicit transaction. `UserCreate` validates an encoded Argon2id/bcrypt hash and the service flushes inside a savepoint. No default password or local hash is copied.

Before production execution, rehearse this operator tool against an approved empty staging pilot database under the **pilot runtime connection**, with name/email/phone from protected interactive input and password via `getpass` twice, 8–128 characters, `hash_password` in memory, SQL echo off. Guards verify target name/address/port/OID/runtime role, revision 0008, zero users and selected admin admission in the **five-entry production allowlist**, and require explicit target confirmation before the single insert; repeat execution refuses. It prints success/aggregate evidence, not identity/hash/password/token. Guard unit tests are local evidence; a successful PostgreSQL staging bootstrap is a **pending rehearsal gate**, not a claimed success. Have the owner keep the initial password privately; no forced-reset feature exists. The remaining four users register with their own credentials through the approved perimeter. Do not add a sixth operator. Record actual out-of-band identity checks before setting verification timestamps; source code does not prove identity.

## Consistent private backup

Proposed starting policy: custom-format logical dump **every 6 hours**, retain 28 six-hourly generations (7 days), 28 daily generations, 8 weekly generations; owner/privacy approval pending. Retention applies to successfully uploaded encrypted versions and must include noncurrent object-version lifecycle expiry, not only current files. Keep a pre-release dump separately until release acceptance. Encrypted versioned private S3 bucket with Block Public Access, TLS-only policy and SSE-KMS (or explicitly approved SSE-S3); recovery identity can decrypt even if EC2 is lost. Separate backup upload role from restore/retention administrator. Consider separate-account copy and Object Lock after reviewing retention/deletion obligations and additional cost. Do not grant the app/backup uploader deletion of backups or KMS administration.

`pg_dump` provides a consistent single-database snapshot while writers run. It does not back up cluster roles/tablespaces, server configuration, packages, release code or certificate/secret recovery. Maintain a separate protected inventory of roles/grants/config/release digest and secret references, never plaintext passwords in the report. Use a matching major-version pg_dump; failure must stop publication and alert. [PostgreSQL pg_dump documentation](https://www.postgresql.org/docs/17/app-pgdump.html).

Future manual Linux example, using an approved protected `PGSERVICEFILE` and `PGPASSFILE` (0600) for the **whatnot_backup** role; do not put passwords or credential URLs in commands. `whatnot_pilot_backup` must pin host/port/db/user and remote verified-TLS parameters. The output directory must be encrypted and owned by the backup operator, mode 0700. These paths are proposals and are not created here.

```bash
set -euo pipefail
umask 077
export PGSERVICEFILE=/etc/whatnot/backup-pg-service.conf
export PGPASSFILE=/etc/whatnot/backup.pgpass
psql 'service=whatnot_pilot_backup' -X -v ON_ERROR_STOP=1 -c \
  'SELECT current_database(), current_user, inet_server_addr(), inet_server_port();'
# Independently compare identity to approved inventory before continuing.
backup_dir=$(mktemp -d /var/lib/whatnot-backups/pilot-XXXXXXXX)
pg_dump --dbname='service=whatnot_pilot_backup' --format=custom \
  --file="$backup_dir/whatnot_pilot.dump"
test -s "$backup_dir/whatnot_pilot.dump"
sha256sum "$backup_dir/whatnot_pilot.dump" > "$backup_dir/whatnot_pilot.dump.sha256"
pg_restore --list "$backup_dir/whatnot_pilot.dump" > "$backup_dir/archive-list.txt"
```

Upload archive/checksum/private manifest only to the preapproved bucket/prefix using the narrowly scoped role after separate AWS authorization. Record UTC snapshot **start**, completion, upload/verification time, object/version ID, bytes, SHA-256, PostgreSQL/release/schema versions and exit statuses. Verify the downloaded object's SHA-256 on an isolated recovery host; an S3 ETag is not a general SHA-256 checksum. Mark backup successful only after off-host verification. Do not emit archive lists containing sensitive object metadata into public logs. No S3 mutation command is executed or authorized here.

**A checksum and `pg_restore --list` prove neither complete data recovery nor application usability.** Before first admission, restore the actual first pilot backup into an isolated target and run the checks below. Repeat monthly, after schema/backup changes and after relevant PostgreSQL upgrades. Proposed alarms: dump/upload failure immediately, no verified off-host snapshot-start within 7 hours, insufficient disk, retention job failure; missed-backup alarm must be outside the failed host.

## Explicit isolated restore, never an automatic recovery action

1. Incident operator identifies the approved snapshot/recovery point; preserve failed production storage/logs/newer audit data. Do not restore over the live DB, drop it, use `--clean`, or run the local recovery scripts on production.
2. Obtain **separate authorization** for a uniquely named empty recovery target such as `whatnot_pilot_restore_YYYYMMDD`; use an isolated new instance/cluster/private DB with production API/workers unable to connect. Disable SMTP and all timers in the restored application. Record host/account/region/name/OID/owner before any writes. Downloads are private; reject an untrusted/mismatched archive.
3. Provision isolated restore/migration ownership and runtime grants deliberately. Restoring `--no-owner --no-privileges` means grants/ownership are **not** recovered from the archive; apply the reviewed role procedure for the recovery target. Never grant production credentials to a test app. Confirm zero user tables and match the uniquely approved target; operator confirmation is mandatory. The literal restore name below is an example and must be replaced in the protected service definition after approval.
4. Run only against that reviewed service target:

```bash
sha256sum --check /private/recovery/whatnot_pilot.dump.sha256
psql 'service=whatnot_isolated_restore' -X -v ON_ERROR_STOP=1 -c \
  'SELECT current_database(), current_user, inet_server_addr(), inet_server_port(), (SELECT oid FROM pg_database WHERE datname=current_database());'
# STOP until target identity AND empty-schema check are independently confirmed.
psql 'service=whatnot_isolated_restore' -X -v ON_ERROR_STOP=1 -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
pg_restore --dbname='service=whatnot_isolated_restore' --exit-on-error \
  --single-transaction --no-owner --no-privileges /private/recovery/whatnot_pilot.dump
```

The checksum file must refer to the downloaded archive path or be checked from its original relative directory; do not accidentally hash a retained source-host file. Never continue after a nonzero restore exit. A service file prevents accidental fallback to the local development URL but is not itself an identity guard: verify its endpoint and the live SQL identity before writes. Do not automate these manual confirmation steps away.

5. Verify revision 0008 (or the separately approved archive/release pair), schema and constraints/indexes/sequences, object ownership/grants, foreign-key integrity, per-table counts and agreed business/audit aggregates against the backup manifest. Document consistency limits if writers ran during collection; independent count queries after pg_dump are not necessarily the same snapshot. Use synthetic-only app smoke actions on the isolated restore and verify login/roles/ownership/readiness and worker logic with SMTP disabled. Preserve real accounts privately; do not reset their passwords to make testing easy.
6. Record restore exit, total elapsed time, data validation, application checks, faults and named reviewer. Only this establishes a tested recovery artifact. A separate reviewed cutover may stop production writers, reconcile post-snapshot business/audit/email outcomes and switch the application to the validated target. Never automatically point production to a restore or automatically start email workers after restoring; previously sent messages may otherwise be resent. Retain the failed source until an explicit retention decision.

## Proposed objectives and alternatives

| Strategy | Proposed objective, pending owner acceptance | Evidence required |
| --- | --- | --- |
| Six-hourly off-host logical dumps | **RPO ≤7 hours**, including snapshot-start age/upload margin; **RTO ≤4 hours** from incident declaration to validated service restoration | Real data growth and concurrent-write test; timed new-host provisioning, secret/key access, download, restore, validation, certificate/network and controlled application cutover. A stalled/failed backup breaches RPO and alerts. Manual on-call response must fit RTO. |
| Self-managed PostgreSQL base backups + continuous encrypted WAL archive | Candidate **RPO ≤15 minutes**, **RTO ≤4 hours**, not promised | Implement/rehearse WAL archiving, archive lag/gap alarms, tested base backup/WAL continuity, retention, recovery target and off-host credentials. Logical dumps alone cannot provide PITR. Operational burden may outweigh five-user savings. |
| Private RDS automated backups/PITR | Candidate **RPO ≤15 minutes**, **RTO ≤4 hours**, not promised | Choose retention (propose 14 days), monitor actual latest restorable time, restore a new private DB instance and time complete app cutover/validation. AWS documents log upload about every five minutes, not a guaranteed user RPO/RTO. [RDS PITR](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html). |

Encrypted EBS snapshots can supplement full-host recovery but do not replace consistent database backup and logical restore evidence; a disk snapshot without database coordination is not an independently verified application recovery. RDS snapshots/PITR restore to a new instance; review parameter groups, TLS, security groups, credentials and initialization performance before cutover.

Prefer forward repair. App-only rollback is permitted only when the previous frontend/backend both support the current schema and business contract, demonstrated beforehand. Never blind-downgrade migrations: 0005 preserves lifecycle evidence, 0006 blocks destructive downgrade, 0007 protects populated Creative data and 0008 protects verification evidence and drops quotas on downgrade. Restoring an older snapshot loses subsequent writes, cannot unsend mail and may replay outbox effects; require an explicit reconciliation plan and approved recovery point before any production cutover.

Pending gates: approved region/target/owners, production secret delivery, bootstrap tool rehearsal, least-privilege tests, encrypted off-host storage and retention, independent recovery credentials/key access, first actual pilot backup restore, measured RPO/RTO, alert receipt and a named recovery operator. This document reports preparation, not a successful production initialization or restore.
