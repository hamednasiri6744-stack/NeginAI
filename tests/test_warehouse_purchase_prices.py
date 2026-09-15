from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from app import warehouse_purchase_prices as prices
from app.warehouse_purchase_contracts import ContractError
from app.sql_guard import validate_read_only_sql


PRODUCT = {'goods_id': 8, 'product_code': 'KA-8', 'product_name': 'قلم نمونه'}
RULE = {'basis': 'manufacturer', 'start_date': '1405/06/01', 'end_date': '1405/06/31'}


def source(**kwargs):
    return dict({'goods_id': 8, 'price_id': 'one', 'on_date': '1405/06/18',
        'start_date': '1405/06/01', 'end_date': '1405/06/31', 'source_count': 1,
        'manufacturer_price': '820000', 'consumer_price': '1100000', 'stock_name': 'کرج'}, **kwargs)


@pytest.mark.parametrize('value', [None, '', 0, -1, 'NaN', 'Infinity', False])
def test_missing_or_invalid_required_price_never_falls_back(value):
    with pytest.raises(ContractError, match='KA-8.*قیمت تولیدکننده'):
        prices.require_source_price(RULE, PRODUCT, source(manufacturer_price=value))


def test_basis_is_exact_and_returned_without_tax_or_rounding_changes():
    assert prices.require_source_price(RULE, PRODUCT, source()) == '820000'
    assert prices.require_source_price(dict(RULE, basis='consumer'), PRODUCT, source()) == '1100000'
    assert prices.require_source_price(RULE, PRODUCT, source(manufacturer_price='820000.25')) == '820000.25'
    assert prices.source_price_status({'basis': 'announcement'}, PRODUCT, None)['status'] == 'not_required'


@pytest.mark.parametrize('change', [
    {'start_date': '1405/06/19'}, {'end_date': '1405/06/17'}, {'price_id': None},
    {'source_count': 0}, {'source_count': 2}, {'goods_id': 9}, {'on_date': None},
    {'on_date': '1405/07/01'},
])
def test_wrong_or_outside_period_source_is_rejected(change):
    with pytest.raises(ContractError):
        prices.require_source_price(RULE, PRODUCT, source(**change))


def test_inclusive_period_and_consumer_does_not_require_manufacturer_row():
    assert prices.require_source_price(RULE, PRODUCT, source(on_date='1405/06/01'))
    assert prices.require_source_price(RULE, PRODUCT, source(on_date='1405/06/31'))
    assert prices.require_source_price(dict(RULE,basis='consumer'), PRODUCT,
        source(source_count=0,manufacturer_price=None)) == '1100000'


@pytest.mark.parametrize('stock', [None, True, '1', 7, 999])
def test_unsupported_warehouse_cannot_use_karaj_price(stock):
    with pytest.raises(ContractError):prices.source_price_query([8], '1405/06/18', stock)


def test_source_query_matches_dated_unrestricted_inventory_source():
    sql = prices.source_price_query([8, 9], '۱۴۰۵/۰۶/۱۸', 2)
    checked = validate_read_only_sql(sql)
    assert set(checked.sources) == {'SLE.tblCPrice', 'NGT.ContractPrices', 'NGT.OrderTypes'}
    assert 'p.OrderTypeRef)=10' in sql
    assert "p.StartDate<=N'1405/06/18'" in sql
    assert "p.EndDate>=N'1405/06/18'" in sql
    assert 'p.StartDate DESC,p.[LastUpdate] DESC,p.Priority DESC,p.Id DESC' in sql
    assert "NULLIF(p.CustRef,'') IS NULL" in sql
    assert "NULLIF(p.GoodsGroupRef,'') IS NULL" in sql
    assert "NULLIF(p.DCRef,'') IS NULL" in sql
    assert 'ISNULL(p.IsRemoved,0)=0' in sql


def test_live_resolver_preserves_missing_product_and_zero(monkeypatch):
    columns = ['GoodsRef','PriceId','StartDate','EndDate','ManufacturerPrice','ConsumerPrice','SourceCount']
    class Cursor:
        description = [(c,) for c in columns]
        def execute(self, query):validate_read_only_sql(query)
        def fetchmany(self, count):return [(8,'one','1405/06/01','',0,100,1)]
    @contextmanager
    def connection(_):yield SimpleNamespace(cursor=lambda: Cursor())
    monkeypatch.setattr(prices,'sql_connection',connection)
    result = prices.resolve_source_prices(None,[8,9],'1405/06/18',1)
    assert result[8]['manufacturer_price'] == '0'
    assert result[9]['price_id'] is None
    assert result[9]['on_date'] == '1405/06/18'
    assert result[9]['stock_id'] == 1
    assert prices.source_price_status(RULE,PRODUCT,result[8])['status'] == 'missing'


def test_source_connection_failure_is_not_misreported_as_missing_price(monkeypatch):
    def failure(_):raise RuntimeError('secret connection details')
    monkeypatch.setattr(prices,'sql_connection',failure)
    with pytest.raises(ContractError,match='بررسی قیمت تولید و مصرف') as error:
        prices.resolve_source_prices(None,[8],'1405/06/18',1)
    assert 'secret' not in str(error.value)
