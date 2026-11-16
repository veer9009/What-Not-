import time

import jwt
import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services.product_images import delivery_key, signed_image_url, verify_image_token
from app.storage.product_images import managed_reference


def settings(**changes):
    return Settings(_env_file=None, environment='test', jwt_secret_key='image-token-unit-test-'+'x'*40, **changes)


def test_image_capabilities_are_purpose_bound_and_expiring():
    config = settings()
    key = 'a'*32+'.webp'
    url = signed_image_url(managed_reference(key), config)
    token = url.split('?token=')[1]
    assert verify_image_token(key, token, config) == key
    assert url.startswith('http://127.0.0.1:8000/api/v1/product-images/')
    claims = jwt.decode(token, delivery_key(config), algorithms=['HS256'])
    assert set(claims) == {'key', 'purpose', 'exp'}
    assert 0 < claims['exp'] - time.time() <= config.image_url_ttl_seconds
    for changed in [dict(exp=1), dict(purpose='access'), dict(key='b'*32+'.webp')]:
        invalid = jwt.encode({**claims, **changed}, delivery_key(config), algorithm='HS256')
        with pytest.raises(HTTPException) as exc:
            verify_image_token(key, invalid, config)
        assert exc.value.status_code == 404
    from app.core.security import create_access_token
    with pytest.raises(HTTPException) as exc:
        verify_image_token(key, create_access_token(1, config), config)
    assert exc.value.status_code == 404


@pytest.mark.parametrize('token', [None,'','not-a-token','x'*2049])
def test_invalid_image_tokens_are_generic(token):
    with pytest.raises(HTTPException) as exc:
        verify_image_token('a'*32+'.webp', token, settings())
    assert exc.value.status_code == 404
    assert exc.value.detail == 'Image is unavailable'


@pytest.mark.parametrize('origin', ['https://user:secret@images.test','https://images.test/path','https://images.test/?key=private','file:///private'])
def test_delivery_origin_rejects_credentials_paths_and_non_http(origin):
    with pytest.raises(ValueError):
        settings(image_delivery_origin=origin)
