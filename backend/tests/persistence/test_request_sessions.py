from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import Settings
from app.main import create_app
from app.models import User
from app.services.inputs import UserCreate
from app.services.users import UserService
from test_services_marketplace import HASH


def test_request_sessions_commit_rollback_cleanup_and_disposal(migrated_engine):
    app = create_app(Settings(_env_file=None, database_url=migrated_engine.url.render_as_string(hide_password=False)))
    sessions = []

    @app.post('/test-only/{mode}')
    def probe(mode: str, session: Session = Depends(get_session)):
        sessions.append(session)
        with session.begin():
            UserService(session).create(UserCreate(name='Probe', email=f'{mode}@example.com', phone=f'probe-{mode}', password_hash=HASH, role='BUYER'))
            if mode == 'failed':
                raise HTTPException(409, 'Deliberate transaction failure')
        return {'ok': True}

    @app.post('/test-only-uncommitted')
    def uncommitted(session: Session = Depends(get_session)):
        sessions.append(session)
        session.add(User(name='Uncommitted', email='uncommitted@example.com', phone='probe-uncommitted', password_hash=HASH, role='BUYER'))
        session.flush()
        return {'ok': True}

    with TestClient(app) as client:
        assert app.state.database_engine is None
        assert client.post('/test-only/committed').status_code == 200
        engine = app.state.database_engine
        assert client.post('/test-only/failed').status_code == 409
        assert client.post('/test-only-uncommitted').status_code == 200
        assert len({id(session) for session in sessions}) == 3
        assert all(not session.in_transaction() for session in sessions)
        assert engine.pool.checkedout() == 0
        with Session(migrated_engine) as verification:
            phones = list(verification.scalars(select(User.phone).where(User.phone.like('probe-%'))))
            assert phones == ['probe-committed']
        with Session(migrated_engine) as cleanup, cleanup.begin():
            cleanup.query(User).filter(User.phone == 'probe-committed').delete()
    assert app.state.database_engine is None
    assert engine.pool.checkedout() == 0
