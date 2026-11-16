import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.errors import UndefinedColumn
from sqlalchemy.exc import ProgrammingError

from app.api.errors import install_error_handlers


def test_storage_failure_logs_sqlstate_without_sql_or_credentials(caplog):
    app = FastAPI()
    install_error_handlers(app)

    @app.get('/failure')
    def failure():
        raise ProgrammingError('private SQL', {'password': 'private parameter'},
                               UndefinedColumn('private database detail'))

    with caplog.at_level(logging.ERROR, logger='whatnot.api'), TestClient(app) as client:
        response = client.get('/failure')

    assert response.status_code == 503
    assert response.json() == {'detail': 'Storage operation is unavailable'}
    record = next(r for r in caplog.records if r.message.startswith('storage_operation_failed'))
    assert record.error_code == 'ProgrammingError'
    assert record.sqlstate == '42703'
    assert 'sqlstate=42703' in record.getMessage()
    assert record.exc_info is None
    assert 'private' not in repr(record.__dict__)
