"""Search regression tests: isolated temporary warehouse DB, no app startup/ERP."""
from types import SimpleNamespace

import pytest

from app import warehouse_assistant_service as service


@pytest.mark.parametrize("value", ["۱۲٬۳۴۵٫۶", "١٢٬٣٤٥٫٦", "12,345.6"])
def test_normalized_digits(value):
    assert service._normalize_search_text(value) == "12345.6"
    assert service._normalize_search_text(0) == "0"


def test_inventory_search_and_numeric_column_filters(tmp_path):
    settings = SimpleNamespace(sqlite_path=tmp_path / "isolated.db")
    service.init_warehouse_store(settings)
    with service.warehouse_connection(settings) as conn:
        conn.execute("""INSERT INTO warehouse_snapshots
            (id,source_filename,source_sheet,content_sha256,product_count,item_count,imported_by,imported_at)
            VALUES(1,'fixture','fixture','fixture',2,2,'test','2026-09-05T00:00:00+00:00')""")
        for code, name in [("451603944", "رب ۸۰۰ گرم"), ("۴۵۱۶۰۳۹۴۵", "رب 800 گرم")]:
            conn.execute("""INSERT INTO warehouse_snapshot_items
                (snapshot_id,source_row,warehouse_code,warehouse_name,product_code,product_name,conversion_rate,stock)
                VALUES(1,1,'THR','انبار نمونه',?,?,12,12345.6)""", (code, name))
    for query in ["800", "۸۰۰", "٨٠٠"]:
        result = service.list_inventory_information(settings, search=query)
        assert result["pagination"]["has_more"] is False
        assert result["summary"]["total_items"] == 2
    for query in ["451603944", "۴۵۱۶۰۳۹۴۴", "٤٥١٦٠٣٩٤٤"]:
        assert service.list_inventory_information(settings, search=query)["summary"]["total_items"] == 1
    for query in ["۱۲٬۳۴۵٫۶", "12,345.6", "١٢٣٤٥.٦"]:
        result = service.list_inventory_information(settings, column_filters={"on_hand_qty": query}, limit=1)
        assert result["summary"]["total_items"] == 2
        assert result["pagination"]["has_more"] is True
        assert result["summary"]["on_hand_qty"] == 24691.2
    result = service.list_inventory_information(settings, column_filters={"product_code": "451603945"})
    assert result["items"][0]["product_code"] == "۴۵۱۶۰۳۹۴۵"
    assert service.list_inventory_information(settings, search="ناپیدا")["summary"]["total_items"] == 0


def test_inventory_filters_contain_literal_text_with_persian_variants(tmp_path):
    settings = SimpleNamespace(sqlite_path=tmp_path / 'isolated.db')
    service.init_warehouse_store(settings)
    with service.warehouse_connection(settings) as conn:
        conn.execute("""INSERT INTO warehouse_snapshots
            (id,source_filename,source_sheet,content_sha256,product_count,item_count,imported_by,imported_at)
            VALUES(1,'fixture','fixture','contains',3,3,'test','2026-09-14T00:00:00+00:00')""")
        for code, name in [('1', 'شیر کم\u200cچرب كيسه ۲۰٪'), ('2', 'شیر کم  چرب کیسه ۲۰٪'), ('3', 'شیر پرچرب 100% A_B')]:
            conn.execute("""INSERT INTO warehouse_snapshot_items
                (snapshot_id,source_row,warehouse_code,warehouse_name,product_code,product_name,brand,conversion_rate,stock)
                VALUES(1,1,'karaj','کرج',?,?,'برند نمونه',12,120)""", (code, name))
    for query in ['کم چرب کیسه', 'کم\u200cچرب كيسه', 'کم   چرب کیسه']:
        result = service.list_inventory_information(settings,
            column_filters={'product_name': query, 'brand': 'نمونه', 'on_hand_qty': '۲'}, limit=1)
        assert result['summary']['total_items'] == 2
        assert result['pagination']['has_more'] is True
        assert service.list_inventory_information(settings, search=query)['summary']['total_items'] == 2
    for query in ['%', '_', 'A_B']:
        for filters in [{'search': query}, {'column_filters': {'product_name': query}}]:
            assert [r['product_code'] for r in service.list_inventory_information(settings, **filters)['items']] == ['3']
