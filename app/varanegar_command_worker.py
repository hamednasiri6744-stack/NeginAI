"""Durable, retryable worker for commands sent to the Varanegar SQL wrapper."""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from typing import Any, Iterator

from app.enterprise_store import EnterpriseStore, EnterpriseStoreError
from app.varanegar_order_bridge import (
    VaranegarOrderBridgeError,
    _fetch_committed_response,
    _positive_order_number,
    _procedure,
    _safe_error,
    _write_connection,
)

SUPPORTED_COMMAND = "varanegar.order.submit.v1"


@contextmanager
def _lease_heartbeat(
    store: EnterpriseStore, command, *, lease_seconds: int
) -> Iterator[list[BaseException]]:
    failures: list[BaseException] = []
    stop = threading.Event()
    interval = max(1.0, lease_seconds / 3.0)

    def beat() -> None:
        while not stop.wait(interval):
            try:
                store.renew_command_lease(command, lease_seconds=lease_seconds)
            except BaseException as exc:
                failures.append(exc)
                stop.set()
                return

    thread = threading.Thread(
        target=beat,
        name=f"negin-lease-{command.command_id[:8]}",
        daemon=True,
    )
    thread.start()
    try:
        yield failures
    finally:
        stop.set()
        thread.join(timeout=min(2.0, interval))



def dispatch_varanegar_order(settings: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Execute one idempotent payload and require a positive official number."""
    required = {"order_unique_id", "requested_by", "system_username", "lines"}
    if not required.issubset(payload):
        raise VaranegarOrderBridgeError("قرارداد فرمان سفارش ورانگر کامل نیست")
    procedure = _procedure(settings)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with _write_connection(settings) as connection:
        cursor = connection.cursor()
        placeholders = "%s" if str(settings.varanegar_order_sql_client).lower() == "pytds" else "?"
        sql = (
            f"EXEC {procedure} @OrderUniqueId={placeholders}, @RequestedBy={placeholders}, "
            f"@SystemUsername={placeholders}, @PayloadJson={placeholders}"
        )
        cursor.execute(
            sql,
            (
                payload["order_unique_id"],
                payload["requested_by"],
                payload["system_username"],
                encoded,
            ),
        )
        response = _fetch_committed_response(cursor)
        if response is None:
            raise VaranegarOrderBridgeError("رویه ثبت سفارش نتیجه‌ای برنگرداند")
        if not bool(response.get("Committed") or response.get("committed")):
            raise VaranegarOrderBridgeError(
                str(response.get("Message") or response.get("message") or "ثبت سفارش رد شد")
            )
        order_number = _positive_order_number(response)
        connection.commit()
    return {
        "committed": True,
        "order_ref": response.get("OrderRef") or response.get("order_ref"),
        "order_no": order_number,
        "order_unique_id": str(
            response.get("OrderUniqueId")
            or response.get("order_unique_id")
            or payload["order_unique_id"]
        ),
    }


def process_one(
    store: EnterpriseStore,
    settings: Any,
    *,
    worker_id: str,
    max_attempts: int = 8,
    lease_seconds: int = 120,
) -> dict[str, Any] | None:
    """Claim and settle at most one command; never acknowledge before receipt."""
    command = store.claim_command(worker_id=worker_id, lease_seconds=lease_seconds)
    if command is None:
        return None
    if command.command_type != SUPPORTED_COMMAND:
        status = store.mark_failed(
            command,
            error_code="UNSUPPORTED_COMMAND",
            safe_message="unsupported durable command type",
            outcome_unknown=False,
            max_attempts=1,
        )
        return {"command_id": command.command_id, "status": status}
    try:
        with _lease_heartbeat(store, command, lease_seconds=lease_seconds) as lease_failures:
            result = dispatch_varanegar_order(settings, command.payload)
        if lease_failures:
          raise EnterpriseStoreError("command lease renewal failed during dispatch")
        external_id = str(result.get("order_ref") or result.get("order_no") or "")
        if not external_id:
            raise VaranegarOrderBridgeError("ورانگر شناسه رسمی سفارش را برنگرداند")
        store.mark_succeeded(
            command,
            external_system="Varanegar",
            external_id=external_id,
            details=result,
        )
        return {"command_id": command.command_id, "status": "succeeded", **result}
    except VaranegarOrderBridgeError as exc:
        status = store.mark_failed(
            command,
            error_code="VARANEGAR_REJECTED",
            safe_message=_safe_error(exc),
            outcome_unknown=False,
            max_attempts=max_attempts,
        )
        return {"command_id": command.command_id, "status": status}
    except EnterpriseStoreError:
        # A stale worker must never settle after losing its lease.
        raise
    except Exception as exc:
        # Transport loss after dispatch is an unknown outcome. The SQL wrapper's
        # idempotency key makes retry safe; the receipt preserves the uncertainty.
        status = store.mark_failed(
            command,
            error_code="VARANEGAR_OUTCOME_UNKNOWN",
            safe_message=_safe_error(exc),
            outcome_unknown=True,
            max_attempts=max_attempts,
        )
        return {"command_id": command.command_id, "status": status}
