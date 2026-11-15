"""Final enforced-read-only data/schema verification; prints aggregate evidence."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from rehearse_existing_server import (SOURCE,REHEARSAL,TESTS,ARCHIVE,CHECKSUM,
    IDENTITY_SQL,verify_identity,Settings,make_url,psycopg,snapshot,require)


def main():
    u=make_url(Settings().database_url.get_secret_value())
    require(u.database==SOURCE and u.host in {'localhost','127.0.0.1','::1'},'Source mismatch')
    states={}
    for name in [SOURCE,REHEARSAL,TESTS]:
        with psycopg.connect(host=u.host,port=u.port or 5432,user=u.username,
            password=u.password,dbname=name,connect_timeout=5,
            options='-c default_transaction_read_only=on -c statement_timeout=30000') as c:
            require(c.execute('SHOW transaction_read_only').fetchone()[0]=='on','Read-only verification unavailable')
            if name!=SOURCE:
                verify_identity(c.execute(IDENTITY_SQL).fetchone(),name,49264 if name==REHEARSAL else 49265)
            states[name]=snapshot(c)
            if name==REHEARSAL:
                required=set(['phone_verified_at','email_verified_at'])
                columns={r[0] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users'")}
                require(required<=columns,'Missing verification columns')
                require(c.execute("SELECT count(*) FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated").fetchone()[0]==0,'Unvalidated constraints')
                require(c.execute("SELECT count(*) FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND (NOT i.indisvalid OR NOT i.indisready)").fetchone()[0]==0,'Invalid indexes')
    original=states[SOURCE]
    restored=states[REHEARSAL]
    require(original['alembic_version']==[({'version_num':'0004'},)],'Original revision changed')
    require(restored['alembic_version']==[({'version_num':'0008'},)],'Rehearsal revision mismatch')
    require(states[TESTS]['alembic_version']==[({'version_num':'0008'},)],'Test revision mismatch')
    require(len(original['users'])==5 and len(original['orders'])==3,'Original counts changed')
    require('request_quotas' in restored and 'request_quotas' not in original,'Quota schema mismatch')
    clone_users={r[0]['id']:r[0] for r in restored['users']}
    for row, in original['users']:
        copied=clone_users[row['id']]
        require(all(copied[k]==v for k,v in row.items()),'Original user field changed in copy')
        require(copied['phone_verified_at'] is None and copied['email_verified_at'] is None,'Unexpected verification history')
    clone_orders={r[0]['id']:r[0] for r in restored['orders']}
    conversions=0
    audit=[r[0] for r in restored['audit_events']]
    for row, in original['orders']:
        expected=dict(row,delivered_at=None,confirmation_deadline=None,completed_at=None,completion_source=None)
        if row['status']=='DELIVERED':
            conversions+=1
            expected.update(status='COMPLETED',completion_source='LEGACY')
            require(sum(a['entity_id']==row['id'] and a['entity_type']=='order' and
                a['actor_type']=='MIGRATION' and a['action']=='ORDER_MIGRATION' and
                a['previous_status']=='DELIVERED' and a['next_status']=='COMPLETED' and
                a['reason']=='0005_LEGACY_MAPPING' for a in audit)==1,'Missing migration audit event')
        else:
            require(row['status']=='PLACED','Unexpected original status')
        require(clone_orders[row['id']]==expected,'Unexpected order mutation')
    require(conversions==2 and len(audit)==2,'Wrong transformation/audit counts')
    for table,rows in original.items():
        if table not in {'users','orders','alembic_version'}:
            require(restored[table]==rows,'Other original records changed in copy')
    digest=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    require(digest==CHECKSUM,'Backup changed')
    evidence={'status':'PASS','source_revision':'0004','rehearsal_revision':'0008',
        'test_revision':'0008','original_users_preserved':5,'original_orders':3,
        'rehearsal_users_including_synthetic_smoke_account':len(restored['users']),
        'legacy_order_conversions':2,'placed_order_unchanged':1,'matching_audit_events':2,
        'request_quotas_table_present':True,'user_verification_columns_present':True,
        'all_original_other_business_rows_match':True,'constraints_indexes_valid':True,
        'all_verification_connections_read_only':True,'backup':str(ARCHIVE),'sha256':digest}
    (Path(__file__).parent/'evidence/auth-rehearsal-verified.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(json.dumps(evidence,indent=2))


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
            'message':str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}))
        raise SystemExit(1)
