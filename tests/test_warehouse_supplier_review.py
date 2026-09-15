import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_warehouse_supplier_portal import store
from test_warehouse_order_stages import setup_order, doc
from app import warehouse_supplier_portal as portal
from app.routes import warehouse_supplier_portal as routes


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
@pytest.mark.parametrize('change', ['date', 'quantity', 'both'])
def test_review_in_warehouse_preserves_order_until_staff_accepts(store, monkeypatch, kind, change):
    assignment = setup_order(store, kind)
    profile = portal.authenticate(store, 'supplier.workflow', 'Fixture-only-123')[1]
    date = '1405/06/27' if change != 'quantity' else '1405/06/25'
    cartons = 3 if change != 'date' else 2
    proposal = portal.save_response(store, profile, assignment['id'], expected_revision=assignment['revision'],
        proposed_delivery_date=date, supplier_comment='درخواست تغییر', submit=True,
        lines=[{'product_code':'00123','proposed_cartons':cartons},{'product_code':'00456','proposed_cartons':1}])
    assert proposal['status'] == 'submitted'
    current = doc(store, kind)
    assert current['order_stage'] == 'sent'
    assert current['supplier_portal']['pending_quantity_changes'] == (0 if change == 'date' else 1)
    assert current['delivery_date'] == '1405/06/25'
    assert next(l for l in current['lines'] if l['product_code']=='00123')['cartons'] == 2
    app = FastAPI(); app.state.settings = store; app.include_router(routes.staff_router)
    app.dependency_overrides[routes.require_session_user] = lambda: 'buyer'
    monkeypatch.setattr(routes, '_staff', lambda request: 'buyer')
    with TestClient(app) as client:
        path = f'/warehouse-assistant/api/supplier-portal/orders/{assignment["id"]}'
        response = client.get(path)
        assert response.status_code == 200
        review = response.json()
        assert review['proposed_delivery_date'] == date
        line = next(l for l in review['lines'] if l['product_code']=='00123')
        assert (line['original_cartons'], line['proposed_cartons']) == (2, cartons)
        payload = {'decision':'accept','expected_revision':review['revision'],'manager_comment':'تأیید انبار'}
        assert client.post(path+'/decision',json={**payload,'expected_revision':review['revision']-1}).status_code == 409
        assert doc(store,kind)['order_stage'] == 'sent'
        assert client.post(path+'/decision',json=payload).status_code == 200
        assert client.post(path+'/decision',json=payload).status_code == 409
    current = doc(store,kind)
    assert current['order_stage'] == 'delivery'
    assert current['supplier_portal']['pending_quantity_changes'] == 0
    assert current['delivery_date'] == date
    assert next(l for l in current['lines'] if l['product_code']=='00123')['cartons'] == cartons
