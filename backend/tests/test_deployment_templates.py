"""Static/template security contracts; these do not claim nginx runtime validation."""
import importlib.util
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def renderer():
    spec = importlib.util.spec_from_file_location('pilot_nginx_renderer', ROOT / 'deploy/render_nginx.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nginx_render_preserves_api_prefix_and_required_access_tls_boundaries():
    rendered = renderer().render_nginx('pilot.example.test', '/reviewed/fullchain.pem',
        '/reviewed/privkey.pem', '/opt/whatnot/current/frontend', '/etc/nginx/pilot-access.conf')
    assert '@@' not in rendered
    assert 'proxy_pass http://127.0.0.1:8000;' in rendered
    assert 'proxy_pass http://127.0.0.1:8000/;' not in rendered
    assert 'ssl_certificate /reviewed/fullchain.pem;' in rendered
    assert 'include /etc/nginx/pilot-access.conf;' in rendered
    assert 'try_files $uri $uri/ /index.html;' in rendered
    assert 'X-Forwarded-For $remote_addr;' in rendered
    assert '$proxy_add_x_forwarded_for' not in rendered
    assert 'client_max_body_size 256k;' in rendered
    assert 'geolocation=(self)' in rendered


@pytest.mark.parametrize('values', [
    ('pilot.example.test; return 200', '/tls/cert', '/tls/key', '/www', '/acl'),
    ('pilot.example.test', '/tls/cert; include /private', '/tls/key', '/www', '/acl'),
    ('pilot.example.test', '/tls/cert', '/tls/key', 'relative/path', '/acl'),
    ('pilot.example.test', '/tls/cert', '/tls/key', '/www', '/acl\nallow all;'),
])
def test_nginx_renderer_rejects_configuration_injection(values):
    with pytest.raises(ValueError):
        renderer().render_nginx(*values)


def test_default_pilot_access_is_fail_closed_and_api_is_loopback_only():
    access = (ROOT / 'deploy/nginx/pilot-access.conf.example').read_text(encoding='utf-8')
    assert 'deny all;' in access and 'allow all;' not in access
    service = (ROOT / 'deploy/systemd/whatnot-api.service').read_text(encoding='utf-8')
    assert '--host 127.0.0.1' in service
    assert '--forwarded-allow-ips=127.0.0.1' in service
    assert 'User=whatnot' in service and 'NoNewPrivileges=true' in service
    assert 'ConditionPathExists=!/etc/whatnot/maintenance' in service
    worker = (ROOT / 'deploy/systemd/whatnot-worker@.service').read_text(encoding='utf-8')
    assert 'ConditionPathExists=!/etc/whatnot/maintenance' in worker
    assert 'app.workers %i' in worker


def test_operator_migration_safety_checks_survive_python_optimization():
    doc = (ROOT / 'docs/PRODUCTION_BACKUP_RECOVERY.md').read_text(encoding='utf-8')
    code = doc.split(".venv/bin/python - <<'PY'\n", 1)[1].split('\nPY', 1)[0]
    tree = ast.parse(code)
    assert not any(isinstance(node, ast.Assert) for node in ast.walk(tree)), 'Operational safety gates must not use optimizable assert'
