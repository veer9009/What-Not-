from datetime import datetime, timezone
from hashlib import sha256
import json
from sqlalchemy import select, func, or_
from app.models.user import User
from app.models.creative import CreativeProvider, CreativeListing, CreativeRFQ, CreativeResponse, CreativeEngagement, CreativeReview
from app.schemas.creative import ProviderInput, ListingInput, RFQInput, ResponseInput, ReviewInput, ModerationInput
from app.services.errors import OwnershipError, ProductNotFound, PersistenceConflict
from app.services.operations import write_operation
from app.services.users import require_user, pagination


class CreativeService:
    def __init__(self, session):
        self.session = session

    def _get(self, model, id, lock=False):
        query = select(model).where(model.id == id).execution_options(populate_existing=True)
        row = self.session.scalar(query.with_for_update() if lock else query)
        if row is None: raise ProductNotFound('Creative record does not exist')
        return row

    def _provider(self, actor, lock=False):
        require_user(self.session, actor, role='SELLER', lock=lock)
        query = select(CreativeProvider).where(CreativeProvider.user_id == actor)
        provider = self.session.scalar(query)
        if provider is None: raise ProductNotFound('Create a provider profile first')
        return provider

    def provider(self, actor):
        require_user(self.session, actor, role='SELLER')
        return self.session.scalar(select(CreativeProvider).where(CreativeProvider.user_id == actor))

    def _listing(self, id, lock=False, available=False):
        listing = self._get(CreativeListing, id, lock)
        provider = self._get(CreativeProvider, listing.provider_id)
        if available:
            require_user(self.session, provider.user_id, role='SELLER', lock=lock)
            if listing.status != 'APPROVED' or not listing.is_active:
                raise PersistenceConflict('Service is unavailable')
        return listing, provider

    def _event(self, recipient, key, kind, id, title, domain='CREATIVE'):
        from app.services.notifications import publish_event
        entity = 'professional' if domain == 'PROFESSIONAL' else 'creative'
        publish_event(self.session, recipient, key, kind, entity, id, title, f'Open {entity.title()} Services to view this update.')

    def _audit(self, actor, engagement, previous):
        from app.models.events import AuditEvent
        self.session.add(AuditEvent(actor_id=actor, action='CREATIVE_TRANSITION', entity_type='creative_engagement', entity_id=engagement.id, previous_status=previous, next_status=engagement.status))

    def _request_values(self, data):
        values = data.model_dump(mode='json', exclude={'request_key'})
        # Canonical validated values let numeric-equivalent money retry identically.
        if 'amount' in values: values['amount'] = format(data.amount, '.2f')
        digest = sha256(json.dumps(values, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        return dict(values, request_key=str(data.request_key), request_fingerprint=digest)

    @write_operation
    def save_provider(self, actor, data):
        data = ProviderInput.model_validate(data)
        require_user(self.session, actor, role='SELLER', lock=True)
        provider = self.provider(actor)
        if provider is None:
            provider = CreativeProvider(user_id=actor, **data.model_dump()); self.session.add(provider)
        else:
            for key, value in data.model_dump().items(): setattr(provider, key, value)
        return provider

    @write_operation
    def create_listing(self, actor, data):
        data = ListingInput.model_validate(data)
        provider = self._provider(actor, True)
        listing = CreativeListing(provider_id=provider.id, **data.model_dump(mode='json'))
        self.session.add(listing)
        return listing

    @write_operation
    def update_listing(self, actor, id, data):
        data = ListingInput.model_validate(data)
        provider = self._provider(actor, True)
        listing, _ = self._listing(id, True)
        if listing.provider_id != provider.id: raise OwnershipError('Not your listing')
        if listing.domain != data.domain: raise PersistenceConflict('Listing domain cannot be changed')
        if listing.status == 'TAKEN_DOWN': raise PersistenceConflict('Admin takedown requires admin review')
        for key, value in data.model_dump(mode='json').items(): setattr(listing, key, value)
        listing.status, listing.rejection_reason = 'PENDING', None
        return listing

    @write_operation
    def resubmit(self, actor, id):
        provider = self._provider(actor, True)
        listing, _ = self._listing(id, True)
        if listing.provider_id != provider.id: raise OwnershipError('Not your listing')
        if listing.status != 'REJECTED': raise PersistenceConflict('Only rejected listings can be resubmitted')
        listing.status, listing.rejection_reason = 'PENDING', None
        return listing

    @write_operation
    def moderate(self, actor, id, data):
        data = ModerationInput.model_validate(data)
        require_user(self.session, actor, role='ADMIN', lock=True)
        listing, provider = self._listing(id, True)
        if data.expected_updated_at is not None and data.expected_updated_at != listing.updated_at:
            raise PersistenceConflict('Listing changed after review; reload and review its current details')
        if listing.status == data.status and listing.rejection_reason == data.reason: return listing
        previous = listing.status
        listing.status, listing.rejection_reason = data.status, data.reason
        from app.models.events import AuditEvent
        self.session.add(AuditEvent(actor_id=actor, action='CREATIVE_MODERATION', entity_type='creative_listing', entity_id=id, previous_status=previous, next_status=data.status, reason=data.reason or 'Approved'))
        self._event(provider.user_id, f'creative:listing:{id}:{data.status}:{listing.updated_at}', 'CREATIVE_MODERATION', id, 'Service listing reviewed', listing.domain)
        return listing

    def _listing_filters(self, query, domain, q=None, category=None, remote=None):
        query = query.where(CreativeListing.domain == domain)
        if q: query = query.where(or_(CreativeListing.title.ilike('%' + q + '%'), CreativeListing.description.ilike('%' + q + '%')))
        if category: query = query.where(CreativeListing.category == category)
        if remote is not None: query = query.where(CreativeListing.remote == remote)
        return query

    def public_listings(self, *, domain='CREATIVE', q=None, category=None, remote=None, offset=0, limit=50):
        offset, limit = pagination(offset, limit)
        query = select(CreativeListing).join(CreativeProvider, CreativeProvider.id == CreativeListing.provider_id).join(User, User.id == CreativeProvider.user_id).where(CreativeListing.status == 'APPROVED', CreativeListing.is_active.is_(True), User.is_active.is_(True))
        return list(self.session.scalars(self._listing_filters(query, domain, q, category, remote).order_by(CreativeListing.id.desc()).offset(offset).limit(limit)))

    def own_listings(self, actor, *, domain='CREATIVE', q=None, category=None, remote=None, offset=0, limit=50):
        offset, limit = pagination(offset, limit)
        provider = self.provider(actor)
        query = select(CreativeListing).where(CreativeListing.provider_id == provider.id) if provider else None
        return [] if query is None else list(self.session.scalars(self._listing_filters(query, domain, q, category, remote).order_by(CreativeListing.id.desc()).offset(offset).limit(limit)))

    def admin_listings(self, actor, *, domain='CREATIVE', q=None, category=None, remote=None, offset=0, limit=50):
        require_user(self.session, actor, role='ADMIN')
        offset, limit = pagination(offset, limit)
        return list(self.session.scalars(self._listing_filters(select(CreativeListing), domain, q, category, remote).order_by(CreativeListing.id.desc()).offset(offset).limit(limit)))

    def listing_view(self, listing):
        from app.api.routes.creative import view
        provider = self._get(CreativeProvider, listing.provider_id)
        count, average = self.session.execute(select(func.count(CreativeReview.id), func.avg(CreativeReview.rating)).select_from(CreativeReview).join(CreativeEngagement, CreativeEngagement.id == CreativeReview.engagement_id).join(CreativeRFQ, CreativeRFQ.id == CreativeEngagement.rfq_id).where(CreativeRFQ.listing_id == listing.id, CreativeEngagement.status == 'COMPLETED')).one()
        return dict(view(listing), provider_name=provider.display_name, provider_verification='NOT_RECORDED', review_count=count, rating_average=str(average) if average is not None else None)

    def dashboard(self, actor, domain):
        provider = self.provider(actor)
        keys = ('active_services', 'pending_approvals', 'new_enquiries', 'submitted_quotations', 'ongoing_projects', 'completed_projects')
        if provider is None: return dict.fromkeys(keys, 0)
        listings = select(CreativeListing.id).where(CreativeListing.provider_id == provider.id, CreativeListing.domain == domain)
        rfqs = select(CreativeRFQ.id).where(CreativeRFQ.listing_id.in_(listings))
        engagements = select(CreativeEngagement.id).where(CreativeEngagement.provider_id == provider.id, CreativeEngagement.rfq_id.in_(rfqs))
        def count(query): return self.session.scalar(select(func.count()).select_from(query.subquery()))
        return dict(active_services=count(select(CreativeListing.id).where(CreativeListing.id.in_(listings), CreativeListing.status == 'APPROVED', CreativeListing.is_active.is_(True))),
                    pending_approvals=count(select(CreativeListing.id).where(CreativeListing.id.in_(listings), CreativeListing.status == 'PENDING')),
                    new_enquiries=count(select(CreativeRFQ.id).where(CreativeRFQ.id.in_(rfqs), ~select(CreativeResponse.id).where(CreativeResponse.rfq_id == CreativeRFQ.id).exists())),
                    submitted_quotations=count(select(CreativeResponse.id).where(CreativeResponse.rfq_id.in_(rfqs))),
                    ongoing_projects=count(select(CreativeEngagement.id).where(CreativeEngagement.id.in_(engagements), CreativeEngagement.status.in_(('ACCEPTED', 'DELIVERED')))),
                    completed_projects=count(select(CreativeEngagement.id).where(CreativeEngagement.id.in_(engagements), CreativeEngagement.status == 'COMPLETED')))

    def reviews(self, actor, domain):
        provider = self.provider(actor)
        if provider is None: return []
        rows = self.session.execute(select(CreativeReview, CreativeRFQ.listing_id).join(CreativeEngagement, CreativeEngagement.id == CreativeReview.engagement_id).join(CreativeRFQ, CreativeRFQ.id == CreativeEngagement.rfq_id).join(CreativeListing, CreativeListing.id == CreativeRFQ.listing_id).where(CreativeEngagement.provider_id == provider.id, CreativeEngagement.status == 'COMPLETED', CreativeListing.domain == domain).order_by(CreativeReview.id.desc())).all()
        return [dict(id=r.id, engagement_id=r.engagement_id, listing_id=listing_id, rating=r.rating, comment=r.text, created_at=r.created_at) for r, listing_id in rows]

    @write_operation
    def create_rfq(self, actor, id, data):
        data = RFQInput.model_validate(data)
        require_user(self.session, actor, role='BUYER', lock=True)
        values = self._request_values(data)
        existing = self.session.scalar(select(CreativeRFQ).where(CreativeRFQ.buyer_id == actor, CreativeRFQ.listing_id == id, CreativeRFQ.request_key == values['request_key']))
        if existing:
            if existing.request_fingerprint != values['request_fingerprint']:
                raise PersistenceConflict('Request key already belongs to different enquiry details')
            return existing
        _, owner = self._listing(id)
        require_user(self.session, owner.user_id, role='SELLER', lock=True)
        listing, provider = self._listing(id, True, True)
        if provider.user_id == actor: raise OwnershipError('Cannot enquire on your own listing')
        rfq = CreativeRFQ(listing_id=id, buyer_id=actor, **values)
        self.session.add(rfq); self.session.flush()
        self._event(provider.user_id, f'creative:rfq:{rfq.id}', 'CREATIVE_RFQ', rfq.id, 'New service enquiry', listing.domain)
        return rfq

    def _rfq_owner(self, actor, rfq, role):
        listing, provider = self._listing(rfq.listing_id)
        expected = rfq.buyer_id if role == 'BUYER' else provider.user_id
        if expected != actor: raise OwnershipError('Not your enquiry')
        return listing, provider

    @write_operation
    def respond(self, actor, id, data):
        data = ResponseInput.model_validate(data)
        require_user(self.session, actor, role='SELLER', lock=True)
        rfq = self._get(CreativeRFQ, id, True)
        listing, provider = self._rfq_owner(actor, rfq, 'SELLER')
        values = self._request_values(data)
        existing = self.session.scalar(select(CreativeResponse).where(CreativeResponse.rfq_id == id, CreativeResponse.request_key == values['request_key']))
        if existing:
            if existing.request_fingerprint != values['request_fingerprint']:
                raise PersistenceConflict('Request key already belongs to different quote details')
            return existing
        self._listing(listing.id, True, True)
        if self.session.scalar(select(CreativeEngagement.id).where(CreativeEngagement.rfq_id == id)):
            raise PersistenceConflict('Accepted terms cannot change')
        response = CreativeResponse(rfq_id=id, **values)
        self.session.add(response); self.session.flush()
        self._event(rfq.buyer_id, f'creative:response:{response.id}', 'CREATIVE_RESPONSE', id, 'Service provider responded', listing.domain)
        return response

    @write_operation
    def accept(self, actor, response_id):
        require_user(self.session, actor, role='BUYER', lock=True)
        response = self._get(CreativeResponse, response_id)
        preliminary = self._get(CreativeRFQ, response.rfq_id)
        self._rfq_owner(actor, preliminary, 'BUYER')
        _, owner = self._listing(preliminary.listing_id)
        # Lock the provider account before enquiry/listing, matching seller writes.
        # Availability is checked again after the replay branch under these locks.
        require_user(self.session, owner.user_id, role='SELLER', active=False, lock=True)
        rfq = self._get(CreativeRFQ, response.rfq_id, True)
        self._rfq_owner(actor, rfq, 'BUYER')
        existing = self.session.scalar(select(CreativeEngagement).where(CreativeEngagement.rfq_id == rfq.id))
        if existing:
            if existing.response_id != response_id: raise PersistenceConflict('Different terms already accepted')
            return existing
        listing, provider = self._listing(rfq.listing_id, True, True)
        engagement = CreativeEngagement(rfq_id=rfq.id, response_id=response.id, buyer_id=actor, provider_id=provider.id, title=listing.title, terms=response.terms, amount=response.amount, currency=response.currency)
        self.session.add(engagement); self.session.flush()
        self._audit(actor, engagement, None)
        self._event(provider.user_id, f'creative:accepted:{engagement.id}', 'CREATIVE_ACCEPTED', engagement.id, 'Service quote accepted', listing.domain)
        return engagement

    def list_rfqs(self, actor, *, domain='CREATIVE', offset=0, limit=50):
        user = require_user(self.session, actor)
        offset, limit = pagination(offset, limit)
        query = select(CreativeRFQ).join(CreativeListing, CreativeListing.id == CreativeRFQ.listing_id).where(CreativeListing.domain == domain)
        if user.role == 'BUYER': query = query.where(CreativeRFQ.buyer_id == actor)
        elif user.role == 'SELLER': query = query.join(CreativeProvider, CreativeProvider.id == CreativeListing.provider_id).where(CreativeProvider.user_id == actor)
        elif user.role != 'ADMIN': raise OwnershipError('Not permitted')
        return list(self.session.scalars(query.order_by(CreativeRFQ.id.desc()).offset(offset).limit(limit)))

    def responses(self, actor, id):
        user = require_user(self.session, actor)
        rfq = self._get(CreativeRFQ, id)
        if user.role != 'ADMIN': self._rfq_owner(actor, rfq, user.role)
        return list(self.session.scalars(select(CreativeResponse).where(CreativeResponse.rfq_id == id).order_by(CreativeResponse.id.desc()).limit(100)))

    def engagements(self, actor, *, domain='CREATIVE', offset=0, limit=50):
        user = require_user(self.session, actor)
        offset, limit = pagination(offset, limit)
        query = select(CreativeEngagement).join(CreativeRFQ, CreativeRFQ.id == CreativeEngagement.rfq_id).join(CreativeListing, CreativeListing.id == CreativeRFQ.listing_id).where(CreativeListing.domain == domain)
        if user.role == 'BUYER': query = query.where(CreativeEngagement.buyer_id == actor)
        elif user.role == 'SELLER': query = query.join(CreativeProvider, CreativeProvider.id == CreativeEngagement.provider_id).where(CreativeProvider.user_id == actor)
        elif user.role != 'ADMIN': raise OwnershipError('Not permitted')
        return list(self.session.scalars(query.order_by(CreativeEngagement.id.desc()).offset(offset).limit(limit)))

    @write_operation
    def deliver(self, actor, id):
        require_user(self.session, actor, role='SELLER', lock=True)
        engagement = self._get(CreativeEngagement, id, True)
        if self._get(CreativeProvider, engagement.provider_id).user_id != actor: raise OwnershipError('Not your engagement')
        if engagement.status in ('DELIVERED', 'COMPLETED'): return engagement
        engagement.status, engagement.delivered_at = 'DELIVERED', datetime.now(timezone.utc)
        self._audit(actor, engagement, 'ACCEPTED')
        listing = self._get(CreativeListing, self._get(CreativeRFQ, engagement.rfq_id).listing_id)
        self._event(engagement.buyer_id, f'creative:delivered:{id}', 'CREATIVE_DELIVERED', id, 'Confirm service delivery', listing.domain)
        return engagement

    @write_operation
    def complete(self, actor, id):
        require_user(self.session, actor, role='BUYER', lock=True)
        engagement = self._get(CreativeEngagement, id, True)
        if engagement.buyer_id != actor: raise OwnershipError('Not your engagement')
        if engagement.status == 'COMPLETED': return engagement
        if engagement.status != 'DELIVERED': raise PersistenceConflict('Provider must mark delivered first')
        engagement.status, engagement.completed_at = 'COMPLETED', datetime.now(timezone.utc)
        self._audit(actor, engagement, 'DELIVERED')
        provider = self._get(CreativeProvider, engagement.provider_id)
        listing = self._get(CreativeListing, self._get(CreativeRFQ, engagement.rfq_id).listing_id)
        self._event(provider.user_id, f'creative:completed:{id}', 'CREATIVE_COMPLETED', id, 'Buyer confirmed completion', listing.domain)
        return engagement

    @write_operation
    def review(self, actor, id, data):
        data = ReviewInput.model_validate(data)
        require_user(self.session, actor, role='BUYER', lock=True)
        engagement = self._get(CreativeEngagement, id, True)
        if engagement.buyer_id != actor or self._get(CreativeProvider, engagement.provider_id).user_id == actor: raise OwnershipError('Not your completed engagement')
        if engagement.status != 'COMPLETED': raise PersistenceConflict('Buyer confirmation required')
        existing = self.session.scalar(select(CreativeReview).where(CreativeReview.engagement_id == id))
        if existing:
            if existing.rating != data.rating or existing.text != data.text: raise PersistenceConflict('Engagement already reviewed')
            return existing
        review = CreativeReview(engagement_id=id, buyer_id=actor, **data.model_dump())
        self.session.add(review)
        return review
