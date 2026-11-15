"""Approved 0008->0009 rehearsal. Original is always PostgreSQL-enforced read-only.

--prepare creates a new protected snapshot archive and exact administrator SQL.
--resume requires administrator-reported OIDs; restores only those new databases.
No server startup, application restart, credential/role changes, or DROP cleanup.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from app.core.config import Settings

SOURCE = 'whatnot_app_dev'
SOURCE_OID = 41069
PROTECTED_OIDS = {41069, 50640, 49264, 49265, 32877}
MIGRATION = ROOT / 'backend/alembic/versions/0009_public_discovery.py'
MIGRATION_SHA256 = '25f693303c54011f36ca282c017e03fccd097fe662719d7d6ae5c2f86261856d'
BIN = Path(r'C:\Program Files\PostgreSQL\17\bin')
COUNTS = dict(users=6, seller_profiles=2, products=3, addresses=1, orders=3)
PUBLIC_FIELDS = ('public_discovery_latitude', 'public_discovery_longitude',
                 'public_discovery_confirmed_at', 'public_discovery_consent_version')
IDENTITY = """SELECT current_database(),oid::bigint,host(inet_server_addr()),
    inet_server_port(),current_setting('server_version_num')::int,pg_is_in_recovery(),
    datdba=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user)
    FROM pg_catalog.pg_database WHERE datname=current_database()"""
EVIDENCE = ROOT / 'docs/security/evidence/0009-rehearsal.json'
STAGE = 'configuration'


def require(condition):
    if not condition:
        raise RuntimeError('Rehearsal safeguard failed; no automatic retry')


def target_names(run):
    require(re.fullmatch(r'[a-f0-9]{8}', run) is not None)
    return tuple(f'whatnot_0009_{kind}_20261115_{run}' for kind in ('rehearsal', 'rollback'))


def validate_target(actual, name, oid, run):
    require(name in target_names(run) and type(oid) is int and oid > 0 and oid not in PROTECTED_OIDS)
    require(len(actual) == 7 and tuple(actual[:4]) == (name, oid, '127.0.0.1', 5432))
    require(170000 <= actual[4] < 180000 and actual[5] is False and actual[6] is True)


def validate_manifest(manifest):
    names = target_names(manifest['run'])
    require((manifest['rehearsal'], manifest['rollback']) == names)
    require(manifest['source'] == SOURCE and manifest['source_oid'] == SOURCE_OID)
    require(manifest['migration_sha256'] == MIGRATION_SHA256)


def compare_preserved(before, after, allow_revision_change=False):
    require(set(before) == set(after))
    require(all(value == after[table] for table, value in before.items()
                if not (allow_revision_change and table == 'alembic_version')))


def checksum(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def migration_check():
    require(checksum(MIGRATION) == MIGRATION_SHA256)


def configuration():
    settings = Settings()
    require(settings.environment == 'development' and settings.database_url is not None)
    url = make_url(settings.database_url.get_secret_value())
    require(url.database == SOURCE and url.host in {'localhost','127.0.0.1','::1'}
            and (url.port or 5432) == 5432 and not url.query and bool(url.username))
    return url


def connect(url, name, readonly=True):
    require(name == SOURCE or re.fullmatch(r'whatnot_0009_(?:rehearsal|rollback)_20261115_[a-f0-9]{8}', name))
    require(name != SOURCE or readonly)
    return psycopg.connect(host='127.0.0.1', port=5432, dbname=name, user=url.username,
        password=url.password, connect_timeout=5, application_name='whatnot_0009_rehearsal',
        options='-c default_transaction_read_only=' + ('on' if readonly else 'off')
                + ' -c statement_timeout=15000 -c lock_timeout=5000 -c timezone=UTC')


def source_check(c):
    actual = c.execute(IDENTITY).fetchone()
    require(tuple(actual[:4]) == (SOURCE,SOURCE_OID,'127.0.0.1',5432)
            and 170000 <= actual[4] < 180000 and actual[5] is False and actual[6] is True)
    require(c.execute('SHOW transaction_read_only').fetchone()[0] == 'on')
    require(c.execute('SELECT version_num FROM public.alembic_version').fetchall() == [('0008',)])
    require({t:c.execute('SELECT count(*) FROM public.'+t).fetchone()[0] for t in COUNTS} == COUNTS)
    require(c.execute("SELECT count(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname NOT IN ('public','information_schema')").fetchone()[0] == 0)
    require(c.execute("SELECT count(*) FROM pg_event_trigger WHERE evtenabled<>'D'").fetchone()[0] == 0)


def snapshot(c, remove_public_fields=False):
    tables = [r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
    result = {}
    for table in tables:
        expression = sql.SQL('to_jsonb(t)')
        if table == 'seller_profiles' and remove_public_fields:
            expression = sql.SQL("to_jsonb(t)-'public_discovery_latitude'-'public_discovery_longitude'-'public_discovery_confirmed_at'-'public_discovery_consent_version'")
        query = sql.SQL("""SELECT count(*),encode(sha256(convert_to(COALESCE(
            string_agg(value,E'\\n' ORDER BY value COLLATE "C"),''),'UTF8')),'hex')
            FROM (SELECT ({expression})::text AS value FROM public.{table} t) snapshot""").format(
                expression=expression, table=sql.Identifier(table))
        count, digest = c.execute(query).fetchone()
        result[table] = dict(count=count,digest=digest)
    return result


def schema_snapshot(c):
    return dict(
        columns=[list(r) for r in c.execute("""SELECT table_name,column_name,data_type,
            character_maximum_length,numeric_precision,numeric_scale,is_nullable,column_default
            FROM information_schema.columns WHERE table_schema='public'
            ORDER BY table_name,ordinal_position""")],
        constraints=[list(r) for r in c.execute("""SELECT t.relname,k.conname,pg_get_constraintdef(k.oid),k.convalidated
            FROM pg_constraint k JOIN pg_class t ON t.oid=k.conrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public'
            ORDER BY t.relname,k.conname""")],
        constraint_metadata=[list(r) for r in c.execute("""SELECT t.relname,k.conname,
            k.contype,k.convalidated,k.condeferrable,k.condeferred,k.connoinherit,k.conislocal,k.coninhcount,
            ARRAY(SELECT a.attname || ':' || format_type(a.atttypid,a.atttypmod)
                || ':' || a.attcollation::text || ':' || a.attnotnull::text
                FROM unnest(k.conkey) WITH ORDINALITY AS keys(attnum,position)
                JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=keys.attnum ORDER BY keys.position)
            FROM pg_constraint k JOIN pg_class t ON t.oid=k.conrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname='public'
            ORDER BY t.relname,k.conname""")],
        indexes=[list(r) for r in c.execute("""SELECT tablename,indexname,indexdef FROM pg_indexes
            WHERE schemaname='public' ORDER BY tablename,indexname""")])


EQUIVALENT_CAST_CHECKS = {
    ('creative_engagements','ck_creative_engagements_status'),
    ('creative_listings','ck_creative_listings_category'),
    ('creative_listings','ck_creative_listings_pricing'),
    ('creative_listings','ck_creative_listings_status'),
    ('email_outbox','ck_email_outbox_state'),('orders','ck_orders_status'),
    ('products','ck_products_status'),('property_listings','ck_property_listings_category'),
    ('property_listings','ck_property_listings_status'),('property_profiles','ck_property_profiles_capacity'),
    ('property_visits','ck_property_visits_status'),('users','ck_users_role')}


def cast_signature(definition):
    literal = r"'(?:[^']|'')*'"
    for prefix,item,suffix in [
        ('CHECK ((({column})::text = ANY ((ARRAY[',literal+r'::character varying','])::text[])))'),
        ('CHECK ((({column})::text = ANY (ARRAY[',r'\('+literal+r'::character varying\)::text','])))')]:
        pattern = re.escape(prefix).replace(re.escape('{column}'),r'(?P<column>[a-z_]+)')
        match = re.fullmatch(pattern+r'(?P<items>'+item+r'(?:, '+item+r')*)'+re.escape(suffix),definition)
        if match:
            return match['column'],tuple(re.findall(literal,match['items']))
    return None


def compare_constraints(before,after):
    require(len(before)==len(after))
    for expected,actual in zip(before,after):
        require(expected[:2]==actual[:2] and expected[3:]==actual[3:])
        if expected[2]!=actual[2]:
            signature = cast_signature(expected[2])
            require(tuple(expected[:2]) in EQUIVALENT_CAST_CHECKS and signature is not None
                    and signature==cast_signature(actual[2]))


def compare_schema(before, after, migrated=False):
    require(set(before)==set(after))
    require(before['indexes'] == after['indexes'])
    if not migrated:
        require(before['columns']==after['columns'])
        compare_constraints(before['constraints'],after['constraints'])
        if 'constraint_metadata' in before:
            require(before['constraint_metadata']==after['constraint_metadata'])
        return
    require(before['columns'] == [r for r in after['columns']
        if not (r[0]=='seller_profiles' and r[1] in PUBLIC_FIELDS)])
    old_names = {tuple(r[:2]) for r in before['constraints']}
    extra = [r for r in after['constraints'] if tuple(r[:2]) not in old_names]
    require(len(extra)==3 and all(r[0]=='seller_profiles' and r[3] is True for r in extra))
    require(set(r[1] for r in extra) == {
        'ck_seller_profiles_public_discovery_latitude',
        'ck_seller_profiles_public_discovery_longitude','ck_seller_profiles_public_discovery_fields'})
    compare_constraints(before['constraints'],[r for r in after['constraints'] if r not in extra])
    if 'constraint_metadata' in before:
        require(before['constraint_metadata']==[r for r in after['constraint_metadata'] if tuple(r[:2]) in old_names])


def child_environment(url, name, readonly=False):
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith('PG')}
    env.update(PGHOST='127.0.0.1',PGPORT='5432',PGUSER=url.username,
               PGPASSWORD=url.password or '',PGDATABASE=name,
               PGCONNECT_TIMEOUT='5',PGAPPNAME='whatnot_0009_rehearsal_tools',
               PGOPTIONS='-c timezone=UTC -c default_transaction_read_only=' + ('on' if readonly else 'off'))
    require(name != SOURCE or readonly)
    return env


def command(binary, args, folder, env=None, input=None, capture=False):
    # Inputs/errors may contain source data. Never print them; logs stay private.
    log = folder / (binary + '-' + uuid4().hex + '.log')
    with log.open('wb') as stream:
        result = subprocess.run([str(BIN / (binary + '.exe')), *map(str,args)], input=input,
            stdout=subprocess.PIPE if capture else stream, stderr=stream, env=env,
            timeout=180, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    require(result.returncode == 0)
    return result.stdout if capture else log


def backup_check(manifest, folder):
    archive = archive_path(manifest,folder)
    require(archive.is_file() and archive.read_bytes()[:5] == b'PGDMP')
    require(checksum(archive) == manifest['backup_sha256'])
    toc = command('pg_restore',['--list',archive],folder,capture=True).decode('utf-8','replace')
    require(re.search(r'^;\s+dbname:\s+whatnot_app_dev\s*$',toc,re.M) is not None)
    for table in manifest['before']:
        require(re.search(r'\bTABLE DATA public '+re.escape(table)+r'\s',toc) is not None)
    # Read/decompress the entire archive, not merely its table of contents.
    command('pg_restore',['--file',os.devnull,archive],folder)
    return archive


def archive_path(manifest,folder):
    name = manifest.get('archive_name','whatnot_app_dev-0008-before-0009.dump')
    require(re.fullmatch(r'whatnot_app_dev-0008-before-0009(?:-[a-f0-9]{8})?\.dump',name) is not None)
    return folder / name


def refresh_backup(url,manifest,folder):
    global STAGE
    STAGE = 'fresh post-administrator exported-snapshot backup'
    previous = dict(path=str(archive_path(manifest,folder)),sha256=manifest['backup_sha256'])
    updated = dict(manifest)
    updated['archive_name'] = 'whatnot_app_dev-0008-before-0009-'+uuid4().hex[:8]+'.dump'
    archive = archive_path(updated,folder)
    require(not archive.exists())
    with connect(url,SOURCE) as c:
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        source_check(c)
        updated['before'] = snapshot(c)
        require(all(updated['before'][t]==v for t,v in manifest['before'].items() if t!='request_quotas'))
        updated['schema_before'] = schema_snapshot(c)
        snapshot_id = c.execute('SELECT pg_export_snapshot()').fetchone()[0]
        require(bool(snapshot_id))
        command('pg_dump',['--format=custom','--snapshot',snapshot_id,'--no-password','--file',archive],
                folder,env=child_environment(url,SOURCE,readonly=True))
        updated['backup_sha256'] = checksum(archive)
        updated['backup_created_utc'] = datetime.now(timezone.utc).isoformat()
        source_check(c)
    checksum_path = folder / (archive.name+'.sha256')
    with checksum_path.open('x',encoding='ascii') as stream:
        stream.write(updated['backup_sha256']+'  '+archive.name+'\n')
    updated['earlier_backups_retained'] = manifest.get('earlier_backups_retained',[]) + [previous]
    backup_check(updated,folder)
    (folder/'manifest-before-refresh.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (folder/'manifest.json').write_text(json.dumps(updated,indent=2),encoding='utf-8')
    print(json.dumps(dict(stage=STAGE,status='PASS',backup=str(archive),bytes=archive.stat().st_size,
        sha256=updated['backup_sha256'],pg_dump_exit=0,listing_exit=0,full_archive_decode_exit=0,
        earlier_backup_retained=True)),flush=True)
    return updated


def protect_directory(folder):
    identity = subprocess.run(['whoami','/user','/fo','csv','/nh'],capture_output=True,text=True,check=True)
    sid = list(csv.reader(identity.stdout.splitlines()))[0][1]
    require(re.fullmatch(r'S-1-[0-9-]+',sid) is not None)
    result = subprocess.run(['icacls',str(folder),'/inheritance:r','/grant:r',
        '*'+sid+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],capture_output=True,check=False)
    require(result.returncode == 0)


def restore_header(name, oid, run):
    validate_target((name,oid,'127.0.0.1',5432,170011,False,True),name,oid,run)
    return f"""DO $guard$ BEGIN
      IF current_database() <> '{name}' OR host(inet_server_addr()) <> '127.0.0.1'
         OR inet_server_port() <> 5432 OR pg_is_in_recovery()
         OR NOT EXISTS(SELECT 1 FROM pg_catalog.pg_database WHERE datname=current_database()
             AND oid={oid} AND datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user))
      THEN RAISE EXCEPTION 'Rehearsal identity mismatch'; END IF;
    END $guard$;
    """.encode('ascii')


def validate_restore_sql(script):
    require(re.search(rb'^\s*\\(?:connect|c)\b|\b(?:CREATE|DROP)\s+DATABASE\b',script,re.I|re.M) is None)


def administrator_sql(manifest):
    result = """-- Approved NEW isolated databases only; never alters source or existing targets.
\\set ON_ERROR_STOP on
SELECT current_database()='postgres' AND host(inet_server_addr())='127.0.0.1'
 AND inet_server_port()=5432 AND NOT pg_is_in_recovery()
 AND current_setting('server_version_num')::int BETWEEN 170000 AND 179999
 AND EXISTS(SELECT 1 FROM pg_roles WHERE rolname=current_user AND (rolsuper OR rolcreatedb))
 AND EXISTS(SELECT 1 FROM pg_database WHERE datname='whatnot_app_dev' AND oid=41069
            AND datlocprovider='c') AS guard_ok \\gset
\\if :guard_ok
\\else
  \\echo STOP: wrong server/source identity, locale provider or administrator privilege.
  \\quit 3
\\endif
"""
    for name in (manifest['rehearsal'],manifest['rollback']):
        require(name in target_names(manifest['run']))
        result += f"""
SELECT NOT EXISTS(SELECT 1 FROM pg_database WHERE datname='{name}')
 AND EXISTS(SELECT 1 FROM pg_database WHERE datname='whatnot_app_dev' AND oid=41069)
 AS unused_ok \\gset
\\if :unused_ok
\\else
  \\echo STOP: target already exists or source identity changed; nothing overwritten.
  \\quit 3
\\endif
SELECT format('CREATE DATABASE %I WITH OWNER %I TEMPLATE template0 ENCODING %L LOCALE_PROVIDER libc LC_COLLATE %L LC_CTYPE %L',
 '{name}',pg_get_userbyid(datdba),pg_encoding_to_char(encoding),datcollate,datctype)
 FROM pg_database WHERE datname='whatnot_app_dev' AND oid=41069 \\gexec
DO $guard$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM pg_database d JOIN pg_database s ON s.datname='whatnot_app_dev'
   WHERE d.datname='{name}' AND d.datdba=s.datdba AND s.oid=41069)
 THEN RAISE EXCEPTION 'New database owner verification failed'; END IF;
END $guard$;
REVOKE ALL ON DATABASE {name} FROM PUBLIC;
"""
    result += f"""
SELECT d.datname,d.oid,d.datdba=s.datdba AS owner_matches_source
 FROM pg_database d JOIN pg_database s ON s.datname='whatnot_app_dev' AND s.oid=41069
 WHERE d.datname IN ('{manifest['rehearsal']}','{manifest['rollback']}') ORDER BY d.datname;
\\echo New isolated targets retained; no restore or migration has run.
"""
    return result


def prepare():
    global STAGE
    url = configuration()
    migration_check()
    folder = Path(tempfile.mkdtemp(prefix='WhatNot0009Rehearsal-')).resolve()
    protect_directory(folder)
    run = uuid4().hex[:8]
    rehearsal,rollback = target_names(run)
    manifest = dict(run=run,source=SOURCE,source_oid=SOURCE_OID,rehearsal=rehearsal,rollback=rollback,
        migration_sha256=MIGRATION_SHA256,created_utc=datetime.now(timezone.utc).isoformat())
    STAGE = 'source read-only snapshot'
    with connect(url,SOURCE) as c:
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
        source_check(c)
        require(c.execute('SELECT count(*) FROM pg_database WHERE datname=ANY(%s)',([rehearsal,rollback],)).fetchone()[0] == 0)
        require(c.execute("SELECT datlocprovider='c' FROM pg_database WHERE datname=current_database()").fetchone()[0] is True)
        manifest['before'] = snapshot(c)
        manifest['schema_before'] = schema_snapshot(c)
        manifest['can_create_database'] = c.execute('SELECT rolsuper OR rolcreatedb FROM pg_roles WHERE rolname=current_user').fetchone()[0]
        print('PASS: source identity/revision/counts verified; read-only snapshot established.',flush=True)
        STAGE = 'fresh exported-snapshot backup'
        snapshot_id = c.execute('SELECT pg_export_snapshot()').fetchone()[0]
        require(bool(snapshot_id))
        archive = folder / 'whatnot_app_dev-0008-before-0009.dump'
        require(not archive.exists())
        command('pg_dump',['--format=custom','--snapshot',snapshot_id,'--no-password','--file',archive],
                folder,env=child_environment(url,SOURCE,readonly=True))
        manifest['backup_sha256'] = checksum(archive)
        (folder / 'backup.sha256').write_text(manifest['backup_sha256']+'  '+archive.name+'\n',encoding='ascii')
        source_check(c)
    STAGE = 'backup integrity verification'
    backup_check(manifest,folder)
    validate_manifest(manifest)
    (folder / 'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    admin_path = ROOT / f'docs/security/create_0009_rehearsal_{run}.psql'
    with admin_path.open('x',encoding='utf-8') as out:
        out.write(administrator_sql(manifest))
    result = dict(status='BLOCKED',stage='new database creation',source=SOURCE,source_oid=SOURCE_OID,
        source_revision='0008',source_read_only=True,counts=COUNTS,backup=str(archive),
        backup_sha256=manifest['backup_sha256'],backup_bytes=archive.stat().st_size,
        snapshot_consistent=True,pg_dump_exit=0,archive_list_exit=0,full_archive_decode_exit=0,
        snapshot_tables=len(manifest['before']),manifest=str(folder/'manifest.json'),
        rehearsal=rehearsal,rollback=rollback,administrator_script=str(admin_path),
        application_role_createdb=manifest['can_create_database'],original_qa_writes=False,
        migrations_executed=False,reason='Existing local administrator must create the two NEW databases; no role privileges changed')
    EVIDENCE.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
    return 3


def target_preflight(url, name, oid, manifest, empty=False):
    with connect(url,name) as c:
        validate_target(c.execute(IDENTITY).fetchone(),name,oid,manifest['run'])
        require(c.execute('SHOW transaction_read_only').fetchone()[0]=='on')
        if empty:
            require(c.execute("""SELECT count(*) FROM pg_class t JOIN pg_namespace n ON n.oid=t.relnamespace
                WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'
                AND t.relkind IN ('r','p','S','v','m','f')""").fetchone()[0]==0)
            require(c.execute("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'").fetchone()[0]==0)
            require(c.execute("SELECT count(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname NOT IN ('public','information_schema')").fetchone()[0]==0)
            require(c.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()').fetchone()[0]==0)


def restore(url,name,oid,manifest,folder):
    global STAGE
    STAGE = 'restore preflight: ' + name
    target_preflight(url,name,oid,manifest,empty=True)
    archive = backup_check(manifest,folder)
    body = command('pg_restore',['--no-owner','--no-privileges','--file','-',archive],folder,capture=True)
    validate_restore_sql(body)
    # Recheck immediately before psql; its FIRST statement also checks identity
    # on the exact physical connection that executes the whole atomic restore.
    target_preflight(url,name,oid,manifest,empty=True)
    STAGE = 'atomic restore: ' + name
    command('psql',['--no-password','--no-psqlrc','--single-transaction','--set','ON_ERROR_STOP=1','--file','-'],
            folder,env=child_environment(url,name),input=restore_header(name,oid,manifest['run'])+body)
    with connect(url,name) as c:
        validate_target(c.execute(IDENTITY).fetchone(),name,oid,manifest['run'])
        require(c.execute('SELECT version_num FROM public.alembic_version').fetchall()==[('0008',)])
        compare_preserved(manifest['before'],snapshot(c))
        compare_schema(manifest['schema_before'],schema_snapshot(c))
    print('PASS: restored exact snapshot/schema at 0008: '+name,flush=True)


def restored_preflight(url,name,oid,manifest):
    target_preflight(url,name,oid,manifest)
    with connect(url,name) as c:
        validate_target(c.execute(IDENTITY).fetchone(),name,oid,manifest['run'])
        require(c.execute('SELECT version_num FROM public.alembic_version').fetchall()==[('0008',)])
        require(c.execute('SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()').fetchone()[0]==0)
        compare_preserved(manifest['before'],snapshot(c))
        compare_schema(manifest['schema_before'],schema_snapshot(c))


def guarded_engine(url,name,oid,manifest,readonly=False):
    from sqlalchemy import create_engine,event
    validate_target((name,oid,'127.0.0.1',5432,170011,False,True),name,oid,manifest['run'])
    target = url.set(host='127.0.0.1',database=name)
    engine = create_engine(target,echo=False,hide_parameters=True,connect_args={
        'connect_timeout':5,'options':'-c timezone=UTC -c lock_timeout=5000 -c statement_timeout=15000'
        + (' -c default_transaction_read_only=on' if readonly else '')})

    def guard(connection,cursor,statement,parameters,context,executemany):
        raw = connection.connection.driver_connection
        require(raw.info.dbname == name)
        if raw.info.transaction_status == psycopg.pq.TransactionStatus.INERROR:
            require(statement.strip().upper().startswith('ROLLBACK TO SAVEPOINT '))
            return
        with raw.cursor() as check:
            check.execute(IDENTITY)
            validate_target(check.fetchone(),name,oid,manifest['run'])
    event.listen(engine,'before_cursor_execute',guard)
    return engine


def verify_0009(c):
    # c is a psycopg connection, including during the explicit rollback probe.
    require(c.execute('SELECT version_num FROM public.alembic_version').fetchall()==[('0009',)])
    rows = c.execute("""SELECT column_name,data_type,numeric_precision,numeric_scale,
        character_maximum_length,is_nullable,column_default FROM information_schema.columns
        WHERE table_schema='public' AND table_name='seller_profiles' AND column_name=ANY(%s)""",
        (list(PUBLIC_FIELDS),)).fetchall()
    require(len(rows)==4)
    for row in rows:
        require(row[5:] == ('YES',None))
        if row[0] in PUBLIC_FIELDS[:2]: require(row[1:4] == ('numeric',9,6))
        elif row[0]==PUBLIC_FIELDS[2]: require(row[1]=='timestamp with time zone')
        else: require(row[1]=='character varying' and row[4]==32)
    require(c.execute("""SELECT count(*) FROM public.seller_profiles WHERE
        public_discovery_latitude IS NOT NULL OR public_discovery_longitude IS NOT NULL
        OR public_discovery_confirmed_at IS NOT NULL OR public_discovery_consent_version IS NOT NULL""").fetchone()[0]==0)


class ExpectedRollback(Exception):
    pass


def constraint_behavior_checks(c):
    """Exercise new constraints on copied sellers; every probe rolls back."""
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError
    from datetime import datetime,timezone
    seller = c.scalar(text('SELECT id FROM seller_profiles ORDER BY id LIMIT 1'))
    require(seller is not None)
    base=dict(lat=0,lon=0,confirmed=datetime.now(timezone.utc),version='public-discovery-v1',seller=seller)
    cases=[({},None),({'lat':90,'lon':180},None),({'lat':-90,'lon':-180},None),
           ({'lat':None,'lon':None,'confirmed':None,'version':None},None),
           ({'lat':91},'latitude'),({'lat':-91},'latitude'),
           ({'lon':181},'longitude'),({'lon':-181},'longitude'),
           ({'confirmed':None},'fields'),({'lat':None},'fields'),
           ({'version':' '},'fields'),({'version':None},'fields')]
    for changes,expected_error in cases:
        try:
            with c.begin_nested() as savepoint:
                c.execute(text('''UPDATE seller_profiles SET public_discovery_latitude=:lat,
                    public_discovery_longitude=:lon,public_discovery_confirmed_at=:confirmed,
                    public_discovery_consent_version=:version WHERE id=:seller'''),{**base,**changes})
                require(expected_error is None)
                savepoint.rollback()
        except IntegrityError as error:
            require(expected_error is not None and error.orig.sqlstate=='23514'
                    and error.orig.diag.constraint_name=='ck_seller_profiles_public_discovery_'+expected_error)
    return len(cases)


def migrate(url,name,oid,manifest,folder,rollback_probe=False):
    global STAGE
    from sqlalchemy import text
    from alembic import command as alembic_command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    STAGE = 'rollback rehearsal' if rollback_probe else '0008 to 0009 rehearsal migration'
    backup_check(manifest,folder)
    migration_check()
    engine = guarded_engine(url,name,oid,manifest)
    config = Config(str(ROOT/'backend/alembic.ini'))
    require(ScriptDirectory.from_config(config).get_heads()==['0009'])
    migration_log = folder / ('rollback-migration.log' if rollback_probe else 'migration.log')
    from contextlib import redirect_stdout,redirect_stderr
    try:
        try:
            with migration_log.open('x',encoding='utf-8') as output,redirect_stdout(output),redirect_stderr(output):
                with engine.begin() as c:
                    raw = c.connection.driver_connection
                    validate_target(raw.execute(IDENTITY).fetchone(),name,oid,manifest['run'])
                    require(c.scalar(text('SELECT version_num FROM public.alembic_version'))=='0008')
                    compare_preserved(manifest['before'],snapshot(raw))
                    migration_check()
                    require(checksum(archive_path(manifest,folder))==manifest['backup_sha256'])
                    config.attributes['connection'] = c
                    config.attributes['database_url'] = engine.url
                    alembic_command.upgrade(config,'0009')
                    verify_0009(raw)
                    require(constraint_behavior_checks(c)==12)
                    verify_0009(raw)
                    compare_preserved(manifest['before'],snapshot(raw,True),allow_revision_change=True)
                    compare_schema(manifest['schema_before'],schema_snapshot(raw),migrated=True)
                    if rollback_probe:
                        raise ExpectedRollback('Controlled failure after DDL/version change, before outer commit')
        except ExpectedRollback:
            require(rollback_probe)
        with connect(url,name) as verification:
            validate_target(verification.execute(IDENTITY).fetchone(),name,oid,manifest['run'])
            if rollback_probe:
                require(verification.execute('SELECT version_num FROM public.alembic_version').fetchall()==[('0008',)])
                compare_preserved(manifest['before'],snapshot(verification))
                compare_schema(manifest['schema_before'],schema_snapshot(verification))
            else:
                verify_0009(verification)
                compare_preserved(manifest['before'],snapshot(verification,True),allow_revision_change=True)
                compare_schema(manifest['schema_before'],schema_snapshot(verification),migrated=True)
        print('PASS: '+('transaction rollback restored exact 0008 schema/data' if rollback_probe
                        else 'migration committed at 0009; all original fields/data preserved'),flush=True)
    finally:
        engine.dispose()


def runtime_checks(url,name,oid,manifest):
    from fastapi.testclient import TestClient
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.main import create_app
    from app.models import User,SellerProfile
    from app.services.discovery import DiscoveryService
    from app.schemas.discovery import DiscoveryQuery
    import secrets
    engine = guarded_engine(url,name,oid,manifest,readonly=True)
    try:
        settings = Settings(_env_file=None,environment='test',database_url=None,jwt_secret_key=secrets.token_urlsafe(48))
        app = create_app(settings)
        app.state.database_engine = engine
        with TestClient(app) as client:
            response = client.get('/api/v1/ready')
            require(response.status_code==200 and response.json()['schema']=='0009')
        # Lifespan disposal above closes its pool, not the engine factory. A new
        # connection below retains the exact same target guards/read-only options.
        with Session(engine) as session,session.begin():
            require(session.execute(select(SellerProfile).limit(0)).all()==[])
            buyer = session.scalar(select(User.id).where(User.role=='BUYER',User.is_active.is_(True)).order_by(User.id).limit(1))
            require(buyer is not None)
            for radius in (1,2,3):
                products = DiscoveryService(session).list(buyer,DiscoveryQuery(location={'latitude':0,'longitude':0},radius_km=radius))
                require(products==[])
        return dict(readiness_http=200,schema='0009',seller_projection='PASS',
                    synthetic_discovery_radii=[1,2,3],empty_until_public_consent=True,
                    read_only=True,network_service_started=False)
    finally:
        engine.dispose()


def resume(args):
    global STAGE
    url = configuration()
    manifest_path = args.resume.resolve()
    folder = manifest_path.parent
    require(manifest_path.name=='manifest.json' and folder.name.startswith('WhatNot0009Rehearsal-')
            and folder.parent.resolve()==Path(tempfile.gettempdir()).resolve())
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    validate_manifest(manifest)
    require(type(args.rehearsal_oid) is int and type(args.rollback_oid) is int
            and args.rehearsal_oid != args.rollback_oid)
    for name,oid in [(manifest['rehearsal'],args.rehearsal_oid),(manifest['rollback'],args.rollback_oid)]:
        validate_target((name,oid,'127.0.0.1',5432,170011,False,True),name,oid,manifest['run'])
    migration_check()
    STAGE = 'resume source read-only verification'
    with connect(url,SOURCE) as c:
        source_check(c)
        current_schema = schema_snapshot(c)
        if 'schema_before' in manifest and 'constraint_metadata' not in manifest['schema_before']:
            # Compare all historical fields before enriching a legacy manifest
            # with freshly verified read-only source enforcement metadata.
            legacy = {k:v for k,v in current_schema.items() if k!='constraint_metadata'}
            compare_schema(manifest['schema_before'],legacy)
            manifest['schema_before']['constraint_metadata'] = current_schema['constraint_metadata']
        if 'schema_before' not in manifest:
            # Initial prepare predates this additional metadata comparison. It
            # remains read-only; backup/snapshot business fingerprints are retained.
            manifest['schema_before'] = current_schema
        compare_schema(manifest['schema_before'],current_schema)
        current = snapshot(c)
        require(all(current[t]==v for t,v in manifest['before'].items() if t!='request_quotas'))
    backup_check(manifest,folder)
    # Check BOTH destinations before any restore. An unexpected existing object
    # stops the whole run; no --clean, overwrite, drop or rerun path exists.
    if args.continue_restored:
        require(not args.refresh_backup)
        restored_preflight(url,manifest['rehearsal'],args.rehearsal_oid,manifest)
        target_preflight(url,manifest['rollback'],args.rollback_oid,manifest,empty=True)
    else:
        for name,oid in [(manifest['rehearsal'],args.rehearsal_oid),(manifest['rollback'],args.rollback_oid)]:
            target_preflight(url,name,oid,manifest,empty=True)
    if args.refresh_backup:
        manifest = refresh_backup(url,manifest,folder)
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    for name,oid in [(manifest['rehearsal'],args.rehearsal_oid),(manifest['rollback'],args.rollback_oid)]:
        if args.continue_restored and name==manifest['rehearsal']:
            restored_preflight(url,name,oid,manifest)
        else:
            restore(url,name,oid,manifest,folder)
    # Probe transactional DDL on the separate disposable database first. A real
    # migration error stops; only the deliberately injected exception is expected.
    migrate(url,manifest['rollback'],args.rollback_oid,manifest,folder,rollback_probe=True)
    migrate(url,manifest['rehearsal'],args.rehearsal_oid,manifest,folder)
    STAGE = 'read-only rehearsal readiness and discovery'
    runtime = runtime_checks(url,manifest['rehearsal'],args.rehearsal_oid,manifest)
    with connect(url,manifest['rehearsal']) as c:
        validate_target(c.execute(IDENTITY).fetchone(),manifest['rehearsal'],args.rehearsal_oid,manifest['run'])
        compare_preserved(manifest['before'],snapshot(c,True),allow_revision_change=True)
    STAGE = 'original final read-only verification'
    with connect(url,SOURCE) as c:
        source_check(c)
        after = snapshot(c)
        require(all(after[t]==v for t,v in manifest['before'].items() if t!='request_quotas'))
        source_quota_drift = after.get('request_quotas') != manifest['before'].get('request_quotas')
    result = dict(status='PASS',source=SOURCE,source_oid=SOURCE_OID,source_revision='0008',
        original_qa_writes=False,original_accounts_and_business_data_unchanged=True,
        source_quota_drift_from_external_activity=source_quota_drift,
        backup=str(archive_path(manifest,folder)),backup_sha256=manifest['backup_sha256'],
        backup_verified=True,snapshot_consistent=True,rehearsal=manifest['rehearsal'],rehearsal_oid=args.rehearsal_oid,
        rehearsal_revision='0009',rollback_database=manifest['rollback'],rollback_oid=args.rollback_oid,
        rollback_revision='0008',rollback_schema_and_data_preserved=True,counts=COUNTS,
        migration_sha256=MIGRATION_SHA256,migration='0008 -> 0009',migration_exit=0,
        all_24_table_data_comparisons_passed=True,account_ids_roles_statuses_hashes_preserved=True,
        columns_added=4,validated_constraints_added=3,all_new_public_fields_null=True,
        new_constraint_behavior_probes=12,
        schema_comparison='Only expected four columns and three constraints added; indexes preserved',
        runtime=runtime,protected_evidence_directory=str(folder),databases_retained=True,
        original_migration_approval_required=True)
    EVIDENCE.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true')
    mode.add_argument('--resume',type=Path)
    parser.add_argument('--rehearsal-oid',type=int)
    parser.add_argument('--rollback-oid',type=int)
    parser.add_argument('--refresh-backup',action='store_true')
    parser.add_argument('--continue-restored',action='store_true')
    args = parser.parse_args()
    if args.prepare:
        require(args.rehearsal_oid is None and args.rollback_oid is None and not args.refresh_backup and not args.continue_restored)
        return prepare()
    return resume(args)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps(dict(status='STOP',stage=STAGE,error_category=type(error).__name__,
                              private_inputs_suppressed=True,no_automatic_retry=True)),flush=True)
        raise SystemExit(1) from None
