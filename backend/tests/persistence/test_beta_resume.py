"""Interrupted-branch regressions and head migration verification."""
from datetime import datetime, timedelta, timezone
from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text, select, func
from conftest import migration_config
from app.models.events import AuditEvent
from test_authentication import auth_client


def test_0008_populated_upgrade_metadata_roundtrip_and_verified_refusal(fresh_database_url):
    config = migration_config(fresh_database_url)
    command.upgrade(config, '0007')
    engine = create_engine(fresh_database_url)
    try:
        with engine.begin() as connection:
            uid = connection.scalar(text("INSERT INTO users(name,email,phone,password_hash,role) VALUES('Existing','existing@example.test','resume-user','hash','BUYER') RETURNING id"))
        command.upgrade(config, '0008')
        command.check(config)
        with engine.connect() as connection:
            assert connection.execute(text('SELECT phone_verified_at,email_verified_at FROM users WHERE id=:id'), {'id': uid}).one() == (None, None)
        command.downgrade(config, '0007')
        assert 'request_quotas' not in inspect(engine).get_table_names()
        command.upgrade(config, 'head')
        command.check(config)
        with engine.begin() as connection:
            connection.execute(text('UPDATE users SET phone_verified_at=now() WHERE id=:id'), {'id': uid})
        with pytest.raises(RuntimeError, match='verification history'):
            command.downgrade(config, '0007')
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT version_num FROM alembic_version')) == '0008'
            assert connection.scalar(text('SELECT phone_verified_at FROM users WHERE id=:id'), {'id': uid}) is not None
    finally:
        engine.dispose()


def test_property_expiry_is_bounded_notifies_once_and_preserves_confirmed_visits(db, records):
    from test_properties import listing
    from app.models.property import PropertyVisit
    from app.services.properties import PropertyService
    service, seller, buyer, prop = listing(db, records)
    prop.status = 'APPROVED'
    visit = PropertyVisit(property_id=prop.id,buyer_id=buyer.id,scheduled_at=datetime.now(timezone.utc)+timedelta(days=2),status='CONFIRMED')
    db.add(visit)
    prop.expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
    db.flush()
    assert PropertyService(db).expire_due(limit=1) == 1
    db.flush()
    assert visit.status == 'CONFIRMED'
    assert PropertyService(db).expire_due(limit=1) == 0
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='PROPERTY_EXPIRED')) == 1


def test_readiness_checks_schema_and_reports_backlog_without_pii(auth_client):
    response = auth_client.get('/api/v1/ready')
    assert response.status_code == 200
    assert response.json()['schema'] == '0008'
    assert isinstance(response.json()['outbox_pending'], int)
    assert not any(word in response.text for word in ['password', 'email@', 'postgresql://'])


@pytest.mark.parametrize('action',['PROPOSE','REJECT'])
def test_suspended_past_visit_can_be_rescheduled_or_rejected(db,records,action):
    from test_properties import listing
    from app.models.property import PropertyVisit
    from app.schemas.property import VisitAction
    service,seller,buyer,prop=listing(db,records)
    prop.status='APPROVED'
    visit=PropertyVisit(property_id=prop.id,buyer_id=buyer.id,status='SUSPENDED',
        scheduled_at=datetime.now(timezone.utc)-timedelta(days=1))
    db.add(visit);db.flush()
    future=datetime.now(timezone.utc)+timedelta(days=1)
    service.visit_action(seller,visit.id,VisitAction(action=action,scheduled_at=future if action=='PROPOSE' else None))
    assert visit.status==('ALTERNATE' if action=='PROPOSE' else 'REJECTED')
    if action=='PROPOSE':
        assert visit.scheduled_at==future
        service.visit_action(buyer,visit.id,VisitAction(action='ACCEPT_ALTERNATE'))
        assert visit.status=='CONFIRMED'


def test_private_api_responses_are_not_cached(auth_client,records):
    from test_authorization import bearer
    for path in ['/notifications','/notifications/unread-count','/orders']:
        response=auth_client.get('/api/v1'+path,headers=bearer(records['buyer'].id))
        assert response.status_code==200
        assert response.headers.get('cache-control')=='no-store'


def test_http_discovery_probes_cannot_distinguish_private_points_in_one_cell(auth_client,db,records):
    from test_authorization import bearer
    records['product'].status='APPROVED'
    records['seller'].dispatch_location_confirmed_at=datetime.now(timezone.utc)
    headers=bearer(records['buyer'].id)
    for origin in [-.025,-.015,-.005,0,.005,.015,.025,.035]:
        observations=[]
        for point in [.001,.009]:
            records['seller'].latitude=point;records['seller'].longitude=point;db.flush()
            response=auth_client.post('/api/v1/discovery/products',headers=headers,
                json={'location':{'latitude':0,'longitude':origin}})
            assert response.status_code==200
            for product in response.json():
                assert not {'distance_km','latitude','longitude'} & product.keys()
            observations.append(response.json())
        assert observations[0]==observations[1]
