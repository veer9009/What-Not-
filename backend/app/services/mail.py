"""Mail adapters. SMTP has a bounded send/ack crash duplicate window."""
from email.message import EmailMessage
from hashlib import sha256
import smtplib
import ssl


class MailFailure(Exception):
    def __init__(self, code='DELIVERY_FAILED', *, permanent=False):
        self.code = code
        self.permanent = permanent


class FakeMailProvider:
    def __init__(self, failures=0):
        self.failures = failures
        self.messages = {}

    def send(self, recipient, title, body, idempotency_key):
        if self.failures:
            self.failures -= 1
            raise MailFailure('TEMPORARY_FAILURE')
        self.messages.setdefault(idempotency_key, (recipient, title, body))
        return idempotency_key


class SMTPMailProvider:
    def __init__(self, settings):
        self.settings = settings

    def send(self, recipient, title, body, idempotency_key):
        settings = self.settings
        if not recipient or '@' not in recipient or any(c in recipient for c in '\r\n'):
            raise MailFailure('INVALID_RECIPIENT', permanent=True)
        message = EmailMessage()
        message['From'] = settings.email_from
        message['To'] = recipient
        message['Subject'] = title
        reference = f'<{sha256(idempotency_key.encode()).hexdigest()}@whatnot.local>'
        message['Message-ID'] = reference
        message.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
                smtp.send_message(message)
        except smtplib.SMTPRecipientsRefused as exc:
            # A 4xx refusal is temporary (mailbox busy/greylisting), not an
            # invalid address. Only explicit 5xx refusals are permanent.
            codes = [result[0] for result in exc.recipients.values()]
            permanent = bool(codes) and all(500 <= code < 600 for code in codes)
            raise MailFailure('INVALID_RECIPIENT' if permanent else 'SMTP_RECIPIENT_TEMPORARY',
                              permanent=permanent) from None
        except (OSError, smtplib.SMTPException):
            raise MailFailure('SMTP_UNAVAILABLE') from None
        return reference
