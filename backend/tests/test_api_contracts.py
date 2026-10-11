import pytest


PRODUCT = {"name": "Cotton Tote", "description": "Handwoven bag", "price": "250.00", "stock_quantity": 4, "category": "Fashion", "delivery_radius_km": 2}


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/auth/register", {"name": "Aanya", "email": "aanya@example.com", "password": "example-password", "role": "BUYER"}),
    ("post", "/auth/login", {"email": "aanya@example.com", "password": "example-password"}),
    ("get", "/products", None), ("get", "/products/10", None),
    ("post", "/products", PRODUCT), ("patch", "/products/10", {"stock_quantity": 0}),
    ("patch", "/products/10/activation", {"is_active": False}),
    ("post", "/products/10/resubmit", None),
    ("get", "/orders", None), ("get", "/orders/20", None),
    ("post", "/orders", {"seller_id": 2, "items": [{"product_id": 10, "quantity": 1}]}),
    ("patch", "/orders/20/status", {"status": "ACCEPTED"}),
    ("get", "/admin/products/pending", None),
    ("post", "/admin/products/10/approve", None),
    ("post", "/admin/products/10/reject", {"rejection_reason": "Please use a clearer photo"}),
])
def test_unimplemented_routes_are_honest(client, method, path, payload):
    response = client.request(method, "/api/v1" + path, **({"json": payload} if payload is not None else {}))
    assert response.status_code == 501
    assert "not implemented" in response.json()["detail"].lower()
    assert "token" not in response.json()


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/products", {**PRODUCT, "status": "APPROVED"}),
    ("post", "/products", {**PRODUCT, "delivery_radius_km": 4}),
    ("patch", "/products/10", {"name": None}),
    ("post", "/orders", {"seller_id": "2", "items": [{"product_id": 10, "quantity": 1}]}),
    ("post", "/admin/products/10/reject", {"rejection_reason": "  "}),
    ("patch", "/orders/20/status", {"status": "PAID"}),
])
def test_invalid_contracts_return_validation_errors(client, method, path, payload):
    assert client.request(method, "/api/v1" + path, json=payload).status_code == 422


@pytest.mark.parametrize("path", ["/products/0", "/products/-1", "/products/teddy", "/orders/0", "/orders/9223372036854775808"])
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
    for path, methods in schema["paths"].items():
        if path.endswith("/health"):
            continue
        for operation in methods.values():
            assert "501" in operation["responses"]
            assert "not implemented" in operation["description"].lower()
