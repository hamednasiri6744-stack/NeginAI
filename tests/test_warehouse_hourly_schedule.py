"""Hourly boundary and single-flight checks; no ERP or scheduler startup."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from app import warehouse_assistant_service as service


@pytest.mark.parametrize('elapsed,running,due', [(3599, False, False), (3600, False, True), (7200, True, False)])
def test_hourly_refresh_boundary_and_busy_lock(tmp_path, monkeypatch, elapsed, running, due):
    now = datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now
    monkeypatch.setattr(service, 'datetime', Clock)
    monkeypatch.setattr(service, 'automatic_refresh_status', lambda _: {
        'running': running, 'last_completed_at': (now - timedelta(seconds=elapsed)).isoformat()})
    settings = SimpleNamespace(sqlite_path=tmp_path / 'isolated.db')
    assert service.automatic_refresh_due(settings) is due
