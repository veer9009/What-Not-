import pytest
from uuid import uuid4
from sqlalchemy import func, select
from test_authentication import auth_client
from test_authorization import bearer
from test_service_concurrency import concurrency_engine, race_while_locked


def setup_flow(db, records):
    from app.schemas.creative import ProviderInput, ListingInput, ModerationInput, RFQInput, ResponseInput
    from app.services.creative import CreativeService
    from app.models.user import User
    admin = User(name='Admin', email='creative-admin@example.test', phone='1119998880', password_hash='test', role='ADMIN')
    db.add(admin); db.flush()
    service = CreativeService(db)
    seller, buyer = records['seller_user'].id, records['buyer'].id
    service.save_provider(seller, ProviderInput(display_name='Studio', bio='Design'))
    listing = service.create_listing(seller, ListingInput(title='Design', description='Brand', category='Video Editing', pricing='FIXED', amount='100', remote=True))
    service.moderate(admin.id, listing.id, ModerationInput(status='APPROVED',expected_updated_at=listing.updated_at))
    rfq = service.create_rfq(buyer, listing.id, RFQInput(brief='A brand identity',request_key=uuid4()))
    response = service.respond(seller, rfq.id, ResponseInput(terms='Logo and style guide', amount='120',request_key=uuid4()))
    return service, buyer, seller, listing, rfq, response


def test_engagement_requires_buyer_confirmation_and_unique_review(db, records):
    from app.schemas.creative import ReviewInput
    from app.services.errors import ServiceError
    from app.models.creative import CreativeEngagement, CreativeReview
    service, buyer, seller, listing, rfq, response = setup_flow(db, records)
    engagement = service.accept(buyer, response.id)
    assert service.accept(buyer, response.id).id == engagement.id
    listing.amount = 999
    assert engagement.amount == 120
    with pytest.raises(ServiceError): service.review(buyer, engagement.id, ReviewInput(rating=5, text='Great'))
    with pytest.raises(ServiceError): service.complete(seller, engagement.id)
    service.deliver(seller, engagement.id)
    service.complete(buyer, engagement.id)
    review = service.review(buyer, engagement.id, ReviewInput(rating=5, text='Great'))
    assert service.review(buyer, engagement.id, ReviewInput(rating=5, text='Great')).id == review.id
    assert db.scalar(select(func.count()).select_from(CreativeEngagement)) == 1
    assert db.scalar(select(func.count()).select_from(CreativeReview)) == 1


def test_rfq_private_and_new_engagement_rechecks_availability(db, records):
    from app.services.errors import ServiceError
    service, buyer, seller, listing, rfq, response = setup_flow(db, records)
    with pytest.raises(ServiceError): service.list_rfqs(records['seller'].id + 10000)
    listing.is_active = False
    with pytest.raises(ServiceError): service.accept(buyer, response.id)
    assert not service.public_listings()


def test_private_rfq_and_all_engagement_mutations_reject_other_participants(db, records):
    from app.models.user import User
    from app.schemas.creative import ResponseInput, ReviewInput
    from app.services.errors import ServiceError
    service, buyer, seller, listing, rfq, response = setup_flow(db, records)
    other = User(name='Other', email='other-creative@example.test', phone='1119998881', password_hash='test', role='BUYER')
    db.add(other);db.flush()
    with pytest.raises(ServiceError): service.responses(other.id, rfq.id)
    with pytest.raises(ServiceError): service.accept(other.id, response.id)
    with pytest.raises(ServiceError): service.respond(buyer, rfq.id, ResponseInput(terms='Unowned',amount='1',request_key=uuid4()))
    engagement = service.accept(buyer, response.id)
    with pytest.raises(ServiceError): service.deliver(other.id, engagement.id)
    with pytest.raises(ServiceError): service.complete(other.id, engagement.id)
    service.deliver(seller, engagement.id);service.complete(buyer, engagement.id)
    with pytest.raises(ServiceError): service.review(other.id, engagement.id, ReviewInput(rating=5,text='Fake'))
    assert not service.list_rfqs(other.id)
    assert not service.engagements(other.id)


def test_suspension_blocks_acceptance_and_admin_can_read_stranded_work(db, records):
    from app.services.errors import ServiceError
    from app.models.user import User
    service, buyer, seller, listing, rfq, response = setup_flow(db, records)
    records['seller_user'].is_active=False
    with pytest.raises(ServiceError):service.accept(buyer,response.id)
    assert not service.public_listings()
    records['seller_user'].is_active=True
    engagement=service.accept(buyer,response.id)
    records['seller_user'].is_active=False
    admin=db.scalar(select(User).where(User.role=='ADMIN'))
    assert service.engagements(admin.id)[0].id==engagement.id


def test_notification_failure_rolls_back_acceptance(db, records, monkeypatch):
    from app.models.creative import CreativeEngagement
    service, buyer, seller, listing, rfq, response = setup_flow(db, records)
    def fail(*args,**kwargs):raise RuntimeError('test persistence failure')
    monkeypatch.setattr('app.services.notifications.publish_event',fail)
    with pytest.raises(RuntimeError):service.accept(buyer,response.id)
    assert db.scalar(select(func.count()).select_from(CreativeEngagement))==0


def test_conflicting_quote_acceptance_and_review_are_rejected(db, records):
    from app.schemas.creative import ResponseInput, ReviewInput
    from app.services.errors import ServiceError
    service, buyer, seller, listing, rfq, response = setup_flow(db, records)
    second=service.respond(seller,rfq.id,ResponseInput(terms='Different',amount='200',request_key=uuid4()))
    engagement=service.accept(buyer,response.id)
    with pytest.raises(ServiceError):service.accept(buyer,second.id)
    with pytest.raises(ServiceError):service.respond(seller,rfq.id,ResponseInput(terms='Changed',amount='300',request_key=uuid4()))
    service.deliver(seller,engagement.id);service.complete(buyer,engagement.id)
    service.review(buyer,engagement.id,ReviewInput(rating=5,text='Good'))
    with pytest.raises(ServiceError):service.review(buyer,engagement.id,ReviewInput(rating=1,text='Changed'))


def test_routes_enforce_roles_and_reject_mass_assignment(auth_client, db, records):
    service,buyer,seller,listing,rfq,response=setup_flow(db,records)
    assert auth_client.get('/api/v1/creative/admin/listings',headers=bearer(buyer)).status_code==403
    assert auth_client.post('/api/v1/creative/provider',json={'display_name':'x','bio':'x'},headers=bearer(buyer)).status_code==403
    assert auth_client.post(f'/api/v1/creative/responses/{response.id}/accept',headers=bearer(seller)).status_code==403
    assert auth_client.post(f'/api/v1/creative/listings/{listing.id}/rfqs',json={'brief':'test','buyer_id':seller},headers=bearer(buyer)).status_code==422
    assert auth_client.post(f'/api/v1/creative/listings/{listing.id}/rfqs',json={'brief':'test','request_key':str(uuid4())},headers=bearer(seller)).status_code==403
    assert auth_client.get('/api/v1/creative/rfqs?limit=101',headers=bearer(buyer)).status_code==422
    assert auth_client.post(f'/api/v1/creative/admin/listings/{listing.id}/moderate',json={'status':'APPROVED'},headers=bearer(seller)).status_code==403
    engagement=service.accept(buyer,response.id)
    listed=auth_client.get('/api/v1/creative/engagements',headers=bearer(buyer))
    assert listed.status_code==200
    assert isinstance(listed.json()[0]['amount'],str)
    assert auth_client.post(f'/api/v1/creative/engagements/{engagement.id}/deliver',headers=bearer(buyer)).status_code==403
    assert auth_client.post(f'/api/v1/creative/engagements/{engagement.id}/complete',headers=bearer(seller)).status_code==403
    assert auth_client.post(f'/api/v1/creative/engagements/{engagement.id}/review',json={'rating':5,'text':'Not yet'},headers=bearer(buyer)).status_code==409


def test_independent_acceptance_transactions_create_one_engagement_and_event(concurrency_engine):
    from sqlalchemy.orm import Session
    from app.models.user import User
    from app.models.creative import CreativeEngagement
    from app.models.events import Notification
    from app.services.creative import CreativeService
    engine=concurrency_engine
    with Session(engine) as session,session.begin():
        buyer=User(name='Buyer',email='racebuyer@creative.test',phone='9100000000',password_hash='test',role='BUYER')
        seller=User(name='Seller',email='raceseller@creative.test',phone='9100000001',password_hash='test',role='SELLER')
        session.add_all([buyer,seller]);session.flush()
        _,buyer_id,_,_,_,response=setup_flow(session,dict(buyer=buyer,seller_user=seller))
        response_id=response.id
    def accept(session):return CreativeService(session).accept(buyer_id,response_id).id
    results=race_while_locked(engine,select(User).where(User.id==buyer_id).with_for_update(),[accept,accept],expected_query='FROM users')
    assert results[0]==results[1]
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(CreativeEngagement))==1
        assert session.scalar(select(func.count()).select_from(Notification).where(Notification.kind=='CREATIVE_ACCEPTED'))==1


def test_moderation_rejects_stale_review_after_provider_edit(db,records):
    from app.schemas.creative import ListingInput,ModerationInput
    from app.models.user import User
    from app.services.errors import PersistenceConflict
    service,buyer,seller,listing,_,_=setup_flow(db,records)
    reviewed=listing.updated_at
    service.update_listing(seller,listing.id,ListingInput(title='Changed scope',description='New scope',category='Video Editing',pricing='FIXED',amount='200',remote=True))
    admin=db.scalar(select(User).where(User.role=='ADMIN'))
    with pytest.raises(PersistenceConflict):service.moderate(admin.id,listing.id,ModerationInput(status='APPROVED',expected_updated_at=reviewed))
    assert listing.status=='PENDING'
    service.moderate(admin.id,listing.id,ModerationInput(status='APPROVED',expected_updated_at=listing.updated_at))
    assert listing.status=='APPROVED'


def test_rfq_and_response_retry_replay_original_or_conflict_without_extra_events(db,records):
    from app.schemas.creative import RFQInput,ResponseInput
    from app.models.creative import CreativeRFQ,CreativeResponse
    from app.models.events import Notification
    from app.services.errors import PersistenceConflict
    service,buyer,seller,listing,rfq,response=setup_flow(db,records)
    request=RFQInput(brief='A second scope',request_key=uuid4())
    first=service.create_rfq(buyer,listing.id,request)
    assert service.create_rfq(buyer,listing.id,request).id==first.id
    with pytest.raises(PersistenceConflict):service.create_rfq(buyer,listing.id,RFQInput(brief='Changed',request_key=request.request_key))
    quote=ResponseInput(terms='New quote',amount='99',request_key=uuid4())
    first_quote=service.respond(seller,first.id,quote)
    assert service.respond(seller,first.id,quote).id==first_quote.id
    with pytest.raises(PersistenceConflict):service.respond(seller,first.id,ResponseInput(terms='Changed',amount='100',request_key=quote.request_key))
    engagement=service.accept(buyer,first_quote.id)
    listing.is_active=False
    assert service.create_rfq(buyer,listing.id,request).id==first.id
    assert service.respond(seller,first.id,quote).id==first_quote.id
    assert db.scalar(select(func.count()).select_from(CreativeRFQ))==2
    assert db.scalar(select(func.count()).select_from(CreativeResponse))==2
    assert db.scalar(select(func.count()).select_from(Notification).where(Notification.kind=='CREATIVE_RFQ'))==2
    assert db.scalar(select(func.count()).select_from(Notification).where(Notification.kind=='CREATIVE_RESPONSE'))==2


def test_cross_actor_delivery_and_confirmation_do_not_deadlock_on_recipient_fk(concurrency_engine,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy.orm import Session
    from app.models.user import User
    from app.models.creative import CreativeEngagement
    from app.services.creative import CreativeService
    from app.services.users import require_user
    engine=concurrency_engine
    with Session(engine) as session,session.begin():
        buyer=User(name='Buyer',email='crossbuyer@creative.test',phone='9200000000',password_hash='test',role='BUYER')
        seller=User(name='Seller',email='crossseller@creative.test',phone='9200000001',password_hash='test',role='SELLER')
        session.add_all([buyer,seller]);session.flush()
        service,buyer_id,seller_id,_,_,response=setup_flow(session,dict(buyer=buyer,seller_user=seller))
        engagement_id=service.accept(buyer_id,response.id).id
    delivering=Event();buyer_locked=Event()
    original=CreativeService._event
    def pause_delivery(self,recipient,key,kind,id,title):
        if kind=='CREATIVE_DELIVERED':
            delivering.set()
            assert buyer_locked.wait(10),'Confirmation must hold its actor lock'
        return original(self,recipient,key,kind,id,title)
    monkeypatch.setattr(CreativeService,'_event',pause_delivery)
    def deliver():
        with Session(engine) as session,session.begin():
            return CreativeService(session).deliver(seller_id,engagement_id).status
    def complete():
        assert delivering.wait(10),'Delivery must hold the engagement lock'
        with Session(engine) as session,session.begin():
            require_user(session,buyer_id,role='BUYER',lock=True)
            buyer_locked.set()
            return CreativeService(session).complete(buyer_id,engagement_id).status
    with ThreadPoolExecutor(max_workers=2) as pool:
        delivery=pool.submit(deliver);confirmation=pool.submit(complete)
        assert delivery.result(timeout=20)=='DELIVERED'
        assert confirmation.result(timeout=20)=='COMPLETED'
    with Session(engine) as session:
        assert session.get(CreativeEngagement,engagement_id).status=='COMPLETED'
