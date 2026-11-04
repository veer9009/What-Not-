from fastapi import APIRouter, Query, Request
from sqlalchemy import select
from app.api.dependencies import Buyer, Seller, Admin, CurrentUser, TransactionSession
from app.api.contracts import IdentifierPath
from app.models.property import PropertyListing, PropertyReport, SavedProperty
from app.models.user import User
from app.schemas.property import PropertyCreate, PropertyProfileInput, MessageInput, VisitCreate, VisitAction, ModerationInput, ReportInput, DispositionInput, SaveInput, LocationInput
from app.services.properties import PropertyService, now
router=APIRouter(prefix='/properties',tags=['Properties'])
def record(row): return {c.name:getattr(row,c.name) for c in row.__table__.columns} if row else None
def service(session,request):return PropertyService(session,request.app.state.settings.property_reconfirmation_days)
@router.get('')
def browse(session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),category:str|None=None,locality:str|None=None):
    q=select(PropertyListing).join(User,User.id==PropertyListing.creator_id).where(PropertyListing.status=='APPROVED',PropertyListing.expires_at>now(),User.is_active.is_(True))
    if category:q=q.where(PropertyListing.category==category)
    if locality:q=q.where(PropertyListing.locality.ilike('%'+locality[:120]+'%'))
    return [PropertyService(session).public(p) for p in session.scalars(q.order_by(PropertyListing.id.desc()).offset(offset).limit(limit))]
@router.get('/profile')
def profile(user:Seller,session:TransactionSession):return record(PropertyService(session).profile(user))
@router.post('/profile')
def profile_save(data:PropertyProfileInput,user:Seller,session:TransactionSession):return record(PropertyService(session).profile(user,data))
@router.get('/mine')
def mine(user:Seller,session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100)):
    return [PropertyService(session).public(p) for p in session.scalars(select(PropertyListing).where(PropertyListing.creator_id==user.id).order_by(PropertyListing.id.desc()).offset(offset).limit(limit))]
@router.get('/saved')
def saved(user:Buyer,session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100)):
    q=select(PropertyListing).join(SavedProperty,SavedProperty.property_id==PropertyListing.id).join(User,User.id==PropertyListing.creator_id).where(SavedProperty.buyer_id==user.id,PropertyListing.status=='APPROVED',PropertyListing.expires_at>now(),User.is_active.is_(True)).order_by(SavedProperty.id.desc()).offset(offset).limit(limit)
    return [PropertyService(session).public(p) for p in session.scalars(q)]
@router.get('/requests')
def requests(user:CurrentUser,session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100)):return PropertyService(session).requests(user,offset,limit)
@router.get('/admin/queue')
def queue(user:Admin,session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100)):
    return [PropertyService(session).public(p) for p in session.scalars(select(PropertyListing).where(PropertyListing.status=='PENDING').order_by(PropertyListing.id).offset(offset).limit(limit))]
@router.get('/admin/reports')
def reports(user:Admin,session:TransactionSession,offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100)):
    return [record(r) for r in session.scalars(select(PropertyReport).where(PropertyReport.disposition=='OPEN').order_by(PropertyReport.id).offset(offset).limit(limit))]
@router.post('/admin/reports/{id}')
def resolve(id:IdentifierPath,data:DispositionInput,user:Admin,session:TransactionSession):return record(PropertyService(session).resolve_report(user,id,data))
@router.post('/enquiries/{id}/reply')
def reply(id:IdentifierPath,data:MessageInput,user:Seller,session:TransactionSession):return record(PropertyService(session).reply(user,id,data.message))
@router.post('/visits/{id}/action')
def visit_action(id:IdentifierPath,data:VisitAction,user:CurrentUser,session:TransactionSession):return record(PropertyService(session).visit_action(user,id,data))
@router.post('/visits/{id}/location')
def visit_location(id:IdentifierPath,user:Buyer,session:TransactionSession):return PropertyService(session).visit_location(user,id)
@router.post('')
def create(data:PropertyCreate,user:Seller,session:TransactionSession,request:Request):
    s=service(session,request);return s.public(s.create(user,data))
@router.get('/{id}')
def detail(id:IdentifierPath,session:TransactionSession):
    s=PropertyService(session);p=s.get(id);s.available(p);return s.public(p)
@router.patch('/{id}')
def edit(id:IdentifierPath,data:PropertyCreate,user:Seller,session:TransactionSession):
    s=PropertyService(session);return s.public(s.update(user,id,data))
@router.post('/{id}/moderation')
def moderate(id:IdentifierPath,data:ModerationInput,user:Admin,session:TransactionSession):
    s=PropertyService(session);return s.public(s.moderate(user,id,data))
@router.post('/{id}/sold')
def sold(id:IdentifierPath,user:Seller,session:TransactionSession):
    s=PropertyService(session);return s.public(s.sold(user,id))
@router.post('/{id}/reconfirm')
def reconfirm(id:IdentifierPath,user:Seller,session:TransactionSession,request:Request):
    s=service(session,request);return s.public(s.reconfirm(user,id))
@router.post('/{id}/resubmit')
def resubmit(id:IdentifierPath,user:Seller,session:TransactionSession):
    s=PropertyService(session);return s.public(s.resubmit(user,id))
@router.post('/{id}/location')
def location(id:IdentifierPath,data:LocationInput,user:CurrentUser,session:TransactionSession):return PropertyService(session).location(user,id,data.reason)
@router.post('/{id}/enquiries')
def enquire(id:IdentifierPath,data:MessageInput,user:Buyer,session:TransactionSession):return record(PropertyService(session).enquire(user,id,data.message))
@router.post('/{id}/visits')
def visit(id:IdentifierPath,data:VisitCreate,user:Buyer,session:TransactionSession):return record(PropertyService(session).visit(user,id,data.scheduled_at))
@router.post('/{id}/save')
def save(id:IdentifierPath,data:SaveInput,user:Buyer,session:TransactionSession):return PropertyService(session).save(user,id,data.saved)
@router.post('/{id}/reports')
def report(id:IdentifierPath,data:ReportInput,user:Buyer,session:TransactionSession):return record(PropertyService(session).report(user,id,data))
