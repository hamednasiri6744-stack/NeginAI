from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from typing import Any, Callable, Iterable

from app.config import Settings
from app.database import sqlite_connection

SESSION_SECONDS = 8 * 60 * 60
ACTIVATION_SECONDS = 60 * 60
PASSWORD_HASH_ITERATIONS = 260_000
USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{1,99}$")
_EPHEMERAL_SESSION_SECRET = secrets.token_bytes(48)


def _ensure_identity_tables(conn) -> None:
    """Install additive identity state without changing the legacy users schema."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS auth_session_state (
          username TEXT PRIMARY KEY COLLATE NOCASE,
          generation INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_activations (
          token_hash TEXT PRIMARY KEY,
          username TEXT NOT NULL COLLATE NOCASE,
          expires_at INTEGER NOT NULL,
          used_at TEXT,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_user_activations_user
          ON user_activations(username, expires_at);
        """
    )


def _session_signing_key(settings: Settings) -> bytes:
    """Return a domain-separated session key that never uses the action API key."""
    configured = settings.session_signing_secret.strip()
    root = configured or settings.oauth_client_secret
    root_bytes = root.encode("utf-8") if root else _EPHEMERAL_SESSION_SECRET
    return hmac.new(root_bytes, b"NeginAI/session-signing/v2", hashlib.sha256).digest()


def _session_generation(conn, username: str) -> int:
    _ensure_identity_tables(conn)
    row = conn.execute(
        "SELECT generation FROM auth_session_state WHERE username=?",
        (username,),
    ).fetchone()
    if row is not None:
        return int(row["generation"])
    now = str(time.time())
    conn.execute(
        "INSERT OR IGNORE INTO auth_session_state(username, generation, updated_at) VALUES (?, 0, ?)",
        (username, now),
    )
    return 0


def _revoke_user_security_state(conn, username: str, now: str | None = None) -> None:
    """Revoke every session, OAuth grant, and activation for one identity."""
    _ensure_identity_tables(conn)
    changed_at = now or str(time.time())
    conn.execute(
        """INSERT INTO auth_session_state(username, generation, updated_at)
           VALUES (?, 1, ?)
           ON CONFLICT(username) DO UPDATE SET
             generation=auth_session_state.generation + 1,
             updated_at=excluded.updated_at""",
        (username, changed_at),
    )
    conn.execute("UPDATE oauth_tokens SET revoked=1 WHERE username=?", (username,))
    conn.execute("UPDATE oauth_codes SET used=1 WHERE username=? AND used=0", (username,))
    conn.execute(
        "UPDATE user_activations SET used_at=? WHERE username=? AND used_at IS NULL",
        (changed_at, username),
    )


def revoke_user_sessions(settings: Settings, username: str) -> None:
    with sqlite_connection(settings.sqlite_path) as conn:
        _ensure_identity_tables(conn)
        changed_at = str(time.time())
        conn.execute(
            """INSERT INTO auth_session_state(username, generation, updated_at)
               VALUES (?, 1, ?)
               ON CONFLICT(username) DO UPDATE SET
                 generation=auth_session_state.generation + 1,
                 updated_at=excluded.updated_at""",
            (username, changed_at),
        )


def revoke_user_credentials(settings: Settings, username: str) -> None:
    """Public seam for administrative password reset/deactivation integrations."""
    with sqlite_connection(settings.sqlite_path) as conn:
        _revoke_user_security_state(conn, username)


def revoke_user_credentials_in_transaction(
    conn: Any, username: str, *, now: str | None = None
) -> None:
    """Atomically revoke credentials inside an existing identity transaction."""
    _revoke_user_security_state(conn, username, now=now)


def hash_password(password: str, iterations: int = PASSWORD_HASH_ITERATIONS) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256$%d$%s$%s" % (
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64)
        expected = base64.urlsafe_b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def upsert_user_hash(
    settings: Settings,
    username: str,
    password_hash: str,
    active: bool = True,
) -> None:
    clean_username = username.strip()
    if not clean_username or len(clean_username) > 100:
        raise ValueError("username must contain 1 to 100 characters")
    if not password_hash.startswith("pbkdf2_sha256$"):
        raise ValueError("unsupported password hash")
    now = str(time.time())
    with sqlite_connection(settings.sqlite_path) as conn:
        existing = conn.execute(
            "SELECT username FROM users WHERE username=?",
            (clean_username,),
        ).fetchone()
        conn.execute(
            """INSERT INTO users
               (username, password_hash, active, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(username) DO UPDATE SET
                 password_hash=excluded.password_hash,
                 active=excluded.active,
                 updated_at=excluded.updated_at""",
            (clean_username, password_hash, int(active), now, now),
        )
        if existing is not None:
            _revoke_user_security_state(conn, str(existing["username"]), now)


def create_user(settings: Settings, username: str, password: str) -> None:
    upsert_user_hash(settings, username, hash_password(password), True)


def provision_users(
    settings: Settings,
    users: Iterable[dict[str, Any]],
    temporary_password: str | None = None,
    activation_ttl_seconds: int = ACTIVATION_SECONDS,
    activation_sink: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Provision accounts with unique, hashed, short-lived activation secrets."""
    prepared = list(users)
    if not prepared:
        return {
            "created": 0,
            "updated": 0,
            "claimed_existing": 0,
            "activation_tokens": {},
            "activation_expires_at": None,
        }
    if temporary_password is not None:
        raise ValueError(
            "shared temporary passwords are disabled; use one-time activation tokens"
        )
    if activation_ttl_seconds < 300 or activation_ttl_seconds > 24 * 60 * 60:
        raise ValueError("activation TTL must be between 5 minutes and 24 hours")

    seen_usernames: set[str] = set()
    seen_personnel_ids: set[int] = set()
    for item in prepared:
        username = str(item.get("username") or "").strip()
        personnel_id = int(item["personnel_id"])
        key = username.casefold()
        if not USERNAME_PATTERN.fullmatch(username):
            raise ValueError(f"invalid generated username: {username}")
        if key in seen_usernames:
            raise ValueError(f"duplicate generated username: {username}")
        if personnel_id in seen_personnel_ids:
            raise ValueError(f"duplicate personnel id: {personnel_id}")
        seen_usernames.add(key)
        seen_personnel_ids.add(personnel_id)

    current = int(time.time())
    now = str(current)
    activation_expires_at = current + activation_ttl_seconds
    counts = {"created": 0, "updated": 0, "claimed_existing": 0}
    activation_tokens: dict[str, str] = {}
    result: dict[str, Any]
    with sqlite_connection(settings.sqlite_path) as conn:
        _ensure_identity_tables(conn)
        existing_rows = conn.execute(
            "SELECT username, personnel_id FROM users"
        ).fetchall()
        by_username = {str(row["username"]).casefold(): row for row in existing_rows}
        by_personnel = {
            int(row["personnel_id"]): row
            for row in existing_rows
            if row["personnel_id"] is not None
        }

        for item in prepared:
            username = str(item["username"]).strip()
            personnel_id = int(item["personnel_id"])
            username_row = by_username.get(username.casefold())
            personnel_row = by_personnel.get(personnel_id)
            if personnel_row is not None and str(personnel_row["username"]).casefold() != username.casefold():
                raise ValueError(
                    f"personnel {personnel_id} already belongs to {personnel_row['username']}"
                )
            if username_row is not None and username_row["personnel_id"] not in (None, personnel_id):
                raise ValueError(
                    f"username {username} already belongs to personnel {username_row['personnel_id']}"
                )

        for item in prepared:
            username = str(item["username"]).strip()
            personnel_id = int(item["personnel_id"])
            existing = by_username.get(username.casefold()) or by_personnel.get(personnel_id)
            # A high-entropy, undisclosed placeholder makes password login
            # impossible until the one-time activation has completed.
            password_hash = hash_password(secrets.token_urlsafe(48))
            activation_token = secrets.token_urlsafe(48)
            values = (
                password_hash,
                1,
                personnel_id,
                str(item.get("full_name") or "").strip(),
                str(item.get("role") or "").strip(),
                str(item.get("branch") or "").strip(),
                str(item.get("sales_line") or "").strip(),
                str(item.get("phone") or "").strip(),
                str(item.get("phone_status") or "").strip(),
                int(item["supervisor_personnel_id"])
                if item.get("supervisor_personnel_id") not in (None, "")
                else None,
                1,
                now,
            )
            if existing is None:
                conn.execute(
                    """INSERT INTO users
                       (username, password_hash, active, personnel_id, full_name, role,
                        branch, sales_line, phone, phone_status, supervisor_personnel_id,
                        must_change_password, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (username, *values, now),
                )
                counts["created"] += 1
            else:
                existing_username = str(existing["username"])
                if existing["personnel_id"] is None:
                    counts["claimed_existing"] += 1
                else:
                    counts["updated"] += 1
                conn.execute(
                    """UPDATE users SET
                         password_hash=?, active=?, personnel_id=?, full_name=?, role=?,
                         branch=?, sales_line=?, phone=?, phone_status=?, supervisor_personnel_id=?,
                         must_change_password=?, updated_at=?
                       WHERE username=?""",
                    (*values, existing_username),
                )
                _revoke_user_security_state(conn, existing_username, now)
            activation_username = (
                str(existing["username"]) if existing is not None else username
            )
            conn.execute(
                "UPDATE user_activations SET used_at=? WHERE username=? AND used_at IS NULL",
                (now, activation_username),
            )
            conn.execute(
                """INSERT INTO user_activations
                   (token_hash, username, expires_at, used_at, created_at)
                   VALUES (?, ?, ?, NULL, ?)""",
                (
                    hashlib.sha256(activation_token.encode("utf-8")).hexdigest(),
                    activation_username,
                    activation_expires_at,
                    now,
                ),
            )
            activation_tokens[username] = activation_token
        result = {
            **counts,
            "activation_tokens": activation_tokens,
            "activation_expires_at": activation_expires_at,
        }
        # The CLI persists the activation bundle before this transaction
        # commits. A sink failure therefore rolls the credential reset back.
        if activation_sink is not None:
            activation_sink(result)
    return result


def activate_user(
    settings: Settings,
    activation_token: str,
    new_password: str,
    now: int | None = None,
) -> str | None:
    if len(new_password) < 8 or len(new_password) > 200:
        raise ValueError("new password must contain 8 to 200 characters")
    if len(activation_token) < 32 or len(activation_token) > 512:
        return None
    current = now or int(time.time())
    changed_at = str(current)
    token_hash = hashlib.sha256(activation_token.encode("utf-8")).hexdigest()
    with sqlite_connection(settings.sqlite_path) as conn:
        _ensure_identity_tables(conn)
        row = conn.execute(
            """SELECT u.username, a.expires_at, a.used_at, u.active
               FROM user_activations a
               JOIN users u ON u.username=a.username
               WHERE a.token_hash=?""",
            (token_hash,),
        ).fetchone()
        if (
            row is None
            or row["used_at"] is not None
            or int(row["expires_at"]) < current
            or not bool(row["active"])
        ):
            return None
        consumed = conn.execute(
            """UPDATE user_activations SET used_at=?
               WHERE token_hash=? AND used_at IS NULL AND expires_at>=?""",
            (changed_at, token_hash, current),
        ).rowcount
        if consumed != 1:
            return None
        username = str(row["username"])
        conn.execute(
            """UPDATE users SET password_hash=?, must_change_password=0, updated_at=?
               WHERE username=? AND active=1""",
            (hash_password(new_password), changed_at, username),
        )
        _revoke_user_security_state(conn, username, changed_at)
        # Preserve the just-consumed token as consumed while invalidating all
        # sibling activation attempts for this account.
        conn.execute(
            "UPDATE user_activations SET used_at=? WHERE username=? AND used_at IS NULL",
            (changed_at, username),
        )
        return username


def ensure_configured_user(settings: Settings) -> None:
    if not settings.login_username or not settings.login_password_hash:
        return
    now = str(time.time())
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT OR IGNORE INTO users
               (username, password_hash, active, created_at, updated_at)
               VALUES (?, ?, 1, ?, ?)""",
            (settings.login_username, settings.login_password_hash, now, now),
        )


def _database_user(settings: Settings, username: str):
    with sqlite_connection(settings.sqlite_path) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username.strip(),),
        ).fetchone()


def user_profile(settings: Settings, username: str) -> dict[str, Any] | None:
    row = _database_user(settings, username)
    if row is None:
        return None
    profile = {
        "username": str(row["username"]),
        "personnel_id": row["personnel_id"],
        "full_name": str(row["full_name"] or ""),
        "role": str(row["role"] or ""),
        "branch": str(row["branch"] or ""),
        "sales_line": str(row["sales_line"] or ""),
        "phone": str(row["phone"] or ""),
        "phone_status": str(row["phone_status"] or ""),
        "supervisor_personnel_id": row["supervisor_personnel_id"],
        "must_change_password": bool(row["must_change_password"]),
        "active": bool(row["active"]),
    }
    # Imported lazily to keep authentication usable during initial database setup.
    from app.control_service import permission_keys_for_user, position_for_user

    profile["permissions"] = permission_keys_for_user(settings, str(row["username"]))
    profile["position"] = position_for_user(settings, str(row["username"]))
    return profile


def user_requires_password_change(settings: Settings, username: str) -> bool:
    profile = user_profile(settings, username)
    return bool(profile and profile["must_change_password"])


def change_password(
    settings: Settings,
    username: str,
    current_password: str,
    new_password: str,
) -> bool:
    if len(new_password) < 8 or len(new_password) > 200:
        raise ValueError("new password must contain 8 to 200 characters")
    if current_password == new_password:
        raise ValueError("new password must be different")
    row = _database_user(settings, username)
    if row is None or not row["active"] or not verify_password(current_password, row["password_hash"]):
        return False
    now = str(time.time())
    with sqlite_connection(settings.sqlite_path) as conn:
        changed = conn.execute(
            """UPDATE users SET password_hash=?, must_change_password=0, updated_at=?
               WHERE username=? AND active=1""",
            (hash_password(new_password), now, str(row["username"])),
        ).rowcount
        if changed:
            _revoke_user_security_state(conn, str(row["username"]), now)
    return bool(changed)


def authenticate_user(settings: Settings, username: str, password: str) -> str | None:
    row = _database_user(settings, username)
    if row is not None:
        if row["active"] and verify_password(password, row["password_hash"]):
            return str(row["username"])
        return None
    if (
        settings.login_username
        and settings.login_password_hash
        and hmac.compare_digest(username, settings.login_username)
        and verify_password(password, settings.login_password_hash)
    ):
        return settings.login_username
    return None


def create_session(settings: Settings, username: str, now: int | None = None) -> str:
    issued_at = now or int(time.time())
    expires = issued_at + SESSION_SECONDS
    with sqlite_connection(settings.sqlite_path) as conn:
        generation = _session_generation(conn, username)
    payload = f"v2|{username}|{expires}|{generation}"
    signature = hmac.new(
        _session_signing_key(settings), payload.encode(), hashlib.sha256
    ).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{signature}".encode()).decode()


def session_username(settings: Settings, token: str, now: int | None = None) -> str | None:
    try:
        decoded = base64.b64decode(token.encode(), altchars=b"-_", validate=True).decode()
        version, username, expires_text, generation_text, signature = decoded.split("|", 4)
        if version != "v2":
            return None
        payload = f"{version}|{username}|{expires_text}|{generation_text}"
        expected = hmac.new(
            _session_signing_key(settings), payload.encode(), hashlib.sha256
        ).hexdigest()
        valid_signature = hmac.compare_digest(signature, expected)
        valid_time = int(expires_text) >= (now or int(time.time()))
        if not (valid_signature and valid_time):
            return None
        with sqlite_connection(settings.sqlite_path) as conn:
            generation = _session_generation(conn, username)
            row = conn.execute(
                "SELECT username, active FROM users WHERE username=?",
                (username,),
            ).fetchone()
        if generation != int(generation_text):
            return None
        if row is not None:
            return str(row["username"]) if row["active"] else None
        if settings.login_username and hmac.compare_digest(username, settings.login_username):
            return settings.login_username
        return None
    except (ValueError, TypeError, UnicodeError):
        return None


def verify_session(settings: Settings, token: str, now: int | None = None) -> bool:
    return session_username(settings, token, now) is not None
