from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from app.schemas.property import PropertyCreate, VisitCreate

def test_sale_listing_rejects_mass_assignment():
    with pytest.raises(ValidationError):
        PropertyCreate(title='House', description='Home', category='Residential', price='500', locality='Pune', private_address='1 Private Street', status='APPROVED')

def test_visits_require_future_aware_datetime():
    for value in [datetime.now(), datetime.now(timezone.utc)-timedelta(days=1)]:
        with pytest.raises(ValidationError):
            VisitCreate(scheduled_at=value)
