"""Supply pipeline checks: isolated database and fake SMTP, never live orders."""
import pytest
import test_warehouse_email as email_tests
from app import warehouse_assistant_service as service
from app import warehouse_fulfillment as fulfillment
from app import warehouse_supplier_portal as supplier_portal


@pytest.fixture
def case():
    value = email_tests.WarehouseEmailTests()
    value.setUp()
    with service.warehouse_connection(value.settings) as conn:
        conn.execute("UPDATE warehouse_snapshots SET period_days=60, imported_at='2099-01-01T00:00:00+00:00'")
        conn.execute("UPDATE warehouse_automatic_preorders SET approved_at='2026-01-01T00:00:00+00:00'")
        conn.execute("""INSERT INTO warehouse_snapshot_items(snapshot_id,source_row,warehouse_code,
            warehouse_name,product_code,product_name,conversion_rate,manufacturer,brand,period_out)
            VALUES(1,1,'karaj','Karaj','00123','Test',12,'supplier','brand',120)""")
    yield value
    value.doCleanups()


def suggestion(case):
    return service.build_suggestions(case.settings, warehouse='karaj', target_days=30,
        reorder_coverage_days=15, only_needed=False)['items'][0]


def test_sent_order_reduces_new_purchase_not_physical_stock(case):
    initial = suggestion(case)
    assert initial['in_transit_qty'] == 24
    assert initial['suggested_quantity'] == 36
    case.send()
    item = suggestion(case)
    assert item['in_transit_qty'] == 24
    assert item['effective_procurement_qty'] == 0
    assert item['inventory_position_qty'] == 24
    assert item['suggested_quantity'] == 36
    assert service.list_automatic_preorders(case.settings) == []


def test_fulfillment_lines_keep_all_product_identity_fields(case):
    case.change("UPDATE warehouse_snapshot_items SET manufacturer_product_code='M-123',barcode='6261234567890',group_level3='دستمال'")
    case.send()
    line=fulfillment.list_fulfillment_orders(case.settings)[0]['fulfillment']['lines'][0]
    assert (line['manufacturer_product_code'],line['barcode'],line['group_level3']) == ('M-123','6261234567890','دستمال')


def test_manual_fulfillment_uses_original_supplier_order_portal_status(case):
    supplier_portal._init(case.settings)
    with service.warehouse_connection(case.settings) as conn:
        # This focused serializer fixture does not need a complete manual-order
        # document; the projection id is enough to prove status-key selection.
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("UPDATE warehouse_automatic_preorders SET source_supplier_order_id=77")
        conn.execute("""INSERT INTO warehouse_supplier_portal_assignments
            (document_kind,document_id,supplier_name,supplier_key,requested_delivery_date,
             proposed_delivery_date,status,created_by,created_at,updated_at)
            VALUES('supplier_order',77,'supplier','supplier','1405/06/20','1405/06/20',
                   'accepted','buyer','now','now')""")
    order = fulfillment.list_fulfillment_orders(case.settings)[0]
    assert order['supplier_portal']['status'] == 'accepted'


def test_approved_or_failed_dispatch_remains_in_transit(case):
    case.change("UPDATE warehouse_automatic_preorders SET status='send_requested'")
    assert suggestion(case)['in_transit_qty'] == 24
    case.transport.side_effect = email_tests.mail.MailDeliveryFailure('failed','rejected')
    case.send()
    assert suggestion(case)['in_transit_qty'] == 24
    assert service.list_inventory_information(case.settings)['items'][0]['in_transit_qty'] == 24


def test_inventory_basis_tracks_sent_partial_and_full_receipts_live(case):
    def item():
        return service.list_inventory_information(case.settings, warehouse='karaj')['items'][0]
    assert item()['in_transit_qty'] == 24
    case.send()
    row = item()
    assert (row['on_hand_qty'], row['in_transit_qty'], row['effective_procurement_qty']) == (0, 24, 24)
    case.change('UPDATE warehouse_snapshot_items SET stock=12')
    partial = receive(case, 12)
    row = item()
    assert (row['on_hand_qty'], row['in_transit_qty'], row['effective_procurement_qty']) == (12, 12, 24)
    assert row['effective_procurement_qty'] == suggestion(case)['inventory_position_qty']
    case.change('UPDATE warehouse_snapshot_items SET stock=24')
    receive(case, 24, partial['revision'])
    row = item()
    assert (row['on_hand_qty'], row['in_transit_qty'], row['effective_procurement_qty']) == (24, 0, 24)


def test_inventory_in_transit_filters_totals_before_pagination_and_isolates_warehouse(case):
    case.send()
    result = service.list_inventory_information(case.settings, limit=1, offset=1,
        column_filters={'in_transit_qty': '۲۴', 'effective_procurement_qty': '٢٤'})
    assert result['items'] == []
    assert result['summary']['total_items'] == 1
    assert result['summary']['in_transit_qty'] == 24
    assert result['summary']['effective_procurement_qty'] == 24
    case.change("UPDATE warehouse_automatic_preorders SET warehouse_code='tehran'")
    result = service.list_inventory_information(case.settings, warehouse='karaj')
    assert result['items'][0]['in_transit_qty'] == 0
    assert result['summary']['in_transit_qty'] == 0


def test_delete_keeps_lines_and_allows_next_rebuild(case):
    deleted = service.transition_automatic_preorder(case.settings,'test',1,'delete')
    assert deleted['status'] == 'cancelled'
    assert len(deleted['lines']) == 1
    assert service.list_automatic_preorders(case.settings) == []
    result = service.prepare_automatic_preorders(case.settings,'test')
    assert result['created_count'] == 1
    assert result['preorders'][0]['id'] != 1


def test_sent_order_cannot_be_deleted(case):
    case.send()
    with pytest.raises(service.WarehouseAssistantError):
        service.transition_automatic_preorder(case.settings,'test',1,'delete')


def receive(case, total, revision=0, **kwargs):
    return fulfillment.receive_fulfillment(case.settings,'receiver',1,
        expected_revision=revision,snapshot_id=1,inventory_reflected=True,
        reference='ERP-123',lines=[{'product_code':'00123','received_qty':total}],**kwargs)


def test_partial_receipt_only_subtracts_outstanding_and_preserves_stock(case):
    case.send()
    # ERP snapshot now contains 12 received units; receiving must not add stock again.
    case.change('UPDATE warehouse_snapshot_items SET stock=12')
    result = receive(case, 12)
    assert result['remaining_qty'] == 12
    assert result['status'] == 'awaiting_supply'
    item = suggestion(case)
    assert item['effective_procurement_qty'] == 12
    assert item['in_transit_qty'] == 12
    assert item['suggested_quantity'] == 36
    with pytest.raises(service.WarehouseAssistantError):
        receive(case,12)  # stale confirmation cannot apply twice
    result = receive(case,24,result['revision'])
    assert result['status'] == 'received'
    assert fulfillment.list_fulfillment_orders(case.settings) == []
    assert len(fulfillment.list_fulfillment_orders(case.settings,True)) == 1


def test_receipt_rejects_excess_missing_erp_confirmation_and_stale_snapshot(case):
    case.send()
    with pytest.raises(service.WarehouseAssistantError): receive(case,25)
    with pytest.raises(service.WarehouseAssistantError):
        fulfillment.receive_fulfillment(case.settings,'r',1,expected_revision=0,snapshot_id=1,
            inventory_reflected=False,reference='ERP',lines=[{'product_code':'00123','received_qty':12}])
    case.change("UPDATE warehouse_snapshots SET imported_at='2000-01-01T00:00:00+00:00'")
    with pytest.raises(service.WarehouseAssistantError): receive(case,12)
    assert suggestion(case)['in_transit_qty'] == 24


def test_in_transit_crosses_business_days_but_not_warehouses(case):
    case.send()
    case.change("UPDATE warehouse_automatic_preorders SET business_date='1400/01/01'")
    assert len(fulfillment.list_fulfillment_orders(case.settings)) == 1
    assert suggestion(case)['in_transit_qty'] == 24
    case.change("UPDATE warehouse_automatic_preorders SET warehouse_code='tehran'")
    assert suggestion(case)['in_transit_qty'] == 0


def test_successful_send_does_not_block_additional_same_day_requirement(case):
    case.send()
    case.change('UPDATE warehouse_supplier_auto_order_settings SET reorder_coverage_days=15,target_days=30')
    result = service.prepare_automatic_preorders(case.settings,'test')
    assert result['created_count'] == 1
    assert result['preorders'][0]['total_cartons'] == 3  # 60-unit target minus 24 = 36 -> 3 cartons
    line = result['preorders'][0]['lines'][0]
    assert (line['physical_procurement_qty'], line['in_transit_qty'],
            line['pending_receipt_qty'], line['inventory_position_qty']) == (0, 24, 0, 24)
    assert (line['sales_rate_days'], line['period_out_qty'], line['coverage_days']) == (60, 120, 12)
    assert case.order()['status'] == 'send_requested'


def test_supply_change_mid_calculation_aborts_before_overwriting_drafts(case, monkeypatch):
    case.change("UPDATE warehouse_automatic_preorders SET status='awaiting_approval',approved_at=NULL")
    original = service.build_suggestions
    before = case.order()
    def calculate_and_approve(*args, **kwargs):
        result = original(*args, **kwargs)
        service.transition_automatic_preorder(case.settings, 'test', 1, 'approve')
        return result
    monkeypatch.setattr(service, 'build_suggestions', calculate_and_approve)
    with pytest.raises(service.WarehouseAssistantError):
        service.prepare_automatic_preorders(case.settings, 'test')
    after = case.order()
    persisted = ('product_code', 'cartons', 'order_quantity', 'system_suggested_cartons',
                 'unadjusted_suggested_cartons', 'approximate_price', 'estimated_value')
    assert [{key: line[key] for key in persisted} for line in after['lines']] == [
        {key: line[key] for key in persisted} for line in before['lines']
    ]
    assert after['lines'][0]['in_transit_qty'] == 24
    assert case.order()['status'] == 'approved'


def test_receive_routes_require_permission_and_preserve_erp(case):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes.warehouse_assistant import router
    from app.auth_service import create_user, create_session
    from app.database import init_sqlite, sqlite_connection
    from unittest.mock import patch
    case.settings.action_api_key='test'
    case.settings.login_username=''
    init_sqlite(case.settings.sqlite_path)
    create_user(case.settings,'Admin','TestOnlyPass9')
    with sqlite_connection(case.settings.sqlite_path) as conn:
        conn.execute("UPDATE users SET role='Admin' WHERE username='Admin'")
    app=FastAPI();app.state.settings=case.settings;app.include_router(router)
    with TestClient(app) as client:
        url='/warehouse-assistant/api/fulfillment-orders/1/receive'
        assert client.post(url,json={}).status_code==401
        client.cookies.set('negin_session',create_session(case.settings,'Admin'))
        with patch('app.routes.warehouse_assistant._capabilities',return_value=set()):
            assert client.get('/warehouse-assistant/api/fulfillment-orders').status_code==403
        case.send()
        payload=dict(expected_revision=0,snapshot_id=1,inventory_reflected=True,reference='ERP-1',
            lines=[dict(product_code='00123',received_qty=12)])
        response=client.post(url,json=payload)
        assert response.status_code==200,response.text
        assert response.json()['fulfillment']['remaining_qty']==12
        assert response.json()['varanegar_write'] is False
        assert client.post(url,json=payload).status_code>=400
        assert client.post('/warehouse-assistant/api/automatic-preorders/1/delete').status_code>=400
