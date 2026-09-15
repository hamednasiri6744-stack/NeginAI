"""Lifecycle status integrates with operator actions and stock reconciliation."""
import json
from unittest.mock import patch

import pytest
from test_warehouse_fulfillment import case
from test_warehouse_rebalancing import balance
from test_warehouse_transfer_bridge import credit
from test_warehouse_transfer_lifecycle import posted
from test_warehouse_transfer_reflection import snapshot
from test_warehouse_transfer_recovery import recoverable
from app import warehouse_assistant_service as service
from app import warehouse_transfer_bridge as bridge
from app import warehouse_transfer_lifecycle as lifecycle
from app import warehouse_transfer_reflection as reflection
from app import warehouse_rebalancing as ledger
from app.warehouse_order_receipts import pending_stock


def change(detail, read, state):
    if state == 'missing':
        detail['headers'] = []; detail['items'] = []
    elif state == 'unconfirmed':
        detail['headers'][0]['ConfirmedBy'] = None
    elif state == 'changed':
        detail['items'][0]['UnitQty'] = detail['items'][0]['TotalQty'] = 24
    elif state == 'unknown':
        read.side_effect = TimeoutError('private SQL connection details')


def reflected_snapshot(posted):
    b, doc, detail, _, _ = posted
    snapshot(b)
    with service.warehouse_connection(b.settings) as conn:
        captured = reflection.capture(conn)
        reflection.apply(conn, captured, {doc:dict(detail, status='reflected')}, 2)


@pytest.mark.parametrize('state', ['confirmed', 'missing', 'unconfirmed', 'changed', 'unknown'])
def test_status_and_list_show_current_erp_separate_from_original_sent(posted, state):
    b, doc, detail, read, original = posted
    change(detail, read, state)
    response = bridge.status(b.settings, 'test-user', doc)
    assert response['status'] == 'sent'
    assert response['result'] == json.loads(original['result_json'])
    assert response['erp']['status'] == state
    assert response['erp']['voucher_no'] == 71
    rows = ledger.list_requests(b.settings, 'test-user')
    assert len(rows) == 1
    assert rows[0]['erp_status'] == state
    assert rows[0]['erp_voucher_no'] == 71
    assert rows[0]['erp_message'] == response['erp']['message']
    assert rows[0]['erp_checked_at'] == response['erp']['checked_at']
    assert rows[0]['credit_status'] == 'sent'


@pytest.mark.parametrize('state', ['missing', 'unconfirmed', 'changed', 'unknown'])
def test_current_bad_state_prevents_destination_completion_despite_previous_reflection(posted, state):
    b, doc, detail, read, _ = posted
    reflected_snapshot(posted)
    assert bridge.status(b.settings, 'test-user', doc)['erp']['status'] == 'confirmed'
    change(detail, read, state)
    ident = ledger.list_requests(b.settings, 'test-user')[0]['id']
    with pytest.raises(service.WarehouseAssistantError, match='وضعیت فعلی بستانکار'):
        ledger.reflect_in_stock(b.settings, 'test-user', ident, snapshot_id=2,
                                source_document='71', destination_document='99', confirmed=True)
    assert read.call_count == 2  # The mutation forces a fresh read, bypassing cached confirmation.
    with service.warehouse_connection(b.settings) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_rebalance_reflections').fetchone()[0] == 0
        assert conn.execute('SELECT status FROM warehouse_transfer_source_stock_state').fetchone()[0] == 'reflected'
        # The previous source snapshot already contains the original debit; a
        # current discrepancy blocks planning instead of subtracting it twice.
        assert ledger.reservations(conn, 'tehran')[1] == {}
        assert ledger.reservations(conn, 'karaj')[0] == {'00123': 12}
        for warehouse in ('tehran', 'karaj'):
            assert reflection.review_codes(conn, warehouse) == {'00123'}
            assert pending_stock(conn, warehouse)[1] == {'00123'}


def test_confirmed_current_state_and_source_snapshot_do_not_double_subtract(posted):
    b, doc, _, _, _ = posted
    reflected_snapshot(posted)
    lifecycle.sync(b.settings, 'test-user', doc)
    with service.warehouse_connection(b.settings) as conn:
        assert ledger.reservations(conn, 'tehran')[1] == {}
        assert ledger.reservations(conn, 'karaj')[0] == {'00123': 12}
        assert reflection.review_codes(conn, 'tehran') == set()
        assert reflection.review_codes(conn, 'karaj') == set()


def test_tombstoned_document_does_not_block_future_inventory_snapshots(posted):
    b, doc, detail, read, _ = posted
    reflected_snapshot(posted)
    change(detail, read, 'missing')
    lifecycle.sync(b.settings, 'test-user', doc)
    with service.warehouse_connection(b.settings) as conn:
        conn.execute('INSERT INTO warehouse_transfer_document_deletions VALUES(?,?,?)',
                     (doc, 'test-user', service._now()))
        conn.execute('DELETE FROM warehouse_transfer_document_lines WHERE document_id=?', (doc,))
        assert reflection.capture(conn) == []
        assert reflection.review_codes(conn, 'tehran') == set()
        assert reflection.review_codes(conn, 'karaj') == set()
        assert lifecycle.get_cached(conn, doc) is None
    assert lifecycle.sync(b.settings, 'test-user') == {}
    row = ledger.list_requests(b.settings, 'test-user')[0]
    assert row['issued_document_id'] is None and row['erp_status'] is None


def test_refresh_route_checks_access_and_returns_live_status(posted):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    b, doc, detail, read, _ = posted
    app = FastAPI(); app.state.settings = b.settings; app.include_router(routes.router)
    with TestClient(app) as client:
        endpoint = f'/warehouse-assistant/api/interwarehouse/documents/{doc}/credit/refresh'
        assert client.post(endpoint).status_code == 401
        read.assert_not_called()
        app.dependency_overrides[routes.require_session_user] = lambda: 'test-user'
        with patch.object(routes, '_require', return_value='test-user') as permissions, patch.object(routes, '_is_admin', return_value=False):
            assert client.post(endpoint).json()['erp']['status'] == 'confirmed'
            detail['headers'][0]['ConfirmDate'] = None
            response = client.post(endpoint)
            assert response.status_code == 200 and response.json()['erp']['status'] == 'unconfirmed'
            assert [call.args[1] for call in permissions.call_args_list] == ['warehouse.order.draft'] * 2
            assert read.call_count == 2
        with patch.object(routes, '_require', return_value='other-user'), patch.object(routes, '_is_admin', return_value=False):
            denied = client.post(endpoint)
            assert denied.status_code == 422
            assert 'دسترسی' in denied.json()['detail']
            assert read.call_count == 2


def test_list_route_refresh_flag_updates_erp_state(posted):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    b, _, detail, read, _ = posted
    app = FastAPI(); app.state.settings = b.settings; app.include_router(routes.router)
    app.dependency_overrides[routes.require_session_user] = lambda: 'test-user'
    with TestClient(app) as client, patch.object(routes, '_require', return_value='test-user'), patch.object(routes, '_is_admin', return_value=False):
        endpoint = '/warehouse-assistant/api/interwarehouse'
        assert client.get(endpoint).json()['items'][0]['erp_status'] == 'confirmed'
        change(detail, read, 'missing')
        response = client.get(endpoint + '?refresh_erp=true')
        assert response.status_code == 200 and response.json()['items'][0]['erp_status'] == 'missing'


def test_return_route_requires_both_capabilities_before_recovery(recoverable):
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes
    b, doc, _, read, _, remote = recoverable
    app = FastAPI(); app.state.settings = b.settings; app.include_router(routes.router)
    endpoint = f'/warehouse-assistant/api/interwarehouse/documents/{doc}/return-to-approved'
    with TestClient(app) as client:
        assert client.post(endpoint).status_code == 401
        read.assert_not_called(); remote.assert_not_called()
        app.dependency_overrides[routes.require_session_user] = lambda: 'test-user'
        def without_transfer(request, capability):
            if capability == 'warehouse.receipt.transfer':
                raise HTTPException(status_code=403, detail='Forbidden')
            return 'test-user'
        with patch.object(routes, '_require', side_effect=without_transfer), patch.object(routes, '_is_admin', return_value=False):
            assert client.post(endpoint).status_code == 403
            read.assert_not_called(); remote.assert_not_called()
        with patch.object(routes, '_require', return_value='test-user') as permissions, patch.object(routes, '_is_admin', return_value=False):
            response = client.post(endpoint)
            assert response.status_code == 200 and response.json()['status'] == 'returned_to_approved'
            assert [call.args[1] for call in permissions.call_args_list] == [
                'warehouse.order.draft', 'warehouse.receipt.transfer']
            read.assert_called_once(); remote.assert_called_once()
