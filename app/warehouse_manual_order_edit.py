"""Explicit carton editing of unsent manual drafts; no external delivery."""
from app.warehouse_assistant_service import (
    WarehouseAssistantError, _order_from_row, _now, warehouse_connection,
    init_warehouse_store, ensure_orderable,
)


def update_lines(settings, username, order_id, lines, *, expected_token, include_all=False, delivery_date=None):
    from app.warehouse_order_delivery import clean_delivery_date, write_date
    if delivery_date is not None:
        delivery_date = clean_delivery_date(delivery_date, optional=True)
    requested = {}
    for line in lines:
        code, cartons = str(line.get('product_code', '')).strip(), line.get('cartons')
        if not code or code in requested or isinstance(cartons, bool) or not isinstance(cartons, int) or not 0 <= cartons <= 1_000_000:
            raise WarehouseAssistantError('کد کالا یا تعداد کارتن معتبر نیست.')
        requested[code] = cartons
    if not any(requested.values()):
        raise WarehouseAssistantError('حداقل یک قلم باید در سفارش باقی بماند.')
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM supplier_orders WHERE id=?', (order_id,)).fetchone()
        if row is None or (not include_all and row['created_by'] != username):
            raise WarehouseAssistantError('سفارش تأمین‌کننده پیدا نشد.')
        order = _order_from_row(conn, row)
        if not order['can_edit']:
            raise WarehouseAssistantError('فقط سفارش تأییدنشده و ارسال‌نشده قابل ویرایش است؛ ابتدا لغو تأیید کنید.')
        if expected_token != order['email_send_token']:
            raise WarehouseAssistantError('سفارش تغییر کرده؛ پیش‌نمایش را دوباره باز کنید.')
        if set(requested) != {line['product_code'] for line in order['lines']}:
            raise WarehouseAssistantError('فهرست اقلام با سفارش یکسان نیست.')
        ensure_orderable(conn, order['warehouse_code'], [code for code, count in requested.items() if count])
        total_quantity = total_value = 0
        for line in order['lines']:
            count = requested[line['product_code']]
            if not count:
                conn.execute('DELETE FROM supplier_order_lines WHERE order_id=? AND product_code=?', (order_id, line['product_code']))
                continue
            quantity = count * max(1, float(line['conversion_rate']))
            value = quantity * float(line['buy_price'])
            total_quantity += quantity
            total_value += value
            conn.execute('''UPDATE supplier_order_lines SET cartons=?,order_quantity=?,requested_quantity=?,estimated_value=?
                            WHERE order_id=? AND product_code=?''',
                         (count, quantity, quantity, value, order_id, line['product_code']))
        conn.execute('UPDATE supplier_orders SET total_quantity=?,estimated_value=?,edited_by=?,edited_at=? WHERE id=?',
                     (total_quantity, total_value, username[:100], _now(), order_id))
        if delivery_date is not None:
            write_date(conn, 'supplier_order', order_id, delivery_date, username, _now())
        return _order_from_row(conn, conn.execute('SELECT * FROM supplier_orders WHERE id=?', (order_id,)).fetchone())
