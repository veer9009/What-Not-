import pytest


@pytest.mark.parametrize('method,path', [
    ('get','/api/v1/products/1/images'),
    ('post','/api/v1/products/1/images'),
    ('post','/api/v1/products/1/images/2/replace'),
    ('post','/api/v1/products/1/images/2/remove'),
    ('post','/api/v1/products/1/images/2/primary'),
])
def test_image_management_rejects_unauthenticated_before_storage(client, method, path):
    response = client.request(method, path, content=b'synthetic')
    assert response.status_code == 401
    assert client.app.state.database_engine is None


def test_image_delivery_requires_a_capability_before_storage(client):
    response = client.get('/api/v1/product-images/' + 'a'*32 + '.webp')
    assert response.status_code == 404
    assert client.app.state.database_engine is None
