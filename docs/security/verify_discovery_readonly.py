"""Verify existing local discovery records without migrations or database writes.

Run from the repository root with backend/.venv/Scripts/python.exe. Output
contains counts and flags only; neither coordinates nor account identities.
This checks current records, not synthetic write-path integration scenarios.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.schema import EXPECTED_REVISION
from app.models import Address, User
from app.schemas.discovery import DiscoveryQuery
from app.schemas.location import Coordinate
from app.services.discovery import DiscoveryService
from app.services.geography import distance_km, within_radius


def verify():
    settings = Settings()
    url = make_url(settings.database_url.get_secret_value())
    if (url.host not in {'localhost', '127.0.0.1', '::1'}
            or (url.port or 5432) != 5432 or url.query
            or not url.database.startswith('whatnot_')):
        raise RuntimeError('Unexpected local database configuration')
    engine = create_engine(url, hide_parameters=True, connect_args={
        'connect_timeout': 5,
        'options': '-c default_transaction_read_only=on -c statement_timeout=10000',
    })
    try:
        with engine.connect() as connection:
            connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            assert connection.scalar(text('SHOW transaction_read_only')) == 'on'
            revision = connection.scalar(text('SELECT version_num FROM alembic_version'))
            assert revision == EXPECTED_REVISION
            columns = connection.execute(text("""SELECT column_name,numeric_precision,numeric_scale
                FROM information_schema.columns WHERE table_schema='public'
                AND table_name='seller_profiles' AND column_name IN
                ('latitude','longitude','public_discovery_latitude','public_discovery_longitude')""")).all()
            assert len(columns) == 4 and all(tuple(row[1:]) == (9, 6) for row in columns)
            constraints = set(connection.scalars(text("""SELECT conname FROM pg_constraint
                WHERE conrelid='public.seller_profiles'::regclass AND contype='c'""")))
            assert any(name.endswith('public_discovery_fields') for name in constraints)
            inventory = dict(connection.execute(text("""SELECT
                (SELECT count(*) FROM users) AS users,
                (SELECT count(*) FROM seller_profiles) AS sellers,
                (SELECT count(*) FROM products) AS products,
                (SELECT count(*) FROM products WHERE status='APPROVED' AND is_active
                    AND stock_quantity>0) AS approved_active_in_stock,
                (SELECT count(*) FROM seller_profiles WHERE dispatch_location_confirmed_at IS NOT NULL
                    AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180) AS valid_confirmed_dispatch,
                (SELECT count(*) FROM seller_profiles WHERE public_discovery_latitude IS NULL
                    AND public_discovery_longitude IS NULL AND public_discovery_confirmed_at IS NULL
                    AND public_discovery_consent_version IS NULL) AS sellers_without_public_location_consent
                """)).mappings().one())
            with Session(bind=connection, autoflush=False) as session:
                service = DiscoveryService(session, settings)
                candidates, after = [], 0
                while batch := service.repository.discovery_candidates(after, 100):
                    candidates.extend(batch)
                    after = batch[-1].id
                missing_consent = sum(
                    p.seller.public_discovery_latitude is None
                    or p.seller.public_discovery_longitude is None
                    or p.seller.public_discovery_confirmed_at is None
                    or p.seller.public_discovery_consent_version != 'public-discovery-v1'
                    for p in candidates)
                addresses = list(session.scalars(select(Address).join(Address.user).where(
                    User.role == 'BUYER', User.is_active.is_(True))))
                source_checks, nearby_pairs, result_counts = 0, 0, []
                for address in addresses:
                    point = Coordinate(latitude=address.latitude, longitude=address.longitude)
                    nearby_pairs += sum(within_radius(distance_km(point.latitude, point.longitude,
                        p.seller.latitude, p.seller.longitude), p.delivery_radius_km) for p in candidates)
                    for radius in (1, 2, 3):
                        saved = service.list(address.user_id, DiscoveryQuery(address_id=address.id, radius_km=radius))
                        transient = service.list(address.user_id, DiscoveryQuery(location=point, radius_km=radius))
                        assert [p.id for p in saved] == [p.id for p in transient]
                        for view in saved:
                            assert not {'latitude', 'longitude', 'distance_km', 'phone'} & view.model_dump().keys()
                            assert service.get(address.user_id, view.id,
                                DiscoveryQuery(location=point, radius_km=radius)) == view
                        if missing_consent == len(candidates):
                            assert saved == []
                        result_counts.append({'radius_km': radius, 'count': len(saved)})
                        source_checks += 1
                assert connection.scalar(text('SHOW transaction_read_only')) == 'on'
                return {'database': url.database, 'revision': revision, 'read_only': True,
                    'inventory': inventory,
                    'coordinate_schema_check': 'passed', 'public_consent_constraint_check': 'passed',
                    'candidates_before_public_location_checks': len(candidates),
                    'candidates_missing_current_public_consent': missing_consent,
                    'valid_saved_buyer_addresses': len(addresses),
                    'saved_address_transient_equivalence_checks': source_checks,
                    'address_product_pairs_within_private_delivery_radius': nearby_pairs,
                    'discovery_results': result_counts,
                    'coordinates_recorded': False, 'migrations_executed': False}
    finally:
        engine.dispose()


if __name__ == '__main__':
    try:
        result = verify()
    except Exception as error:
        # Driver, ORM and validation errors can contain private parameters.
        print(json.dumps({'status': 'failed', 'error_class': type(error).__name__,
                          'private_details_suppressed': True}))
        raise SystemExit(1)
    report = json.dumps(result, indent=2)
    (ROOT / 'docs/security/evidence/buyer-discovery-readonly.json').write_text(report, encoding='utf-8')
    print(report)
