from decimal import Decimal
from types import SimpleNamespace
import pytest
from app import warehouse_purchase_contracts as pc
from app.warehouse_purchase_invoice_bridge import invoice_presentation


def rule(**overrides):
    return dict(dict(supplier_id=5,scope='item',product_code='A',title='پلانگتون',
        start_date='1405/06/17',end_date='',status='active',basis='consumer',
        includes_tax=False,adjustment_percent='-60',discount_percent='20',
        discount_steps=[{'percent':'20'},{'percent':'5'}],
        tail_discount={'kind':'percent','basis':'net_before_tax','value':'0'},note=''),**overrides)


def test_plankton_stages_match_invoice_732_and_remain_distinct_from_tail():
    result=pc.calculate(rule(),price='3890000',quantity=648,tax_rate=0)
    assert result['unit_price']=='1556000'
    assert result['total']=='766298880'
    assert result['tail_discount']=='0'
    assert [s['percent'] for s in result['discount_stages']]==['20','5']
    assert result['discount_stages'][1]['base']==result['discount_stages'][0]['remaining']


@pytest.mark.parametrize('reduction,price,expected',[('50','9800000','3724000'),('55','8650000','2958300'),('47.849462','3720000','1474400'),('59.915612','2370000','722000')])
def test_item_exceptions_reproduce_observed_unit_prices(reduction,price,expected):
    assert pc.calculate(rule(adjustment_percent='-'+reduction),price=price,quantity=1,tax_rate=0)['total']==expected


def test_vat_is_after_both_column_stages_and_tail_is_separate():
    result=pc.calculate(rule(includes_tax=True),price='1144000',quantity=1,tax_rate=10)
    assert result['net_before_tax']=='316160'
    assert result['tax']=='31616'
    assert result['total']=='347776'
    tail=pc.calculate(rule(includes_tax=True,tail_discount={'kind':'percent','basis':'after_tax','value':'10'}),price='1144000',quantity=1,tax_rate=10)
    assert tail['tail_discount']=='34778' and tail['total']=='312998'


def test_rounding_is_per_stage_and_not_combined_percentage():
    result=pc.calculate(rule(adjustment_percent='0'),price=13,quantity=1,tax_rate=0)
    assert result['discount']=='4' and result['total']=='9'


def test_save_reload_revision_and_presentation_preserve_steps(tmp_path):
    settings=SimpleNamespace(sqlite_path=tmp_path/'test.db')
    pc.replace_catalog(settings,[dict(supplier_id=5,supplier='پلانگتون',manufacturer_id=5,
        product_code='A',product_name='قلم',goods_id=1,brand_id=15,brand='پلانگتون',tax_rate=10,tax_status='known')])
    saved=pc.save_contract(settings,'test',rule())
    assert pc.resolve_products(settings,5,'1405/06/17')['items'][0]['contract']['discount_steps']==rule()['discount_steps']
    edited=pc.save_contract(settings,'test',dict(saved,discount_steps=[{'percent':'20'},{'percent':'6'}]),saved['id'],1)
    assert [x['contract']['discount_steps'][-1]['percent'] for x in pc.history(settings,saved['id'])]==['6','5']
    amounts=pc.calculate(edited,price=1000,quantity=1,tax_rate=0)
    display,_=invoice_presentation([{'amounts':amounts}],[{'rule':edited}],amounts['total'])
    assert display[0]['pricing']['discount_steps']==edited['discount_steps']
    old_client=dict(edited);del old_client['discount_steps']
    with pytest.raises(pc.ContractError,match='بازخوانی'):
        pc.save_contract(settings,'test',old_client,edited['id'],2)
    with pytest.raises(pc.ContractError,match='بازخوانی'):
        pc.update_item_batch(settings,'test',dict(old_client,contract_versions={edited['id']:2}))
    assert len(pc.history(settings,saved['id']))==2


@pytest.mark.parametrize('steps',[None,[],[{'percent':'19'}],[{'percent':'20'},{'percent':''}],[{'percent':'20'},{'percent':'NaN'}],[{'percent':'20'},{'percent':'101'}],[{'percent':'20'}]*6])
def test_invalid_steps_fail_closed(steps):
    with pytest.raises(pc.ContractError):pc.calculate(rule(discount_steps=steps),price=100,quantity=1,tax_rate=10)


def test_legacy_rule_without_steps_is_unchanged():
    old=rule(adjustment_percent='0',discount_percent='18',tail_discount={'kind':'percent','basis':'net_before_tax','value':'8.95'},includes_tax=True)
    del old['discount_steps']
    assert pc.calculate(old,price=1100000,quantity=1,tax_rate=10)['total']=='828610'
