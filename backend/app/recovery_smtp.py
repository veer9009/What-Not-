"""Private bounded SMTP child; accepts no command-line credentials or DB config."""
import os
import sys
import threading
import time


def main():
    # Independent of the worker: an orphan must not outlive the lease's reserved
    # SMTP budget. Arm before potentially blocking imports, stdin or DNS/network.
    try:
        deadline = float(sys.argv[1])
        remaining = deadline - time.monotonic()
        if not 0 < remaining <= 20:
            return 1
    except Exception:
        return 1
    timer = threading.Timer(remaining, lambda: os._exit(1))
    timer.daemon = True
    timer.start()
    try:
        import json
        from types import SimpleNamespace
        from pydantic import SecretStr
        from app.services.mail import SMTPMailProvider, MailFailure
        try:
            payload = json.loads(sys.stdin.read())
            values = payload['settings']
            values['smtp_password'] = SecretStr(values['smtp_password']) if values['smtp_password'] else None
            if time.monotonic() >= deadline:
                return 1
            SMTPMailProvider(SimpleNamespace(**values)).send(*payload['message'])
            return 0
        except MailFailure as exc:
            return 2 if exc.permanent else 1
        except Exception:
            return 1
    finally:
        timer.cancel()


if __name__ == '__main__':
    sys.exit(main())
