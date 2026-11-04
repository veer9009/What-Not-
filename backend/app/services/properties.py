from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select, String
from app.models.user import User
from app.models.property import PropertyProfile, PropertyListing, PropertyEnquiry, PropertyVisit, SavedProperty, PropertyReport

def now(): return datetime.now(timezone.utc)
def fail(code=409): raise HTTPException(code,'Property operation is unavailable for this record or state')
class PropertyService:
    def __init__(self,session,days=30): self.s=session; self.days=days
    def expire_due(self,limit=50):
        """Record each expired reconfirmation cycle once; retain appointments."""
        from app.models.events import AuditEvent
        from app.services.notifications import publish_event
        if not 1 <= limit <= 100:
            raise ValueError('Batch limit must be between 1 and 100')
        expiry_key = 'expiry:' + PropertyListing.expires_at.cast(String)
        handled = select(AuditEvent.id).where(AuditEvent.entity_type=='property',
            AuditEvent.entity_id==PropertyListing.id,AuditEvent.action=='PROPERTY_EXPIRED',
            AuditEvent.reason==expiry_key).exists()
        rows = list(self.s.scalars(select(PropertyListing).where(
            PropertyListing.status=='APPROVED',PropertyListing.expires_at<=now(),~handled)
            .order_by(PropertyListing.expires_at,PropertyListing.id).limit(limit)
            .with_for_update(skip_locked=True).execution_options(populate_existing=True)))
        for prop in rows:
            # Use PostgreSQL's timestamp rendering consistently for the cycle key.
            reason=self.s.scalar(select('expiry:' + PropertyListing.expires_at.cast(String)).where(PropertyListing.id==prop.id))
            self.s.add(AuditEvent(actor_type='SYSTEM',entity_type='property',entity_id=prop.id,
                action='PROPERTY_EXPIRED',reason=reason))
            publish_event(self.s,prop.creator_id,f'property:{prop.id}:{reason}',
                'PROPERTY_EXPIRED','property',prop.id,'Property reconfirmation required',
                'Your listing is hidden from discovery until you reconfirm availability.')
        self.s.flush()
        return len(rows)
    def actor(self,user,role=None):
        actor=self.s.scalar(select(User).where(User.id==user.id).execution_options(populate_existing=True))
        if not actor or not actor.is_active or (role and actor.role!=role): fail(403)
        return actor
    def guard(self,user,id,role=None,participants=()):
        # Account rows precede listing rows. Sorting all participants avoids
        # buyer/creator lock inversion; NO KEY UPDATE permits FK KEY SHARE.
        creator=self.s.scalar(select(PropertyListing.creator_id).where(PropertyListing.id==id))
        if creator is None:fail(404)
        for uid in sorted({user.id,creator,*participants}):
            self.s.scalar(select(User).where(User.id==uid).with_for_update(key_share=True).execution_options(populate_existing=True))
        self.actor(user,role)
        return self.get(id)
    def get(self,id):
        p=self.s.scalar(select(PropertyListing).where(PropertyListing.id==id).with_for_update().execution_options(populate_existing=True))
        if not p: fail(404)
        return p
    def own(self,user,p):
        self.actor(user,'SELLER')
        if p.creator_id!=user.id: fail(404)
    def available(self,p):
        owner=self.s.scalar(select(User).where(User.id==p.creator_id).execution_options(populate_existing=True))
        if p.status!='APPROVED' or p.expires_at<=now() or not owner.is_active: fail()
    def event(self,recipient,kind,entity,id):
        from app.services.notifications import publish_event
        publish_event(self.s,recipient,str(uuid4()),kind,entity,id,'Property activity','Open your property workspace to review an update.')
    def audit(self,user,p,action,reason=None,previous=None):
        from app.models.events import AuditEvent
        self.s.add(AuditEvent(actor_id=user.id,entity_type='property',entity_id=p.id,action=action,reason=reason,previous_status=previous,next_status=p.status))
    def profile(self,user,data=None):
        self.s.scalar(select(User).where(User.id==user.id).with_for_update(key_share=True).execution_options(populate_existing=True))
        self.actor(user,'SELLER')
        p=self.s.scalar(select(PropertyProfile).where(PropertyProfile.user_id==user.id))
        if data:
            if not p: p=PropertyProfile(user_id=user.id); self.s.add(p)
            for k,v in data.model_dump().items(): setattr(p,k,v)
            self.s.flush()
        return p
    def create(self,user,data):
        profile=self.profile(user)
        if not profile: fail()
        p=PropertyListing(creator_id=user.id,capacity=profile.capacity,**data.model_dump(),reconfirmed_at=now(),expires_at=now()+timedelta(days=self.days))
        self.s.add(p);self.s.flush(); return p
    def public(self,p):
        profile=self.s.scalar(select(PropertyProfile).where(PropertyProfile.user_id==p.creator_id))
        return dict(id=p.id,creator_id=p.creator_id,title=p.title,description=p.description,category=p.category,price=str(p.price),locality=p.locality,status=p.status,expires_at=p.expires_at,updated_at=p.updated_at,rejection_reason=p.rejection_reason,capacity=p.capacity,display_name=profile.display_name)
    def disposition_visits(self,p,terminal=False):
        for v in self.s.scalars(select(PropertyVisit).where(PropertyVisit.property_id==p.id,PropertyVisit.status.in_(['PENDING','ALTERNATE','CONFIRMED','SUSPENDED']))):
            v.status='CANCELLED' if terminal or v.status in ['PENDING','ALTERNATE'] else 'SUSPENDED'
            v.reason='Listing unavailable' if terminal else 'Listing requires review and explicit appointment reconfirmation'
            self.event(v.buyer_id,'PROPERTY_VISIT_UPDATED','property_visit',v.id)
        if terminal:
            for e in self.s.scalars(select(PropertyEnquiry).where(PropertyEnquiry.property_id==p.id,PropertyEnquiry.status=='OPEN')):
                e.status='CLOSED';self.event(e.buyer_id,'PROPERTY_ENQUIRY_CLOSED','property_enquiry',e.id)
    def update(self,user,id,data):
        p=self.guard(user,id,'SELLER');self.own(user,p)
        if p.status in ['SOLD','HIDDEN']:fail()
        for k,v in data.model_dump().items():setattr(p,k,v)
        p.capacity=self.profile(user).capacity
        p.status='PENDING';p.rejection_reason=None;self.disposition_visits(p);self.s.flush();return p
    def resubmit(self,user,id):
        p=self.guard(user,id,'SELLER');self.own(user,p)
        if p.status!='REJECTED':fail()
        p.status='PENDING';p.rejection_reason=None;return p
    def reconfirm(self,user,id):
        p=self.guard(user,id,'SELLER');self.own(user,p)
        if p.status in ['SOLD','HIDDEN']:fail()
        p.reconfirmed_at=now();p.expires_at=now()+timedelta(days=self.days);return p
    def sold(self,user,id):
        p=self.guard(user,id,'SELLER');self.own(user,p)
        if p.status!='SOLD':p.status='SOLD';self.disposition_visits(p,True);self.audit(user,p,'PROPERTY_SOLD')
        return p
    def moderate(self,user,id,data):
        p=self.guard(user,id,'ADMIN')
        if p.status=='SOLD' or (data.status=='APPROVED' and p.status!='PENDING'):fail()
        if data.status=='APPROVED' and data.expected_updated_at!=p.updated_at:fail()
        if data.status in ['REJECTED','HIDDEN'] and not (data.reason and data.reason.strip()):fail(422)
        old=p.status;p.status=data.status;p.rejection_reason=data.reason if data.status=='REJECTED' else None
        if data.status!='APPROVED':self.disposition_visits(p,data.status=='HIDDEN')
        self.audit(user,p,'PROPERTY_MODERATED',data.reason,old);self.event(p.creator_id,'PROPERTY_MODERATED','property',p.id);return p
    def enquire(self,user,id,message):
        p=self.guard(user,id,'BUYER');self.available(p)
        e=PropertyEnquiry(property_id=id,buyer_id=user.id,message=message);self.s.add(e);self.s.flush();self.event(p.creator_id,'PROPERTY_ENQUIRY','property_enquiry',e.id);return e
    def reply(self,user,id,message):
        e=self.s.get(PropertyEnquiry,id)
        if not e:fail(404)
        p=self.guard(user,e.property_id,'SELLER',participants=(e.buyer_id,));self.s.refresh(e);self.own(user,p);self.available(p)
        if e.status!='OPEN':fail()
        e.response=message;self.event(e.buyer_id,'PROPERTY_REPLY','property_enquiry',e.id);return e
    def visit(self,user,id,date):
        p=self.guard(user,id,'BUYER');self.available(p)
        if date.tzinfo is None or date<=now():fail(422)
        v=PropertyVisit(property_id=id,buyer_id=user.id,scheduled_at=date);self.s.add(v);self.s.flush();self.event(p.creator_id,'PROPERTY_VISIT','property_visit',v.id);return v
    def visit_action(self,user,id,data):
        v=self.s.get(PropertyVisit,id)
        if not v:fail(404)
        p=self.guard(user,v.property_id,participants=(v.buyer_id,));self.s.refresh(v)
        owner=p.creator_id==user.id and user.role=='SELLER';buyer=v.buyer_id==user.id and user.role=='BUYER'
        if not(owner or buyer):fail(404)
        if data.action=='CANCEL' and v.status in ['PENDING','ALTERNATE','CONFIRMED','SUSPENDED']:v.status='CANCELLED'
        else:
            self.available(p)
            if data.action in ['ACCEPT','ACCEPT_ALTERNATE','RECONFIRM'] and v.scheduled_at<=now():fail()
            if owner and data.action=='ACCEPT' and v.status=='PENDING':v.status='CONFIRMED'
            elif owner and data.action=='REJECT' and v.status in ['PENDING','ALTERNATE','SUSPENDED']:v.status='REJECTED'
            elif owner and data.action=='PROPOSE' and v.status in ['PENDING','ALTERNATE','SUSPENDED'] and data.scheduled_at:
                if data.scheduled_at.tzinfo is None or data.scheduled_at<=now():fail(422)
                v.scheduled_at=data.scheduled_at;v.status='ALTERNATE'
            elif buyer and data.action=='ACCEPT_ALTERNATE' and v.status=='ALTERNATE':v.status='CONFIRMED'
            elif buyer and data.action=='RECONFIRM' and v.status=='SUSPENDED':v.status='PENDING'
            else:fail()
        self.event(v.buyer_id if owner else p.creator_id,'PROPERTY_VISIT_UPDATED','property_visit',v.id);return v
    def visit_location(self,user,id):
        v=self.s.get(PropertyVisit,id)
        if not v or v.buyer_id!=user.id:fail(404)
        p=self.guard(user,v.property_id,'BUYER');self.s.refresh(v)
        if v.status!='CONFIRMED' or v.scheduled_at<=now() or p.status!='APPROVED':fail(403)
        owner=self.s.get(User,p.creator_id)
        if not owner.is_active:fail(403)
        self.audit(user,p,'PROPERTY_APPOINTMENT_ADDRESS_READ');return {'address':p.private_address}
    def location(self,user,id,reason):
        p=self.guard(user,id)
        if user.id!=p.creator_id:
            if user.role!='ADMIN' or not reason or not reason.strip():fail(403)
        self.audit(user,p,'PROPERTY_PRIVATE_ADDRESS_READ',reason);return {'address':p.private_address}
    def save(self,user,id,saved):
        p=self.guard(user,id,'BUYER')
        record=self.s.scalar(select(SavedProperty).where(SavedProperty.buyer_id==user.id,SavedProperty.property_id==id))
        if saved and not record:self.available(p);self.s.add(SavedProperty(buyer_id=user.id,property_id=id))
        if not saved and record:self.s.delete(record)
        return {'saved':saved}
    def report(self,user,id,data):
        self.guard(user,id,'BUYER')
        if data.reason=='other' and not data.explanation.strip():fail(422)
        r=PropertyReport(property_id=id,reporter_id=user.id,**data.model_dump());self.s.add(r);self.s.flush();return r
    def resolve_report(self,user,id,data):
        r=self.s.get(PropertyReport,id)
        if not r:fail(404)
        p=self.guard(user,r.property_id,'ADMIN');self.s.refresh(r)
        if r.disposition!='OPEN':fail()
        r.disposition=data.disposition;r.resolution_reason=data.reason
        if data.takedown:p.status='HIDDEN';self.disposition_visits(p,True)
        self.audit(user,p,'PROPERTY_REPORT_'+data.disposition,data.reason);return r
    def requests(self,user,offset=0,limit=30):
        self.actor(user)
        if user.role not in ['SELLER','BUYER']:fail(403)
        result={}
        for key,model in [('enquiries',PropertyEnquiry),('visits',PropertyVisit)]:
            q=select(model).join(PropertyListing,PropertyListing.id==model.property_id).where(model.buyer_id==user.id if user.role=='BUYER' else PropertyListing.creator_id==user.id).order_by(model.id.desc()).offset(offset).limit(limit)
            rows=[]
            for item in self.s.scalars(q):
                row={c.name:getattr(item,c.name) for c in model.__table__.columns};p=self.s.get(PropertyListing,item.property_id);profile=self.s.scalar(select(PropertyProfile).where(PropertyProfile.user_id==p.creator_id));owner=self.s.get(User,p.creator_id)
                if user.role=='BUYER' and profile.share_contact and p.status=='APPROVED' and owner.is_active and ((key=='enquiries' and item.status=='OPEN' and p.expires_at>now()) or (key=='visits' and item.status=='CONFIRMED' and item.scheduled_at>now())):row['creator_contact']=owner.phone
                rows.append(row)
            result[key]=rows
        return result
