"""Read-only local discovery inventory; emit counts, never points or identities."""
import json
import argparse
import getpass
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import psycopg
from sqlalchemy.engine import make_url
from app.core.config import Settings
from app.schemas.location import Coordinate
from app.services.discovery import locality_center
from app.services.geography import distance_km


FUNNEL = """
SELECT count(*) AS total_products,
 count(*) FILTER (WHERE p.status='APPROVED') AS approved,
 count(*) FILTER (WHERE p.status='APPROVED' AND p.is_active) AS approved_active,
 count(*) FILTER (WHERE p.status='APPROVED' AND p.is_active AND p.stock_quantity>0) AS in_stock,
 count(*) FILTER (WHERE p.status='APPROVED' AND p.is_active AND p.stock_quantity>0
   AND u.is_active AND u.role='SELLER') AS active_seller,
 count(*) FILTER (WHERE p.status='APPROVED' AND p.is_active AND p.stock_quantity>0
   AND u.is_active AND u.role='SELLER' AND s.dispatch_location_confirmed_at IS NOT NULL)
   AS eligible_before_locality,
 count(*) FILTER (WHERE s.latitude IS NULL OR s.longitude IS NULL) AS missing_seller_coordinates
FROM public.products p
JOIN public.seller_profiles s ON s.id=p.seller_id
JOIN public.users u ON u.id=s.user_id
"""


def inspect(database=None, check_point=False):
    url = make_url(Settings().database_url.get_secret_value())
    if (url.host not in {'localhost', '127.0.0.1', '::1'}
            or (url.port or 5432) != 5432 or url.query
            or not url.database.startswith('whatnot_')):
        raise RuntimeError('STOP: unexpected local inspection configuration')

    def connect(name):
        return psycopg.connect(host=url.host, port=url.port or 5432,
            user=url.username, password=url.password, dbname=name, connect_timeout=5,
            options='-c default_transaction_read_only=on -c statement_timeout=5000')

    with connect(url.database) as connection:
        if connection.execute('SHOW transaction_read_only').fetchone()[0] != 'on':
            raise RuntimeError('STOP: read-only source connection unavailable')
        databases = connection.execute("""SELECT datname,oid FROM pg_database
            WHERE starts_with(datname,'whatnot_') AND datallowconn
            AND has_database_privilege(current_user,oid,'CONNECT') ORDER BY datname""").fetchall()
        sessions = connection.execute("""SELECT datname,state,count(*) FROM pg_stat_activity
            WHERE starts_with(datname,'whatnot_') AND pid<>pg_backend_pid()
            GROUP BY datname,state ORDER BY datname,state""").fetchall()
        connections = connection.execute("""SELECT datname,pid,client_port,state FROM pg_stat_activity
            WHERE starts_with(datname,'whatnot_') AND pid<>pg_backend_pid()
            AND client_port IS NOT NULL ORDER BY datname,pid""").fetchall()

    result = {'captured_at_utc': datetime.now(timezone.utc).isoformat(),
              'configured_database': url.database, 'read_only': True,
              'sessions': [{'database': name, 'state': state, 'count': count}
                           for name, state, count in sessions],
              'connections': [{'database': name, 'postgres_pid': pid, 'client_port': port, 'state': state}
                              for name, pid, port, state in connections], 'databases': []}
    if database is not None:
        if database not in {name for name, _ in databases}:
            raise RuntimeError('STOP: selected database identity not found')
        databases = [(name, oid) for name, oid in databases if name == database]
    if check_point and database is None:
        raise RuntimeError('STOP: private-point inspection requires an explicit database name')
    if check_point and not sys.stdin.isatty():
        raise RuntimeError('STOP: private-point inspection requires an interactive terminal with hidden input')
    point = (Coordinate(latitude=getpass.getpass('Latitude from the confirmed request (hidden): '),
                        longitude=getpass.getpass('Longitude from the confirmed request (hidden): '))
             if check_point else None)
    for name, expected_oid in databases:
        with connect(name) as connection:
            connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            actual = connection.execute("""SELECT current_database(),oid
                FROM pg_database WHERE datname=current_database()""").fetchone()
            if tuple(actual) != (name, expected_oid):
                raise RuntimeError('STOP: database identity mismatch')
            entry = {'database': name, 'oid': expected_oid,
                     'transaction_read_only': connection.execute('SHOW transaction_read_only').fetchone()[0]}
            if entry['transaction_read_only'] != 'on':
                raise RuntimeError('STOP: inventory transaction is not read-only')
            if not connection.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0]:
                entry['schema'] = 'uninitialized'
            else:
                entry['revision'] = connection.execute('SELECT version_num FROM public.alembic_version').fetchone()[0]
                if entry['revision'] != '0008':
                    entry['inspection'] = 'unsupported revision; not queried'
                else:
                    entry['counts'] = {table: connection.execute(f'SELECT count(*) FROM public.{table}').fetchone()[0]
                        for table in ('users', 'seller_profiles', 'products', 'addresses', 'orders')}
                    with connection.cursor() as cursor:
                        cursor.execute(FUNNEL)
                        entry['eligibility_funnel'] = dict(zip([column.name for column in cursor.description], cursor.fetchone()))
                    entry['product_status_counts'] = dict(connection.execute(
                        'SELECT status,count(*) FROM public.products GROUP BY status ORDER BY status').fetchall())
                    entry['confirmed_seller_profiles'] = connection.execute(
                        'SELECT count(*) FROM public.seller_profiles WHERE dispatch_location_confirmed_at IS NOT NULL').fetchone()[0]
                    entry['invalid_seller_coordinates'] = connection.execute("""SELECT count(*)
                        FROM public.seller_profiles WHERE latitude IS NULL OR longitude IS NULL
                        OR NOT (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)""").fetchone()[0]
                    columns = connection.execute("""SELECT table_name,column_name,numeric_precision,numeric_scale,is_nullable
                        FROM information_schema.columns WHERE table_schema='public'
                        AND table_name IN ('seller_profiles','addresses')
                        AND column_name IN ('latitude','longitude') ORDER BY table_name,column_name""").fetchall()
                    entry['location_columns'] = [dict(zip(
                        ['table','column','precision','scale','nullable'], row)) for row in columns]
                    if point is not None:
                        eligible = connection.execute("""SELECT s.latitude,s.longitude,p.delivery_radius_km
                            FROM public.products p JOIN public.seller_profiles s ON s.id=p.seller_id
                            JOIN public.users u ON u.id=s.user_id
                            WHERE p.status='APPROVED' AND p.is_active AND p.stock_quantity>0
                            AND u.is_active AND u.role='SELLER'
                            AND s.dispatch_location_confirmed_at IS NOT NULL""").fetchall()
                        entry['private_point_check'] = {
                            'eligible_before_locality': len(eligible),
                            'locality_candidates': sum(
                                distance_km(point.latitude, point.longitude, *locality_center(lat, lon)) <= radius + .8
                                for lat, lon, radius in eligible),
                            'coordinates_recorded': False,
                        }
            result['databases'].append(entry)
    return result


if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--database')
        parser.add_argument('--check-point', action='store_true')
        args = parser.parse_args()
        result = inspect(args.database, args.check_point)
        evidence_name = 'discovery-private-point-counts.json' if args.check_point else 'discovery-inventory.json'
        (Path(__file__).parent / 'evidence' / evidence_name).write_text(
            json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))
    except Exception as error:
        print(json.dumps({'status': 'STOP', 'exception_class': type(error).__name__,
                          'message': str(error) if type(error) is RuntimeError else 'Private connection inputs suppressed'}))
        raise SystemExit(1)
