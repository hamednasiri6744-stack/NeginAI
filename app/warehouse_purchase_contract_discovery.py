"""Read-only discovery of initial purchase-contract proposals from ERP history.

Discovery is deliberately advisory: it stores evidence in the assistant's SQLite
database but never creates or activates a contract and never writes to Varanegar.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import re
from uuid import uuid4

from app.business_time import jalali_business_date
from app.database import sql_connection
from app.sql_guard import validate_read_only_sql
from app.warehouse_purchase_contracts import ContractError, connect, initialize, text


MAX_ITEMS = 10_000
TAX_FACTORS = {4, 8, 12}
COLUMN_DISCOUNT_FACTORS = {2, 6, 3, 7}
# Historical factor allocations prove order and arithmetic, but cannot by
# themselves prove the commercial label "column" versus "invoice tail".
TAIL_PERCENT_FACTORS = set()


def _decimal(value):
    try:
        value = Decimal(str(value))
        return value if value.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def parse_receipt_prices(value):
    """Return (consumer, manufacturer) only for an unambiguous price comment."""
    value = text(value).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
    value = value.replace(',', '').replace('٬', '')
    match = re.fullmatch(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)', value)
    if not match:
        return None
    values = tuple(Decimal(part) for part in match.groups())
    return values if all(value > 0 for value in values) else None


def _percent(value):
    rendered = format(value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP), 'f')
    return rendered.rstrip('0').rstrip('.') if '.' in rendered else rendered


def _signature_label(proposal):
    basis = 'قیمت تولید' if proposal['basis'] == 'manufacturer' else 'قیمت مصرف'
    tax = 'شامل مالیات' if proposal['includes_tax'] else 'بدون مالیات'
    steps = ' سپس '.join(f"{step['percent']}٪" for step in proposal['discount_steps']) or 'بدون تخفیف ستون'
    tail = proposal['tail_discount']
    return f"{basis} · {tax} · تغییر {proposal['adjustment_percent']}٪ · {steps} · انتهایی {tail['value']}٪"


def analyze(rows, supplier_id, supplier_name=''):
    """Infer ranked supplier-level proposals from normalized historical rows.

    Each row contains the invoice item's unit price, receipt price comment and
    allocated invoice factors.  Ambiguous rows remain visible as rejected
    evidence instead of being silently coerced into a rule.
    """
    if type(supplier_id) is not int or supplier_id <= 0:
        raise ContractError('تأمین‌کننده برای کشف قرارداد معتبر نیست.')
    if not isinstance(rows, list) or len(rows) > MAX_ITEMS:
        raise ContractError('حجم سابقهٔ خرید برای کشف قرارداد معتبر نیست.')
    observations = []
    signatures = defaultdict(list)
    rejection_counts = Counter()
    for raw in rows:
        row = dict(raw)
        qty = _decimal(row.get('quantity'))
        price = _decimal(row.get('unit_price'))
        receipt_source = parse_receipt_prices(row.get('price_comment'))
        sources = ({'consumer': receipt_source[0], 'manufacturer': receipt_source[1]}
                   if receipt_source else {})
        for basis in ('consumer', 'manufacturer'):
            dated = _decimal(row.get('dated_' + basis))
            if basis not in sources and dated is not None and dated > 0:
                sources[basis] = dated
        factors = row.get('factors') or []
        reason = None
        if not qty or qty <= 0 or not price or price <= 0:
            reason = 'مقدار یا فی قلم معتبر نیست'
        elif _decimal(row.get('prize_quantity') or 0) != 0:
            reason = 'قلم دارای جایزه است'
        elif row.get('receipt_match') is not True:
            reason = 'مقدار یا منبع رسید با قلم فاکتور یکتا نیست'
        elif not sources:
            reason = 'قیمت تولید/مصرف معتبر در رسید ثبت نشده است'
        normalized_factors = []
        if not reason:
            for factor in factors:
                factor_id = int(factor.get('factor_id') or 0)
                rate = _decimal(factor.get('percent'))
                amount = _decimal(factor.get('amount'))
                if rate is None or amount is None:
                    reason = 'عامل فاکتور ناقص است'; break
                normalized_factors.append((factor_id, rate, amount))
        taxes = {rate for factor_id, rate, amount in normalized_factors if factor_id in TAX_FACTORS and amount != 0}
        if not reason and len(taxes) > 1:
            reason = 'نرخ مالیات قلم چندگانه است'
        tax_rate = next(iter(taxes), Decimal(0))
        unsupported = [factor_id for factor_id, rate, amount in normalized_factors
                       if amount != 0 and factor_id not in TAX_FACTORS | COLUMN_DISCOUNT_FACTORS | TAIL_PERCENT_FACTORS]
        if not reason and unsupported:
            reason = 'عامل مبلغی یا ناشناخته نیازمند تنظیم دستی است'
        if reason:
            rejection_counts[reason] += 1
            observations.append(_observation(row, accepted=False, reason=reason))
            continue
        steps = [rate for factor_id, rate, amount in normalized_factors
                 if factor_id in COLUMN_DISCOUNT_FACTORS and amount != 0]
        tails = [rate for factor_id, rate, amount in normalized_factors
                 if factor_id in TAIL_PERCENT_FACTORS and amount != 0]
        if len(tails) > 1:
            reason = 'بیش از یک تخفیف انتهایی دارد'
            rejection_counts[reason] += 1
            observations.append(_observation(row, accepted=False, reason=reason))
            continue
        # A zero first step is retained because the contract/bridge expect one.
        step_values = steps or [Decimal(0)]
        tail_value = tails[0] if tails else Decimal(0)
        candidates = []
        for basis, source_price in sources.items():
            for includes_tax in (True, False):
                base = source_price / (Decimal(1) + tax_rate / 100) if includes_tax else source_price
                if base <= 0:
                    continue
                adjustment = (price / base - 1) * 100
                if Decimal('-100') <= adjustment <= Decimal('100'):
                    candidates.append((basis, includes_tax, adjustment))
        if not candidates:
            reason = 'فی قلم با قیمت‌های منبع قابل بازسازی نیست'
            rejection_counts[reason] += 1
            observations.append(_observation(row, accepted=False, reason=reason))
            continue
        for basis, includes_tax, adjustment in candidates:
            rounded_adjustment = adjustment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            signature = (basis, includes_tax, rounded_adjustment,
                         tuple(value.quantize(Decimal('0.0001')) for value in step_values),
                         tail_value.quantize(Decimal('0.0001')))
            signatures[signature].append((row, adjustment))
        observations.append(_observation(row, accepted=True, reason=''))

    ranked = []
    eligible_count = sum(1 for row in observations if row['accepted'])
    for signature, matches in signatures.items():
        basis, includes_tax, adjustment, steps, tail = signature
        exact = sum(abs(actual - adjustment) <= Decimal('0.05') for row, actual in matches)
        invoice_count = len({str(row.get('invoice_id')) for row, actual in matches})
        product_count = len({text(row.get('product_code')) for row, actual in matches})
        # Prefer stable, broad patterns; use simplicity only to break equal evidence.
        coverage = Decimal(exact) / Decimal(eligible_count or 1)
        confidence = 'high' if exact >= 3 and invoice_count >= 2 and coverage >= Decimal('.80') else (
            'medium' if exact >= 2 and coverage >= Decimal('.50') else 'review')
        proposal = dict(
            basis=basis, includes_tax=includes_tax, adjustment_percent=_percent(adjustment),
            discount_percent=_percent(steps[0]),
            discount_steps=[{'percent': _percent(value)} for value in steps],
            tail_discount={'kind': 'percent', 'basis': 'net_before_tax', 'value': _percent(tail)},
            evidence_count=exact, invoice_count=invoice_count, product_count=product_count,
            eligible_count=eligible_count, coverage_percent=str((coverage * 100).quantize(Decimal('0.1'))),
            confidence=confidence,
        )
        proposal['label'] = _signature_label(proposal)
        proposal['score'] = (exact, invoice_count, product_count, -abs(adjustment))
        ranked.append(proposal)
    ranked.sort(key=lambda item: item.pop('score'), reverse=True)
    # Multiple algebraic decompositions are intentionally shown; the user chooses
    # the commercial meaning, not merely the closest arithmetic fit.
    return {
        'supplier_id': supplier_id, 'supplier': text(supplier_name),
        'generated_at': datetime.now(timezone.utc).isoformat(), 'advisory_only': True,
        'source': 'confirmed_purchase_invoices_and_linked_receipts',
        'rows_read': len(rows), 'eligible_count': eligible_count,
        'rejected_count': len(rows) - eligible_count, 'rejections': dict(rejection_counts),
        'proposals': ranked[:8], 'observations': observations[:500],
        'warnings': [
            'پیشنهاد کشف‌شده قرارداد فعال نیست و باید همراه فاکتورهای نمونه بازبینی شود.',
            'تاریخ شروع، توافق‌های خارج از فاکتور و آفر کالایی از روی حساب ریاضی قابل حدس قطعی نیست.',
            'تخفیف‌های درصدی تاریخی به‌ترتیب مراحل نمایش داده می‌شوند؛ انتهایی بودن یک مرحله باید از قرارداد واقعی تأیید شود.',
        ],
    }


def _observation(row, accepted, reason):
    return {key: row.get(key) for key in ('invoice_id', 'invoice_no', 'invoice_date', 'product_code', 'product_name')} | {
        'accepted': accepted, 'reason': reason,
    }


def _query_rows(settings, supplier_id, from_year, to_year):
    if any(type(value) is not int for value in (supplier_id, from_year, to_year)):
        raise ContractError('بازهٔ سابقهٔ خرید معتبر نیست.')
    if not 1300 <= from_year <= to_year <= 1500:
        raise ContractError('بازهٔ سال مالی معتبر نیست.')
    scope = f"h.SupplierRef={supplier_id} AND h.AccYear BETWEEN {from_year} AND {to_year} AND h.Status=1 AND h.ConfirmDate IS NOT NULL AND h.SupType=1"
    item_sql = f"""SELECT TOP ({MAX_ITEMS + 1}) h.ID invoice_id,h.VchNo invoice_no,h.VchDate invoice_date,
      h.SupplierRef supplier_id,CONVERT(varbinary(max),s.SupplierName) supplier_name,
      i.ID item_id,i.GoodsRef goods_id,i.Qty quantity,i.PrizeQty prize_quantity,i.Price unit_price,
      g.GoodsCode product_code,CONVERT(varbinary(max),g.GoodsName) product_name
      FROM ICA.TblSupInvoiceHdr h JOIN ICA.TblSupInvoiceItm i ON i.HdrRef=h.ID
      JOIN GNR.tblGoods g ON g.ID=i.GoodsRef LEFT JOIN GNR.tblSupplier s ON s.ID=h.SupplierRef
      WHERE {scope} ORDER BY h.VchDate DESC,h.ID DESC,i.RowOrder"""
    try:
        with sql_connection(settings) as source:
            items = _fetch(source, item_sql, MAX_ITEMS + 1)
            if len(items) > MAX_ITEMS:
                raise ContractError('سابقهٔ این تأمین‌کننده بیش از حد مجاز است؛ بازهٔ سال مالی را محدود کنید.')
            if not items:
                return []
            invoice_ids = sorted({int(row['invoice_id']) for row in items})
            item_ids = sorted({int(row['item_id']) for row in items})
            invoices = ','.join(map(str, invoice_ids)); item_refs = ','.join(map(str, item_ids))
            receipt_sql = f"""SELECT r.SupInvoiceHdrRef invoice_id,i.GoodsRef goods_id,i.ID receipt_item_id,
              vh.StockDCRef stock_id,i.TotalQty receipt_quantity,CONVERT(varbinary(max),i.Comment) price_comment
              FROM ICA.tblSupInvInvoiceRelation r JOIN Inv.tblVocherHdr vh ON vh.ID=r.InvVchHdrRef
              JOIN Inv.tblVocherItm i ON i.HdrRef=r.InvVchHdrRef
              WHERE r.SupInvoiceHdrRef IN ({invoices})"""
            factor_sql = f"""SELECT x.SupInvoiceItmRef item_id,t.TollRef factor_id,t.SysPrice [percent],x.Amount amount
              FROM ICA.TblSupInvoiceItmXToll x JOIN ICA.TblSupInvoiceTolls t ON t.ID=x.SupInvoiceTollsRef
              WHERE x.SupInvoiceItmRef IN ({item_refs}) ORDER BY x.SupInvoiceItmRef,
              CASE t.TollRef WHEN 2 THEN 1 WHEN 6 THEN 2 WHEN 3 THEN 3 WHEN 7 THEN 4 ELSE 99 END,t.ID"""
            receipts = _fetch(source, receipt_sql, MAX_ITEMS * 4)
            factors = _fetch(source, factor_sql, MAX_ITEMS * 6)
    except ContractError:
        raise
    except Exception:
        raise ContractError('خواندن سابقهٔ فاکتورهای خرید از ورانگر انجام نشد؛ هیچ پیشنهادی ذخیره نشد.') from None
    by_receipt = defaultdict(list); by_factor = defaultdict(list)
    for row in receipts: by_receipt[(int(row['invoice_id']), int(row['goods_id']))].append(row)
    for row in factors: by_factor[int(row['item_id'])].append(row)
    result = []; item_counts = Counter((int(row['invoice_id']), int(row['goods_id'])) for row in items)
    for item in items:
        linked = by_receipt[(int(item['invoice_id']), int(item['goods_id']))]
        comments = {text(row.get('price_comment')) for row in linked if text(row.get('price_comment'))}
        stocks = {int(row['stock_id']) for row in linked if row.get('stock_id') is not None}
        invoice_qty = _decimal(item.get('quantity')) or Decimal(0)
        receipt_qty = sum((_decimal(row.get('receipt_quantity')) or Decimal(0) for row in linked), Decimal(0))
        result.append(dict(item, price_comment=next(iter(comments)) if len(comments) == 1 else '',
                           stock_id=next(iter(stocks)) if len(stocks) == 1 else None,
                           receipt_match=bool(linked) and len(stocks) == 1 and receipt_qty == invoice_qty
                               and item_counts[(int(item['invoice_id']), int(item['goods_id']))] == 1,
                           factors=by_factor[int(item['item_id'])]))
    # Prefer the price captured on the linked receipt.  When that old structured
    # convention is absent, use the dated NGT source for the receipt's warehouse.
    from app.warehouse_purchase_prices import resolve_source_prices
    contexts = defaultdict(set)
    for row in result:
        if row['receipt_match'] and row.get('stock_id') in (1, 2, 9):
            contexts[(row['stock_id'], text(row['invoice_date']))].add(int(row['goods_id']))
    dated = {}
    for (stock_id, on_date), goods_ids in contexts.items():
        prices = resolve_source_prices(settings, sorted(goods_ids), on_date, stock_id)
        for goods_id, price in prices.items():
            dated[(stock_id, on_date, goods_id)] = price
    for row in result:
        price = dated.get((row.get('stock_id'), text(row.get('invoice_date')), int(row['goods_id'])), {})
        row['dated_manufacturer'] = price.get('manufacturer_price') if price.get('source_count') == 1 else None
        row['dated_consumer'] = price.get('consumer_price') if price.get('price_id') else None
    return result


def _fetch(connection, query, limit):
    cursor = connection.cursor(); cursor.execute(validate_read_only_sql(query).sql)
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchmany(limit + 1)
    if len(rows) > limit:
        raise ContractError('حجم شواهد خرید بیش از حد مجاز است.')
    return [{column: (value.decode('cp1256') if isinstance(value, bytes) else value)
             for column, value in zip(columns, row)} for row in rows]


def discover(settings, supplier_id, from_year=None, to_year=None):
    initialize(settings)
    current_year = int(jalali_business_date()[:4])
    from_year = current_year - 1 if from_year is None else int(from_year)
    to_year = current_year if to_year is None else int(to_year)
    with connect(settings) as connection:
        catalog_row = connection.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=? LIMIT 1', (supplier_id,)).fetchone()
    if not catalog_row:
        raise ContractError('تأمین‌کننده در فهرست خرید نیست؛ ابتدا فهرست را به‌روز کنید.')
    supplier = json.loads(catalog_row[0])['supplier']
    result = analyze(_query_rows(settings, supplier_id, from_year, to_year), supplier_id, supplier)
    result.update(from_year=from_year, to_year=to_year, run_id=str(uuid4()))
    with connect(settings) as connection:
        connection.execute('''CREATE TABLE IF NOT EXISTS warehouse_purchase_contract_discovery (
          run_id TEXT PRIMARY KEY,supplier_id INTEGER NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL)''')
        connection.execute('INSERT INTO warehouse_purchase_contract_discovery VALUES (?,?,?,?)',
                           (result['run_id'], supplier_id, json.dumps(result, ensure_ascii=False), result['generated_at']))
    return result


def latest(settings, supplier_id):
    initialize(settings)
    with connect(settings) as connection:
        connection.execute('''CREATE TABLE IF NOT EXISTS warehouse_purchase_contract_discovery (
          run_id TEXT PRIMARY KEY,supplier_id INTEGER NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL)''')
        row = connection.execute('SELECT payload FROM warehouse_purchase_contract_discovery WHERE supplier_id=? ORDER BY created_at DESC LIMIT 1', (supplier_id,)).fetchone()
    return json.loads(row[0]) if row else None
