"""Validated coordinate source shared by dispatch and discovery adapters."""
from app.schemas.common import ContractModel
from app.services.inputs import Latitude, Longitude


class Coordinate(ContractModel):
    latitude: Latitude
    longitude: Longitude
