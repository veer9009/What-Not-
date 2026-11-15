"""Mock-only reset tests. Never connect to a database or reset a real password."""
from contextlib import contextmanager
from unittest.mock import Mock
import secrets
import warnings
import pytest
import reset_original_admin as reset
from app.core.security import hash_password,verify_password

GOOD=('whatnot_app_dev',41069,'127.0.0.1',5432,'dev_role',170011,False,True)


@pytest.mark.parametrize('index,value',[(0,'whatnot_chrome_qa_20261115'),(1,50640),
    (2,'192.0.2.1'),(3,5433),(4,'postgres'),(5,160000),(6,True),(7,False)])
def test_identity_rejection(index,value):
    actual=list(GOOD);actual[index]=value
    with pytest.raises(RuntimeError):reset.validate_identity(tuple(actual),'dev_role')


def test_good_identity():reset.validate_identity(GOOD,'dev_role')


@pytest.mark.parametrize('rows',[
    [],[(7,'other@example.com','ADMIN',True)],[(7,'admin@example.com','BUYER',True)],
    [(7,'admin@example.com','ADMIN',False)],[(7,'admin@example.com','ADMIN',True)]*2])
def test_account_mismatch(rows):
    with pytest.raises(RuntimeError):reset.validate_account(rows)


class Result:
    def __init__(self,rows):self.rows=rows
    def fetchall(self):return self.rows
    def fetchone(self):return self.rows[0]


class FakeConnection:
    def __init__(self):self.value='old';self.updates=0;self.commits=0;self.rollbacks=0
    @contextmanager
    def transaction(self):
        before=self.value
        try:yield
        except Exception:self.value=before;self.rollbacks+=1;raise
        else:self.commits+=1
    def execute(self,query,params=None):
        if isinstance(query,str) and query.startswith('UPDATE public.users'):
            self.value=params[0];self.updates+=1
            return Result([(7,)])
        if isinstance(query,str) and query.startswith('SELECT password_hash='):
            return Result([(self.value==params[0],)])
        if isinstance(query,str) and 'FOR UPDATE' in query:
            return Result([(7,'admin@example.com','ADMIN',True)])
        return Result([])


@pytest.fixture
def harness(monkeypatch):
    connection=FakeConnection()
    monkeypatch.setattr(reset,'verify_schema',lambda c,role:None)
    monkeypatch.setattr(reset,'public_tables',lambda c:['users','products'])
    monkeypatch.setattr(reset,'preservation_digest',lambda c,uid,tables:'unchanged')
    return connection


def run(connection):
    password=secrets.token_urlsafe(24)
    encoded=hash_password(password)
    reset.reset_transaction(connection,'dev_role',7,encoded,lambda:None)
    return password


def test_success_exactly_one_update_and_existing_hasher(harness,monkeypatch):
    execute=harness.execute
    calls=[]
    def record(query,params=None):
        if isinstance(query,str) and query.startswith('UPDATE '):calls.append((query,params))
        return execute(query,params)
    monkeypatch.setattr(harness,'execute',record)
    password=run(harness)
    assert harness.updates==1 and harness.commits==1 and harness.rollbacks==0
    assert verify_password(password,harness.value)
    assert calls[0][0]==("UPDATE public.users SET password_hash=%s "
        "WHERE id=%s AND email=%s AND role='ADMIN' AND is_active RETURNING id")
    assert calls[0][1][1:]==(7,'admin@example.com')


def test_account_id_changed_refuses_write(harness):
    with pytest.raises(RuntimeError):
        reset.reset_transaction(harness,'dev_role',8,hash_password(secrets.token_urlsafe(20)),lambda:None)
    assert harness.updates==0 and harness.rollbacks==1


def test_identity_failure_prevents_write(harness,monkeypatch):
    monkeypatch.setattr(reset,'verify_schema',Mock(side_effect=RuntimeError('wrong identity')))
    with pytest.raises(RuntimeError):run(harness)
    assert harness.updates==0 and harness.rollbacks==1


def test_post_update_mismatch_rolls_back(harness,monkeypatch):
    values=iter(['before','after'])
    monkeypatch.setattr(reset,'preservation_digest',lambda *args:next(values))
    with pytest.raises(RuntimeError):run(harness)
    assert harness.value=='old' and harness.updates==1 and harness.rollbacks==1 and harness.commits==0


def test_failed_update_rolls_back(harness,monkeypatch):
    execute=harness.execute
    def fail(query,params=None):
        result=execute(query,params)
        if isinstance(query,str) and query.startswith('UPDATE '):raise RuntimeError('synthetic failure')
        return result
    monkeypatch.setattr(harness,'execute',fail)
    with pytest.raises(RuntimeError):run(harness)
    assert harness.value=='old' and harness.rollbacks==1


def test_backup_failure_prevents_write(harness):
    with pytest.raises(RuntimeError):
        reset.reset_transaction(harness,'dev_role',7,hash_password(secrets.token_urlsafe(20)),
            Mock(side_effect=RuntimeError('backup mismatch')))
    assert harness.updates==0 and harness.rollbacks==1


def test_hidden_prompt_refuses_echo(monkeypatch):
    from getpass import GetPassWarning
    def fallback(prompt):warnings.warn('Echo unavailable',GetPassWarning)
    monkeypatch.setattr(reset,'getpass',fallback)
    with pytest.raises(GetPassWarning):reset.hidden_password('Synthetic prompt: ')


def test_password_rules_preserve_spaces():
    value='  '+secrets.token_urlsafe(16)+'  '
    assert reset.validate_password(value)==value
    for value in ['short','x'*129]:
        with pytest.raises(RuntimeError):reset.validate_password(value)


@pytest.mark.parametrize('rows',[[],[(7,),(8,)],[(8,)]])
def test_unexpected_update_count_or_id_rolls_back(harness,monkeypatch,rows):
    execute=harness.execute
    def unexpected(query,params=None):
        result=execute(query,params)
        return Result(rows) if isinstance(query,str) and query.startswith('UPDATE ') else result
    monkeypatch.setattr(harness,'execute',unexpected)
    with pytest.raises(RuntimeError):run(harness)
    assert harness.value=='old' and harness.rollbacks==1 and harness.commits==0


def test_failed_readback_rolls_back(harness,monkeypatch):
    execute=harness.execute
    def wrong(query,params=None):
        result=execute(query,params)
        return Result([(False,)]) if isinstance(query,str) and query.startswith('SELECT password_hash=') else result
    monkeypatch.setattr(harness,'execute',wrong)
    with pytest.raises(RuntimeError):run(harness)
    assert harness.value=='old' and harness.rollbacks==1


def test_backup_validation(tmp_path,monkeypatch):
    import hashlib
    from types import SimpleNamespace
    artifact=tmp_path/'synthetic.dump'
    artifact.write_bytes(b'PGDMPsynthetic-test-only')
    expected=hashlib.sha256(artifact.read_bytes()).hexdigest()
    listing=SimpleNamespace(returncode=0,stdout=';     dbname: whatnot_app_dev\n1; 0 1 TABLE DATA public users role\n')
    monkeypatch.setattr(reset.subprocess,'run',Mock(return_value=listing))
    reset.verify_backup(artifact,expected)
    with pytest.raises(RuntimeError):reset.verify_backup(artifact,'0'*64)
    listing.returncode=1
    with pytest.raises(RuntimeError):reset.verify_backup(artifact,expected)
    listing.returncode=0
    listing.stdout=';     dbname: whatnot_chrome_qa_20261115\n1; 0 1 TABLE DATA public users role\n'
    with pytest.raises(RuntimeError):reset.verify_backup(artifact,expected)


def test_default_cli_is_read_only(monkeypatch,harness,capsys):
    class Managed:
        def __enter__(self):return harness
        def __exit__(self,*args):return False
    execute=harness.execute
    def read(query,params=None):
        if isinstance(query,str) and query.startswith('SELECT id,email,role,is_active'):
            return Result([(7,'admin@example.com','ADMIN',True)])
        return execute(query,params)
    monkeypatch.setattr(harness,'execute',read)
    monkeypatch.setattr(reset,'connection_parameters',lambda:({},'dev_role'))
    connect=Mock(return_value=Managed())
    monkeypatch.setattr(reset.psycopg,'connect',connect)
    forbidden=Mock(side_effect=AssertionError('write path must not run'))
    monkeypatch.setattr(reset,'reset_transaction',forbidden)
    reset.main([])
    forbidden.assert_not_called()
    assert connect.call_args.kwargs['options'].startswith('-c default_transaction_read_only=on')
    assert 'CHECK ONLY' in capsys.readouterr().out


@pytest.mark.parametrize('failure',['missing_backup','noninteractive','confirmation','password_confirmation'])
def test_cli_execution_guards_prevent_write(monkeypatch,harness,failure):
    from types import SimpleNamespace
    class Managed:
        def __enter__(self):return harness
        def __exit__(self,*args):return False
    execute=harness.execute
    def read(query,params=None):
        if isinstance(query,str) and query.startswith('SELECT id,email,role,is_active'):
            return Result([(7,'admin@example.com','ADMIN',True)])
        return execute(query,params)
    monkeypatch.setattr(harness,'execute',read)
    monkeypatch.setattr(reset,'connection_parameters',lambda:({},'dev_role'))
    connect=Mock(return_value=Managed())
    monkeypatch.setattr(reset.psycopg,'connect',connect)
    monkeypatch.setattr(reset.sys,'stdin',SimpleNamespace(isatty=lambda:failure!='noninteractive'))
    monkeypatch.setattr(reset,'verify_backup',Mock())
    monkeypatch.setattr('builtins.input',lambda prompt:'NO' if failure=='confirmation' else reset.CONFIRMATION)
    monkeypatch.setattr(reset,'hidden_password',Mock(side_effect=[secrets.token_urlsafe(20),'different']))
    forbidden=Mock(side_effect=AssertionError('write path must not run'))
    monkeypatch.setattr(reset,'reset_transaction',forbidden)
    args=['--execute']
    if failure!='missing_backup':args+=['--backup','synthetic.dump','--backup-sha256','0'*64]
    with pytest.raises(RuntimeError):reset.main(args)
    forbidden.assert_not_called()
    assert connect.call_count==1 and harness.updates==0
