from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from app.api.dependencies import get_transaction_session
from app.core.config import Settings
from app.main import create_app
from app.models import Product
from app.models.property import PropertyListing
from test_authorization import bearer
from test_authentication import auth_client
from test_discovery import available
from app.services.properties import PropertyService
from app.schemas.property import PropertyProfileInput


def test_product_search_precedes_eligible_pagination(auth_client, available, db):
    p = available['product']
    p.name = 'Unrelated'
    for name, description, status in [('Needle one', 'x', 'APPROVED'), ('Needle hidden', 'x', 'PENDING'), ('Other', 'needle two', 'APPROVED')]:
        db.add(Product(seller_id=p.seller_id, name=name, description=description, price=1,
                       stock_quantity=1, category='Crafts', delivery_radius_km=3, status=status))
    db.flush()
    body = {'location': {'latitude': 19.076, 'longitude': 72.8777}, 'q': 'NEEDLE', 'offset': 1, 'limit': 1}
    response = auth_client.post('/api/v1/discovery/products', json=body, headers=bearer(available['buyer'].id))
    assert response.status_code == 200
    assert [item['name'] for item in response.json()] == ['Other']
    assert auth_client.post('/api/v1/discovery/products', json={**body, 'q': 'x' * 121}, headers=bearer(available['buyer'].id)).status_code == 422
    available['seller'].public_discovery_confirmed_at = None
    available['seller'].public_discovery_latitude = None
    available['seller'].public_discovery_longitude = None
    available['seller'].public_discovery_consent_version = None
    db.flush()
    assert auth_client.post('/api/v1/discovery/products', json=body, headers=bearer(available['buyer'].id)).json() == []


def test_property_search_precedes_pagination_and_respects_publication(db, records):
    now = datetime.now(timezone.utc)
    PropertyService(db).profile(records['seller_user'], PropertyProfileInput(display_name='Owner', capacity='OWNER'))
    def add(title, description='plain', status='APPROVED', expires=None):
        p = PropertyListing(creator_id=records['seller_user'].id, capacity='OWNER', title=title,
            description=description, category='Residential', price=100, locality='Pune',
            private_address='hidden address', status=status, reconfirmed_at=now,
            expires_at=expires or now + timedelta(days=1))
        db.add(p)
        db.flush()
        return p
    first = add('Needle first')
    add('Needle expired', expires=now-timedelta(days=1))
    add('Needle pending', status='PENDING')
    add('Other', 'needle description')
    add('Unrelated')
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_transaction_session] = lambda: db
    with TestClient(app) as client:
        result = client.get('/api/v1/properties', params={'q': 'NEEDLE', 'offset': 1, 'limit': 1, 'locality': 'Pune', 'category': 'Residential'})
        assert result.status_code == 200
        assert [item['id'] for item in result.json()] == [first.id]
        assert 'hidden address' not in result.text
        assert client.get('/api/v1/properties', params={'q': 'x' * 121}).status_code == 422
