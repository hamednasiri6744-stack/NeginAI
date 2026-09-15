"""User-specified unit/carton/amount contract; no live API or production writes."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app import warehouse_checkbar_image as vision


def matched(unit='قوطی', cartons='70', amount='1680', *, supplier='شرکت کامان', factor=24, **changes):
    row = dict(source_page=1, description='کالای نمونه', supplier_code='300152301',
               barcode=None, cartons='70', units='1680', quantity_text='متن خوانده‌شده', uncertain=False,
               printed_unit=unit, printed_cartons=cartons, printed_amount=amount)
    row.update(changes)
    extraction = vision.ImageExtraction.model_validate(dict(supplier=supplier, reference_no='1735',
        date='1405/06/16', warnings=[], pages=[dict(page_number=1, complete=True)], lines=[row]))
    source = dict(supplier=supplier, expected_token='test', lines=[], catalog=[dict(product_code='local',
        manufacturer_product_code='300152301', barcode='', product_name='کالای نمونه', conversion_rate=factor)])
    return vision.match_rows(extraction, source)['rows'][0]


@pytest.mark.parametrize('supplier', ['شرکت کامان', 'سیلانه سبز', 'شرکت سیلانه‌سبز', 'انجیر طلایی', 'انجير طلايي'])
def test_three_suppliers_never_add_total_to_cartons(supplier):
    row = matched(supplier=supplier)
    assert (row['cartons'], row['units']) == (70, 0)
    assert row['total_base_units'] == 1680 and row['selected'] == 0
    assert row['problems'] == []
    assert '1680' in row['quantity_text'] and 'قوطی' in row['quantity_text']


@pytest.mark.parametrize('unit,cartons,amount,factor,expected', [
    ('کارتن','47','47',24,1128), ('عدد','1','30',30,30),
    ('قوطی','19','228',12,228), ('قوطی','35','420',12,420),
    ('قوطی','۷۰','۱٬۶۸۰',24,1680), ('کارتن','0','0',24,0), ('عدد','0','0',24,0),
])
def test_image_examples_resolve_to_one_quantity(unit, cartons, amount, factor, expected):
    row = matched(unit, cartons, amount, factor=factor)
    assert row['cartons'] * factor + row['units'] == expected
    assert row['units'] == 0


@pytest.mark.parametrize('unit,cartons,amount', [
    (None,'70','1680'), ('قوطی',None,'1680'), ('قوطی','70',None),
    ('بسته','70','1680'), ('کیلو','70','1680'), ('قوطی','-70','1680'),
    ('قوطی','70','1,68'), ('قوطی','70','1680.5'), ('کارتن','47','48'),
])
def test_unknown_or_inconsistent_raw_columns_never_fall_back_to_double_count(unit, cartons, amount):
    row = matched(unit, cartons, amount)
    assert row['cartons'] is None and row['units'] is None
    assert row['selected'] == 0 and row['problems']


@pytest.mark.parametrize('factor', [12,48,0,None,float('nan')])
def test_factor_mismatch_or_unknown_preserves_printed_base_total_and_requires_review(factor):
    row = matched(factor=factor)
    assert (row['cartons'],row['units']) == (0,1680)
    assert row['total_base_units'] == 1680
    assert row['selected'] == 0 and row['problems']


def test_other_supplier_retains_existing_loose_quantity_semantics():
    row = matched(supplier='تأمین‌کننده دیگر')
    assert (row['cartons'], row['units']) == (70,1680)
    assert row.get('total_base_units') is None


def test_code_and_description_survive_generic_uncertainty():
    row = matched(uncertain=True)
    assert row['selected'] == 0 and row['problems']
    assert (row['cartons'],row['units']) == (70,0)


def test_api_prompt_requests_raw_columns_and_supplies_selected_supplier_rule(monkeypatch):
    client = MagicMock()
    client.return_value.__enter__.return_value.responses.parse.return_value = SimpleNamespace(
        status='completed', output_parsed=vision.ImageExtraction.model_validate(dict(supplier='کامان',
            reference_no='1735',date='1405/06/16',warnings=[],pages=[dict(page_number=1,complete=True)],lines=[])))
    monkeypatch.setattr(vision,'OpenAI',client)
    vision.extract(SimpleNamespace(openai_api_key='fake',openai_model='configured'), b'\xff\xd8\xfftest', supplier='شرکت کامان')
    args = client.return_value.__enter__.return_value.responses.parse.call_args.kwargs
    prompt = args['input'][0]['content']
    assert 'printed_unit' in prompt and 'printed_cartons' in prompt and 'printed_amount' in prompt
    assert '1680' in prompt and '70' in prompt
    assert 'THREE_COLUMN_QUANTITY' in prompt
    assert args['model'] == 'configured' and args['store'] is False


def test_all_17_rows_on_reference_photo_preserve_483_cartons_not_2716_units():
    # Independently transcribed from delivery note 1735, dated 1405/06/16.
    rows = [('کارتن',47,47,24), ('عدد',1,30,30), ('کارتن',1,1,24),
            ('قوطی',70,1680,24), ('کارتن',60,60,24), ('کارتن',9,9,24),
            ('کارتن',9,9,24), ('قوطی',19,228,12), ('کارتن',13,13,24),
            ('کارتن',12,12,24), ('کارتن',25,25,24), ('کارتن',36,36,24),
            ('کارتن',37,37,24), ('قوطی',35,420,12), ('کارتن',22,22,24),
            ('کارتن',38,38,24), ('کارتن',49,49,24)]
    actual = [matched(unit, str(cartons), str(amount), factor=factor)
              for unit, cartons, amount, factor in rows]
    assert sum(row['cartons'] for row in actual) == 483
    assert all(row['units'] == 0 and not row['problems'] for row in actual)
    assert sum(amount for _,_,amount,_ in rows) == 2716  # Mixed printed units, not a base-unit total.
