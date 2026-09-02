from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from datetime import datetime

from app.config import Settings
from app.database import sqlite_connection

AUTH_CODE_SECONDS = 5 * 60
ACCESS_TOKEN_SECONDS = 60 * 60
REFRESH_TOKEN_SECONDS = 30 * 24 * 60 * 60
DEFAULT_SCOPE = "company.read"


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pkce_matches(verifier: str, challenge: str, method: str | None) -> bool:
    if not challenge:
        return True
    if method in (None, "plain"):
        return hmac.compare_digest(verifier, challenge)
    if method == "S256":
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        actual = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return hmac.compare_digest(actual, challenge)
    return False


def create_authorization_code(
    settings: Settings,
    username: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    now: int | None = None,
) -> str:
    code = secrets.token_urlsafe(48)
    expires_at = (now or int(time.time())) + AUTH_CODE_SECONDS
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO oauth_codes
               (code_hash, username, client_id, redirect_uri, scope, code_challenge,
                code_challenge_method, expires_at, used)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                _hash_secret(code), username, client_id, redirect_uri, scope,
                code_challenge, code_challenge_method, expires_at,
            ),
        )
    return code


def _issue_token_pair(conn, username: str, scope: str, now: int) -> dict[str, object]:
    access_token = secrets.token_urlsafe(48)
    refresh_token = secrets.token_urlsafe(48)
    created_at = datetime.utcnow().isoformat()
    conn.executemany(
        """INSERT INTO oauth_tokens
           (token_hash, username, token_type, scope, expires_at, revoked, created_at)
           VALUES (?, ?, ?, ?, ?, 0, ?)""",
        [
            (_hash_secret(access_token), username, "access", scope, now + ACCESS_TOKEN_SECONDS, created_at),
            (_hash_secret(refresh_token), username, "refresh", scope, now + REFRESH_TOKEN_SECONDS, created_at),
        ],
    )
    return {
        "access_token": access_token,
        # GPT Actions expects the standard lower-case OAuth token type in the
        # token endpoint response before it sends the bearer-authenticated action.
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_SECONDS,
        "refresh_token": refresh_token,
        "scope": scope,
    }


def exchange_authorization_code(
    settings: Settings,
    code: str,
    client_id: str,
    redirect_uri: str,
    code_verifier: str = "",
    now: int | None = None,
) -> dict[str, object] | None:
    current = now or int(time.time())
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT * FROM oauth_codes WHERE code_hash=?",
            (_hash_secret(code),),
        ).fetchone()
        if not row or row["used"] or row["expires_at"] < current:
            return None
        if not hmac.compare_digest(row["client_id"], client_id):
            return None
        if not hmac.compare_digest(row["redirect_uri"], redirect_uri):
            return None
        if not _pkce_matches(code_verifier, row["code_challenge"] or "", row["code_challenge_method"]):
            return None
        updated = conn.execute(
            "UPDATE oauth_codes SET used=1 WHERE code_hash=? AND used=0",
            (_hash_secret(code),),
        )
        if updated.rowcount != 1:
            return None
        return _issue_token_pair(conn, row["username"], row["scope"], current)


def exchange_refresh_token(
    settings: Settings, refresh_token: str, now: int | None = None
) -> dict[str, object] | None:
    current = now or int(time.time())
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            """SELECT username, scope, expires_at, revoked FROM oauth_tokens
               WHERE token_hash=? AND token_type='refresh'""",
            (_hash_secret(refresh_token),),
        ).fetchone()
        if not row or row["revoked"] or row["expires_at"] < current:
            return None
        conn.execute(
            "UPDATE oauth_tokens SET revoked=1 WHERE token_hash=?",
            (_hash_secret(refresh_token),),
        )
        return _issue_token_pair(conn, row["username"], row["scope"], current)


def verify_access_token(settings: Settings, token: str, now: int | None = None) -> str | None:
    current = now or int(time.time())
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            """SELECT username, expires_at, revoked FROM oauth_tokens
               WHERE token_hash=? AND token_type='access'""",
            (_hash_secret(token),),
        ).fetchone()
    if not row or row["revoked"] or row["expires_at"] < current:
        return None
    return str(row["username"])
