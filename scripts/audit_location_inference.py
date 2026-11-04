"""Offline synthetic diagnostic: no network, credentials, or application data.

Run from repository root with backend/.venv/Scripts/python.exe
scripts/audit_location_inference.py. Reproduces the historical exact-distance
contract and checks the current locality implementation. No real seller is queried.
"""
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from app.services.geography import EARTH_RADIUS_KM, distance_km


def main():
    # Fabricated equatorial point; never load a seller or application configuration.
    hidden = (0.004321, 0.005678)
    origins = ((0, 0), (0.01, 0), (0, 0.01))
    observations = [round(distance_km(*origin, *hidden), 2) for origin in origins]
    baseline = math.radians(0.01) * EARTH_RADIUS_KM
    north = (observations[0]**2 - observations[1]**2 + baseline**2) / (2 * baseline)
    east = (observations[0]**2 - observations[2]**2 + baseline**2) / (2 * baseline)
    estimated = (math.degrees(north / EARTH_RADIUS_KM), math.degrees(east / EARTH_RADIUS_KM))
    print('Historical exact-distance synthetic inference error (metres):', round(distance_km(*hidden, *estimated) * 1000, 2))
    print('All synthetic observation points within 1 km:',
          all(distance_km(*origin, *hidden) <= 1 for origin in origins))
    from types import SimpleNamespace
    from decimal import Decimal
    from app.services.discovery import DiscoveryService
    from app.schemas.location import Coordinate
    def product(point):
        return SimpleNamespace(id=1,seller_id=2,name='Synthetic',description='Offline',price='10.00',
            stock_quantity=1,category='Crafts',delivery_radius_km=1,images=[],
            seller=SimpleNamespace(latitude=Decimal(point),longitude=Decimal(point),shop_name='Synthetic',is_verified=False))
    service=DiscoveryService(None)
    for origin in ['-.025','-.015','-.005','0','.005','.015','.025','.035']:
        source=Coordinate(latitude=0,longitude=origin)
        views=[service._eligible_view(product(point),source) for point in ['.001','.009']]
        outputs=[view.model_dump() if view is not None else None for view in views]
        assert outputs[0]==outputs[1]
        assert all(output is None or not {'distance_km','latitude','longitude'} & output.keys() for output in outputs)
    print('Current locality regression: PASS (8 probe origins; same-cell private points indistinguishable).')
    print('Residual: exact checkout decisions remain a bounded oracle; admission and durable quotas mitigate, not eliminate, inference.')


if __name__ == '__main__':
    main()
