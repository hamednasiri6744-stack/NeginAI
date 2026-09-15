"""Recovery keeps native writes outside the application and preserves its audit."""
import copy
import json
from unittest.mock import Mock

import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_transfer_bridge import credit
from test_warehouse_transfer_lifecycle import posted
from app import warehouse_assistant_service as service
from app import warehouse_transfer_lifecycle as lifecycle
from app import warehouse_transfer_recovery as recovery
from app.warehouse_receipt_reflection import TRIGGER_HASHES

REAL_RECOVERY_READ = recovery._read_recovery_evidence


def test_automatic_recovery_refreshes_stale_stock_once_then_rechecks(recoverable, monkeypatch):
    b, doc, _, read, _, remote = recoverable
    with service.warehouse_connection(b.settings) as conn:
        days = conn.execute('SELECT period_days FROM warehouse_snapshots WHERE id=2').fetchone()[0]
        conn.execute("UPDATE warehouse_transfer_source_stock_state SET status='reflected'")
    def refresh(settings, username, period_days):
        assert settings == b.settings and username == 'test-user' and period_days == days
        with service.warehouse_connection(settings) as conn:
            conn.execute("UPDATE warehouse_transfer_source_stock_state SET status='review'")
    sync = Mock(side_effect=refresh)
    monkeypatch.setattr(service, 'sync_varanegar_snapshot', sync)
    assert recovery.recover_with_inventory_refresh(b.settings, 'test-user', doc)['returned_count'] == 1
    sync.assert_called_once(); remote.assert_called_once()
    assert read.call_count == 2  # Fresh ERP absence check again after inventory refresh.


def test_automatic_recovery_does_not_refresh_current_inventory(recoverable, monkeypatch):
    b, doc, _, _, _, _ = recoverable
    sync = Mock()
    monkeypatch.setattr(service, 'sync_varanegar_snapshot', sync)
    assert recovery.recover_with_inventory_refresh(b.settings, 'test-user', doc)['returned_count'] == 1
    sync.assert_not_called()


def test_return_api_runs_automatic_refresh_and_returns_lines(recoverable, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    b, doc, _, _, _, _ = recoverable
    with service.warehouse_connection(b.settings) as conn:
        conn.execute("UPDATE warehouse_transfer_source_stock_state SET status='reflected'")
    def refresh(*args, **kwargs):
        with service.warehouse_connection(b.settings) as conn:
            conn.execute("UPDATE warehouse_transfer_source_stock_state SET status='review'")
    sync = Mock(side_effect=refresh)
    monkeypatch.setattr(service, 'sync_varanegar_snapshot', sync)
    permissions = []
    def require(request, permission):
        permissions.append(permission)
        return 'test-user'
    monkeypatch.setattr(routes, '_require', require)
    monkeypatch.setattr(routes, '_is_admin', lambda *args: False)
    app = FastAPI(); app.state.settings = b.settings
    app.add_api_route('/documents/{document_id}/return-to-approved', routes.recover_transfer_document, methods=['POST'])
    with TestClient(app) as client:
        response = client.post(f'/documents/{doc}/return-to-approved')
    assert response.status_code == 200 and response.json()['returned_count'] == 1
    assert permissions == ['warehouse.order.draft', 'warehouse.receipt.transfer']
    sync.assert_called_once()


@pytest.mark.parametrize('failure', ['refresh_error', 'still_stale', 'credit_reappears', 'receipt'])
def test_automatic_recovery_keeps_document_on_failed_or_unsafe_refresh(recoverable, monkeypatch, failure):
    b, doc, detail, _, _, remote = recoverable
    with service.warehouse_connection(b.settings) as conn:
        conn.execute("UPDATE warehouse_transfer_source_stock_state SET status='reflected'")
    def refresh(*args, **kwargs):
        if failure == 'refresh_error': raise OSError('password sensitive-host')
        if failure == 'still_stale': return
        with service.warehouse_connection(b.settings) as conn:
            conn.execute("UPDATE warehouse_transfer_source_stock_state SET status='review'")
        if failure == 'credit_reappears': detail['headers'] = [dict(ID=501)]
        if failure == 'receipt': remote.return_value = dict(headers=[], receipts=[dict(ID=601)])
    sync = Mock(side_effect=refresh)
    monkeypatch.setattr(service, 'sync_varanegar_snapshot', sync)
    with pytest.raises(service.WarehouseAssistantError) as exc:
        recovery.recover_with_inventory_refresh(b.settings, 'test-user', doc)
    assert 'password' not in str(exc.value) and 'sensitive-host' not in str(exc.value)
    sync.assert_called_once()
    assert_not_returned(b, doc)


@pytest.mark.parametrize('reason', ['owner', 'payload', 'receipt'])
def test_automatic_recovery_does_not_refresh_unrelated_guard_errors(recoverable, monkeypatch, reason):
    b, doc, _, _, _, remote = recoverable
    if reason == 'payload':
        with service.warehouse_connection(b.settings) as conn:
            conn.execute('UPDATE warehouse_rebalance_requests SET quantity=quantity+1')
    if reason == 'receipt': remote.return_value = dict(headers=[], receipts=[dict(ID=601)])
    sync = Mock()
    monkeypatch.setattr(service, 'sync_varanegar_snapshot', sync)
    with pytest.raises(service.WarehouseAssistantError):
        recovery.recover_with_inventory_refresh(b.settings, 'other' if reason == 'owner' else 'test-user', doc)
    sync.assert_not_called()
    assert_not_returned(b, doc)


@pytest.fixture
def recoverable(posted, monkeypatch):
    b, doc, detail, read, original = posted
    detail.update(headers=[], items=[])
    evidence = dict(status='review', headers=[], items=[],
        contract=dict(valid=True, configuration=[dict(KeyValue='1')],
            effects=[dict(CardexType=1, EffectOnHandQty=True, EffectType=1)],
            trigger_hashes=TRIGGER_HASHES),
        effects=[dict(CardexType=1, EffectOnHandQty=True, EffectType=-1)],
        flags=[dict(KeyValue='1')])
    with service.warehouse_connection(b.settings) as conn:
        snap = dict(conn.execute('SELECT * FROM warehouse_snapshots WHERE id=1').fetchone())
        snap.update(id=2, source_kind='varanegar', content_sha256='absent-credit',
            imported_at=service._now(), period_end='1405/06/22')
        conn.execute(f'INSERT INTO warehouse_snapshots({",".join(snap)}) VALUES({",".join("?" for _ in snap)})', tuple(snap.values()))
        for item in conn.execute('SELECT * FROM warehouse_snapshot_items WHERE snapshot_id=1').fetchall():
            row = dict(item); row.pop('id'); row['snapshot_id'] = 2
            conn.execute(f'INSERT INTO warehouse_snapshot_items({",".join(row)}) VALUES({",".join("?" for _ in row)})', tuple(row.values()))
        conn.execute('INSERT INTO warehouse_transfer_source_stock_state VALUES(?,?,?,?,?)',
            (doc, 'review', 2, json.dumps(evidence), service._now()))
    remote = Mock(return_value=dict(headers=[], receipts=[]))
    monkeypatch.setattr(recovery, '_read_recovery_evidence', remote)
    return b, doc, detail, read, original, remote


def test_return_preserves_original_sent_and_request_and_archives_membership(recoverable):
    b, doc, _, read, original, remote = recoverable
    with service.warehouse_connection(b.settings) as conn:
        requests = [tuple(r) for r in conn.execute('SELECT * FROM warehouse_rebalance_requests')]
        lines = [tuple(r) for r in conn.execute('SELECT * FROM warehouse_transfer_document_lines')]
    result = recovery.return_to_approved(b.settings, 'test-user', doc)
    assert result['document_id'] == doc and result['returned_count'] == 1
    remote.assert_called_once(); read.assert_called_once()
    with service.warehouse_connection(b.settings) as conn:
        assert dict(conn.execute('SELECT * FROM warehouse_transfer_bridge_intents').fetchone()) == original
        assert [tuple(r) for r in conn.execute('SELECT * FROM warehouse_rebalance_requests')] == requests
        assert [tuple(r) for r in conn.execute('SELECT * FROM warehouse_transfer_document_line_history')] == lines
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_lines').fetchone()[0] == 0
        assert conn.execute('SELECT deleted_by FROM warehouse_transfer_document_deletions WHERE document_id=?', (doc,)).fetchone()[0] == 'test-user'
        audit = dict(conn.execute('SELECT * FROM warehouse_transfer_recovery_audit WHERE document_id=?', (doc,)).fetchone())
        proof = json.loads(audit['evidence_json'])
        assert audit['restored_by'] == 'test-user'
        assert proof['original_transfer_key'] == original['transfer_key']
        assert proof['snapshot_id'] == 2
        assert proof['remote_evidence'] == dict(headers=[], receipts=[])
        assert len(proof['original_fingerprint']) == 64 and len(proof['captured_fingerprint']) == 64
        assert proof['reason'] == 'native_credit_deleted_no_destination_receipt'
        assert 'inventory' not in proof and len(audit['evidence_json']) < 6000


def assert_not_returned(b, doc):
    with service.warehouse_connection(b.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_lines WHERE document_id=?', (doc,)).fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_deletions WHERE document_id=?', (doc,)).fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_line_history WHERE document_id=?', (doc,)).fetchone()[0] == 0


@pytest.mark.parametrize('state', ['confirmed', 'unconfirmed', 'changed', 'unknown'])
def test_live_not_missing_blocks_even_if_cached_missing(posted, state, monkeypatch):
    b, doc, detail, read, original = posted
    actual = copy.deepcopy(detail)
    detail.update(headers=[], items=[])
    lifecycle.sync(b.settings, 'test-user', doc)
    detail.update(actual)
    if state == 'unconfirmed': detail['headers'][0]['ConfirmedBy'] = None
    if state == 'changed': detail['items'][0]['TotalQty'] = 13
    if state == 'unknown': read.side_effect = OSError('secret')
    remote = Mock()
    monkeypatch.setattr(recovery, '_read_recovery_evidence', remote)
    with pytest.raises(service.WarehouseAssistantError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    assert read.call_count == 2
    remote.assert_not_called()
    assert_not_returned(b, doc)


@pytest.mark.parametrize('evidence', [dict(headers=[dict(ID=501)], receipts=[]),
    dict(headers=[], receipts=[dict(ID=601, ConfirmedBy=None, ConfirmDate=None)]),
    dict(headers=[], receipts=[dict(ID=601, ConfirmedBy=2, ConfirmDate='now')]),
    dict(headers=[]), dict(receipts=[]), None])
def test_fresh_credit_or_any_receipt_or_incomplete_evidence_blocks(recoverable, evidence):
    b, doc, _, _, _, remote = recoverable
    remote.return_value = evidence
    with pytest.raises(service.WarehouseAssistantError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    assert_not_returned(b, doc)


def test_remote_failure_never_exposes_secrets(recoverable):
    b, doc, _, _, _, remote = recoverable
    remote.side_effect = OSError('password sensitive-host')
    with pytest.raises(service.WarehouseAssistantError) as exc:
        recovery.return_to_approved(b.settings, 'test-user', doc)
    assert 'password' not in str(exc.value) and 'sensitive-host' not in str(exc.value)
    assert_not_returned(b, doc)


@pytest.mark.parametrize('mutation', [
    "UPDATE warehouse_snapshots SET source_kind='excel' WHERE id=2",
    "UPDATE warehouse_snapshots SET period_end='1404/06/22' WHERE id=2",
    "UPDATE warehouse_snapshots SET imported_at='2000-01-01T00:00:00+00:00' WHERE id=2",
    "UPDATE warehouse_transfer_source_stock_state SET snapshot_id=1",
    "UPDATE warehouse_transfer_source_stock_state SET status='reflected'",
    "DELETE FROM warehouse_transfer_source_stock_state",
    "DELETE FROM warehouse_snapshot_items WHERE snapshot_id=2 AND warehouse_code='tehran'",
    "UPDATE warehouse_rebalance_requests SET quantity=quantity+1",
])
def test_stale_or_incomplete_inventory_and_changed_payload_block(recoverable, mutation):
    b, doc, _, _, _, remote = recoverable
    with service.warehouse_connection(b.settings) as conn:
        conn.execute(mutation)
    with pytest.raises(service.WarehouseAssistantError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    remote.assert_not_called()
    assert_not_returned(b, doc)


@pytest.mark.parametrize('field,value', [('headers', [dict(ID=501)]), ('items', [dict(TotalQty=12)]),
    ('headers', None), ('contract', {'valid': True}), ('effects', []), ('flags', [dict(KeyValue='0')]),
    ('status', 'reflected')])
def test_absence_requires_full_native_stock_contract(recoverable, field, value):
    b, doc, _, _, _, remote = recoverable
    with service.warehouse_connection(b.settings) as conn:
        evidence = json.loads(conn.execute('SELECT evidence_json FROM warehouse_transfer_source_stock_state').fetchone()[0])
        evidence[field] = value
        conn.execute('UPDATE warehouse_transfer_source_stock_state SET evidence_json=?', (json.dumps(evidence),))
    with pytest.raises(service.WarehouseAssistantError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    remote.assert_not_called()
    assert_not_returned(b, doc)


@pytest.mark.parametrize('mutation', [
    "UPDATE warehouse_transfer_bridge_intents SET updated_at='2099-01-01'",
    "UPDATE warehouse_transfer_erp_state SET checked_at='2099-01-01'",
    "UPDATE warehouse_transfer_erp_state SET fingerprint='changed'",
    "UPDATE warehouse_transfer_erp_refresh SET generation=generation+1",
    "UPDATE warehouse_transfer_erp_refresh SET generation=generation+1,published_generation=published_generation+1",
    "UPDATE warehouse_transfer_source_stock_state SET updated_at='2099-01-01'",
    "UPDATE warehouse_snapshots SET content_sha256='concurrent' WHERE id=2",
    "UPDATE warehouse_snapshot_items SET stock=stock+1 WHERE snapshot_id=2 AND warehouse_code='tehran'",
    "UPDATE warehouse_transfer_document_lines SET brand='concurrent'",
    "UPDATE warehouse_rebalance_requests SET quantity=quantity+1",
    "INSERT INTO warehouse_rebalance_reflections SELECT request_id,2,'test-user','now','71','99' FROM warehouse_transfer_document_lines",
])
def test_concurrent_mutation_cannot_apply_old_evidence(recoverable, mutation):
    b, doc, _, _, _, remote = recoverable
    def concurrent(*args):
        with service.warehouse_connection(b.settings) as conn:
            conn.execute(mutation)
        return dict(headers=[], receipts=[])
    remote.side_effect = concurrent
    with pytest.raises(service.WarehouseAssistantError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    assert_not_returned(b, doc)


def test_existing_destination_reflection_blocks(recoverable):
    b, doc, _, _, _, remote = recoverable
    with service.warehouse_connection(b.settings) as conn:
        conn.execute("INSERT INTO warehouse_rebalance_reflections SELECT request_id,2,'test-user','now','71','99' FROM warehouse_transfer_document_lines")
    with pytest.raises(service.WarehouseAssistantError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    remote.assert_not_called()
    assert_not_returned(b, doc)


def test_owner_checked_before_any_remote_access(recoverable):
    b, doc, _, read, _, remote = recoverable
    with pytest.raises(service.WarehouseAssistantError):
        recovery.return_to_approved(b.settings, 'other-user', doc)
    read.assert_not_called(); remote.assert_not_called()
    assert_not_returned(b, doc)
    assert recovery.return_to_approved(b.settings, 'admin', doc, include_all=True)['returned_count'] == 1


def test_repeat_never_archives_or_returns_lines_twice(recoverable):
    b, doc, _, _, original, remote = recoverable
    recovery.return_to_approved(b.settings, 'test-user', doc)
    with pytest.raises(service.WarehouseAssistantError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    assert remote.call_count == 1
    with service.warehouse_connection(b.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_line_history').fetchone()[0] == 1
        assert dict(conn.execute('SELECT * FROM warehouse_transfer_bridge_intents').fetchone()) == original


def test_history_conflict_rolls_back_no_partial_detach(recoverable):
    import sqlite3
    b, doc, _, _, original, _ = recoverable
    with service.warehouse_connection(b.settings) as conn:
        conn.execute('INSERT INTO warehouse_transfer_document_line_history SELECT * FROM warehouse_transfer_document_lines')
    with pytest.raises(sqlite3.IntegrityError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    with service.warehouse_connection(b.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_lines').fetchone()[0] == 1
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_deletions').fetchone()[0] == 0
        assert dict(conn.execute('SELECT * FROM warehouse_transfer_bridge_intents').fetchone()) == original
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_recovery_audit').fetchone()[0] == 0


def test_recovery_keeps_single_source_reservation_and_destination_inbound(recoverable):
    from app.warehouse_rebalancing import reservations
    from app.warehouse_transfer_reflection import capture, review_codes
    b, doc, _, _, _, _ = recoverable
    with service.warehouse_connection(b.settings) as conn:
        assert reservations(conn, 'tehran')[1] == {'00123': 12}
        assert reservations(conn, 'karaj')[0] == {'00123': 12}
        inventory = [tuple(row) for row in conn.execute('SELECT * FROM warehouse_snapshot_items ORDER BY id')]
        assert len(capture(conn)) == 1
        assert '00123' in review_codes(conn, 'tehran')
    recovery.return_to_approved(b.settings, 'test-user', doc)
    with service.warehouse_connection(b.settings) as conn:
        assert reservations(conn, 'tehran')[1] == {'00123': 12}
        assert reservations(conn, 'karaj')[0] == {'00123': 12}
        assert [tuple(row) for row in conn.execute('SELECT * FROM warehouse_snapshot_items ORDER BY id')] == inventory
        assert capture(conn) == []
        assert review_codes(conn, 'tehran') == set()
        assert review_codes(conn, 'karaj') == set()


def test_audit_conflict_rolls_back_history_and_tombstone_together(recoverable):
    import sqlite3
    b, doc, _, _, original, _ = recoverable
    with service.warehouse_connection(b.settings) as conn:
        recovery.init_schema(conn)
        conn.execute('INSERT INTO warehouse_transfer_recovery_audit VALUES(?,?,?,?)', (doc, 'prior', 'prior', '{}'))
    with pytest.raises(sqlite3.IntegrityError):
        recovery.return_to_approved(b.settings, 'test-user', doc)
    assert_not_returned(b, doc)
    with service.warehouse_connection(b.settings) as conn:
        assert conn.execute('SELECT restored_by FROM warehouse_transfer_recovery_audit').fetchone()[0] == 'prior'
        assert dict(conn.execute('SELECT * FROM warehouse_transfer_bridge_intents').fetchone()) == original


@pytest.mark.parametrize('link', ['DocRef', 'TICAHdrRef', 'tuple', 'unrelated', 'credit-id', 'credit-uuid'])
def test_remote_query_selects_native_links_in_one_readonly_snapshot(posted, monkeypatch, link):
    """Execute the real SELECT expressions over an isolated header relation."""
    import sqlite3
    from contextlib import contextmanager
    from pytds.extensions import ISOLATION_LEVEL_SNAPSHOT
    from app import database
    b, doc, _, _, _ = posted
    with service.warehouse_connection(b.settings) as conn:
        captured = lifecycle._capture(conn, 'test-user', doc, False)[0]
    sql = sqlite3.connect(':memory:')
    sql.execute("ATTACH DATABASE ':memory:' AS inv")
    fields = ['ID', 'UniqueId', 'VocherNo', 'AccYear', 'StockDCRef', 'TStockDCRef', 'DocRef', 'TICAHdrRef',
              'TVchTypeRef', 'TVocherTypeCode', 'TVocherNo', 'ConfirmedBy', 'ConfirmDate', 'VocherTypeCode']
    sql.execute('CREATE TABLE inv.tblVocherHdr (' + ','.join(fields) + ')')
    row = dict(ID=601, UniqueId='receipt', VocherTypeCode=15, ConfirmedBy=None, ConfirmDate=None)
    if link in ('DocRef', 'TICAHdrRef'): row[link] = 501
    if link == 'tuple': row.update(AccYear=1405, StockDCRef=1, TStockDCRef=2, TVocherTypeCode=65, TVocherNo=71)
    if link == 'credit-id': row.update(ID=501, VocherTypeCode=65)
    if link == 'credit-uuid': row.update(UniqueId=captured['transfer_key'], VocherTypeCode=65)
    sql.execute('INSERT INTO inv.tblVocherHdr (' + ','.join(row) + ') VALUES (' + ','.join('?' for _ in row) + ')', tuple(row.values()))
    queries = []
    class Cursor:
        def execute(self, query):
            assert source.isolation_level == ISOLATION_LEVEL_SNAPSHOT
            assert query.lstrip().startswith('SELECT ')
            assert 'NOLOCK' not in query
            queries.append(query)
            self.inner = sql.execute(query)
            self.description = self.inner.description
        def fetchall(self): return self.inner.fetchall()
    class Source:
        isolation_level = None
        def cursor(self): return Cursor()
    source = Source()
    connections = []
    @contextmanager
    def report_connection(settings):
        connections.append(settings)
        yield source
    for field in ('server', 'database', 'username', 'password'):
        setattr(b.settings, 'sql_' + field, 'isolated-report')
    monkeypatch.setattr(database, 'sql_connection', report_connection)
    try:
        result = REAL_RECOVERY_READ(b.settings, captured)
    finally:
        sql.close()
    assert len(queries) == 2 and connections == [b.settings]
    assert bool(result['headers']) == link.startswith('credit-')
    assert bool(result['receipts']) == (link in ('DocRef', 'TICAHdrRef', 'tuple'))
