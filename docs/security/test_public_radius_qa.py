"""Rollback-only tests on approved populated Chrome QA; no migration/reset fixtures."""
import secrets
from datetime import datetime, timezone
from decimal import Decimal
import pytest
import psycopg
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import get_session, get_transaction_session
from app.core.config import Settings
from app.core.security import create_access_token
from app.main import create_app
from app.models import User, Product, SellerProfile, Address
from app.schemas.discovery import DiscoveryQuery, DiscoverySource
from app.schemas.public_discovery import PublicDiscoveryConfirmation
from app.services.discovery import DiscoveryService
from app.services.sellers import SellerService
from app.services.errors import ProductNotFound
from run_chrome_discovery_qa import target, preflight, require, IDENTITY, QA


def rows(connection):
    return {t:list(connection.scalars(text('SELECT row_to_json(t)::text FROM '+t+' t ORDER BY id')))
            for t in ('users','seller_profiles','products','addresses','orders')}


@pytest.fixture(scope='module')
def engine():
    url,oid=target()
    require(oid==50640,'Unapproved test OID')
    preflight(url,oid)
    engine=create_engine(url,hide_parameters=True)
    def guard(connection,cursor,statement,parameters,context,executemany):
        raw=connection.connection.driver_connection
        require(raw.info.dbname==QA,'Wrong test database')
        if raw.info.transaction_status==psycopg.pq.TransactionStatus.INERROR:
            require(statement.strip().upper().startswith('ROLLBACK TO SAVEPOINT '),'Only savepoint recovery allowed')
            return
        with raw.cursor() as check:
            check.execute(IDENTITY)
            require(tuple(check.fetchone())==(QA,oid,True),'QA test identity changed')
    event.listen(engine,'before_cursor_execute',guard)
    with engine.connect() as connection:before=rows(connection)
    try:yield engine
    finally:
        with engine.connect() as connection:
            require(rows(connection)==before,'QA business rows changed; no cleanup attempted')
        engine.dispose()


@pytest.fixture
def state(engine):
    with engine.connect() as connection:
        outer=connection.begin()
        try:
            with Session(bind=connection,join_transaction_mode='create_savepoint',expire_on_commit=False) as session:
                with session.begin():
                    yield dict(db=session,buyer=session.scalar(select(User).where(User.email=='chrome-buyer@example.com')),
                        seller_user=session.scalar(select(User).where(User.email=='chrome-seller@example.com')),
                        seller=session.scalar(select(SellerProfile)),
                        product=session.scalar(select(Product).where(Product.name=='QA Nearby Vase')),
                        address=session.scalar(select(Address)))
        finally:outer.rollback()


def found(s,longitude,radius=3):
    s['db'].flush()
    return DiscoveryService(s['db']).list(s['buyer'].id,
        DiscoveryQuery(location={'latitude':0,'longitude':longitude},radius_km=radius))


@pytest.mark.parametrize('radius,inside,outside',[(1,.008993,.008994),(2,.017986,.017987),(3,.026979,.026980)])
def test_each_persisted_precision_boundary(state,radius,inside,outside):
    state['product'].delivery_radius_km=3
    assert state['product'].id in [p.id for p in found(state,inside,radius)]
    assert state['product'].id not in [p.id for p in found(state,outside,radius)]
    assert not found(state,.1,radius)


def test_smaller_seller_radius_and_pagination(state):
    state['product'].delivery_radius_km=1
    assert not found(state,.012,3)
    state['product'].delivery_radius_km=2
    assert len(found(state,.012,2))==1
    service=DiscoveryService(state['db'])
    assert not service.list(state['buyer'].id,DiscoveryQuery(location={'latitude':0,'longitude':.012},radius_km=2,offset=1))


@pytest.mark.parametrize('target,field,value',[
    ('product','status','PENDING'),('product','status','REJECTED'),('product','is_active',False),
    ('product','stock_quantity',0),('seller','dispatch_location_confirmed_at',None),
    ('seller_user','is_active',False),('seller_user','role','BUYER'),
])
def test_existing_eligibility_preserved(state,target,field,value):
    setattr(state[target],field,value)
    assert state['product'].id not in [p.id for p in found(state,0)]


def test_consent_revoke_reconfirm_and_private_data(state):
    service=SellerService(state['db']);seller=state['seller']
    private=(seller.latitude,seller.longitude,seller.dispatch_location_confirmed_at)
    service.set_public_discovery(state['seller_user'].id,None)
    assert not found(state,0)
    service.set_public_discovery(state['seller_user'].id,PublicDiscoveryConfirmation(
        latitude=0,longitude=0,consent=True,consent_version='public-discovery-v1'))
    assert len(found(state,0))==2
    assert (seller.latitude,seller.longitude,seller.dispatch_location_confirmed_at)==private


def test_public_and_private_point_gates_both_apply(state):
    state['seller'].public_discovery_longitude=Decimal('.02')
    assert not found(state,0,1)
    state['seller'].public_discovery_longitude=0
    state['seller'].latitude=Decimal('1')
    assert not found(state,0,3)


@pytest.mark.parametrize('radius',[1,2,3])
def test_private_same_cell_indistinguishability(state,radius):
    for origin in [-.025,-.015,-.005,0,.005,.015,.025,.035]:
        observations=[]
        for point in ['.001','.009']:
            state['seller'].latitude=Decimal(point);state['seller'].longitude=Decimal(point)
            observations.append([p.model_dump() for p in found(state,origin,radius)])
        assert observations[0]==observations[1]


def test_saved_address_and_detail_rules(state):
    service=DiscoveryService(state['db']);buyer=state['buyer'].id;product=state['product'].id
    assert len(service.list(buyer,DiscoveryQuery(address_id=state['address'].id,radius_km=1)))==2
    assert service.get(buyer,product,DiscoverySource(location={'latitude':0,'longitude':.012},radius_km=2)).id==product
    with pytest.raises(ProductNotFound):
        service.get(buyer,product,DiscoverySource(location={'latitude':0,'longitude':.012},radius_km=1))


@pytest.mark.parametrize('patch',[
    {'public_discovery_latitude':None},{'public_discovery_latitude':91},
    {'public_discovery_longitude':181},{'public_discovery_confirmed_at':None},
    {'public_discovery_consent_version':None},{'public_discovery_consent_version':''},
])
def test_database_public_point_constraints(state,patch):
    with pytest.raises(IntegrityError),state['db'].begin_nested():
        for key,value in patch.items():setattr(state['seller'],key,value)
        state['db'].flush()


def test_http_auth_radius_ownership_and_consent(state):
    settings=Settings(_env_file=None,environment='development',jwt_secret_key=secrets.token_urlsafe(48),
        beta_allowed_emails=['chrome-buyer@example.com','chrome-seller@example.com'],abuse_limits_enabled=True)
    app=create_app(settings)
    app.dependency_overrides[get_session]=lambda:state['db']
    app.dependency_overrides[get_transaction_session]=lambda:state['db']
    buyer={'Authorization':'Bearer '+create_access_token(state['buyer'].id,settings)}
    seller={'Authorization':'Bearer '+create_access_token(state['seller_user'].id,settings)}
    path='/api/v1/discovery/products';point={'location':{'latitude':0,'longitude':.012}}
    with TestClient(app) as client:
        assert client.get('/api/v1/ready').json()['schema']=='0009'
        assert client.post(path,json={**point,'radius_km':1},headers=buyer).json()==[]
        response=client.post(path,json={**point,'radius_km':2},headers=buyer)
        assert response.status_code==200 and len(response.json())==1
        assert not {'latitude','longitude','distance_km','public_discovery_latitude'} & response.json()[0].keys()
        assert client.post(path,json={**point,'radius_km':3},headers=buyer).status_code==200
        assert client.post(path,json=point).status_code==401
        assert client.post(path,json=point,headers=seller).status_code==403
        assert client.post(path,json={**point,'radius_km':True},headers=buyer).status_code==422
        confirm='/api/v1/sellers/me/public-discovery-location'
        body={'latitude':0,'longitude':0,'consent':True,'consent_version':'public-discovery-v1'}
        assert client.patch(confirm,json=body,headers=buyer).status_code==403
        assert client.patch(confirm,json={**body,'consent':False},headers=seller).status_code==422
        assert client.patch(confirm,json=body,headers=seller).status_code==200
        assert client.post(confirm+'/revoke',json={},headers=seller).status_code==200
        assert client.post(path,json={**point,'radius_km':3},headers=buyer).json()==[]
