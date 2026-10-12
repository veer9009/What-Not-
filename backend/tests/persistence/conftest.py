"""Real PostgreSQL tests: never consume DATABASE_URL or a user's running server."""

import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
from uuid import uuid4

from alembic import command
from alembic.config import Config
import psycopg
from psycopg import sql
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session


BACKEND = Path(__file__).resolve().parents[2]


def run_pg(binary, *args, allowed_codes=(0,)):
    executable = shutil.which(binary)
    if executable is None:
        pytest.fail(f"PostgreSQL initdb and pg_ctl must be on PATH: missing {binary}")
    # pg_ctl's server child can inherit pipe handles on Windows. File output
    # avoids waiting for a pipe EOF that only arrives when the server stops.
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
        result = subprocess.run(
            [executable, *map(str, args)], stdout=output, stderr=subprocess.STDOUT,
            timeout=60, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode not in allowed_codes:
            output.seek(0)
            pytest.fail(f"{binary} failed: {output.read()}")
        return result.returncode


@pytest.fixture(scope="session")
def isolated_cluster():
    # This fixture deliberately ignores every application/env database setting.
    # Do not use TemporaryDirectory's finalizer: failed shutdown must retain files.
    root = Path(tempfile.mkdtemp(prefix="whatnot-phase3-postgres-")).resolve()
    data = root / "data"
    password = secrets.token_urlsafe(32)
    password_file = root / "password"
    password_file.write_text(password, encoding="utf-8")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    startup_attempted = False
    try:
        run_pg("initdb", "-D", data, "-U", "whatnot_test", "--auth=scram-sha-256",
               "--pwfile", password_file, "--encoding=UTF8", "--no-locale")
        password_file.unlink()
        startup_attempted = True
        try:
            run_pg("pg_ctl", "-D", data, "-l", root / "server.log", "-w", "-t", "30",
                   "-o", f"-h 127.0.0.1 -p {port}", "start")
        except BaseException:
            log = root / "server.log"
            if log.exists():
                print(log.read_text(encoding="utf-8", errors="replace"))
            raise
        connection_args = dict(host="127.0.0.1", port=port, user="whatnot_test",
                               password=password, dbname="postgres")
        with psycopg.connect(**connection_args) as connection:
            actual = connection.execute("SHOW data_directory").fetchone()[0]
            assert Path(actual).resolve() == data.resolve(), "Unexpected PostgreSQL cluster"
        yield connection_args
    finally:
        assert data.parent == root and root.name.startswith("whatnot-phase3-postgres-")
        if startup_attempted:
            # pg_ctl can fail after spawning postgres. Check this exact owned
            # data directory even when startup never reported success.
            status = run_pg("pg_ctl", "-D", data, "status", allowed_codes=(0, 3))
            if status == 0:
                run_pg("pg_ctl", "-D", data, "-w", "-t", "30", "-m", "fast", "stop")
            if run_pg("pg_ctl", "-D", data, "status", allowed_codes=(0, 3)) != 3:
                pytest.fail(f"Temporary cluster shutdown unconfirmed; files retained at {root}")
        # A failed status/stop raises before deletion. Only this generated path is owned.
        shutil.rmtree(root)


@pytest.fixture
def fresh_database_url(isolated_cluster):
    name = "whatnot_test_" + uuid4().hex
    assert name not in {"whatnot_db", "upsc_compass"}
    with psycopg.connect(**isolated_cluster, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    return URL.create("postgresql+psycopg", username=isolated_cluster["user"],
                      password=isolated_cluster["password"], host="127.0.0.1",
                      port=isolated_cluster["port"], database=name)


def migration_config(url):
    config = Config(str(BACKEND / "alembic.ini"))
    # Explicit test URL wins over environment/.env; no credentials in ini/logs.
    config.attributes["database_url"] = url
    return config


@pytest.fixture(scope="session")
def migrated_engine(isolated_cluster):
    name = "whatnot_test_suite"
    with psycopg.connect(**isolated_cluster, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = URL.create("postgresql+psycopg", username=isolated_cluster["user"],
                     password=isolated_cluster["password"], host="127.0.0.1",
                     port=isolated_cluster["port"], database=name)
    command.upgrade(migration_config(url), "head")
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(migrated_engine):
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            with session.begin():
                yield session
        transaction.rollback()


@pytest.fixture
def records(db):
    from app.models import Address, Order, OrderItem, Product, SellerProfile, User

    buyer = User(name="Buyer", email="buyer@example.test", phone="1000000001",
                 password_hash="test-only-already-hashed", role="BUYER")
    seller_user = User(name="Maker", email="maker@example.test", phone="1000000002",
                       password_hash="test-only-already-hashed", role="SELLER")
    seller = SellerProfile(user=seller_user, shop_name="Local maker", phone="1000000002",
                           latitude="19.076000", longitude="72.877700")
    product = Product(seller=seller, name="Handmade vase", description="A vase",
                      price="250.00", stock_quantity=5, category="Crafts", delivery_radius_km=2)
    address = Address(user=buyer, label="Home", address_line1="1 Maker Lane", city="Mumbai",
                      state="Maharashtra", pincode="400001", latitude="19.070000",
                      longitude="72.870000")
    order = Order(buyer=buyer, seller=seller, address=address, subtotal="500.00",
                  delivery_fee="49.00", total_amount="549.00")
    item = OrderItem(order=order, product=product, seller_id=seller.id,
                     product_name="Handmade vase", quantity=2, unit_price="250.00")
    db.add_all([buyer, seller_user, seller, product, address, order])
    db.flush()
    item.seller_id = seller.id
    db.add(item)
    db.flush()
    return dict(buyer=buyer, seller_user=seller_user, seller=seller, product=product,
                address=address, order=order, item=item)
