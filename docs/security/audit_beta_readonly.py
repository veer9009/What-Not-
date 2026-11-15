"""Release audit evidence only. Every database connection is forced read-only."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
import psycopg
from sqlalchemy.engine import make_url
from app.core.config import Settings


def main():
    settings = Settings()
    url = make_url(settings.database_url.get_secret_value())
    assert url.database == 'whatnot_app_dev'
    assert url.host in {'127.0.0.1', 'localhost', '::1'} and (url.port or 5432) == 5432 and not url.query
    evidence = {'configured_database': url.database, 'configured_environment': settings.environment,
                'configured_allowlist_count': len(settings.beta_allowed_emails),
                'configured_token_minutes': settings.access_token_expire_minutes, 'databases': []}
    for name, oid in [('whatnot_app_dev', 41069), ('whatnot_chrome_qa_20261115', 50640),
                      ('whatnot_tests_20261115_a7e394c2', 49265)]:
        with psycopg.connect(host='127.0.0.1', port=5432, user=url.username,
                password=url.password, dbname=name, connect_timeout=5,
                application_name='whatnot_release_audit_readonly',
                options='-c default_transaction_read_only=on -c statement_timeout=5000') as connection:
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            identity = connection.execute("""SELECT current_database(), d.oid::bigint,
                host(inet_server_addr()), inet_server_port(), current_setting('server_version_num')::int,
                pg_is_in_recovery(), d.datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user)
                FROM pg_database d WHERE datname=current_database()""").fetchone()
            assert identity[:4] == (name, oid, '127.0.0.1', 5432) and identity[5] is False
            assert connection.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
            revision = connection.execute('SELECT version_num FROM public.alembic_version').fetchall()
            columns = {r[0] for r in connection.execute("""SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='seller_profiles'""")}
            required = {'public_discovery_latitude', 'public_discovery_longitude',
                        'public_discovery_confirmed_at', 'public_discovery_consent_version'}
            counts = {table: connection.execute('SELECT count(*) FROM public.' + table).fetchone()[0]
                      for table in ('users', 'seller_profiles', 'products', 'addresses', 'orders')}
            row = dict(database=name, oid=oid, host=identity[2], port=identity[3],
                       server_version=identity[4], owner_matches=identity[6], read_only=True,
                       revision=[r[0] for r in revision], counts=counts,
                       missing_public_point_columns=sorted(required - columns))
            if name == 'whatnot_app_dev':
                row['sessions'] = [dict(database=r[0], client_port=r[1], postgres_pid=r[2],
                    state=r[3], open_transaction=r[4]) for r in connection.execute("""
                    SELECT datname,client_port,pid,state,xact_start IS NOT NULL FROM pg_stat_activity
                    WHERE datname=current_database() AND pid<>pg_backend_pid()""")]
            row['can_create_database'], row['can_create_schema'] = connection.execute("""
                SELECT rolcreatedb,has_database_privilege(current_database(),'CREATE')
                FROM pg_roles WHERE rolname=current_user""").fetchone()
            evidence['databases'].append(row)
            print(json.dumps(row), flush=True)
    path = Path(__file__).parent / 'evidence/beta-final-readonly.json'
    path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print('Read-only evidence saved.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('STOP: read-only audit failed; exception category=' + type(error).__name__, flush=True)
        raise SystemExit(1) from None
