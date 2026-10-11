import pytest
from pydantic import ValidationError

from app.schemas.auth import UserRegistration, LoginRequest
from app.schemas.user import PublicUserResponse


def test_registration_and_login_contracts_do_not_expose_password_in_repr():
    user = UserRegistration(name="  Aanya  ", email="aanya@example.com", password="example-password", role="BUYER")
    assert user.name == "Aanya"
    assert "example-password" not in repr(user)
    assert LoginRequest(email=user.email, password="example-password").password.get_secret_value() == "example-password"


@pytest.mark.parametrize("changes", [{"name": " "}, {"email": "invalid"}, {"password": "short"}, {"role": "ADMIN"}, {"id": 1}])
def test_registration_rejects_invalid_or_privileged_fields(changes):
    data = {"name": "Aanya", "email": "aanya@example.com", "password": "example-password", "role": "BUYER", **changes}
    with pytest.raises(ValidationError):
        UserRegistration(**data)


def test_public_user_has_integer_id_and_never_contains_password():
    data = {"id": 1, "name": "Aanya", "email": "aanya@example.com", "role": "BUYER"}
    assert "password" not in PublicUserResponse(**data).model_dump()
    for changes in [{"id": "1"}, {"id": True}, {"id": 0}, {"password": "secret"}]:
        with pytest.raises(ValidationError):
            PublicUserResponse(**{**data, **changes})
