"""Document valuation uses the source snapshot, not current or consumer prices."""
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_balance_proposals import preview, accept
from app import warehouse_rebalancing as ledger
from app import warehouse_assistant_service as service
import pytest
from app import warehouse_transfer_documents as documents
from app.business_time import TEHRAN_TIMEZONE
from datetime import datetime


def test_confirmation_is_staged_and_delete_releases_only_its_reservation(balance):
    accept(balance,preview(balance),1)
    rows=ledger.list_requests(balance.settings,'test-user')
    assert rows[0]['issued_document_id'] is None
    from app.warehouse_transfer_documents import delete_pending
    delete_pending(balance.settings,'test-user',rows[0]['id'])
    assert ledger.list_requests(balance.settings,'test-user')==[]
    with service.warehouse_connection(balance.settings) as conn:
        assert ledger.reservations(conn,'tehran')[1]=={}
        assert ledger.reservations(conn,'karaj')[0]=={}
        assert conn.execute('SELECT COUNT(*) FROM warehouse_rebalance_requests').fetchone()[0]==1
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_documents').fetchone()[0]==0
    delete_pending(balance.settings,'test-user',rows[0]['id'])
    balance.transport.assert_not_called()


def test_document_line_price_comes_from_original_source_snapshot(balance):
    balance.change("UPDATE warehouse_snapshot_items SET buy_price=70 WHERE warehouse_code='tehran'")
    balance.change("UPDATE warehouse_snapshot_items SET buy_price=900 WHERE warehouse_code='karaj'")
    accept(balance,preview(balance),1)
    with service.warehouse_connection(balance.settings) as conn:
        snapshot=dict(conn.execute('SELECT * FROM warehouse_snapshots WHERE id=1').fetchone())
        snapshot.update(id=2,content_sha256='document-price-new-snapshot')
        conn.execute(f'INSERT INTO warehouse_snapshots({",".join(snapshot)}) VALUES({",".join("?" for _ in snapshot)})',tuple(snapshot.values()))
        for original in conn.execute('SELECT * FROM warehouse_snapshot_items WHERE snapshot_id=1').fetchall():
            item=dict(original);item.pop('id',None);item.update(snapshot_id=2,buy_price=999)
            conn.execute(f'INSERT INTO warehouse_snapshot_items({",".join(item)}) VALUES({",".join("?" for _ in item)})',tuple(item.values()))
    rows=ledger.list_requests(balance.settings,'test-user')
    assert len(rows)==1 and rows[0]['estimated_unit_price']==70
    assert rows[0]['quantity']==12 and rows[0]['created_at']
    assert ledger.list_requests(balance.settings,'another-user')==[]
    assert len(ledger.list_requests(balance.settings,'another-user',include_all=True))==1
    balance.transport.assert_not_called()


def test_missing_source_snapshot_price_stays_unknown(balance):
    accept(balance,preview(balance),1)
    balance.change("DELETE FROM warehouse_snapshot_items WHERE warehouse_code='tehran'")
    row=ledger.list_requests(balance.settings,'test-user')[0]
    assert row['estimated_unit_price'] is None


def test_explicit_issue_combines_batches_splits_routes_and_uses_today(balance,monkeypatch):
    from test_warehouse_balance_proposals import add_gilan
    add_gilan(balance)
    balance.change("UPDATE warehouse_snapshot_items SET stock=240,buy_price=70 WHERE warehouse_code='tehran'")
    accept(balance,preview(balance),1,key='first')
    accept(balance,preview(balance),1,key='second')
    balance.change("UPDATE warehouse_snapshot_items SET stock=60 WHERE warehouse_code='karaj'")
    accept(balance,preview(balance,'tehran','gilan'),4,key='third')
    balance.change("UPDATE warehouse_rebalance_batches SET created_at='2025-01-01T00:00:00+00:00'")
    rows=ledger.list_requests(balance.settings,'test-user');ids=[r['id'] for r in rows]
    assert all(r['issued_document_id'] is None for r in rows)
    with service.warehouse_connection(balance.settings) as conn:
        before={w:ledger.reservations(conn,w) for w in ('tehran','karaj','gilan')}
    monkeypatch.setattr(documents,'tehran_now',lambda:datetime(2026,9,13,0,5,tzinfo=TEHRAN_TIMEZONE))
    result=documents.create_documents(balance.settings,'test-user',ids,request_id='issue')
    assert len(result['documents'])==2
    assert {(d['source'],d['destination'],d['item_count']) for d in result['documents']}=={('tehran','karaj',2),('tehran','gilan',1)}
    assert all(d['business_date']=='1405/06/22' for d in result['documents'])
    assert documents.create_documents(balance.settings,'test-user',list(reversed(ids)),request_id='issue')==result
    with pytest.raises(service.WarehouseAssistantError):
        documents.create_documents(balance.settings,'test-user',ids[:1],request_id='issue')
    with pytest.raises(service.WarehouseAssistantError):
        documents.create_documents(balance.settings,'test-user',ids,request_id='duplicate')
    with pytest.raises(service.WarehouseAssistantError):
        documents.delete_pending(balance.settings,'test-user',ids[0])
    # Issuance freezes the displayed pricing/brand even if snapshots get pruned.
    balance.change('DELETE FROM warehouse_snapshot_items')
    rows=ledger.list_requests(balance.settings,'test-user')
    assert all(r['estimated_unit_price']==70 and r['issued_document_date']=='1405/06/22' for r in rows)
    assert sum(r['quantity']*r['estimated_unit_price'] for r in rows)==5040
    with service.warehouse_connection(balance.settings) as conn:
        assert before=={w:ledger.reservations(conn,w) for w in before}
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_documents').fetchone()[0]==2
    balance.transport.assert_not_called()


@pytest.mark.parametrize('invalid',[[],[True],[1.5],[0],[1,1],[999]])
def test_invalid_issue_is_atomic(balance,invalid):
    accept(balance,preview(balance),1)
    with pytest.raises(service.WarehouseAssistantError):
        documents.create_documents(balance.settings,'test-user',invalid,request_id='invalid')
    with service.warehouse_connection(balance.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_documents').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_issues').fetchone()[0]==0


def test_cross_user_and_deleted_selection_rejected_without_partial_issue(balance):
    accept(balance,preview(balance),1,key='first')
    accept(balance,preview(balance),1,key='second')
    ids=[r['id'] for r in ledger.list_requests(balance.settings,'test-user')]
    with pytest.raises(service.WarehouseAssistantError):documents.delete_pending(balance.settings,'other',ids[0])
    with pytest.raises(service.WarehouseAssistantError):documents.create_documents(balance.settings,'other',ids,request_id='forbidden')
    documents.delete_pending(balance.settings,'test-user',ids[0])
    with pytest.raises(service.WarehouseAssistantError):documents.create_documents(balance.settings,'test-user',ids,request_id='stale')
    with pytest.raises(service.WarehouseAssistantError):
        ledger.reflect_in_stock(balance.settings,'test-user',ids[0],snapshot_id=2,source_document='S',destination_document='D',confirmed=True)
    with service.warehouse_connection(balance.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_lines').fetchone()[0]==0
        assert ledger.reservations(conn,'karaj')[0]=={'00123':12}
    remaining=ledger.list_requests(balance.settings,'test-user')
    assert len(remaining)==1 and remaining[0]['issued_document_id'] is None


def test_reflected_line_cannot_be_deleted_or_issued(balance):
    accept(balance,preview(balance),1)
    row=ledger.list_requests(balance.settings,'test-user')[0]
    with service.warehouse_connection(balance.settings) as conn:
        conn.execute('INSERT INTO warehouse_rebalance_reflections VALUES(?,?,?,?,?,?)',(row['id'],1,'test-user','now','S','D'))
    with pytest.raises(service.WarehouseAssistantError):documents.delete_pending(balance.settings,'test-user',row['id'])
    with pytest.raises(service.WarehouseAssistantError):documents.create_documents(balance.settings,'test-user',[row['id']],request_id='received')


def test_http_mutations_require_permission_and_strict_ids(balance):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.routes import warehouse_assistant as routes
    accept(balance,preview(balance),1)
    ident=ledger.list_requests(balance.settings,'test-user')[0]['id']
    app=FastAPI();app.state.settings=balance.settings;app.include_router(routes.router)
    root='/warehouse-assistant/api/interwarehouse'
    with TestClient(app) as client:
        assert client.post(root+'/documents',json=dict(request_ids=[ident],request_id='http')).status_code==401
        assert client.delete(root+f'/requests/{ident}').status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'test-user'
        with patch.object(routes,'_require',return_value='test-user'),patch.object(routes,'_is_admin',return_value=False):
            assert client.post(root+'/documents',json=dict(request_ids=[True],request_id='bad')).status_code==422
            assert client.post(root+'/documents',json=dict(request_ids=[ident],request_id='http')).status_code==200
            assert client.delete(root+f'/requests/{ident}').status_code>=400


def test_simultaneous_issue_and_delete_never_leave_deleted_document_line(balance):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    accept(balance,preview(balance),1)
    ident=ledger.list_requests(balance.settings,'test-user')[0]['id']
    barrier=Barrier(2)
    def run(action):
        barrier.wait(timeout=5)
        try:
            action()
            return True
        except service.WarehouseAssistantError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        issuing=pool.submit(run,lambda:documents.create_documents(balance.settings,'test-user',[ident],request_id='race'))
        deleting=pool.submit(run,lambda:documents.delete_pending(balance.settings,'test-user',ident))
        assert sorted([issuing.result(),deleting.result()])==[False,True]
    with service.warehouse_connection(balance.settings) as conn:
        issued=conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_lines').fetchone()[0]
        deleted=conn.execute('SELECT COUNT(*) FROM warehouse_rebalance_deletions').fetchone()[0]
        assert issued+deleted==1
        assert ledger.reservations(conn,'karaj')[0]==({'00123':12} if issued else {})


def test_delete_document_returns_lines_to_confirmed_without_releasing_stock(balance):
    accept(balance,preview(balance),1)
    ident=ledger.list_requests(balance.settings,'test-user')[0]['id']
    issued=documents.create_documents(balance.settings,'test-user',[ident],request_id='old')
    doc_id=issued['documents'][0]['id']
    documents.delete_document(balance.settings,'test-user',doc_id)
    row=ledger.list_requests(balance.settings,'test-user')[0]
    assert row['issued_document_id'] is None
    with service.warehouse_connection(balance.settings) as conn:
        assert ledger.reservations(conn,'karaj')[0]=={'00123':12}
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_line_history').fetchone()[0]==1
    new=documents.create_documents(balance.settings,'test-user',[ident],request_id='new')
    assert new['documents'][0]['id']!=doc_id
    documents.delete_document(balance.settings,'test-user',doc_id)
    assert ledger.list_requests(balance.settings,'test-user')[0]['issued_document_id']==new['documents'][0]['id']


def test_revoke_confirmation_releases_reservation_and_allows_fresh_proposal(balance):
    accept(balance,preview(balance),1)
    ident=ledger.list_requests(balance.settings,'test-user')[0]['id']
    documents.revoke_pending(balance.settings,'test-user',ident)
    assert ledger.list_requests(balance.settings,'test-user')==[]
    with service.warehouse_connection(balance.settings) as conn:
        assert ledger.reservations(conn,'tehran')[1]=={}
        assert ledger.reservations(conn,'karaj')[0]=={}
    assert preview(balance)['lines']
    with pytest.raises(service.WarehouseAssistantError):
        documents.create_documents(balance.settings,'test-user',[ident],request_id='revoked')


def test_document_delete_and_revoke_enforce_ownership_and_erp_guards(balance):
    accept(balance,preview(balance),1)
    ident=ledger.list_requests(balance.settings,'test-user')[0]['id']
    with pytest.raises(service.WarehouseAssistantError):
        documents.revoke_pending(balance.settings,'other',ident)
    doc=documents.create_documents(balance.settings,'test-user',[ident],request_id='guard')['documents'][0]['id']
    with pytest.raises(service.WarehouseAssistantError):
        documents.delete_document(balance.settings,'other',doc)
    with pytest.raises(service.WarehouseAssistantError):
        documents.revoke_pending(balance.settings,'test-user',ident)
    with service.warehouse_connection(balance.settings) as conn:
        conn.execute("INSERT INTO warehouse_transfer_bridge_intents VALUES(?,'key','{}','test-user','now','pending',NULL,'now')",(doc,))
    with pytest.raises(service.WarehouseAssistantError,match='ورانگر'):
        documents.delete_document(balance.settings,'test-user',doc)
    with service.warehouse_connection(balance.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_deletions').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_lines').fetchone()[0]==1
        conn.execute('DELETE FROM warehouse_transfer_bridge_intents')
        conn.execute('INSERT INTO warehouse_rebalance_reflections VALUES(?,?,?,?,?,?)',(ident,1,'test-user','now','S','D'))
    with pytest.raises(service.WarehouseAssistantError,match='منعکس'):
        documents.delete_document(balance.settings,'test-user',doc)


def test_document_delete_and_revoke_http_authentication(balance):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=balance.settings;app.include_router(routes.router)
    root='/warehouse-assistant/api/interwarehouse'
    with TestClient(app) as client:
        assert client.delete(root+'/documents/1').status_code==401
        assert client.post(root+'/requests/1/revoke').status_code==401


def test_revoke_retry_is_idempotent_and_cannot_reflect_or_delete(balance):
    accept(balance,preview(balance),1)
    ident=ledger.list_requests(balance.settings,'test-user')[0]['id']
    first=documents.revoke_pending(balance.settings,'test-user',ident)
    assert documents.revoke_pending(balance.settings,'test-user',ident)==first
    with pytest.raises(service.WarehouseAssistantError):documents.delete_pending(balance.settings,'test-user',ident)
    with pytest.raises(service.WarehouseAssistantError):
        ledger.reflect_in_stock(balance.settings,'test-user',ident,snapshot_id=2,source_document='S',destination_document='D',confirmed=True)
