"""Confirmed checkbar receipts, temporary SQLite and fake ERP only."""
import pytest
from test_warehouse_order_receipts import orders, details, close, prepared
from test_warehouse_fulfillment import case, suggestion
from app import warehouse_checkbar as cb, warehouse_assistant_service as service
from app import warehouse_receipt_bridge as bridge


def draft(orders, amount=120, key='confirmed-one'):
    source=cb.prepare(orders.settings,'karaj','supplier',[])
    return dict(warehouse='karaj',supplier='supplier',order_ids=[],expected_token=source['expected_token'],
        request_id=key,metadata={'reference_no':'2222'},
        lines=[dict(preorder_id=None,product_code='00123',cartons=0,units=amount)])


def checked(orders,payload,**preview_fields):
    plan=cb.matching_preview(orders.settings,dict(payload,**preview_fields))
    return dict(payload,confirm_receipt=True,allocations=[{k:v for k,v in a.items() if k!='product_code'} for a in plan['allocations']],
                allocation_revision=plan['revision'],accept_unallocated=plan['unallocated_qty']>0)


def issue(orders,amount=120,key='confirmed-one'):
    return cb.issue(orders.settings,'worker',checked(orders,draft(orders,amount,key)))


def edit(orders,doc,amount=60):
    raw=draft(orders,amount,'edit-one')
    payload=checked(orders,raw,document_id=doc['id'],expected_revision=doc['revision'])
    return cb.edit_document(orders.settings,'worker',doc['id'],dict(
        expected_revision=doc['revision'],**{k:v for k,v in payload.items() if k not in ('warehouse','supplier','order_ids','expected_token')}))


def test_preview_is_readonly_and_confirmed_save_immediately_consumes_fifo_without_erp(orders):
    source=cb.prepare(orders.settings,'karaj','supplier',[])
    assert len(source['aggregate_open_lines'])==1
    assert source['aggregate_open_lines'][0]['preorder_id'] is None
    assert source['aggregate_open_lines'][0]['remaining_qty']==200
    payload=checked(orders,draft(orders))
    assert details(orders,1)['received_qty']==0
    doc=cb.issue(orders.settings,'worker',payload)
    assert doc['receipt_confirmed']
    assert bridge.order_matching(orders.settings,doc['id'])==doc['order_matching']
    assert details(orders,1)['status']=='received'
    assert (details(orders,2)['received_qty'],details(orders,2)['remaining_qty'])==(20,80)
    assert orders.remote.calls==[]
    inventory=service.list_inventory_information(orders.settings)['items'][0]
    assert (inventory['on_hand_qty'],inventory['in_transit_qty'],inventory['pending_receipt_qty'])==(0,80,120)
    assert suggestion(orders)['inventory_position_qty']==200
    assert cb.issue(orders.settings,'worker',payload)['id']==doc['id']
    assert details(orders,2)['remaining_qty']==80


@pytest.mark.parametrize('result',['sent','pending','rejected'])
def test_later_erp_result_never_consumes_checkbar_receipt_twice(orders,result):
    doc=issue(orders)
    request=prepared(orders,doc,matching_confirmed=False)
    orders.remote.lose=result=='pending';orders.remote.reject=result=='rejected'
    assert bridge.submit(orders.settings,'worker',doc['id'],request)['status']==result
    assert details(orders,2)['remaining_qty']==80
    assert suggestion(orders)['inventory_position_qty']==200
    if result=='pending':
        assert bridge.submit(orders.settings,'worker',doc['id'])['status']=='sent'
        assert details(orders,2)['remaining_qty']==80


def test_edit_reallocates_own_capacity_and_delete_reopens_balance_with_history(orders):
    doc=issue(orders)
    changed=edit(orders,doc,60)
    assert changed['id']==doc['id'] and changed['revision']==1
    assert details(orders,1)['received_qty']==60
    assert details(orders,2)['received_qty']==0
    assert suggestion(orders)['inventory_position_qty']==200
    request=dict(expected_revision=1,request_id='delete-confirmed')
    cb.delete_document(orders.settings,'worker',doc['id'],request)
    cb.delete_document(orders.settings,'worker',doc['id'],request)
    assert details(orders,1)['remaining_qty']==details(orders,2)['remaining_qty']==100
    assert service.list_inventory_information(orders.settings)['items'][0]['pending_receipt_qty']==0
    versions=cb.document_history(orders.settings,doc['id'])['versions']
    assert [v['operation'] for v in versions]==['issue','edit','delete']
    assert versions[0]['document']['order_matching']['allocations'][0]['quantity']==100


def test_out_of_cycle_closure_after_checkbar_save_preserves_received_and_can_reopen(orders):
    issue(orders)
    result=close(orders,2,80)
    assert (result['status'],result['received_qty'],result['remaining_qty'])==('closed',20,0)
    assert suggestion(orders)['inventory_position_qty']==120
    result=close(orders,2,80,key='reopen',reopen=True)
    assert result['remaining_qty']==80
    assert len(result['history'])==2


def test_stale_draft_and_missing_confirmation_plan_cannot_consume(orders):
    raw=draft(orders)
    payload=checked(orders,raw)
    close(orders,1,10)
    with pytest.raises(service.WarehouseAssistantError):cb.issue(orders.settings,'worker',payload)
    raw=draft(orders)
    with pytest.raises(service.WarehouseAssistantError):cb.issue(orders.settings,'worker',dict(raw,confirm_receipt=True))
    assert details(orders,1)['received_qty']==0


def test_overage_requires_acceptance_and_zero_is_not_blank(orders):
    raw=draft(orders,250)
    payload=checked(orders,raw)
    with pytest.raises(service.WarehouseAssistantError,match='اضافه'):
        cb.issue(orders.settings,'worker',dict(payload,accept_unallocated=False))
    cb.issue(orders.settings,'worker',payload)
    assert service.list_inventory_information(orders.settings)['items'][0]['pending_receipt_qty']==250
    zero=issue(orders,0,'zero')
    assert zero['lines'][0]['actual_qty']==0
    raw=draft(orders,None,'blank');raw['lines'][0]['cartons']=None
    with pytest.raises(service.WarehouseAssistantError,match='خالی'):checked(orders,raw)


def test_sent_confirmation_blocks_edit_and_delete_and_keeps_transferred_receipt(orders):
    doc=issue(orders)
    bridge.submit(orders.settings,'worker',doc['id'],prepared(orders,doc))
    with pytest.raises(service.WarehouseAssistantError):edit(orders,doc,20)
    with pytest.raises(service.WarehouseAssistantError):
        cb.delete_document(orders.settings,'worker',doc['id'],dict(expected_revision=0,request_id='deleted-after-erp'))
    assert details(orders,2)['remaining_qty']==80
    assert suggestion(orders)['inventory_position_qty']==200


def test_inventory_excel_cannot_double_count_untransferred_confirmed_goods(orders,tmp_path):
    from test_warehouse_assistant import _inventory_workbook
    issue(orders)
    path=tmp_path/'stock.xlsx';path.write_bytes(_inventory_workbook())
    with pytest.raises(service.WarehouseAssistantError,match='ورانگر'):
        service.import_inventory_snapshot(orders.settings,path,'stock.xlsx','worker')
    assert service.latest_snapshot(orders.settings)['id']==1


def test_public_confirm_save_and_close_workflow_records_actor_without_erp(orders,monkeypatch):
    from fastapi import FastAPI,Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=orders.settings;app.include_router(routes.router)
    raw=draft(orders)
    with TestClient(app) as client:
        path='/warehouse-assistant/api/checkbars/matching-preview'
        assert client.post(path,json=raw).status_code==401
        def user(request:Request):request.state.username='warehouse-worker';return 'warehouse-worker'
        app.dependency_overrides[routes.require_session_user]=user
        monkeypatch.setattr(routes,'_capabilities',lambda *_:{'warehouse.order.draft','warehouse.assistant.view'})
        plan=client.post(path,json=raw)
        assert plan.status_code==200,plan.text
        data=plan.json()
        payload=dict(raw,confirm_receipt=True,allocation_revision=data['revision'],allocations=[{k:v for k,v in a.items() if k!='product_code'} for a in data['allocations']])
        response=client.post('/warehouse-assistant/api/checkbars',json=payload)
        assert response.status_code==201,response.text
        assert response.json()['document']['receipt_confirmed']
        info=details(orders,2)
        assert info['remaining_qty']==80 and info['received_qty']==20
        response=client.post('/warehouse-assistant/api/fulfillment-orders/2/balance',json=dict(
            expected_revision=info['revision'],request_id='close-via-api',reason='Supplier will not send',confirmed=True,
            lines=[dict(product_code='00123',quantity=80)]))
        assert response.status_code==200,response.text
        info=response.json()['fulfillment']
        assert info['status']=='closed' and info['history'][0]['recorded_by']=='warehouse-worker'
        assert orders.remote.calls==[]
