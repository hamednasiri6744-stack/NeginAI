from app import warehouse_checkbar_image as vision
from test_warehouse_checkbar_image import extracted, line, source


def matched(**changes):
    return vision.match_rows(extracted([line(**changes)]),source())['rows'][0]


def test_two_identifiers_win_even_when_ocr_marks_row_uncertain():
    row=matched(barcode='00099',uncertain=True,description='[ناخوانا]')
    assert row['selected']==0 and row['match_signals']==['supplier_code','barcode']


def test_unrecognized_supplier_code_does_not_veto_known_barcode():
    row=matched(supplier_code='9999',barcode='00099',description='[ناخوانا]')
    assert row['selected']==0 and row['match_reason']


def test_code_and_description_beat_conflicting_barcode_alone():
    row=matched(barcode='00100',description='شامپو 250')
    assert row['selected']==0 and row['match_signals']==['supplier_code','description']
    assert row['suggestions'][0]==0 and 1 in row['suggestions']


def test_conflicting_identifiers_without_tiebreaker_require_choice():
    row=matched(barcode='00100',description='[ناخوانا]')
    assert row['selected'] is None and set(row['suggestions'])=={0,1}


def test_description_can_choose_without_identifiers():
    assert matched(supplier_code=None,barcode=None,description='250 شامپو')['selected']==0


def test_weak_description_never_assigns_arbitrary_catalog_product():
    assert matched(supplier_code=None,barcode=None,description='ناخوانا')['selected'] is None


def test_alternate_barcodes_participate_in_ranking():
    src=source();src['catalog'][0]['barcode2']='123456';src['catalog'][0]['barcode_list']='88888;99999'
    for code in ['123456','99999']:
        row=vision.match_rows(extracted([line(supplier_code=None,barcode=code,description='[ناخوانا]')]),src)['rows'][0]
        assert row['selected']==0


def test_two_orders_with_same_product_are_not_arbitrarily_assigned():
    src=source();src['lines']=[dict(src['catalog'][0],preorder_id=1),dict(src['catalog'][0],preorder_id=2)]
    row=vision.match_rows(extracted([line(barcode='00099')]),src)['rows'][0]
    assert row['selected'] is None and len(row['suggestions'])>=2
