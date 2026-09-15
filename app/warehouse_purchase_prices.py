"""Read-only, dated price source shared with the inventory snapshot.

These prices are not interchangeable: manufacturer price comes from the ERP
price row linked to the selected NGT contract; consumer price is its UserPrice.
No last purchase, other warehouse, expired period, or input sample is a fallback.
"""
from decimal import Decimal, InvalidOperation

from app.database import sql_connection
from app.sql_guard import validate_read_only_sql
from app.warehouse_purchase_contracts import ContractError, clean_date, text


LABELS = {'manufacturer': 'قیمت تولیدکننده', 'consumer': 'قیمت مصرف‌کننده'}


def price_context(stock_id, on_date):
    from app.warehouse_assistant_service import WAREHOUSES
    if type(stock_id) is not int:
        raise ContractError('انبار را برای بررسی قیمت مبنای خرید انتخاب کنید.')
    stock = next((r for r in WAREHOUSES.values() if r['stock_dc_ref'] == stock_id), None)
    if stock is None:
        raise ContractError('منبع قیمت این انبار در اطلاعات انبار تعریف نشده است.')
    return {'stock_id': stock_id, 'stock_name': stock['name'],
            'order_type_id': stock['price_order_type_ref'], 'on_date': clean_date(on_date)}


def source_price_query(goods_ids, on_date, stock_id):
    context = price_context(stock_id, on_date)
    if not goods_ids or len(goods_ids) > 500 or any(type(g) is not int or g <= 0 for g in goods_ids):
        raise ContractError('شناسه کالا برای خواندن قیمت معتبر نیست.')
    # Inputs interpolated here are validated integers and a canonical Jalali date.
    # Scope and ranking intentionally match sync_varanegar_snapshot.
    ids = ','.join(str(g) for g in sorted(set(goods_ids)))
    return f"""WITH source_prices AS (
      SELECT UniqueId,MAX(ManufacturerPrice) ManufacturerPrice,COUNT(*) SourceCount
      FROM SLE.tblCPrice GROUP BY UniqueId
    ), candidates AS (
      SELECT TRY_CONVERT(int,p.GoodsRef) GoodsRef,p.Id PriceId,p.StartDate,p.EndDate,
        p.UserPrice ConsumerPrice,s.ManufacturerPrice,ISNULL(s.SourceCount,0) SourceCount,
        ROW_NUMBER() OVER (PARTITION BY TRY_CONVERT(int,p.GoodsRef),TRY_CONVERT(int,p.OrderTypeRef)
          ORDER BY p.StartDate DESC,p.[LastUpdate] DESC,p.Priority DESC,p.Id DESC) PriceRank
      FROM NGT.ContractPrices p
      INNER JOIN NGT.OrderTypes t ON TRY_CONVERT(int,t.BackOfficeId)=TRY_CONVERT(int,p.OrderTypeRef)
        AND ISNULL(t.IsRemoved,0)=0
      LEFT JOIN source_prices s ON s.UniqueId=p.Id
      WHERE TRY_CONVERT(int,p.GoodsRef) IN ({ids})
        AND TRY_CONVERT(int,p.OrderTypeRef)={context['order_type_id']}
        AND ISNULL(p.IsRemoved,0)=0 AND p.StartDate<=N'{context['on_date']}'
        AND (p.EndDate IS NULL OR p.EndDate='' OR p.EndDate>=N'{context['on_date']}')
        AND NULLIF(p.GoodsRef,'') IS NOT NULL
        AND NULLIF(p.GoodsGroupRef,'') IS NULL AND NULLIF(p.MainTypeRef,'') IS NULL
        AND NULLIF(p.SubTypeRef,'') IS NULL AND NULLIF(p.CustRef,'') IS NULL
        AND NULLIF(p.CustCtgrRef,'') IS NULL AND NULLIF(p.CustActRef,'') IS NULL
        AND NULLIF(p.CustLevelRef,'') IS NULL AND ISNULL(p.MainCustTypeRef,0)=0
        AND ISNULL(p.SubCustTypeRef,0)=0 AND NULLIF(p.StateRef,'') IS NULL
        AND NULLIF(p.CountyRef,'') IS NULL AND NULLIF(p.AreaRef,'') IS NULL
        AND NULLIF(p.BuyTypeRef,'') IS NULL AND ISNULL(p.UsanceDay,0)=0
        AND NULLIF(p.DealerCtgrRef,'') IS NULL AND NULLIF(p.DCRef,'') IS NULL
        AND ISNULL(p.SaleOfficeRef,0)=0 AND ISNULL(p.MinQty,0)=0
        AND ISNULL(p.MaxQty,0)=0 AND ISNULL(p.BatchNoRef,0)=0 AND NULLIF(p.BatchNo,'') IS NULL
    ) SELECT GoodsRef,PriceId,StartDate,EndDate,ManufacturerPrice,ConsumerPrice,SourceCount
      FROM candidates WHERE PriceRank=1 ORDER BY GoodsRef"""


def resolve_source_prices(settings, goods_ids, on_date, stock_id):
    """Return one source record per requested goods ID, including missing records."""
    context = price_context(stock_id, on_date)
    if not isinstance(goods_ids, (list, tuple, set)) or len(goods_ids) > 10000 or any(
            type(g) is not int or g <= 0 for g in goods_ids):
        raise ContractError('شناسه کالا برای خواندن قیمت معتبر نیست.')
    requested = sorted(set(goods_ids))
    result = {g: dict(context, goods_id=g, price_id=None, start_date='', end_date='',
                      manufacturer_price=None, consumer_price=None, source_count=0) for g in requested}
    if not requested:
        return result
    try:
        with sql_connection(settings) as connection:
            cursor = connection.cursor()
            for start in range(0, len(requested), 500):
                batch = requested[start:start + 500]
                cursor.execute(validate_read_only_sql(source_price_query(batch, on_date, stock_id)).sql)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchmany(len(batch) + 1)
                if len(rows) > len(batch):
                    raise ContractError('منبع قیمت چند نتیجه برای یک کالا برگرداند؛ بررسی لازم است.')
                seen = set()
                for raw in rows:
                    row = dict(zip(columns, raw)); goods_id = row['GoodsRef']
                    if goods_id not in batch or goods_id in seen:
                        raise ContractError('منبع قیمت یک کالا مبهم است؛ بررسی لازم است.')
                    seen.add(goods_id)
                    result[goods_id].update(price_id=str(row['PriceId']), start_date=text(row['StartDate']),
                        end_date=text(row['EndDate']), source_count=int(row['SourceCount']),
                        manufacturer_price=None if row['ManufacturerPrice'] is None else str(row['ManufacturerPrice']),
                        consumer_price=None if row['ConsumerPrice'] is None else str(row['ConsumerPrice']))
    except ContractError:
        raise
    except Exception:
        raise ContractError('بررسی قیمت تولید و مصرف از ورانگر انجام نشد؛ محاسبه با قیمت تأییدنشده انجام نمی‌شود.') from None
    return result


def positive_price(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = Decimal(str(value))
        return value if value.is_finite() and 0 < value <= Decimal('1e15') else None
    except (InvalidOperation, ValueError):
        return None


def source_price_status(rule, product, source):
    """Validate a server-read source against this product and contract period."""
    basis = rule.get('basis') if rule else None
    status = {'status': 'not_required', 'basis': basis, 'price': None, 'message': '',
              'on_date': (source or {}).get('on_date'), 'source': source}
    if basis not in LABELS:
        return status
    identity = f"{text(product.get('product_name'))} ({text(product.get('product_code'))})"
    context = source or {}
    on_date = context.get('on_date')
    if (not on_date or context.get('goods_id') != product.get('goods_id')
            or (rule.get('start_date') and rule['start_date'] > on_date)
            or (rule.get('end_date') and rule['end_date'] < on_date)):
        return dict(status, status='unverified', message=f'قیمت مبنای کالای {identity} در تاریخ قرارداد تأیید نشده است.')
    if context.get('source_count', 0) > 1:
        return dict(status, status='conflict', message=f'منبع {LABELS[basis]} کالای {identity} چندگانه است؛ بررسی لازم است.')
    price = positive_price(context.get(basis + '_price'))
    valid_period = (context.get('price_id') and context.get('start_date')
                    and context['start_date'] <= on_date
                    and (not context.get('end_date') or context['end_date'] >= on_date))
    if price is None or not valid_period or (basis == 'manufacturer' and context.get('source_count') != 1):
        return dict(status, status='missing', message=(f'کالای {identity} در تاریخ {on_date} '
            f'در {context.get("stock_name") or "انبار انتخاب‌شده"} {LABELS[basis]} معتبر ندارد.'))
    return dict(status, status='ready', price=str(price))


def require_source_price(rule, product, source):
    status = source_price_status(rule, product, source)
    if status['status'] != 'ready':
        raise ContractError(status['message'] or 'این قاعده به منبع قیمت تولید یا مصرف متصل نیست.')
    return status['price']
