"""Original local admin recovery. Default: read-only. Never import from the API.

Execution requires separate owner approval, --execute, a verified backup and
interactive confirmation. Exceptions are deliberately not printed: driver errors
can contain bound parameters. This tool never creates users or migrates schemas.
"""
import argparse
from getpass import getpass, GetPassWarning
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.core.security import hash_password

DATABASE = 'whatnot_app_dev'
OID = 41069
EMAIL = 'admin@example.com'
CONFIRMATION = 'RESET EXISTING ADMIN whatnot_app_dev OID 41069'
PG_RESTORE = Path(r'C:\Program Files\PostgreSQL\17\bin\pg_restore.exe')


def require(condition):
    if not condition:
        raise RuntimeError('Recovery safeguard failed')


def validate_identity(actual, expected_user):
    require(len(actual) == 8)
    database, oid, host, port, user, version, recovery, owner = actual
    require((database, oid, host, port, user) ==
            (DATABASE, OID, '127.0.0.1', 5432, expected_user))
    require(170000 <= version < 180000 and recovery is False and owner is True)


def validate_account(rows):
    require(len(rows) == 1)
    require(rows[0][1:] == (EMAIL, 'ADMIN', True))
    return rows[0]


def verify_schema(connection, expected_user):
    identity = connection.execute("""
        SELECT current_database(), d.oid::bigint, host(inet_server_addr()),
               inet_server_port(), current_user, current_setting('server_version_num')::int,
               pg_is_in_recovery(), d.datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user)
        FROM pg_database d WHERE d.datname=current_database()
    """).fetchone()
    validate_identity(identity, expected_user)
    require(connection.execute('SELECT version_num FROM public.alembic_version').fetchall()
            == [('0008',)])
    columns = connection.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns WHERE table_schema='public' AND table_name='users'
    """).fetchall()
    require(('password_hash', 'character varying', 255, 'NO') in columns)
    require({row[0] for row in columns} == {
        'id', 'name', 'email', 'phone', 'password_hash', 'role', 'is_active',
        'created_at', 'updated_at', 'phone_verified_at', 'email_verified_at'})
    require(connection.execute("""SELECT count(*) FROM pg_trigger
        WHERE tgrelid='public.users'::regclass AND NOT tgisinternal""").fetchone()[0] == 0)


def public_tables(connection):
    tables = [row[0] for row in connection.execute("""SELECT tablename FROM pg_tables
        WHERE schemaname='public' ORDER BY tablename""").fetchall()]
    require('users' in tables and 'alembic_version' in tables)
    return tables


def preservation_digest(connection, user_id, tables):
    """Only opaque digests leave PostgreSQL; no stored credentials are fetched.

    Exclude only this account's password_hash. Include all other users' hashes,
    this account's timestamps/profile, and all rows in every public base table.
    Table locks keep the comparison stable while the transaction runs.
    """
    result = []
    for table in tables:
        expression = sql.SQL('to_jsonb(t)')
        params = ()
        if table == 'users':
            expression = sql.SQL("CASE WHEN t.id=%s THEN to_jsonb(t)-'password_hash' ELSE to_jsonb(t) END")
            params = (user_id,)
        query = sql.SQL("""SELECT encode(sha256(convert_to(COALESCE(
            string_agg(value, '' ORDER BY value), ''), 'UTF8')), 'hex')
            FROM (SELECT ({expression})::text AS value FROM public.{table} t) snapshot""").format(
                expression=expression, table=sql.Identifier(table))
        result.append((table, connection.execute(query, params).fetchone()[0]))
    return result


ACCOUNT_QUERY = """SELECT id,email,role,is_active FROM public.users
    WHERE lower(email)=lower(%s) FOR UPDATE"""


def reset_transaction(connection, expected_user, user_id, encoded, backup_check):
    with connection.transaction():
        verify_schema(connection, expected_user)
        tables = public_tables(connection)
        # Bound lock_timeout: refuse busy writers; never terminate sessions.
        for table in tables:
            connection.execute(sql.SQL('LOCK TABLE public.{} IN SHARE ROW EXCLUSIVE MODE').format(
                sql.Identifier(table)))
        verify_schema(connection, expected_user)
        account = validate_account(connection.execute(ACCOUNT_QUERY, (EMAIL,)).fetchall())
        require(account[0] == user_id)
        before = preservation_digest(connection, user_id, tables)
        backup_check()
        verify_schema(connection, expected_user)
        changed = connection.execute("UPDATE public.users SET password_hash=%s "
            "WHERE id=%s AND email=%s AND role='ADMIN' AND is_active RETURNING id",
            (encoded, user_id, EMAIL)).fetchall()
        require(changed == [(user_id,)])
        require(connection.execute('SELECT password_hash=%s FROM public.users WHERE id=%s',
                                   (encoded, user_id)).fetchone()[0] is True)
        require(validate_account(connection.execute(ACCOUNT_QUERY, (EMAIL,)).fetchall()) == account)
        require(preservation_digest(connection, user_id, tables) == before)


def hidden_password(prompt):
    with warnings.catch_warnings():
        warnings.simplefilter('error', GetPassWarning)
        return getpass(prompt)


def validate_password(value):
    require(8 <= len(value) <= 128)
    return value  # Never strip or normalize a password.


def verify_backup(path, expected_sha256):
    require(re.fullmatch(r'[0-9a-fA-F]{64}', expected_sha256) is not None)
    digest = hashlib.sha256()
    with path.open('rb') as archive:
        require(archive.read(5) == b'PGDMP')
        archive.seek(0)
        for block in iter(lambda: archive.read(1024 * 1024), b''):
            digest.update(block)
    require(digest.hexdigest() == expected_sha256.lower())
    listing = subprocess.run([str(PG_RESTORE), '--list', str(path)],
                             capture_output=True, text=True, check=False, timeout=30)
    require(listing.returncode == 0)
    require(re.search(r'^;\s+dbname:\s+whatnot_app_dev\s*$', listing.stdout, re.M) is not None)
    require(re.search(r'\bTABLE DATA public users\s', listing.stdout) is not None)


def connection_parameters():
    settings = Settings()
    require(settings.environment == 'development' and settings.database_url is not None)
    url = make_url(settings.database_url.get_secret_value())
    require(url.drivername == 'postgresql+psycopg' and url.database == DATABASE)
    require(url.host in ('localhost', '127.0.0.1', '::1') and (url.port or 5432) == 5432)
    require(not url.query and bool(url.username))
    return dict(host='127.0.0.1', port=5432, dbname=DATABASE, user=url.username,
                password=url.password, connect_timeout=5,
                application_name='whatnot_original_admin_recovery'), url.username


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--backup', type=Path)
    parser.add_argument('--backup-sha256')
    args = parser.parse_args(argv)
    params, role = connection_parameters()
    with psycopg.connect(**params, options='-c default_transaction_read_only=on -c statement_timeout=5000') as connection:
        with connection.transaction():
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            verify_schema(connection, role)
            account = validate_account(connection.execute(
                ACCOUNT_QUERY.replace(' FOR UPDATE', ''), (EMAIL,)).fetchall())
    print('READ-ONLY VERIFIED: 127.0.0.1:5432 / whatnot_app_dev / OID 41069 / revision 0008')
    print('Account verified: admin@example.com / active ADMIN. No password was read.')
    if not args.execute:
        print('CHECK ONLY: no reset executed.')
        return
    require(sys.stdin.isatty() and args.backup is not None and args.backup_sha256 is not None)
    backup_check = lambda: verify_backup(args.backup, args.backup_sha256)
    backup_check()
    print('Separate owner approval is required. Stop application writers before continuing.')
    require(input('Type exactly: ' + CONFIRMATION + '\n') == CONFIRMATION)
    password = validate_password(hidden_password('New password (8-128 characters): '))
    require(password == hidden_password('Confirm new password: '))
    encoded = hash_password(password)
    del password
    with psycopg.connect(**params, autocommit=True,
                         options='-c lock_timeout=5000 -c statement_timeout=15000') as connection:
        reset_transaction(connection, role, account[0], encoded, backup_check)
    del encoded
    print('COMMITTED: exactly one existing admin password hash updated; preservation checks passed.')
    print('Existing access tokens are not revoked by a password reset.')


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt):
        print('STOP: recovery did not complete successfully. No automatic retry. '
              'Verify outcome before any retry; sensitive error details suppressed.', file=sys.stderr)
        raise SystemExit(1) from None
