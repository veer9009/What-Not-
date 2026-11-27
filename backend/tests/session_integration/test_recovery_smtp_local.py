"""Real loopback SMTP STARTTLS; synthetic disposable-schema recovery only."""
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
import ipaddress
from pathlib import Path
import re
import socketserver
import ssl
import sys
import threading

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import pytest

from app.services.mail import RecoverySMTPProvider, MailFailure
from app.services.recovery_delivery import process_recovery_email
from .test_password_recovery import recovery, BASE, CSRF
from .test_recovery_delivery import durable, job


@pytest.fixture
def local_smtp(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, 'Local test SMTP CA')])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
        .sign(key, hashes.SHA256()))
    certfile, keyfile = tmp_path / 'test-ca.pem', tmp_path / 'test-key.pem'
    certfile.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                        serialization.NoEncryption()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile, keyfile)
    messages, tls_sessions, tls_attempts = [], [], []
    diagnostics = {'errors': [], 'expect_certificate_rejection': False,
                   'error_recorded': threading.Event()}
    certificate_alerts = {'TLSV1_ALERT_UNKNOWN_CA', 'SSLV3_ALERT_BAD_CERTIFICATE',
                          'SSLV3_ALERT_CERTIFICATE_UNKNOWN'}

    class Handler(socketserver.StreamRequestHandler):
        def finish(self):
            try:
                super().finish()
            finally:
                # STARTTLS replaces the original request socket. TCPServer only
                # closes that original, detached socket; close the TLS owner too.
                self.connection.close()

        def handle(self):
            self.connection.settimeout(8)
            self.wfile.write(b'220 localhost test sink\r\n'); self.wfile.flush()
            tls = False
            while line := self.rfile.readline():
                command = line.split(b' ', 1)[0].strip().upper()
                if command in {b'EHLO', b'HELO'}:
                    reply = b'250-localhost\r\n250 STARTTLS\r\n' if not tls else b'250 localhost\r\n'
                elif command == b'STARTTLS':
                    tls_attempts.append(True)
                    self.wfile.write(b'220 Ready for TLS\r\n'); self.wfile.flush()
                    self.connection = context.wrap_socket(self.connection, server_side=True)
                    self.rfile = self.connection.makefile('rb')
                    self.wfile = self.connection.makefile('wb')
                    tls = True
                    tls_sessions.append(self.connection.version())
                    continue
                elif command in {b'MAIL', b'RCPT'}:
                    assert tls, 'Synthetic message attempted without TLS'
                    reply = b'250 OK\r\n'
                elif command == b'DATA':
                    assert tls
                    self.wfile.write(b'354 End with dot\r\n'); self.wfile.flush()
                    data = []
                    while (part := self.rfile.readline()) != b'.\r\n':
                        assert part
                        data.append(part)
                    messages.append(BytesParser(policy=policy.default).parsebytes(b''.join(data)))
                    reply = b'250 Stored only in memory\r\n'
                elif command == b'QUIT':
                    self.wfile.write(b'221 Bye\r\n'); self.wfile.flush()
                    return
                else:
                    reply = b'250 OK\r\n'
                self.wfile.write(reply); self.wfile.flush()

    class Server(socketserver.ThreadingTCPServer):
        # server_close joins every handler before teardown checks its errors.
        daemon_threads = False
        def handle_error(self, request, client_address):
            error = sys.exc_info()[1]
            diagnostics['errors'].append({'type': type(error).__name__,
                'ssl_error': isinstance(error, ssl.SSLError),
                'reason': error.reason if isinstance(error, ssl.SSLError) else None})
            diagnostics['error_recorded'].set()

    with Server(('127.0.0.1', 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address[1], certfile, messages, tls_sessions, tls_attempts, diagnostics
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            assert not thread.is_alive(), 'Local SMTP listener did not stop'
            errors = diagnostics['errors']
            if diagnostics['expect_certificate_rejection']:
                assert len(errors) == 1, errors
                assert errors[0]['ssl_error'] and errors[0]['reason'] in certificate_alerts, errors
            else:
                assert not errors, errors


def configure(settings, local_smtp):
    settings.email_provider = 'smtp'
    settings.smtp_host = '127.0.0.1'
    settings.smtp_port = local_smtp[0]
    settings.smtp_starttls = True
    settings.smtp_username = settings.smtp_password = None
    settings.email_from = 'local-sink@example.com'
    settings.recovery_smtp_deadline_seconds = 15


def test_real_tls_smtp_recovery_request_worker_verify_reset(durable, local_smtp, monkeypatch):
    client, engine, settings, _, uid, email = durable
    configure(settings, local_smtp)
    monkeypatch.setenv('SSL_CERT_FILE', str(local_smtp[1]))
    provider = RecoverySMTPProvider(settings)
    client.app.state.recovery_mail_provider = provider
    # Exercise the documented root-caller regression through the real child.
    monkeypatch.chdir(Path(__file__).resolve().parents[3])
    response = client.post(BASE + 'request', headers=CSRF, json={'email': email})
    assert response.status_code == 202
    challenge = response.json()['challenge']
    assert not local_smtp[2]
    assert job(engine, challenge).state == 'PENDING'
    assert process_recovery_email(engine, settings) == 1
    row = job(engine, challenge)
    assert row.state == 'SENT', row.last_error_code
    assert row.ciphertext is None and row.key_id is None
    assert len(local_smtp[2]) == 1 and local_smtp[3][0].startswith('TLS')
    message = local_smtp[2][0]
    assert message['To'] == email
    otp = re.search(r'\b[0-9]{6}\b', message.get_content()).group()
    verified = client.post(BASE + 'verify', headers=CSRF, json={'challenge': challenge, 'otp': otp})
    assert verified.status_code == 200
    reset = client.post(BASE + 'reset', headers=CSRF,
        json={'reset_token': verified.json()['reset_token'], 'password': 'synthetic replacement password'})
    assert reset.status_code == 200
    assert client.post('/api/v1/auth/login', headers=CSRF,
        json={'email': email, 'password': 'synthetic replacement password'}).status_code == 200
    assert client.post('/api/v1/auth/login', headers=CSRF,
        json={'email': email, 'password': 'old password'}).status_code == 401


def test_real_tls_smtp_rejects_untrusted_certificate(durable, local_smtp, monkeypatch):
    settings = durable[2]
    configure(settings, local_smtp)
    monkeypatch.delenv('SSL_CERT_FILE', raising=False)
    diagnostics = local_smtp[5]
    diagnostics['expect_certificate_rejection'] = True
    with pytest.raises(MailFailure):
        RecoverySMTPProvider(settings).send('synthetic@example.com', 'Synthetic', 'Synthetic', 'synthetic')
    assert not local_smtp[2]
    assert local_smtp[4], 'Negative control must actually reach TLS negotiation'
    assert diagnostics['error_recorded'].wait(timeout=3), 'Missing TLS peer rejection diagnostic'
