from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_warehouse_supplier_portal import store
from test_warehouse_portal_access import shared
from app import warehouse_supplier_portal as portal
from app import warehouse_assistant_service as service
from app.routes.warehouse_supplier_portal import public_router
import pytest


def test_summary_list_does_not_load_order_details_or_mark_viewed(shared, monkeypatch):
    settings, group, manager, worker, assignments = shared
    expected = [{k: row[k] for k in ('id', 'status', 'document', 'delivery_date',
                'requested_delivery_date', 'proposed_delivery_date')}
                for row in portal.list_assignments(settings, account_id=manager['id'])]
    def no_details(*args, **kwargs):
        raise AssertionError('Listing must not hydrate order lines or inventory snapshots')
    monkeypatch.setattr(portal, '_document', no_details)
    app = FastAPI(); app.state.settings = settings; app.include_router(public_router)
    with TestClient(app) as client:
        client.post('/supplier-portal/api/login', json={'username':manager['username'],'password':'1'})
        response = client.get('/supplier-portal/api/orders')
        assert response.status_code == 200
        assert response.json()['orders'] == expected
        assert response.headers['cache-control'] == 'no-store'
    with service.warehouse_connection(settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_portal_publications WHERE first_viewed_at IS NOT NULL').fetchone()[0] == 0


def test_summary_skips_unavailable_sources_without_hiding_valid_orders(shared):
    settings, group, manager, worker, assignments = shared
    with service.warehouse_connection(settings) as conn:
        conn.execute("UPDATE supplier_orders SET status='cancelled' WHERE id=2")
        conn.execute("UPDATE warehouse_portal_publications SET withdrawn_at='2026-09-12' WHERE assignment_id=?", (assignments[2]['id'],))
        # Legacy assignments without a publication record also remain supported.
        conn.execute("INSERT OR IGNORE INTO warehouse_portal_publications(assignment_id,epoch,published_at,published_by,withdrawn_at) VALUES(?,1,'2026-09-12','test','2026-09-12')",(assignments[2]['id'],))
    rows = portal.list_assignment_summaries(settings, account_id=manager['id'])
    assert {row['id'] for row in rows} == {assignments[0]['id'], assignments[3]['id']}
    assert portal.list_assignment_summaries(settings, account_id=worker['id']) == []


def test_detail_uses_saved_lines_and_preserves_first_view_and_scope(shared, monkeypatch):
    settings, group, manager, worker, assignments = shared
    expected = portal.get_assignment(settings, assignments[0]['id'], account_id=manager['id'])
    def no_details(*args, **kwargs):
        raise AssertionError('Supplier detail must not recalculate inventory and forecasts')
    monkeypatch.setattr(portal, '_document', no_details)
    app = FastAPI(); app.state.settings = settings; app.include_router(public_router)
    with TestClient(app) as client:
        client.post('/supplier-portal/api/login', json={'username':manager['username'],'password':'1'})
        response = client.get(f"/supplier-portal/api/orders/{assignments[0]['id']}")
        assert response.status_code == 200
        actual = response.json()
        assert response.headers['cache-control'] == 'no-store'
        assert actual['first_viewed_at']
        assert actual['document'] == expected['document']
        assert len(actual['lines']) == len(expected['lines'])
        for got, want in zip(actual['lines'], expected['lines']):
            assert got == {key: want[key] for key in got}
        client.post('/supplier-portal/api/login', json={'username':worker['username'],'password':'1'})
        assert client.get(f"/supplier-portal/api/orders/{assignments[0]['id']}").status_code == 409


@pytest.mark.parametrize('kind', ['supplier_order', 'automatic_preorder'])
def test_supplier_document_matches_saved_content_without_inventory(store, monkeypatch, kind):
    with service.warehouse_connection(store) as conn:
        document_id = 1 if kind == 'supplier_order' else conn.execute(
            'SELECT id FROM warehouse_automatic_preorders WHERE source_supplier_order_id=1').fetchone()['id']
    expected = portal._document(store, kind, document_id)
    def no_inventory(*args, **kwargs):
        raise AssertionError('Inventory hydration is not needed for supplier viewing')
    monkeypatch.setattr(portal, 'get_supplier_order', no_inventory)
    monkeypatch.setattr(portal, 'get_automatic_preorder', no_inventory)
    actual = portal._supplier_document(store, kind, document_id)
    for key in ('number', 'warehouse_code', 'snapshot_id', 'total_quantity', 'contact_email'):
        assert actual[key] == expected[key]
    assert len(actual['lines']) == len(expected['lines'])
    for got, want in zip(actual['lines'], expected['lines']):
        assert got == {key: want[key] for key in got}


def test_light_detail_keeps_removed_response_lines(store):
    assignment = portal.create_assignment(store, 'buyer', document_kind='supplier_order',
        document_id=1, requested_delivery_date='1405/06/25')
    with service.warehouse_connection(store) as conn:
        conn.execute("""UPDATE warehouse_supplier_portal_response_lines
            SET proposed_cartons=0,line_status='unavailable',supplier_note='ناموجود'
            WHERE assignment_id=? AND product_code='00456'""", (assignment['id'],))
        conn.execute("DELETE FROM supplier_order_lines WHERE order_id=1 AND product_code='00456'")
    actual = portal.get_assignment(store, assignment['id'], supplier_view=True)
    removed = next(line for line in actual['lines'] if line['product_code'] == '00456')
    assert removed['product_name'] == 'کالای دوم'
    assert removed['barcode'] == '626000000002'
    assert removed['original_cartons'] == 1
    assert removed['proposed_cartons'] == 0
