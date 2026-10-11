from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.db.base import Base
import app.models  # Register every mapping before exposing metadata.


config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)
target_metadata = Base.metadata


def database_url():
    explicit = config.attributes.get("database_url")
    if explicit is not None:
        url = make_url(explicit)
        if url.drivername != "postgresql+psycopg":
            raise ValueError("Migrations require PostgreSQL with psycopg 3")
        return url
    settings = Settings()
    if settings.database_url is None:
        raise ValueError("Set DATABASE_URL before running Alembic")
    return make_url(settings.database_url.get_secret_value())


def run_migrations_offline():
    context.configure(url=database_url(), target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    engine = create_engine(database_url(), poolclass=pool.NullPool, echo=False)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
