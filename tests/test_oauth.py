import base64
import hashlib
import re
from dataclasses import replace
from urllib.parse import parse_qs, urlparse


PKCE_VERIFIER = "v" * 43
PKCE_CHALLENGE = base64.urlsafe_b64encode(
    hashlib.sha256(PKCE_VERIFIER.encode("ascii")).digest()
).rstrip(b"=").decode("ascii")
CHATGPT_REDIRECT = "https://chatgpt.com/aip/g-test/oauth/callback"
OPENAI_REDIRECT = "https://oauth.openai.com/aip/g-test/oauth/callback"


def _password_hash(password: str) -> str:
    salt = b"oauth-test-salt"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10_000)
    return "pbkdf2_sha256$10000$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def _configured(settings):
    return replace(
        settings,
        login_username="Admin",
        login_password_hash=_password_hash("test-password"),
        oauth_client_id="neginai-chatgpt",
        oauth_client_secret="oauth-secret",
        oauth_redirect_uris=(CHATGPT_REDIRECT, OPENAI_REDIRECT),
    )


def test_oauth_rejects_untrusted_redirect(client, settings):
    client.app.state.settings = _configured(settings)
    response = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": "neginai-chatgpt",
            "redirect_uri": "https://attacker.example/callback",
            "state": "state-1",
        },
    )
    assert response.status_code == 400
    assert "attacker.example" in response.text


def test_oauth_accepts_only_exact_configured_callbacks(client, settings):
    client.app.state.settings = _configured(settings)
    response = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": "neginai-chatgpt",
            "redirect_uri": OPENAI_REDIRECT,
            "state": "state-1",
            "scope": "company.read",
            "code_challenge": PKCE_CHALLENGE,
            "code_challenge_method": "s256",
        },
    )
    assert response.status_code == 200

    evil = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": "neginai-chatgpt",
            "redirect_uri": "https://oauth.openai.com/aip/another-gpt/oauth/callback",
            "scope": "company.read",
            "code_challenge": PKCE_CHALLENGE,
            "code_challenge_method": "S256",
        },
    )
    assert evil.status_code == 400


def test_oauth_requires_s256_pkce(client, settings):
    client.app.state.settings = _configured(settings)
    base = {
        "response_type": "code",
        "client_id": "neginai-chatgpt",
        "redirect_uri": CHATGPT_REDIRECT,
        "scope": "company.read",
    }

    missing = client.get("/oauth/authorize", params=base)
    plain = client.get(
        "/oauth/authorize",
        params={
            **base,
            "code_challenge": "p" * 43,
            "code_challenge_method": "plain",
        },
    )

    assert missing.status_code == 400
    assert plain.status_code == 400


def test_oauth_login_uses_shared_rate_limiter(client, settings):
    from app.login_rate_limit import LocalLoginRateLimiter

    client.app.state.settings = _configured(settings)
    client.app.state.login_rate_limiter = LocalLoginRateLimiter(limit=1)
    page = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": "neginai-chatgpt",
            "redirect_uri": CHATGPT_REDIRECT,
            "scope": "company.read",
            "code_challenge": PKCE_CHALLENGE,
            "code_challenge_method": "S256",
        },
    )
    hidden = dict(re.findall(r'name="([^"]+)" value="([^"]*)"', page.text))

    first = client.post(
        "/oauth/authorize",
        data={**hidden, "username": "Admin", "password": "wrong"},
    )
    blocked = client.post(
        "/oauth/authorize",
        data={**hidden, "username": "Admin", "password": "wrong"},
    )

    assert first.status_code == 200
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_oauth_setup_hides_secret_until_admin_login(client, settings):
    configured = _configured(settings)
    client.app.state.settings = configured
    anonymous = client.get("/oauth/setup")
    assert anonymous.status_code == 200
    assert configured.oauth_client_secret not in anonymous.text
    assert anonymous.headers["cache-control"].startswith("no-store")

    login = client.post(
        "/auth/login", json={"username": "Admin", "password": "test-password"}
    )
    assert login.status_code == 200
    from http.cookies import SimpleCookie

    cookie = SimpleCookie()
    cookie.load(login.headers["set-cookie"])
    session = cookie["negin_session"].value
    authorized = client.get("/oauth/setup", headers={"Cookie": f"negin_session={session}"})
    assert authorized.status_code == 200
    assert configured.oauth_client_secret in authorized.text
    assert "https://ai.neginpakhsh.com/oauth/authorize" in authorized.text


def test_oauth_authorization_code_and_bearer_flow(client, settings, monkeypatch):
    configured = _configured(settings)
    client.app.state.settings = configured
    redirect_uri = CHATGPT_REDIRECT
    page = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": configured.oauth_client_id,
            "redirect_uri": redirect_uri,
            "state": "state-1",
            "scope": "company.read",
            "code_challenge": PKCE_CHALLENGE,
            "code_challenge_method": "S256",
        },
    )
    assert page.status_code == 200
    assert "رمز عبور به ChatGPT ارسال نمی‌شود" in page.text

    import re

    hidden = dict(re.findall(r'name="([^"]+)" value="([^"]*)"', page.text))
    login = client.post(
        "/oauth/authorize",
        data={**hidden, "username": "Admin", "password": "test-password"},
        follow_redirects=False,
    )
    assert login.status_code == 303
    query = parse_qs(urlparse(login.headers["location"]).query)
    assert query["state"] == ["state-1"]

    basic = base64.b64encode(
        f"{configured.oauth_client_id}:{configured.oauth_client_secret}".encode()
    ).decode()
    exchanged = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": query["code"][0],
            "redirect_uri": redirect_uri,
            "code_verifier": PKCE_VERIFIER,
        },
        headers={"Authorization": f"Basic {basic}"},
    )
    assert exchanged.status_code == 200
    token = exchanged.json()["access_token"]
    assert exchanged.json()["refresh_token"]

    def fake_chat(_settings, message, conversation_id, username):
        assert username == configured.login_username
        return {"conversation_id": conversation_id or "oauth-chat", "answer": message}

    monkeypatch.setattr("app.routes.chat.chat", fake_chat)
    chat_response = client.post(
        "/chat",
        json={"message": "گزارش فروش"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chat_response.status_code == 200
    assert chat_response.json()["answer"] == "گزارش فروش"

    reused = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": query["code"][0],
            "redirect_uri": redirect_uri,
            "code_verifier": PKCE_VERIFIER,
        },
        headers={"Authorization": f"Basic {basic}"},
    )
    assert reused.status_code == 400
    assert reused.json()["error"] == "invalid_grant"


def test_database_user_can_complete_oauth_authorization(client, settings):
    from app.auth_service import upsert_user_hash
    from app.database import sqlite_connection

    configured = _configured(settings)
    client.app.state.settings = configured
    upsert_user_hash(configured, "m.etemadi", _password_hash("7055"))
    redirect_uri = CHATGPT_REDIRECT
    page = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": configured.oauth_client_id,
            "redirect_uri": redirect_uri,
            "state": "user-state",
            "scope": "company.read",
            "code_challenge": PKCE_CHALLENGE,
            "code_challenge_method": "S256",
        },
    )
    hidden = dict(re.findall(r'name="([^"]+)" value="([^"]*)"', page.text))
    login = client.post(
        "/oauth/authorize",
        data={**hidden, "username": "m.etemadi", "password": "7055"},
        follow_redirects=False,
    )

    assert login.status_code == 303
    code = parse_qs(urlparse(login.headers["location"]).query)["code"][0]
    from app.oauth_service import _hash_secret

    with sqlite_connection(configured.sqlite_path) as conn:
        row = conn.execute(
            "SELECT username FROM oauth_codes WHERE code_hash=?",
            (_hash_secret(code),),
        ).fetchone()
    assert row["username"] == "m.etemadi"


def test_oauth_token_accepts_json_and_camel_case_credentials(client, settings):
    from app.oauth_service import create_authorization_code

    configured = _configured(settings)
    client.app.state.settings = configured
    redirect_uri = CHATGPT_REDIRECT
    code = create_authorization_code(
        configured, "Admin", configured.oauth_client_id, redirect_uri, "company.read",
        PKCE_CHALLENGE, "S256",
    )
    response = client.post(
        "/oauth/token",
        json={
            "grantType": "authorization_code",
            "clientId": configured.oauth_client_id,
            "clientSecret": configured.oauth_client_secret,
            "code": code,
            "redirectUri": redirect_uri,
            "codeVerifier": PKCE_VERIFIER,
        },
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_oauth_token_trims_pasted_client_credentials(client, settings):
    from app.oauth_service import create_authorization_code

    configured = _configured(settings)
    client.app.state.settings = configured
    redirect_uri = CHATGPT_REDIRECT
    code = create_authorization_code(
        configured, "Admin", configured.oauth_client_id, redirect_uri, "company.read",
        PKCE_CHALLENGE, "S256",
    )
    response = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": f"  {configured.oauth_client_id} ",
            "client_secret": f" {configured.oauth_client_secret}\n",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": PKCE_VERIFIER,
        },
    )
    assert response.status_code == 200


def test_oauth_invalid_client_does_not_write_sqlite_diagnostics(client, settings):
    from app.database import sqlite_connection

    configured = _configured(settings)
    client.app.state.settings = configured
    before = hashlib.sha256(configured.sqlite_path.read_bytes()).digest()
    response = client.post(
        "/oauth/token",
        json={
            "grantType": "authorization_code",
            "clientId": configured.oauth_client_id,
            "clientSecret": "wrong-secret",
            "code": "unused-code",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"] == "invalid_client"
    assert hashlib.sha256(configured.sqlite_path.read_bytes()).digest() == before

    with sqlite_connection(configured.sqlite_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM oauth_client_diagnostics"
        ).fetchone()[0]
    assert count == 0


def test_oauth_token_rejects_query_credentials_without_sqlite_write(client, settings):
    from app.database import sqlite_connection

    configured = _configured(settings)
    client.app.state.settings = configured
    response = client.post(
        "/oauth/token",
        params={
            "client_id": configured.oauth_client_id,
            "client_secret": configured.oauth_client_secret,
        },
        data={"grant_type": "authorization_code", "code": "unused"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"
    with sqlite_connection(configured.sqlite_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM oauth_client_diagnostics"
        ).fetchone()[0]
    assert count == 0


def test_inactive_user_cannot_refresh_or_use_oauth_tokens(settings):
    from app.auth_service import create_user
    from app.database import sqlite_connection
    from app.oauth_service import (
        create_authorization_code,
        exchange_authorization_code,
        exchange_refresh_token,
        verify_access_token,
    )

    configured = _configured(settings)
    create_user(configured, "oauth.user", "StrongPass9")
    redirect_uri = CHATGPT_REDIRECT
    code = create_authorization_code(
        configured,
        "oauth.user",
        configured.oauth_client_id,
        redirect_uri,
        "company.read",
        PKCE_CHALLENGE,
        "S256",
    )
    pair = exchange_authorization_code(
        configured, code, configured.oauth_client_id, redirect_uri, PKCE_VERIFIER
    )
    assert pair is not None

    with sqlite_connection(configured.sqlite_path) as conn:
        conn.execute("UPDATE users SET active=0 WHERE username='oauth.user'")

    assert verify_access_token(configured, pair["access_token"]) is None
    assert exchange_refresh_token(configured, pair["refresh_token"]) is None
    with sqlite_connection(configured.sqlite_path) as conn:
        remaining = conn.execute(
            "SELECT COUNT(*) FROM oauth_tokens WHERE username='oauth.user' AND revoked=0"
        ).fetchone()[0]
    assert remaining == 0


def test_password_change_revokes_oauth_token_family(settings):
    from app.auth_service import change_password, create_user
    from app.oauth_service import (
        create_authorization_code,
        exchange_authorization_code,
        exchange_refresh_token,
        verify_access_token,
    )

    configured = _configured(settings)
    create_user(configured, "password.user", "StrongPass9")
    redirect_uri = CHATGPT_REDIRECT
    code = create_authorization_code(
        configured,
        "password.user",
        configured.oauth_client_id,
        redirect_uri,
        "company.read",
        PKCE_CHALLENGE,
        "S256",
    )
    pair = exchange_authorization_code(
        configured, code, configured.oauth_client_id, redirect_uri, PKCE_VERIFIER
    )
    assert pair is not None

    assert change_password(
        configured, "password.user", "StrongPass9", "Replacement10"
    )
    assert verify_access_token(configured, pair["access_token"]) is None
    assert exchange_refresh_token(configured, pair["refresh_token"]) is None
