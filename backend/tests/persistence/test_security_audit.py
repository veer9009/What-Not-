"""Bounded attacker-input checks using only the isolated PostgreSQL fixture."""
from sqlalchemy import func, select

from app.models import Product, User
from test_authentication import auth_client  # noqa: F401
from test_authorization import bearer


def test_sql_like_product_text_is_stored_as_data(auth_client, db, records):
    text = "Audit ' OR '1'='1 -- <script>synthetic</script>"
    users_before = db.scalar(select(func.count()).select_from(User))
    response = auth_client.patch(
        f"/api/v1/products/{records['product'].id}",
        headers=bearer(records['seller_user'].id), json={'name': text})
    assert response.status_code == 200
    assert response.json()['name'] == text
    assert db.get(Product, records['product'].id).name == text
    assert db.scalar(select(func.count()).select_from(User)) == users_before
    # API JSON storing text is safe; browser escaping is reviewed separately.


def test_sql_like_order_identifier_is_rejected(auth_client, records):
    response = auth_client.get('/api/v1/orders/1%20OR%201%3D1',
                              headers=bearer(records['buyer'].id))
    assert response.status_code == 422
    assert 'traceback' not in response.text.lower()
    assert 'SELECT' not in response.text


def test_client_cannot_add_payment_state_or_authoritative_totals(auth_client, records):
    response = auth_client.post('/api/v1/orders',
        headers={**bearer(records['buyer'].id),
                 'Idempotency-Key': 'a7777777-7777-4777-8777-777777777777'},
        json={'seller_id': records['seller'].id, 'address_id': records['address'].id,
              'items': [{'product_id': records['product'].id, 'quantity': 1,
                         'expected_unit_price': '250.00'}],
              'total_amount': '0.01', 'payment_status': 'PAID'})
    assert response.status_code == 422
    assert records['product'].stock_quantity == 5


def test_invalid_registration_does_not_echo_submitted_secrets(auth_client):
    marker = 'synthetic-audit-password-never-a-real-credential'
    response = auth_client.post('/api/v1/auth/register', json={
        'name': 'Audit', 'email': 'audit@example.com', 'phone': 'audit-only',
        'password': marker, 'role': 'ADMIN'})
    assert response.status_code == 422
    assert marker not in response.text
    assert all('input' not in issue and 'ctx' not in issue
               for issue in response.json()['detail'])


def test_no_upload_route_accepts_a_synthetic_file(auth_client):
    response = auth_client.post('/api/v1/uploads',
                               files={'file': ('audit.txt', b'synthetic only', 'text/plain')})
    assert response.status_code == 404
