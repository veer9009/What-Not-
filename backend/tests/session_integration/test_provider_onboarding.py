"""Synthetic users only; existing SELLER/CreativeProvider and moderation boundary."""
from uuid import uuid4
import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.core.config import Settings
from app.core.security import hash_password
from app.main import create_app
from app.models import User
from app.models.creative import CreativeProvider
from app.schemas.auth import UserRegistration
from app.schemas.creative import ListingInput, ModerationInput, ProviderInput
from app.services.auth import AuthService
from app.services.creative import CreativeService
from app.services.errors import DuplicateUser, InvalidRole


@pytest.mark.parametrize('category', ['VFX', 'Video Editing', 'Travel Video Editing', 'Influencer Reel Editing'])
def test_provider_creation_requires_seller_and_listing_review(session_engine, category):
    with Session(session_engine) as session, session.begin():
        service = AuthService(session)
        seller = service.register(UserRegistration(name='Synthetic creator', email=uuid4().hex+'@example.com',
            phone=uuid4().hex, password='synthetic password', role='SELLER'))
        buyer = service.register(UserRegistration(name='Synthetic buyer', email=uuid4().hex+'@example.com',
            phone=uuid4().hex, password='synthetic password', role='BUYER'))
        admin = User(name='Synthetic reviewer', email=uuid4().hex+'@example.com', phone=uuid4().hex,
                     role='ADMIN', password_hash=hash_password('synthetic password'))
        session.add(admin);session.flush()
        creative = CreativeService(session)
        profile = creative.save_provider(seller.id, ProviderInput(display_name='Studio', bio='Portfolio and experience'))
        assert creative.save_provider(seller.id, ProviderInput(display_name='Studio', bio='Updated')).id == profile.id
        with pytest.raises(InvalidRole):
            creative.save_provider(buyer.id, ProviderInput(display_name='Buyer', bio='No silent enrollment'))
        assert buyer.role == 'BUYER'
        assert not session.scalar(select(CreativeProvider).where(CreativeProvider.user_id == buyer.id))
        listing = creative.create_listing(seller.id, ListingInput(title='Synthetic service', description='Synthetic scope',
            category=category, pricing='QUOTATION', remote=True, portfolio=['https://example.com/portfolio']))
        assert listing.status == 'PENDING' and listing.id not in {item.id for item in creative.public_listings()}
        with pytest.raises(InvalidRole):
            creative.moderate(seller.id, listing.id, ModerationInput(status='APPROVED', expected_updated_at=listing.updated_at))
        creative.moderate(admin.id, listing.id, ModerationInput(status='APPROVED', expected_updated_at=listing.updated_at))
        assert listing.id in {item.id for item in creative.public_listings()}
        with pytest.raises(DuplicateUser):
            service.register(UserRegistration(name='Duplicate', email=seller.email, phone=uuid4().hex,
                password='synthetic password', role='SELLER'))


def test_http_provider_access_keeps_roles_and_admin_boundary(session_engine):
    settings = Settings(_env_file=None, environment='test', jwt_secret_key=secrets.token_urlsafe(48), abuse_limits_enabled=False)
    app = create_app(settings)
    def reader():
        with Session(session_engine) as session:
            yield session
    app.dependency_overrides[get_session] = reader
    headers = {'Origin':'https://testserver', 'X-WhatNot-CSRF':'1'}
    with TestClient(app, base_url='https://testserver') as client:
        email=uuid4().hex+'@example.com'
        registered=client.post('/api/v1/auth/register', headers=headers, json={'name':'Synthetic buyer',
            'email':email,'phone':uuid4().hex,'password':'synthetic password','role':'BUYER'})
        assert registered.status_code == 201
        login=client.post('/api/v1/auth/login', headers=headers, json={'email':email,'password':'synthetic password'})
        assert login.status_code == 200
        authorization={'Authorization':'Bearer '+login.json()['access_token']}
        assert client.post('/api/v1/creative/provider',headers={**headers, **authorization},
            json={'display_name':'No elevation','bio':'Synthetic'}).status_code == 403
        assert client.get('/api/v1/creative/admin/listings',headers=authorization).status_code == 403
        assert client.get('/api/v1/auth/me',headers=authorization).json()['role'] == 'BUYER'
