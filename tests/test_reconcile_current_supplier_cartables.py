import pytest
from test_warehouse_supplier_portal import store
from app import warehouse_supplier_portal as portal, warehouse_assistant_service as service
from scripts.reconcile_current_supplier_cartables import inspect_all, publish_reviewed


def ready(store):
    portal.create_account(store,'buyer',username='09120000000',password='1',
                          supplier_name='تأمین‌کننده نمونه',mobile='09120000000')
    with service.warehouse_connection(store) as conn:
        return inspect_all(conn)[0]


def test_manual_projection_published_once_without_notifications(store):
    review=ready(store)
    assert review['reason']=='ready' and review['kind']=='supplier_order'
    result=publish_reviewed(store,review,'1405/06/22','tester')
    actual=portal.get_assignment(store,result['assignment_id'],staff=True)
    assert actual['requested_delivery_date']=='1405/06/22'
    assert actual['workflow_status']=='awaiting_supplier'
    assert actual['notification_status']=='not_sent'
    assert actual['can_withdraw']
    with service.warehouse_connection(store) as conn:
        assert inspect_all(conn)[0]['reason']=='already_in_portal'
        assert conn.execute('SELECT COUNT(*) FROM warehouse_supplier_portal_assignments').fetchone()[0]==1
        assert conn.execute('SELECT total_quantity FROM supplier_orders WHERE id=1').fetchone()[0]==36
    with pytest.raises(service.WarehouseAssistantError):
        publish_reviewed(store,review,'1405/06/22','tester')


def test_receipt_arriving_after_review_blocks_publication(store):
    review=ready(store)
    with service.warehouse_connection(store) as conn:
        conn.execute('''INSERT INTO warehouse_fulfillment_receipts
            (preorder_id,product_code,quantity,snapshot_id,reference,recorded_by,recorded_at)
            VALUES(?,?,1,1,'fixture','tester','now')''',(review['preorder_id'],'00123'))
        assert inspect_all(conn)[0]['reason']=='receipt_activity_needs_review'
    with pytest.raises(service.WarehouseAssistantError):
        publish_reviewed(store,review,'1405/06/22','tester')


def test_revoked_approval_is_not_published(store):
    review=ready(store)
    service.transition_supplier_order(store,'buyer',1,'revoke_approval',include_all=True)
    with pytest.raises(service.WarehouseAssistantError):
        publish_reviewed(store,review,'1405/06/22','tester')
    with service.warehouse_connection(store) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_supplier_portal_assignments').fetchone()[0]==0


def test_missing_phone_and_existing_date_are_not_guessed(store):
    portal._init(store)
    with service.warehouse_connection(store) as conn:
        assert inspect_all(conn)[0]['reason']=='missing_mobile'
    ready(store)
    from app.warehouse_order_delivery import update_delivery_date
    doc=service.get_supplier_order(store,1,'buyer',include_all=True)
    update_delivery_date(store,'buyer','supplier_order',1,'1405/06/25',expected_token=doc['email_send_token'],include_all=True)
    with service.warehouse_connection(store) as conn:
        review=inspect_all(conn)[0]
    with pytest.raises(service.WarehouseAssistantError,match='Existing delivery date'):
        publish_reviewed(store,review,'1405/06/22','tester')


def test_account_collision_rolls_back_date_and_publication(store):
    review=ready(store)
    with service.warehouse_connection(store) as conn:
        conn.execute("UPDATE warehouse_supplier_portal_accounts SET supplier_key='different' WHERE username='09120000000'")
        # The contact remains explicitly configured for the original supplier.
        conn.execute("UPDATE warehouse_supplier_auto_order_settings SET contact_mobile='09120000000'")
    with pytest.raises(service.WarehouseAssistantError):
        publish_reviewed(store,review,'1405/06/22','tester')
    with service.warehouse_connection(store) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_supplier_portal_assignments').fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM warehouse_order_delivery_dates').fetchone()[0]==0
