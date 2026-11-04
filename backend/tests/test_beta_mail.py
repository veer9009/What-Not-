import pytest


def test_fake_provider_honors_idempotency_key():
    from app.services.mail import FakeMailProvider
    provider = FakeMailProvider()
    assert provider.send('buyer@example.test', 'Update', 'Body', 'event:1') == provider.send('buyer@example.test', 'Update', 'Body', 'event:1')
    assert len(provider.messages) == 1


@pytest.mark.parametrize('code,permanent',[(450,False),(451,False),(452,False),(550,True)])
def test_smtp_recipient_refusal_classification(monkeypatch,code,permanent):
    import smtplib
    import pytest
    from app.core.config import Settings
    from app.services.mail import SMTPMailProvider, MailFailure
    class SMTP:
        def __init__(self,*args,**kwargs): pass
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def send_message(self,message):
            raise smtplib.SMTPRecipientsRefused({'buyer@example.com':(code,b'Refused')})
    monkeypatch.setattr(smtplib,'SMTP',SMTP)
    provider=SMTPMailProvider(Settings(_env_file=None,smtp_starttls=False))
    with pytest.raises(MailFailure) as failure:
        provider.send('buyer@example.com','Update','Body','stable-event')
    assert failure.value.permanent is permanent
    assert failure.value.code==('INVALID_RECIPIENT' if permanent else 'SMTP_RECIPIENT_TEMPORARY')
