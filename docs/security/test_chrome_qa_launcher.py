"""Launcher isolation checks: synthetic configuration only; no DB connections."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_chrome_discovery_qa as qa


@pytest.fixture
def manifest(monkeypatch,tmp_path):
    path=tmp_path/'approved-qa.json'
    path.write_text(json.dumps({'database':qa.QA,'oid':900001,'revision':'0008',
                               'fixtures_version':'chrome-discovery-v1'}),encoding='utf-8')
    monkeypatch.setattr(qa,'MANIFEST',path)
    monkeypatch.setattr(qa,'Settings',lambda:SimpleNamespace(database_url=SecretStr(
        'postgresql+psycopg://synthetic:synthetic-only@127.0.0.1:5432/whatnot_app_dev')))
    return path


def test_explicitly_targets_only_new_qa_database_without_changing_private_connection_inputs(manifest):
    url,oid=qa.target()
    assert url.database==qa.QA and oid==900001
    assert url.username=='synthetic' and url.password=='synthetic-only'


def test_missing_manifest_fails_before_any_database_connection(manifest,monkeypatch):
    monkeypatch.setattr(qa,'MANIFEST',manifest.parent/'not-created.json')
    with pytest.raises(RuntimeError,match='manifest missing'):
        qa.target()


@pytest.mark.parametrize('oid',[41069,49264,49265,32877,0,True])
def test_rejects_original_rehearsal_test_and_invalid_oids(manifest,oid):
    data=json.loads(manifest.read_text())
    data['oid']=oid
    manifest.write_text(json.dumps(data))
    with pytest.raises(RuntimeError,match='Unapproved QA database OID'):
        qa.target()


@pytest.mark.parametrize('url',[
    'postgresql+psycopg://synthetic:synthetic-only@remote.example.com/whatnot_app_dev',
    'postgresql+psycopg://synthetic:synthetic-only@127.0.0.1:5440/whatnot_app_dev',
    'postgresql+psycopg://synthetic:synthetic-only@127.0.0.1:5432/whatnot_tests_20261115_a7e394c2',
    'postgresql+psycopg://synthetic:synthetic-only@127.0.0.1:5432/whatnot_app_dev?options=unsafe',
])
def test_rejects_remote_unrelated_or_overridable_connection_targets(manifest,monkeypatch,url):
    monkeypatch.setattr(qa,'Settings',lambda:SimpleNamespace(database_url=SecretStr(url)))
    with pytest.raises(RuntimeError,match='Unexpected local connection'):
        qa.target()


@pytest.mark.parametrize('patch',[{'database':'whatnot_app_dev'},{'revision':'0004'},
                                  {'fixtures_version':'unapproved'}])
def test_rejects_wrong_manifest_identity_or_schema(manifest,patch):
    data=json.loads(manifest.read_text())
    data.update(patch)
    manifest.write_text(json.dumps(data))
    with pytest.raises(RuntimeError,match='Invalid QA provisioning manifest'):
        qa.target()
