from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.config import Settings
from app.database import sqlite_connection


PushSender = Callable[[dict[str, Any], dict[str, Any]], None]
_ALLOWED_PUSH_HOST_SUFFIXES = (
    "fcm.googleapis.com",
    "push.services.mozilla.com",
    "web.push.apple.com",
    "notify.windows.com",
)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def private_key_path(settings: Settings) -> Path:
    return settings.vapid_private_key_path or settings.sqlite_path.parent / "vapid_private.pem"


def ensure_vapid_private_key(path: Path | None) -> None:
    if path is None or path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    private_key = ec.generate_private_key(ec.SECP256R1())
    path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def vapid_public_key(path: Path | None) -> str:
    if path is None:
        raise RuntimeError("VAPID private key is not configured")
    ensure_vapid_private_key(path)
    private_key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise RuntimeError("VAPID private key is invalid")
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    import base64

    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _validate_endpoint(endpoint: str) -> str:
    clean = endpoint.strip()
    parsed = urlparse(clean)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not any(
        host == suffix or host.endswith("." + suffix)
        for suffix in _ALLOWED_PUSH_HOST_SUFFIXES
    ):
        raise ValueError("unsupported push endpoint")
    return clean


def save_push_subscription(
    settings: Settings,
    username: str,
    subscription: dict[str, Any],
    user_agent: str | None = None,
) -> None:
    endpoint = _validate_endpoint(str(subscription.get("endpoint") or ""))
    keys = subscription.get("keys") or {}
    p256dh = str(keys.get("p256dh") or "").strip()
    auth = str(keys.get("auth") or "").strip()
    if not p256dh or not auth or len(p256dh) > 512 or len(auth) > 512:
        raise ValueError("invalid push subscription keys")
    now = utc_stamp()
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO push_subscriptions
               (username, endpoint, p256dh, auth, user_agent, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(endpoint) DO UPDATE SET
                 username=excluded.username,
                 p256dh=excluded.p256dh,
                 auth=excluded.auth,
                 user_agent=excluded.user_agent,
                 updated_at=excluded.updated_at,
                 last_error=NULL""",
            (username, endpoint, p256dh, auth, (user_agent or "")[:500], now, now),
        )


def delete_push_subscription(settings: Settings, username: str, endpoint: str) -> int:
    with sqlite_connection(settings.sqlite_path) as conn:
        cursor = conn.execute(
            "DELETE FROM push_subscriptions WHERE username=? AND endpoint=?",
            (username, endpoint.strip()),
        )
        return cursor.rowcount


def list_push_subscriptions(settings: Settings, username: str) -> list[dict[str, Any]]:
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT id, endpoint, p256dh, auth, user_agent, created_at,
                      updated_at, last_success_at, last_error
               FROM push_subscriptions WHERE username=? ORDER BY id""",
            (username,),
        ).fetchall()
    return [dict(row) for row in rows]


def _default_sender(settings: Settings) -> PushSender:
    def send(subscription: dict[str, Any], payload: dict[str, Any]) -> None:
        from pywebpush import webpush

        key_path = private_key_path(settings)
        ensure_vapid_private_key(key_path)
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=str(key_path),
            vapid_claims={"sub": settings.vapid_subject},
            ttl=3600,
            timeout=10,
        )

    return send


def _status_code(exc: Exception) -> int | None:
    direct = getattr(exc, "status_code", None)
    if isinstance(direct, int):
        return direct
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def send_user_push(
    settings: Settings,
    username: str,
    title: str,
    body: str,
    url: str | None = None,
    *,
    sender: PushSender | None = None,
) -> dict[str, int]:
    rows = list_push_subscriptions(settings, username)
    result = {"attempted": len(rows), "delivered": 0, "expired": 0, "failed": 0}
    send = sender or _default_sender(settings)
    payload = {
        "title": str(title)[:120] or "نگین پخش",
        "body": str(body)[:700] or "گزارش خودکار آماده است.",
        "url": url or settings.push_notification_url,
        "tag": f"neginai-{username}-{uuid4().hex[:16]}",
    }
    for row in rows:
        subscription = {
            "endpoint": row["endpoint"],
            "keys": {"p256dh": row["p256dh"], "auth": row["auth"]},
        }
        try:
            send(subscription, payload)
            with sqlite_connection(settings.sqlite_path) as conn:
                conn.execute(
                    """UPDATE push_subscriptions
                       SET last_success_at=?, last_error=NULL, updated_at=? WHERE id=?""",
                    (utc_stamp(), utc_stamp(), row["id"]),
                )
            result["delivered"] += 1
        except Exception as exc:
            status = _status_code(exc)
            if status in {404, 410}:
                with sqlite_connection(settings.sqlite_path) as conn:
                    conn.execute("DELETE FROM push_subscriptions WHERE id=?", (row["id"],))
                result["expired"] += 1
            else:
                with sqlite_connection(settings.sqlite_path) as conn:
                    conn.execute(
                        """UPDATE push_subscriptions
                           SET last_error=?, updated_at=? WHERE id=?""",
                        (f"{type(exc).__name__}: {str(exc)[:300]}", utc_stamp(), row["id"]),
                    )
                result["failed"] += 1
    return result
