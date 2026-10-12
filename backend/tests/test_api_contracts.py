import pytest


PRODUCT = {"name": "Cotton Tote", "description": "Handwoven bag", "price": "250.00", "stock_quantity": 4, "category": "Fashion", "delivery_radius_km": 2}


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/products", None), ("get", "/products/10", None),
    ("post", "/orders", {"seller_id": 2, "items": [{"product_id": 10, "quantity": 1}]}),
])
def test_unimplemented_routes_are_honest(client, method, path, payload):
    response = client.request(method, "/api/v1" + path, **({"json": payload} if payload is not None else {}))
    assert response.status_code == 501
    assert "not implemented" in response.json()["detail"].lower()
    assert "token" not in response.json()


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/orders", {"seller_id": "2", "items": [{"product_id": 10, "quantity": 1}]}),
])
def test_invalid_contracts_return_validation_errors(client, method, path, payload):
    assert client.request(method, "/api/v1" + path, json=payload).status_code == 422


@pytest.mark.parametrize("path", ["/products/0", "/products/-1", "/products/teddy", "/products/9223372036854775808"])
def test_path_ids_must_fit_positive_bigint(client, path):
    assert client.get("/api/v1" + path).status_code == 422


def test_openapi_exposes_contracts_and_documents_placeholders(client):
    schema = client.get("/openapi.json").json()
    models = schema["components"]["schemas"]
    assert models["ProductResponse"]["properties"]["id"]["type"] == "integer"
    assert models["OrderCreate"]["properties"]["seller_id"]["type"] == "integer"
    assert set(models["ProductStatus"]["enum"]) == {"PENDING", "APPROVED", "REJECTED"}
    assert set(models["OrderStatus"]["enum"]) == {"PLACED", "ACCEPTED", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED", "REJECTED"}
    assert "status" not in models["ProductCreate"]["properties"]
    placeholders = {('/api/v1/products', 'get'), ('/api/v1/products/{product_id}', 'get'), ('/api/v1/orders', 'post')}
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if (path, method) in placeholders:
                assert '501' in operation['responses']
                assert 'not implemented' in operation['description'].lower()
            elif path != '/api/v1/health' and path not in {'/api/v1/auth/register', '/api/v1/auth/login'}:
                assert operation['security'] == [{'HTTPBearer': []}]


def test_unknown_property_names_cannot_echo_secrets_in_validation(client):
    secret = 'secret-password-in-property-name'
    response = client.post('/api/v1/orders', json={'seller_id': 1,
        'items': [{'product_id': 1, 'quantity': 1}], secret: 'value'})
    assert response.status_code == 422
    assert secret not in response.text
