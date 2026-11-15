from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings


def build_engine(settings: Settings) -> Engine:
    """Explicit factory; does not create tables or connect until first use."""
    if settings.database_url is None:
        raise ValueError("DATABASE_URL is required for database operations")
    return create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True, echo=False,
                         hide_parameters=True, pool_size=settings.database_pool_size,
                         max_overflow=settings.database_max_overflow,
                         pool_timeout=settings.database_pool_timeout_seconds,
                         pool_recycle=1800,
                         connect_args={'connect_timeout': settings.database_connect_timeout_seconds})


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Commit on success, roll back on failure, always close the session."""
    with Session(engine, expire_on_commit=False) as session:
        with session.begin():
            yield session
