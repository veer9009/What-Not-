"""Read-only diagnosis of the configured local auth/schema mismatch.

Never calls auth routes, writes quota counters, executes migrations, or prints
credentials/customer records. PostgreSQL enforces read-only transactions.
Run from repository root using the existing backend virtual environment.
"""
import asyncio
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool
from fastapi import FastAPI
from app.api.errors import install_error_handlers
from app.core.config import Settings
from app.db.base import Base
import app.models
from app.models import User
from app.models.abuse import RequestQuota


def main():
    settings = Settings()
    if settings.database_url is None:
        print(json.dumps({'configured_database': False}))
        return 1
    url = make_url(settings.database_url.get_secret_value())
    # The user's current authorization is for the local development database.
    # Refuse accidental remote/cloud targets without exposing their address.
    if url.host not in {'localhost', '127.0.0.1', '::1'}:
        print(json.dumps({'refused': 'Configured database is not loopback; no connection attempted'}))
        return 1
    engine = create_engine(url, poolclass=NullPool, echo=False, hide_parameters=True,
        connect_args={'options': '-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=2000',
                      'connect_timeout': 5})
    result = {'environment': settings.environment,
              'auth_quotas_enabled': settings.abuse_limits_enabled and settings.environment != 'test',
              'beta_allowlist_count': len(settings.beta_allowed_emails),
              'signing_key_present': settings.jwt_secret_key is not None,
              'database_target_loopback': True,
              'settings_file': 'backend/.env (process environment takes precedence)',
              'probes': {}}
    boundary = FastAPI()
    install_error_handlers(boundary)
    try:
        with engine.connect() as connection:
            if connection.scalar(text('SHOW transaction_read_only')) != 'on':
                raise RuntimeError('Read-only safeguard unavailable')
            result['transaction_read_only'] = True
            result['database_name_matches_configuration'] = connection.scalar(text('SELECT current_database()')) == url.database
            result['applied_revisions'] = list(connection.scalars(text('SELECT version_num FROM alembic_version')))
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            result['table_count_in_default_schema'] = len(tables)
            result['users_count'] = connection.scalar(text('SELECT count(*) FROM users'))
            result['order_status_counts'] = dict(connection.execute(text(
                'SELECT status, count(*) FROM orders GROUP BY status ORDER BY status')).all())
            result['schema_drift'] = {}
            for table in Base.metadata.sorted_tables:
                if table.name not in tables:
                    result['schema_drift'][table.name] = {'missing_table': True}
                else:
                    columns = {column['name'] for column in inspector.get_columns(table.name)}
                    missing = sorted(set(table.columns.keys()) - columns)
                    if missing:
                        result['schema_drift'][table.name] = {'missing_columns': missing}
        # A failed parse aborts its transaction; isolate each probe connection.
        # LIMIT 0 validates current ORM projections without returning user data.
        for label, statement in [('current_user_projection', select(User).limit(0)),
                                 ('current_quota_projection', select(RequestQuota).limit(0))]:
            try:
                with engine.connect() as connection:
                    if connection.scalar(text('SHOW transaction_read_only')) != 'on':
                        raise RuntimeError('Read-only safeguard unavailable')
                    connection.execute(statement)
                result['probes'][label] = {'status': 'PASS'}
            except SQLAlchemyError as error:
                response = asyncio.run(boundary.exception_handlers[SQLAlchemyError](None, error))
                result['probes'][label] = {'status': 'FAIL', 'exception_class': type(error).__name__,
                    'driver_exception_class': type(error.orig).__name__ if hasattr(error, 'orig') else None,
                    'sqlstate': getattr(getattr(error, 'orig', None), 'sqlstate', None),
                    'application_handler_http_status': response.status_code,
                    'application_handler_body': json.loads(response.body)}
    except SQLAlchemyError as error:
        result['connection_or_metadata_error'] = {'exception_class': type(error).__name__,
            'sqlstate': getattr(getattr(error, 'orig', None), 'sqlstate', None)}
        print(json.dumps(result, indent=2))
        return 1
    finally:
        engine.dispose()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        # Never print a raw configuration/connection exception or its inputs.
        print(json.dumps({'diagnostic_error_class': type(error).__name__}))
        raise SystemExit(1)
