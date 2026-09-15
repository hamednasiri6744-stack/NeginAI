"""Real local services with temporary SQLite and a fake ERP transport only."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_warehouse_fulfillment import case, suggestion
from test_warehouse_checkbar import activate
from test_warehouse_receipt_bridge import Remote, req
from app import warehouse_checkbar as cb, warehouse_receipt_bridge as bridge
from app import warehouse_order_receipts as flow, warehouse_fulfillment as fulfillment
from app import warehouse_assistant_service as service


@pytest.fixture
def orders(case, monkeypatch):
    activate(case)
    case.send()
    with service.warehouse_connection(case.settings) as conn:
        conn.execute("UPDATE warehouse_automatic_preorder_lines SET order_quantity=100,conversion_rate=1,cartons=100")
        conn.execute("UPDATE warehouse_snapshot_items SET conversion_rate=1")
        first = dict(conn.execute('SELECT * FROM warehouse_automatic_preorders WHERE id=1').fetchone())
        first.update(id=2,preorder_number='ORDER-2',generation_key='second')
        conn.execute('INSERT INTO warehouse_automatic_preorders('+','.join(first)+') VALUES('+','.join('?' for _ in first)+')',list(first.values()))
        line = dict(conn.execute('SELECT * FROM warehouse_automatic_preorder_lines WHERE preorder_id=1').fetchone())
        line.pop('id');line['preorder_id']=2
        conn.execute('INSERT INTO warehouse_automatic_preorder_lines('+','.join(line)+') VALUES('+','.join('?' for _ in line)+')',list(line.values()))
        mail=dict(conn.execute('SELECT * FROM warehouse_email_attempts WHERE preorder_id=1').fetchone())
        mail.pop('id');mail.update(preorder_id=2,message_id='second@example.test',completed_at='2090-01-02T00:00:00+00:00')
        conn.execute('INSERT INTO warehouse_email_attempts('+','.join(mail)+') VALUES('+','.join('?' for _ in mail)+')',list(mail.values()))
        conn.execute("UPDATE warehouse_email_attempts SET completed_at='2090-01-01T00:00:00+00:00' WHERE preorder_id=1")
    case.settings.varanegar_receipt_bridge_enabled=True
    case.settings.varanegar_receipt_commit_enabled=True
    case.remote=Remote();monkeypatch.setattr(bridge,'_remote',case.remote)
    return case


def document(case, amount=120, key='new'):
    prepared=cb.prepare(case.settings,'karaj','supplier',[])
    return cb.issue(case.settings,'worker',dict(warehouse='karaj',supplier='supplier',order_ids=[],
        expected_token=prepared['expected_token'],request_id=key,metadata={'reference_no':'2222'},
        lines=[dict(preorder_id=None,product_code='00123',cartons=0,units=amount)]))


def prepared(case, doc, **fields):
    request=req(**fields)
    preview=bridge.preview(case.settings,'worker',doc['id'],request)
    return request.model_copy(update=dict(preview_token=preview['preview_token'],validation_token=preview['result']['ValidationToken']))


def details(case, order_id):
    with service.warehouse_connection(case.settings) as conn:
        return fulfillment.fulfillment_detail(conn,order_id)


def close(case, order_id, amount, key='close-one', reopen=False, revision=None):
    return flow.adjust_balance(case.settings,'manager',order_id,expected_revision=details(case,order_id)['revision'] if revision is None else revision,
        request_id=key,reason='supplier cannot send',lines=[dict(product_code='00123',quantity=amount)],reopen=reopen)


def test_fifo_200_ordered_120_arrived_leaves_80_only_after_sent(orders):
    doc=document(orders)
    plan=bridge.order_matching(orders.settings,doc['id'])
    assert [(a['preorder_id'],a['quantity']) for a in plan['allocations']]==[(1,100),(2,20)]
    request=prepared(orders,doc)
    assert details(orders,1)['received_qty']==0
    bridge.submit(orders.settings,'worker',doc['id'],request)
    assert details(orders,1)['status']=='received'
    assert (details(orders,2)['received_qty'],details(orders,2)['remaining_qty'])==(20,80)
    stock=service.list_inventory_information(orders.settings)['items'][0]
    assert (stock['on_hand_qty'],stock['in_transit_qty'],stock['pending_receipt_qty'],stock['effective_procurement_qty'])==(0,80,120,200)
    assert suggestion(orders)['inventory_position_qty']==200
    bridge.submit(orders.settings,'worker',doc['id'])
    assert details(orders,2)['received_qty']==20


def test_manual_allocation_can_override_fifo_without_changing_physical_count(orders):
    doc=document(orders)
    plan=bridge.order_matching(orders.settings,doc['id'])
    request=prepared(orders,doc,allocation_revision=plan['revision'],allocations=[dict(source_row=1,preorder_id=1,quantity=40),dict(source_row=1,preorder_id=2,quantity=80)])
    bridge.submit(orders.settings,'worker',doc['id'],request)
    assert details(orders,1)['remaining_qty']==60
    assert details(orders,2)['remaining_qty']==20
    encoded=json.loads(orders.remote.calls[-1][2])
    assert len(encoded['lines'])==1 and encoded['lines'][0]['quantity']=='120'


def test_concurrent_retries_consume_and_create_only_once(orders):
    from threading import Barrier
    doc=document(orders);request=prepared(orders,doc);barrier=Barrier(2)
    def send():
        barrier.wait(timeout=10)
        return bridge.submit(orders.settings,'worker',doc['id'],request)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first,second=pool.submit(send),pool.submit(send)
        assert first.result(timeout=20)['status']==second.result(timeout=20)['status']=='sent'
    assert len(orders.remote.commits)==1
    assert details(orders,2)['received_qty']==20


def test_different_carton_factors_never_change_base_unit_allocations(orders):
    orders.change('UPDATE warehouse_automatic_preorder_lines SET conversion_rate=12 WHERE preorder_id=1')
    orders.change('UPDATE warehouse_automatic_preorder_lines SET conversion_rate=24 WHERE preorder_id=2')
    doc=document(orders)
    plan=bridge.order_matching(orders.settings,doc['id'])
    assert [row['conversion_rate'] for row in plan['rows'][0]['orders']]==[12,24]
    assert [row['quantity'] for row in plan['allocations']]==[100,20]
    bridge.submit(orders.settings,'worker',doc['id'],prepared(orders,doc))
    assert details(orders,2)['remaining_qty']==80


def test_overage_requires_explicit_acceptance_and_buffers_entire_physical_receipt(orders):
    doc=document(orders,250)
    request=prepared(orders,doc)
    with pytest.raises(service.WarehouseAssistantError,match='اضافه'):
        bridge.submit(orders.settings,'worker',doc['id'],request)
    bridge.submit(orders.settings,'worker',doc['id'],request.model_copy(update={'accept_unallocated':True}))
    assert details(orders,2)['remaining_qty']==0
    with service.warehouse_connection(orders.settings) as conn:
        assert flow.pending_stock(conn,'karaj')[0]['00123']==250
        assert sum(r['received_qty'] for r in fulfillment.supply_rows(conn,'karaj'))==200


def test_unmatched_receipt_requires_acceptance_and_does_not_consume_other_supplier(orders):
    orders.change("UPDATE warehouse_automatic_preorders SET supplier='another supplier'")
    doc=document(orders,10)
    request=prepared(orders,doc,accept_unallocated=True)
    bridge.submit(orders.settings,'worker',doc['id'],request)
    assert details(orders,1)['received_qty']==0
    assert details(orders,2)['received_qty']==0


@pytest.mark.parametrize('allocations',[
    [dict(source_row=1,preorder_id=1,quantity=101)],
    [dict(source_row=1,preorder_id=1,quantity=100),dict(source_row=1,preorder_id=2,quantity=21)],
    [dict(source_row=2,preorder_id=1,quantity=1)],
    [dict(source_row=1,preorder_id=99,quantity=1)],
    [dict(source_row=1,preorder_id=1,quantity=1),dict(source_row=1,preorder_id=1,quantity=1)],
    [dict(source_row=1,preorder_id=1,quantity=.0001)],
])
def test_invalid_allocation_rejected_before_erp(orders,allocations):
    doc=document(orders)
    with pytest.raises(service.WarehouseAssistantError):
        bridge.preview(orders.settings,'worker',doc['id'],req(allocations=allocations))
    assert not orders.remote.calls


def test_pending_reservation_blocks_stale_second_request_and_closure(orders):
    one,two=document(orders,key='first'),document(orders,key='second')
    first,second=prepared(orders,one),prepared(orders,two)
    orders.remote.lose=True
    assert bridge.submit(orders.settings,'worker',one['id'],first)['status']=='pending'
    assert details(orders,1)['received_qty']==0
    assert details(orders,1)['lines'][0]['reserved_qty']==100
    assert suggestion(orders)['receipt_review_required']
    assert suggestion(orders)['suggested_quantity']==0
    with pytest.raises(service.WarehouseAssistantError):bridge.submit(orders.settings,'worker',two['id'],second)
    with pytest.raises(service.WarehouseAssistantError,match='پیگیری'):close(orders,1,1)
    assert bridge.submit(orders.settings,'worker',one['id'])['status']=='sent'
    assert details(orders,1)['received_qty']==100


def test_rejected_transfer_releases_reservation_without_receiving(orders):
    doc=document(orders);request=prepared(orders,doc);orders.remote.reject=True
    assert bridge.submit(orders.settings,'worker',doc['id'],request)['status']=='rejected'
    assert details(orders,1)['lines'][0]['reserved_qty']==0
    assert details(orders,1)['received_qty']==0
    assert close(orders,1,100)['status']=='closed'


def test_close_reopen_is_audited_idempotent_and_affects_new_order_planning(orders):
    doc=document(orders);bridge.submit(orders.settings,'worker',doc['id'],prepared(orders,doc))
    before=details(orders,2)
    result=close(orders,2,80,revision=before['revision'])
    assert result['status']=='closed' and result['closed_qty']==80 and result['received_qty']==20
    close(orders,2,80,revision=before['revision'])
    assert len(details(orders,2)['history'])==1
    assert service.list_inventory_information(orders.settings)['items'][0]['in_transit_qty']==0
    result=close(orders,2,80,key='reopen-one',reopen=True)
    assert result['remaining_qty']==80 and result['closed_qty']==0 and len(result['history'])==2
    with pytest.raises(service.WarehouseAssistantError):close(orders,2,81,key='too-much')
    with pytest.raises(service.WarehouseAssistantError):close(orders,2,1,key='close-one')


def test_closure_invalidates_matching_and_old_preview(orders):
    doc=document(orders);plan=bridge.order_matching(orders.settings,doc['id']);request=prepared(orders,doc)
    close(orders,1,5)
    with pytest.raises(service.WarehouseAssistantError):bridge.submit(orders.settings,'worker',doc['id'],request)
    with pytest.raises(service.WarehouseAssistantError,match='تغییر'):
        bridge.preview(orders.settings,'worker',doc['id'],req(allocation_revision=plan['revision']))


def test_manual_reconciliation_cannot_duplicate_a_bridged_receipt(orders):
    doc=document(orders);bridge.submit(orders.settings,'worker',doc['id'],prepared(orders,doc))
    with pytest.raises(service.WarehouseAssistantError,match='دوبار'):
        fulfillment.receive_fulfillment(orders.settings,'worker',2,expected_revision=details(orders,2)['revision'],snapshot_id=1,
            inventory_reflected=True,reference='ERP-71',lines=[dict(product_code='00123',received_qty=100)])


def test_confirmation_reflection_keeps_position_and_review_blocks_manual_purchase(orders):
    doc=document(orders);bridge.submit(orders.settings,'worker',doc['id'],prepared(orders,doc))
    orders.change("UPDATE warehouse_receipt_stock_state SET status='reflected'")
    orders.change('UPDATE warehouse_snapshot_items SET stock=120')
    row=service.list_inventory_information(orders.settings)['items'][0]
    assert (row['in_transit_qty'],row['pending_receipt_qty'],row['effective_procurement_qty'])==(80,0,200)
    orders.change("UPDATE warehouse_receipt_stock_state SET status='review'")
    assert suggestion(orders)['suggested_quantity']==0 and suggestion(orders)['receipt_review_required']
    with pytest.raises(service.WarehouseAssistantError,match='پیگیری'):
        service.create_supplier_orders(orders.settings,'buyer',snapshot_id=1,warehouse='karaj',lines=[dict(product_code='00123',quantity=1)])


def test_stale_revision_does_not_change_balance(orders):
    with pytest.raises(service.WarehouseAssistantError):close(orders,1,10,revision=9)
    assert details(orders,1)['remaining_qty']==100


def test_blank_reason_is_optional_and_preserves_idempotent_audit(orders):
    payload=dict(expected_revision=0,request_id='blank-reason',reason=' ',lines=[dict(product_code='00123',quantity=20)])
    result=flow.adjust_balance(orders.settings,'worker',1,**payload)
    assert result['remaining_qty']==80
    assert result['received_qty']==0
    assert result['history'][0]['reason']==''
    assert flow.adjust_balance(orders.settings,'worker',1,**payload)['remaining_qty']==80


def test_balance_routes_require_permission_and_explicit_confirmation(orders,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=orders.settings;app.include_router(routes.router)
    payload=dict(expected_revision=0,request_id='route-close',lines=[dict(product_code='00123',quantity=5)],confirmed=True)
    with TestClient(app) as client:
        url='/warehouse-assistant/api/fulfillment-orders/1/balance'
        assert client.post(url,json=payload).status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'worker'
        monkeypatch.setattr(routes,'_capabilities',lambda *_:set())
        assert client.post(url,json=payload).status_code==403
        monkeypatch.setattr(routes,'_capabilities',lambda *_:{'warehouse.order.draft'})
        assert client.post(url,json={**payload,'confirmed':False}).status_code==422
        result=client.post(url,json=payload)
        assert result.status_code==200,result.text
        assert result.json()['fulfillment']['remaining_qty']==95


def newer_snapshot(case, stock=120):
    with service.warehouse_connection(case.settings) as conn:
        row=dict(conn.execute('SELECT * FROM warehouse_snapshots WHERE id=1').fetchone())
        row.update(id=2,content_sha256='new-stock-snapshot')
        conn.execute('INSERT INTO warehouse_snapshots('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',list(row.values()))
        item=dict(conn.execute('SELECT * FROM warehouse_snapshot_items LIMIT 1').fetchone())
        item.pop('id');item.update(snapshot_id=2,stock=stock)
        conn.execute('INSERT INTO warehouse_snapshot_items('+','.join(item)+') VALUES('+','.join('?' for _ in item)+')',list(item.values()))


@pytest.mark.parametrize('read',[lambda case:service.list_inventory_information(case.settings),suggestion])
def test_snapshot_publication_between_selection_and_ledger_read_requires_refresh(orders,monkeypatch,read):
    previous=service.latest_snapshot(orders.settings)
    def raced(_):
        newer_snapshot(orders)
        return previous
    monkeypatch.setattr(service,'latest_snapshot',raced)
    with pytest.raises(service.WarehouseAssistantError,match='بازخوانی'):
        read(orders)


def test_preorder_catalog_uses_current_stock_with_current_receipt_ledger(orders):
    from app.warehouse_preorder_catalog import catalog_items
    doc=document(orders);bridge.submit(orders.settings,'worker',doc['id'],prepared(orders,doc))
    newer_snapshot(orders)
    orders.change("UPDATE warehouse_receipt_stock_state SET status='reflected',snapshot_id=2")
    with service.warehouse_connection(orders.settings) as conn:
        conn.execute('BEGIN')
        order=conn.execute('SELECT * FROM warehouse_automatic_preorders WHERE id=2').fetchone()
        item=catalog_items(conn,order)[0]
        assert (item['on_hand_qty'],item['pending_receipt_qty'],item['effective_procurement_qty'])==(120,0,200)


@pytest.mark.parametrize('failure',[None,'source','publish'])
def test_stock_import_reads_evidence_in_same_source_transaction_and_publishes_atomically(orders,monkeypatch,failure):
    from contextlib import contextmanager
    from test_warehouse_assistant import _FakeWarehouseConnection
    from app import warehouse_receipt_reflection as reflection
    doc=document(orders);bridge.submit(orders.settings,'worker',doc['id'],prepared(orders,doc))
    orders.settings.sql_server='synthetic';orders.settings.sql_username='synthetic';orders.settings.sql_password='synthetic'
    orders.settings.sql_configured=True
    queries=[]
    @contextmanager
    def source(_):yield _FakeWarehouseConnection(queries)
    monkeypatch.setattr(service,'sql_connection',source)
    def evidence(cursor,captured):
        assert cursor.queries is queries
        assert queries[0]=='SET TRANSACTION ISOLATION LEVEL SNAPSHOT'
        assert 'FRU.StockGoodsModel' in queries[1]
        if failure=='source':raise service.WarehouseAssistantError('synthetic source failure')
        return {str(doc['id']):dict(status='reflected',headers=[],message='synthetic coherent evidence')}
    monkeypatch.setattr(reflection,'source_queries',evidence)
    original=reflection.apply
    def publish(*args):
        original(*args)
        if failure=='publish':raise service.WarehouseAssistantError('synthetic publication failure')
    monkeypatch.setattr(reflection,'apply',publish)
    if failure:
        with pytest.raises(service.WarehouseAssistantError,match='synthetic'):
            service.sync_varanegar_snapshot(orders.settings,'tester')
    else:
        service.sync_varanegar_snapshot(orders.settings,'tester')
    with service.warehouse_connection(orders.settings) as conn:
        row=conn.execute('SELECT status,snapshot_id FROM warehouse_receipt_stock_state').fetchone()
        latest=conn.execute('SELECT MAX(id) FROM warehouse_snapshots').fetchone()[0]
        assert (row['status'],row['snapshot_id'],latest)==(('waiting',None,1) if failure else ('reflected',2,2))
