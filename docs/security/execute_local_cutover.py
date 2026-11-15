"""Owner-approved, single-attempt 0004 -> 0008 cutover of the local original.

On failure, leave the maintenance settings in place. Never retry or downgrade.
No credentials or customer rows are written to the evidence files.
"""
from contextlib import redirect_stdout,redirect_stderr
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from rehearse_auth_recovery import (Settings,make_url,require,snapshot,psycopg,
    Base,User,RequestQuota,select,inspect)
from sqlalchemy import create_engine,event,text
from alembic import command
from alembic.config import Config
from cutover_control import control,verify_defaults,release_plan,is_expected_refusal

ROOT=Path(__file__).resolve().parents[2]
DB='whatnot_app_dev'


def main():
    source=make_url(Settings().database_url.get_secret_value())
    require(source.database==DB and source.host in {'localhost','127.0.0.1'} and (source.port or 5432)==5432,'Unapproved target')
    source=source.set(host='127.0.0.1',port=5432)
    folder=Path(tempfile.mkdtemp(prefix='WhatNotCutover-')).resolve()
    account=subprocess.check_output(['whoami'],text=True).strip()
    acl=subprocess.run(['icacls',str(folder),'/inheritance:r','/grant:r',f'{account}:(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],capture_output=True)
    require(acl.returncode==0,'Backup ACL failed')
    evidence={'date':'2026-11-15','folder':str(folder),'stages':{}}
    stage='preflight'
    def save(name,value):
        evidence['stages'][name]=value
        encoded=json.dumps(evidence,indent=2)
        (folder/'cutover-evidence.json').write_text(encoded,encoding='utf-8')
        (ROOT/'docs/security/evidence/auth-cutover-result.json').write_text(encoded,encoding='utf-8')
        print(json.dumps({'stage':name,**value}),flush=True)
    def hashes():
        recorded=json.loads((ROOT/'docs/security/evidence/auth-cutover-preflight.json').read_text())['migrations']
        for entry in recorded:
            current=hashlib.sha256((ROOT/entry['file']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            require(current==entry['sha256_normalized_lf'],'Migration script differs from rehearsal')
        return {r['file']:r['sha256_normalized_lf'] for r in recorded}
    engine=create_engine(source,hide_parameters=True,pool_pre_ping=False,
        connect_args={'connect_timeout':5,'options':'-c default_transaction_read_only=off -c lock_timeout=5000 -c statement_timeout=30000'})
    checked=0
    try:
        # A prior verified refusal probe may have closed the held session while
        # leaving the effective barrier enabled. Admit only read-only normal
        # sessions long enough to acquire this controlled migration connection.
        with psycopg.connect(host='127.0.0.1',port=5432,user=source.username,
                password=source.password,dbname='postgres',connect_timeout=5) as admission:
            current=admission.execute("SELECT oid,datallowconn FROM pg_database WHERE datname='whatnot_app_dev'").fetchone()
            require(current is not None and current[0]==41069,'Maintenance target OID changed')
            if not current[1]:
                prior=json.loads((ROOT/'docs/security/evidence/auth-cutover-result.json').read_text())
                require(prior['stages'].get('final_gate',{}).get('status')=='FAIL' and
                    'migration' not in prior['stages'],'Cannot resume a migration attempt or unknown barrier')
                defaults=admission.execute('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=%s AND setrole=0',(current[0],)).fetchall()
                require(defaults==[(['default_transaction_read_only=on'],)],'Read-only barrier must remain in place during admission')
                require(admission.execute("SELECT count(*) FROM pg_stat_activity WHERE datname='whatnot_app_dev'").fetchone()[0]==0,'Unexpected source sessions during admission')
                control(admission,current[0],'allow_connections')
                save('read_only_admission',{'status':'PASS','source_remains_read_only':True,
                    'purpose':'Acquire held authorized migration connection after verified refusal probe'})
        with engine.connect() as connection, psycopg.connect(
            host='127.0.0.1',port=5432,user=source.username,password=source.password,
            dbname='postgres',connect_timeout=5) as maintenance:
            row=connection.execute(text("SELECT current_database(),oid,inet_server_addr()::text,inet_server_port(),datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user),datallowconn FROM pg_database WHERE datname=current_database()")).one()
            require(row[0]==DB and row[2]=='127.0.0.1/32' and row[3]==5432 and row[4] and row[5],'Source identity/owner/connectivity mismatch')
            oid=row[1]
            connection.commit()
            raw=connection.connection.driver_connection
            def guard(conn,cursor,statement,parameters,context,executemany):
                nonlocal checked
                with raw.cursor() as c:
                    c.execute('SELECT current_database(),oid,inet_server_addr()::text,inet_server_port() FROM pg_database WHERE datname=current_database()')
                    require(c.fetchone()==(DB,oid,'127.0.0.1/32',5432),'Effective SQL target mismatch')
                checked+=1
            event.listen(engine,'before_cursor_execute',guard)
            def no_others():
                count=connection.scalar(text('SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()'))
                require(count==0,'Other database sessions remain; no automatic termination')
                require(connection.scalar(text('SELECT count(*) FROM pg_prepared_xacts WHERE database=current_database()'))==0,'Prepared transactions exist')
            def take_snapshot():
                with connection.begin():
                    return snapshot(raw)
            no_others()
            original_defaults=connection.execute(text('SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=:oid AND setrole=0'),{'oid':oid}).all()
            verify_defaults(original_defaults)
            connection.commit()
            baseline=take_snapshot()
            require(baseline['alembic_version']==[({'version_num':'0004'},)],'Revision is not approved 0004')
            require(len(baseline['users'])==5 and len(baseline['orders'])==3,'Source counts differ')
            statuses={}
            for r, in baseline['orders']:
                statuses[r['status']]=statuses.get(r['status'],0)+1
            require(statuses=={'DELIVERED':2,'PLACED':1},'Order states differ')
            script_hashes=hashes()
            previous_backup=Path(r'C:\Users\DELL\AppData\Local\Temp\WhatNotCutover-ccqw8brx\whatnot_app_dev-0004-cutover.dump')
            require(hashlib.sha256(previous_backup.read_bytes()).hexdigest()==
                'eccda3083719c8e9a2203245b57c1e117881335e005dcc0a274de57f35fa21d5',
                'Previously verified cutover backup changed')
            save(stage,{'status':'PASS','database':DB,'host':'127.0.0.1','port':5432,'oid':oid,
                'revision':'0004','users':5,'orders':statuses,'other_sessions':0,
                'previous_backup_checksum_matches':True,'migration_hashes':script_hashes})
            stage='maintenance_barrier'
            control(maintenance,oid,'set_readonly')
            probe_args=dict(host='127.0.0.1',port=5432,user=source.username,password=source.password,dbname=DB,connect_timeout=5)
            with psycopg.connect(**probe_args) as probe:
                require(probe.execute('SELECT current_database()').fetchone()[0]==DB,'Probe target mismatch')
                require(probe.execute('SHOW default_transaction_read_only').fetchone()[0]=='on','New connections not read-only')
                try:
                    probe.execute('UPDATE users SET id=id WHERE false')
                except psycopg.errors.ReadOnlySqlTransaction:
                    probe.rollback()
                else:
                    raise RuntimeError('Maintenance barrier failed to block application writes')
            no_others();connection.commit()
            save(stage,{'status':'PASS','new_application_connections_read_only':True,
                        'zero_row_write_probe_sqlstate':'25006','other_sessions':0})
            stage='fresh_backup'
            archive=folder/'whatnot_app_dev-0004-cutover.dump'
            env={k:v for k,v in os.environ.items() if not k.upper().startswith('PG')}
            env.update(PGPASSWORD=source.password or '',PGOPTIONS='-c default_transaction_read_only=on -c lock_timeout=5000')
            with psycopg.connect(**probe_args) as backup_connection:
                backup_connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
                require(snapshot(backup_connection)==baseline,'Data changed before backup snapshot')
                snapshot_id=backup_connection.execute('SELECT pg_export_snapshot()').fetchone()[0]
                with (folder/'pg_dump.log').open('wb') as log:
                    dump=subprocess.run([shutil.which('pg_dump'),'--host','127.0.0.1','--port','5432',
                        '--username',source.username,'--dbname',DB,'--no-password','--format=custom',
                        '--snapshot',snapshot_id,'--file',str(archive)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
                require(dump.returncode==0 and archive.stat().st_size>0,'Fresh backup failed')
            listing=subprocess.run([shutil.which('pg_restore'),'--list',str(archive)],capture_output=True)
            require(listing.returncode==0 and b'TABLE DATA' in listing.stdout,'Fresh archive listing failed')
            (folder/'archive-list.txt').write_bytes(listing.stdout)
            digest=hashlib.sha256(archive.read_bytes()).hexdigest()
            (folder/'backup.sha256').write_text(digest+'\n',encoding='ascii')
            archive.chmod(0o444)
            save(stage,{'status':'PASS','path':str(archive),'bytes':archive.stat().st_size,
                'sha256':digest,'pg_dump_exit':dump.returncode,'pg_restore_list_exit':listing.returncode,
                'consistent_snapshot':True,'archive_read_only_attribute':True,'test_restore_performed':False})
            stage='final_gate'
            no_others();connection.commit()
            control(maintenance,oid,'block_connections')
            refused=False
            try:
                unexpected=psycopg.connect(**probe_args)
            except psycopg.OperationalError as error:
                allowed=maintenance.execute('SELECT datallowconn FROM pg_database WHERE oid=%s',(oid,)).fetchone()[0]
                maintenance.commit()
                require(is_expected_refusal(str(error),allowed),'Unexpected connection failure; barrier unverified')
                refused=True
            else:
                unexpected.close()
            require(refused,'Hard connection barrier not enforced')
            no_others();connection.commit()
            require(take_snapshot()==baseline,'Data changed before migration')
            require(hashes()==script_hashes and hashlib.sha256(archive.read_bytes()).hexdigest()==digest,'Scripts or backup changed')
            save(stage,{'status':'PASS','allow_connections':False,'new_connections_verified_refused':True,
                'only_held_migration_connection':True,'backup_checksum_matches':True,'revision':'0004'})
            stage='migration'
            cfg=Config(str(ROOT/'backend/alembic.ini'))
            cfg.attributes['database_url']=source
            cfg.attributes['connection']=connection
            migration_log=folder/'migration.log'
            start=time.monotonic()
            with migration_log.open('w',encoding='utf-8') as log,redirect_stdout(log),redirect_stderr(log):
                with connection.begin():
                    command.upgrade(cfg,'0008')
            save(stage,{'status':'PASS','command':"command.upgrade(config, '0008') using verified held connection",
                'exit_status':0,'seconds':round(time.monotonic()-start,3),'log':str(migration_log)})
            stage='integrity'
            connection.exec_driver_sql('SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY');connection.commit()
            with connection.begin():
                require(raw.execute('SHOW transaction_read_only').fetchone()[0]=='on','Validation not read-only')
                current=snapshot(raw)
                require(current['alembic_version']==[({'version_num':'0008'},)],'Final revision mismatch')
                for table,rows in baseline.items():
                    if table not in {'users','orders','alembic_version'}:
                        require(current[table]==rows,'Unexpected original business-row change')
                users=[{k:v for k,v in row[0].items() if k not in {'phone_verified_at','email_verified_at'}} for row in current['users']]
                require(sorted(users,key=lambda r:r['id'])==sorted([r[0] for r in baseline['users']],key=lambda r:r['id']),'Original users changed')
                require(all(r[0]['phone_verified_at'] is None and r[0]['email_verified_at'] is None for r in current['users']),'Unexpected verification evidence')
                expected_orders={r[0]['id']:dict(r[0],delivered_at=None,confirmation_deadline=None,completed_at=None,completion_source=None) for r in baseline['orders']}
                audit=[r[0] for r in current['audit_events']]
                converted=0
                for row, in current['orders']:
                    expected=expected_orders[row['id']]
                    if expected['status']=='DELIVERED':
                        expected.update(status='COMPLETED',completion_source='LEGACY');converted+=1
                        require(sum(a['entity_id']==row['id'] and a['entity_type']=='order' and a['actor_type']=='MIGRATION' and a['action']=='ORDER_MIGRATION' and a['previous_status']=='DELIVERED' and a['next_status']=='COMPLETED' and a['reason']=='0005_LEGACY_MAPPING' for a in audit)==1,'Missing audit mapping')
                    require(row==expected,'Unexpected order transformation')
                require(len(current['orders'])==3 and converted==2 and len(audit)==2,'Order/audit counts differ')
                inspector=inspect(connection)
                for table in Base.metadata.sorted_tables:
                    require(inspector.has_table(table.name),'Missing mapped table')
                    require(set(table.columns.keys())<={c['name'] for c in inspector.get_columns(table.name)},'Missing mapped columns')
                connection.execute(select(User).limit(0));connection.execute(select(RequestQuota).limit(0))
                command.check(cfg)
            save(stage,{'status':'PASS','revision':'0008','users_before':5,'users_after':5,
                'orders_before':3,'orders_after':3,'legacy_conversions':2,'placed_unchanged':1,
                'matching_audit_events':2,'all_original_other_rows_unchanged':True,
                'orm_schema_and_auth_projections':'PASS','alembic_check':'PASS','validation_read_only':True})
            stage='reopen_after_integrity'
            connection.exec_driver_sql('SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE');connection.commit()
            for action in release_plan(True):
                control(maintenance,oid,action)
            save(stage,{'status':'PASS','original_database_settings_restored':True,
                'application_processes_started':False,'guarded_sql_statements':checked})
        return 0
    except Exception as error:
        save(stage,{'status':'FAIL','exception_class':type(error).__name__,
            'sqlstate':getattr(error,'sqlstate',getattr(getattr(error,'orig',None),'sqlstate',None)),
            'message':str(error) if type(error) is RuntimeError else 'Private exception inputs suppressed',
            'automatic_retry_or_recovery_attempted':False,'maintenance_settings_may_remain':True})
        return 1
    finally:
        engine.dispose()


if __name__=='__main__':
    raise SystemExit(main())
