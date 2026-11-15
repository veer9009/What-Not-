"""Fail-closed manual Chrome QA launcher. Never creates/seeds/migrates a database."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from sqlalchemy import create_engine,event,text
from sqlalchemy.engine import Engine,make_url
from sqlalchemy.orm import Session
import psycopg
from app.core.config import Settings
from app.schemas.discovery import DiscoveryQuery
from app.services.discovery import DiscoveryService
from qa_admin_policy import configured_admin_email,validate_roster,BASE_EMAILS

QA='whatnot_chrome_qa_20261115'
MANIFEST=Path(__file__).parent/'evidence/chrome-qa-provisioning.json'


def require(condition,message):
    if not condition: raise RuntimeError(message)


def target():
    base=make_url(Settings().database_url.get_secret_value())
    require(base.host in {'localhost','127.0.0.1','::1'} and (base.port or 5432)==5432
            and not base.query and base.database in {'whatnot_app_dev',QA},'Unexpected local connection configuration')
    require(MANIFEST.is_file(),'Manual QA provisioning manifest missing; fixture approval/provisioning required')
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8-sig'))
    require(manifest.get('database')==QA and manifest.get('revision')=='0008'
            and manifest.get('fixtures_version')=='chrome-discovery-v1','Invalid QA provisioning manifest')
    oid=manifest.get('oid')
    require(type(oid) is int and oid>0 and oid not in {41069,49264,49265,32877},'Unapproved QA database OID')
    return base.set(database=QA),oid


IDENTITY="""SELECT current_database(),oid,datdba=(SELECT oid FROM pg_roles WHERE rolname=current_user)
    FROM pg_database WHERE datname=current_database()"""


def preflight(url,oid):
    engine=create_engine(url,hide_parameters=True,connect_args={
        'options':'-c default_transaction_read_only=on -c statement_timeout=5000'})
    try:
        with Session(engine) as session,session.begin():
            session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            require(tuple(session.execute(text(IDENTITY)).one())==(QA,oid,True),'QA name/OID/owner mismatch')
            require(session.scalar(text('SHOW transaction_read_only'))=='on','QA preflight must be read-only')
            require(session.scalar(text('SELECT version_num FROM public.alembic_version'))=='0009','QA revision mismatch (public discovery migration required)')
            counts={table:session.scalar(text(f'SELECT count(*) FROM public.{table}'))
                    for table in ('users','seller_profiles','products','addresses','orders')}
            admin_email=configured_admin_email()
            require(counts==dict(users=3 if admin_email else 2,seller_profiles=1,products=3,addresses=1,orders=0),'QA business fixture counts differ')
            users=session.execute(text("""SELECT id,email,role,is_active,password_hash LIKE '$argon2id$%'
                FROM public.users ORDER BY email""")).all()
            validate_roster([(row[1],row[2],row[3]) for row in users],admin_email)
            require(all(row[4] for row in users),'QA account hash policy differs')
            buyer=next(row[0] for row in users if row[2]=='BUYER')
            seller=session.execute(text("""SELECT shop_name,latitude=0 AND longitude=0,
                dispatch_location_confirmed_at IS NOT NULL,is_verified FROM public.seller_profiles""")).one()
            require(tuple(seller)==('Chrome QA Maker',True,True,False),'QA dispatch fixture differs')
            require(session.scalar(text("SELECT count(*) FROM seller_profiles WHERE public_discovery_latitude=0 AND public_discovery_longitude=0 AND public_discovery_confirmed_at IS NOT NULL AND public_discovery_consent_version='public-discovery-v1'"))==1,'Approved QA public point not confirmed')
            products=session.execute(text("""SELECT name,price::text,stock_quantity,status,is_active,delivery_radius_km
                FROM public.products ORDER BY name""")).all()
            require([tuple(row) for row in products]==[
                ('QA Nearby Basket','125.50',4,'APPROVED',True,1),
                ('QA Nearby Vase','250.00',5,'APPROVED',True,2),
                ('QA Pending Sample','99.00',3,'PENDING',True,3)],'QA product fixtures differ')
            address=session.execute(text("""SELECT user_id,label,pincode,latitude=0 AND longitude=0
                FROM public.addresses""")).one()
            require(tuple(address)==(buyer,'QA Home','999999',True),'QA owned address fixture differs')
            service=DiscoveryService(session)
            positive=service.list(buyer,DiscoveryQuery(location={'latitude':0,'longitude':0}))
            negative=service.list(buyer,DiscoveryQuery(location={'latitude':1,'longitude':1}))
            require({product.name for product in positive}=={'QA Nearby Vase','QA Nearby Basket'} and not negative,
                    'QA positive/negative service checks failed')
            return {'status':'PASS','database':QA,'oid':oid,'revision':'0009','read_only_preflight':True,
                    'counts':counts,'positive_products':2,'negative_products':0}
    finally:
        engine.dispose()


def serve(url,oid,port=8001):
    # Only this new QA child receives the URL/key/settings; existing .env and
    # original process credentials/settings remain unchanged. QA tokens use an
    # independent ephemeral signing key and cannot authenticate to the original.
    os.environ['DATABASE_URL']=url.render_as_string(hide_password=False)
    os.environ['WHAT_NOT_ENVIRONMENT']='development'
    os.environ['WHAT_NOT_JWT_SECRET_KEY']=secrets.token_urlsafe(48)
    os.environ['WHAT_NOT_CORS_ORIGINS']='["http://127.0.0.1:5174"]'
    admin_email=configured_admin_email()
    os.environ['WHAT_NOT_BETA_ALLOWED_EMAILS']=json.dumps(BASE_EMAILS+([admin_email] if admin_email else []))
    os.environ['WHAT_NOT_ABUSE_LIMITS_ENABLED']='true'
    os.environ['WHAT_NOT_EMAIL_PROVIDER']='disabled'
    def guard(connection,cursor,statement,parameters,context,executemany):
        raw=connection.connection.driver_connection
        require(raw.info.dbname==QA,'QA runtime connected to an unapproved database')
        if raw.info.transaction_status==psycopg.pq.TransactionStatus.INERROR:
            require(statement.strip().upper().startswith('ROLLBACK TO SAVEPOINT '),'Only QA transaction recovery allowed')
            return
        with raw.cursor() as check:
            check.execute(IDENTITY)
            require(tuple(check.fetchone())==(QA,oid,True),'QA runtime identity changed')
    event.listen(Engine,'before_cursor_execute',guard)
    from app.main import create_app
    import uvicorn
    require(port in (8001,8002),'Unapproved QA port')
    uvicorn.run(create_app(Settings()),host='127.0.0.1',port=port,access_log=False)


if __name__=='__main__':
    try:
        parser=argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--serve',action='store_true')
        parser.add_argument('--port',type=int,choices=(8001,8002),default=8001)
        args=parser.parse_args()
        url,oid=target()
        print(json.dumps(preflight(url,oid),indent=2),flush=True)
        if args.serve: serve(url,oid,args.port)
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
            'message':str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}),flush=True)
        raise SystemExit(1)
