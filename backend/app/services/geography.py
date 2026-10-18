"""Small numeric geography primitives; never log or echo submitted coordinates."""
from decimal import Decimal
import math

EARTH_RADIUS_KM = 6371.0088
BOUNDARY_TOLERANCE_KM = 1e-9


def _coordinate(value, bound):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError('Invalid coordinate')
    if not math.isfinite(value) or not -bound <= value <= bound:
        raise ValueError('Invalid coordinate')
    return float(value)


def distance_km(latitude_a, longitude_a, latitude_b, longitude_b) -> float:
    lat_a = math.radians(_coordinate(latitude_a, 90))
    lon_a = math.radians(_coordinate(longitude_a, 180))
    lat_b = math.radians(_coordinate(latitude_b, 90))
    lon_b = math.radians(_coordinate(longitude_b, 180))
    haversine = (math.sin((lat_b - lat_a) / 2) ** 2
                 + math.cos(lat_a) * math.cos(lat_b) * math.sin((lon_b - lon_a) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, max(0.0, haversine))))


def within_radius(distance: float, radius: int) -> bool:
    if type(radius) is not int or radius not in (1, 2, 3):
        raise ValueError('Invalid delivery radius')
    if isinstance(distance, bool) or not isinstance(distance, (float, int)) or not math.isfinite(distance) or distance < 0:
        raise ValueError('Invalid distance')
    return distance <= radius + BOUNDARY_TOLERANCE_KM
