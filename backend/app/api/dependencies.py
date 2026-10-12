"""One session per request; write transaction scopes remain explicit."""
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.db.session import build_engine


def get_session(request: Request) -> Iterator[Session]:
    application = request.app
    with application.state.database_engine_lock:
        if application.state.database_engine is None:
            application.state.database_engine = build_engine(application.state.settings)
        engine = application.state.database_engine
    with Session(engine, expire_on_commit=False) as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                session.rollback()
