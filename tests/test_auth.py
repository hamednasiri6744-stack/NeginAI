import base64
import hashlib
from dataclasses import replace

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


def _password_hash(password: str) -> str:
    salt = b"fixed-test-salt"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 10_000)
    return "pbkdf2_sha256$10000$%s$%s" % (
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


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


def test_provisioned_user_must_change_temporary_password_before_data_access(
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
        temporary_password="1",
    )
    assert result == {"created": 1, "updated": 0, "claimed_existing": 0}

    login = client.post("/auth/login", json={"username": "A.kamran", "password": "1"})
    assert login.status_code == 200
    assert login.json()["must_change_password"] is True
    assert login.json()["phone"] == "09120000000"
    from http.cookies import SimpleCookie

    cookie = SimpleCookie()
    cookie.load(login.headers["set-cookie"])
    session_header = {"Cookie": f"negin_session={cookie['negin_session'].value}"}

    blocked = client.get("/chat/conversations", headers=session_header)
    assert blocked.status_code == 428

    changed = client.post(
        "/auth/change-password",
        json={"current_password": "1", "new_password": "StrongPass9"},
        headers=session_header,
    )
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False
    assert client.get("/chat/conversations", headers=session_header).status_code == 200
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
        temporary_password="1",
    )
    assert result == {"created": 0, "updated": 0, "claimed_existing": 1}
    assert authenticate_user(settings, "m.etemadi", "7055") is None
    assert authenticate_user(settings, "m.etemadi", "1") == "m.etemadi"
