"""Disabled-by-default bridge for validated Varanegar order registration.

The reporting connection in :mod:`app.database` remains read-only. This
module owns a separate credential that may only execute one reviewed wrapper.
The payload is assembled from a server-side draft and a fresh NGT validation.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import pyodbc
import pytds

from app.database import sqlite_connection


class VaranegarOrderBridgeError(RuntimeError):
    """Base class for safe, user-facing bridge failures."""


class VaranegarOrderBridgeUnavailable(VaranegarOrderBridgeError):
    pass


_PROCEDURE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _procedure(settings: Any) -> str:
    name = str(settings.varanegar_order_procedure or "").strip()
    if not _PROCEDURE_NAME.fullmatch(name):
        raise VaranegarOrderBridgeUnavailable("نام رویه ثبت سفارش ورانگر معتبر نیست")
    return name


@contextmanager
def _write_connection(settings: Any) -> Iterator[Any]:
    """Open the isolated operational connection; never use report credentials."""
    if not settings.varanegar_order_sql_configured:
        raise VaranegarOrderBridgeUnavailable(
            "حساب محدود ثبت سفارش ورانگر هنوز روی سرور تنظیم نشده است"
        )
    client = str(settings.varanegar_order_sql_client or "odbc").lower()
    if client not in {"odbc", "pytds"}:
        raise VaranegarOrderBridgeUnavailable(
            "کلاینت اتصال ثبت سفارش باید odbc یا pytds باشد"
        )
    if client == "pytds":
        server, separator, port_value = settings.varanegar_order_sql_server.partition(",")
        connection = pytds.connect(
            dsn=server.strip(),
            port=int(port_value) if separator and port_value.isdigit() else None,
            database=settings.varanegar_order_sql_database,
            user=settings.varanegar_order_sql_username,
            password=settings.varanegar_order_sql_password,
            timeout=settings.sql_query_timeout,
            login_timeout=settings.sql_query_timeout,
            readonly=False,
            validate_host=True,
        )
    else:
        trust = "yes" if settings.varanegar_order_sql_trust_certificate else "no"
        connection = pyodbc.connect(
            f"DRIVER={{{settings.varanegar_order_sql_driver}}};"
            f"SERVER={settings.varanegar_order_sql_server};"
            f"DATABASE={settings.varanegar_order_sql_database};"
            f"UID={settings.varanegar_order_sql_username};"
            f"PWD={settings.varanegar_order_sql_password};"
            f"TrustServerCertificate={trust};ApplicationIntent=ReadWrite;",
            timeout=settings.sql_query_timeout,
        )
    try:
        connection.autocommit = False
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _draft_identity(settings: Any, username: str, visit_id: str) -> dict[str, str]:
    with sqlite_connection(settings.sqlite_path) as connection:
        row = connection.execute(
            """SELECT d.id, d.idempotency_key
               FROM previsit_drafts AS d
               INNER JOIN previsit_visits AS v ON v.id = d.visit_id
               WHERE d.visit_id = ? AND d.username = ? AND v.status = 'active'""",
            (visit_id, username),
        ).fetchone()
    if not row:
        raise VaranegarOrderBridgeError("پیش‌نویس فعال سفارش پیدا نشد")
    return {"draft_id": str(row["id"]), "idempotency_key": str(row["idempotency_key"])}


def _existing_submission(settings: Any, idempotency_key: str) -> dict[str, Any] | None:
    with sqlite_connection(settings.sqlite_path) as connection:
        row = connection.execute(
            "SELECT status, response_json FROM previsit_submissions WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
    if not row or row["status"] != "sent" or not row["response_json"]:
        return None
    result = json.loads(row["response_json"])
    result["idempotent_replay"] = True
    return result


def _record_prepared(
    settings: Any,
    *,
    draft_id: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """INSERT INTO previsit_submissions
                 (draft_id, idempotency_key, payload_json, status, created_at)
               VALUES (?, ?, ?, 'prepared', ?)
               ON CONFLICT(idempotency_key) DO UPDATE SET
                 payload_json = excluded.payload_json,
                 status = CASE WHEN previsit_submissions.status = 'sent' THEN 'sent' ELSE 'prepared' END""",
            (draft_id, idempotency_key, encoded, _now()),
        )


def _record_result(
    settings: Any,
    idempotency_key: str,
    *,
    status: str,
    response: dict[str, Any],
    response_code: int,
) -> None:
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """UPDATE previsit_submissions
               SET status = ?, response_code = ?, response_json = ?, sent_at = ?
               WHERE idempotency_key = ?""",
            (
                status,
                response_code,
                json.dumps(response, ensure_ascii=False, separators=(",", ":")),
                _now() if status == "sent" else None,
                idempotency_key,
            ),
        )


def _safe_error(exc: Exception) -> str:
    message = str(exc).replace("\r", " ").replace("\n", " ").strip()
    return message[:600] or "خطای نامشخص در ثبت سفارش ورانگر"


def _fetch_committed_response(cursor: Any) -> dict[str, Any] | None:
    """Find the wrapper result after any legacy nested-procedure result sets."""
    while True:
        if cursor.description is not None:
            columns = [str(column[0]) for column in cursor.description]
            if any(column.casefold() == "committed" for column in columns):
                row = cursor.fetchone()
                return dict(zip(columns, row)) if row is not None else None
        if not cursor.nextset():
            return None


def _positive_order_number(response: dict[str, Any]) -> int:
    raw_value = response.get("OrderNo") or response.get("order_no")
    try:
        order_number = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise VaranegarOrderBridgeError(
            "ورانگر شماره نهایی معتبر برای درخواست برنگرداند؛ ثبت تأیید نشد"
        ) from exc
    if order_number <= 0:
        raise VaranegarOrderBridgeError(
            "ورانگر فقط شماره موقت صفر یا منفی برگرداند؛ مرحله شماره‌گذاری رسمی کامل نشده و ثبت تأیید نشد"
        )
    return order_number


def submit_validated_order(
    settings: Any,
    username: str,
    visit_id: str,
    validation: dict[str, Any],
) -> dict[str, Any]:
    """Register one freshly validated draft through the reviewed SQL wrapper."""
    if not settings.varanegar_order_bridge_enabled:
        raise VaranegarOrderBridgeUnavailable(
            "مسیر مستقل ثبت سفارش ورانگر هنوز فعال نشده است؛ هیچ سندی ثبت نشد"
        )
    identity = _draft_identity(settings, username, visit_id)
    replay = _existing_submission(settings, identity["idempotency_key"])
    if replay:
        return replay

    contract = validation.get("_submission_contract")
    if not isinstance(contract, dict) or not contract.get("lines"):
        raise VaranegarOrderBridgeError("قرارداد سروری ثبت سفارش کامل نیست")
    if contract.get("has_prizes"):
        raise VaranegarOrderBridgeError(
            "این سفارش جایزه دارد و تا تکمیل نگاشت جایزه، برای جلوگیری از ثبت ناقص ارسال نشد"
        )
    for line in contract["lines"]:
        if not line.get("cprice_ref") or not int(line.get("acc_year") or 0):
            raise VaranegarOrderBridgeError(
                "قیمت قراردادی یا سال مالی رسمی یکی از اقلام از EVC برنگشت؛ سفارش ارسال نشد"
            )
    payload = {
        "order_unique_id": identity["idempotency_key"],
        "requested_by": username,
        "system_username": settings.varanegar_order_system_username,
        "customer_ref": contract["customer_ref"],
        "dealer_ref": contract["dealer_ref"],
        "order_type_ref": contract["order_type_ref"],
        "payment_usance_ref": contract["payment_usance_ref"],
        "sale_office_ref": contract["sale_office_ref"],
        "dc_ref": contract["dc_ref"],
        "route_id": contract["route_id"],
        "official_net_amount": validation.get("totals", {}).get("net"),
        "lines": contract["lines"],
    }
    _record_prepared(
        settings,
        draft_id=identity["draft_id"],
        idempotency_key=identity["idempotency_key"],
        payload=payload,
    )

    # The commit switch is independent. Validation-only mode never opens the
    # operational database, so legacy procedures cannot consume a number.
    if not settings.varanegar_order_commit_enabled:
        return {
            "status": "prepared",
            "committed": False,
            "message": "کنترل‌ها تأیید شد، اما کلید ثبت نهایی ورانگر خاموش است؛ هیچ سندی ثبت نشد.",
            "idempotency_key": identity["idempotency_key"],
        }

    # The reviewed wrapper now turns the low-level -OrderHdrRef placeholder into
    # the next dbo.tblOrderNo value under a transaction-held row lock. Keep this
    # independent deployment lock until the DBA has installed that exact wrapper
    # and its rollback/concurrency behavior has been accepted for production.
    if not settings.varanegar_order_numbering_verified:
        raise VaranegarOrderBridgeUnavailable(
            "نسخه تراکنشی شماره‌گذاری درخواست ورانگر هنوز روی دیتابیس نصب و تأیید نشده است؛ هیچ سندی ثبت نشد"
        )

    procedure = _procedure(settings)
    encoded_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    try:
        with _write_connection(settings) as connection:
            cursor = connection.cursor()
            if str(settings.varanegar_order_sql_client).lower() == "pytds":
                sql = (
                    f"EXEC {procedure} @OrderUniqueId=%s, @RequestedBy=%s, "
                    "@SystemUsername=%s, @PayloadJson=%s"
                )
            else:
                sql = (
                    f"EXEC {procedure} @OrderUniqueId=?, @RequestedBy=?, "
                    "@SystemUsername=?, @PayloadJson=?"
                )
            cursor.execute(
                sql,
                (
                    identity["idempotency_key"],
                    username,
                    settings.varanegar_order_system_username,
                    encoded_payload,
                ),
            )
            response = _fetch_committed_response(cursor)
            if response is None:
                raise VaranegarOrderBridgeError("رویه ثبت سفارش نتیجه‌ای برنگرداند")
            committed = bool(response.get("Committed") or response.get("committed"))
            if not committed:
                raise VaranegarOrderBridgeError(
                    str(response.get("Message") or response.get("message") or "ثبت سفارش ورانگر تأیید نشد")
                )
            order_number = _positive_order_number(response)
            connection.commit()
        result = {
            "status": "sent",
            "committed": True,
            "order_ref": response.get("OrderRef") or response.get("order_ref"),
            "order_no": order_number,
            "order_unique_id": str(
                response.get("OrderUniqueId")
                or response.get("order_unique_id")
                or identity["idempotency_key"]
            ),
            "message": str(response.get("Message") or response.get("message") or "سفارش در ورانگر ثبت شد"),
            "idempotency_key": identity["idempotency_key"],
        }
        _record_result(
            settings,
            identity["idempotency_key"],
            status="sent",
            response=result,
            response_code=200,
        )
        return result
    except VaranegarOrderBridgeError as exc:
        failure = {"committed": False, "message": _safe_error(exc)}
        _record_result(
            settings,
            identity["idempotency_key"],
            status="failed",
            response=failure,
            response_code=409,
        )
        raise
    except Exception as exc:
        failure = {"committed": False, "message": _safe_error(exc)}
        _record_result(
            settings,
            identity["idempotency_key"],
            status="failed",
            response=failure,
            response_code=502,
        )
        raise VaranegarOrderBridgeError(
            "ارتباط با مسیر محدود ثبت سفارش ورانگر ناموفق بود؛ هیچ ثبت تأییدشده‌ای دریافت نشد"
        ) from exc
