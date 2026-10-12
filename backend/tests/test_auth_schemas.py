import secrets

import pytest
from pydantic import ValidationError

from app.schemas.auth import UserRegistration, LoginRequest
from app.schemas.user import PublicUserResponse

PASSWORD = secrets.token_urlsafe(24)


def test_registration_and_login_contracts_do_not_expose_password_in_repr():
    user = UserRegistration(name="  Aanya  ", email="aanya@example.com", phone="1234567890", password=PASSWORD, role="BUYER")
    assert user.name == "Aanya"
    assert PASSWORD not in repr(user)
    assert LoginRequest(email=user.email, password=PASSWORD).password.get_secret_value() == PASSWORD


@pytest.mark.parametrize("changes", [{"name": " "}, {"email": "invalid"}, {"password": secrets.token_hex(2)}, {"role": "ADMIN"}, {"id": 1}])
def test_registration_rejects_invalid_or_privileged_fields(changes):
    data = {"name": "Aanya", "email": "aanya@example.com", "phone": "1234567890", "password": PASSWORD, "role": "BUYER", **changes}
    with pytest.raises(ValidationError):
        UserRegistration(**data)


def test_public_user_has_integer_id_and_never_contains_password():
    data = {"id": 1, "name": "Aanya", "email": "aanya@example.com", "role": "BUYER"}
    assert "password" not in PublicUserResponse(**data).model_dump()
    for changes in [{"id": "1"}, {"id": True}, {"id": 0}, {"password": PASSWORD}]:
        with pytest.raises(ValidationError):
            PublicUserResponse(**{**data, **changes})


def test_password_whitespace_is_preserved_and_length_checks_still_apply():
    password = ' ' + secrets.token_urlsafe(24) + ' '
    registration = UserRegistration(name='Ravi', email='ravi@example.com', phone='phone', password=password)
    assert registration.password.get_secret_value() == password
    assert LoginRequest(email=registration.email, password=password).password.get_secret_value() == password
    for value in [secrets.token_hex(2), 'x' * 129]:
        with pytest.raises(ValidationError):
            UserRegistration(name='Ravi', email='ravi@example.com', phone='phone', password=value)
