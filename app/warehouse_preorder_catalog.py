"""Snapshot-backed supplier picker; no ERP calls or external delivery."""
from app.business_time import jalali_business_date, tehran_now


def ensure_editable(conn, order):
    from app.warehouse_assistant_service import WarehouseAssistantError, _supplier_portal_order_status
    if order is None:
        raise WarehouseAssistantError('سفارش پیدا نشد.')
    portal = _supplier_portal_order_status(conn, 'automatic_preorder', order['id']) or {}
    if portal.get('dispatch_locked'):
        raise WarehouseAssistantError('سفارش پس از شروع ارسال لینک قابل تغییر نیست.')
    if order['status'] != 'awaiting_approval' or order['business_date'] != jalali_business_date(tehran_now()):
        raise WarehouseAssistantError('افزودن کالا فقط به سفارش تأییدنشدهٔ روز جاری مجاز است.')
    if conn.execute("SELECT 1 FROM warehouse_email_attempts WHERE preorder_id=? AND status IN ('sending','sent','unknown')", (order['id'],)).fetchone():
        raise WarehouseAssistantError('سفارش دارای ارسال فعال یا ثبت‌شده قابل تغییر نیست.')


def catalog_items(conn, order):
    from app.warehouse_assistant_service import (
        _inventory_information_item, _supply_scope_is_strict, _clean_number, LAST_STOCK_DEMAND_BASIS,
        ORDER_CYCLE_BLOCKED_SQL,
    )
    from app.warehouse_fulfillment import supply_position
    # Current stock and the receipt ledger must describe the same local snapshot.
    snapshot = conn.execute('SELECT * FROM warehouse_snapshots ORDER BY id DESC LIMIT 1').fetchone()
    if snapshot is None:
        return []
    rows = conn.execute(f'''SELECT * FROM warehouse_snapshot_items
        WHERE snapshot_id=? AND warehouse_code=? AND manufacturer=? COLLATE NOCASE
        AND NOT {ORDER_CYCLE_BLOCKED_SQL}
        ORDER BY product_name,product_code''',
        (snapshot['id'], order['warehouse_code'], order['supplier'])).fetchall()
    allowed = None
    if _supply_scope_is_strict(conn):
        allowed = {r[0].casefold() for r in conn.execute('''SELECT brand FROM warehouse_supply_scope
            WHERE warehouse_code=? AND supplier=? COLLATE NOCASE AND enabled=1''',
            (order['warehouse_code'], order['supplier']))}
    incoming, _ = supply_position(conn, order['warehouse_code'])
    from app.warehouse_rebalancing import reservations
    outgoing = reservations(conn, order['warehouse_code'])[1]
    from app.warehouse_order_receipts import pending_stock
    pending, review = pending_stock(conn, order['warehouse_code'])
    result = []
    for row in rows:
        raw = dict(row)
        raw['transfer_reserved_qty'] = outgoing.get(row['product_code'], 0)
        raw['in_transit_qty'] = incoming.get(row['product_code'], 0)
        raw['pending_receipt_qty'] = pending.get(row['product_code'], 0)
        raw['receipt_review_required'] = row['product_code'] in review
        item = _inventory_information_item(raw)
        item['conversion_rate'] = max(1, item['conversion_rate'])
        days = (max(0, int(row['sales_rate_days'] or 0))
                if snapshot['demand_basis'] in ('net_sales_stockout_adjusted', LAST_STOCK_DEMAND_BASIS)
                else max(0, int(snapshot['period_days'] or 60)))
        daily = max(0, float(row['period_out'] or 0)) / days if days else 0
        item.update(average_daily_out=_clean_number(daily),
                    coverage_days=_clean_number(item['effective_procurement_qty']/daily) if daily else None,
                    approximate_price=max(0, float(row['buy_price'] or 0)),
                    can_add=row['product_code'] not in review and (allowed is None or row['brand'].casefold() in allowed))
        result.append(item)
    return result


def get_preorder_catalog(settings, preorder_id):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _automatic_preorder_from_row
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN')
        order = conn.execute('SELECT * FROM warehouse_automatic_preorders WHERE id=?', (preorder_id,)).fetchone()
        ensure_editable(conn, order)
        snapshot = conn.execute('SELECT id,imported_at FROM warehouse_snapshots ORDER BY id DESC LIMIT 1').fetchone()
        return {'items': catalog_items(conn, order), 'supplier': order['supplier'],
                'warehouse_name': order['warehouse_name'], 'snapshot_id': snapshot['id'] if snapshot else None,
                'snapshot_imported_at': snapshot['imported_at'] if snapshot else None,
                'expected_token': _automatic_preorder_from_row(conn, order)['email_send_token']}
