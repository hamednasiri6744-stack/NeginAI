from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Literal

from app.database import sqlite_connection
from app.push_service import send_user_push

NotificationSeverity = Literal["critical", "high", "medium", "info"]
VALID_SEVERITIES = {"critical", "high", "medium", "info"}
PUSH_SEVERITIES = {"critical", "high"}


def _utc_iso(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat()


def _event_key(*parts: object) -> str:
    raw = "|".join(str(part or "") for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
def emit_operational_notification(
    settings: Any,
    *,
    username: str,
    title: str,
    body: str,
    severity: NotificationSeverity,
    category: str,
    source: str = "varanegar",
    entity_type: str | None = None,
    entity_id: str | None = None,
    action_path: str | None = None,
    dedupe_key: str | None = None,
    occurred_at: datetime | None = None,
    payload: dict[str, Any] | None = None,
    requires_ack: bool | None = None,
    push: bool = True,
) -> dict[str, Any]:
    level = str(severity).strip().lower()
    if level not in VALID_SEVERITIES:
        raise ValueError(f"unsupported notification severity: {severity}")
    owner = username.strip()
    if not owner:
        raise ValueError("username is required")
    stamp = _utc_iso(occurred_at)
    ack_required = level == "critical" if requires_ack is None else bool(requires_ack)
    clean_dedupe = (dedupe_key or "").strip() or None
    with sqlite_connection(settings.sqlite_path) as conn:
        if clean_dedupe:
            existing = conn.execute(
                "SELECT id, read_at, acknowledged_at FROM notifications WHERE username=? AND dedupe_key=?",
                (owner, clean_dedupe),
            ).fetchone()
            if existing is not None:
                return {
                    "id": int(existing["id"]),
                    "created": False,
                    "severity": level,
                    "requires_ack": ack_required,
                }
        cursor = conn.execute(
            """INSERT INTO notifications
               (username, automation_id, title, body, payload_json, source, category,
                severity, entity_type, entity_id, action_path, dedupe_key, occurred_at,
                requires_ack, created_at)
               VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                owner, title.strip(), body.strip(),
                json.dumps(payload or {}, ensure_ascii=False, default=str),
                source.strip() or "varanegar", category.strip() or "general", level,
                entity_type, entity_id, action_path, clean_dedupe, stamp,
                int(ack_required), stamp,
            ),
        )
        notification_id = int(cursor.lastrowid)
    if push and level in PUSH_SEVERITIES:
        try:
            send_user_push(
                settings,
                owner,
                title.strip(),
                body.strip(),
                action_path or "/visitor/notifications",
            )
        except Exception:
            pass
    return {
        "id": notification_id,
        "created": True,
        "severity": level,
        "requires_ack": ack_required,
    }


def observe_route_assignment(settings: Any, username: str, route_payload: dict[str, Any]) -> None:
    day_route = route_payload.get("day_route") or {}
    route_id = str(day_route.get("id") or "")
    route_title = str(day_route.get("title") or "").strip()
    route_date = str(day_route.get("date") or "")
    status = str(route_payload.get("day_route_status") or "")
    fingerprint = _event_key(route_id, route_title, route_date, status)
    stamp = _utc_iso()
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT fingerprint, payload_json FROM operational_alert_state WHERE username=? AND rule_key='route_assignment'",
            (username,),
        ).fetchone()
        previous = str(row["fingerprint"]) if row is not None else None
        conn.execute(
            """INSERT INTO operational_alert_state
               (username, rule_key, fingerprint, payload_json, updated_at)
               VALUES (?, 'route_assignment', ?, ?, ?)
               ON CONFLICT(username, rule_key) DO UPDATE SET
                 fingerprint=excluded.fingerprint,
                 payload_json=excluded.payload_json,
                 updated_at=excluded.updated_at""",
            (
                username,
                fingerprint,
                json.dumps({"route_id": route_id, "route_title": route_title, "status": status}, ensure_ascii=False),
                stamp,
            ),
        )
    if previous is None or previous == fingerprint:
        return
    title = "مسیر امروز تغییر کرد"
    body = f"مسیر فعال امروز به «{route_title}» تغییر کرد." if route_title else "تخصیص مسیر امروز تغییر کرد؛ مسیر جدید را بررسی کنید."
    emit_operational_notification(
        settings,
        username=username,
        title=title,
        body=body,
        severity="high",
        category="route",
        source="NGT",
        entity_type="route",
        entity_id=route_id or None,
        action_path="/visitor/route",
        dedupe_key=f"route-assignment:{route_date}:{fingerprint}",
        payload={"route_id": route_id, "route_title": route_title, "status": status},
    )
