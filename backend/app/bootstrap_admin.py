"""One-time interactive operator bootstrap; never run automatically at startup."""
import argparse
from getpass import getpass
import re

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import build_engine
from app.schemas.auth import UserRegistration
from app.services.inputs import UserCreate
from app.services.users import UserService

IDENTITY = text('''SELECT current_database(), current_user, inet_server_addr()::text,
    inet_server_port(), (SELECT oid FROM pg_database WHERE datname=current_database())''')


def validate_target(settings, expected_database):
    if (settings.environment != 'production' or
        not re.fullmatch(r'whatnot_pilot(?:_[a-z0-9]+)*', expected_database) or
        settings.database_url is None or
        make_url(settings.database_url.get_secret_value()).database != expected_database or
        len(settings.beta_allowed_emails) != 10):
        raise RuntimeError('Bootstrap requires an explicit pilot target, production settings and ten admitted identities')


def validate_identity(actual, database, address, port, oid):
    if tuple(actual) != (database, 'whatnot_runtime', address, port, oid):
        raise RuntimeError('Bootstrap database identity or runtime role mismatch')


def create_initial_admin(session, settings, database, address, port, oid, details):
    validate_target(settings, database)
    if details.email not in settings.beta_allowed_emails:
        raise RuntimeError('Administrator must be one of the ten admitted identities')
    validate_identity(session.execute(IDENTITY).one(), database, address, port, oid)
    from app.db.schema import EXPECTED_REVISION
    if session.scalar(text('SELECT version_num FROM alembic_version')) != EXPECTED_REVISION:
        raise RuntimeError('Bootstrap requires the reviewed application schema')
    # Block concurrent registration/bootstrap while checking the empty table.
    # Identity is verified before this lock and again before the sole insert.
    session.execute(text('LOCK TABLE users IN EXCLUSIVE MODE'))
    if session.scalar(text('SELECT count(*) FROM users')) != 0:
        raise RuntimeError('Bootstrap refuses a database with existing users')
    validate_identity(session.execute(IDENTITY).one(), database, address, port, oid)
    return UserService(session).create(UserCreate(name=details.name, email=details.email,
        phone=details.phone, role='ADMIN',
        password_hash=hash_password(details.password.get_secret_value())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--server-address', required=True)
    parser.add_argument('--port', type=int, default=5432)
    parser.add_argument('--oid', type=int, required=True)
    args = parser.parse_args()
    settings = Settings()
    # Reject development/original targets before constructing an engine.
    validate_target(settings, args.database)
    confirmation = f'BOOTSTRAP {args.database} OID {args.oid}'
    if input('API, workers and restarts must be stopped. Type ' + confirmation + ': ') != confirmation:
        raise RuntimeError('Bootstrap not confirmed')
    name = input('Operator name: ')
    email = input('Selected operator email: ')
    phone = input('Operator phone: ')
    password = getpass('New unique password (8-128 characters): ')
    if getpass('Repeat password: ') != password:
        raise RuntimeError('Passwords do not match')
    details = UserRegistration(name=name, email=email, phone=phone, password=password)
    engine = build_engine(settings)
    try:
        with Session(engine) as session, session.begin():
            validate_identity(session.execute(IDENTITY).one(), args.database,
                              args.server_address, args.port, args.oid)
            # Bound lock/statement waits; failure rolls back and prints no inputs.
            session.execute(text("SET LOCAL lock_timeout = '5s'"))
            session.execute(text("SET LOCAL statement_timeout = '30s'"))
            create_initial_admin(session, settings, args.database, args.server_address,
                                 args.port, args.oid, details)
    finally:
        engine.dispose()
    print('Initial administrator created. No other users changed. Verify privately before admitting participants.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Configuration/DB/validation exceptions may otherwise echo sensitive input.
        raise SystemExit('STOP: bootstrap failed (' + type(error).__name__ + '); no automatic retry') from None
