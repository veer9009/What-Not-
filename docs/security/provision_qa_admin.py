"""Prepared QA-only admin provisioner. Default is read-only; --execute needs owner approval."""
import argparse
from getpass import getpass,GetPassWarning
import json
import os
import sys
import warnings
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from sqlalchemy import create_engine,event,text
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.security import hash_password
from app.schemas.auth import UserRegistration
from app.services.inputs import UserCreate
from app.services.users import UserService
from qa_admin_policy import QA_MARKER,configured_admin_email,validate_identity,validate_roster,require
from run_chrome_discovery_qa import target,QA

IDENTITY=text('''SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),
    (SELECT datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user) FROM pg_database WHERE datname=current_database()),
    current_user,host(inet_server_addr()),inet_server_port(),current_setting('server_version_num')::int,pg_is_in_recovery()''')
TABLES=('users','seller_profiles','products','addresses','orders')


def hidden_password(prompt):
    # Fail closed instead of getpass's fallback to an echoed input prompt.
    with warnings.catch_warnings():
        warnings.simplefilter('error',GetPassWarning)
        return getpass(prompt)


def inspect_state(session,expected_user,admin_email,require_absent=False):
    validate_identity(tuple(session.execute(IDENTITY).one()),expected_user)
    require(session.scalar(text('SELECT version_num FROM public.alembic_version'))=='0009','QA schema must be 0009')
    rows=session.execute(text('SELECT email,role,is_active FROM public.users ORDER BY email')).all()
    admins=sum(row[1]=='ADMIN' for row in rows)
    if require_absent:require(admins==0,'QA admin already exists; duplicate execution refused')
    require(admins in (0,1),'Unexpected administrator count')
    validate_roster(rows,admin_email if admins else None)
    counts={table:session.scalar(text('SELECT count(*) FROM public.'+table)) for table in TABLES}
    require(counts==dict(users=2+admins,seller_profiles=1,products=3,addresses=1,orders=0),'Unexpected QA fixture counts')
    return {'admin_count':admins,'counts':counts}


def fingerprints(session):
    # Existing credentials/location remain inside PostgreSQL; return only opaque
    # SHA-256 preservation digests in memory, never raw rows or credential fields.
    result={}
    for table in TABLES:
        where=" WHERE role <> 'ADMIN'" if table=='users' else ''
        result[table]=session.scalar(text("SELECT encode(sha256(convert_to(COALESCE(string_agg(row_to_json(t)::text,'' ORDER BY id),''),'UTF8')),'hex') FROM public."+table+' t'+where))
    return result


def run_transaction(engine,details,expected_user,admin_email,session_factory=Session):
    require(str(details.email).lower()==admin_email,'Prompt email must match explicit QA admin admission')
    with session_factory(engine) as session,session.begin():
        inspect_state(session,expected_user,admin_email,require_absent=True)
        # Serialize roster checks/insertion and preserve business rows. No
        # unrelated sessions are terminated; bounded lock failure rolls back.
        session.execute(text('LOCK TABLE public.users,public.seller_profiles,public.products,public.addresses,public.orders IN SHARE ROW EXCLUSIVE MODE'))
        inspect_state(session,expected_user,admin_email,require_absent=True)
        before=fingerprints(session)
        created=UserService(session).create(UserCreate(name=details.name,email=details.email,phone=details.phone,
            password_hash=hash_password(details.password.get_secret_value()),role='ADMIN',is_active=True))
        session.flush()
        require(created.role=='ADMIN' and created.is_active is True,'Created account is not active ADMIN')
        state=inspect_state(session,expected_user,admin_email)
        require(state['admin_count']==1,'Administrator count verification failed')
        require(fingerprints(session)==before,'Existing QA records changed; rolling back')
    return state  # only after outer commit completes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Use only after separate explicit owner approval')
    args=parser.parse_args()
    require(os.environ.get('WHATNOT_QA_ENVIRONMENT')==QA_MARKER and Settings().environment=='development',
            'Explicit local QA marker and development environment required')
    admin_email=configured_admin_email()
    require(admin_email is not None,'Set explicit QA admin email locally before verification')
    url,oid=target()
    require(oid==50640 and url.drivername=='postgresql+psycopg','Unapproved QA target')
    url=url.set(host='127.0.0.1')
    options='-c statement_timeout=15000 -c lock_timeout=5000'
    # First connection is read-only even for --execute. No user query can precede identity.
    check_engine=create_engine(url,hide_parameters=True,connect_args={'options':options+' -c default_transaction_read_only=on'})
    try:
        with Session(check_engine) as s,s.begin():
            require(s.scalar(text('SHOW transaction_read_only'))=='on','Read-only preflight unavailable')
            state=inspect_state(s,url.username,admin_email,require_absent=args.execute)
    finally:check_engine.dispose()
    if not args.execute:
        print(json.dumps({'status':'READ_ONLY_VERIFIED','database':QA,'oid':oid,'revision':'0009',**state}))
        return
    require(sys.stdin.isatty(),'Interactive local terminal required; no piped credentials')
    require(input('Owner approval required. Type CREATE QA ADMIN OID 50640: ')=='CREATE QA ADMIN OID 50640','Operator confirmation mismatch')
    name=input('Administrator name: ');email=input('Administrator email (must match QA admission): ');phone=input('Administrator phone: ')
    password=hidden_password('New administrator password (8-128 characters): ')
    require(hidden_password('Repeat password: ')==password,'Passwords do not match')
    details=UserRegistration(name=name,email=email,phone=phone,password=password)
    engine=create_engine(url,hide_parameters=True,connect_args={'options':options})
    def guard(connection,cursor,statement,parameters,context,executemany):
        raw=connection.connection.driver_connection
        require(raw.info.dbname==QA,'Wrong physical QA target')
        import psycopg
        if raw.info.transaction_status==psycopg.pq.TransactionStatus.INERROR:
            require(statement.strip().upper().startswith('ROLLBACK TO SAVEPOINT '),'Only savepoint recovery allowed')
            return
        with raw.cursor() as check:
            check.execute(str(IDENTITY))
            validate_identity(tuple(check.fetchone()),url.username)
    event.listen(engine,'before_cursor_execute',guard)
    try:state=run_transaction(engine,details,url.username,admin_email)
    finally:engine.dispose()
    print(json.dumps({'status':'CREATED','database':QA,'oid':oid,'revision':'0009','admin_active':True,**state}))


if __name__=='__main__':
    try:main()
    except Exception as error:
        # Never print exception contents: DB errors may carry sensitive parameters.
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,'message':'No automatic retry. Inspect identity/policy and transaction outcome privately; credentials suppressed.'}))
        raise SystemExit(1)
