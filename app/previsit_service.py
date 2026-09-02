"""Local, auditable pre-visit order drafts.

This module deliberately does not create Varanegar documents.  A reviewed NGT
bridge will consume the queued payload later, after the NGT request contract
has been verified against a non-production tour.
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from threading import Lock
from typing import Any
from uuid import uuid4

from app.database import sqlite_connection
from app.models import (
    PrevisitDraftUpdateRequest,
    PrevisitOutcomeRequest,
    PrevisitSavedRequestUpsert,
    PrevisitVisitStartRequest,
)
from app.seller_workspace_service import (
    SellerDayRouteMismatch,
    SellerRouteNotFound,
    require_seller_day_route,
    resolve_ngt_visit_outcome,
    seller_route_customers,
)


class PrevisitError(ValueError):
    pass


_visit_start_lock = Lock()
_saved_request_write_lock = Lock()
_visit_start_busy_timeout_ms = 3_000
_visit_start_retry_delays = (0.1, 0.25, 0.5)
_saved_request_retry_delays = (0.1, 0.25, 0.5)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _owned_visit(settings: Any, username: str, visit_id: str) -> dict[str, Any]:
    with sqlite_connection(settings.sqlite_path) as connection:
        row = connection.execute(
            "SELECT * FROM previsit_visits WHERE id = ? AND username = ?",
            (visit_id, username),
        ).fetchone()
    if not row:
        raise PrevisitError("Visit was not found")
    return dict(row)


def _draft(settings: Any, username: str, visit_id: str) -> dict[str, Any]:
    with sqlite_connection(settings.sqlite_path) as connection:
        row = connection.execute(
            "SELECT * FROM previsit_drafts WHERE visit_id = ? AND username = ?",
            (visit_id, username),
        ).fetchone()
    if not row:
        raise PrevisitError("Order draft was not found")
    return dict(row)


def _serialize_draft(visit: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    lines = json.loads(draft["cart_json"])
    total = sum(
        (float(line["quantity"]) * float(line["unit_price"])) - float(line["discount_amount"])
        for line in lines
    )
    return {
        "visit_id": visit["id"],
        "route_id": visit["route_id"],
        "customer_id": visit["customer_id"],
        "visit_status": visit["status"],
        "started_at": visit["started_at"],
        "idempotency_key": draft["idempotency_key"],
        "warehouse_ref": draft.get("warehouse_ref"),
        "warehouse_name": draft.get("warehouse_name") or "",
        "lines": lines,
        "line_count": len(lines),
        "total_amount": round(total, 2),
        "payment_type": draft["payment_type"],
        "order_type": draft["order_type"],
        "outcome": "no_visit" if draft["outcome"] == "skipped" else draft["outcome"],
        "outcome_reason": draft["outcome_reason"],
        "outcome_reason_id": draft.get("outcome_reason_id"),
        "visit_status_id": draft.get("visit_status_id"),
        "start_distance_meters": visit.get("start_distance_meters"),
        "ngt_send_enabled": False,
        "ngt_status": "not_sent",
    }


def _distance_meters(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    earth_radius = 6_371_000.0
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = math.radians(latitude_b - latitude_a)
    delta_lon = math.radians(longitude_b - longitude_a)
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    return earth_radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _validate_visit_location(route: dict[str, Any], customer: dict[str, Any], payload: PrevisitVisitStartRequest) -> float | None:
    policy = route.get("visit_location_policy") or {}
    if not policy.get("enabled") or not policy.get("enforced") or customer.get("location_check_exempt"):
        return None
    if payload.latitude is None or payload.longitude is None:
        raise PrevisitError("برای شروع ویزیت، موقعیت فعلی بازاریاب باید از GPS دریافت شود")
    customer_latitude = customer.get("latitude")
    customer_longitude = customer.get("longitude")
    if customer_latitude is None or customer_longitude is None:
        raise PrevisitError("موقعیت مشتری ثبت نشده است؛ ابتدا موقعیت مشتری را ثبت و پیش‌نویس تغییرات را ذخیره کنید")
    distance = _distance_meters(
        float(payload.latitude), float(payload.longitude),
        float(customer_latitude), float(customer_longitude),
    )
    maximum = policy.get("max_distance_meters")
    if maximum is not None and distance > float(maximum):
        raise PrevisitError(f"فاصله شما از مشتری {round(distance):,} متر است؛ حداکثر فاصله مجاز NGT {int(maximum):,} متر است")
    return round(distance, 2)


def _validate_required_customer_fields(route: dict[str, Any], customer: dict[str, Any]) -> None:
    policy = route.get("visit_location_policy") or {}
    aliases = {
        "phone": "phone", "mobile": "mobile", "storename": "store_name", "store_name": "store_name",
        "address": "address", "customercode": "code", "customer_code": "code",
        "latitude": "latitude", "longitude": "longitude",
    }
    missing = []
    for configured in policy.get("required_customer_fields") or []:
        normalized = str(configured).replace(" ", "").replace("-", "_").casefold()
        field = aliases.get(normalized)
        if field and customer.get(field) in (None, ""):
            missing.append(str(configured))
    if missing:
        raise PrevisitError("اطلاعات اجباری مشتری باید پیش از شروع ویزیت تکمیل شود: " + "، ".join(missing))


def start_visit(settings: Any, username: str, payload: PrevisitVisitStartRequest) -> dict[str, Any]:
    try:
        require_seller_day_route(settings, username, payload.route_id)
    except SellerDayRouteMismatch as exc:
        raise PrevisitError(str(exc)) from exc
    try:
        route = seller_route_customers(settings, username, payload.route_id)
    except SellerRouteNotFound as exc:
        raise PrevisitError("Route was not found in the seller assignment") from exc
    customer_id = str(payload.customer_id)
    customer = next((item for item in route["customers"] if str(item["id"]) == customer_id), None)
    if customer is None:
        raise PrevisitError("Customer is not assigned to this route")
    start_distance = _validate_visit_location(route, customer, payload)

    timestamp = _now()
    visit_id = str(uuid4())
    draft_id = str(uuid4())
    idempotency_key = str(uuid4())
    # Uvicorn runs sync endpoints in a thread pool, and more than one Uvicorn
    # process may share this SQLite file.  The in-process lock handles repeated
    # taps in one worker; BEGIN IMMEDIATE makes the check/insert atomic across
    # workers.  Short retries absorb a concurrent local write instead of
    # turning customer entry into a raw HTTP 500.
    with _visit_start_lock:
        for attempt in range(len(_visit_start_retry_delays) + 1):
            try:
                with sqlite_connection(settings.sqlite_path) as connection:
                    connection.execute(f"PRAGMA busy_timeout={_visit_start_busy_timeout_ms}")
                    connection.execute("BEGIN IMMEDIATE")
                    existing = connection.execute(
                        "SELECT id FROM previsit_visits WHERE username = ? AND route_id = ? AND customer_id = ? AND status = 'active'",
                        (username, payload.route_id, customer_id),
                    ).fetchone()
                    if existing:
                        visit_id = str(existing["id"])
                    else:
                        connection.execute(
                            """INSERT INTO previsit_visits
                               (id, username, route_id, customer_id, status, started_at, start_latitude, start_longitude,
                                start_accuracy, start_distance_meters, created_at, updated_at)
                               VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)""",
                            (visit_id, username, payload.route_id, customer_id, timestamp, payload.latitude, payload.longitude,
                             payload.accuracy, start_distance, timestamp, timestamp),
                        )
                        connection.execute(
                            """INSERT INTO previsit_drafts
                               (id, visit_id, username, idempotency_key, cart_json, payment_type, order_type, outcome, outcome_reason, updated_at)
                               VALUES (?, ?, ?, ?, '[]', '', '', 'draft', '', ?)""",
                            (draft_id, visit_id, username, idempotency_key, timestamp),
                        )
                break
            except sqlite3.OperationalError as exc:
                is_locked = "locked" in str(exc).casefold() or "busy" in str(exc).casefold()
                if not is_locked:
                    raise
                if attempt >= len(_visit_start_retry_delays):
                    raise PrevisitError(
                        "شروع ویزیت به‌دلیل هم‌زمانی عملیات انجام نشد؛ دوباره تلاش کنید"
                    ) from exc
                time.sleep(_visit_start_retry_delays[attempt])
    return get_visit_draft(settings, username, visit_id)


def get_visit_draft(settings: Any, username: str, visit_id: str) -> dict[str, Any]:
    return _serialize_draft(_owned_visit(settings, username, visit_id), _draft(settings, username, visit_id))


def update_draft(settings: Any, username: str, visit_id: str, payload: PrevisitDraftUpdateRequest) -> dict[str, Any]:
    visit = _owned_visit(settings, username, visit_id)
    if visit["status"] != "active":
        raise PrevisitError("This visit is already closed")
    lines = [line.model_dump() for line in payload.lines]
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """UPDATE previsit_drafts SET cart_json = ?, payment_type = ?, order_type = ?,
                   warehouse_ref = ?, warehouse_name = ?, updated_at = ?
               WHERE visit_id = ? AND username = ?""",
            (
                json.dumps(lines, ensure_ascii=False, separators=(",", ":")),
                payload.payment_type.strip(), payload.order_type.strip(), payload.warehouse_ref,
                payload.warehouse_name.strip(), _now(), visit_id, username,
            ),
        )
    return get_visit_draft(settings, username, visit_id)


def _saved_request_row(settings: Any, username: str, visit_id: str, request_id: str) -> dict[str, Any]:
    with sqlite_connection(settings.sqlite_path) as connection:
        row = connection.execute(
            """SELECT * FROM previsit_saved_requests
               WHERE id = ? AND visit_id = ? AND username = ?""",
            (request_id, visit_id, username),
        ).fetchone()
    if not row:
        raise PrevisitError("درخواست ذخیره‌شده پیدا نشد")
    return dict(row)


def _serialize_saved_request(row: dict[str, Any]) -> dict[str, Any]:
    lines = json.loads(row.get("cart_json") or "[]")
    preview = json.loads(row.get("preview_json") or "{}")
    fallback_total = sum(
        (float(line.get("quantity") or 0) * float(line.get("unit_price") or 0))
        - float(line.get("discount_amount") or 0)
        for line in lines
    )
    totals = preview.get("totals") if isinstance(preview, dict) else {}
    total_amount = (totals or {}).get("net", fallback_total)
    return {
        "id": row["id"],
        "visit_id": row["visit_id"],
        "route_id": row["route_id"],
        "customer_id": row["customer_id"],
        "request_number": int(row["request_number"]),
        "lines": lines,
        "line_count": len(lines),
        "total_amount": round(float(total_amount or 0), 2),
        "payment_type": row.get("payment_type") or "",
        "order_type": row.get("order_type") or "",
        "warehouse_ref": row.get("warehouse_ref"),
        "warehouse_name": row.get("warehouse_name") or "",
        "preview": preview,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _saved_request_payload(payload: PrevisitSavedRequestUpsert) -> tuple[str, str]:
    lines = [line.model_dump() for line in payload.lines]
    if not lines:
        raise PrevisitError("برای ذخیره درخواست، سبد خرید نباید خالی باشد")
    cart_json = json.dumps(lines, ensure_ascii=False, separators=(",", ":"))
    preview_json = json.dumps(payload.preview or {}, ensure_ascii=False, separators=(",", ":"))
    if len(preview_json.encode("utf-8")) > 2_000_000:
        raise PrevisitError("اطلاعات محاسبه درخواست بیش از حد مجاز است")
    return cart_json, preview_json


def create_saved_request(
    settings: Any, username: str, visit_id: str, payload: PrevisitSavedRequestUpsert,
) -> dict[str, Any]:
    visit = _owned_visit(settings, username, visit_id)
    if visit["status"] != "active":
        raise PrevisitError("این ویزیت پایان یافته است")
    cart_json, preview_json = _saved_request_payload(payload)
    request_id = str(uuid4())
    timestamp = _now()
    # Keep numbering and insertion in one SQLite statement. This avoids taking
    # an eager write lock before the number is known and lets short concurrent
    # writes from the app finish without losing the seller's request.
    with _saved_request_write_lock:
        for attempt in range(len(_saved_request_retry_delays) + 1):
            try:
                with sqlite_connection(settings.sqlite_path) as connection:
                    connection.execute("PRAGMA busy_timeout=3000")
                    connection.execute(
                        """INSERT INTO previsit_saved_requests
                           (id, visit_id, username, route_id, customer_id, request_number, cart_json,
                            payment_type, order_type, warehouse_ref, warehouse_name, preview_json,
                            created_at, updated_at)
                           SELECT ?, ?, ?, ?, ?, COALESCE(MAX(request_number), 0) + 1, ?, ?, ?, ?, ?, ?, ?, ?
                           FROM previsit_saved_requests
                           WHERE visit_id = ? AND username = ?""",
                        (
                            request_id, visit_id, username, visit["route_id"], visit["customer_id"],
                            cart_json, payload.payment_type.strip(), payload.order_type.strip(),
                            payload.warehouse_ref, payload.warehouse_name.strip(), preview_json,
                            timestamp, timestamp, visit_id, username,
                        ),
                    )
                    connection.execute(
                        """UPDATE previsit_drafts
                           SET cart_json = '[]', payment_type = ?, order_type = ?, warehouse_ref = ?,
                               warehouse_name = ?, updated_at = ?
                           WHERE visit_id = ? AND username = ?""",
                        (
                            payload.payment_type.strip(), payload.order_type.strip(), payload.warehouse_ref,
                            payload.warehouse_name.strip(), timestamp, visit_id, username,
                        ),
                    )
                break
            except sqlite3.OperationalError as exc:
                is_locked = "locked" in str(exc).casefold() or "busy" in str(exc).casefold()
                if not is_locked:
                    raise
                if attempt >= len(_saved_request_retry_delays):
                    raise PrevisitError(
                        "ذخیره درخواست به‌دلیل هم‌زمانی عملیات انجام نشد؛ دوباره تلاش کنید"
                    ) from exc
                time.sleep(_saved_request_retry_delays[attempt])
    return get_saved_request(settings, username, visit_id, request_id)


def list_saved_requests(settings: Any, username: str, visit_id: str) -> list[dict[str, Any]]:
    _owned_visit(settings, username, visit_id)
    with sqlite_connection(settings.sqlite_path) as connection:
        rows = connection.execute(
            """SELECT * FROM previsit_saved_requests
               WHERE visit_id = ? AND username = ?
               ORDER BY request_number DESC""",
            (visit_id, username),
        ).fetchall()
    return [_serialize_saved_request(dict(row)) for row in rows]


def list_route_saved_requests(settings: Any, username: str, route_id: str) -> list[dict[str, Any]]:
    """Return the seller's saved requests for the active Tehran business day."""
    tehran_now = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Tehran"))
    day_start = tehran_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    start_utc = day_start.astimezone(timezone.utc).isoformat()
    end_utc = day_end.astimezone(timezone.utc).isoformat()
    with sqlite_connection(settings.sqlite_path) as connection:
        rows = connection.execute(
            """SELECT * FROM previsit_saved_requests
               WHERE username = ? AND route_id = ? AND created_at >= ? AND created_at < ?
               ORDER BY updated_at DESC, request_number DESC""",
            (username, str(route_id), start_utc, end_utc),
        ).fetchall()
    return [_serialize_saved_request(dict(row)) for row in rows]


def get_saved_request(
    settings: Any, username: str, visit_id: str, request_id: str,
) -> dict[str, Any]:
    _owned_visit(settings, username, visit_id)
    return _serialize_saved_request(_saved_request_row(settings, username, visit_id, request_id))


def update_saved_request(
    settings: Any, username: str, visit_id: str, request_id: str, payload: PrevisitSavedRequestUpsert,
) -> dict[str, Any]:
    visit = _owned_visit(settings, username, visit_id)
    if visit["status"] != "active":
        raise PrevisitError("این ویزیت پایان یافته است")
    _saved_request_row(settings, username, visit_id, request_id)
    cart_json, preview_json = _saved_request_payload(payload)
    timestamp = _now()
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """UPDATE previsit_saved_requests
               SET cart_json = ?, payment_type = ?, order_type = ?, warehouse_ref = ?, warehouse_name = ?,
                   preview_json = ?, updated_at = ?
               WHERE id = ? AND visit_id = ? AND username = ?""",
            (
                cart_json, payload.payment_type.strip(), payload.order_type.strip(), payload.warehouse_ref,
                payload.warehouse_name.strip(), preview_json, timestamp, request_id, visit_id, username,
            ),
        )
        connection.execute(
            """UPDATE previsit_drafts
               SET cart_json = '[]', payment_type = ?, order_type = ?, warehouse_ref = ?,
                   warehouse_name = ?, updated_at = ?
               WHERE visit_id = ? AND username = ?""",
            (
                payload.payment_type.strip(), payload.order_type.strip(), payload.warehouse_ref,
                payload.warehouse_name.strip(), timestamp, visit_id, username,
            ),
        )
    return get_saved_request(settings, username, visit_id, request_id)


def complete_visit(settings: Any, username: str, visit_id: str, payload: PrevisitOutcomeRequest) -> dict[str, Any]:
    visit = _owned_visit(settings, username, visit_id)
    if visit["status"] != "active":
        raise PrevisitError("This visit is already closed")
    draft = _draft(settings, username, visit_id)
    lines = json.loads(draft["cart_json"])
    with sqlite_connection(settings.sqlite_path) as connection:
        saved_request_count = int(connection.execute(
            "SELECT COUNT(*) FROM previsit_saved_requests WHERE visit_id = ? AND username = ?",
            (visit_id, username),
        ).fetchone()[0])
    if payload.outcome == "order" and not lines and not saved_request_count:
        raise PrevisitError("پایان ویزیت سفارشی نیاز به حداقل یک درخواست ذخیره‌شده دارد")
    normalized_outcome = "no_visit" if payload.outcome == "skipped" else payload.outcome
    resolution = {"reason_id": None, "reason": "", "visit_status_id": None}
    if normalized_outcome in {"no_order", "no_visit"}:
        if not payload.reason_id:
            raise PrevisitError("برای تعیین تکلیف مشتری، انتخاب دلیل NGT الزامی است")
        resolution = resolve_ngt_visit_outcome(
            settings,
            username,
            str(visit["route_id"]),
            str(visit["customer_id"]),
            normalized_outcome,
            payload.reason_id,
        )
    timestamp = _now()
    stored_outcome = "skipped" if normalized_outcome == "no_visit" else normalized_outcome
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """UPDATE previsit_visits SET status = 'completed', ended_at = ?, end_latitude = ?, end_longitude = ?, end_accuracy = ?, updated_at = ?
               WHERE id = ? AND username = ?""",
            (timestamp, payload.latitude, payload.longitude, payload.accuracy, timestamp, visit_id, username),
        )
        connection.execute(
            """UPDATE previsit_drafts SET outcome = ?, outcome_reason = ?, outcome_reason_id = ?, visit_status_id = ?, updated_at = ?
               WHERE visit_id = ? AND username = ?""",
            (stored_outcome, resolution["reason"], resolution["reason_id"], resolution["visit_status_id"], timestamp, visit_id, username),
        )
    return get_visit_draft(settings, username, visit_id)
