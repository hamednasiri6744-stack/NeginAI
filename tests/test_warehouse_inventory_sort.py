"""Global inventory ordering against an isolated SQLite snapshot; no ERP calls."""
from types import SimpleNamespace

import pytest

from app import warehouse_assistant_service as service
from app import warehouse_purchase_contracts as contracts


@pytest.fixture
def inventory(tmp_path):
    settings = SimpleNamespace(sqlite_path=tmp_path / 'sort-fixture.db')
    service.init_warehouse_store(settings)
    contracts.initialize(settings)
    with service.warehouse_connection(settings) as conn:
        conn.execute("""INSERT INTO warehouse_snapshots
            (id,source_filename,source_sheet,content_sha256,product_count,item_count,imported_by,imported_at)
            VALUES (1,'fixture','fixture','fixture',320,320,'test','2026-09-08')""")
        conn.executemany("""INSERT INTO warehouse_snapshot_items
            (snapshot_id,source_row,warehouse_code,warehouse_name,product_code,product_name,
             conversion_rate,stock,manufacturer_price,manufacturer,days_since_last_stock,last_in_stock_date)
            VALUES (1,?,'karaj','انبار نمونه',?,?,1,?,?,?,?,?)""",
            [(i + 1, f'P{i:03}', f'کالا {i}', i + 0.5, 1000 - i * 2,
              'شرکت کامان' if i % 2 == 0 else 'سیلانه سبز',
              None if i == 319 else i, None if i == 319 else f'1405/06/{i % 30 + 1:02}')
             for i in range(320)])
    return settings


@pytest.mark.parametrize('direction,expected', [('desc', ['P319', 'P318', 'P317']),
                                               ('asc', ['P000', 'P001', 'P002'])])
def test_numeric_order_is_global_before_limit_and_offset(inventory, direction, expected):
    result = service.list_inventory_information(inventory, sort_by='on_hand_qty',
                                                 sort_direction=direction, limit=3)
    assert [r['product_code'] for r in result['items']] == expected
    assert result['summary']['total_items'] == 320
    assert result['pagination']['has_more'] is True
    second = service.list_inventory_information(inventory, sort_by='on_hand_qty',
                                                 sort_direction=direction, limit=2, offset=1)
    assert [r['product_code'] for r in second['items']] == expected[1:]
    assert second['summary']['on_hand_qty'] == result['summary']['on_hand_qty']


def test_header_filter_then_price_order_covers_all_rows(inventory):
    result = service.list_inventory_information(inventory,
        column_filters={'manufacturer': 'کامان'}, sort_by='manufacturer_price',
        sort_direction='asc', limit=2)
    assert [r['product_code'] for r in result['items']] == ['P318', 'P316']
    assert [r['manufacturer_price'] for r in result['items']] == [364, 368]
    assert result['summary']['total_items'] == 160
    assert result['pagination']['has_more'] is True


@pytest.mark.parametrize('column', ['days_since_last_stock', 'last_in_stock_date'])
@pytest.mark.parametrize('direction', ['asc', 'desc'])
def test_null_values_remain_last_in_either_direction(inventory, column, direction):
    result = service.list_inventory_information(inventory, sort_by=column,
        sort_direction=direction, limit=320)
    assert len(result['items']) == 320
    assert result['items'][-1]['product_code'] == 'P319'
    assert result['items'][-1][column] is None


def test_tax_rates_sort_numerically_not_by_label_and_unknown_stays_last(inventory):
    contracts.replace_catalog(inventory, [
        dict(product_code=code, product_name=code, goods_id=i, supplier_id=17,
             supplier='fixture', brand_id=1, brand='fixture', tax_rate=rate,
             tax_status='known' if rate is not None else 'unknown')
        for i, (code, rate) in enumerate([('P000', 2), ('P001', 10), ('P002', 16), ('P003', 0)])])
    asc = service.list_inventory_information(inventory, sort_by='tax_rate', sort_direction='asc', limit=5)
    desc = service.list_inventory_information(inventory, sort_by='tax_rate', sort_direction='desc', limit=5)
    assert [r['tax_rate'] for r in asc['items']] == [0, 2, 10, 16, None]
    assert [r['tax_rate'] for r in desc['items']] == [16, 10, 2, 0, None]
    filtered = service.list_inventory_information(inventory, column_filters={'tax_rate': '۱۰'},
        sort_by='on_hand_qty', sort_direction='desc', limit=1)
    assert filtered['items'][0]['product_code'] == 'P001'
    assert filtered['summary']['total_items'] == 1


@pytest.mark.parametrize('values', [
    {'sort_by': 'stock'}, {'sort_by': 'product_code DESC; DELETE FROM warehouse_snapshot_items;--'},
    {'sort_direction': 'DESC'}, {'sort_direction': 'desc NULLS LAST;--'},
])
def test_invalid_sort_rejected_before_read_and_snapshot_unchanged(inventory, values):
    with pytest.raises(service.WarehouseAssistantError, match='مرتب‌سازی'):
        service.list_inventory_information(inventory, **values)
    with service.warehouse_connection(inventory) as conn:
        assert conn.execute('SELECT COUNT(*) FROM warehouse_snapshot_items').fetchone()[0] == 320


def test_ordering_does_not_write_snapshot_quantities_or_prices(inventory):
    with service.warehouse_connection(inventory) as conn:
        before = [tuple(r) for r in conn.execute('SELECT * FROM warehouse_snapshot_items ORDER BY id')]
    for column in ['on_hand_qty', 'manufacturer_price', 'effective_procurement_qty']:
        service.list_inventory_information(inventory, sort_by=column, limit=10)
    with service.warehouse_connection(inventory) as conn:
        after = [tuple(r) for r in conn.execute('SELECT * FROM warehouse_snapshot_items ORDER BY id')]
    assert after == before


@pytest.mark.parametrize('column', sorted(service.INVENTORY_FILTER_SQL))
def test_every_inventory_header_has_an_executable_allowlisted_sort(inventory, column):
    result = service.list_inventory_information(inventory, sort_by=column, limit=1)
    assert len(result['items']) == 1
    assert result['summary']['total_items'] == 320
