import json
import pytest
from test_warehouse_fulfillment import case
from test_warehouse_order_receipts import orders, document, prepared, details
from test_checkbar_confirmation import edit
from app import warehouse_assistant_service as service
from app import warehouse_checkbar as cb, warehouse_receipt_bridge as bridge
from app import warehouse_receipt_lifecycle as lifecycle
from app import warehouse_receipt_reflection as reflection


def sent(case):
    doc=document(case)
    bridge.submit(case.settings,'worker',doc['id'],prepared(case,doc))
    return doc


@pytest.mark.parametrize('presence',['exists','review','unknown'])
def test_receipt_locks_both_edit_and_delete_and_displays_number(orders,monkeypatch,presence):
    doc=sent(orders)
    monkeypatch.setattr(lifecycle,'probe',lambda *_:dict(state=presence,number=71,confirmed=True))
    state=bridge.transfer_status(orders.settings,doc['id'])
    assert state['receipt']['locked'] and state['receipt']['number']==71
    with pytest.raises(service.WarehouseAssistantError):
        cb.edit_context(orders.settings,doc['id'])
    with pytest.raises(service.WarehouseAssistantError):
        cb.delete_document(orders.settings,'worker',doc['id'],dict(expected_revision=0,request_id='delete'))
    assert details(orders,2)['remaining_qty']==80


def test_timeout_never_unlocks_or_discards_transfer(orders,monkeypatch):
    doc=sent(orders)
    def timeout(*_):raise TimeoutError()
    monkeypatch.setattr(lifecycle,'probe',timeout)
    result=bridge.transfer_status(orders.settings,doc['id'])
    assert result['status']=='sent' and result['receipt']['state']=='unknown'
    assert not result['transfer_history']


def test_deleted_receipt_retains_counts_history_and_can_be_deleted_locally(orders,monkeypatch):
    doc=sent(orders)
    monkeypatch.setattr(lifecycle,'probe',lambda *_:dict(state='deleted',number=71))
    result=bridge.transfer_status(orders.settings,doc['id'])
    assert result['status']=='not_sent' and result['receipt']['state']=='deleted'
    assert len(result['transfer_history'])==1
    assert details(orders,2)['remaining_qty']==80  # Receipt deletion is not unloading reversal.
    current=cb.get_document(orders.settings,doc['id'])
    assert current['receipt_confirmed']
    cb.delete_document(orders.settings,'worker',doc['id'],dict(expected_revision=0,request_id='delete'))
    assert details(orders,1)['remaining_qty']==100 and details(orders,2)['remaining_qty']==100
    with service.warehouse_connection(orders.settings) as conn:
        assert len(lifecycle.history(conn,doc['id']))==1
        captured=reflection.capture(conn)
        assert captured[0]['deleted_generation']


def test_deleted_receipt_can_edit_and_retransfer_with_new_key_without_double_receiving(orders,monkeypatch):
    doc=sent(orders)
    monkeypatch.setattr(lifecycle,'probe',lambda *_:dict(state='deleted',number=71))
    bridge.transfer_status(orders.settings,doc['id'])
    updated=edit(orders,cb.get_document(orders.settings,doc['id']),60)
    assert updated['id']==doc['id'] and updated['number']==doc['number'] and updated['revision']==1
    assert details(orders,1)['remaining_qty']==40 and details(orders,2)['remaining_qty']==100
    old_remote=orders.remote
    def replacement(settings,key,user,encoded,commit):
        result=old_remote(settings,key,user,encoded,commit)
        return dict(result,ReplacementSupported=1)
    monkeypatch.setattr(bridge,'_remote',replacement)
    request=bridge.ReceiptRequest(expected_revision=1,voucher_date='1405/06/15',reference_no='2222')
    preview=bridge.preview(orders.settings,'worker',doc['id'],request)
    assert preview['status']=='ready' and len(preview['payload']['replaces_receipts'])==1
    request=request.model_copy(update=dict(preview_token=preview['preview_token'],validation_token=preview['result']['ValidationToken']))
    bridge.submit(orders.settings,'worker',doc['id'],request)
    bridge.submit(orders.settings,'worker',doc['id'],request)
    assert len(old_remote.commits)==2
    assert details(orders,1)['remaining_qty']==40 and details(orders,2)['remaining_qty']==100


def test_reappearing_old_receipt_blocks_edit_and_old_bridge_blocks_replacement(orders,monkeypatch):
    doc=sent(orders)
    monkeypatch.setattr(lifecycle,'probe',lambda *_:dict(state='deleted',number=71))
    bridge.transfer_status(orders.settings,doc['id'])
    preview=bridge.preview(orders.settings,'worker',doc['id'],bridge.ReceiptRequest(expected_revision=0,voucher_date='1405/06/15',reference_no='2222'))
    assert preview['status']=='invalid' and 'نسخهٔ جدید' in preview['result']['Message']
    monkeypatch.setattr(lifecycle,'probe',lambda *_:dict(state='exists',number=71))
    with pytest.raises(service.WarehouseAssistantError):cb.edit_context(orders.settings,doc['id'])


def test_deleted_receipt_stays_quarantined_until_coherent_stock_snapshot(orders,monkeypatch):
    from app.warehouse_order_receipts import pending_stock
    doc=sent(orders)
    monkeypatch.setattr(lifecycle,'probe',lambda *_:dict(state='deleted',number=71))
    bridge.transfer_status(orders.settings,doc['id'])
    with service.warehouse_connection(orders.settings) as conn:
        assert '00123' in pending_stock(conn,'karaj')[1]
        captured=reflection.capture(conn)
        conn.execute("UPDATE warehouse_snapshots SET source_kind='varanegar',period_end='1405/06/15' WHERE id=1")
        reflection.apply(conn,captured,{doc['id']:dict(status='waiting',headers=[],items=[])},1)
        assert not pending_stock(conn,'karaj')[1]


def test_pre_matching_legacy_transfer_does_not_invent_an_active_confirmation(orders,monkeypatch):
    doc=sent(orders)
    with service.warehouse_connection(orders.settings) as conn:
        payload=json.loads(conn.execute('SELECT payload_json FROM warehouse_checkbar_transfers').fetchone()[0])
        payload.pop('order_matching')
        conn.execute('UPDATE warehouse_checkbar_transfers SET payload_json=?',(json.dumps(payload),))
        conn.execute('DELETE FROM warehouse_receipt_allocations')
    monkeypatch.setattr(lifecycle,'probe',lambda *_:dict(state='deleted',number=71))
    bridge.transfer_status(orders.settings,doc['id'])
    cb.delete_document(orders.settings,'worker',doc['id'],dict(expected_revision=0,request_id='delete'))
    with service.warehouse_connection(orders.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_checkbar_confirmations WHERE active=1').fetchone()[0]==0


@pytest.mark.parametrize('presence,expected',[('absent','deleted'),('matching','exists'),('different','review'),('orphan','review')])
def test_sql_probe_checks_both_identities_and_orphan_items_with_selects_only(monkeypatch,presence,expected):
    from contextlib import contextmanager
    from app import database
    key='12345678-1234-1234-1234-123456789abc'
    calls=[]
    class Cursor:
        def execute(self,sql):
            calls.append(sql);assert sql.strip().upper().startswith('SELECT')
            headers=[dict(ID=501,UniqueId=key if presence=='matching' else '12345678-1234-1234-1234-123456789def',VocherNo=71,ConfirmDate=None,ConfirmedBy=None)]
            self.rows=(headers if presence in ('matching','different') else []) if 'VocherHdr' in sql else ([{'HdrRef':501}] if presence=='orphan' else [])
            self.description=[(k,) for k in self.rows[0]] if self.rows else []
        def fetchall(self):return [tuple(r.values()) for r in self.rows]
    @contextmanager
    def connection(_):yield object()
    monkeypatch.setattr(database,'sql_connection',connection)
    monkeypatch.setattr(reflection,'snapshot_cursor',lambda _:Cursor())
    assert lifecycle.probe(None,dict(result_json=json.dumps(dict(VocherId=501,VocherNo=71)),transfer_key=key))['state']==expected
    assert f"ID=501 OR UniqueId='{key}'" in calls[0] and 'HdrRef=501' in calls[1]
