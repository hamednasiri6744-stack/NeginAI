"""Independent expectations from the six-row Afagh dispatch note."""
import pytest

from app import warehouse_checkbar_image as vision
from test_warehouse_checkbar_image import extracted, line, source


def pack_row(**changes):
    return line(barcode='00099', cartons=None, units='1440',
                printed_pack_count='30', printed_pack_size='48', printed_total_units='1,440',
                description_uncertain=True, **changes)


def catalog(factor=48):
    result = source()
    result['catalog'][0]['conversion_rate'] = factor
    return result


def test_clear_identifiers_and_verified_columns_survive_unclear_description():
    result = vision.match_rows(extracted([pack_row()]), catalog())['rows'][0]
    assert result['selected'] == 0
    assert (result['cartons'], result['units'], result['total_base_units']) == (30, 0, 1440)
    assert result['problems']  # Description uncertainty stays visible for review.


@pytest.mark.parametrize('count,size,total', [
    ('30','48','1,440'), ('60','24','1,440'), ('30','24','720'),
    ('50','24','1,200'), ('60','8','480'), ('170','8','1,360'),
])
def test_dispatch_count_times_pack_size_is_total_not_extra_units(count,size,total):
    row = line(cartons=None,units=None,printed_pack_count=count,printed_pack_size=size,
               printed_total_units=total)
    result = vision.match_rows(extracted([row]),catalog(int(size)))['rows'][0]
    assert result['cartons'] == int(count) and result['units'] == 0
    assert result['total_base_units'] == int(total.replace(',',''))
    assert result['selected'] == 0


def test_different_catalog_pack_preserves_total_and_requires_review():
    row = vision.match_rows(extracted([pack_row()]),catalog(24))['rows'][0]
    assert row['selected'] == 0
    assert (row['cartons'],row['units'],row['total_base_units']) == (0,1440,1440)


@pytest.mark.parametrize('changes',[
    {'printed_pack_count':'31'}, {'printed_pack_size':None}, {'printed_total_units':'bad'},
    {'printed_pack_count':'1.5'}, {'printed_pack_size':'0'},
])
def test_inconsistent_pack_columns_preserve_identity_and_leave_counts_blank(changes):
    raw = pack_row(); raw.update(changes)
    row = vision.match_rows(extracted([raw]),catalog())['rows'][0]
    assert row['selected'] == 0 and row['problems']
    assert row['cartons'] is None and row['units'] is None


def test_two_identifiers_survive_generic_uncertainty():
    raw=pack_row();raw['uncertain']=True
    row=vision.match_rows(extracted([raw]),catalog())['rows'][0]
    assert row['selected'] == 0


def test_code_and_description_outweigh_barcode_alone():
    raw=pack_row();raw['barcode']='00100'
    row=vision.match_rows(extracted([raw]),catalog())['rows'][0]
    assert row['selected'] == 0
