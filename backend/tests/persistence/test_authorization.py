import time

import jwt
import pytest
from sqlalchemy import select

from app.models import User
from test_authentication import auth_client, register, login, SECRET, PASSWORD


def bearer(user_id, **claims):
    token = jwt.encode(dict(sub=str(user_id), iat=int(time.time()),
                            exp=int(time.time()) + 900, **claims), SECRET, algorithm='HS256')
    return {'Authorization': f'Bearer {token}'}


def test_database_role_overrides_forged_token_role(auth_client, db, records):
    headers = bearer(records['buyer'].id, role='ADMIN')
    assert auth_client.get('/api/v1/admin/products/pending', headers=headers).status_code == 403
    assert auth_client.patch(f"/api/v1/products/{records['product'].id}",
                             json={'name': 'Stolen'}, headers=headers).status_code == 403
    assert records['product'].name == 'Handmade vase'


@pytest.mark.parametrize('actor', ['buyer', 'seller_user'])
def test_nonadmins_cannot_moderate(auth_client, records, actor):
    headers = bearer(records[actor].id)
    assert auth_client.get('/api/v1/admin/products/pending', headers=headers).status_code == 403
    assert auth_client.post(f"/api/v1/admin/products/{records['product'].id}/approve",
                            headers=headers).status_code == 403


def test_seller_cannot_modify_another_sellers_product(auth_client, records):
    register(auth_client)
    headers = {'Authorization': 'Bearer ' + login(auth_client).json()['access_token']}
    product_id = records['product'].id
    for method, suffix, data in [('patch', '', {'name': 'Stolen'}),
                                ('patch', '/activation', {'is_active': False}),
                                ('post', '/resubmit', None)]:
        response = auth_client.request(method, f'/api/v1/products/{product_id}{suffix}',
                                      headers=headers, **({'json': data} if data else {}))
        assert response.status_code == 403
    assert records['product'].name == 'Handmade vase'
    assert records['product'].is_active


def test_own_address_only_and_actor_body_rejected(auth_client, records):
    headers = bearer(records['seller_user'].id)
    address_id = records['address'].id
    assert auth_client.get(f'/api/v1/addresses/{address_id}', headers=headers).status_code == 403
    assert auth_client.patch(f'/api/v1/addresses/{address_id}', headers=headers,
                             json={'label': 'Stolen'}).status_code == 403
    assert auth_client.post(f'/api/v1/addresses/{address_id}/default', headers=headers).status_code == 403
    headers = bearer(records['buyer'].id)
    assert auth_client.patch(f'/api/v1/addresses/{address_id}', headers=headers,
                             json={'label': 'New', 'user_id': records['seller_user'].id}).status_code == 422


@pytest.mark.parametrize('role', ['BUYER', 'SELLER'])
def test_unrelated_buyer_and_seller_cannot_read_or_transition_orders(auth_client, records, role):
    order_id = records['order'].id
    registered = register(auth_client, role=role)
    headers = bearer(registered.json()['id'])
    assert auth_client.get(f'/api/v1/orders/{order_id}', headers=headers).status_code == 403
    assert auth_client.patch(f'/api/v1/orders/{order_id}/status', headers=headers,
                             json={'status': 'CANCELLED'}).status_code == 403
    response = auth_client.get('/api/v1/orders', headers=headers)
    assert response.status_code == (200 if role == 'BUYER' else 404)
    if role == 'BUYER':
        assert response.json() == []


def test_admin_moderation_and_seller_order_workflow(auth_client, db, records):
    admin = User(name='Admin', email='admin@example.com', phone='admin',
                 password_hash='test-only-hash', role='ADMIN')
    db.add(admin)
    db.flush()
    headers = bearer(admin.id)
    queue = auth_client.get('/api/v1/admin/products/pending', headers=headers)
    assert queue.status_code == 200
    product_id = records['product'].id
    assert queue.json()[0]['id'] == product_id
    assert auth_client.post(f'/api/v1/admin/products/{product_id}/approve', headers=headers).status_code == 200
    seller = bearer(records['seller_user'].id)
    updated = auth_client.patch(f'/api/v1/products/{product_id}', headers=seller, json={'name': 'Own edit'})
    assert updated.status_code == 200 and updated.json()['status'] == 'PENDING'
    assert auth_client.post(f'/api/v1/admin/products/{product_id}/reject', headers=headers,
                           json={'rejection_reason': 'Fix image'}).status_code == 200
    assert auth_client.post(f'/api/v1/products/{product_id}/resubmit', headers=seller).status_code == 200
    order_id = records['order'].id
    assert auth_client.get('/api/v1/orders', headers=seller).json()[0]['id'] == order_id
    assert auth_client.patch(f'/api/v1/orders/{order_id}/status', headers=seller,
                            json={'status': 'ACCEPTED'}).status_code == 200
    buyer = bearer(records['buyer'].id)
    assert auth_client.patch(f'/api/v1/orders/{order_id}/status', headers=buyer,
                            json={'status': 'PREPARING'}).status_code == 403
    assert auth_client.patch(f'/api/v1/orders/{order_id}/status', headers=buyer,
                            json={'status': 'CANCELLED'}).status_code == 200
    assert auth_client.patch(f'/api/v1/orders/{order_id}/status', headers=buyer,
                            json={'status': 'CANCELLED'}).status_code == 409


def test_changed_database_role_and_activity_take_effect(auth_client, db, records):
    headers = bearer(records['seller_user'].id)
    product_id = records['product'].id
    records['seller_user'].role = 'BUYER'
    db.flush()
    assert auth_client.patch(f'/api/v1/products/{product_id}', headers=headers,
                             json={'name': 'Edit'}).status_code == 403
    records['seller_user'].is_active = False
    db.flush()
    assert auth_client.patch(f'/api/v1/products/{product_id}', headers=headers,
                             json={'name': 'Edit'}).status_code == 401


@pytest.mark.parametrize('claims,algorithm,key', [
    ({'exp': 1}, 'HS256', SECRET), ({'iat': 9999999999}, 'HS256', SECRET),
    ({'exp': None}, 'HS256', SECRET), ({'sub': '0'}, 'HS256', SECRET),
    ({'sub': '-1'}, 'HS256', SECRET), ({'sub': '9223372036854775808'}, 'HS256', SECRET),
    ({'sub': 'not-id'}, 'HS256', SECRET), ({'sub': 1}, 'HS256', SECRET),
    ({'sub': '999999'}, 'HS256', SECRET), ({}, 'HS256', 'wrong-key-' + 'y' * 40),
    ({}, 'HS384', SECRET),
])
def test_jwt_invalid_claims_signature_algorithm_and_nonexistent_user(auth_client, records, claims, algorithm, key):
    payload = {'sub': str(records['buyer'].id), 'iat': int(time.time()), 'exp': int(time.time()) + 900, **claims}
    token = jwt.encode(payload, key, algorithm=algorithm)
    response = auth_client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401


@pytest.mark.parametrize('missing', ['sub', 'iat', 'exp'])
def test_jwt_requires_each_claim(auth_client, missing):
    claims = {'sub': '1', 'iat': int(time.time()), 'exp': int(time.time()) + 900}
    del claims[missing]
    token = jwt.encode(claims, SECRET, algorithm='HS256')
    assert auth_client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_token_contains_only_identity_and_time_claims(auth_client):
    register(auth_client)
    token = login(auth_client).json()['access_token']
    claims = jwt.decode(token, SECRET, algorithms=['HS256'])
    assert set(claims) == {'sub', 'iat', 'exp'}
    assert claims['exp'] - claims['iat'] == 900


def test_complete_seller_profile_and_product_creation(auth_client):
    register(auth_client)
    headers = {'Authorization': 'Bearer ' + login(auth_client).json()['access_token']}
    assert auth_client.get('/api/v1/sellers/me', headers=headers).status_code == 404
    profile = dict(shop_name='Ravi Crafts', phone='9000000001', latitude='19.076000', longitude='72.877700')
    assert auth_client.post('/api/v1/sellers/me', headers=headers, json=profile).status_code == 201
    assert auth_client.post('/api/v1/sellers/me', headers=headers, json=profile).status_code == 409
    assert auth_client.patch('/api/v1/sellers/me', headers=headers, json={'is_verified': True}).status_code == 422
    assert auth_client.patch('/api/v1/sellers/me', headers=headers, json={'shop_name': 'New shop'}).status_code == 200
    product = dict(name='Vase', description='Clay vase', price='250.00', stock_quantity=5,
                   category='Crafts', delivery_radius_km=2)
    created = auth_client.post('/api/v1/products', headers=headers, json=product)
    assert created.status_code == 201
    assert created.json()['status'] == 'PENDING'
    assert auth_client.get('/api/v1/sellers/me/products', headers=headers).json()[0]['id'] == created.json()['id']
    assert auth_client.post('/api/v1/products', headers=headers, json={**product, 'seller_id': 1}).status_code == 422


def test_own_address_workflow_and_order_history_preservation(auth_client, records):
    headers = bearer(records['buyer'].id)
    payload = dict(label='New home', address_line1='2 Test Lane', city='Mumbai', state='Maharashtra',
                   pincode='400001', latitude='19.070000', longitude='72.870000', is_default=True)
    response = auth_client.post('/api/v1/addresses', headers=headers, json=payload)
    assert response.status_code == 201
    address_id = response.json()['id']
    assert response.json()['user_id'] == records['buyer'].id
    assert auth_client.get(f'/api/v1/addresses/{address_id}', headers=headers).status_code == 200
    assert auth_client.patch(f'/api/v1/addresses/{address_id}', headers=headers,
                            json={'label': 'Updated'}).status_code == 200
    assert auth_client.post(f"/api/v1/addresses/{records['address'].id}/default", headers=headers).status_code == 200
    addresses = auth_client.get('/api/v1/addresses', headers=headers).json()
    assert sum(address['is_default'] for address in addresses) == 1
    assert auth_client.patch(f"/api/v1/addresses/{records['address'].id}", headers=headers,
                            json={'city': 'Delhi'}).status_code == 409
    assert records['address'].city == 'Mumbai'


@pytest.mark.parametrize('method,path,payload', [
    ('post', '/products', {'name': 'Vase', 'description': 'Vase', 'price': '250.00',
                         'stock_quantity': 4, 'category': 'Crafts', 'delivery_radius_km': 4}),
    ('patch', '/products/1', {'name': None}),
    ('post', '/admin/products/1/reject', {'rejection_reason': '  '}),
    ('patch', '/orders/1/status', {'status': 'PAID'}),
])
def test_authenticated_invalid_contracts_return_422(auth_client, db, records, method, path, payload):
    user = records['seller_user']
    if path.startswith('/admin'):
        user.role = 'ADMIN'
        db.flush()
    response = auth_client.request(method, '/api/v1' + path, headers=bearer(user.id), json=payload)
    assert response.status_code == 422
    assert all('input' not in error for error in response.json()['detail'])


@pytest.mark.parametrize('path', ['/orders/0', '/orders/9223372036854775808', '/addresses/-1'])
def test_authenticated_invalid_path_ids_return_422(auth_client, records, path):
    assert auth_client.get('/api/v1' + path, headers=bearer(records['buyer'].id)).status_code == 422


def test_missing_resource_returns_404(auth_client, records):
    headers = bearer(records['seller_user'].id)
    assert auth_client.patch('/api/v1/products/999999', headers=headers, json={'name': 'Edit'}).status_code == 404
    assert auth_client.get('/api/v1/orders/999999', headers=headers).status_code == 404
    assert auth_client.get('/api/v1/addresses/999999', headers=headers).status_code == 404


@pytest.mark.parametrize('method,path,payload', [
    ('get', '/admin/products/pending', None), ('post', '/admin/products/1/approve', None),
    ('post', '/admin/products/1/reject', {'rejection_reason': 'Fix'}),
    ('post', '/products', {}), ('patch', '/products/1', {'name': 'Edit'}),
    ('patch', '/products/1/activation', {'is_active': False}), ('post', '/products/1/resubmit', None),
    ('get', '/orders', None), ('get', '/orders/1', None),
    ('patch', '/orders/1/status', {'status': 'CANCELLED'}),
    ('get', '/addresses', None), ('post', '/addresses', {}), ('get', '/addresses/1', None),
    ('patch', '/addresses/1', {'label': 'Edit'}), ('post', '/addresses/1/default', None),
    ('get', '/sellers/me', None), ('post', '/sellers/me', {}),
    ('patch', '/sellers/me', {'shop_name': 'Edit'}), ('get', '/sellers/me/products', None),
])
def test_every_protected_route_rejects_missing_auth_without_storage(client, method, path, payload):
    response = client.request(method, '/api/v1' + path, **({'json': payload} if payload is not None else {}))
    assert response.status_code == 401
    assert client.app.state.database_engine is None
