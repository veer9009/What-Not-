"""Approved one-time 0008->0009 additive upgrade, pinned to Chrome QA OID 50640."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from sqlalchemy import create_engine, event, text
from alembic.config import Config
from alembic import command
from run_chrome_discovery_qa import target, preflight, require, IDENTITY, QA, ROOT


def main():
    url, oid = target()
    require(oid == 50640, 'Unapproved QA OID')
    preflight(url, oid)
    engine = create_engine(url, hide_parameters=True)
    def guard(connection, cursor, statement, parameters, context, executemany):
        raw = connection.connection.driver_connection
        require(raw.info.dbname == QA, 'Wrong migration target')
        with raw.cursor() as check:
            check.execute(IDENTITY)
            require(tuple(check.fetchone()) == (QA, oid, True), 'Migration identity changed')
    event.listen(engine, 'before_cursor_execute', guard)
    def snapshot(connection):
        return {t: connection.execute(text('SELECT row_to_json(t)::text FROM public.'+t+' t ORDER BY id')).scalars().all()
                for t in ('users','seller_profiles','products','addresses','orders')}
    try:
        with engine.connect() as c:
            require(c.scalar(text('SELECT version_num FROM alembic_version')) == '0008', 'Expected 0008; never retry blindly')
            before = snapshot(c)
            require(not c.scalar(text("SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='seller_profiles' AND column_name LIKE 'public_discovery_%'")), 'Unexpected public columns')
        folder = Path(tempfile.mkdtemp(prefix='WhatNotPublicRadiusQA-'))
        archive = folder/'chrome-qa-before-0009.dump'
        pg = Path('C:/Program Files/PostgreSQL/17/bin')
        env = {**os.environ, 'PGPASSWORD':url.password, 'PGOPTIONS':'-c default_transaction_read_only=on'}
        # pg_dump's own REPEATABLE READ snapshot is consistent. No restore or overwrite.
        args = [str(pg/'pg_dump.exe'),'-h',url.host,'-p',str(url.port or 5432),'-U',url.username,
                '-d',QA,'-Fc','--no-owner','--no-privileges','-f',str(archive)]
        require(subprocess.run(args,env=env,capture_output=True).returncode == 0,'QA backup failed; stop')
        listing = subprocess.run([str(pg/'pg_restore.exe'),'--list',str(archive)],capture_output=True)
        require(listing.returncode == 0 and b'TABLE DATA' in listing.stdout,'QA backup unreadable; stop')
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        with engine.begin() as c:
            require(tuple(c.execute(text(IDENTITY)).one()) == (QA,oid,True),'Wrong pre-migration identity')
            require(c.scalar(text('SELECT version_num FROM alembic_version')) == '0008','Revision changed')
            require(snapshot(c) == before,'QA business rows changed since preflight; stop')
            require(hashlib.sha256(archive.read_bytes()).hexdigest() == checksum,'Backup changed')
            config = Config(str(ROOT/'backend/alembic.ini'))
            config.attributes['connection'] = c
            config.attributes['database_url'] = url
            command.upgrade(config,'0009')
            require(c.scalar(text('SELECT version_num FROM alembic_version')) == '0009','Upgrade not complete')
            require(c.scalar(text('SELECT count(*) FROM seller_profiles WHERE public_discovery_latitude IS NOT NULL OR public_discovery_longitude IS NOT NULL OR public_discovery_confirmed_at IS NOT NULL OR public_discovery_consent_version IS NOT NULL')) == 0,'Unexpected backfill')
            after = snapshot(c)
            for row in after['seller_profiles']:
                value=json.loads(row)
                for key in list(value):
                    if key.startswith('public_discovery_'):del value[key]
                require(value in [json.loads(r) for r in before['seller_profiles']], 'Private seller data changed')
            require(all(after[t] == before[t] for t in before if t != 'seller_profiles'),'Business data changed')
        result={'database':QA,'oid':oid,'before_revision':'0008','after_revision':'0009','backup':str(archive),
                'sha256':checksum,'backup_listing_exit':listing.returncode,'private_business_fields_unchanged':True,
                'public_fields_initially_null':True,'migration_command':'alembic.command.upgrade(verified_QA_connection, 0009)',
                'exit_code':0,'counts':{t:len(v) for t,v in before.items()}}
        (Path(__file__).parent/'evidence/public-radius-qa-migration.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:
        engine.dispose()


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
                          'message':str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}))
        raise SystemExit(1)
