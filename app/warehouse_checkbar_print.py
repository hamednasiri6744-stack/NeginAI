"""Read-only checkbar print projection with current same-warehouse prices."""
from html import escape
from math import isfinite

from app import warehouse_checkbar as checkbar
from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, WarehouseAssistantError


def print_document(settings, document_id):
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN')
        document = checkbar._current_document(conn, document_id)
        if document.get('worksheet_workflow') and not document.get('worksheet_approved_at'):
            raise WarehouseAssistantError('ابتدا برگه چک‌بار را برای چاپ و شمارش تأیید کنید.')
        snapshot = conn.execute('SELECT id,imported_at FROM warehouse_snapshots ORDER BY id DESC LIMIT 1').fetchone()
        prices = {row['product_code']: dict(row) for row in conn.execute(
            '''SELECT product_code,manufacturer_price,consumer_price FROM warehouse_snapshot_items
               WHERE snapshot_id=? AND warehouse_code=?''',
            (snapshot['id'], document['warehouse']))} if snapshot else {}
        document['price_snapshot_at'] = snapshot['imported_at'] if snapshot else None
        document['price_snapshot_id'] = snapshot['id'] if snapshot else None
        # Update only this in-memory print projection. Saved revisions and new
        # inspection prices remain intact; absent current prices stay unknown.
        for line in document['lines']:
            current = prices.get(line['product_code'], {})
            line['manufacturer_price'] = current.get('manufacturer_price')
            line['consumer_price'] = current.get('consumer_price')
    return document


def _text(value):
    return escape(str(value if value is not None else ''), quote=True)


def _number(value, missing=''):
    if value is None or value == '':
        return missing
    try:
        number = float(value)
    except (ValueError, TypeError):
        return missing
    if not isfinite(number):
        return missing
    return f'{number:,.2f}'.rstrip('0').rstrip('.')


def render(document):
    meta = document.get('metadata', {})
    def field(label, value):
        content = f'<span class="value">{_text(value)}</span>' if value else '<span class="blank"></span>'
        return f'<div class="field"><span class="label">{label}:</span>{content}</div>'
    metadata = '<div class="meta-row">' + ''.join([
        field('تاریخ', meta.get('date')), field('شماره حواله', meta.get('waybill') or meta.get('reference_no')),
        field('نام راننده', meta.get('driver')), field('تلفن راننده', meta.get('phone'))]) + '</div>'
    metadata += '<div class="meta-row">' + ''.join([
        field('تأمین‌کننده', document['supplier']), field('شماره بارنامه', meta.get('bill_of_lading')),
        field('پلاک', meta.get('plate')), field('تحویل‌گیرنده', meta.get('receiver'))]) + '</div>'
    metadata += '<div class="meta-row">' + field('توضیحات', meta.get('note')) + field('انبار', document['warehouse_name']) + '</div>'
    headings = ['ردیف', 'کد کالا', 'کد کالای<br>تأمین‌کننده', 'بارکد', 'نام کالا', 'مبنا',
                'مصرف‌کننده<br>فعلی', 'تولیدکننده<br>فعلی', 'تعداد سفارش<br>(عدد)', 'تعداد<br>به کارتن', 'تعداد<br>جزء', 'تعداد کل', 'تولید جدید', 'مصرف جدید']
    header = ''.join(f'<th scope="col" class="{"entry-head group-start" if i == 9 else "entry-head" if i > 9 else ""}">{title}</th>' for i, title in enumerate(headings))
    rows = []
    for index, line in enumerate(document['lines'], 1):
        cells = [('', str(index)), ('code', _text(line['product_code'])), ('code', _text(line.get('manufacturer_product_code'))),
                 ('code', _text(line.get('barcode'))), ('name', _text(line['product_name'])), ('count', _number(line.get('conversion_rate'))),
                 ('price', _number(line.get('consumer_price'), '—')), ('price', _number(line.get('manufacturer_price'), '—')),
                 ('count', _number(line.get('order_quantity'), '—')),
                 ('entry group-start', _number(line.get('cartons'))), ('entry', _number(line.get('units'))),
                 ('count', _number(line.get('actual_qty'))), ('entry price', _number(line.get('manufacturer_price_new'))),
                 ('entry price', _number(line.get('consumer_price_new')))]
        rows.append('<tr>' + ''.join(f'<td class="{cls}">{value}</td>' for cls, value in cells) + '</tr>')
    missing = any(line.get('manufacturer_price') is None or line.get('consumer_price') is None for line in document['lines'])
    missing_note = '<p class="price-missing">— : قیمت فعلی کالا در آخرین اطلاعات این انبار موجود نیست.</p>' if missing else ''
    total = sum(line['actual_qty'] for line in document['lines'] if line.get('actual_qty') is not None)
    widths = [7,19,22,28,52,10,22,22,14,16,13,16,18,18]
    cols = ''.join(f'<col style="width:{width}mm">' for width in widths)
    signatures = ''.join(f'<div><div class="signature-space"></div><div class="signature-caption">{label}</div></div>' for label in
                         ['نام و امضای راننده / تحویل‌دهنده', 'نام و امضای تحویل‌گیرنده', 'نام و امضای مسئول انبار'])
    number = _text(document['number'])
    snapshot = _text(document.get('price_snapshot_at'))
    return f'''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>چاپ چک‌بار {number}</title><link rel="stylesheet" href="/static/warehouse-checkbar-print.css?v=1"><script src="/static/warehouse-checkbar-print.js?v=1" defer></script></head><body>
<div class="toolbar"><p>چاپ چک‌بار {number}<small>قیمت‌های فعلی از آخرین اطلاعات موجودی همین انبار · A4 افقی</small></p><div class="toolbar-actions"><a class="back" href="/warehouse-assistant#checkbar">بازگشت به چک‌بارها</a><button id="printCheckbar" type="button">چاپ / ذخیره PDF</button></div></div>
<main class="sheet"><header class="document-head"><div><h1>چک‌بار ورود کالا</h1><div class="subtitle">{number} · نسخه {_text(document.get('revision', 0))}</div></div><div class="brand">دستیار انبار نگین<small>واحد انبار و دریافت کالا</small></div></header>
<section class="metadata" aria-label="اطلاعات تحویل">{metadata}</section>
<table aria-label="اقلام چک‌بار"><colgroup>{cols}</colgroup><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody>
<tfoot><tr><td colspan="9" class="total-label">{len(rows)} قلم کالا · جمع مقدار ثبت‌شده</td><td class="group-start"></td><td></td><td>{_number(total)}</td><td></td><td></td></tr></tfoot></table>{missing_note}
<section class="notes"><strong>ملاحظات کنترل کالا / مغایرت‌ها:</strong><div class="note-line"></div><div class="note-line"></div></section>
<section class="signatures" aria-label="تأیید تحویل">{signatures}</section>
<footer class="foot"><span>{number} · {_text(document['warehouse_name'])}</span><span>قیمت فعلی بر اساس موجودی: <time data-print-date="{snapshot}">{snapshot or 'دریافت نشده'}</time></span></footer></main></body></html>'''
