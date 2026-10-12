"""Real request units of work, with rollback-isolated generated cluster storage."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import Settings
from app.main import create_app
from app.models import User
from test_authentication import SECRET, register, login


def test_auth_request_commits_before_response_and_rolls_back_commit_failure(migrated_engine):
    with migrated_engine.connect() as connection:
        outer = connection.begin()
        sessions = []
        fail_commit = False

        def request_session():
            with Session(bind=connection, join_transaction_mode='create_savepoint', expire_on_commit=False) as session:
                sessions.append(session)
                if fail_commit:
                    def fail(*args):
                        if not session.in_nested_transaction():
                            raise OperationalError('sensitive SQL statement', {}, Exception('database password-secret'))
                    event.listen(session, 'before_commit', fail)
                yield session

        app = create_app(Settings(_env_file=None, environment='test', jwt_secret_key=SECRET))
        app.dependency_overrides[get_session] = request_session
        try:
            with TestClient(app) as client:
                registered = register(client)
                assert registered.status_code == 201
                # The HTTP response means the transaction has already completed.
                assert not sessions[-1].in_transaction()
                with Session(bind=connection) as verify:
                    assert verify.scalar(select(User).where(User.id == registered.json()['id'])) is not None
                token = login(client).json()['access_token']
                assert client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 200
                assert not sessions[-1].in_transaction()
                fail_commit = True
                failed = register(client, email='rollback@example.com', phone='rollback')
                assert failed.status_code == 503
                assert 'sensitive' not in failed.text and 'password-secret' not in failed.text
                assert not sessions[-1].in_transaction()
                with Session(bind=connection) as verify:
                    assert verify.scalar(select(User).where(User.email == 'rollback@example.com')) is None
        finally:
            outer.rollback()
