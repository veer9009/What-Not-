from fastapi import APIRouter, Query
from typing import Annotated
from sqlalchemy import inspect
from decimal import Decimal
from app.api.dependencies import Buyer, Seller, Admin, CurrentUser, TransactionSession
from app.api.contracts import IdentifierPath
from app.schemas.creative import ProviderInput, ListingInput, ModerationInput, RFQInput, ResponseInput, ReviewInput
from app.services.creative import CreativeService
from app.models.creative import CreativeReview
from sqlalchemy import select

router = APIRouter(prefix='/creative', tags=['Creative Services'])
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]

def view(row):
    if row is None: return None
    values = {column.key: getattr(row, column.key) for column in inspect(row).mapper.column_attrs}
    return {key: str(value) if isinstance(value, Decimal) else value for key, value in values.items()}

@router.get('/listings')
def listings(session: TransactionSession, offset: Offset=0, limit: Limit=50):
    return [view(row) for row in CreativeService(session).public_listings(offset=offset, limit=limit)]

@router.get('/listings/mine')
def own_listings(user: Seller, session: TransactionSession, offset: Offset=0, limit: Limit=50):
    return [view(row) for row in CreativeService(session).own_listings(user.id, offset=offset, limit=limit)]

@router.get('/provider')
def provider(user: Seller, session: TransactionSession):
    return view(CreativeService(session).provider(user.id))

@router.post('/provider')
def save_provider(payload: ProviderInput, user: Seller, session: TransactionSession):
    return view(CreativeService(session).save_provider(user.id, payload))

@router.post('/listings', status_code=201)
def create_listing(payload: ListingInput, user: Seller, session: TransactionSession):
    return view(CreativeService(session).create_listing(user.id, payload))

@router.patch('/listings/{listing_id}')
def update_listing(listing_id: IdentifierPath, payload: ListingInput, user: Seller, session: TransactionSession):
    return view(CreativeService(session).update_listing(user.id, listing_id, payload))

@router.post('/listings/{listing_id}/resubmit')
def resubmit(listing_id: IdentifierPath, user: Seller, session: TransactionSession):
    return view(CreativeService(session).resubmit(user.id, listing_id))

@router.get('/admin/listings')
def admin_listings(user: Admin, session: TransactionSession, offset: Offset=0, limit: Limit=50):
    return [view(row) for row in CreativeService(session).admin_listings(user.id, offset=offset, limit=limit)]

@router.post('/admin/listings/{listing_id}/moderate')
def moderate(listing_id: IdentifierPath, payload: ModerationInput, user: Admin, session: TransactionSession):
    return view(CreativeService(session).moderate(user.id, listing_id, payload))

@router.post('/listings/{listing_id}/rfqs', status_code=201)
def create_rfq(listing_id: IdentifierPath, payload: RFQInput, user: Buyer, session: TransactionSession):
    return view(CreativeService(session).create_rfq(user.id, listing_id, payload))

@router.get('/rfqs')
def rfqs(user: CurrentUser, session: TransactionSession, offset: Offset=0, limit: Limit=50):
    return [view(row) for row in CreativeService(session).list_rfqs(user.id, offset=offset, limit=limit)]

@router.get('/rfqs/{rfq_id}/responses')
def responses(rfq_id: IdentifierPath, user: CurrentUser, session: TransactionSession):
    return [view(row) for row in CreativeService(session).responses(user.id, rfq_id)]

@router.post('/rfqs/{rfq_id}/responses', status_code=201)
def respond(rfq_id: IdentifierPath, payload: ResponseInput, user: Seller, session: TransactionSession):
    return view(CreativeService(session).respond(user.id, rfq_id, payload))

@router.post('/responses/{response_id}/accept')
def accept(response_id: IdentifierPath, user: Buyer, session: TransactionSession):
    return view(CreativeService(session).accept(user.id, response_id))

@router.get('/engagements')
def engagements(user: CurrentUser, session: TransactionSession, offset: Offset=0, limit: Limit=50):
    rows = CreativeService(session).engagements(user.id, offset=offset, limit=limit)
    ids = [row.id for row in rows]
    reviewed = set(session.scalars(select(CreativeReview.engagement_id).where(CreativeReview.engagement_id.in_(ids)))) if ids else set()
    return [dict(view(row), reviewed=row.id in reviewed) for row in rows]

@router.post('/engagements/{engagement_id}/deliver')
def deliver(engagement_id: IdentifierPath, user: Seller, session: TransactionSession):
    return view(CreativeService(session).deliver(user.id, engagement_id))

@router.post('/engagements/{engagement_id}/complete')
def complete(engagement_id: IdentifierPath, user: Buyer, session: TransactionSession):
    return view(CreativeService(session).complete(user.id, engagement_id))

@router.post('/engagements/{engagement_id}/review')
def review(engagement_id: IdentifierPath, payload: ReviewInput, user: Buyer, session: TransactionSession):
    return view(CreativeService(session).review(user.id, engagement_id, payload))
