import sqlite3
import pytest
from test_warehouse_supplier_portal import store
from test_warehouse_order_stages import setup_order, doc
from app import warehouse_supplier_portal as portal, warehouse_assistant_service as service


def proposal(store, kind, quantity=True):
    assignment=setup_order(store,kind)
    with service.warehouse_connection(store) as conn:
        conn.execute("UPDATE warehouse_automatic_preorders SET business_date='1405/06/17',status='send_requested' WHERE id=1")
    profile=portal.authenticate(store,'supplier.workflow','Fixture-only-123')[1]
    return portal.save_response(store,profile,assignment['id'],expected_revision=assignment['revision'],
        proposed_delivery_date='1405/06/27',supplier_comment='',submit=True,
        lines=[{'product_code':'00123','proposed_cartons':3 if quantity else 2},{'product_code':'00456','proposed_cartons':1}])


@pytest.mark.parametrize('quantity',[False,True])
def test_old_sent_order_response_can_be_accepted_without_reapproving(store,quantity):
    response=proposal(store,'automatic_preorder',quantity)
    portal.decide(store,'buyer',response['id'],decision='accept',expected_revision=response['revision'])
    current=doc(store,'automatic_preorder')
    assert current['status']=='send_requested'
    assert current['business_date']=='1405/06/17'
    assert current['delivery_date']=='1405/06/27'
    assert current['order_stage']=='delivery'
    assert next(l for l in current['lines'] if l['product_code']=='00123')['cartons']==(3 if quantity else 2)


@pytest.mark.parametrize('kind',['supplier_order','automatic_preorder'])
def test_failed_decision_rolls_back_quantities_and_response_together(store,kind):
    response=proposal(store,kind)
    with service.warehouse_connection(store) as conn:
        conn.execute("CREATE TRIGGER fail_accept BEFORE UPDATE OF status ON warehouse_supplier_portal_assignments WHEN NEW.status='accepted' BEGIN SELECT RAISE(ABORT,'fixture decision failure'); END")
    with pytest.raises((sqlite3.IntegrityError,service.WarehouseAssistantError)):
        portal.decide(store,'buyer',response['id'],decision='accept',expected_revision=response['revision'])
    current=doc(store,kind)
    assert current['delivery_date']=='1405/06/25'
    assert next(l for l in current['lines'] if l['product_code']=='00123')['cartons']==2
    after=portal.get_assignment(store,response['id'],staff=True)
    assert after['status']=='submitted' and after['revision']==response['revision']


def test_old_unapproved_draft_still_cannot_be_approved_normally(store):
    with service.warehouse_connection(store) as conn:
        conn.execute("UPDATE warehouse_automatic_preorders SET source_supplier_order_id=NULL,business_date='1405/06/17',status='awaiting_approval' WHERE id=1")
    with pytest.raises(service.WarehouseAssistantError,match='روز جاری'):
        service.transition_automatic_preorder(store,'buyer',1,'approve')


def test_date_only_does_not_rewrite_quantity_metadata(store):
    response=proposal(store,'automatic_preorder',False)
    before=doc(store,'automatic_preorder')
    portal.decide(store,'buyer',response['id'],decision='accept',expected_revision=response['revision'])
    after=doc(store,'automatic_preorder')
    assert (after.get('edited_at'),after.get('edited_by'))==(before.get('edited_at'),before.get('edited_by'))


def test_changed_source_is_not_silently_overwritten(store):
    response=proposal(store,'automatic_preorder')
    with service.warehouse_connection(store) as conn:
        conn.execute("UPDATE warehouse_automatic_preorder_lines SET cartons=4 WHERE preorder_id=1 AND product_code='00123'")
    with pytest.raises(service.WarehouseAssistantError,match='تعداد سفارش اصلی'):
        portal.decide(store,'buyer',response['id'],decision='accept',expected_revision=response['revision'])
    assert portal.get_assignment(store,response['id'],staff=True)['status']=='submitted'
