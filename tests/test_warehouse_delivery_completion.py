import pytest
from test_warehouse_fulfillment import case
from test_warehouse_order_receipts import orders, details, close
from test_checkbar_confirmation import issue
from app import warehouse_order_receipts as flow, warehouse_checkbar as cb
from app import warehouse_fulfillment as fulfillment, warehouse_assistant_service as service


def finish(case, order_id=1, key='finish-delivery'):
    return flow.finish_delivery(case.settings,'manager',order_id,
        expected_revision=details(case,order_id)['revision'],request_id=key)


@pytest.mark.parametrize('amount',[40,100])
def test_completion_survives_linked_checkbar_deletion_without_reopening_capacity(orders,amount):
    doc=issue(orders,amount)
    ended=finish(orders)
    assert ended['status']=='closed' and ended['delivery_ended']
    assert ended['remaining_qty']==0 and ended['received_qty']==amount
    cb.delete_document(orders.settings,'worker',doc['id'],dict(expected_revision=0,request_id='delete-linked'))
    info=details(orders,1)
    assert info['status']=='closed' and info['remaining_qty']==0 and info['received_qty']==0
    assert info['completion']['recorded_by']=='manager'
    assert 1 not in [o['id'] for o in fulfillment.list_fulfillment_orders(orders.settings)]
    with service.warehouse_connection(orders.settings) as conn:
        assert fulfillment.supply_position(conn,'karaj')[0]['00123']==100  # Only order 2.
        plan=flow.matching(conn,dict(warehouse='karaj',supplier='supplier',lines=[dict(product_code='00123',actual_qty=50)]))
        assert [a['preorder_id'] for a in plan['allocations']]==[2]
    with pytest.raises(service.WarehouseAssistantError):close(orders,1,10,reopen=True)


def test_finish_is_idempotent_checks_revision_and_preserves_unrelated_order(orders):
    revision=details(orders,1)['revision']
    with pytest.raises(service.WarehouseAssistantError):
        flow.finish_delivery(orders.settings,'manager',1,expected_revision=revision+1,request_id='stale-end')
    finish(orders)
    replay=flow.finish_delivery(orders.settings,'manager',1,expected_revision=revision,request_id='finish-delivery')
    assert replay['delivery_ended'] and replay['completion']['request_id']=='finish-delivery'
    assert details(orders,2)['remaining_qty']==100


def test_end_blocks_reuse_of_own_previous_allocation_during_checkbar_edit(orders):
    doc=issue(orders,40);finish(orders)
    with service.warehouse_connection(orders.settings) as conn:
        plan=flow.matching(conn,doc,exclude_document_id=doc['id'])
    assert all(a['preorder_id']!=1 for a in plan['allocations'])


def test_remaining_checkbar_targets_selected_order_not_older_fifo_order(orders):
    source=cb.prepare(orders.settings,'karaj','supplier',[2],remaining_order_id=2)
    assert [o['id'] for o in source['outstanding_orders']]==[2]
    payload=dict(warehouse='karaj',supplier='supplier',order_ids=[2],remaining_order_id=2,
        expected_token=source['expected_token'],request_id='remaining-order-2',metadata={'reference_no':'2222'},
        lines=[dict(preorder_id=2,product_code='00123',cartons=0,units=25)])
    doc=cb.issue(orders.settings,'worker',payload)
    assert doc['remaining_order_id']==2
    with service.warehouse_connection(orders.settings) as conn:
        plan=flow.matching(conn,doc)
    assert [(a['preorder_id'],a['quantity']) for a in plan['allocations']]==[(2,25)]
    with pytest.raises(service.WarehouseAssistantError):
        cb.prepare(orders.settings,'karaj','supplier',[1],remaining_order_id=2)


def test_finish_endpoint_requires_permission_confirmation_and_replays_safely(orders,monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=orders.settings;app.include_router(routes.router)
    payload=dict(expected_revision=details(orders,1)['revision'],request_id='route-finish',confirmed=True)
    with TestClient(app) as client:
        url='/warehouse-assistant/api/fulfillment-orders/1/finish'
        assert client.post(url,json=payload).status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'worker'
        monkeypatch.setattr(routes,'_capabilities',lambda *_:set())
        assert client.post(url,json=payload).status_code==403
        monkeypatch.setattr(routes,'_capabilities',lambda *_:{'warehouse.order.draft'})
        assert client.post(url,json={**payload,'confirmed':False}).status_code==422
        result=client.post(url,json=payload)
        assert result.status_code==200,result.text
        assert result.json()['fulfillment']['delivery_ended']
        assert result.json()['varanegar_write'] is False
        assert client.post(url,json=payload).status_code==200


def test_stale_allocation_plan_cannot_receive_against_completed_order(orders):
    with service.warehouse_connection(orders.settings) as conn:
        doc=dict(warehouse='karaj',supplier='supplier',lines=[dict(product_code='00123',actual_qty=40)])
        plan=flow.matching(conn,doc)
    finish(orders)
    with service.warehouse_connection(orders.settings) as conn:
        with pytest.raises(service.WarehouseAssistantError):
            flow.matching(conn,doc,requested=plan['allocations'],expected_revision=plan['revision'])
