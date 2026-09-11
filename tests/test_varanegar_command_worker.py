from types import SimpleNamespace
import time

import pytest

from app.enterprise_store import ClaimedCommand, EnterpriseStoreError
from app.varanegar_command_worker import process_one


def _command(command_type="varanegar.order.submit.v1"):
    return ClaimedCommand(
        command_id="command-1",
        idempotency_key="key-1",
        command_type=command_type,
        subject="seller",
        payload={"order_unique_id": "key-1"},
        attempt_count=1,
        worker_id="worker-1",
    )


class Store:
    def __init__(self, command):
        self.command = command
        self.success = None
        self.failure = None

    def claim_command(self, **_kwargs):
        return self.command

    def renew_command_lease(self, command, **_kwargs):
        return None

    def mark_succeeded(self, command, **kwargs):
        self.success = (command, kwargs)

    def mark_failed(self, command, **kwargs):
        self.failure = (command, kwargs)
        return "retry" if kwargs["max_attempts"] > 1 else "dead_letter"


def test_worker_writes_success_receipt_only_after_official_id(monkeypatch):
    store = Store(_command())
    monkeypatch.setattr(
        "app.varanegar_command_worker.dispatch_varanegar_order",
        lambda *_args: {"committed": True, "order_ref": 42, "order_no": 7},
    )
    result = process_one(store, SimpleNamespace(), worker_id="worker-1")
    assert result["status"] == "succeeded"
    assert store.success[1]["external_system"] == "Varanegar"
    assert store.success[1]["external_id"] == "42"
    assert store.failure is None


def test_transport_failure_is_recorded_as_unknown_and_retried(monkeypatch):
    store = Store(_command())

    def fail(*_args):
        raise ConnectionError("private host detail")

    monkeypatch.setattr("app.varanegar_command_worker.dispatch_varanegar_order", fail)
    result = process_one(store, SimpleNamespace(), worker_id="worker-1")
    assert result["status"] == "retry"
    assert store.failure[1]["outcome_unknown"] is True
    assert store.failure[1]["error_code"] == "VARANEGAR_OUTCOME_UNKNOWN"


def test_unknown_command_is_dead_lettered_without_dispatch(monkeypatch):
    store = Store(_command("future.command"))
    monkeypatch.setattr(
        "app.varanegar_command_worker.dispatch_varanegar_order",
        lambda *_args: (_ for _ in ()).throw(AssertionError("must not dispatch")),
    )
    result = process_one(store, SimpleNamespace(), worker_id="worker-1")
    assert result["status"] == "dead_letter"
    assert store.failure[1]["error_code"] == "UNSUPPORTED_COMMAND"


def test_heartbeat_renews_lease_during_blocking_dispatch(monkeypatch):
    store = Store(_command())
    renewals = []
    store.renew_command_lease = lambda command, **kwargs: renewals.append((command, kwargs))

    def slow_dispatch(*_args):
        time.sleep(1.15)
        return {"committed": True, "order_ref": 42, "order_no": 7}

    monkeypatch.setattr("app.varanegar_command_worker.dispatch_varanegar_order", slow_dispatch)
    result = process_one(store, SimpleNamespace(), worker_id="worker-1", lease_seconds=3)
    assert result["status"] == "succeeded"
    assert len(renewals) >= 1


def test_heartbeat_lease_loss_fails_closed_without_stale_settlement(monkeypatch):
    store = Store(_command())

    def lost_lease(*_args, **_kwargs):
        raise EnterpriseStoreError("lost")

    store.renew_command_lease = lost_lease

    def slow_dispatch(*_args):
        time.sleep(1.15)
        return {"committed": True, "order_ref": 42, "order_no": 7}

    monkeypatch.setattr("app.varanegar_command_worker.dispatch_varanegar_order", slow_dispatch)
    with pytest.raises(EnterpriseStoreError, match="lease renewal failed"):
        process_one(store, SimpleNamespace(), worker_id="worker-1", lease_seconds=3)
    assert store.success is None
    assert store.failure is None
