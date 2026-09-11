import base64
import hashlib
from dataclasses import replace
from pathlib import Path

from app.auth_service import (
    authenticate_user,
    create_user,
    create_session,
    session_username,
    hash_password,
    provision_users,
    upsert_user_hash,
    verify_password,
    verify_session,
)
from app.config import ensure_action_api_key


def _password_hash(password: str) -> str:
    salt = b"fixed-test-salt"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10_000)
    return "pbkdf2_sha256$10000$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def test_startup_generates_an_independent_persistent_session_secret(
    tmp_path: Path, monkeypatch
):
    env_path = tmp_path / ".env"
    for name in (
        "NEGIN_ACTION_API_KEY",
        "NEGIN_OAUTH_CLIENT_SECRET",
        "NEGIN_SESSION_SIGNING_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)

    ensure_action_api_key(env_path)

    values = dict(
        line.split("=", 1)
        for line in env_path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    secrets = {
        values["NEGIN_ACTION_API_KEY"],
        values["NEGIN_OAUTH_CLIENT_SECRET"],
        values["NEGIN_SESSION_SIGNING_SECRET"],
    }
    assert len(secrets) == 3
    assert all(len(value) >= 48 for value in secrets)


def test_password_and_signed_session(settings):
    configured = replace(
        settings, login_username="sample-user", login_password_hash=_password_hash("sample-password")
    )
    assert verify_password("sample-password", configured.login_password_hash)
    assert not verify_password("wrong", configured.login_password_hash)
    token = create_session(configured, "sample-user", now=1_000)
    assert verify_session(configured, token, now=1_001)
    assert not verify_session(configured, token + "x", now=1_001)
    assert not verify_session(configured, token, now=40_000)


def test_generated_password_hash_is_salted_and_verifiable():
    first = hash_password("strong-test-password", iterations=10_000)
    second = hash_password("strong-test-password", iterations=10_000)
    assert first != second
    assert verify_password("strong-test-password", first)
    assert not verify_password("wrong", first)


def test_login_sets_secure_http_only_cookie(client, settings):
    configured = replace(
        settings, login_username="sample-user", login_password_hash=_password_hash("sample-password")
    )
    client.app.state.settings = configured
    bad = client.post("/auth/login", json={"username": "sample-user", "password": "wrong"})
    assert bad.status_code == 401
    good = client.post(
        "/auth/login", json={"username": "sample-user", "password": "sample-password"}
    )
    assert good.status_code == 200
    cookie = good.headers["set-cookie"]
    assert "negin_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie


def test_database_user_can_login_and_session_keeps_own_username(client, settings):
    upsert_user_hash(settings, "m.etemadi", _password_hash("7055"))

    assert authenticate_user(settings, "m.etemadi", "7055") == "m.etemadi"
    assert authenticate_user(settings, "m.etemadi", "wrong") is None

    response = client.post(
        "/auth/login", json={"username": "m.etemadi", "password": "7055"}
    )
    assert response.status_code == 200
    from http.cookies import SimpleCookie

    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    token = cookie["negin_session"].value
    assert session_username(settings, token) == "m.etemadi"


def test_provisioned_user_uses_unique_one_time_activation_before_data_access(
    client, settings
):
    result = provision_users(
        settings,
        [
            {
                "username": "A.kamran",
                "personnel_id": 22,
                "full_name": "عارف کامران",
                "role": "فروشنده",
                "branch": "دفتر فروش البرز",
                "sales_line": "لاین مارکت",
                "phone": "09120000000",
                "phone_status": "معتبر",
                "supervisor_personnel_id": 14,
            }
        ],
    )
    assert {key: result[key] for key in ("created", "updated", "claimed_existing")} == {
        "created": 1,
        "updated": 0,
        "claimed_existing": 0,
    }
    activation_token = result["activation_tokens"]["A.kamran"]

    login = client.post("/auth/login", json={"username": "A.kamran", "password": "1"})
    assert login.status_code == 401

    activated = client.post(
        "/auth/activate",
        json={"activation_token": activation_token, "new_password": "StrongPass9"},
    )
    assert activated.status_code == 200
    assert activated.json()["activated"] is True
    assert activated.json()["must_change_password"] is False
    assert activated.json()["phone"] == "09120000000"
    from http.cookies import SimpleCookie

    cookie = SimpleCookie()
    cookie.load(activated.headers["set-cookie"])
    session_header = {"Cookie": f"negin_session={cookie['negin_session'].value}"}

    assert client.get("/chat/conversations", headers=session_header).status_code == 200
    reused = client.post(
        "/auth/activate",
        json={"activation_token": activation_token, "new_password": "OtherPass10"},
    )
    assert reused.status_code == 400
    assert authenticate_user(settings, "A.kamran", "1") is None
    assert authenticate_user(settings, "A.kamran", "StrongPass9") == "A.kamran"


def test_provisioning_can_claim_matching_legacy_username(settings):
    create_user(settings, "m.etemadi", "7055")
    result = provision_users(
        settings,
        [
            {
                "username": "M.etemadi",
                "personnel_id": 770,
                "full_name": "محمود اعتمادی",
                "role": "سرپرست",
                "branch": "دفتر فروش گیلان",
                "sales_line": "لاین مارکت",
                "phone": "09115995662",
                "phone_status": "معتبر",
                "supervisor_personnel_id": None,
            }
        ],
    )
    assert result["claimed_existing"] == 1
    assert authenticate_user(settings, "m.etemadi", "7055") is None
    token = result["activation_tokens"]["M.etemadi"]
    from app.auth_service import activate_user

    assert activate_user(settings, token, "Replacement9") == "m.etemadi"
    assert authenticate_user(settings, "m.etemadi", "Replacement9") == "m.etemadi"


def test_session_signature_is_independent_of_action_api_key(settings):
    create_user(settings, "session.user", "StrongPass9")
    token = create_session(settings, "session.user", now=1_000)
    changed_action_key = replace(settings, action_api_key="rotated-action-key")

    assert session_username(changed_action_key, token, now=1_001) == "session.user"


def test_password_change_and_logout_revoke_prior_sessions(client, settings):
    create_user(settings, "revoke.user", "StrongPass9")
    login = client.post(
        "/auth/login", json={"username": "revoke.user", "password": "StrongPass9"}
    )
    from http.cookies import SimpleCookie

    first_cookie = SimpleCookie()
    first_cookie.load(login.headers["set-cookie"])
    old_token = first_cookie["negin_session"].value
    changed = client.post(
        "/auth/change-password",
        json={"current_password": "StrongPass9", "new_password": "NewStrong10"},
        headers={"Cookie": f"negin_session={old_token}"},
    )
    assert changed.status_code == 200
    assert session_username(settings, old_token) is None

    fresh_cookie = SimpleCookie()
    fresh_cookie.load(changed.headers["set-cookie"])
    fresh_token = fresh_cookie["negin_session"].value
    assert session_username(settings, fresh_token) == "revoke.user"
    logged_out = client.post(
        "/auth/logout", headers={"Cookie": f"negin_session={fresh_token}"}
    )
    assert logged_out.status_code == 200
    assert session_username(settings, fresh_token) is None


def test_activation_tokens_are_unique_expiring_and_shared_passwords_are_rejected(settings):
    users = [
        {"username": "first.user", "personnel_id": 901},
        {"username": "second.user", "personnel_id": 902},
    ]
    result = provision_users(settings, users, activation_ttl_seconds=300)
    tokens = result["activation_tokens"]

    assert tokens["first.user"] != tokens["second.user"]
    from app.auth_service import activate_user

    assert (
        activate_user(
            settings,
            tokens["first.user"],
            "StrongPass9",
            now=result["activation_expires_at"] + 1,
        )
        is None
    )
    import pytest

    with pytest.raises(ValueError, match="shared temporary passwords are disabled"):
        provision_users(settings, users, temporary_password="shared")


def test_activation_delivery_failure_rolls_back_provisioning(settings):
    from app.database import sqlite_connection
    import pytest

    def fail_delivery(_result):
        raise OSError("activation destination unavailable")

    with pytest.raises(OSError, match="destination unavailable"):
        provision_users(
            settings,
            [{"username": "rollback.user", "personnel_id": 903}],
            activation_sink=fail_delivery,
        )

    with sqlite_connection(settings.sqlite_path) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM users WHERE username='rollback.user'"
            ).fetchone()
            is None
        )
