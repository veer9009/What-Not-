"""Owner-approved explicit synthetic public-point confirmation, QA OID 50640 only."""
import json
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from app.schemas.public_discovery import PublicDiscoveryConfirmation
from app.services.sellers import SellerService
from run_chrome_discovery_qa import target, require, preflight, IDENTITY, QA


def main():
    url,oid=target()
    require(oid==50640,'Unapproved QA OID')
    engine=create_engine(url,hide_parameters=True)
    def guard(connection,cursor,statement,parameters,context,executemany):
        raw=connection.connection.driver_connection
        require(raw.info.dbname==QA,'Wrong fixture target')
        with raw.cursor() as check:
            check.execute(IDENTITY)
            require(tuple(check.fetchone())==(QA,oid,True),'Fixture identity changed')
    event.listen(engine,'before_cursor_execute',guard)
    try:
        with Session(engine) as s,s.begin():
            require(s.scalar(text('SELECT version_num FROM alembic_version'))=='0009','Expected migrated QA')
            require(s.scalar(text('SELECT count(*) FROM users'))==2 and s.scalar(text('SELECT count(*) FROM seller_profiles'))==1,'Unexpected fixtures')
            actor=s.scalar(text("SELECT id FROM users WHERE email='chrome-seller@example.com' AND role='SELLER' AND is_active"))
            require(actor is not None,'Synthetic seller missing')
            old=s.execute(text('SELECT row_to_json(t) FROM seller_profiles t')).scalar_one()
            require(old['shop_name']=='Chrome QA Maker' and all(old[k] is None for k in old if k.startswith('public_discovery_')),'Unexpected existing public data; stop')
            SellerService(s).set_public_discovery(actor,PublicDiscoveryConfirmation(
                latitude=0,longitude=0,consent=True,consent_version='public-discovery-v1'))
            new=s.execute(text('SELECT row_to_json(t) FROM seller_profiles t')).scalar_one()
            # The database's updated_at trigger may legitimately update metadata.
            require(all(new[k]==v for k,v in old.items() if not k.startswith('public_discovery_') and k!='updated_at'), 'Private/business fields changed')
        state=preflight(url,oid)
        result={'status':'PASS','database':QA,'oid':oid,'revision':'0009','explicit_owner_approval':True,
                'synthetic_public_point':[0,0],'consent_version':'public-discovery-v1','private_fields_unchanged':True,
                'counts':state['counts'],'positive_products':state['positive_products'],'negative_products':state['negative_products']}
        (Path(__file__).parent/'evidence/qa-public-point.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:engine.dispose()


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
            'message':str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}))
        raise SystemExit(1)
