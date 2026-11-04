import pytest
from sqlalchemy import select, func
from app.models import User
from app.models.events import AuditEvent
from test_authentication import auth_client
from test_authorization import bearer


@pytest.fixture
def administrator(db):
    user=User(name='Operator',email='operator@example.com',phone='admin-beta',password_hash='test',role='ADMIN')
    db.add(user);db.flush();return user


def test_normal_buyer_cannot_use_admin_operational_routes(auth_client,records):
    headers=bearer(records['buyer'].id)
    for path in ['/admin/users','/admin/orders','/admin/audit','/admin/operations']:
        assert auth_client.get('/api/v1'+path,headers=headers).status_code==403


def test_admin_suspension_is_audited_and_blocks_existing_tokens(auth_client,db,records,administrator):
    headers=bearer(administrator.id)
    response=auth_client.patch(f"/api/v1/admin/users/{records['buyer'].id}/active",headers=headers,
                              json={'is_active':False,'reason':'Investigated beta abuse'})
    assert response.status_code==200
    assert response.json()['is_active'] is False
    assert 'password_hash' not in response.text
    assert auth_client.get('/api/v1/auth/me',headers=bearer(records['buyer'].id)).status_code==401
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='USER_SUSPENDED'))==1


def test_admin_account_changes_require_reason_and_cannot_mass_assign_role(auth_client,records,administrator):
    path=f"/api/v1/admin/users/{records['buyer'].id}/active"
    headers=bearer(administrator.id)
    assert auth_client.patch(path,headers=headers,json={'is_active':False,'reason':'  '}).status_code==422
    assert auth_client.patch(path,headers=headers,json={'is_active':False,'reason':'Case','role':'ADMIN'}).status_code==422
    assert records['buyer'].is_active


def test_private_admin_reads_require_reason_and_leave_audit(auth_client,db,records,administrator):
    headers=bearer(administrator.id)
    path=f"/api/v1/admin/orders/{records['order'].id}/fulfillment"
    assert auth_client.post(path,headers=headers,json={'reason':' '}).status_code==422
    response=auth_client.post(path,headers=headers,json={'reason':'Delivery investigation'})
    assert response.status_code==200
    assert 'latitude' not in response.text and 'longitude' not in response.text
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='FULFILLMENT_READ'))==1


def test_product_approval_rejects_content_edited_after_admin_review(auth_client,db,records,administrator):
    product=records['product']
    reviewed_at=product.updated_at.isoformat()
    product.name='New content not yet reviewed'
    db.flush()
    response=auth_client.post(f'/api/v1/admin/products/{product.id}/approve',headers=bearer(administrator.id),
        json={'expected_updated_at':reviewed_at})
    assert response.status_code==409
    assert product.status=='PENDING'
