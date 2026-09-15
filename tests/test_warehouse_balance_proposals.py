"""Independent balancing proposals; isolated SQLite, never ERP."""
import pytest
from test_warehouse_rebalancing import balance
from test_warehouse_fulfillment import case
from app import warehouse_rebalancing as rebalance
from app import warehouse_assistant_service as service


def preview(case, source='tehran', destination=None):
    return rebalance.balance_preview(case.settings, 'test-user', source, destination=destination, include_all=True)


def accept(case, data, cartons=None, key='balance'):
    row=data['lines'][0]
    return rebalance.accept_balance(case.settings, 'test-user', data['source'],
        [{'product_code':row['product_code'],'cartons':cartons or row['available_cartons']}],
        expected_token=data['expected_token'],request_id=key,destination=data['destination'],include_all=True)


def add_gilan(balance):
    with service.warehouse_connection(balance.settings) as conn:
        item=dict(conn.execute("SELECT * FROM warehouse_snapshot_items WHERE warehouse_code='tehran'").fetchone())
        item.pop('id',None);item.update(warehouse_code='gilan',warehouse_name='Gilan',source_row=3,stock=0)
        conn.execute(f'INSERT INTO warehouse_snapshot_items({",".join(item)}) VALUES({",".join("?" for _ in item)})',tuple(item.values()))


@pytest.mark.parametrize('source,destination',[(s,d) for s in ('tehran','karaj','gilan') for d in ('tehran','karaj','gilan') if s!=d])
def test_all_six_routes_keep_identity_and_inbound_separate(balance,source,destination):
    add_gilan(balance)
    balance.change('UPDATE warehouse_snapshot_items SET stock=0')
    balance.change(f"UPDATE warehouse_snapshot_items SET stock=112 WHERE warehouse_code='{source}'")
    if destination=='gilan':
        balance.change("UPDATE warehouse_snapshot_items SET stock=60 WHERE warehouse_code IN ('tehran','karaj')")
        balance.change(f"UPDATE warehouse_snapshot_items SET stock=120 WHERE warehouse_code='{source}'")
    balance.change("UPDATE warehouse_snapshot_items SET brand='Trade name',manufacturer='Maker'")
    data=preview(balance,source,destination)
    assert data['destination']==destination
    assert data['lines'][0]['brand']=='Trade name'
    count=data['lines'][0]['minimum_cartons'];units=count*12
    result=accept(balance,data,count)
    rows=rebalance.list_requests(balance.settings,'test-user',include_all=True)
    assert len(rows)==1 and rows[0]['source']==source and rows[0]['destination']==destination
    assert rows[0]['brand']=='Trade name'
    assert result['reduced_purchase_quantity']==(12 if destination=='karaj' else 0)
    with service.warehouse_connection(balance.settings) as conn:
        for warehouse in ('tehran','karaj','gilan'):
            incoming,outgoing=rebalance.reservations(conn,warehouse)[:2]
            assert incoming==({'00123':units} if warehouse==destination else {})
            assert outgoing==({'00123':units} if warehouse==source else {})
    balance.transport.assert_not_called()


def test_cross_destination_stock_is_reserved_once_and_tokens_bind_route(balance):
    add_gilan(balance)
    balance.change("UPDATE warehouse_snapshot_items SET stock=240 WHERE warehouse_code='tehran'")
    karaj=preview(balance,'tehran','karaj');gilan=preview(balance,'tehran','gilan')
    assert not gilan['lines']
    with pytest.raises(service.WarehouseAssistantError):
        accept(balance,karaj|dict(destination='gilan'),1)
    accept(balance,karaj,key='karaj')
    fresh=preview(balance,'tehran','gilan')
    with pytest.raises(service.WarehouseAssistantError):accept(balance,fresh|dict(expected_token=gilan['expected_token']),4,key='gilan')
    assert fresh['lines'][0]['source_position']==120
    accept(balance,fresh,4,key='gilan')
    with service.warehouse_connection(balance.settings) as conn:
        assert rebalance.reservations(conn,'tehran')[1]=={'00123':168}
    with pytest.raises(service.WarehouseAssistantError):accept(balance,karaj|dict(destination='gilan'),1,key='karaj')


@pytest.mark.parametrize('source,destination',[('gilan',None),('gilan','gilan'),('tehran','tehran'),('tehran','unknown'),('unknown','karaj')])
def test_invalid_routes_are_rejected(balance,source,destination):
    with pytest.raises(service.WarehouseAssistantError):preview(balance,source,destination)


def test_explicit_route_http_authorization_and_destination(balance):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.routes import warehouse_assistant as routes
    add_gilan(balance)
    balance.change("UPDATE warehouse_snapshot_items SET stock=60 WHERE warehouse_code='karaj'")
    balance.change("UPDATE warehouse_snapshot_items SET stock=120 WHERE warehouse_code='tehran'")
    app=FastAPI();app.state.settings=balance.settings;app.include_router(routes.router)
    path='/warehouse-assistant/api/interwarehouse/balance/tehran/gilan'
    data=preview(balance,'tehran','gilan')
    payload=dict(expected_token=data['expected_token'],request_id='http-route',lines=[dict(product_code='00123',cartons=4)])
    with TestClient(app) as client:
        assert client.get(path).status_code==401
        assert client.post(path+'/accept',json=payload).status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'test-user'
        with patch.object(routes,'_capabilities',return_value=set()):
            assert client.get(path).status_code==403
            assert client.post(path+'/accept',json=payload).status_code==403
        with patch.object(routes,'_require',return_value='test-user'),patch.object(routes,'_is_admin',return_value=True):
            response=client.get(path)
            assert response.status_code==200 and response.json()['destination']=='gilan'
            wrong=client.post('/warehouse-assistant/api/interwarehouse/balance/tehran/karaj/accept',json=payload)
            assert wrong.status_code>=400
            assert client.post(path+'/accept',json=payload).status_code==200
    assert rebalance.list_requests(balance.settings,'test-user',include_all=True)[0]['destination']=='gilan'


def test_equal_days_not_equal_units_and_reduce_purchase_once(balance):
    balance.change("UPDATE warehouse_snapshot_items SET stock=120 WHERE warehouse_code='tehran'")
    balance.change("UPDATE warehouse_snapshot_items SET period_out=240 WHERE warehouse_code='karaj'")
    data=preview(balance);row=data['lines'][0]
    assert row['available_cartons']==6  # 84 would leave 18 days; 72 preserves the 20-day floor.
    assert row['source_after_days']==24 and row['destination_after_days']==18
    assert data['minimum_source_days']==20
    result=accept(balance,data)
    assert result['reduced_purchase_quantity']==24
    assert balance.order()['status']=='cancelled'
    assert len(rebalance.list_requests(balance.settings,'test-user',include_all=True))==1
    assert accept(balance,data)==result
    item=service.build_suggestions(balance.settings,warehouse='karaj',only_needed=False)['items'][0]
    assert item['in_transit_qty']==72
    assert not preview(balance)['lines']
    balance.transport.assert_not_called()


@pytest.mark.parametrize('stock',[0,89,90])
def test_source_must_exceed_45_days(balance,stock):
    balance.change(f"UPDATE warehouse_snapshot_items SET stock={stock} WHERE warehouse_code='tehran'")
    assert not preview(balance)['lines']


@pytest.mark.parametrize('stock',[30,31,40])
def test_destination_at_or_above_15_days_does_not_need_transfer(balance,stock):
    balance.change(f"UPDATE warehouse_snapshot_items SET stock={stock} WHERE warehouse_code='karaj'")
    assert not preview(balance)['lines']


def test_transit_counts_and_approved_purchase_is_not_edited(balance):
    balance.change("UPDATE warehouse_automatic_preorders SET status='approved',approved_at='now'")
    data=preview(balance)
    assert data['lines'][0]['destination_before_days']==12
    accept(balance,data,1)
    assert balance.order()['total_quantity']==24


@pytest.mark.parametrize('change',[
    "UPDATE warehouse_snapshot_items SET consumer_price=99 WHERE warehouse_code='tehran'",
    "UPDATE warehouse_snapshot_items SET consumer_price=0 WHERE warehouse_code='karaj'",
    "UPDATE warehouse_snapshot_items SET conversion_rate=6 WHERE warehouse_code='tehran'",
    "UPDATE warehouse_snapshot_items SET period_out=0 WHERE warehouse_code='karaj'",
])
def test_ineligible_price_demand_or_carton_is_not_proposed(balance,change):
    balance.change(change);assert not preview(balance)['lines']


def test_stale_proposal_is_rejected_without_order_changes(balance):
    data=preview(balance)
    balance.change("UPDATE warehouse_snapshot_items SET stock=100 WHERE warehouse_code='tehran'")
    with pytest.raises(service.WarehouseAssistantError):accept(balance,data)
    assert balance.order()['total_quantity']==24
    assert not rebalance.list_requests(balance.settings,'test-user',include_all=True)


def test_manual_and_system_drafts_share_one_reduction_budget(balance):
    manual=service.create_supplier_orders(balance.settings,'test-user',snapshot_id=1,warehouse='karaj',
        lines=[{'product_code':'00123','quantity':24}],note='test')[0]
    accept(balance,preview(balance),1)
    a=balance.order()['total_quantity']
    b=service.get_supplier_order(balance.settings,manual['id'],'test-user',include_all=True)['total_quantity']
    assert a+b==36  # 48 - 12, not 48 - 24


def test_transfer_reduces_destination_immediately_and_survives_hourly_rebuild(balance):
    balance.change('UPDATE warehouse_supplier_auto_order_settings SET enabled=1,minimum_cartons=0,target_days=30,reorder_coverage_days=15')
    service.prepare_automatic_preorders(balance.settings, 'test-user')
    before = service.list_automatic_preorders(balance.settings)[0]
    assert before['total_quantity'] == 60  # 2 units/day for 30 days.
    proposal = preview(balance)
    result = accept(balance, proposal, 1)
    assert result['reduced_purchase_quantity'] == 12
    assert service.get_automatic_preorder(balance.settings, before['id'])['total_quantity'] == 48
    assert accept(balance, proposal, 1) == result
    service.prepare_automatic_preorders(balance.settings, 'system', trigger='hourly')
    after = service.list_automatic_preorders(balance.settings)
    assert len(after) == 1 and after[0]['total_quantity'] == 48
    item = service.build_suggestions(balance.settings, warehouse='karaj', only_needed=False)['items'][0]
    assert item['in_transit_qty'] == 12
    with service.warehouse_connection(balance.settings) as conn:
        assert conn.execute("SELECT stock FROM warehouse_snapshot_items WHERE warehouse_code='karaj'").fetchone()[0] == 0
    balance.transport.assert_not_called()


def test_reverse_direction_and_no_purchase_required(balance):
    balance.change("UPDATE warehouse_automatic_preorders SET status='cancelled'")
    balance.change("UPDATE warehouse_snapshot_items SET stock=120 WHERE warehouse_code='karaj'")
    balance.change("UPDATE warehouse_snapshot_items SET stock=0 WHERE warehouse_code='tehran'")
    data=preview(balance,'karaj');assert data['destination']=='tehran'
    assert accept(balance,data)['reduced_purchase_quantity']==0


def test_source_inbound_is_in_basis_but_not_available_to_ship(balance):
    balance.change("UPDATE warehouse_automatic_preorders SET warehouse_code='tehran',status='approved',approved_at='now',total_quantity=120")
    balance.change("UPDATE warehouse_automatic_preorder_lines SET warehouse_code='tehran',order_quantity=120,cartons=10")
    balance.change("UPDATE warehouse_snapshot_items SET stock=24 WHERE warehouse_code='tehran'")
    row=preview(balance)['lines'][0]
    assert row['source_position']==144 and row['source_before_days']==72
    assert row['available_cartons']==2  # planning includes inbound; shipping cannot use it
    item=service.build_suggestions(balance.settings,warehouse='tehran',only_needed=False)['items'][0]
    assert item['inventory_position_qty']==row['source_position']


def test_adjusted_forecast_and_manual_cycle_exclusion(balance):
    balance.change("UPDATE warehouse_snapshots SET demand_basis='net_sales_last_stock_window'")
    balance.change("UPDATE warehouse_snapshot_items SET period_out=60,raw_period_out=600,sales_rate_days=30")
    assert preview(balance)['lines'][0]['source_before_days']==56
    balance.change("INSERT INTO warehouse_order_cycle_overrides(warehouse_code,product_code,forced_active,updated_by,updated_at) VALUES('karaj','00123',0,'test','now')")
    assert not preview(balance)['lines']


def test_price_can_be_higher_and_equalization_can_exceed_20_days(balance):
    balance.change("UPDATE warehouse_snapshot_items SET stock=180,consumer_price=101 WHERE warehouse_code='tehran'")
    row=preview(balance)['lines'][0]
    assert row['source_after_days']==42 and row['destination_after_days']==48
    assert row['available_cartons']==8


def test_reconciliation_requires_new_snapshot_and_explicit_evidence(balance):
    accept(balance,preview(balance),1)
    row=rebalance.list_requests(balance.settings,'test-user',include_all=True)[0]
    args=dict(snapshot_id=1,source_document='OUT-1',destination_document='IN-1',confirmed=True)
    with pytest.raises(service.WarehouseAssistantError):
        rebalance.reflect_in_stock(balance.settings,'test-user',row['id'],**args)
    with service.warehouse_connection(balance.settings) as conn:
        # A newer import with both actual physical movements already reflected.
        snapshot=dict(conn.execute('SELECT * FROM warehouse_snapshots WHERE id=1').fetchone())
        snapshot['id']=2;snapshot['content_sha256']='reflected-test'
        conn.execute(f'INSERT INTO warehouse_snapshots({",".join(snapshot)}) VALUES({",".join("?" for _ in snapshot)})',tuple(snapshot.values()))
        for original in conn.execute('SELECT * FROM warehouse_snapshot_items WHERE snapshot_id=1').fetchall():
            item=dict(original);item.pop('id',None);item['snapshot_id']=2
            item['stock']+=12 if item['warehouse_code']=='karaj' else -12
            conn.execute(f'INSERT INTO warehouse_snapshot_items({",".join(item)}) VALUES({",".join("?" for _ in item)})',tuple(item.values()))
    args['snapshot_id']=2
    for change in [dict(confirmed=False),dict(destination_document=' '),dict(snapshot_id=1)]:
        with pytest.raises(service.WarehouseAssistantError):
            rebalance.reflect_in_stock(balance.settings,'test-user',row['id'],**(args|change))
    with pytest.raises(service.WarehouseAssistantError):
        rebalance.reflect_in_stock(balance.settings,'other-user',row['id'],**args)
    result=rebalance.reflect_in_stock(balance.settings,'test-user',row['id'],**args)
    assert rebalance.reflect_in_stock(balance.settings,'test-user',row['id'],**args)==result
    with service.warehouse_connection(balance.settings) as conn:
        assert rebalance.reservations(conn,'karaj')[:2]==({},{})
        assert rebalance.reservations(conn,'tehran')[:2]==({},{})
    item=service.build_suggestions(balance.settings,warehouse='karaj',only_needed=False)['items'][0]
    assert item['inventory_position_qty']==12 and item['in_transit_qty']==0
    assert rebalance.list_requests(balance.settings,'test-user')[0]['reflected_at']
    balance.transport.assert_not_called()


def test_routes_require_permissions_and_retire_inline_acceptance(balance):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from app.routes import warehouse_assistant as routes
    app=FastAPI();app.state.settings=balance.settings;app.include_router(routes.router)
    data=preview(balance)
    payload=dict(expected_token=data['expected_token'],request_id='route',lines=[dict(product_code='00123',cartons=1)])
    with TestClient(app) as client:
        assert client.get('/warehouse-assistant/api/interwarehouse/balance/tehran').status_code==401
        assert client.post('/warehouse-assistant/api/interwarehouse/balance/tehran/accept',json=payload).status_code==401
        app.dependency_overrides[routes.require_session_user]=lambda:'test-user'
        with patch.object(routes,'_capabilities',return_value=set()):
            assert client.get('/warehouse-assistant/api/interwarehouse/balance/tehran').status_code==403
            assert client.post('/warehouse-assistant/api/interwarehouse/balance/tehran/accept',json=payload).status_code==403
        with patch.object(routes,'_capabilities',return_value={'warehouse.order.draft'}):
            assert client.post('/warehouse-assistant/api/interwarehouse/requests/1/reflect',json=dict(snapshot_id=2,source_document='out',destination_document='in',confirmed=True)).status_code==403
        with patch.object(routes,'_require',return_value='test-user'),patch.object(routes,'_is_admin',return_value=True):
            assert client.post('/warehouse-assistant/api/interwarehouse/automatic_preorder/1/accept',json=payload).status_code==410
            for count in [True,1.5,0,-1]:
                assert client.post('/warehouse-assistant/api/interwarehouse/balance/tehran/accept',json=payload|dict(lines=[dict(product_code='00123',cartons=count)])).status_code==422
            assert client.get('/warehouse-assistant/api/interwarehouse/balance/unknown').status_code>=400
    assert not rebalance.list_requests(balance.settings,'test-user',include_all=True)


def test_competing_proposals_and_invalid_batch_are_atomic(balance):
    data=preview(balance)
    for lines in [[dict(product_code='00123',cartons=1),dict(product_code='absent',cartons=1)],
                  [dict(product_code='00123',cartons=1)]*2]:
        with pytest.raises(service.WarehouseAssistantError):
            rebalance.accept_balance(balance.settings,'test-user','tehran',lines,expected_token=data['expected_token'],request_id='invalid',include_all=True)
    assert balance.order()['total_quantity']==24
    assert not rebalance.list_requests(balance.settings,'test-user',include_all=True)
    accept(balance,data,1)
    with pytest.raises(service.WarehouseAssistantError):accept(balance,data,1,key='competitor')
    assert balance.order()['total_quantity']==12
    assert len(rebalance.list_requests(balance.settings,'test-user',include_all=True))==1


def test_source_floor_allows_exactly_20_days_and_rejects_one_more_carton(balance):
    balance.change("UPDATE warehouse_snapshot_items SET period_out=1200 WHERE warehouse_code='karaj'")
    data=preview(balance);row=data['lines'][0]
    assert row['available_cartons']==6 and row['source_after_days']==20
    with pytest.raises(service.WarehouseAssistantError):accept(balance,data,7)
    assert balance.order()['total_quantity']==24
    assert not rebalance.list_requests(balance.settings,'test-user',include_all=True)
    accept(balance,data,6)
    item=service.build_suggestions(balance.settings,warehouse='tehran',only_needed=False)['items'][0]
    assert item['inventory_position_qty']==40  # two per day, twenty days retained


@pytest.mark.parametrize('destination_daily',[1,2,4,10,20,100])
@pytest.mark.parametrize('source_stock',[91,112,120,181])
def test_proposal_never_crosses_source_20_day_floor(balance,destination_daily,source_stock):
    balance.change(f"UPDATE warehouse_snapshot_items SET stock={source_stock} WHERE warehouse_code='tehran'")
    balance.change(f"UPDATE warehouse_snapshot_items SET period_out={destination_daily*60} WHERE warehouse_code='karaj'")
    row=preview(balance)['lines'][0]
    assert row['source_after_days']>=20
    assert row['quantity']<=source_stock-40


def test_changed_floor_invalidates_previously_loaded_proposals(balance,monkeypatch):
    from app import warehouse_balance_proposals as proposals
    with monkeypatch.context() as old_policy:
        old_policy.setattr(proposals,'MINIMUM_SOURCE_DAYS',0)
        earlier=preview(balance)
    assert preview(balance)['expected_token']!=earlier['expected_token']
    with pytest.raises(service.WarehouseAssistantError):accept(balance,earlier,1)
    assert balance.order()['total_quantity']==24
    assert not rebalance.list_requests(balance.settings,'test-user',include_all=True)


def test_batch_transfer_persists_both_items_with_product_identity(balance):
    with service.warehouse_connection(balance.settings) as conn:
        for original in conn.execute('SELECT * FROM warehouse_snapshot_items WHERE snapshot_id=1').fetchall():
            item=dict(original);item.pop('id',None);item['product_code']='SECOND';item['source_row']+=100
            item['manufacturer']='Second maker';item['brand']='Second brand'
            conn.execute(f'INSERT INTO warehouse_snapshot_items({",".join(item)}) VALUES({",".join("?" for _ in item)})',tuple(item.values()))
    data=preview(balance);by_code={r['product_code']:r for r in data['lines']}
    assert by_code['SECOND']['manufacturer']=='Second maker' and by_code['SECOND']['brand']=='Second brand'
    lines=[dict(product_code='00123',cartons=1),dict(product_code='SECOND',cartons=2)]
    args=dict(expected_token=data['expected_token'],request_id='batch-test',include_all=True)
    result=rebalance.accept_balance(balance.settings,'test-user','tehran',lines,**args)
    assert rebalance.accept_balance(balance.settings,'test-user','tehran',lines,**args)==result
    rows=rebalance.list_requests(balance.settings,'test-user',include_all=True)
    assert len(rows)==2 and len({r['batch_id'] for r in rows})==1
    assert {r['product_code']:r['cartons'] for r in rows}=={'00123':1,'SECOND':2}
    second=next(r for r in rows if r['product_code']=='SECOND')
    assert second['manufacturer']=='Second maker' and second['brand']=='Second brand'
    assert result['reduced_purchase_quantity']==12
