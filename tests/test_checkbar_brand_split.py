"""Brand issuance uses temporary SQLite and the existing fake ERP only."""
import pytest
from test_checkbar_confirmation import checked, draft
from test_warehouse_order_receipts import orders, details, prepared
from test_warehouse_fulfillment import case
from app import warehouse_checkbar as cb, warehouse_assistant_service as service
from app import warehouse_receipt_bridge as bridge, warehouse_order_receipts as flow


@pytest.fixture
def brands(orders):
    with service.warehouse_connection(orders.settings) as conn:
        conn.execute("UPDATE warehouse_snapshot_items SET brand='Alpha'")
        conn.execute("UPDATE warehouse_automatic_preorder_lines SET brand='Alpha'")
        stock=dict(conn.execute('SELECT * FROM warehouse_snapshot_items LIMIT 1').fetchone())
        for code,brand in [('B200','Beta'),('C300','Alpha')]:
            row=dict(stock,product_code=code,product_name=code,brand=brand)
            row.pop('id',None)
            conn.execute('INSERT INTO warehouse_snapshot_items('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',list(row.values()))
            for order_id in [1,2]:
                row=dict(conn.execute('SELECT * FROM warehouse_automatic_preorder_lines WHERE preorder_id=? LIMIT 1',(order_id,)).fetchone())
                row.pop('id');row.update(product_code=code,product_name=code,brand=brand)
                conn.execute('INSERT INTO warehouse_automatic_preorder_lines('+','.join(row)+') VALUES('+','.join('?' for _ in row)+')',list(row.values()))
    return orders


def request(brands,split=True):
    raw=draft(brands)
    raw.update(split_by_brand=split,lines=[dict(preorder_id=None,product_code=c,cartons=0,units=q) for c,q in [('00123',120),('B200',60),('C300',30)]])
    return checked(brands,raw)


def test_atomic_split_remaps_fifo_and_replay_without_double_consumption(brands):
    payload=request(brands)
    doc=cb.issue(brands.settings,'worker',payload)
    assert [d['brand'] for d in doc['brand_batch']]==['Alpha','Beta']
    children=[cb.get_document(brands.settings,d['id']) for d in doc['brand_batch']]
    assert [len(d['lines']) for d in children]==[2,1]
    assert all(d['metadata']['reference_no']=='2222' for d in children)
    assert [(a['source_row'],a['product_code'],a['quantity']) for a in children[0]['order_matching']['allocations']]==[(1,'00123',100),(1,'00123',20),(2,'C300',30)]
    assert children[1]['order_matching']['allocations'][0]['source_row']==1
    assert children[0]['number']!=children[1]['number']
    assert details(brands,1)['received_qty']==190
    assert details(brands,2)['received_qty']==20
    assert cb.issue(brands.settings,'worker',payload)['brand_batch']==doc['brand_batch']
    assert len(cb.documents(brands.settings))==2
    assert details(brands,1)['received_qty']==190
    assert brands.remote.calls==[]
    with service.warehouse_connection(brands.settings) as conn:
        assert flow.pending_stock(conn,'karaj')[0]=={'00123':120,'B200':60,'C300':30}


def test_default_off_preserves_single_document_and_zero(brands):
    raw=request(brands,False)
    raw['lines'][1]['units']=0
    payload=checked(brands,raw)
    doc=cb.issue(brands.settings,'worker',payload)
    assert len(doc['lines'])==3 and doc['lines'][1]['actual_qty']==0
    assert 'brand_batch' not in doc


def test_unknown_brand_refused_without_any_document_or_allocation(brands):
    with service.warehouse_connection(brands.settings) as conn:
        conn.execute("UPDATE warehouse_snapshot_items SET brand='' WHERE product_code='B200'")
    with pytest.raises(service.WarehouseAssistantError,match='برند'):
        cb.issue(brands.settings,'worker',request(brands))
    assert cb.documents(brands.settings)==[]
    assert details(brands,1)['received_qty']==0


def test_second_child_failure_rolls_back_whole_batch(brands,monkeypatch):
    payload=request(brands)
    original=flow.confirm_checkbar
    calls=[]
    def fail_second(*args):
        calls.append(1)
        if len(calls)==2:raise RuntimeError('isolated failure')
        return original(*args)
    monkeypatch.setattr(flow,'confirm_checkbar',fail_second)
    with pytest.raises(RuntimeError,match='isolated failure'):cb.issue(brands.settings,'worker',payload)
    assert cb.documents(brands.settings)==[]
    assert details(brands,1)['received_qty']==0


def test_children_transfer_independently_and_delete_only_releases_own_brand(brands):
    first=cb.issue(brands.settings,'worker',request(brands))
    second=cb.get_document(brands.settings,first['brand_batch'][1]['id'])
    bridge.submit(brands.settings,'worker',second['id'],prepared(brands,second))
    assert bridge.transfer_status(brands.settings,first['id'])['status']=='not_sent'
    assert bridge.transfer_status(brands.settings,second['id'])['status']=='sent'
    cb.delete_document(brands.settings,'worker',first['id'],dict(expected_revision=0,request_id='delete-alpha'))
    assert details(brands,1)['received_qty']==60
    assert details(brands,2)['received_qty']==0


def test_manual_allocations_preserved_and_brand_locked_during_edit(brands):
    raw=request(brands)
    # Explicitly allocate 80 to the newer order, overriding FIFO.
    raw['allocations']=[dict(source_row=1,preorder_id=1,quantity=40),dict(source_row=1,preorder_id=2,quantity=80),
                        dict(source_row=2,preorder_id=1,quantity=60),dict(source_row=3,preorder_id=1,quantity=30)]
    doc=cb.issue(brands.settings,'worker',raw)
    assert [a['quantity'] for a in doc['order_matching']['allocations']]==[40,80,30]
    edit=dict(expected_revision=0,request_id='edit-add-wrong-brand',metadata={'reference_no':'2222'},lines=raw['lines'])
    with pytest.raises(service.WarehouseAssistantError,match='برند'):cb.edit_document(brands.settings,'worker',doc['id'],edit)
    assert cb.get_document(brands.settings,doc['id'])['revision']==0
    assert {line['brand'] for line in cb.edit_context(brands.settings,doc['id'])['catalog']}=={'Alpha'}


def test_zero_count_is_kept_but_blank_confirmed_batch_is_rejected(brands):
    raw=request(brands)
    raw['lines'][1]['units']=0
    payload=checked(brands,raw)
    first=cb.issue(brands.settings,'worker',payload)
    second=cb.get_document(brands.settings,first['brand_batch'][1]['id'])
    assert len(second['lines'])==1 and second['lines'][0]['actual_qty']==0
    assert second['order_matching']['allocations']==[]
    # A zero-only document can be retained; it is not a positive-quantity ERP receipt.
    with pytest.raises(service.WarehouseAssistantError):prepared(brands,second)
    raw=draft(brands,key='blank-batch')
    raw.update(split_by_brand=True,confirm_receipt=True)
    raw['lines'][0].update(cartons=None,units=None)
    with pytest.raises(service.WarehouseAssistantError,match='خالی'):cb.issue(brands.settings,'worker',raw)
    assert len(cb.documents(brands.settings))==2


def test_concurrent_retry_only_creates_one_batch(brands):
    from concurrent.futures import ThreadPoolExecutor
    payload=request(brands)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:cb.issue(brands.settings,'worker',payload),range(2)))
    assert results[0]['brand_batch']==results[1]['brand_batch']
    assert len(cb.documents(brands.settings))==2
    assert details(brands,2)['received_qty']==20
    with pytest.raises(service.WarehouseAssistantError):
        cb.issue(brands.settings,'worker',dict(payload,split_by_brand=False))


def test_brand_batch_public_api_and_excel(brands,monkeypatch):
    from io import BytesIO
    from openpyxl import load_workbook
    from fastapi import FastAPI,Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=brands.settings;app.include_router(routes.router)
    def user(request:Request):request.state.username='warehouse-worker';return 'warehouse-worker'
    app.dependency_overrides[routes.require_session_user]=user
    monkeypatch.setattr(routes,'_capabilities',lambda *_:{'warehouse.order.draft','warehouse.assistant.view'})
    with TestClient(app) as client:
        result=client.post('/warehouse-assistant/api/checkbars',json=request(brands))
        assert result.status_code==201,result.text
        assert result.json()['varanegar_write'] is False
        batch=result.json()['document']['brand_batch']
        for item in batch:
            response=client.get(f"/warehouse-assistant/api/checkbars/{item['id']}/document.xlsx")
            assert response.status_code==200
            book=load_workbook(BytesIO(response.content))
            assert item['brand'] in book.active['K3'].value
        listed=client.get('/warehouse-assistant/api/checkbars').json()['documents']
        assert {d['brand'] for d in listed}=={'Alpha','Beta'}
