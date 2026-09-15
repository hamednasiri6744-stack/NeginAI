import json
from dataclasses import replace
from pathlib import Path
import pytest
from app.config import Settings
from app.warehouse_transfer_deployment import configure_transfer_bridge


def settings():
    return Settings(sql_server='report-server',sql_database='report-db',sql_username='readonly',
        sql_password='report-secret',sql_driver='test',sql_trust_certificate=True,
        sql_query_timeout=30,sql_max_rows=1000,action_api_key='test',sqlite_path=Path('test.db'),
        varanegar_receipt_sql_server='192.168.1.171',varanegar_receipt_sql_database='NeginPakhsh',
        varanegar_receipt_sql_username='neginai',varanegar_receipt_sql_password='existing-secret')


def profile(**overrides):
    return dict(version=1,enabled=True,commit_enabled=False,credential_source='existing_receipt_bridge',
        expected_server='192.168.1.171',expected_database='NeginPakhsh',expected_username='neginai',**overrides)


def test_absent_profile_preserves_settings(tmp_path):
    original=settings()
    assert configure_transfer_bridge(original,tmp_path/'absent.json') is original


@pytest.mark.parametrize('commit',[False,True])
def test_explicit_profile_only_changes_transfer_settings(tmp_path,commit):
    p=tmp_path/'profile.json';data=profile();data['commit_enabled']=commit
    p.write_text(json.dumps(data));original=settings();result=configure_transfer_bridge(original,p)
    assert result.varanegar_transfer_bridge_enabled is True
    assert result.varanegar_transfer_commit_enabled is commit
    assert result.varanegar_transfer_sql_password=='existing-secret'
    assert result.sql_username=='readonly' and result.sql_password=='report-secret'
    assert not original.varanegar_transfer_bridge_enabled
    assert 'secret' not in p.read_text()


@pytest.mark.parametrize('change',[{'commit_enabled':'true'},{'enabled':False,'commit_enabled':True},
    {'credential_source':'reporting'},{'expected_username':'other'},{'version':True},{'password':'bad'}])
def test_bad_profile_disables_only_transfer_and_does_not_log_secrets(tmp_path,change,caplog):
    p=tmp_path/'profile.json';data=profile();data.update(change);p.write_text(json.dumps(data))
    original=replace(settings(),varanegar_transfer_bridge_enabled=True,varanegar_transfer_commit_enabled=True)
    result=configure_transfer_bridge(original,p)
    assert not result.varanegar_transfer_bridge_enabled and not result.varanegar_transfer_commit_enabled
    assert result.sql_password=='report-secret'
    assert 'existing-secret' not in caplog.text and 'bad' not in caplog.text


def test_missing_existing_secret_does_not_fall_back_to_report_login(tmp_path):
    p=tmp_path/'profile.json';p.write_text(json.dumps(profile()))
    result=configure_transfer_bridge(replace(settings(),varanegar_receipt_sql_password=''),p)
    assert not result.varanegar_transfer_bridge_enabled
    assert result.varanegar_transfer_sql_username==''


def test_corrupt_profile_does_not_break_warehouse(tmp_path):
    p=tmp_path/'profile.json';p.write_text('{bad')
    assert not configure_transfer_bridge(settings(),p).varanegar_transfer_bridge_enabled
