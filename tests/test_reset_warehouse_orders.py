import sqlite3
from pathlib import Path

import pytest
from test_warehouse_supplier_portal import store
from test_warehouse_portal_access import shared
from app import warehouse_assistant_service as service
from app import warehouse_order_sms as sms
from scripts import reset_warehouse_orders as resetter


@pytest.fixture
def reset_store(shared):
    settings = shared[0]
    sms._init_store(settings)
    path = service.warehouse_database_path(settings)
    path.with_name('warehouse-automatic-orders.paused').touch()
    return settings, path


def dump_tables(path, names=None):
    with sqlite3.connect(path) as conn:
        tables = names or [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {t: conn.execute('SELECT * FROM ' + resetter.quoted(t)).fetchall() for t in tables}


def test_reset_preserves_base_accounts_sequences_and_archive_can_restore(reset_store):
    settings, path = reset_store
    before = dump_tables(path)
    result = resetter.reset(path, execute=True)
    after = dump_tables(path)
    assert all(not after[t] for t in resetter.TABLES)
    assert {t: rows for t, rows in before.items() if t not in resetter.TABLES} == {
        t: rows for t, rows in after.items() if t not in resetter.TABLES}
    archived = dump_tables(result['archive'], resetter.TABLES)
    assert archived == {t: before[t] for t in resetter.TABLES}
    # Rehearse restoring original IDs over unchanged base data; no sequences reset.
    with sqlite3.connect(path) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('PRAGMA defer_foreign_keys=ON')
        for table, rows in archived.items():
            if rows:
                conn.executemany('INSERT INTO '+resetter.quoted(table)+' VALUES('+','.join('?' for _ in rows[0])+')',rows)
        conn.commit()
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    assert dump_tables(path) == before


def test_dry_run_and_failed_archive_never_delete(reset_store, monkeypatch):
    settings, path = reset_store
    before = dump_tables(path)
    assert resetter.reset(path)['dry_run']
    assert dump_tables(path) == before
    def fail(*args):
        raise OSError('backup unavailable')
    monkeypatch.setattr(resetter, 'archive_rows', fail)
    with pytest.raises(OSError):
        resetter.reset(path, execute=True)
    assert dump_tables(path) == before


def test_unreviewed_dependency_blocks_reset(reset_store):
    settings, path = reset_store
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE protected_extra(id INTEGER REFERENCES supplier_orders(id))')
    before = dump_tables(path)
    with pytest.raises(RuntimeError, match='Protected table'):
        resetter.reset(path, execute=True)
    assert dump_tables(path) == before


def test_pause_required_and_hourly_due_skips_without_altering_settings(reset_store, monkeypatch):
    settings, path = reset_store
    before = dump_tables(path)
    monkeypatch.setattr(service, 'automatic_refresh_status', lambda _: pytest.fail('Paused scheduler must not start work'))
    assert service.automatic_refresh_due(settings) is False
    assert dump_tables(path) == before
    path.with_name('warehouse-automatic-orders.paused').unlink()
    with pytest.raises(RuntimeError, match='Pause hourly'):
        resetter.reset(path, execute=True)


def test_inflight_transfer_blocks_reset(reset_store):
    settings, path = reset_store
    with sqlite3.connect(path) as conn:
        conn.execute("INSERT INTO warehouse_checkbar_transfers VALUES(999,'fixture',1,'test','{}','pending',NULL,'now')")
    before = dump_tables(path)
    with pytest.raises(RuntimeError, match='operation active'):
        resetter.reset(path, execute=True)
    assert dump_tables(path) == before
