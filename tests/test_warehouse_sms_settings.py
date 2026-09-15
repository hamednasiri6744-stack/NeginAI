import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app import warehouse_sms_settings as sms
from app.routes import warehouse_assistant as routes
from app.routes.dependencies import require_session_user


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    path.write_bytes(b'# keep exactly\r\nUNRELATED="original # value"\r\nASANAK_USERNAME=09120000000\r\nASANAK_SOURCE=982100000000\r\nASANAK_PASSWORD=original-secret\r\n')
    monkeypatch.setattr(sms, 'ENV_PATH', path)
    return path


def test_reads_saved_account_without_returning_password(env_file):
    data = sms.read_settings()
    assert data['configured'] is True
    assert data['password_configured'] is True
    assert data['source'] == '982100000000'
    assert 'original-secret' not in json.dumps(data)
    assert 'password' not in data


@pytest.mark.parametrize('secret', ['', 'new#pass', "quote'pass\\${NO_EXPANSION}", 'pass$#"123'])
def test_save_roundtrip_preserves_existing_env_and_empty_password(env_file, secret):
    data = sms.save_settings({'username': '۰۹۱۲۰۰۰۰۰۰۰۱', 'source': '982100000001', 'password': secret})
    values = sms.dotenv_values(env_file, interpolate=False)
    assert values['ASANAK_PASSWORD'] == (secret or 'original-secret')
    assert values['ASANAK_USERNAME'] == '091200000001'
    assert values['ASANAK_SOURCE'] == '982100000001'
    assert env_file.read_bytes().startswith(b'# keep exactly\r\nUNRELATED="original # value"\r\n')
    assert data == sms.read_settings()
    assert values['ASANAK_PASSWORD'] not in json.dumps(data)


@pytest.mark.parametrize('payload', [
    {}, [], {'username': 'x', 'source': '12345'},
    {'username': '12345', 'source': '12345', 'password': '\nINJECT=1'},
    {'username': '12345', 'source': '12345', 'password': 123},
    {'username': '12345', 'source': '12345', 'send_url': 'https://invalid.example'},
])
def test_invalid_settings_do_not_modify_file(env_file, payload):
    before = env_file.read_bytes()
    with pytest.raises(sms.SmsSettingsError):
        sms.save_settings(payload)
    assert env_file.read_bytes() == before


def test_initial_setup_requires_password(env_file):
    env_file.write_text('UNRELATED=keep\n')
    with pytest.raises(sms.SmsSettingsError):
        sms.save_settings({'username': '12345', 'source': '12345'})
    assert env_file.read_text() == 'UNRELATED=keep\n'


def test_duplicate_and_export_keys_are_replaced(env_file):
    with env_file.open('a') as f:
        f.write('export ASANAK_PASSWORD=duplicate\n')
    sms.save_settings({'username': '12345', 'source': '12345', 'password': 'new-secret'})
    assert env_file.read_text().count('ASANAK_PASSWORD=') == 1


@pytest.fixture
def api_client(env_file, monkeypatch):
    app = FastAPI()
    app.state.settings = SimpleNamespace()
    async def identity(request: Request):
        request.state.username = request.headers.get('X-Test-User', 'worker')
    app.dependency_overrides[require_session_user] = identity
    monkeypatch.setattr(routes, '_capabilities', lambda request, username: {'warehouse.assistant.view'})
    monkeypatch.setattr(routes, '_is_admin', lambda request, username: username == 'admin')
    app.include_router(routes.router)
    with TestClient(app) as client:
        yield client


def test_worker_cannot_read_or_save(api_client, env_file):
    before = env_file.read_bytes()
    for method in ['get', 'put']:
        response = getattr(api_client, method)('/warehouse-assistant/api/sms-settings')
        assert response.status_code == 403
        assert 'original-secret' not in response.text
    assert env_file.read_bytes() == before


def test_admin_api_saves_and_rereads_without_echoing_secret(api_client):
    headers = {'X-Test-User': 'admin', 'X-Warehouse-Settings': '1', 'Origin': 'http://testserver'}
    response = api_client.put('/warehouse-assistant/api/sms-settings', headers=headers,
                             json={'username': '12345', 'source': '982112345', 'password': 'only-in-file'})
    assert response.status_code == 200
    assert 'only-in-file' not in response.text
    assert response.headers['cache-control'] == 'no-store'
    read = api_client.get('/warehouse-assistant/api/sms-settings', headers=headers)
    assert read.json() == response.json()
    assert read.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('extra', [{}, {'X-Warehouse-Settings': '1', 'Origin': 'https://elsewhere.example'}])
def test_cross_origin_or_missing_custom_header_cannot_save(api_client, env_file, extra):
    before = env_file.read_bytes()
    response = api_client.put('/warehouse-assistant/api/sms-settings', headers={'X-Test-User': 'admin', **extra},
                             json={'username': '12345', 'source': '12345', 'password': 'never-save'})
    assert response.status_code == 403
    assert env_file.read_bytes() == before


def test_invalid_api_secret_is_not_reflected_in_error(api_client):
    response = api_client.put('/warehouse-assistant/api/sms-settings',
                             headers={'X-Test-User': 'admin', 'X-Warehouse-Settings': '1'},
                             json={'username': '12345', 'source': '12345', 'password': 'secret\nINJECT=1'})
    assert response.status_code == 422
    assert 'secret' not in response.text and 'INJECT' not in response.text


def test_anonymous_cannot_read_settings(env_file):
    app = FastAPI()
    app.include_router(routes.router)
    with TestClient(app) as client:
        assert client.get('/warehouse-assistant/api/sms-settings').status_code == 401
