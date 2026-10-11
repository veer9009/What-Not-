from decimal import Decimal

from alembic import command
import pytest
from sqlalchemy import inspect, text

from app.core.config import Settings
from conftest import migration_config


def test_database_configuration_is_optional_and_secret(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    assert hasattr(settings, "database_url"), "Phase 3 database configuration is missing"
    assert settings.database_url is None
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://u:hidden@localhost/test")
    assert "hidden" not in repr(settings)


@pytest.mark.parametrize("url", ["sqlite:///test.db", "postgresql://u:p@localhost/db", "not-a-url"])
def test_configuration_rejects_other_drivers(url):
    with pytest.raises(ValueError):
        Settings(_env_file=None, database_url=url)


def test_unconfigured_engine_has_clear_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from app.db.session import build_engine
    with pytest.raises(ValueError, match="DATABASE_URL"):
        build_engine(Settings(_env_file=None))


def test_environment_url_and_explicit_setting_precedence(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env:hidden@localhost/environment")
    settings = Settings(_env_file=None)
    assert settings.database_url.get_secret_value().endswith("/environment")
    explicit = Settings(_env_file=None, database_url="postgresql+psycopg://test:secret@localhost/explicit")
    assert explicit.database_url.get_secret_value().endswith("/explicit")


def test_relationships_defaults_snapshots_and_timestamps(db, records):
    r = records
    assert r["seller_user"].seller_profile is r["seller"]
    assert r["seller"].products == [r["product"]]
    assert r["buyer"].addresses == [r["address"]]
    assert r["buyer"].orders == [r["order"]]
    assert r["seller"].orders == [r["order"]]
    assert r["order"].items == [r["item"]]
    assert r["item"].product is r["product"]
    assert r["order"].address is r["address"]
    assert r["product"].status == "PENDING" and r["product"].is_active
    assert r["order"].status == "PLACED"
    assert r["buyer"].is_active and not r["seller"].is_verified
    assert isinstance(r["product"].id, int) and r["product"].id > 0
    old = r["product"].updated_at
    assert old.utcoffset() is not None
    r["product"].name = "Renamed later"
    r["product"].price = Decimal("900.00")
    db.flush()
    db.refresh(r["product"])
    assert r["product"].updated_at > old
    db.refresh(r["item"])
    assert r["item"].product_name == "Handmade vase"
    assert r["item"].unit_price == Decimal("250.00")


def test_database_session_rolls_back_on_exception(migrated_engine):
    from app.db.session import session_scope
    with pytest.raises(RuntimeError):
        with session_scope(migrated_engine) as session:
            session.execute(text("INSERT INTO users(name,email,phone,password_hash,role) "
                                 "VALUES ('Rollback','rollback@example.test','rollback','hash','BUYER')"))
            raise RuntimeError("rollback")
    with migrated_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM users WHERE phone='rollback'")) == 0


def test_database_engine_and_session_commit(migrated_engine, monkeypatch):
    from app.db.session import build_engine, session_scope
    url = migrated_engine.url.render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", url)
    engine = build_engine(Settings(_env_file=None))
    try:
        with session_scope(engine) as session:
            session.execute(text("INSERT INTO users(name,email,phone,password_hash,role) "
                                 "VALUES ('Commit','commit@example.test','commit','hash','BUYER')"))
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM users WHERE phone='commit'")) == 1
        with session_scope(engine) as session:
            session.execute(text("DELETE FROM users WHERE phone='commit'"))
    finally:
        engine.dispose()


def test_migration_round_trip_and_metadata_match(fresh_database_url):
    from sqlalchemy import create_engine
    config = migration_config(fresh_database_url)
    command.upgrade(config, "head")
    engine = create_engine(fresh_database_url)
    try:
        assert set(inspect(engine).get_table_names()) == {
            "alembic_version", "users", "seller_profiles", "products", "product_images",
            "addresses", "orders", "order_items",
        }
        command.check(config)
        command.downgrade(config, "base")
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}
        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()


def test_id_money_and_timezone_column_types(migrated_engine):
    inspector = inspect(migrated_engine)
    for table in ("users", "seller_profiles", "products", "product_images", "addresses", "orders", "order_items"):
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        assert str(columns["id"]["type"]) == "BIGINT"
        assert "nextval" in columns["id"]["default"]
        if table != "order_items":
            assert columns["created_at"]["type"].timezone
    for table, name in [("products", "price"), ("orders", "subtotal"), ("orders", "delivery_fee"),
                        ("orders", "total_amount"), ("order_items", "unit_price")]:
        column = next(c for c in inspector.get_columns(table) if c["name"] == name)
        assert (column["type"].precision, column["type"].scale) == (12, 2)
