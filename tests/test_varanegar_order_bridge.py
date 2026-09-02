from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.database import sqlite_connection
from app.models import PrevisitOutcomeRequest
from app.routes.seller_workspace import complete_my_previsit
from app.varanegar_order_bridge import (
    VaranegarOrderBridgeError,
    VaranegarOrderBridgeUnavailable,
    _fetch_committed_response,
    submit_validated_order,
)


def _active_draft(settings, *, key: str = "8c10b26e-b490-4e23-9625-ed34539bef6d") -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """INSERT INTO previsit_visits
               (id, username, route_id, customer_id, status, started_at, created_at, updated_at)
               VALUES ('visit-1', 'seller', '98', '7494', 'active', ?, ?, ?)""",
            (now, now, now),
        )
        connection.execute(
            """INSERT INTO previsit_drafts
               (id, visit_id, username, idempotency_key, cart_json, payment_type, order_type, outcome, updated_at)
               VALUES ('draft-1', 'visit-1', 'seller', ?, '[]', 'نقدی', 'عادی', 'draft', ?)""",
            (key, now),
        )


def _validation(*, prizes: bool = False):
    return {
        "totals": {"net": 1_200_000},
        "_submission_contract": {
            "customer_ref": 7494,
            "dealer_ref": 22,
            "order_type_ref": 2,
            "payment_usance_ref": 401,
            "sale_office_ref": 1,
            "dc_ref": 1,
            "route_id": "98",
            "has_prizes": prizes,
            "lines": [
                {
                    "product_ref": 4014,
                    "product_unique_id": "96522c6d-06da-446d-8339-4edf496d54ff",
                    "stock_ref": 1,
                    "quantity": 12,
                    "unit_price": 100_000,
                    "cprice_ref": 152007,
                    "acc_year": 1405,
                    "unit_ref": 3,
                    "pay_duration": 0,
                    "pay_discount_ref": None,
                }
            ],
        },
    }


def _configured(settings):
    return replace(
        settings,
        varanegar_order_bridge_enabled=True,
        varanegar_order_commit_enabled=True,
        varanegar_order_numbering_verified=True,
        varanegar_order_sql_server="db",
        varanegar_order_sql_username="execute_only",
        varanegar_order_sql_password="secret",
    )


def test_bridge_is_disabled_by_default_and_creates_no_submission(settings):
    _active_draft(settings)
    with pytest.raises(VaranegarOrderBridgeUnavailable):
        submit_validated_order(settings, "seller", "visit-1", _validation())
    with sqlite_connection(settings.sqlite_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM previsit_submissions").fetchone()[0] == 0


def test_validation_only_mode_never_opens_operational_connection(settings, monkeypatch):
    _active_draft(settings)
    configured = replace(settings, varanegar_order_bridge_enabled=True)
    monkeypatch.setattr(
        "app.varanegar_order_bridge._write_connection",
        lambda _settings: pytest.fail("operational connection must remain closed"),
    )
    result = submit_validated_order(configured, "seller", "visit-1", _validation())
    assert result["status"] == "prepared"
    assert result["committed"] is False
    with sqlite_connection(settings.sqlite_path) as connection:
        row = connection.execute("SELECT status, payload_json FROM previsit_submissions").fetchone()
    assert row["status"] == "prepared"
    assert json.loads(row["payload_json"])["system_username"] == "VnAdmin"


def test_unverified_numbering_blocks_before_operational_connection(settings, monkeypatch):
    _active_draft(settings)
    configured = replace(
        settings,
        varanegar_order_bridge_enabled=True,
        varanegar_order_commit_enabled=True,
        varanegar_order_sql_server="db",
        varanegar_order_sql_username="execute_only",
        varanegar_order_sql_password="secret",
    )
    monkeypatch.setattr(
        "app.varanegar_order_bridge._write_connection",
        lambda _settings: pytest.fail("unverified numbering must not open an operational connection"),
    )

    with pytest.raises(VaranegarOrderBridgeUnavailable, match="شماره‌گذاری"):
        submit_validated_order(configured, "seller", "visit-1", _validation())


def test_committed_positive_order_is_idempotent(settings, monkeypatch):
    _active_draft(settings)
    calls = []

    class Cursor:
        description = [("Committed",), ("OrderRef",), ("OrderNo",), ("OrderUniqueId",), ("Message",)]

        def execute(self, sql, params):
            calls.append((sql, params))

        def fetchone(self):
            return (1, 12345, 58939, None, "ok")

        def nextset(self):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            calls.append("commit")

    @contextmanager
    def fake_connection(_settings):
        yield Connection()

    monkeypatch.setattr("app.varanegar_order_bridge._write_connection", fake_connection)
    first = submit_validated_order(_configured(settings), "seller", "visit-1", _validation())
    second = submit_validated_order(_configured(settings), "seller", "visit-1", _validation())
    assert first["committed"] is True
    assert first["order_no"] == 58939
    assert second["idempotent_replay"] is True
    assert len([item for item in calls if isinstance(item, tuple)]) == 1


def test_negative_temporary_order_number_is_never_committed(settings, monkeypatch):
    _active_draft(settings)
    calls = []

    class Cursor:
        description = [("Committed",), ("OrderRef",), ("OrderNo",), ("Message",)]

        def execute(self, _sql, _params):
            calls.append("execute")

        def fetchone(self):
            return (1, 333013, -333013, "temporary")

        def nextset(self):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def commit(self):
            calls.append("commit")

    @contextmanager
    def fake_connection(_settings):
        yield Connection()

    monkeypatch.setattr("app.varanegar_order_bridge._write_connection", fake_connection)
    with pytest.raises(VaranegarOrderBridgeError, match="شماره موقت"):
        submit_validated_order(_configured(settings), "seller", "visit-1", _validation())
    assert calls == ["execute"]
    with sqlite_connection(settings.sqlite_path) as connection:
        row = connection.execute("SELECT status FROM previsit_submissions").fetchone()
    assert row["status"] == "failed"


def test_bridge_response_skips_legacy_non_result_sets():
    class Cursor:
        def __init__(self):
            self.index = 0
            self.descriptions = [None, [("ErrNumber",), ("ErrMessage",)], [("Committed",), ("OrderRef",)]]

        @property
        def description(self):
            return self.descriptions[self.index]

        def fetchone(self):
            return (1, 12345)

        def nextset(self):
            self.index += 1
            return self.index < len(self.descriptions)

    assert _fetch_committed_response(Cursor()) == {"Committed": 1, "OrderRef": 12345}


def test_prize_order_is_blocked_until_prize_contract_is_supported(settings):
    _active_draft(settings)
    configured = replace(settings, varanegar_order_bridge_enabled=True)
    with pytest.raises(VaranegarOrderBridgeError, match="جایزه"):
        submit_validated_order(configured, "seller", "visit-1", _validation(prizes=True))


def test_disabled_bridge_preserves_existing_local_completion_flow(settings, monkeypatch):
    validation = {"credit_control": {"allowed": True}, "totals": {"net": 1_200_000}}
    monkeypatch.setattr("app.routes.seller_workspace.validate_order_draft", lambda *_args: validation)
    monkeypatch.setattr(
        "app.routes.seller_workspace.submit_validated_order",
        lambda *_args: pytest.fail("disabled bridge must not be invoked"),
    )
    monkeypatch.setattr(
        "app.routes.seller_workspace.complete_visit",
        lambda *_args: {"visit_id": "visit-1", "visit_status": "completed"},
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings)),
        state=SimpleNamespace(username="seller"),
    )

    result = complete_my_previsit(
        "visit-1",
        PrevisitOutcomeRequest(outcome="order", reason=""),
        request,
    )

    assert result["visit_status"] == "completed"
    assert result["official_totals"]["net"] == 1_200_000
    assert "order_registration" not in result


def test_sql_wrapper_allocates_from_locked_varanegar_counter_and_never_uses_max_plus_one():
    source = open("scripts/sql/install_varanegar_order_bridge.sql", encoding="utf-8").read()
    compact = "".join(source.upper().split())
    assert "@EXISTINGORDERNO<=0" in compact
    assert "THROW51007" in compact
    assert "ROLLBACKTRANSACTION" in compact
    assert "EXECDBO.NGT_REPLICATEORDERMASTER" in compact
    assert "GNR.DATETIMETOSOLAR(GETDATE(),'YYYY/MM/DD')" not in compact
    assert "FROMDBO.OPRDATEASO" in compact
    assert "O.DCID=@DCREF" in compact
    assert "O.SYSREF=1" in compact
    assert "O.ACCYEARNAME=@ACCYEAR" in compact
    assert "O.ISCLOSED=0" in compact
    assert "@SALEOPERATIONDATECOUNT<>1OR@SALEOPERATIONDATEISNULL" in compact
    assert "THROW51008" in compact
    assert "@ORDERUNIQUEID,@SALEOPERATIONDATE,@CUSTOMERUNIQUEID,@DEALERUNIQUEID,@SALEOPERATIONDATE" in compact
    assert "FREEREASONIDUNIQUEIDENTIFIERNULL" in compact
    assert "CREATETABLE#TBLTEMPEVC" in compact
    assert "CREATETABLE#TBLTEMPEVCITEM" in compact
    assert "CREATETABLE#TBLTEMPEVCITEMSTATUTES" in compact
    assert "CREATETABLE#TBLTEMPEVCSKIPDISCOUNT" in compact
    assert "CREATETABLE#TBLTEMPEVCPRIZE" in compact
    assert "CREATETABLE#TBLTEMPEVCPERIODICDISCOUNT" in compact
    assert "CREATETABLE#TBLTEMPEVCPRIZEPACKAGE" in compact
    assert "@HEADERORDERNO<>-@EXISTINGORDERREF" in compact
    assert "UPDATEDBO.TBLORDERNOWITH(UPDLOCK,HOLDLOCK)" in compact
    assert "OUTPUTINSERTED.ORDERNOINTO@ALLOCATED(ORDERNO)" in compact
    assert "SALEOFFICEREF=@SALEOFFICEREF" in compact
    assert "ACCYEAR=@ACCYEAR" in compact
    assert "DCREF=@DCREF" in compact
    assert "UPDATESLE.TBLORDERHDR" in compact
    assert "ORDERNO=@ALLOCATEDORDERNO" in compact
    assert "THEALLOCATEDVARANEGARREQUESTNUMBERALREADYEXISTS" in compact
    assert "UPDATE#FINALRESULT" in compact
    assert "MAX(ORDERNO)" not in compact
