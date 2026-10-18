import pytest
from pydantic import ValidationError

from app.schemas.discovery import DiscoveryQuery, DiscoverySource


@pytest.mark.parametrize('payload', [{}, {'address_id': 1, 'location': {'latitude': 0, 'longitude': 0}},
    {'address_id': '1'}, {'address_id': True}, {'address_id': 0}, {'address_id': None},
    {'location': {'latitude': 91, 'longitude': 0}}, {'location': {'latitude': 0, 'longitude': 181}},
    {'location': {'latitude': 'NaN', 'longitude': 0}}, {'location': {'latitude': 0}},
    {'location': {'latitude': 0, 'longitude': 0}, 'user_id': 1}])
def test_discovery_requires_one_valid_source(payload):
    with pytest.raises(ValidationError):
        DiscoverySource.model_validate(payload)


@pytest.mark.parametrize('patch', [{'offset': -1}, {'offset': True}, {'limit': 0}, {'limit': 101}, {'limit': '10'}])
def test_discovery_pagination_is_bounded(patch):
    with pytest.raises(ValidationError):
        DiscoveryQuery.model_validate({'address_id': 1, **patch})


def test_source_and_defaults():
    assert DiscoverySource(address_id=1).address_id == 1
    query = DiscoveryQuery(location={'latitude': 0, 'longitude': -180})
    assert query.offset == 0 and query.limit == 100
