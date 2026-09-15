"""Current ERP lifecycle evidence uses isolated SQLite and a read-only seam."""
import copy
import json
from unittest.mock import Mock

import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_transfer_bridge import credit, request, sent
from app import warehouse_transfer_bridge as bridge
from app import warehouse_transfer_lifecycle as lifecycle
from app import warehouse_assistant_service as service

REAL_READ_MANY = lifecycle._read_many


@pytest.fixture
def posted(credit, monkeypatch):
    b, doc, ident, remote = credit
    req = request(credit)
    remote.return_value = sent()
    bridge.submit(b.settings, 'test-user', doc, req)
    with service.warehouse_connection(b.settings) as conn:
        lifecycle.init_schema(conn)
        row = dict(conn.execute('SELECT * FROM warehouse_transfer_bridge_intents').fetchone())
    payload = json.loads(row['payload_json'])
    detail = dict(headers=[dict(ID=501, UniqueId=row['transfer_key'], VocherNo=71,
        StockDCRef=2, TStockDCRef=1, AccYear=1405, VocherTypeCode=65,
        HealthCodeType=1047, HealthCode=1, VocherDate=payload['voucher_date'],
        ConfirmedBy=2, ConfirmDate='2026-09-13T10:00:00')],
        items=[dict(GoodsCode='00123', UnitRef=1, BasicUnitRef=1, UnitCapacity=1, UnitQty=12, TotalQty=12)])
    read = Mock(return_value={doc: detail})
    monkeypatch.setattr(lifecycle, '_read_many', read)
    return b, doc, detail, read, row


def test_confirmed_cache_and_force_read_preserve_sent_intent(posted):
    b, doc, detail, read, original = posted
    result = lifecycle.sync(b.settings, 'test-user', doc)[doc]
    assert result['status'] == 'confirmed' and result['voucher_no'] == 71
    assert result['confirmed_at'] == '2026-09-13T10:00:00'
    assert lifecycle.sync(b.settings, 'test-user', doc)[doc] == result
    assert read.call_count == 1
    lifecycle.sync(b.settings, 'test-user', doc, force=True)
    assert read.call_count == 2
    with service.warehouse_connection(b.settings) as conn:
        assert dict(conn.execute('SELECT * FROM warehouse_transfer_bridge_intents').fetchone()) == original
        assert lifecycle.get_cached(conn, doc)['status'] == 'confirmed'


@pytest.mark.parametrize('field,value', [('ConfirmedBy', None), ('ConfirmDate', None), ('ConfirmDate', '')])
def test_correct_document_without_confirmation_is_unconfirmed(posted, field, value):
    b, doc, detail, _, _ = posted
    detail['headers'][0][field] = value
    assert lifecycle.sync(b.settings, 'test-user', doc)[doc]['status'] == 'unconfirmed'


def test_missing_document_not_recreated_or_marked_pending(posted):
    b, doc, detail, _, _ = posted
    detail['headers'] = []; detail['items'] = []
    state = lifecycle.sync(b.settings, 'test-user', doc)[doc]
    assert state['status'] == 'missing' and state['voucher_no'] == 71
    with service.warehouse_connection(b.settings) as conn:
        assert conn.execute('SELECT status FROM warehouse_transfer_bridge_intents').fetchone()[0] == 'sent'


@pytest.mark.parametrize('section,field,value', [
    ('headers', 'StockDCRef', 9), ('headers', 'TStockDCRef', 9),
    ('headers', 'VocherNo', 72), ('headers', 'AccYear', 1404),
    ('headers', 'VocherTypeCode', 15), ('headers', 'HealthCode', 2),
    ('headers', 'UniqueId', '00000000-0000-0000-0000-000000000001'),
    ('headers', 'VocherDate', '1405/01/01'),
    ('items', 'TotalQty', 13), ('items', 'UnitRef', 2),
    ('items', 'UnitCapacity', 12), ('items', 'GoodsCode', 'another'),
])
def test_identity_and_line_changes_require_review(posted, section, field, value):
    b, doc, detail, _, _ = posted
    detail[section][0][field] = value
    assert lifecycle.sync(b.settings, 'test-user', doc)[doc]['status'] == 'changed'


def test_duplicate_identity_is_changed(posted):
    b, doc, detail, _, _ = posted
    detail['headers'].append(copy.deepcopy(detail['headers'][0]))
    assert lifecycle.sync(b.settings, 'test-user', doc)[doc]['status'] == 'changed'


def test_offline_overrides_previous_confirmation_without_secret_leak(posted):
    b, doc, _, read, _ = posted
    lifecycle.sync(b.settings, 'test-user', doc)
    read.side_effect = OSError('secret password and server')
    result = lifecycle.sync(b.settings, 'test-user', doc, force=True)[doc]
    assert result['status'] == 'unknown' and result['voucher_no'] == 71
    with service.warehouse_connection(b.settings) as conn:
        row = dict(conn.execute('SELECT * FROM warehouse_transfer_erp_state').fetchone())
        assert 'secret' not in str(row)


def test_access_filters_single_and_bulk_read(posted):
    b, doc, _, read, _ = posted
    with pytest.raises(service.WarehouseAssistantError):
        lifecycle.sync(b.settings, 'other-user', doc)
    assert lifecycle.sync(b.settings, 'other-user') == {}
    read.assert_not_called()
    assert lifecycle.sync(b.settings, 'admin', include_all=True)[doc]['status'] == 'confirmed'


def test_concurrent_changed_payload_never_saves_old_evidence(posted):
    b, doc, detail, read, _ = posted
    def concurrent(*args):
        with service.warehouse_connection(b.settings) as conn:
            conn.execute("UPDATE warehouse_transfer_bridge_intents SET payload_json='{}' WHERE document_id=?", (doc,))
        return {doc: detail}
    read.side_effect = concurrent
    assert lifecycle.sync(b.settings, 'test-user', doc) == {}
    with service.warehouse_connection(b.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_erp_state').fetchone()[0] == 0


@pytest.mark.parametrize('change', ['status', 'deletion'])
def test_concurrent_local_deletion_or_status_change_never_attaches_read(posted, change):
    b, doc, detail, read, _ = posted
    def concurrent(*args):
        with service.warehouse_connection(b.settings) as conn:
            if change == 'status':
                conn.execute("UPDATE warehouse_transfer_bridge_intents SET status='rejected' WHERE document_id=?", (doc,))
            else:
                conn.execute('INSERT INTO warehouse_transfer_document_deletions VALUES(?,?,?)',
                             (doc, 'test-user', service._now()))
        return {doc: detail}
    read.side_effect = concurrent
    assert lifecycle.sync(b.settings, 'test-user', doc) == {}


def test_expired_cache_refreshes_and_stale_fingerprint_not_returned(posted):
    b, doc, detail, read, _ = posted
    lifecycle.sync(b.settings, 'test-user', doc)
    with service.warehouse_connection(b.settings) as conn:
        conn.execute("UPDATE warehouse_transfer_erp_state SET checked_at='2000-01-01T00:00:00+00:00'")
    detail['headers'][0]['ConfirmedBy'] = None
    assert lifecycle.sync(b.settings, 'test-user', doc)[doc]['status'] == 'unconfirmed'
    assert read.call_count == 2
    with service.warehouse_connection(b.settings) as conn:
        conn.execute("UPDATE warehouse_transfer_bridge_intents SET result_json='{}'")
        assert lifecycle.get_cached(conn, doc) is None


def test_invalid_read_evidence_is_unknown(posted):
    b, doc, _, read, _ = posted
    read.return_value = {doc: {'headers': [{}], 'items': []}}
    assert lifecycle.sync(b.settings, 'test-user', doc)[doc]['status'] == 'unknown'


def test_unconfigured_report_connection_never_attempts_network(posted, monkeypatch):
    b, doc, _, _, _ = posted
    from app import database
    network = Mock(side_effect=AssertionError('network must not run'))
    monkeypatch.setattr(lifecycle, '_read_many', REAL_READ_MANY)
    monkeypatch.setattr(database, 'sql_connection', network)
    b.settings.sql_server = ''
    assert lifecycle.sync(b.settings, 'test-user', doc)[doc]['status'] == 'unknown'
    network.assert_not_called()


def test_read_boundary_uses_one_report_snapshot_with_readonly_queries(posted, monkeypatch):
    from contextlib import contextmanager
    from app import database
    from pytds.extensions import ISOLATION_LEVEL_SNAPSHOT
    b, doc, detail, _, _ = posted
    queries = []
    class Cursor:
        def execute(self, sql):
            queries.append(sql)
            assert source.isolation_level == ISOLATION_LEVEL_SNAPSHOT
            assert sql.lstrip().startswith('SELECT ')
            rows = detail['headers'] if 'FROM inv.tblVocherHdr' in sql else detail['items']
            self.description = [(name,) for name in rows[0]]
            self.rows = [tuple(row.values()) for row in rows]
        def fetchall(self):
            return self.rows
    class Source:
        isolation_level = None
        def cursor(self):
            return Cursor()
    source = Source()
    @contextmanager
    def report_connection(settings):
        assert settings is b.settings
        yield source
    for field in ('server', 'database', 'username', 'password'):
        setattr(b.settings, 'sql_' + field, 'isolated-report')
    monkeypatch.setattr(database, 'sql_connection', report_connection)
    monkeypatch.setattr(lifecycle, '_read_many', REAL_READ_MANY)
    assert lifecycle.sync(b.settings, 'test-user', doc)[doc]['status'] == 'confirmed'
    assert len(queries) == 2
    assert 'H.ID=501' in queries[0] and 'I.HdrRef IN (501)' in queries[1]


def test_newer_nested_refresh_wins_even_if_older_snapshot_finishes_last(posted):
    b, doc, detail, read, _ = posted
    later = {}
    def old_snapshot(*args):
        read.side_effect = None
        read.return_value = {doc:dict(headers=[], items=[])}
        later.update(lifecycle.sync(b.settings, 'test-user', doc, force=True))
        return {doc:detail}
    read.side_effect = old_snapshot
    older_result = lifecycle.sync(b.settings, 'test-user', doc, force=True)
    assert later[doc]['status'] == 'missing'
    assert older_result == later
    with service.warehouse_connection(b.settings) as conn:
        assert lifecycle.get_cached(conn, doc) == later[doc]
        assert json.loads(conn.execute('SELECT evidence_json FROM warehouse_transfer_erp_state').fetchone()[0]) == dict(headers=[], items=[])


def test_older_refresh_returns_unknown_while_newer_read_is_pending(posted):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, Lock
    b, doc, detail, read, _ = posted
    lifecycle.sync(b.settings, 'test-user', doc)  # Previous successful cache.
    old_started, new_started, finish_old, finish_new = (Event() for _ in range(4))
    lock = Lock(); starts = []
    def delayed_read(*args):
        with lock:
            starts.append(1)
            number = len(starts)
        if number == 1:
            old_started.set()
            assert finish_old.wait(10)
            return {doc: detail}
        new_started.set()
        assert finish_new.wait(10)
        return {doc:dict(headers=[], items=[])}
    read.side_effect = delayed_read
    with ThreadPoolExecutor(max_workers=2) as pool:
        try:
            older = pool.submit(lifecycle.sync, b.settings, 'test-user', doc, force=True)
            assert old_started.wait(10)
            newer = pool.submit(lifecycle.sync, b.settings, 'test-user', doc, force=True)
            assert new_started.wait(10)
            finish_old.set()
            assert older.result(timeout=10)[doc]['status'] == 'unknown'
            with service.warehouse_connection(b.settings) as conn:
                assert lifecycle.get_cached(conn, doc) is None
            finish_new.set()
            assert newer.result(timeout=10)[doc]['status'] == 'missing'
        finally:
            finish_old.set(); finish_new.set()
    with service.warehouse_connection(b.settings) as conn:
        assert lifecycle.get_cached(conn, doc)['status'] == 'missing'
