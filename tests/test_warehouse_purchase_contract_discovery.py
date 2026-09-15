from types import SimpleNamespace

import pytest

from app import warehouse_purchase_contract_discovery as discovery
from app import warehouse_purchase_contracts as contracts


def history_row(index, **changes):
    row = {
        'invoice_id': 100 + index, 'invoice_no': index, 'invoice_date': f'1405/05/{index:02d}',
        'product_code': f'P{index}', 'product_name': f'کالای {index}',
        'quantity': '10', 'prize_quantity': '0', 'unit_price': '1000',
        'price_comment': '1600-1100', 'receipt_match': True,
        'factors': [{'factor_id': 8, 'percent': '10', 'amount': '900'}],
    }
    row.update(changes)
    return row


def test_receipt_price_parser_is_strict_and_accepts_persian_digits():
    assert discovery.parse_receipt_prices('۱٬۶۰۰ - ۱۱۰۰') == (1600, 1100)
    assert discovery.parse_receipt_prices('قیمت 1600-1100') is None
    assert discovery.parse_receipt_prices('0-1100') is None


def test_analyze_ranks_repeatable_rule_and_keeps_rejections_visible():
    rows = [history_row(i) for i in range(1, 5)]
    rows.append(history_row(9, receipt_match=False))
    result = discovery.analyze(rows, 17, 'شرکت نمونه')
    best = result['proposals'][0]
    assert (best['basis'], best['includes_tax'], best['adjustment_percent']) == ('manufacturer', True, '0')
    assert best['confidence'] == 'high'
    assert best['evidence_count'] == 4 and best['invoice_count'] == 4
    assert result['eligible_count'] == 4 and result['rejected_count'] == 1
    assert result['observations'][-1]['accepted'] is False
    assert result['advisory_only'] is True


def test_discount_factors_keep_their_historical_sequence_without_inventing_tail_semantics():
    factors = [
        {'factor_id': 2, 'percent': '20', 'amount': '2000'},
        {'factor_id': 6, 'percent': '5', 'amount': '400'},
        {'factor_id': 8, 'percent': '10', 'amount': '760'},
        {'factor_id': 3, 'percent': '3', 'amount': '228'},
    ]
    result = discovery.analyze([history_row(i, factors=factors) for i in range(1, 4)], 5)
    best = result['proposals'][0]
    assert best['discount_steps'] == [{'percent': '20'}, {'percent': '5'}, {'percent': '3'}]
    assert best['tail_discount'] == {'kind': 'percent', 'basis': 'net_before_tax', 'value': '0'}


def test_unknown_or_fixed_factor_is_not_silently_inferred():
    row = history_row(1, factors=[{'factor_id': 1, 'percent': '0', 'amount': '500'}])
    result = discovery.analyze([row], 5)
    assert result['proposals'] == []
    assert result['rejected_count'] == 1
    assert 'تنظیم دستی' in result['observations'][0]['reason']


@pytest.fixture
def store(tmp_path):
    settings = SimpleNamespace(sqlite_path=tmp_path / 'warehouse.db')
    contracts.initialize(settings)
    contracts.replace_catalog(settings, [dict(product_code='P1', product_name='کالا', goods_id=1,
        brand_id=2, brand='برند', supplier_id=17, supplier='شرکت نمونه', manufacturer_id=17,
        manufacturer='شرکت نمونه', group_id=3, group_name='گروه', tax_rate=10, tax_status='known')])
    return settings


def test_discovery_is_saved_as_evidence_and_never_creates_contract(store, monkeypatch):
    monkeypatch.setattr(discovery, '_query_rows', lambda *args: [history_row(i) for i in range(1, 4)])
    result = discovery.discover(store, 17, 1404, 1405)
    assert discovery.latest(store, 17)['run_id'] == result['run_id']
    assert contracts.list_contracts(store) == []
    with contracts.connect(store) as connection:
        assert connection.execute('SELECT COUNT(*) FROM warehouse_purchase_contract_discovery').fetchone()[0] == 1


def test_discovered_contract_requires_evidence_reference(store):
    payload = dict(supplier_id=17, scope='item', product_code='P1', title='پیشنهاد',
        start_date='1405/06/18', end_date='', status='draft', basis='manufacturer', includes_tax=True,
        adjustment_percent='0', discount_percent='0', tail_discount_percent='0', source_mode='discovered')
    with pytest.raises(contracts.ContractError, match='شواهد'):
        contracts.save_contract(store, 'tester', payload)
    payload['evidence_run_id'] = 'run-1'; payload['agreement_reference'] = 'توافق ۱۲'
    saved = contracts.save_contract(store, 'tester', payload)
    assert saved['source_mode'] == 'discovered' and saved['agreement_reference'] == 'توافق ۱۲'


def test_discovery_api_requires_refresh_permission_and_returns_advisory(store, monkeypatch):
    from fastapi import FastAPI, Request
    from fastapi.testclient import TestClient
    from app.routes import warehouse_assistant as routes

    app = FastAPI(); app.state.settings = store
    async def identity(request: Request):
        request.state.username = request.headers.get('X-Test-User', 'editor')
    app.dependency_overrides[routes.require_session_user] = identity
    monkeypatch.setattr(routes, '_capabilities', lambda request, username:
        {'warehouse.assistant.view', 'warehouse.data.refresh'} if username == 'editor' else {'warehouse.assistant.view'})
    monkeypatch.setattr(routes.purchase_contract_discovery, 'discover', lambda settings, supplier_id, from_year, to_year:
        {'supplier_id': supplier_id, 'advisory_only': True, 'proposals': []})
    app.include_router(routes.router)
    headers = {'X-Warehouse-Settings': '1', 'Origin': 'http://testserver'}
    with TestClient(app) as client:
        response = client.post('/warehouse-assistant/api/purchase-contracts/discovery', headers=headers, json={'supplier_id': 17})
        assert response.status_code == 200 and response.json()['advisory_only'] is True
        denied = client.post('/warehouse-assistant/api/purchase-contracts/discovery',
            headers={**headers, 'X-Test-User': 'viewer'}, json={'supplier_id': 17})
        assert denied.status_code == 403
