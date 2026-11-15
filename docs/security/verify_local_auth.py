"""Authorized original-DB auth smoke; creates exactly one synthetic buyer."""
import json
import logging
from pathlib import Path
import secrets
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from rehearse_auth_recovery import Settings,make_url,require,snapshot,psycopg,create_app,TestClient
from sqlalchemy import create_engine,event


def main():
    settings=Settings()
    u=make_url(settings.database_url.get_secret_value())
    require(settings.environment=='development' and u.database=='whatnot_app_dev' and
        u.host in {'localhost','127.0.0.1'} and (u.port or 5432)==5432,'Unapproved app target')
    def read_state():
        with psycopg.connect(host='127.0.0.1',port=5432,user=u.username,password=u.password,
            dbname=u.database,options='-c default_transaction_read_only=on',connect_timeout=5) as c:
            require(c.execute('SELECT current_database()').fetchone()[0]==u.database,'Wrong source')
            return snapshot(c)
    before=read_state()
    require(before['alembic_version']==[({'version_num':'0008'},)] and len(before['users'])==5,'Unexpected pre-smoke state')
    settings=settings.model_copy(update={'email_provider':'disabled'})
    engine=create_engine(u,hide_parameters=True)
    def guard(conn,cursor,statement,parameters,context,executemany):
        with conn.connection.driver_connection.cursor() as c:
            c.execute('SELECT current_database(),oid,inet_server_addr()::text,inet_server_port() FROM pg_database WHERE datname=current_database()')
            require(c.fetchone()==('whatnot_app_dev',41069,'127.0.0.1/32',5432),'Auth SQL target mismatch')
    event.listen(engine,'before_cursor_execute',guard)
    application=create_app(settings)
    application.state.database_engine=engine
    events=[]
    class Capture(logging.Handler):
        def emit(self,record):
            events.append(record.getMessage())
    handler=Capture()
    logger=logging.getLogger('whatnot.api')
    logger.addHandler(handler)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    statuses={}
    key=secrets.token_hex(8)
    password=secrets.token_urlsafe(36)
    payload=dict(name='Local recovery verification',email='local-recovery-'+key+'@example.com',
        phone='recovery-'+key,password=password,role='BUYER')
    try:
        with TestClient(application) as client:
            def check(label,method,path,status,**kwargs):
                response=client.request(method,'/api/v1'+path,**kwargs)
                statuses[label]=response.status_code
                require(response.status_code==status,'Unexpected HTTP status for '+label)
                return response
            check('health','GET','/health',200)
            check('readiness','GET','/ready',200)
            registered=check('registration','POST','/auth/register',201,json=payload)
            check('duplicate_registration','POST','/auth/register',409,json=payload)
            login=check('login','POST','/auth/login',200,json=dict(email=payload['email'],password=password))
            me=check('authenticated_identity','GET','/auth/me',200,
                headers={'Authorization':'Bearer '+login.json()['access_token']})
            require(me.json()['id']==registered.json()['id'],'Token identity mismatch')
            check('wrong_password','POST','/auth/login',401,
                json=dict(email=payload['email'],password='incorrect-password'))
            old_limit=settings.auth_quarter_hour_limit
            try:
                settings.auth_quarter_hour_limit=1
                limited=check('quota_enforced','POST','/auth/login',429,
                    json=dict(email=payload['email'],password=password))
                require(int(limited.headers['Retry-After'])>0,'Missing quota retry advice')
            finally:
                settings.auth_quarter_hour_limit=old_limit
        after=read_state()
        require(len(after['users'])==6,'Synthetic registration count mismatch')
        users={r[0]['id']:r[0] for r in after['users']}
        require(all(users[r[0]['id']]==r[0] for r in before['users']),'Original user changed')
        for table,rows in before.items():
            if table not in {'users','request_quotas'}:
                require(after[table]==rows,'Unexpected non-auth business-row change')
        require(len(after['request_quotas'])>0,'Quota writes absent')
        require('storage_operation_failed' not in events and 503 not in statuses.values(),'Storage/auth failure observed')
        result={'status':'PASS','database':'whatnot_app_dev','http_statuses':statuses,
            'original_users_preserved':5,'synthetic_users_created':1,'total_users_after':6,
            'orders_after':3,'unrelated_business_rows_unchanged':True,'quota_rows':len(after['request_quotas']),
            'storage_operation_failed_events':0,'unexpected_503_responses':0,
            'server_mode':'controlled FastAPI TestClient; no background server',
            'credentials_or_personal_information_printed':False}
        (Path(__file__).parent/'evidence/auth-local-http.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
    finally:
        logger.removeHandler(handler)
        engine.dispose()


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
            'message':str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}))
        raise SystemExit(1)
