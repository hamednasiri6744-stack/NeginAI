"""Read-only list of type-20 receipts with no purchase-invoice relation."""
from datetime import datetime, timezone

from app.business_time import jalali_business_date
from app.database import sql_connection
from app.sql_guard import validate_read_only_sql


class ReceiptListError(ValueError):
    pass


def receipt_query(year):
    if type(year) is not int or not 1300 <= year <= 1500:
        raise ReceiptListError('سال مالی باید بین ۱۳۰۰ و ۱۵۰۰ باشد.')
    # TOP is applied to receipts before joining their distinct manufacturers.
    # Any relation reserves a receipt, even an unconfirmed or orphaned invoice.
    return f"""WITH receipts AS (
      SELECT TOP (10001) v.ID,v.AccYear,v.VocherNo,v.VocherDate,v.StockDCRef,
        v.SupplierRef,v.ConfirmDate,v.Comment,v.TVocherNo
      FROM Inv.tblVocherHdr v
      WHERE v.AccYear={year} AND v.VocherTypeCode=20
        AND NOT EXISTS (SELECT 1 FROM ICA.tblSupInvInvoiceRelation r WHERE r.InvVchHdrRef=v.ID)
      ORDER BY v.VocherDate DESC,v.ID DESC
    ), makers AS (
      SELECT DISTINCT i.HdrRef,g.ManufacturerRef
      FROM Inv.tblVocherItm i JOIN receipts r ON r.ID=i.HdrRef
      LEFT JOIN GNR.tblGoods g ON g.ID=i.GoodsRef
    )
    SELECT r.ID receipt_id,r.AccYear fiscal_year,r.VocherNo receipt_no,
      r.VocherDate receipt_date,r.StockDCRef stock_id,
      CONVERT(varbinary(max),s.StockDCName) stock_name,
      r.SupplierRef supplier_id,CONVERT(varbinary(max),p.SupplierName) supplier_name,
      CASE WHEN r.ConfirmDate IS NULL THEN 0 ELSE 1 END confirmed,
      CONVERT(varbinary(max),r.Comment) comment,r.TVocherNo supplier_reference,
      k.ManufacturerRef manufacturer_id,CONVERT(varbinary(max),m.ManufacturerName) manufacturer_name
    FROM receipts r
    LEFT JOIN GNR.tblStockDC s ON s.ID=r.StockDCRef
    LEFT JOIN GNR.tblSupplier p ON p.ID=r.SupplierRef
    LEFT JOIN makers k ON k.HdrRef=r.ID
    LEFT JOIN GNR.tblManufacturer m ON m.ID=k.ManufacturerRef
    ORDER BY r.VocherDate DESC,r.ID DESC,k.ManufacturerRef"""


def _text(value):
    if isinstance(value, bytes):
        value = value.decode('cp1256')
    return str(value or '').strip().replace('ي', 'ی').replace('ك', 'ک')


def normalize_rows(rows):
    receipts = {}
    for raw in rows:
        key = raw['receipt_id']
        if key not in receipts:
            receipts[key] = {**{k: raw[k] for k in (
                'receipt_id', 'fiscal_year', 'receipt_no', 'stock_id',
                'supplier_id', 'supplier_reference')},
                **{k: _text(raw[k]) for k in ('receipt_date', 'stock_name', 'supplier_name', 'comment')},
                'confirmed': bool(raw['confirmed']), 'manufacturers': []}
        maker = {'id': raw['manufacturer_id'], 'name': _text(raw['manufacturer_name']) or 'مشخص نشده'}
        if maker not in receipts[key]['manufacturers']:
            receipts[key]['manufacturers'].append(maker)
    return list(receipts.values())


def list_receipts(settings, year=None):
    year = int(jalali_business_date().split('/')[0]) if year is None else year
    query = validate_read_only_sql(receipt_query(year)).sql
    try:
        with sql_connection(settings) as connection:
            cursor = connection.cursor()
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            raw = cursor.fetchmany(100001)
            if len(raw) > 100000:
                raise ReceiptListError('فهرست بیش از حد مجاز است؛ نتیجهٔ ناقص نمایش داده نشد.')
            items = normalize_rows(dict(zip(columns, row)) for row in raw)
            if len(items) > 10000:
                raise ReceiptListError('بیش از ۱۰٬۰۰۰ رسید در این سال وجود دارد؛ نتیجهٔ ناقص نمایش داده نشد.')
    except ReceiptListError:
        raise
    except Exception:
        raise ReceiptListError('خواندن رسیدهای بدون فاکتور از ورانگر انجام نشد؛ دوباره دریافت کنید.') from None
    return {'items': items, 'year': year, 'total': len(items),
            'confirmed': sum(item['confirmed'] for item in items),
            'read_at': datetime.now(timezone.utc).isoformat(), 'varanegar_write': False}
