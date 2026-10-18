from decimal import Decimal

import pytest

from app.services.geography import distance_km, within_radius


@pytest.mark.parametrize('points,expected', [
    ((19, 72, 19, 72), 0),
    ((0, 0, 0, .001), .1111950802),
    ((0, 179.999, 0, -179.999), .2223901605),
    ((90, -180, 90, 180), 0),
    ((0, -180, 0, 180), 0),
    ((Decimal('19'), Decimal('72'), Decimal('19'), Decimal('72')), 0),
])
def test_short_distance_and_longitude_boundaries(points, expected):
    assert distance_km(*points) == pytest.approx(expected, abs=1e-8)


@pytest.mark.parametrize('index,value', [
    (0, 90.000001), (0, -90.000001), (1, 180.000001), (1, -180.000001),
    (2, float('nan')), (3, float('inf')), (0, Decimal('NaN')),
    (1, Decimal('Infinity')), (0, True), (1, '72'), (2, None),
])
def test_invalid_coordinates_are_rejected_without_echo(index, value):
    points = [0, 0, 0, 0]
    points[index] = value
    with pytest.raises(ValueError, match='Invalid coordinate'):
        distance_km(*points)


@pytest.mark.parametrize('radius', [1, 2, 3])
def test_inclusive_boundary_with_only_arithmetic_tolerance(radius):
    assert within_radius(radius, radius)
    assert within_radius(radius - .000001, radius)
    assert within_radius(radius + .0000000005, radius)
    assert not within_radius(radius + .000001, radius)
    assert not within_radius(radius + .000000002, radius)


@pytest.mark.parametrize('distance,radius', [(float('nan'), 1), (float('inf'), 2),
    (-1, 1), (0, True), (0, 1.0), (0, 4), (0, '1')])
def test_invalid_distance_or_radius_rejected(distance, radius):
    with pytest.raises(ValueError):
        within_radius(distance, radius)
