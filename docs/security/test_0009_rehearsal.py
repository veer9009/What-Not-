"""Mock-only targeting and comparison tests; never connect to PostgreSQL."""
import copy
from pathlib import Path
import pytest
import rehearse_0009_migration as r

RUN = 'd4e5f6a7'
NAME = 'whatnot_0009_rehearsal_20261115_' + RUN
ROLLBACK = 'whatnot_0009_rollback_20261115_' + RUN
IDENTITY = (NAME, 60001, '127.0.0.1', 5432, 170011, False, True)


@pytest.mark.parametrize('name,oid', [('whatnot_app_dev',41069),
    ('whatnot_chrome_qa_20261115',50640), ('whatnot_tests_20261115_a7e394c2',49265),
    (NAME,41069),(NAME,50640),(NAME,0),(NAME,True),('other',60001)])
def test_reject_protected_or_unapproved_target(name,oid):
    with pytest.raises(RuntimeError):r.validate_target(IDENTITY,name,oid,RUN)


@pytest.mark.parametrize('index,value',[(0,'whatnot_app_dev'),(1,41069),(2,'192.0.2.1'),
    (3,5433),(4,160000),(5,True),(6,False)])
def test_reject_identity_mismatch(index,value):
    actual=list(IDENTITY);actual[index]=value
    with pytest.raises(RuntimeError):r.validate_target(tuple(actual),NAME,60001,RUN)


def test_accept_exact_new_target():r.validate_target(IDENTITY,NAME,60001,RUN)


def test_accept_separate_rollback_target():
    r.validate_target((ROLLBACK,*IDENTITY[1:]),ROLLBACK,60001,RUN)


def test_private_comparison_allows_only_version_change():
    before={'users':{'count':6,'digest':'users'},'seller_profiles':{'count':2,'digest':'seller'},
            'alembic_version':{'count':1,'digest':'0008'}}
    after=copy.deepcopy(before);after['alembic_version']['digest']='0009'
    r.compare_preserved(before,after,allow_revision_change=True)
    with pytest.raises(RuntimeError):r.compare_preserved(before,after)
    after['users']['digest']='changed'
    with pytest.raises(RuntimeError):r.compare_preserved(before,after,allow_revision_change=True)


def test_extra_table_or_changed_counts_fail():
    before={'users':{'count':6,'digest':'private'}}
    for after in [{'users':{'count':7,'digest':'private'}},{**before,'extra':{}}]:
        with pytest.raises(RuntimeError):r.compare_preserved(before,after)


def test_manifest_rejects_old_qa_and_source_names():
    manifest={'run':RUN,'rehearsal':NAME,'rollback':ROLLBACK,'source':'whatnot_app_dev',
              'source_oid':41069,'migration_sha256':r.MIGRATION_SHA256}
    r.validate_manifest(manifest)
    for key,value in [('rehearsal','whatnot_app_dev'),('rollback',NAME),
                      ('source_oid',50640),('migration_sha256','0'*64)]:
        broken={**manifest,key:value}
        with pytest.raises(RuntimeError):r.validate_manifest(broken)


def test_restore_header_pins_only_target():
    header=r.restore_header(NAME,60001,RUN).decode()
    assert NAME in header and '60001' in header and 'current_database()' in header
    with pytest.raises(RuntimeError):r.restore_header('whatnot_app_dev',41069,RUN)


@pytest.mark.parametrize('script',[b'\\connect whatnot_app_dev\n',b'CREATE DATABASE unexpected;',
                                 b'DROP DATABASE unexpected;'])
def test_reject_restore_connection_changes(script):
    with pytest.raises(RuntimeError):r.validate_restore_sql(script)


def test_ordinary_dump_sql_is_accepted():
    r.validate_restore_sql(b'SET statement_timeout = 0;\nCREATE TABLE public.users (id bigint);')


def test_backup_name_cannot_escape_protected_folder():
    folder=Path('synthetic')
    assert r.archive_path({},folder).name=='whatnot_app_dev-0008-before-0009.dump'
    for name in ['../other.dump','whatnot_app_dev.dump','C:/other.dump']:
        with pytest.raises(RuntimeError):r.archive_path({'archive_name':name},folder)


def test_schema_comparison_rejects_unexpected_changes():
    before=dict(columns=[['users','id']],constraints=[['users','pk','PRIMARY KEY (id)',True]],indexes=[])
    r.compare_schema(before,copy.deepcopy(before))
    changed=copy.deepcopy(before);changed['columns'].append(['users','unexpected'])
    with pytest.raises(RuntimeError):r.compare_schema(before,changed)
    with pytest.raises(RuntimeError):r.compare_schema(before,changed,migrated=True)


def test_source_can_never_be_opened_writable(monkeypatch):
    forbidden=MockConnect()
    monkeypatch.setattr(r.psycopg,'connect',forbidden)
    with pytest.raises(RuntimeError):r.connect(None,'whatnot_app_dev',readonly=False)
    assert not forbidden.called


class MockConnect:
    called=False
    def __call__(self,*args,**kwargs):
        self.called=True
        raise AssertionError('Database connection not allowed in unit tests')


import json
EQUIVALENT = json.loads((Path(__file__).parent/'evidence/0009-constraint-investigation.json').read_text())['differences']


@pytest.mark.parametrize('case', EQUIVALENT, ids=lambda c:c['constraint'])
def test_documented_cast_rewrite_is_accepted(case):
    before=dict(columns=[],indexes=[],constraints=[[case['table'],case['constraint'],case['expected'],True]])
    after=copy.deepcopy(before);after['constraints'][0][2]=case['actual']
    r.compare_schema(before,after)


@pytest.mark.parametrize('change', ['literal','column','operator','bounded','unknown','name','flag','metadata'])
def test_cast_rewrite_rejects_real_changes(change):
    case=EQUIVALENT[0]
    before=dict(columns=[],indexes=[],constraints=[[case['table'],case['constraint'],case['expected'],True]],constraint_metadata=[['table','check',True]])
    after=copy.deepcopy(before);after['constraints'][0][2]=case['actual']
    if change=='literal':after['constraints'][0][2]=case['actual'].replace('ACCEPTED','ALTERED')
    if change=='column':after['constraints'][0][2]=case['actual'].replace('(status)','(other)')
    if change=='operator':after['constraints'][0][2]=case['actual'].replace(' = ANY ',' <> ANY ')
    if change=='bounded':after['constraints'][0][2]=case['actual'].replace('character varying','character varying(1)')
    if change=='unknown':before['constraints'][0][2]='CHECK (true)';after['constraints'][0][2]='CHECK (false)'
    if change=='name':before['constraints'][0][1]=after['constraints'][0][1]='unexpected_check'
    if change=='flag':after['constraints'][0][3]=False
    if change=='metadata':after['constraint_metadata'][0][2]=False
    with pytest.raises(RuntimeError):r.compare_schema(before,after)


def test_continuation_requires_existing_0008_and_exact_data(monkeypatch):
    from unittest.mock import MagicMock
    connection=MagicMock()
    connection.__enter__.return_value=connection
    connection.execute.return_value.fetchone.return_value=IDENTITY
    connection.execute.return_value.fetchall.return_value=[('0009',)]
    monkeypatch.setattr(r,'target_preflight',lambda *a,**kw:None)
    monkeypatch.setattr(r,'connect',lambda *a,**kw:connection)
    with pytest.raises(RuntimeError):r.restored_preflight(None,NAME,60001,{'run':RUN})


@pytest.mark.parametrize('suffix',[" NOT VALID", " COLLATE bad", " OR true", "::boolean"])
def test_unknown_cast_extensions_fail_closed(suffix):
    assert r.cast_signature(EQUIVALENT[0]['actual']+suffix) is None


def test_cast_literals_order_null_and_escaping():
    a="CHECK (((status)::text = ANY ((ARRAY['O''K'::character varying, 'B'::character varying])::text[])))"
    b="CHECK (((status)::text = ANY (ARRAY[('O''K'::character varying)::text, ('B'::character varying)::text])))"
    assert r.cast_signature(a)==r.cast_signature(b)
    assert r.cast_signature(a)!=r.cast_signature(b.replace("'O''K'", "'B'").replace("('B'::", "('C'::",1))
    assert r.cast_signature(a.replace("'B'::character varying", "NULL::character varying")) is None
    assert r.cast_signature(a.replace("'O''K'::character varying, 'B'::character varying", "")) is None
