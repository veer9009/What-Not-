"""Local nginx template contracts; no server, storage, or database is used."""
from pathlib import Path
import re

import pytest


TEMPLATE = Path(__file__).resolve().parents[2] / "deploy/nginx/whatnot.conf.template"


def test_image_policy_allows_local_object_url_previews():
    config = TEMPLATE.read_text(encoding="utf-8")
    policy = re.search(r'add_header Content-Security-Policy "([^"]+)" always;', config)[1]
    directives = dict(part.strip().split(" ", 1) for part in policy.split(";") if part.strip())
    assert directives["img-src"].split() == ["'self'", "https:", "data:", "blob:"]
    assert {key: value for key, value in directives.items() if key != "img-src"} == {
        "default-src": "'self'", "script-src": "'self'",
        "style-src": "'self' 'unsafe-inline'", "connect-src": "'self'",
        "font-src": "'self'", "object-src": "'none'", "base-uri": "'self'",
        "frame-ancestors": "'none'", "form-action": "'self'",
    }


def api_location(path):
    config = TEMPLATE.read_text(encoding="utf-8")
    # nginx checks regular-expression locations before the ordinary /api/ prefix.
    for match in re.finditer(r"location ~ (\S+) \{([^{}]*)\}", config):
        if re.search(match[1], path):
            return match[2]
    return re.search(r"location /api/ \{([^{}]*)\}", config)[1]


@pytest.mark.parametrize("path", [
    "/api/v1/products/1/images",
    "/api/v1/products/123/images/456/replace",
])
def test_image_upload_and_replacement_accept_raw_five_mib(path):
    # The frontend sends the File itself, so there is no multipart overhead.
    assert "client_max_body_size 5m;" in api_location(path)


@pytest.mark.parametrize("path", [
    "/api/v1/products", "/api/v1/auth/login",
    "/api/v1/products/1/images/2/remove", "/api/v1/products/1/images/2/primary",
    "/api/v1/products/0/images", "/api/v1/products/-1/images",
    "/api/v1/products/1/images/0/replace", "/api/v1/products/1/images/-2/replace",
    "/api/v1/products/1/images/2/replace/extra", "/api/v1/products/1/images-extra",
    "/api/v1/products/1/images/.hidden", "/api/v1/product-images/abc.webp",
])
def test_unrelated_paths_do_not_gain_a_larger_body_limit(path):
    assert "client_max_body_size" not in api_location(path)
    assert "client_max_body_size 256k;" in TEMPLATE.read_text(encoding="utf-8")


@pytest.mark.parametrize("path", [
    "/api/v1/products/1/images", "/api/v1/products/1/images/2/replace",
])
def test_upload_locations_preserve_api_proxy_and_inherited_controls(path):
    location = api_location(path)
    assert "limit_req zone=whatnot_pilot burst=30 nodelay;" in location
    assert "limit_req_status 429;" in location
    assert "proxy_pass http://127.0.0.1:8000;" in location
    # Defining even one local proxy header would discard all server headers.
    assert "proxy_set_header" not in location
    assert "allow " not in location and "deny " not in location
    assert "proxy_read_timeout" not in location
    config = TEMPLATE.read_text(encoding="utf-8")
    tls_server = config.rsplit("server {", 1)[1].split("location = /api", 1)[0]
    for directive in [
        "include @@PILOT_ACCESS_FILE@@;", "client_body_timeout 10s;",
        "proxy_set_header Host $host;", "proxy_set_header X-Real-IP $remote_addr;",
        "proxy_set_header X-Forwarded-For $remote_addr;",
        "proxy_set_header X-Forwarded-Proto $scheme;",
        "proxy_set_header X-Request-ID $request_id;", 'proxy_set_header Connection "";',
        "proxy_connect_timeout 5s;", "proxy_read_timeout 30s;",
        "proxy_send_timeout 30s;", "proxy_http_version 1.1;",
    ]:
        assert directive in tls_server
