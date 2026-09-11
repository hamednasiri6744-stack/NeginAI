from __future__ import annotations

from pathlib import Path

import pytest

from app.enterprise_store import EnterpriseStore, EnterpriseStoreError, canonical_payload


class CapturingPool:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_payload_hash_is_deterministic_across_key_order():
    first, first_hash = canonical_payload({"b": 2, "a": {"y": 1}})
    second, second_hash = canonical_payload({"a": {"y": 1}, "b": 2})
    assert first == second
    assert first_hash == second_hash


def test_store_pool_is_lazy_bounded_and_transactional():
    captured = {}

    def factory(**kwargs):
        captured.update(kwargs)
        return CapturingPool(**kwargs)

    EnterpriseStore("postgresql://app:secret@db/neginai", pool_factory=factory, max_size=16)
    assert captured["min_size"] == 1
    assert captured["max_size"] == 16
    assert captured["open"] is False
    assert captured["kwargs"]["autocommit"] is False


@pytest.mark.parametrize("url", ["", "   "])
def test_store_rejects_missing_database_url(url):
    with pytest.raises(EnterpriseStoreError):
        EnterpriseStore(url, pool_factory=CapturingPool)


def test_migration_contains_skip_locked_leases_receipts_and_audit():
    migration = Path("migrations/postgres/001_enterprise_core.sql").read_text(
        encoding="utf-8"
    ).casefold()
    module = Path("app/enterprise_store.py").read_text(encoding="utf-8").casefold()
    assert "command_outbox" in migration
    assert "command_receipts" in migration
    assert "agent_jobs" in migration
    assert "audit_events" in migration
    assert "for update skip locked" in module
    assert "lease_expired" in module
    assert "dead_letter" in module


def test_command_settlement_and_renewal_are_fenced_to_exact_live_claim():
    module = Path("app/enterprise_store.py").read_text(encoding="utf-8").casefold()
    assert "def renew_command_lease" in module
    assert module.count("and locked_by=%s and attempt_count=%s") >= 3
    assert module.count("and locked_until >= clock_timestamp()") >= 3
    assert "command lease was lost before renewal" in module
    assert "command lease was lost before success" in module
    assert "command lease was lost before failure receipt" in module


def test_expired_lease_recovery_preserves_unknown_receipt_before_retry_contract():
    module = Path("app/enterprise_store.py").read_text(encoding="utf-8").casefold()
    assert "set status='retry'" in module
    assert "'lease', 'unknown'" in module
    assert "lease_expired" in module
