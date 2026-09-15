import importlib.util
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("handover_activity", ROOT / "scripts/warehouse_handover_activity.py")
activity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(activity)


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE warehouse_automatic_refresh_state(id,lock_token,lock_expires_at)")
    yield connection
    connection.close()


@pytest.mark.parametrize("table,status", [
    ("warehouse_email_attempts", "sending"),
    ("warehouse_supplier_order_email_attempts", "sending"),
    ("warehouse_supplier_portal_email_attempts", "sending"),
    ("warehouse_sms_downloads", "sending"),
    ("warehouse_checkbar_transfers", "pending"),
    ("warehouse_purchase_invoice_attempts", "pending"),
    ("warehouse_transfer_bridge_intents", "pending"),
    ("warehouse_transfer_bridge_intents", "blocked"),
])
def test_inflight_operations_refuse_handover(conn, table, status):
    conn.execute("CREATE TABLE " + table + " (status)")
    conn.execute("INSERT INTO " + table + " VALUES (?)", (status,))
    with pytest.raises(RuntimeError, match="active"):
        activity.assert_warehouse_idle(conn)
    conn.execute("UPDATE " + table + " SET status='sent'")
    activity.assert_warehouse_idle(conn)


def test_refresh_and_portal_sms_guard(conn):
    conn.execute("INSERT INTO warehouse_automatic_refresh_state VALUES(1,'busy','2999-01-01T00:00:00+00:00')")
    with pytest.raises(RuntimeError, match="refresh"):
        activity.assert_warehouse_idle(conn)
    conn.execute("DELETE FROM warehouse_automatic_refresh_state")
    conn.execute("CREATE TABLE warehouse_supplier_portal_sms_attempts(status,error)")
    conn.execute("INSERT INTO warehouse_supplier_portal_sms_attempts VALUES('unknown',?)", ("ارسال در جریان است؛ نتیجه هنوز قطعی نیست.",))
    with pytest.raises(RuntimeError, match="SMS"):
        activity.assert_warehouse_idle(conn)


def test_idle_check_does_not_commit_or_change_data(conn):
    conn.execute("BEGIN IMMEDIATE")
    activity.assert_warehouse_idle(conn)
    assert conn.in_transaction
    assert conn.total_changes == 0


def test_handover_scope_keeps_limited_launcher_and_single_stop():
    source = (ROOT / "scripts/transition_warehouse_worker_once.ps1").read_text()
    assert source.count("Stop-Process") == 1
    assert "Stop-Process -Id $ExpectedPid" in source
    assert "Assert-WarehouseRestartTask" in source
    assert "CreationDate -ne $worker.CreationDate" in source
    assert "$replacementOwner.Sid -eq $serviceSid" in source
    assert "Start-Process" not in source
    launcher = (ROOT / "scripts/start_public_service.ps1").read_text()
    assert launcher.index("$serviceIdentity.IsSystem") < launcher.index("warehouse-handover.request")
