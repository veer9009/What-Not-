"""Offline configuration and real AEAD tests; never contact SMTP."""
import base64
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def config(**overrides):
    values = dict(_env_file=None, environment='test', password_recovery_key='h' * 48,
                  recovery_active_key='v1', recovery_encryption_keys={'v1': base64.b64encode(b'e' * 32).decode()})
    return Settings(**(values | overrides))


def test_recovery_remains_disabled_by_default():
    assert not config().recovery_delivery_enabled


@pytest.mark.parametrize('keys', [{'v1': 'bad'}, {'v1': base64.b64encode(b'short').decode()}])
def test_recovery_rejects_invalid_encryption_keys(keys):
    with pytest.raises(ValidationError):
        config(recovery_encryption_keys=keys)


def test_recovery_rejects_key_reuse():
    shared = 'h' * 32
    with pytest.raises(ValidationError):
        config(password_recovery_key=shared,
               recovery_encryption_keys={'v1': base64.b64encode(shared.encode()).decode()})


@pytest.mark.parametrize('field', ['jwt_secret_key', 'password_recovery_key'])
def test_recovery_rejects_identical_encoded_secrets(field):
    encoded = base64.b64encode(b'e' * 32).decode()
    with pytest.raises(ValidationError):
        config(**{field: encoded})


def test_real_aead_binds_context_and_randomizes_ciphertext():
    pytest.importorskip('cryptography', reason='Real cryptography dependency unavailable; no substitute')
    from app.services.recovery_delivery import seal, unseal
    settings = config()
    first = seal(settings, b'synthetic-otp-000007', b'challenge:A')
    second = seal(settings, b'synthetic-otp-000007', b'challenge:A')
    assert first != second
    assert b'000007' not in first[1]
    assert unseal(settings, *first, b'challenge:A') == b'synthetic-otp-000007'
    with pytest.raises(Exception):
        unseal(settings, *first, b'challenge:B')
    with pytest.raises(Exception):
        unseal(settings, first[0], first[1][:-1] + bytes([first[1][-1] ^ 1]), b'challenge:A')


def test_missing_crypto_fails_closed(monkeypatch):
    from app.services import recovery_delivery
    monkeypatch.setattr(recovery_delivery, 'aesgcm', lambda: (_ for _ in ()).throw(ImportError()))
    with pytest.raises(Exception):
        recovery_delivery.seal(config(), b'synthetic', b'context')


def test_worker_is_disabled_before_database_access():
    from app.services.recovery_delivery import process_recovery_email
    engine = SimpleNamespace(connect=lambda: pytest.fail('Disabled worker accessed database'))
    assert process_recovery_email(engine, config()) == 0


def test_activation_without_crypto_is_unavailable(monkeypatch):
    from fastapi import HTTPException
    from app.services.auth_recovery import recovery_ready
    from app.services.mail import FakeMailProvider
    def missing():
        raise ImportError()
    monkeypatch.setattr('app.services.recovery_delivery.aesgcm', missing)
    with pytest.raises(HTTPException) as error:
        recovery_ready(config(recovery_delivery_enabled=True), FakeMailProvider())
    assert error.value.status_code == 503


def test_key_rotation_can_drain_old_jobs_but_missing_key_is_rejected():
    pytest.importorskip('cryptography')
    from app.services.recovery_delivery import seal, unseal
    old = config()
    sealed = seal(old, b'synthetic', b'context')
    rotated = config(recovery_active_key='v2', recovery_encryption_keys={
        'v1': base64.b64encode(b'e' * 32).decode(), 'v2': base64.b64encode(b'r' * 32).decode()})
    assert unseal(rotated, *sealed, b'context') == b'synthetic'
    del rotated.recovery_encryption_keys['v1']
    with pytest.raises(KeyError):
        unseal(rotated, *sealed, b'context')


def test_recovery_smtp_hard_deadline_uses_no_secret_arguments(monkeypatch):
    import subprocess
    from app.services.mail import RecoverySMTPProvider, MailFailure
    observed = {}
    def blocked(command, **options):
        observed.update(command=command, **options)
        raise subprocess.TimeoutExpired(command, options['timeout'])
    monkeypatch.setattr(subprocess, 'run', blocked)
    settings = config(smtp_password='synthetic-smtp-secret', recovery_smtp_deadline_seconds=3)
    with pytest.raises(MailFailure) as error:
        RecoverySMTPProvider(settings).send('synthetic@example.test', 'Title', 'synthetic-OTP-body', 'stable-key')
    assert error.value.code == 'SMTP_DEADLINE'
    assert observed['timeout'] == 3 and observed['stdout'] == subprocess.DEVNULL and observed['stderr'] == subprocess.DEVNULL
    assert 'synthetic-smtp-secret' not in repr(observed['command'])
    assert 'synthetic-OTP-body' not in repr(observed['command'])


@pytest.mark.parametrize('exit_code,permanent', [(1, False), (2, True)])
def test_recovery_smtp_failure_codes_are_sanitized(monkeypatch, exit_code, permanent):
    import subprocess
    from app.services.mail import RecoverySMTPProvider, MailFailure
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(returncode=exit_code))
    with pytest.raises(MailFailure) as error:
        RecoverySMTPProvider(config()).send('synthetic@example.test', 'title', 'body', 'key')
    assert error.value.code == 'SMTP_FAILURE' and error.value.permanent == permanent


@pytest.mark.skipif(__import__('os').name != 'nt', reason='Windows orphan-process handle regression')
def test_smtp_child_deadline_survives_worker_death():
    """Kill a synthetic worker during fake SMTP, and wait on its actual child.

    The SMTP adapter is replaced inside the child before main; no network access.
    """
    import ctypes
    import json
    import subprocess
    import sys
    from ctypes import wintypes
    child_code = """
import sys,time
from types import SimpleNamespace
from app.services import mail
def send(*args):
    print('synthetic-sending', flush=True)
    time.sleep(60)
mail.SMTPMailProvider=lambda settings: SimpleNamespace(send=send)
from app.recovery_smtp import main
raise SystemExit(main())
"""
    parent_code = """
import sys,time,subprocess,json
child=subprocess.Popen([sys.executable,'-c',sys.argv[1],str(time.monotonic()+6)],stdin=subprocess.PIPE,text=True)
print(child.pid,flush=True)
child.stdin.write(json.dumps({'settings':{'smtp_password':None},'message':['synthetic']*4}))
child.stdin.close()
time.sleep(60)
"""
    parent = subprocess.Popen([sys.executable, '-c', parent_code, child_code],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = None
    try:
        pid = int(parent.stdout.readline())
        handle = kernel.OpenProcess(0x00100000 | 0x0001, False, pid)
        assert handle
        assert parent.stdout.readline().strip() == 'synthetic-sending'
        parent.terminate();parent.wait(timeout=3)
        assert kernel.WaitForSingleObject(handle, 8000) == 0, 'Orphan SMTP child outlived its absolute deadline'
    finally:
        if parent.poll() is None:
            parent.terminate();parent.wait(timeout=3)
        if handle:
            if kernel.WaitForSingleObject(handle, 0) != 0:
                kernel.TerminateProcess(handle, 1)
            kernel.CloseHandle(handle)
        parent.stdout.close()
