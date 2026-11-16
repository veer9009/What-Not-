from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services.products import set_primary_image
from app.services.product_images import signed_image_url
from app.storage.product_images import managed_reference


def test_legacy_primary_url_echo_keeps_the_managed_attachment():
    settings = Settings(_env_file=None, environment='test', jwt_secret_key='compatibility-test-'+'x'*40)
    reference = managed_reference('a'*32+'.webp')
    primary = SimpleNamespace(is_primary=True, image_url=reference)
    product = SimpleNamespace(images=[primary])
    set_primary_image(product, signed_image_url(reference, settings), settings)
    assert primary.image_url == reference
    from pydantic import HttpUrl
    settings.image_delivery_origin = 'https://IMAGES.EXAMPLE:443'
    normalized = HttpUrl(signed_image_url(reference, settings))
    set_primary_image(product, normalized, settings)
    assert primary.image_url == reference
    # An external URL, even with the same path, remains an ordinary hosted URL.
    external = 'https://external.example/api/v1/product-images/'+'a'*32+'.webp'
    set_primary_image(product, external, settings)
    assert primary.image_url == external


def test_legacy_api_cannot_add_a_sixth_non_primary_image():
    product = SimpleNamespace(images=[SimpleNamespace(is_primary=False) for _ in range(5)])
    with pytest.raises(HTTPException) as exc:
        set_primary_image(product, 'https://example.test/new.png')
    assert exc.value.status_code == 409
    assert len(product.images) == 5
