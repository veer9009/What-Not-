"""Explicit seller consent to an inferable public business discovery point."""
from typing import Annotated, Literal
from pydantic import Field, field_validator
from app.schemas.location import Coordinate

PUBLIC_DISCOVERY_CONSENT_VERSION = 'public-discovery-v1'


class PublicDiscoveryConfirmation(Coordinate):
    consent: Annotated[bool, Field(strict=True)]
    consent_version: Literal['public-discovery-v1']

    @field_validator('consent')
    @classmethod
    def require_consent(cls, value):
        if value is not True:
            raise ValueError('Explicit public-location consent is required')
        return value
