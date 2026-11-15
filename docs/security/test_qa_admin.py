"""No DB connections or account writes: policy and mocked transaction tests."""
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock
import secrets
import pytest
from app.schemas.auth import UserRegistration
from app.core.security import verify_password
import provision_qa_admin as provision
from qa_admin_policy import validate_identity, configured_admin_email, validate_roster

GOOD=('whatnot_chrome_qa_20261115',50640,True,'qa_role','127.0.0.1',5432,170000,False)


@pytest.mark.parametrize('index,value',[(0,'whatnot_app_dev'),(1,1),(2,False),(3,'postgres'),
    (4,'192.0.2.1'),(5,5433),(6,160000),(7,True)])
def test_identity_rejects(index,value):
    row=list(GOOD);row[index]=value
    with pytest.raises(RuntimeError):validate_identity(tuple(row),'qa_role')


def test_identity_accepts():validate_identity(GOOD,'qa_role')


def test_wrong_identity_stops_before_any_user_query():
    session=Mock()
    session.execute.return_value.one.return_value=('whatnot_app_dev',50640,True,'qa_role','127.0.0.1',5432,170000,False)
    with pytest.raises(RuntimeError):provision.inspect_state(session,'qa_role','operator@example.com',True)
    assert session.execute.call_count==1
    session.scalar.assert_not_called()


def test_admin_email_requires_explicit_qa_marker_and_distinct_email(monkeypatch):
    monkeypatch.setenv('WHATNOT_QA_ADMIN_EMAIL','operator@example.com')
    monkeypatch.delenv('WHATNOT_QA_ENVIRONMENT',raising=False)
    with pytest.raises(RuntimeError):configured_admin_email()
    monkeypatch.setenv('WHATNOT_QA_ENVIRONMENT','chrome-discovery-v1')
    assert configured_admin_email()=='operator@example.com'
    monkeypatch.setenv('WHATNOT_QA_ADMIN_EMAIL','chrome-buyer@example.com')
    with pytest.raises(RuntimeError):configured_admin_email()


BASE=[('chrome-buyer@example.com','BUYER',True),('chrome-seller@example.com','SELLER',True)]


def test_roster_does_not_admit_unconfigured_or_inactive_admin():
    validate_roster(BASE,None)
    validate_roster(BASE+[('operator@example.com','ADMIN',True)],'operator@example.com')
    for rows,email in [(BASE+[('operator@example.com','ADMIN',True)],None),
        (BASE+[('other@example.com','ADMIN',True)],'operator@example.com'),
        (BASE+[('operator@example.com','ADMIN',False)],'operator@example.com')]:
        with pytest.raises(RuntimeError):validate_roster(rows,email)


class FakeSession:
    def __init__(self):self.admins=0;self.commits=0;self.rollbacks=0;self.changed=False
    def __enter__(self):return self
    def __exit__(self,*args):pass
    @contextmanager
    def begin(self):
        before=self.admins
        try:yield
        except Exception:self.admins=before;self.rollbacks+=1;raise
        else:self.commits+=1
    def execute(self,*args,**kwargs):return Mock()
    def flush(self):pass


@pytest.fixture
def harness(monkeypatch):
    session=FakeSession();created=[]
    def inspect(s,expected_user,admin_email,require_absent=False):
        if require_absent and s.admins:raise RuntimeError('QA admin already exists')
        return {'admin_count':s.admins,'counts':{'users':2+s.admins,'seller_profiles':1,'products':3,'addresses':1,'orders':0}}
    monkeypatch.setattr(provision,'inspect_state',inspect)
    monkeypatch.setattr(provision,'fingerprints',lambda s:('changed' if s.changed else 'original'))
    class Service:
        def __init__(self,s):self.s=s
        def create(self,data):
            created.append(data);self.s.admins+=1
            return SimpleNamespace(role='ADMIN',is_active=True)
    monkeypatch.setattr(provision,'UserService',Service)
    password=secrets.token_urlsafe(24)
    details=UserRegistration(name='QA Operator',email='operator@example.com',phone='qa-only-operator',password=password)
    return session,created,details,password


def run(h):
    session,created,details,password=h
    return provision.run_transaction(object(),details,'qa_role','operator@example.com',session_factory=lambda engine:session)


def test_success_uses_usercreate_argon2_and_active_admin(harness):
    state=run(harness);s,created,details,password=harness
    assert s.commits==1 and s.rollbacks==0 and state['admin_count']==1
    assert created[0].role.value=='ADMIN' and created[0].is_active is True
    assert verify_password(password,created[0].password_hash.get_secret_value())


def test_duplicate_prevents_second_service_call(harness):
    run(harness)
    with pytest.raises(RuntimeError):run(harness)
    assert len(harness[1])==1 and harness[0].admins==1


def test_service_failure_rolls_back(harness,monkeypatch):
    class Broken:
        def __init__(self,s):self.s=s
        def create(self,data):self.s.admins+=1;raise RuntimeError('synthetic failure')
    monkeypatch.setattr(provision,'UserService',Broken)
    with pytest.raises(RuntimeError):run(harness)
    assert harness[0].admins==0 and harness[0].rollbacks==1 and harness[0].commits==0


def test_preservation_failure_rolls_back(harness,monkeypatch):
    calls=iter(['before','after'])
    monkeypatch.setattr(provision,'fingerprints',lambda s:next(calls))
    with pytest.raises(RuntimeError):run(harness)
    assert harness[0].admins==0 and harness[0].rollbacks==1


def test_default_cli_is_read_only_and_never_calls_write(harness,monkeypatch,capsys):
    from sqlalchemy.engine import URL
    monkeypatch.setenv('WHATNOT_QA_ENVIRONMENT','chrome-discovery-v1')
    monkeypatch.setenv('WHATNOT_QA_ADMIN_EMAIL','operator@example.com')
    monkeypatch.setattr(provision,'Settings',lambda:SimpleNamespace(environment='development'))
    monkeypatch.setattr(provision,'target',lambda:(URL.create('postgresql+psycopg',username='qa_role',host='127.0.0.1',port=5432,database='whatnot_chrome_qa_20261115'),50640))
    engine=Mock();construct=Mock(return_value=engine)
    monkeypatch.setattr(provision,'create_engine',construct)
    session=harness[0];session.scalar=lambda query:'on'
    monkeypatch.setattr(provision,'Session',lambda engine:session)
    writer=Mock();monkeypatch.setattr(provision,'run_transaction',writer)
    monkeypatch.setattr(provision.sys,'argv',['provision_qa_admin.py'])
    provision.main()
    writer.assert_not_called()
    assert 'default_transaction_read_only=on' in construct.call_args.kwargs['connect_args']['options']
    output=capsys.readouterr().out
    assert 'READ_ONLY_VERIFIED' in output and harness[3] not in output
    assert 'operator@example.com' not in output


def test_non_qa_environment_stops_before_connection(monkeypatch):
    monkeypatch.delenv('WHATNOT_QA_ENVIRONMENT',raising=False)
    monkeypatch.setattr(provision.sys,'argv',['provision_qa_admin.py','--execute'])
    connector=Mock();monkeypatch.setattr(provision,'create_engine',connector)
    with pytest.raises(RuntimeError):provision.main()
    connector.assert_not_called()


def test_hidden_prompt_refuses_echo_fallback(monkeypatch):
    import warnings
    from getpass import GetPassWarning
    def fallback(prompt):warnings.warn('Cannot disable echo',GetPassWarning)
    monkeypatch.setattr(provision,'getpass',fallback)
    with pytest.raises(GetPassWarning):provision.hidden_password('Synthetic password prompt: ')
