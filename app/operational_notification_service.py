from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any, Literal

from app.database import sqlite_connection
from app.push_service import send_user_push

NotificationSeverity = Literal["critical", "high", "medium", "info"]
VALID_SEVERITIES = {"critical", "high", "medium", "info"}
PUSH_SEVERITIES = {"critical", "high"}
_COMMERCIAL_REFRESH_AT: dict[str, float] = {}
COMMERCIAL_REFRESH_SECONDS = 300.0


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
        seller_route_customers_basic,
        seller_routes,
        seller_voucher_return_report,
    )
    result = {"route": False, "route_customers": False, "returned_cheques": False, "distribution": False, "returns": False, "commercial_policy": False}
    route_payload: dict[str, Any] = {}
    try:
        route_payload = seller_routes(settings, username)
        result["route"] = True
    except Exception:
        pass
    try:
        day_route = route_payload.get("day_route") or {}
        route_id = str(day_route.get("id") or "")
        if route_id:
            observe_route_customers(settings, username, seller_route_customers_basic(settings, username, route_id))
            result["route_customers"] = True
    except Exception:
        pass
    try:
        observe_voucher_returns(settings, username, seller_voucher_return_report(settings, username))
        result["returns"] = True
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
    try:
        now = time.monotonic()
        last = _COMMERCIAL_REFRESH_AT.get(username, 0.0)
        if now - last >= COMMERCIAL_REFRESH_SECONDS:
            from app.commercial_policy_snapshot import seller_commercial_policy_snapshot
            observe_commercial_policy(settings, username, seller_commercial_policy_snapshot(settings, username))
            _COMMERCIAL_REFRESH_AT[username] = now
            result["commercial_policy"] = True
    except Exception:
        pass
    return result


def observe_route_customers(settings: Any, username: str, payload: dict[str, Any]) -> None:
    route = payload.get("route") or {}
    route_id = str(route.get("id") or "")
    if not route_id:
        return
    current = {
        str(item.get("id")): {
            "id": item.get("id"),
            "name": item.get("store_name") or item.get("name"),
            "code": item.get("code"),
            "alarm": str(item.get("alarm") or "").strip(),
        }
        for item in payload.get("customers") or [] if item.get("id") is not None
    }
    previous = _snapshot_state(settings, username, f"route_customers:{route_id}", {"items": current})
    if previous is None:
        return
    old = previous.get("items") or {}
    old_ids, current_ids = set(old), set(current)

    for customer_id in sorted(old_ids - current_ids):
        before = old.get(customer_id) or {}
        name = str(before.get("name") or customer_id)
        emit_operational_notification(
            settings, username=username, title="فهرست فعال مسیر امروز تغییر کرد",
            body=f"{name} دیگر در فهرست فعال همین مسیر روز دیده نمی‌شود؛ مسیر را قبل از مراجعه بررسی کنید.",
            severity="high", category="customer", source=str(payload.get("source") or "NGT"),
            entity_type="customer", entity_id=customer_id, action_path="/visitor/route",
            dedupe_key=f"route-customer:removed:{route_id}:{customer_id}:{_event_key(json.dumps(current, sort_keys=True, default=str))}",
            payload={"route_id": route_id, "customer": before},
        )
    for customer_id in sorted(current_ids - old_ids):
        item = current[customer_id]
        name = str(item.get("name") or customer_id)
        emit_operational_notification(
            settings, username=username, title="مشتری جدید در مسیر امروز",
            body=f"{name} به فهرست فعال مسیر امروز اضافه شده است.",
            severity="medium", category="customer", source=str(payload.get("source") or "NGT"),
            entity_type="customer", entity_id=customer_id, action_path="/visitor/route",
            dedupe_key=f"route-customer:added:{route_id}:{customer_id}:{_event_key(json.dumps(current, sort_keys=True, default=str))}",
            payload={"route_id": route_id, "customer": item},
        )
    for customer_id in sorted(current_ids & old_ids):
        before, item = old[customer_id], current[customer_id]
        if str(before.get("alarm") or "").strip() == str(item.get("alarm") or "").strip():
            continue
        new_alarm = str(item.get("alarm") or "").strip()
        if not new_alarm:
            continue
        name = str(item.get("name") or customer_id)
        emit_operational_notification(
            settings, username=username, title="هشدار مشتری در NGT تغییر کرد",
            body=f"{name}: {new_alarm}", severity="medium", category="customer",
            source="NGT.Customers.Alarm", entity_type="customer", entity_id=customer_id,
            action_path="/visitor/route",
            dedupe_key=f"customer-alarm:{customer_id}:{_event_key(new_alarm)}",
            payload={"route_id": route_id, "customer": item},
        )


def observe_voucher_returns(settings: Any, username: str, payload: dict[str, Any]) -> None:
    month = str(payload.get("report_month") or "")
    current = {
        "full_returned_count": int(payload.get("full_returned_count") or 0),
        "undistributed_count": int(payload.get("undistributed_count") or 0),
        "voucher_count": int(payload.get("voucher_count") or 0),
    }
    previous = _snapshot_state(settings, username, f"voucher_returns:{month or 'current'}", current)
    if previous is None:
        return
    old_returns = int(previous.get("full_returned_count") or 0)
    new_returns = current["full_returned_count"]
    if new_returns > old_returns:
        delta = new_returns - old_returns
        emit_operational_notification(
            settings, username=username, title="برگشتی کامل جدید ثبت شد",
            body=f"تعداد حواله‌های برگشتی کامل این ماه {delta} مورد افزایش یافت و اکنون {new_returns} مورد است.",
            severity="high", category="return", source=str(payload.get("source") or "SLE.tblSaleVocherHdr"),
            entity_type="sales_return", entity_id=month or None, action_path="/visitor/reports",
            dedupe_key=f"voucher-return:{month}:{new_returns}", payload={**payload, "delta": delta},
        )
    old_undistributed = int(previous.get("undistributed_count") or 0)
    new_undistributed = current["undistributed_count"]
    if new_undistributed > old_undistributed:
        emit_operational_notification(
            settings, username=username, title="حواله توزیع‌نشده افزایش یافت",
            body=f"تعداد حواله‌های توزیع‌نشده این ماه از {old_undistributed} به {new_undistributed} رسید.",
            severity="medium", category="distribution", source=str(payload.get("source") or "SLE.tblSaleVocherHdr"),
            entity_type="voucher", entity_id=month or None, action_path="/visitor/reports",
            dedupe_key=f"undistributed-voucher:{month}:{new_undistributed}", payload=payload,
        )


def observe_credit_block(
    settings: Any,
    username: str,
    *,
    route_id: str,
    customer_id: str,
    credit_control: dict[str, Any],
) -> None:
    if credit_control.get("allowed") is not False:
        return
    mode = str(credit_control.get("mode") or "unknown")
    deficit = float(credit_control.get("deficit") or 0)
    available = credit_control.get("available_amount")
    evaluated = float(credit_control.get("evaluated_total") or 0)
    day_key = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    emit_operational_notification(
        settings, username=username, title="کنترل اعتبار سفارش را متوقف کرد",
        body=str(credit_control.get("message") or "ثبت سفارش طبق کنترل اعتبار رسمی NGT مجاز نیست."),
        severity="high", category="credit", source=str(credit_control.get("source") or "NGT presale credit-control parity"),
        entity_type="customer", entity_id=str(customer_id), action_path="/visitor/orders",
        dedupe_key=f"credit-block:{day_key}:{customer_id}:{mode}",
        payload={"route_id": route_id, "customer_id": customer_id, "mode": mode,
                 "deficit": deficit, "available_amount": available, "evaluated_total": evaluated},
    )


def observe_official_quote(
    settings: Any,
    username: str,
    *,
    route_id: str,
    customer_id: str,
    order_type_ref: int | str,
    payment_usance_ref: int | str,
    warehouse_ref: int | str,
    requested_lines: list[dict[str, Any]],
    result: dict[str, Any],
) -> None:
    context = {
        "route_id": str(route_id), "customer_id": str(customer_id),
        "order_type_ref": str(order_type_ref), "payment_usance_ref": str(payment_usance_ref),
        "warehouse_ref": str(warehouse_ref),
        "lines": sorted(
            [{"product_id": str(line.get("product_id")), "quantity": float(line.get("quantity") or 0)} for line in requested_lines],
            key=lambda item: item["product_id"],
        ),
    }
    context_key = _event_key(json.dumps(context, ensure_ascii=False, sort_keys=True))

    quote = {
        "prices": {
            str(item.get("product_id")): float(item.get("unit_price") or 0)
            for item in result.get("items") or []
        },
        "discounts": {
            str(item.get("product_id")): {
                "amount": float(item.get("discount_amount") or 0),
                "percent": float(item.get("discount_percent") or 0),
                "breakdown": item.get("discount_breakdown") or {},
            }
            for item in result.get("items") or []
        },
        "gifts": sorted(
            [{"product_id": str(item.get("product_id") or ""), "quantity": float(item.get("quantity") or 0)}
             for item in result.get("gift_lines") or []],
            key=lambda item: (item["product_id"], item["quantity"]),
        ),
        "restrictions": result.get("restrictions") or [],
    }
    previous = _snapshot_state(settings, username, f"official_quote:{context_key}", quote)
    if previous is None:
        return
    changes: list[str] = []
    high = False
    if previous.get("prices") != quote["prices"]:
        changes.append("قیمت رسمی")
        high = True
    if previous.get("discounts") != quote["discounts"]:
        changes.append("تخفیف")
    if previous.get("gifts") != quote["gifts"]:
        changes.append("اشانتیون")
    if previous.get("restrictions") != quote["restrictions"]:
        changes.append("محدودیت فروش")
        high = True
    if not changes:
        return
    fingerprint = _event_key(json.dumps(quote, ensure_ascii=False, sort_keys=True, default=str))
    emit_operational_notification(
        settings, username=username, title="شرایط رسمی سفارش تغییر کرد",
        body=f"در محاسبه مجدد رسمی NGT برای همین ترکیب سفارش، {'، '.join(changes)} تغییر کرده است؛ قبل از ثبت نهایی دوباره بررسی کنید.",
        severity="high" if high else "medium", category="pricing", source="NGT EVC presale",
        entity_type="customer", entity_id=str(customer_id), action_path="/visitor/orders",
        dedupe_key=f"official-quote:{context_key}:{fingerprint}",
        payload={"context": context, "quote": quote, "changed": changes},
    )


def _promotion_change_labels(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    fields = {
        "title": "عنوان قانون",
        "discount_percent": "درصد تخفیف",
        "discount_amount": "مبلغ تخفیف",
        "min_qty": "حداقل تعداد",
        "max_qty": "حداکثر تعداد",
        "min_amount": "حداقل مبلغ",
        "max_amount": "حداکثر مبلغ",
        "prize_quantity": "تعداد جایزه",
        "prize_product_id": "کالای جایزه",
        "prize_step": "گام جایزه",
        "start_date": "تاریخ شروع",
        "end_date": "تاریخ پایان",
        "conditions": "شرایط اعمال",
        "products": "دامنه کالاها",
        "brands": "دامنه برندها",
    }
    return [label for key, label in fields.items() if before.get(key) != after.get(key)]


def observe_commercial_policy(settings: Any, username: str, payload: dict[str, Any]) -> None:
    current = {
        "prices": payload.get("prices") or {},
        "promotions": payload.get("promotions") or {},
    }
    previous = _snapshot_state(settings, username, "commercial_policy", current)
    if previous is None:
        return
    old_prices = previous.get("prices") or {}
    new_prices = current["prices"]
    price_changes_by_brand: dict[str, list[dict[str, Any]]] = {}
    for key in sorted(set(old_prices) | set(new_prices)):
        before = old_prices.get(key)
        after = new_prices.get(key)
        if before == after:
            continue
        item = after or before or {}
        brand = str(item.get("brand_name") or "بدون برند").strip() or "بدون برند"
        product_name = str(item.get("product_name") or item.get("product_code") or key)
        order_name = str(item.get("order_type_name") or item.get("order_type_ref") or "")
        change = {
            "key": key,
            "product_id": item.get("product_id"),
            "product_name": product_name,
            "brand_name": brand,
            "order_type": order_name,
            "before": before,
            "after": after,
        }
        price_changes_by_brand.setdefault(brand, []).append(change)

    for brand, changes in price_changes_by_brand.items():
        sale_price_changes = [
            change for change in changes
            if (change.get("before") or {}).get("sale_price") != (change.get("after") or {}).get("sale_price")
        ]
        sample_parts: list[str] = []
        for change in sale_price_changes[:3]:
            before_price = (change.get("before") or {}).get("sale_price")
            after_price = (change.get("after") or {}).get("sale_price")
            sample_parts.append(
                f"{change['product_name']}: {float(before_price or 0):,.0f} → {float(after_price or 0):,.0f} ریال"
            )
        if not sample_parts:
            sample_parts = [f"{change['product_name']} ({change['order_type']})" for change in changes[:3]]
        more = len(changes) - len(sample_parts)
        body = "؛ ".join(sample_parts)
        if more > 0:
            body += f"؛ و {more} مورد دیگر"
        fingerprint = _event_key(json.dumps(changes, ensure_ascii=False, sort_keys=True, default=str))
        emit_operational_notification(
            settings,
            username=username,
            title=f"قیمت فروش برند {brand} تغییر کرد",
            body=body,
            severity="high" if sale_price_changes else "medium",
            category="pricing",
            source="NGT.ContractPrices",
            entity_type="brand",
            entity_id=brand,
            action_path="/visitor/orders",
            dedupe_key=f"seller-brand-price:{brand}:{fingerprint}",
            payload={
                "brand": brand,
                "change_count": len(changes),
                "sale_price_change_count": len(sale_price_changes),
                "changes": changes,
                "price_semantics": "active generic base contract; final price remains NGT EVC dependent",
            },
        )

    old_rules = previous.get("promotions") or {}
    new_rules = current["promotions"]
    for rule_id in sorted(set(old_rules) | set(new_rules), key=lambda value: int(value)):
        before = old_rules.get(rule_id)
        after = new_rules.get(rule_id)
        if before == after:
            continue
        item = after or before or {}
        kind = str(item.get("kind") or "discount")
        kind_label = "جایزه/اشانتیون" if kind == "prize" else "تخفیف"
        brands = "، ".join(item.get("brands") or []) or "برندهای تخصیص‌یافته فروشنده"
        rule_title = str(item.get("title") or f"قانون {item.get('rule_code') or rule_id}")
        if before is None:
            title = f"قانون {kind_label} جدید فعال شد"
            detail = f"{rule_title} برای {brands} وارد مجموعه قوانین فعال شد."
            change_labels = ["فعال‌شدن قانون"]
        elif after is None:
            title = f"قانون {kind_label} دیگر فعال نیست"
            detail = f"{rule_title} برای {brands} دیگر در مجموعه قوانین فعال دیده نمی‌شود."
            change_labels = ["غیرفعال/منقضی‌شدن قانون"]
        else:
            change_labels = _promotion_change_labels(before, after)
            title = f"قانون {kind_label} تغییر کرد"
            labels = "، ".join(change_labels) or "تعریف قانون"
            detail = f"{rule_title} برای {brands} تغییر کرد: {labels}."
        fingerprint = _event_key(json.dumps(after or before or {}, ensure_ascii=False, sort_keys=True, default=str))
        emit_operational_notification(
            settings,
            username=username,
            title=title,
            body=detail,
            severity="high",
            category="promotion",
            source="SLE.tblDiscount + SLE.tblDiscountCondition",
            entity_type="promotion_rule",
            entity_id=str(rule_id),
            action_path="/visitor/orders",
            dedupe_key=f"seller-promotion:{rule_id}:{fingerprint}:{'on' if after is not None else 'off'}",
            payload={
                "rule_id": rule_id,
                "kind": kind,
                "brands": item.get("brands") or [],
                "change_labels": change_labels,
                "before": before,
                "after": after,
            },
        )
