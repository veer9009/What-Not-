"""Live browser smoke test using the existing isolated PostgreSQL harness only.

Run with backend/.venv Python, Node 24+ and an installed Chrome/Chromium browser.
Only the generated test DATABASE_URL is used. No credential artifacts are written.
"""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import shutil
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'backend'
sys.path.insert(0, str(BACKEND))
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.core.security import hash_password
from app.services.inputs import UserCreate
from app.services.users import UserService


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def ready(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Owned test server exited before startup')
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(.1)
    raise RuntimeError('Owned test server did not become ready')


def main():
    browser = Path(os.environ.get('WHATNOT_BROWSER_EXECUTABLE', r'C:\Program Files\Google\Chrome\Application\chrome.exe'))
    if not browser.is_file():
        raise SystemExit('Set WHATNOT_BROWSER_EXECUTABLE to an installed Chrome/Chromium browser')
    spec = importlib.util.spec_from_file_location('phase7_isolated_harness', BACKEND / 'tests/persistence/conftest.py')
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    cluster = harness.isolated_cluster.__wrapped__()
    processes = []
    browser_profile = Path(tempfile.mkdtemp(prefix='whatnot-phase7-browser-')).resolve()
    try:
        connection = next(cluster)
        url = harness.fresh_database_url.__wrapped__(connection)
        assert url.database.startswith('whatnot_test_')
        assert url.database not in {'whatnot_db', 'upsc_compass'}
        command.upgrade(harness.migration_config(url), 'head')
        admin_password = secrets.token_urlsafe(24)
        engine = create_engine(url)
        try:
            with Session(engine) as session, session.begin():
                UserService(session).create(UserCreate(name='Test administrator', email='admin.phase7@example.com', phone='phase7-admin', password_hash=hash_password(admin_password), role='ADMIN'))
        finally:
            engine.dispose()
        api_port, ui_port = free_port(), free_port()
        while ui_port == api_port:
            ui_port = free_port()
        env = os.environ.copy()
        # Explicit values override all possible application settings; the app is
        # constructed with _env_file=None in the owned server subprocess below.
        env['DATABASE_URL'] = url.render_as_string(hide_password=False)
        env['WHAT_NOT_JWT_SECRET_KEY'] = secrets.token_urlsafe(48)
        env['WHAT_NOT_ENVIRONMENT'] = 'test'
        env['WHAT_NOT_JWT_ALGORITHM'] = 'HS256'
        env['WHAT_NOT_ACCESS_TOKEN_EXPIRE_MINUTES'] = '15'
        env['WHAT_NOT_CORS_ORIGINS'] = json.dumps([f'http://127.0.0.1:{ui_port}'])
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        with (ROOT / 'phase7-browser-servers.log').open('w', encoding='utf-8') as log:
            server_code = 'from app.main import create_app; from app.core.config import Settings; import uvicorn; uvicorn.run(create_app(Settings(_env_file=None)),host="127.0.0.1",port=' + str(api_port) + ',access_log=False)'
            processes.append(subprocess.Popen([sys.executable, '-c', server_code], cwd=BACKEND, env=env, stdout=log, stderr=log, creationflags=flags))
            processes.append(subprocess.Popen(['node', str(ROOT / 'node_modules/vite/bin/vite.js'), 'preview', '--host', '127.0.0.1', '--port', str(ui_port), '--strictPort'], cwd=ROOT, env=env, stdout=log, stderr=log, creationflags=flags))
            ready(f'http://127.0.0.1:{api_port}/api/v1/health', processes[0])
            ready(f'http://127.0.0.1:{ui_port}', processes[1])
            browser_port = free_port()
            processes.append(subprocess.Popen([str(browser), '--headless=new', '--no-first-run', '--disable-gpu',
                '--disable-background-networking', '--disable-component-update',
                '--remote-debugging-address=127.0.0.1', f'--remote-debugging-port={browser_port}',
                f'--user-data-dir={browser_profile}', 'about:blank'], stdout=log, stderr=log, creationflags=flags))
            ready(f'http://127.0.0.1:{browser_port}/json/version', processes[-1])
            with urlopen(f'http://127.0.0.1:{browser_port}/json/list') as response:
                targets = json.load(response)
            page_socket = next(t['webSocketDebuggerUrl'] for t in targets if t['type'] == 'page')
            data = {'ws': page_socket, 'ui': f'http://127.0.0.1:{ui_port}', 'api': f'http://127.0.0.1:{api_port}', 'password': secrets.token_urlsafe(24), 'adminPassword': admin_password}
            # Credentials go through an anonymous pipe, never a file/URL/argv.
            result = subprocess.run(['node', str(ROOT / 'scripts/phase7_browser.mjs')], input=json.dumps(data), text=True, cwd=ROOT, env=env, creationflags=flags, capture_output=True, timeout=180)
            print(result.stdout, end='')  # Runner emits fixed stage labels only, never raw browser/API data.
            if result.returncode != 0:
                raise RuntimeError('Phase 7 live browser smoke failed; see sanitized stage label above.')
            print('Phase 7 isolated-backend browser assertions passed; native Chrome CDP, four viewport widths, no checkout requests.', flush=True)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        cluster.close()
        assert browser_profile.parent == Path(tempfile.gettempdir()).resolve()
        assert browser_profile.name.startswith('whatnot-phase7-browser-')
        # Remove only this run's verified generated profile after its browser exited.
        if all(process.poll() is not None for process in processes):
            shutil.rmtree(browser_profile, ignore_errors=True)
        print('Owned test servers stopped; disposable PostgreSQL cluster cleanup completed.', flush=True)


if __name__ == '__main__':
    main()
