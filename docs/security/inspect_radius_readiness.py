"""Read-only approved QA schema inspection; no migrations or application writes."""
import json
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import create_engine, text
from app.schemas.discovery import DiscoveryQuery
from app.services.geography import distance_km, within_radius
from run_chrome_discovery_qa import target, preflight, require, IDENTITY, QA


def main():
    url, oid = target()
    require(oid == 50640, 'Unapproved QA OID')
    state = preflight(url, oid)
    engine = create_engine(url, hide_parameters=True, connect_args={
        'options': '-c default_transaction_read_only=on -c statement_timeout=5000'})
    try:
        with engine.connect() as connection:
            require(tuple(connection.execute(text(IDENTITY)).one()) == (QA, oid, True),
                    'QA identity mismatch')
            require(connection.scalar(text('SHOW transaction_read_only')) == 'on', 'Not read-only')
            columns = list(connection.scalars(text("""SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='seller_profiles' ORDER BY ordinal_position""")))
    finally:
        engine.dispose()
    validation = []
    for radius in (1, 2, 3):
        try:
            DiscoveryQuery.model_validate({'location': {'latitude': 0, 'longitude': 0}, 'radius_km': radius})
        except ValidationError as error:
            validation.append({'radius_km': radius, 'accepted': False,
                               'categories': sorted({item['type'] for item in error.errors()})})
        else:
            validation.append({'radius_km': radius, 'accepted': True})
    # Synthetic points only: exact membership reveals which private point exists
    # inside one currently indistinguishable cell. No real location is inspected.
    inference = []
    for radius, origin in [(1, -.005), (2, -.012), (3, -.020)]:
        distances = [distance_km(0, origin, point, point) for point in (.001, .009)]
        inference.append({'radius_km': radius, 'synthetic_distances_km': distances,
                          'exact_membership': [within_radius(d, radius) for d in distances]})
    result = {'qa_preflight': state, 'read_only': True,
              'seller_location_columns': [c for c in columns if any(s in c for s in
                                         ('latitude', 'longitude', 'location', 'consent'))],
              'current_radius_contract': validation, 'synthetic_inference_demonstration': inference,
              'migrations_run': False, 'business_writes': False}
    (Path(__file__).parent / 'evidence/live-radius-readiness.json').write_text(
        json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'status': 'STOP', 'exception_class': type(error).__name__,
                          'message': str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}))
        raise SystemExit(1)
