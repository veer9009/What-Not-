"""Approved Step 37 fixtures. Restore only a NEW verified empty QA database.

No CREATE/DROP DATABASE, migrations, original connections or destructive cleanup.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import os
import secrets
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_chrome_discovery_qa import QA,MANIFEST,IDENTITY,require,Settings,make_url,preflight
import psycopg
from psycopg import sql
from sqlalchemy import create_engine,event,text
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models import User,SellerProfile,Product,Address

TESTS='whatnot_tests_20261115_a7e394c2'
QA_OID=50640
BIN=Path('C:/Program Files/PostgreSQL/17/bin')


def run(binary,args,env):
    result=subprocess.run([str(BIN/binary),*args],env=env,capture_output=True,timeout=120)
    require(result.returncode==0,f'STOP: {binary} failed; private process output suppressed')
    return result.stdout.decode('utf-8',errors='replace')


def main():
    require(not sys.argv[1:],'Provisioner accepts no target overrides')
    require(not MANIFEST.exists(),'STOP: QA manifest already exists; no restore or reseed permitted')
    base=make_url(Settings().database_url.get_secret_value())
    require(base.host in {'localhost','127.0.0.1','::1'} and (base.port or 5432)==5432
            and not base.query and base.database in {'whatnot_app_dev',QA},'Unexpected connection settings')
    def connect(name,readonly=True):
        require(name in {QA,TESTS},'Unapproved connection target')
        return psycopg.connect(host=base.host,port=base.port or 5432,user=base.username,
            password=base.password,dbname=name,connect_timeout=5,
            options='-c default_transaction_read_only='+('on' if readonly else 'off')+' -c statement_timeout=30000')
    def identity(c,name,oid=None):
        row=tuple(c.execute(IDENTITY).fetchone())
        require(row[0]==name and row[2] and (oid is None or row[1]==oid),'Database name/OID/owner mismatch')
        if name==QA:require(row[1] not in {41069,49264,49265,32877},'Protected database OID refused')
        return row[1]
    def tables(c):
        return [row[0] for row in c.execute("""SELECT tablename FROM pg_tables
            WHERE schemaname='public' ORDER BY tablename""")]
    def empty_destination(c):
        identity(c,QA,QA_OID)
        require(c.execute("""SELECT
            (SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace) +
            (SELECT count(*) FROM pg_proc WHERE pronamespace='public'::regnamespace) +
            (SELECT count(*) FROM pg_type WHERE typnamespace='public'::regnamespace) +
            (SELECT count(*) FROM pg_namespace WHERE nspname NOT IN ('public','pg_catalog','information_schema')
                AND nspname NOT LIKE 'pg_toast%' AND nspname NOT LIKE 'pg_temp%') +
            (SELECT count(*) FROM pg_extension WHERE extname<>'plpgsql')""").fetchone()[0]==0,
            'QA target contains unexpected objects; nothing overwritten')
    def empty_business(c,names):
        for name in names:
            if name!='alembic_version':
                require(c.execute(sql.SQL('SELECT count(*) FROM public.{}').format(sql.Identifier(name))).fetchone()[0]==0,
                        'QA/test business or quota data present; stop without cleanup')
    with connect(QA) as target:
        empty_destination(target)
        oid=QA_OID
    folder=Path(tempfile.mkdtemp(prefix='WhatNotChromeQA-'))
    archive=folder/'empty-isolated-0008.dump'
    env={**os.environ,'PGPASSWORD':base.password or '',
         'PGOPTIONS':'-c default_transaction_read_only=on -c statement_timeout=30000'}
    common=['--host',base.host,'--port',str(base.port or 5432),'--username',base.username,'--no-password']
    with connect(TESTS) as source:
        source.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        identity(source,TESTS,49265)
        revision=source.execute('SELECT version_num FROM public.alembic_version').fetchone()[0]
        require(revision=='0008','Isolated schema revision differs')
        source_tables=tables(source)
        # Only the schema is archived. No business/quota/version rows are dumped.
        empty_business(source,[name for name in source_tables if name!='request_quotas'])
        snapshot=source.execute('SELECT pg_export_snapshot()').fetchone()[0]
        run('pg_dump.exe',[*common,'--dbname',TESTS,'--format=custom','--schema-only','--no-acl',
            '--snapshot',snapshot,'--file',str(archive)],env)
    listing=run('pg_restore.exe',['--list',str(archive)],env)
    require('TABLE public alembic_version' in listing and archive.stat().st_size>0
            and 'TABLE DATA ' not in listing and 'SEQUENCE SET ' not in listing,'Archive is not schema-only')
    restore_list=folder/'restore-schema.list'
    # template0 already supplies the empty public namespace. Preserve it; copy
    # its objects without trying to recreate/drop that existing namespace.
    restore_list.write_text('\n'.join(';' + line if ' SCHEMA - public ' in line else line
                                      for line in listing.splitlines())+'\n',encoding='utf-8')
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
    with connect(QA) as target:
        empty_destination(target)
    # Hardcoded destination, no --clean/--create, one transaction, stop on errors.
    restore_env={**env,'PGOPTIONS':'-c lock_timeout=5000 -c statement_timeout=30000'}
    run('pg_restore.exe',[*common,'--dbname',QA,'--no-owner','--no-privileges',
        '--exit-on-error','--single-transaction','--use-list',str(restore_list),str(archive)],restore_env)
    with connect(QA) as target:
        identity(target,QA,oid)
        require(tables(target)==source_tables,'Restored table set differs')
        require(target.execute('SELECT count(*) FROM public.alembic_version').fetchone()[0]==0,'Unexpected copied version rows')
        empty_business(target,tables(target))
    credentials={'buyer_email':'chrome-buyer@example.com','buyer_password':secrets.token_urlsafe(24),
                 'seller_email':'chrome-seller@example.com','seller_password':secrets.token_urlsafe(24)}
    # Encrypt to this Windows user's DPAPI context; no plaintext secret file/args.
    protect="$qaText=[Console]::In.ReadToEnd(); $qaSecure=ConvertTo-SecureString -String $qaText -AsPlainText -Force; ConvertFrom-SecureString -SecureString $qaSecure"
    encrypted=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',protect],
        input=json.dumps(credentials),text=True,capture_output=True,timeout=30)
    require(encrypted.returncode==0 and bool(encrypted.stdout.strip()),'QA password protection failed; stop before seeding')
    private_file=folder/'qa-credentials.dpapi'
    private_file.write_text(encrypted.stdout.strip(),encoding='utf-8')
    url=base.set(database=QA)
    engine=create_engine(url,hide_parameters=True)
    def guard(connection,cursor,statement,parameters,context,executemany):
        raw=connection.connection.driver_connection
        require(raw.info.dbname==QA,'Unapproved fixture write target')
        with raw.cursor() as check:
            check.execute(IDENTITY)
            require(tuple(check.fetchone())==(QA,oid,True),'Fixture database identity changed')
    event.listen(engine,'before_cursor_execute',guard)
    try:
        with Session(engine) as session,session.begin():
            for name in source_tables:
                if name!='alembic_version':
                    require(session.scalar(text('SELECT count(*) FROM public."'+name.replace('"','""')+'"'))==0,'QA changed before fixture insertion')
            require(session.scalar(text('SELECT count(*) FROM public.alembic_version'))==0,'Unexpected revision metadata')
            # Initialize metadata for the already-copied, verified 0008 schema.
            # No Alembic command/migration/stamp runs and no source rows are copied.
            session.execute(text('INSERT INTO public.alembic_version(version_num) VALUES (:revision)'),{'revision':revision})
            buyer=User(name='Chrome QA Buyer',email=credentials['buyer_email'],phone='qa-only-buyer',
                role='BUYER',is_active=True,password_hash=hash_password(credentials['buyer_password']))
            seller=User(name='Chrome QA Seller',email=credentials['seller_email'],phone='qa-only-seller',
                role='SELLER',is_active=True,password_hash=hash_password(credentials['seller_password']))
            shop=SellerProfile(user=seller,shop_name='Chrome QA Maker',phone='qa-only-seller',latitude=0,longitude=0,
                dispatch_location_confirmed_at=datetime.now(timezone.utc),is_verified=False)
            products=[Product(seller=shop,name=name,description='Synthetic Chrome acceptance fixture',
                category='Crafts',price=price,stock_quantity=stock,status=status,is_active=True,delivery_radius_km=radius)
                for name,price,stock,status,radius in [
                    ('QA Nearby Vase','250.00',5,'APPROVED',2),
                    ('QA Nearby Basket','125.50',4,'APPROVED',1),
                    ('QA Pending Sample','99.00',3,'PENDING',3)]]
            address=Address(user=buyer,label='QA Home',address_line1='Synthetic QA address only',
                city='QA',state='QA',pincode='999999',latitude=0,longitude=0,is_default=True)
            session.add_all([buyer,seller,shop,address,*products])
            session.flush()
    finally:
        engine.dispose()
    manifest={'database':QA,'oid':oid,'revision':'0008','fixtures_version':'chrome-discovery-v1',
        'approved_by_owner':True,'private_credentials_path':str(private_file),
        'schema_archive':str(archive),'schema_archive_sha256':checksum,'schema_only':True,
        'source_database':TESTS,'source_oid':49265,'revision_metadata_initialized_from_verified_schema':True}
    # Preflight independently verifies committed fixtures before manifest publication.
    result=preflight(url,oid)
    MANIFEST.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({**result,'schema_archive':str(archive),'schema_archive_sha256':checksum,
        'credentials_storage':'Windows-current-user DPAPI; no plaintext emitted',
        'private_credentials_path':str(private_file),'migrations_run':False},indent=2),flush=True)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
            'message':str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}),flush=True)
        raise SystemExit(1)
