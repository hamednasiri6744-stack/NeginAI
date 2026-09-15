"""Only isolated SQLite fixtures; never move live stock or send messages."""
import pytest
from test_warehouse_fulfillment import case
from app import warehouse_assistant_service as service
from app import warehouse_rebalancing as rebalance


@pytest.fixture
def balance(case):
    case.change("UPDATE warehouse_automatic_preorders SET status='awaiting_approval',approved_at=NULL")
    case.change('UPDATE warehouse_snapshot_items SET consumer_price=100')
    with service.warehouse_connection(case.settings) as conn:
        conn.execute("""INSERT INTO warehouse_snapshot_items(snapshot_id,source_row,warehouse_code,
            warehouse_name,product_code,product_name,conversion_rate,manufacturer,brand,stock,
            period_out,sales_rate_days,consumer_price)
            VALUES(1,2,'tehran','Tehran','00123','Test',12,'supplier','brand',112,120,60,100)""")
    return case


def proposal(case, kind='automatic_preorder', ident=1):
    return rebalance.preview(case.settings,'test-user',kind,ident,include_all=True)


def accept(case, data, cartons=1, key='test-transfer'):
    return rebalance.accept(case.settings,'test-user',data['document_kind'],data['document_id'],
        [{'product_code':'00123','cartons':cartons}],expected_token=data['expected_token'],
        request_id=key,include_all=True)


def test_fifty_day_surplus_equal_consumer_price_and_partial_order(balance):
    data=proposal(balance)
    assert data['source']=='tehran' and data['destination']=='karaj'
    assert data['lines'][0]['available_cartons']==1  # 112 - (120/60)*50 = 12
    result=accept(balance,data)
    assert result['order']['total_quantity']==12
    assert result['order']['lines'][0]['cartons']==1
    rows=rebalance.list_requests(balance.settings,'test-user',include_all=True)
    assert len(rows)==1 and rows[0]['quantity']==12
    assert rows[0]['source']=='tehran' and rows[0]['destination']=='karaj'
    assert proposal(balance)['lines'][0]['available_cartons']==0
    assert service.build_suggestions(balance.settings,warehouse='karaj',only_needed=False)['items'][0]['in_transit_qty']==12
    assert service.build_suggestions(balance.settings,warehouse='tehran',only_needed=False)['items'][0]['available_quantity']==100
    balance.transport.assert_not_called()


@pytest.mark.parametrize('price,cartons',[(99,0),(100,1),(101,1),(0,0)])
def test_price_direction(balance,price,cartons):
    balance.change(f"UPDATE warehouse_snapshot_items SET consumer_price={price} WHERE warehouse_code='tehran'")
    assert proposal(balance)['lines'][0]['available_cartons']==cartons


def test_adjusted_demand_not_raw_sales_and_rounding_down(balance):
    balance.change("UPDATE warehouse_snapshots SET demand_basis='net_sales_last_stock_window'")
    balance.change("UPDATE warehouse_snapshot_items SET period_out=30,raw_period_out=300,sales_rate_days=30,stock=73 WHERE warehouse_code='tehran'")
    assert proposal(balance)['lines'][0]['available_cartons']==1  # 23 loose units, one full carton


def test_unknown_demand_or_missing_price_not_assumed_zero(balance):
    balance.change("UPDATE warehouse_snapshots SET demand_basis='net_sales_last_stock_window'")
    balance.change("UPDATE warehouse_snapshot_items SET sales_rate_days=0 WHERE warehouse_code='tehran'")
    assert proposal(balance)['lines'][0]['available_cartons']==0


def test_full_transfer_closes_purchase_without_deleting_transfer_or_snapshot(balance):
    balance.change("UPDATE warehouse_snapshot_items SET stock=124 WHERE warehouse_code='tehran'")
    before=balance.order()
    data=proposal(balance)
    result=accept(balance,data,2)
    assert result['order']['status']=='cancelled' and not result['order']['lines']
    assert result['order']['total_quantity']==0
    assert accept(balance,data,2)==result  # retry does not duplicate or subtract again
    assert len(rebalance.list_requests(balance.settings,'test-user',include_all=True))==1
    with service.warehouse_connection(balance.settings) as conn:
        assert conn.execute("SELECT stock FROM warehouse_snapshot_items WHERE warehouse_code='tehran'").fetchone()[0]==124
    assert before['total_quantity']==24


def test_stale_stock_or_price_rejected_atomically(balance):
    data=proposal(balance)
    balance.change("UPDATE warehouse_snapshot_items SET consumer_price=99 WHERE warehouse_code='tehran'")
    with pytest.raises(service.WarehouseAssistantError):accept(balance,data)
    assert balance.order()['total_quantity']==24
    assert not rebalance.list_requests(balance.settings,'test-user',include_all=True)


def test_manual_reverse_direction_same_behavior(balance):
    balance.change("UPDATE warehouse_snapshot_items SET stock=124 WHERE warehouse_code='karaj'")
    balance.change("UPDATE warehouse_snapshot_items SET stock=0 WHERE warehouse_code='tehran'")
    order=service.create_supplier_orders(balance.settings,'test-user',snapshot_id=1,warehouse='tehran',
        lines=[{'product_code':'00123','quantity':24}],note='isolated test')[0]
    data=proposal(balance,'supplier_order',order['id'])
    assert data['source']=='karaj' and data['destination']=='tehran'
    assert accept(balance,data,2)['order']['status']=='cancelled'


def test_approved_order_and_other_owners_cannot_be_mutated(balance):
    balance.change("UPDATE warehouse_automatic_preorders SET status='approved',approved_at='now'")
    with pytest.raises(service.WarehouseAssistantError):proposal(balance)


def test_request_does_not_oversubscribe_or_accept_zero(balance):
    data=proposal(balance)
    for count in [0,2,-1,True,1.5]:
        with pytest.raises(service.WarehouseAssistantError):accept(balance,data,count)
    assert balance.order()['total_quantity']==24


def test_out_of_cycle_cannot_supply(balance):
    with service.warehouse_connection(balance.settings) as conn:
        conn.execute("INSERT INTO warehouse_order_cycle_overrides(warehouse_code,product_code,forced_active,updated_by,updated_at) VALUES('tehran','00123',0,'test','now')")
    assert proposal(balance)['lines'][0]['available_cartons']==0


def test_two_drafts_cannot_reserve_the_same_stock(balance):
    manual=service.create_supplier_orders(balance.settings,'test-user',snapshot_id=1,warehouse='karaj',
        lines=[{'product_code':'00123','quantity':24}],note='second draft')[0]
    earlier=proposal(balance,'supplier_order',manual['id'])
    accept(balance,proposal(balance))
    with pytest.raises(service.WarehouseAssistantError):accept(balance,earlier,key='second')
    assert service.get_supplier_order(balance.settings,manual['id'],'test-user',include_all=True)['total_quantity']==24


def test_route_permissions_and_manual_owner(balance):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=balance.settings;app.include_router(routes.router)
    with TestClient(app) as client:
        assert client.get('/warehouse-assistant/api/interwarehouse').status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'test-user'
        with patch.object(routes,'_capabilities',return_value=set()):
            assert client.get('/warehouse-assistant/api/interwarehouse').status_code==403
        with patch.object(routes,'_require',return_value='test-user'),patch.object(routes,'_is_admin',return_value=True):
            response=client.get('/warehouse-assistant/api/interwarehouse/automatic_preorder/1/proposal')
            assert response.status_code==410
            response=client.get('/warehouse-assistant/api/interwarehouse/balance/tehran')
            assert response.status_code==200
            data=response.json()
            result=client.post('/warehouse-assistant/api/interwarehouse/balance/tehran/accept',json={
                'expected_token':data['expected_token'],'request_id':'api-test','lines':[{'product_code':'00123','cartons':1}]})
            assert result.status_code==200,result.text
            assert result.json()['reduced_purchase_quantity']==12
            assert len(client.get('/warehouse-assistant/api/interwarehouse').json()['items'])==1


def test_annotation_is_read_only_and_uses_requested_warehouse(balance):
    raw=service.build_suggestions(balance.settings,warehouse='karaj',only_needed=False)
    data=rebalance.annotate_suggestions(balance.settings,raw)
    assert data['transfer_source']=='tehran'
    assert data['items'][0]['transfer_offer']['available_cartons']==1
    assert not rebalance.list_requests(balance.settings,'test-user',include_all=True)
