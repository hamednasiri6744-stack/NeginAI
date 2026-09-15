"""Print real isolated checkbars with live-snapshot prices; no ERP writes."""
from html.parser import HTMLParser
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_warehouse_fulfillment import case
from test_warehouse_checkbar import activate
from app import warehouse_checkbar as checkbar
from app import warehouse_checkbar_print as printing
from app import warehouse_assistant_service as service


@pytest.fixture
def document(case):
    activate(case)
    case.change('UPDATE warehouse_snapshot_items SET manufacturer_price=111,consumer_price=222')
    source = checkbar.prepare(case.settings, 'karaj', 'supplier', [])
    saved = checkbar.issue(case.settings, 'tester', dict(warehouse='karaj', supplier='supplier', order_ids=[],
        expected_token=source['expected_token'], request_id='print-fixture', metadata={'reference_no':'2222', 'driver':'<img src=x onerror=alert(1)>'},
        lines=[dict(product_code='00123', cartons=1, units=2, manufacturer_price_new=777, consumer_price_new=888)]))
    with service.warehouse_connection(case.settings) as conn:
        snap = dict(conn.execute('SELECT * FROM warehouse_snapshots WHERE id=1').fetchone())
        snap.update(id=2, content_sha256='current-print', imported_at='2026-09-14T08:00:00+00:00')
        conn.execute(f'INSERT INTO warehouse_snapshots({",".join(snap)}) VALUES({",".join("?" for _ in snap)})', tuple(snap.values()))
        item = dict(conn.execute("SELECT * FROM warehouse_snapshot_items WHERE warehouse_code='karaj'").fetchone())
        item.pop('id', None)
        item.update(snapshot_id=2, manufacturer_price=333, consumer_price=444)
        conn.execute(f'INSERT INTO warehouse_snapshot_items({",".join(item)}) VALUES({",".join("?" for _ in item)})', tuple(item.values()))
        item.update(warehouse_code='tehran', manufacturer_price=555, consumer_price=666)
        conn.execute(f'INSERT INTO warehouse_snapshot_items({",".join(item)}) VALUES({",".join("?" for _ in item)})', tuple(item.values()))
    return case, saved


def test_print_reads_current_same_warehouse_prices_preserves_saved_and_new(document):
    case, saved = document
    before = checkbar.get_document(case.settings, saved['id'])
    result = printing.print_document(case.settings, saved['id'])
    line = result['lines'][0]
    assert (line['manufacturer_price'], line['consumer_price']) == (333, 444)
    assert (line['manufacturer_price_new'], line['consumer_price_new']) == (777, 888)
    assert (line['cartons'], line['units'], line['actual_qty']) == (1, 2, 14)
    assert result['price_snapshot_id'] == 2
    assert checkbar.get_document(case.settings, saved['id']) == before
    assert before['lines'][0]['manufacturer_price'] == 111
    case.change("UPDATE warehouse_snapshot_items SET manufacturer_price=0,consumer_price=999 WHERE snapshot_id=2 AND warehouse_code='karaj'")
    fresh = printing.print_document(case.settings, saved['id'])['lines'][0]
    assert (fresh['manufacturer_price'], fresh['consumer_price']) == (0, 999)
    case.transport.assert_not_called()


def test_absent_current_product_does_not_fall_back_to_old_or_other_warehouse(document):
    case, saved = document
    case.change("DELETE FROM warehouse_snapshot_items WHERE snapshot_id=2 AND warehouse_code='karaj'")
    result = printing.print_document(case.settings, saved['id'])
    assert result['lines'][0]['manufacturer_price'] is None
    assert result['lines'][0]['consumer_price'] is None
    assert 'قیمت فعلی کالا در آخرین اطلاعات این انبار موجود نیست' in printing.render(result)


class Table(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=None; self.cell=None
    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.row=[]
        if tag in ('td','th'): self.cell=''
    def handle_data(self, data):
        if self.cell is not None: self.cell+=data
    def handle_endtag(self, tag):
        if tag in ('td','th'): self.row.append(self.cell); self.cell=None
        if tag == 'tr': self.rows.append(self.row)


def test_print_has_fourteen_columns_escaped_text_and_correct_price_positions(document):
    case, saved = document
    result = printing.print_document(case.settings, saved['id'])
    html = printing.render(result)
    table = Table(); table.feed(html)
    assert len(table.rows[0]) == 14 and len(table.rows[1]) == 14
    assert table.rows[1][6:14] == ['444','333','24','1','2','14','777','888']
    assert 'مالیات' not in html and 'tax condition' not in html
    assert '<img' not in html and '&lt;img' in html
    result['lines'][0].update(cartons=None, units=None, actual_qty=None, manufacturer_price_new=None, consumer_price_new=0)
    table = Table(); table.feed(printing.render(result))
    assert table.rows[1][9:14] == ['', '', '', '', '0']


def test_print_route_permissions_fresh_html_and_missing_document(document):
    from app.routes import warehouse_assistant as routes
    case, saved = document
    app = FastAPI(); app.state.settings=case.settings; app.include_router(routes.router)
    path=f'/warehouse-assistant/api/checkbars/{saved["id"]}/print'
    with TestClient(app) as client:
        assert client.get(path).status_code == 401
        app.dependency_overrides[routes.require_session_user] = lambda: 'tester'
        with patch.object(routes, '_capabilities', return_value=set()):
            assert client.get(path).status_code == 403
        with patch.object(routes, '_require', return_value='tester'):
            response=client.get(path)
            assert response.status_code == 200
            assert response.headers['cache-control'] == 'no-store'
            assert response.headers['content-type'].startswith('text/html')
            table=Table(); table.feed(response.text)
            assert table.rows[1][6:8] == ['444','333']
            assert client.get('/warehouse-assistant/api/checkbars/99999/print').status_code >= 400
    case.transport.assert_not_called()
