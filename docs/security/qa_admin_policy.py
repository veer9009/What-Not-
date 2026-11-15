"""Explicit local-QA admin admission only; no production configuration changes."""
import os
from ipaddress import ip_address
from pydantic import EmailStr, TypeAdapter

QA_MARKER='chrome-discovery-v1'
BASE_EMAILS=['chrome-buyer@example.com','chrome-seller@example.com']


def require(condition,message):
    if not condition:raise RuntimeError(message)


def configured_admin_email():
    value=os.environ.get('WHATNOT_QA_ADMIN_EMAIL','').strip()
    if not value:return None
    require(os.environ.get('WHATNOT_QA_ENVIRONMENT')==QA_MARKER,'Explicit QA environment marker required for admin admission')
    email=str(TypeAdapter(EmailStr).validate_python(value)).lower()
    require(email not in BASE_EMAILS,'Admin email must differ from existing QA accounts')
    return email


def validate_identity(actual,expected_user):
    database,oid,owner,user,address,port,version,recovery=actual
    require(database=='whatnot_chrome_qa_20261115' and oid==50640 and owner is True
        and user==expected_user and ip_address(address)==ip_address('127.0.0.1')
        and port==5432 and 170000<=version<180000 and recovery is False,'QA server/database identity mismatch')


def validate_roster(rows,admin_email):
    expected=[(BASE_EMAILS[0],'BUYER',True),(BASE_EMAILS[1],'SELLER',True)]
    if admin_email:expected.append((admin_email,'ADMIN',True))
    require(sorted(tuple(r) for r in rows)==sorted(expected),'Unexpected QA account roster or admin admission')
