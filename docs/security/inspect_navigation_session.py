"""Local read-only diagnosis; never emit credentials, identities or coordinates."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
import psycopg
from sqlalchemy.engine import make_url
from app.core.config import Settings

def inspect():
    settings = Settings()
    url = make_url(settings.database_url.get_secret_value())
    assert url.host in {'localhost', '127.0.0.1', '::1'} and url.database.startswith('whatnot_') and not url.query
    result = {'database': url.database, 'access_token_minutes': settings.access_token_expire_minutes,
              'configured_environment': settings.environment}
    with psycopg.connect(host=url.host, port=url.port or 5432, user=url.username, password=url.password,
                        dbname=url.database, connect_timeout=5,
                        options='-c default_transaction_read_only=on -c statement_timeout=5000') as connection:
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        result['read_only'] = connection.execute('SHOW transaction_read_only').fetchone()[0] == 'on'
        assert result['read_only']
        result['revision'] = connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        cursor = connection.execute("""SELECT o.id,o.status,
            EXISTS (SELECT 1 FROM audit_events e WHERE e.entity_type='order' AND e.entity_id=o.id
              AND e.actor_id=o.buyer_id AND e.action='DELIVERY_LOCATION_CONFIRMED') AS buyer_confirmed,
            a.latitude BETWEEN -90 AND 90 AND a.longitude BETWEEN -180 AND 180 AS valid_saved_point,
            bu.is_active AS buyer_active,su.is_active AS seller_active
            FROM orders o JOIN addresses a ON a.id=o.address_id JOIN users bu ON bu.id=o.buyer_id
            JOIN seller_profiles s ON s.id=o.seller_id JOIN users su ON su.id=s.user_id ORDER BY o.id""")
        result['orders'] = [dict(zip([column.name for column in cursor.description], row)) for row in cursor.fetchall()]
        result['session_like_tables'] = [row[0] for row in connection.execute("""SELECT table_name
            FROM information_schema.tables WHERE table_schema='public'
            AND (table_name LIKE '%session%' OR table_name LIKE '%token%') ORDER BY table_name""")]
    return result

if __name__ == '__main__':
    try:
        report = json.dumps(inspect(), indent=2)
    except Exception as error:
        print(json.dumps({'error_class': type(error).__name__, 'private_details_suppressed': True}))
        raise SystemExit(1)
    (Path(__file__).parent / 'evidence/navigation-session-inventory.json').write_text(report, encoding='utf-8')
    print(report)
