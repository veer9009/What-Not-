from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from app.schemas.property import PropertyCreate, PropertyProfileInput, VisitAction
from app.services.properties import PropertyService
from app.models.user import User
from app.schemas.property import ModerationInput, ReportInput, DispositionInput

def listing(db, records):
    s=PropertyService(db); seller=records['seller_user']; buyer=records['buyer']
    s.profile(seller,PropertyProfileInput(display_name='Owner',capacity='OWNER'))
    p=s.create(seller,PropertyCreate(title='House',description='Quiet home',category='Residential',price='500000',locality='Pune',private_address='Secret Street 123'))
    return s,seller,buyer,p

def test_property_moderation_visit_privacy_and_sale(db,records):
    s,seller,buyer,p=listing(db,records)
    with pytest.raises(HTTPException): s.enquire(buyer,p.id,'Hello')
    p.status='APPROVED'; db.flush()
    v=s.visit(buyer,p.id,datetime.now(timezone.utc)+timedelta(days=2))
    with pytest.raises(HTTPException): s.visit_location(buyer,v.id)
    s.visit_action(seller,v.id,VisitAction(action='ACCEPT'))
    assert s.visit_location(buyer,v.id)['address']=='Secret Street 123'
    assert 'private_address' not in s.public(p)
    s.sold(seller,p.id)
    assert v.status=='CANCELLED'
    with pytest.raises(HTTPException): s.visit_location(buyer,v.id)

def test_expiry_and_material_edit_suspend_visits(db,records):
    s,seller,buyer,p=listing(db,records); p.status='APPROVED'; db.flush()
    v=s.visit(buyer,p.id,datetime.now(timezone.utc)+timedelta(days=2))
    s.visit_action(seller,v.id,VisitAction(action='ACCEPT'))
    p.expires_at=datetime.now(timezone.utc)-timedelta(days=1)
    with pytest.raises(HTTPException): s.enquire(buyer,p.id,'Hello')
    assert s.visit_location(buyer,v.id)['address']
    s.update(seller,p.id,PropertyCreate(title='Changed',description='Quiet home',category='Residential',price='500000',locality='Pune',private_address='Other Street'))
    assert v.status=='SUSPENDED'
    with pytest.raises(HTTPException): s.visit_location(buyer,v.id)

def test_owner_permissions_alternate_time_save_report_and_rejection(db,records):
    s,seller,buyer,p=listing(db,records)
    admin=User(name='Admin',email='property-admin@example.test',phone='1000777001',role='ADMIN',password_hash='test')
    outsider=User(name='Other',email='property-other@example.test',phone='1000777002',role='BUYER',password_hash='test')
    db.add_all([admin,outsider]);db.flush()
    with pytest.raises(HTTPException):s.moderate(buyer,p.id,ModerationInput(status='APPROVED'))
    with pytest.raises(HTTPException):s.moderate(admin,p.id,ModerationInput(status='REJECTED'))
    s.moderate(admin,p.id,ModerationInput(status='REJECTED',reason='Clarify listing'))
    s.reconfirm(seller,p.id)
    assert p.status=='REJECTED'
    s.resubmit(seller,p.id);db.flush();s.moderate(admin,p.id,ModerationInput(status='APPROVED',expected_updated_at=p.updated_at))
    v=s.visit(buyer,p.id,datetime.now(timezone.utc)+timedelta(days=2))
    with pytest.raises(HTTPException):s.visit_action(outsider,v.id,VisitAction(action='ACCEPT_ALTERNATE'))
    s.visit_action(seller,v.id,VisitAction(action='PROPOSE',scheduled_at=datetime.now(timezone.utc)+timedelta(days=3)))
    assert v.status=='ALTERNATE'
    s.visit_action(buyer,v.id,VisitAction(action='ACCEPT_ALTERNATE'))
    assert v.status=='CONFIRMED'
    with pytest.raises(HTTPException):s.visit_location(outsider,v.id)
    with pytest.raises(HTTPException):s.location(buyer,p.id,None)
    assert s.location(admin,p.id,'Investigating a report')['address']
    assert s.save(buyer,p.id,True)==s.save(buyer,p.id,True)=={'saved':True}
    s.save(buyer,p.id,False)
    r=s.report(buyer,p.id,ReportInput(reason='already sold'))
    s.resolve_report(admin,r.id,DispositionInput(disposition='ACTIONED',reason='Investigation confirmed',takedown=True))
    assert p.status=='HIDDEN' and v.status=='CANCELLED'

def test_material_review_requires_explicit_two_party_reconfirmation(db,records):
    s,seller,buyer,p=listing(db,records);p.status='APPROVED';db.flush()
    v=s.visit(buyer,p.id,datetime.now(timezone.utc)+timedelta(days=2));s.visit_action(seller,v.id,VisitAction(action='ACCEPT'))
    s.update(seller,p.id,PropertyCreate(title='Changed',description='Quiet home',category='Residential',price='500000',locality='Pune',private_address='Other Street'))
    p.status='APPROVED';db.flush()
    with pytest.raises(HTTPException):s.visit_location(buyer,v.id)
    s.visit_action(buyer,v.id,VisitAction(action='RECONFIRM'))
    assert v.status=='PENDING'
    s.visit_action(seller,v.id,VisitAction(action='ACCEPT'))
    assert s.visit_location(buyer,v.id)['address']=='Other Street'

def test_property_routes_reject_roles_private_idor_and_mass_assignment(db,records):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.core.config import Settings
    from app.api.dependencies import get_current_user, get_transaction_session
    s,seller,buyer,p=listing(db,records);p.status='APPROVED';db.flush()
    app=create_app(Settings(_env_file=None))
    app.dependency_overrides[get_transaction_session]=lambda:db
    app.dependency_overrides[get_current_user]=lambda:buyer
    with TestClient(app) as client:
        root='/api/v1/properties'
        assert client.get(root+'/admin/queue').status_code==403
        assert client.post(root+f'/{p.id}/sold').status_code==403
        assert client.post(root+f'/{p.id}/location',json={}).status_code==403
        public=client.get(root+f'/{p.id}')
        assert public.status_code==200 and 'Secret Street' not in public.text
        assert client.post(root+f'/{p.id}/visits',json={'scheduled_at':'2040-01-01T00:00:00'}).status_code==422
        app.dependency_overrides[get_current_user]=lambda:seller
        assert client.post(root,json={'status':'APPROVED','creator_id':buyer.id}).status_code==422

def test_sold_visit_confirmation_independent_transaction_race(fresh_database_url):
    from alembic import command
    from sqlalchemy import create_engine,select
    from sqlalchemy.orm import Session
    from conftest import migration_config
    from test_service_concurrency import race_while_locked
    from app.models.property import PropertyListing,PropertyVisit
    command.upgrade(migration_config(fresh_database_url),'head')
    engine=create_engine(fresh_database_url,connect_args={'options':'-c lock_timeout=10000 -c statement_timeout=15000'})
    try:
        with Session(engine,expire_on_commit=False) as seed,seed.begin():
            seller=User(name='Owner',email='race-owner@example.test',phone='prop-race-seller',role='SELLER',password_hash='test')
            buyer=User(name='Buyer',email='race-buyer@example.test',phone='prop-race-buyer',role='BUYER',password_hash='test')
            seed.add_all([seller,buyer]);seed.flush();s=PropertyService(seed)
            s.profile(seller,PropertyProfileInput(display_name='Race owner',capacity='AGENT'))
            p=s.create(seller,PropertyCreate(title='House',description='House',category='Residential',price='500',locality='Pune',private_address='Private'))
            p.status='APPROVED';seed.flush();v=s.visit(buyer,p.id,datetime.now(timezone.utc)+timedelta(days=2))
            seller_id,pid,vid=seller.id,p.id,v.id
        def sell(session):
            PropertyService(session).sold(session.get(User,seller_id),pid);return 'sold'
        def confirm(session):
            try:PropertyService(session).visit_action(session.get(User,seller_id),vid,VisitAction(action='ACCEPT'));return 'confirmed'
            except HTTPException:return 'unavailable'
        result=race_while_locked(engine,select(PropertyListing).where(PropertyListing.id==pid).with_for_update(),[sell,confirm])
        assert 'sold' in result
        with Session(engine) as verify:
            assert verify.get(PropertyListing,pid).status=='SOLD'
            assert verify.get(PropertyVisit,vid).status=='CANCELLED'
    finally:engine.dispose()

def test_profile_capacity_snapshot_and_stale_moderation(db,records):
    s,seller,buyer,p=listing(db,records)
    s.profile(seller,PropertyProfileInput(display_name='Agent',capacity='AGENT'))
    draft=PropertyCreate(title='Agent house',description='House',category='Residential',price='500',locality='Pune',private_address='Private')
    agent=s.create(seller,draft);agent.status='APPROVED';db.flush()
    s.profile(seller,PropertyProfileInput(display_name='Owner',capacity='OWNER'))
    assert s.public(agent)['capacity']=='AGENT'
    assert s.public(s.create(seller,draft))['capacity']=='OWNER'
    s.update(seller,agent.id,draft)
    assert agent.status=='PENDING' and agent.capacity=='OWNER'
    reviewed=agent.updated_at
    s.update(seller,agent.id,draft.model_copy(update={'title':'Unreviewed new title'}))
    admin=User(name='Admin',email='stale-property@example.test',phone='stale-property',role='ADMIN',password_hash='test')
    db.add(admin);db.flush()
    with pytest.raises(HTTPException) as stale:
        s.moderate(admin,agent.id,ModerationInput(status='APPROVED',expected_updated_at=reviewed))
    assert stale.value.status_code==409
    s.moderate(admin,agent.id,ModerationInput(status='APPROVED',expected_updated_at=agent.updated_at))

@pytest.mark.parametrize('unavailable',['PENDING','REJECTED','HIDDEN','EXPIRED','SUSPENDED'])
def test_saved_properties_never_return_unreviewed_or_unavailable_content(db,records,unavailable):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.core.config import Settings
    from app.api.dependencies import get_current_user,get_transaction_session
    s,seller,buyer,p=listing(db,records);p.status='APPROVED';db.flush();s.save(buyer,p.id,True)
    p.description='Unreviewed secret edit'
    if unavailable=='EXPIRED':p.expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    elif unavailable=='SUSPENDED':seller.is_active=False
    else:p.status=unavailable
    db.flush();app=create_app(Settings(_env_file=None))
    app.dependency_overrides[get_transaction_session]=lambda:db
    app.dependency_overrides[get_current_user]=lambda:buyer
    with TestClient(app) as client:
        response=client.get('/api/v1/properties/saved')
        assert response.status_code==200 and response.json()==[]

@pytest.mark.parametrize('operation',['enquiry','visit'])
def test_suspension_committed_while_request_waits_blocks_new_work(fresh_database_url,operation):
    from alembic import command
    from sqlalchemy import create_engine,select,text
    from sqlalchemy.orm import Session
    from conftest import migration_config
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    import time
    command.upgrade(migration_config(fresh_database_url),'head')
    engine=create_engine(fresh_database_url,connect_args={'options':'-c lock_timeout=10000 -c statement_timeout=15000'})
    try:
        with Session(engine,expire_on_commit=False) as seed,seed.begin():
            seller=User(name='Owner',email='suspend-owner@example.test',phone='prop-suspend-seller',role='SELLER',password_hash='test')
            buyer=User(name='Buyer',email='suspend-buyer@example.test',phone='prop-suspend-buyer',role='BUYER',password_hash='test')
            seed.add_all([seller,buyer]);seed.flush();s=PropertyService(seed)
            s.profile(seller,PropertyProfileInput(display_name='Owner',capacity='OWNER'))
            p=s.create(seller,PropertyCreate(title='House',description='House',category='Residential',price='500',locality='Pune',private_address='Private'))
            p.status='APPROVED';seed.flush();bid,pid=buyer.id,p.id
        pids=Queue()
        def request():
            with Session(engine) as session,session.begin():
                actor=session.get(User,bid)  # authentication read before suspension commits
                pids.put(session.scalar(text('SELECT pg_backend_pid()')))
                try:
                    service=PropertyService(session)
                    if operation=='enquiry':service.enquire(actor,pid,'Hello')
                    else:service.visit(actor,pid,datetime.now(timezone.utc)+timedelta(days=2))
                    return 200
                except HTTPException as error:return error.status_code
        with ThreadPoolExecutor(max_workers=1) as pool:
            with Session(engine) as blocker,blocker.begin():
                buyer=blocker.scalar(select(User).where(User.id==bid).with_for_update(key_share=True))
                buyer.is_active=False;blocker.flush()
                future=pool.submit(request);worker_pid=pids.get(timeout=10)
                deadline=time.monotonic()+5
                with engine.connect() as observer:
                    while time.monotonic()<deadline:
                        waiting=observer.scalar(text("SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=:pid"),{'pid':worker_pid})
                        if waiting:break
                        if future.done():break
                        observer.commit();time.sleep(.02)
                    assert waiting,'Request must wait on account guard before writing new work'
            assert future.result(timeout=15)==403
    finally:engine.dispose()
