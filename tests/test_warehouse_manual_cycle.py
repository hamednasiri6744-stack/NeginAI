"""Manual cycle override contract: temporary SQLite, no ERP or delivery."""
import pytest
from app import warehouse_assistant_service as service
from app.warehouse_order_receipts import ensure_orderable


@pytest.fixture
def stock(settings):
    service.init_warehouse_store(settings)
    with service.warehouse_connection(settings) as conn:
        conn.execute("""INSERT INTO warehouse_snapshots(id,source_filename,source_sheet,content_sha256,
            product_count,item_count,imported_by,imported_at,period_days)
            VALUES(1,'test','test','manual-cycle',1,2,'test','2099-01-01T00:00:00+00:00',60)""")
        for warehouse in ('karaj', 'tehran'):
            conn.execute("""INSERT INTO warehouse_snapshot_items(snapshot_id,source_row,warehouse_code,
                warehouse_name,product_code,product_name,conversion_rate,manufacturer,brand,period_out,
                ordering_cycle_active) VALUES(1,1,?,?,'00123','Test item',12,'Supplier','Brand',120,1)""",
                (warehouse, warehouse))
    return settings


def override(settings, mode):
    return service.save_order_cycle_override(settings, 'tester', warehouse='karaj', product_code='00123', mode=mode)


def suggestions(settings, warehouse='karaj'):
    return service.build_suggestions(settings, warehouse=warehouse, only_needed=False)


def test_manual_exclusion_wins_over_system_and_is_warehouse_scoped(stock):
    assert len(suggestions(stock)['items']) == 1
    result=override(stock,'force_inactive')
    assert result['system_ordering_cycle_active'] is True
    assert result['order_cycle_forced_inactive'] is True
    assert result['ordering_cycle_active'] is False
    assert suggestions(stock)['items'] == []
    assert suggestions(stock)['summary']['excluded_manual_items'] == 1
    assert suggestions(stock)['summary']['excluded_stale_items'] == 0
    assert len(suggestions(stock,'tehran')['items']) == 1
    inventory=service.list_inventory_information(stock, warehouse='karaj')
    assert inventory['items'][0]['order_cycle_forced_inactive'] is True
    assert inventory['items'][0]['ordering_cycle_active'] is False
    assert inventory['summary']['out_of_cycle_items'] == 1


def test_manual_block_survives_reinitialization_and_snapshot_refresh(stock):
    override(stock,'force_inactive')
    service.init_warehouse_store(stock)
    with service.warehouse_connection(stock) as conn:
        conn.execute("""INSERT INTO warehouse_snapshots(id,source_filename,source_sheet,content_sha256,
            product_count,item_count,imported_by,imported_at,period_days)
            VALUES(2,'new','test','new-cycle',1,2,'test','2099-01-02T00:00:00+00:00',60)""")
        conn.execute("UPDATE warehouse_snapshot_items SET snapshot_id=2")
        conn.execute("UPDATE warehouse_snapshot_items SET stock=100,ordering_cycle_active=1")
        assert conn.execute("SELECT forced_active FROM warehouse_order_cycle_overrides").fetchone()[0] == 0
    assert suggestions(stock)['items'] == []


@pytest.mark.parametrize('mode', ['system','force_active'])
def test_exclusion_is_reversible_without_changing_system_state(stock,mode):
    override(stock,'force_inactive')
    result=override(stock,mode)
    assert result['order_cycle_forced_inactive'] is False
    assert result['ordering_cycle_active'] is True
    assert len(suggestions(stock)['items']) == 1


def test_direct_order_and_existing_order_send_guard_reject_excluded_item(stock):
    override(stock,'force_inactive')
    with pytest.raises(service.WarehouseAssistantError,match='خارج از چرخه'):
        service.create_supplier_orders(stock,'tester',snapshot_id=1,warehouse='karaj',lines=[{'product_code':'00123','quantity':12}])
    with service.warehouse_connection(stock) as conn:
        with pytest.raises(service.WarehouseAssistantError,match='خارج از چرخه'):
            ensure_orderable(conn,'karaj',['00123'])
        ensure_orderable(conn,'tehran',['00123'])


def test_automatic_preparation_omits_manually_excluded_item(stock):
    baseline=service.prepare_automatic_preorders(stock,'tester')
    assert any(order['warehouse_code']=='karaj' for order in baseline['preorders'])
    override(stock,'force_inactive')
    result=service.prepare_automatic_preorders(stock,'tester')
    assert all(not (order['warehouse_code']=='karaj' and any(line['product_code']=='00123' for line in order['lines'])) for order in result['preorders'])


def test_manual_order_approval_rechecks_cycle_but_preserves_history(stock):
    result=service.create_supplier_orders(stock,'tester',snapshot_id=1,warehouse='karaj',lines=[{'product_code':'00123','quantity':12}])
    order_id=result[0]['id']
    override(stock,'force_inactive')
    with pytest.raises(service.WarehouseAssistantError,match='خارج از چرخه'):
        service.transition_supplier_order(stock,'tester',order_id,'approve')
    order=service.get_supplier_order(stock,order_id,'tester')
    assert order['lines'][0]['product_code']=='00123'
    assert order['is_approved'] is False


def test_sms_link_is_blocked_before_external_delivery(stock,monkeypatch):
    from app import warehouse_order_sms as sms
    order=service.create_supplier_orders(stock,'tester',snapshot_id=1,warehouse='karaj',lines=[{'product_code':'00123','quantity':12}])[0]
    override(stock,'force_inactive')
    calls=[]
    monkeypatch.setattr(sms,'_provider_config',lambda:{})
    monkeypatch.setattr(sms,'_send_provider',lambda *args:calls.append(args))
    with pytest.raises(service.WarehouseAssistantError,match='خارج از چرخه'):
        sms.send_document_link(stock,'tester',document_kind='supplier_order',document_id=order['id'],
            order_number=order['order_number'],supplier='Supplier',mobile='09121112233',filename='test.xlsx',content=b'test')
    assert calls == []


def test_automatic_existing_draft_cannot_be_approved_after_exclusion(stock):
    orders=service.prepare_automatic_preorders(stock,'tester')['preorders']
    order=next(order for order in orders if order['warehouse_code']=='karaj')
    override(stock,'force_inactive')
    with pytest.raises(service.WarehouseAssistantError,match='خارج از چرخه'):
        service.transition_automatic_preorder(stock,'tester',order['id'],'approve')


def test_api_accepts_manual_exclusion_and_rejects_unknown_mode(client,stock):
    from test_warehouse_assistant import _session
    headers=_session(stock,'CycleAdmin','Admin')
    response=client.put('/warehouse-assistant/api/inventory/order-cycle',headers=headers,
        json={'warehouse':'karaj','product_code':'00123','mode':'force_inactive'})
    assert response.status_code == 200, response.text
    assert response.json()['ordering_cycle_active'] is False
    invalid=client.put('/warehouse-assistant/api/inventory/order-cycle',headers=headers,
        json={'warehouse':'karaj','product_code':'00123','mode':'other'})
    assert invalid.status_code == 422
