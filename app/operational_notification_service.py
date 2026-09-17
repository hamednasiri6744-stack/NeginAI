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


def _snapshot_state(settings: Any, username: str, rule_key: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    fingerprint = _event_key(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
    stamp = _utc_iso()
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT fingerprint, payload_json FROM operational_alert_state WHERE username=? AND rule_key=?",
            (username, rule_key),
        ).fetchone()
        previous_payload = None
        if row is not None:
            try:
                previous_payload = json.loads(str(row["payload_json"] or "{}"))
            except json.JSONDecodeError:
                previous_payload = {}
        conn.execute(
            """INSERT INTO operational_alert_state
               (username, rule_key, fingerprint, payload_json, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(username, rule_key) DO UPDATE SET
                 fingerprint=excluded.fingerprint, payload_json=excluded.payload_json,
                 updated_at=excluded.updated_at""",
            (username, rule_key, fingerprint, json.dumps(payload, ensure_ascii=False, default=str), stamp),
        )
    return previous_payload


def observe_returned_cheques(settings: Any, username: str, payload: dict[str, Any]) -> None:
    current = {
        str(item.get("id")): {
            "id": item.get("id"), "number": item.get("number"),
            "status": item.get("status"), "status_date": item.get("status_date"),
            "amount": item.get("amount"), "seller_share": item.get("seller_share"),
            "settled_amount": item.get("settled_amount"),
            "customer_id": item.get("customer_id"),
            "customer_name": item.get("customer_store") or item.get("customer_name"),
        }
        for item in payload.get("cheques") or [] if item.get("id") is not None
    }
    previous = _snapshot_state(settings, username, "returned_cheques", {"items": current})
    if previous is None:
        return
    old = previous.get("items") or {}
    for cheque_id, item in current.items():
        before = old.get(cheque_id)
        customer = str(item.get("customer_name") or "مشتری").strip()
        number = str(item.get("number") or cheque_id)
        if before is None:
            emit_operational_notification(
                settings, username=username, title="چک برگشتی جدید",
                body=f"چک {number} مربوط به {customer} در وضعیت چک‌های برگشتی فروش شما ثبت شد.",
                severity="critical", category="finance", source=str(payload.get("source") or "Varanegar"),
                entity_type="cheque", entity_id=cheque_id, action_path="/visitor/customers",
                dedupe_key=f"returned-cheque:new:{cheque_id}:{item.get('status_date') or ''}",
                payload=item, requires_ack=True,
            )
            continue
        if (before.get("status"), before.get("status_date")) != (item.get("status"), item.get("status_date")):
            emit_operational_notification(
                settings, username=username, title="وضعیت چک برگشتی تغییر کرد",
                body=f"وضعیت چک {number} مربوط به {customer} به «{item.get('status') or 'وضعیت جدید'}» تغییر کرد.",
                severity="high", category="finance", source=str(payload.get("source") or "Varanegar"),
                entity_type="cheque", entity_id=cheque_id, action_path="/visitor/customers",
                dedupe_key=f"returned-cheque:status:{cheque_id}:{item.get('status_date') or item.get('status')}", payload=item,
            )
        elif before.get("settled_amount") != item.get("settled_amount"):
            emit_operational_notification(
                settings, username=username, title="تسویه چک برگشتی به‌روزرسانی شد",
                body=f"مبلغ تسویه ثبت‌شده برای چک {number} مربوط به {customer} تغییر کرد.",
                severity="medium", category="finance", source=str(payload.get("source") or "Varanegar"),
                entity_type="cheque", entity_id=cheque_id, action_path="/visitor/customers",
                dedupe_key=f"returned-cheque:settlement:{cheque_id}:{item.get('settled_amount')}", payload=item,
            )


def observe_distribution(settings: Any, username: str, payload: dict[str, Any]) -> None:
    current = {
        str(item.get("id")): {
            "id": item.get("id"), "number": item.get("number"),
            "customer_name": item.get("customer_store") or item.get("customer_name"),
            "distribution_number": item.get("distribution_number"),
            "distribution_date": item.get("distribution_date"), "sent_at": item.get("sent_at"),
            "driver_name": item.get("driver_name"), "driver_mobile": item.get("driver_mobile"),
            "amount": item.get("amount"),
        }
        for item in payload.get("invoices") or [] if item.get("id") is not None
    }
    previous = _snapshot_state(settings, username, "distribution_in_progress", {"items": current})
    if previous is None:
        return
    old = previous.get("items") or {}
    for invoice_id, item in current.items():
        before = old.get(invoice_id)
        customer = str(item.get("customer_name") or "مشتری").strip()
        number = str(item.get("number") or invoice_id)
        if before is None:
            emit_operational_notification(
                settings, username=username, title="سفارش وارد فرآیند توزیع شد",
                body=f"سفارش/فاکتور {number} برای {customer} در برنامه توزیع قرار گرفت.",
                severity="medium", category="distribution", source=str(payload.get("source") or "Varanegar"),
                entity_type="invoice", entity_id=invoice_id, action_path="/visitor/orders",
                dedupe_key=f"distribution:new:{invoice_id}:{item.get('distribution_number') or item.get('distribution_date')}", payload=item,
            )
            continue
        if before.get("distribution_date") != item.get("distribution_date"):
            emit_operational_notification(
                settings, username=username, title="زمان توزیع سفارش تغییر کرد",
                body=f"تاریخ توزیع سفارش/فاکتور {number} برای {customer} تغییر کرد.",
                severity="high", category="distribution", source=str(payload.get("source") or "Varanegar"),
                entity_type="invoice", entity_id=invoice_id, action_path="/visitor/orders",
                dedupe_key=f"distribution:date:{invoice_id}:{item.get('distribution_date')}", payload=item,
            )
        elif not before.get("sent_at") and item.get("sent_at"):
            emit_operational_notification(
                settings, username=username, title="سفارش ارسال شد",
                body=f"سفارش/فاکتور {number} برای {customer} از توزیع ارسال شد.",
                severity="high", category="distribution", source=str(payload.get("source") or "Varanegar"),
                entity_type="invoice", entity_id=invoice_id, action_path="/visitor/orders",
                dedupe_key=f"distribution:sent:{invoice_id}:{item.get('sent_at')}", payload=item,
            )
        elif (before.get("driver_name"), before.get("driver_mobile")) != (item.get("driver_name"), item.get("driver_mobile")):
            emit_operational_notification(
                settings, username=username, title="راننده توزیع تغییر کرد",
                body=f"اطلاعات راننده سفارش/فاکتور {number} برای {customer} تغییر کرد.",
                severity="medium", category="distribution", source=str(payload.get("source") or "Varanegar"),
                entity_type="invoice", entity_id=invoice_id, action_path="/visitor/orders",
                dedupe_key=f"distribution:driver:{invoice_id}:{item.get('driver_name')}:{item.get('driver_mobile')}", payload=item,
            )


def refresh_operational_alerts(settings: Any, username: str) -> dict[str, bool]:
    """Best-effort read-only refresh of seller-relevant Varanegar/NGT operational changes."""
    from app.seller_workspace_service import (
        seller_distribution_in_progress,
        seller_returned_cheques,
        seller_routes,
    )
    result = {"route": False, "returned_cheques": False, "distribution": False}
    try:
        seller_routes(settings, username)
        result["route"] = True
    except Exception:
        pass
    try:
        observe_returned_cheques(settings, username, seller_returned_cheques(settings, username))
        result["returned_cheques"] = True
    except Exception:
        pass
    try:
        observe_distribution(settings, username, seller_distribution_in_progress(settings, username))
        result["distribution"] = True
    except Exception:
        pass
    return result
