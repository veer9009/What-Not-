"""Prove seller-supported discovery points read-only; never emit locations/IDs."""
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.models import User
from app.schemas.discovery import DiscoveryQuery
from app.schemas.location import Coordinate
from app.services.discovery import DiscoveryService
from inspect_discovery_inventory import locality_center, distance_km


def verify():
    url = make_url(Settings().database_url.get_secret_value())
    if (url.database != 'whatnot_app_dev' or url.host not in {'localhost','127.0.0.1','::1'}
            or (url.port or 5432) != 5432 or url.query):
        raise RuntimeError('STOP: unexpected protected local target')
    engine = create_engine(url, hide_parameters=True, connect_args={
        'options': '-c default_transaction_read_only=on -c statement_timeout=10000'})
    try:
        with Session(engine) as session, session.begin():
            session.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
            identity = session.execute(text("""SELECT current_database(),oid FROM pg_database
                WHERE datname=current_database()""")).one()
            if tuple(identity) != ('whatnot_app_dev',41069):
                raise RuntimeError('STOP: database identity mismatch')
            if session.scalar(text('SHOW transaction_read_only')) != 'on':
                raise RuntimeError('STOP: read-only protection unavailable')
            if session.scalar(text('SELECT version_num FROM public.alembic_version')) != '0008':
                raise RuntimeError('STOP: schema revision mismatch')
            actor = session.scalar(select(User.id).where(User.role=='BUYER',User.is_active.is_(True)).order_by(User.id))
            if actor is None:
                raise RuntimeError('STOP: no active buyer for read-only service verification')
            service = DiscoveryService(session)
            candidates = service.repository.discovery_candidates(0,100)
            # Only the observed three-product inventory is within this proof.
            if len(candidates) != 3 or session.scalar(text('SELECT count(*) FROM public.products')) != 3:
                raise RuntimeError('STOP: observed inventory changed; review before proceeding')
            sellers = {product.seller_id:product.seller for product in candidates}
            result_counts = []
            own_product_checks = []
            for seller_id,seller in sellers.items():
                # A private dispatch point remains solely in process memory.
                # This is an authorized read-only service probe, not a test fixture.
                query = DiscoveryQuery(location=Coordinate(latitude=seller.latitude,longitude=seller.longitude))
                found = service.list(actor,query)
                diagnostic_ids = {product.id for product in candidates
                    if distance_km(query.location.latitude,query.location.longitude,
                        *locality_center(product.seller.latitude,product.seller.longitude))
                    <= product.delivery_radius_km + .8}
                if diagnostic_ids != {product.id for product in found}:
                    raise RuntimeError('STOP: diagnostic and production membership differ')
                result_counts.append(len(found))
                own = {product.id for product in candidates if product.seller_id==seller_id}
                own_product_checks.append(own.issubset({product.id for product in found}))
            if not result_counts or not all(own_product_checks) or min(result_counts)<1:
                raise RuntimeError('STOP: seller-supported positive discovery did not qualify')
            return {'captured_at_utc':datetime.now(timezone.utc).isoformat(),
                'database':identity[0],'oid':identity[1],'revision':'0008','read_only':True,
                'eligible_before_locality':len(candidates),'seller_supported_points_checked':len(sellers),
                'points_returning_products':sum(count>0 for count in result_counts),
                'minimum_results_at_supported_point':min(result_counts),
                'maximum_results_at_supported_point':max(result_counts),
                'all_own_eligible_products_returned':all(own_product_checks),
                'diagnostic_matches_service_at_supported_points':True,
                'coordinates_or_record_ids_emitted':False,'api_requests_sent':0}
    finally:
        engine.dispose()


if __name__=='__main__':
    try:
        result=verify()
        (Path(__file__).parent/'evidence/locality-supported-points.json').write_text(
            json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
            'message':str(error) if type(error) is RuntimeError else 'Private inputs suppressed'}))
        raise SystemExit(1)
