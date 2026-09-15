"""Internally approved purchase orders and manually reconciled inbound receipts.

Quantities are base units; no ERP write, stock mutation, or external delivery.
"""
import hashlib
import json
import math
from datetime import datetime


def supply_rows(conn, warehouse=None, preorder_id=None):
    clauses, params = [], []
    if warehouse is not None:
        clauses.append('o.warehouse_code=?')
        params.append(warehouse)
    if preorder_id is not None:
        clauses.append('o.id=?')
        params.append(preorder_id)
    return conn.execute("""SELECT base.*,
        CASE WHEN delivery_ended THEN MAX(0,order_quantity-received_qty)
          ELSE adjustment_closed_qty END AS closed_qty FROM (SELECT o.id AS preorder_id,o.warehouse_code,o.preorder_number,
        o.supplier,o.source_supplier_order_id,l.product_code,l.product_name,l.conversion_rate,l.order_quantity,
        (SELECT i.group_level3 FROM warehouse_snapshot_items i WHERE i.snapshot_id=o.snapshot_id
          AND i.warehouse_code=o.warehouse_code AND i.product_code=l.product_code LIMIT 1) AS group_level3,
        (SELECT i.manufacturer_product_code FROM warehouse_snapshot_items i WHERE i.snapshot_id=o.snapshot_id
          AND i.warehouse_code=o.warehouse_code AND i.product_code=l.product_code LIMIT 1) AS manufacturer_product_code,
        (SELECT i.barcode FROM warehouse_snapshot_items i WHERE i.snapshot_id=o.snapshot_id
          AND i.warehouse_code=o.warehouse_code AND i.product_code=l.product_code LIMIT 1) AS barcode,
        COALESCE((SELECT SUM(r.quantity) FROM warehouse_fulfillment_receipts r
          WHERE r.preorder_id=o.id AND r.product_code=l.product_code),0)
        + COALESCE((SELECT SUM(a.quantity) FROM warehouse_receipt_allocations a
          JOIN warehouse_checkbar_transfers t ON t.document_id=a.document_id
          WHERE a.preorder_id=o.id AND a.product_code=l.product_code AND t.status='sent'
          AND NOT EXISTS(SELECT 1 FROM warehouse_checkbar_confirmations c WHERE c.document_id=a.document_id AND c.active=1)),0)
        + COALESCE((SELECT SUM(a.quantity) FROM warehouse_receipt_allocations a
          JOIN warehouse_checkbar_confirmations c ON c.document_id=a.document_id AND c.active=1
          WHERE a.preorder_id=o.id AND a.product_code=l.product_code),0) AS received_qty,
        COALESCE((SELECT SUM(a.quantity) FROM warehouse_receipt_allocations a
          JOIN warehouse_checkbar_transfers t ON t.document_id=a.document_id
          WHERE a.preorder_id=o.id AND a.product_code=l.product_code AND t.status='pending'
          AND NOT EXISTS(SELECT 1 FROM warehouse_checkbar_confirmations c WHERE c.document_id=a.document_id AND c.active=1)),0) AS reserved_qty,
        COALESCE((SELECT SUM(a.quantity) FROM warehouse_fulfillment_adjustments a
          WHERE a.preorder_id=o.id AND a.product_code=l.product_code),0) AS adjustment_closed_qty,
        EXISTS(SELECT 1 FROM warehouse_delivery_completions e WHERE e.preorder_id=o.id) AS delivery_ended,
        o.approved_at AS sent_at
        FROM warehouse_automatic_preorders o
        JOIN warehouse_automatic_preorder_lines l ON l.preorder_id=o.id
        WHERE o.status IN ('approved','send_requested')"""
        + (' AND ' + ' AND '.join(clauses) if clauses else '')
        + ' ORDER BY o.id,l.product_code) base', params).fetchall()


def supply_position(conn, warehouse):
    rows = supply_rows(conn, warehouse=warehouse)
    quantities = {}
    for row in rows:
        quantities[row['product_code']] = quantities.get(row['product_code'], 0) + max(
            0, float(row['order_quantity']) - float(row['received_qty']) - float(row['closed_qty']))
    from app.warehouse_order_receipts import pending_stock
    pending, review = pending_stock(conn, warehouse)
    from app.warehouse_rebalancing import reservations
    transfers, outgoing, transfer_rows = reservations(conn, warehouse)
    for code, quantity in transfers.items():
        quantities[code] = quantities.get(code, 0) + quantity
    from app.warehouse_native_transit import position, current_snapshot
    native, _, native_rows = position(conn, warehouse)
    native_snapshot = current_snapshot(conn)
    for code, quantity in native.items():
        quantities[code] = quantities.get(code, 0) + quantity
    revision = hashlib.sha256(json.dumps([[
        (r['preorder_id'], r['product_code'], r['order_quantity'], r['received_qty'], r['closed_qty'], r['reserved_qty'])
        for r in rows], pending, sorted(review), transfer_rows, native_snapshot, native_rows], sort_keys=True, separators=(',', ':')).encode()).hexdigest() if rows or pending or review or transfer_rows or native_snapshot is not None else ''
    return quantities, revision


def fulfillment_detail(conn, preorder_id):
    rows = supply_rows(conn, preorder_id=preorder_id)
    if not rows:
        return None
    lines = [dict(row, remaining_qty=max(0, float(row['order_quantity']) - float(row['received_qty']) - float(row['closed_qty']))) for row in rows]
    remaining = sum(line['remaining_qty'] for line in lines)
    history = [dict(r) for r in conn.execute('SELECT * FROM warehouse_fulfillment_adjustments WHERE preorder_id=? ORDER BY id', (preorder_id,))]
    receipts = [dict(r) for r in conn.execute('''SELECT a.*,COALESCE(t.status,'checkbar_confirmed') AS status,t.result_json,
        COALESCE(s.status,CASE WHEN c.active=1 THEN 'waiting' END) AS stock_status,
        c.revision AS confirmation_revision FROM warehouse_receipt_allocations a
        LEFT JOIN warehouse_checkbar_transfers t ON t.document_id=a.document_id
        LEFT JOIN warehouse_checkbar_confirmations c ON c.document_id=a.document_id
        LEFT JOIN warehouse_receipt_stock_state s ON s.document_id=a.document_id
        WHERE a.preorder_id=? AND (t.status IN ('pending','sent') OR c.active=1)''', (preorder_id,))]
    # Include confirmation revisions/deletions even when their allocation is removed.
    revision = conn.execute('SELECT COUNT(*) FROM warehouse_fulfillment_receipts WHERE preorder_id=?', (preorder_id,)).fetchone()[0] + len(history) + sum(r['status']=='sent' and r['confirmation_revision'] is None for r in receipts)
    revision += conn.execute('SELECT COALESCE(SUM(c.revision+1),0) FROM warehouse_checkbar_confirmations c JOIN warehouse_checkbars d ON d.id=c.document_id WHERE d.warehouse_code=? AND d.supplier=?',(rows[0]['warehouse_code'],rows[0]['supplier'])).fetchone()[0]
    closed = sum(line['closed_qty'] for line in lines)
    completion = conn.execute('SELECT * FROM warehouse_delivery_completions WHERE preorder_id=?',(preorder_id,)).fetchone()
    revision += bool(completion)
    return {
        'status': 'closed' if completion else 'awaiting_supply' if remaining > 0 else ('closed' if closed > 0 else 'received'),
        'delivery_ended': bool(completion), 'completion': dict(completion) if completion else None,
        'closed_qty': closed, 'history': history, 'linked_receipts': receipts,
        'manual_receive_allowed': not receipts and not closed and not completion,
        'revision': revision, 'sent_at': rows[0]['sent_at'], 'lines': lines,
        'remaining_qty': remaining,
        'remaining_cartons': sum(line['remaining_qty'] / max(1, line['conversion_rate']) for line in lines),
        'received_qty': sum(line['received_qty'] for line in lines),
    }


def list_fulfillment_orders(settings, include_completed=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _automatic_preorder_from_row
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        rows = conn.execute("""SELECT o.* FROM warehouse_automatic_preorders o
            WHERE o.status IN ('approved','send_requested')
            ORDER BY o.id DESC""").fetchall()
        result = []
        for row in rows:
            info = fulfillment_detail(conn, row['id'])
            if info and (include_completed or info['status'] == 'awaiting_supply'):
                source_kind = "manual" if row["source_supplier_order_id"] is not None else "automatic"
                result.append(dict(
                    _automatic_preorder_from_row(conn, row),
                    source_kind=source_kind,
                    order_number=row["preorder_number"],
                    fulfillment=info,
                ))
        return result


def receive_fulfillment(settings, username, preorder_id, *, expected_revision,
                        snapshot_id, inventory_reflected, reference, lines):
    from app.warehouse_assistant_service import (
        init_warehouse_store, warehouse_connection, WarehouseAssistantError, _now,
    )
    if not inventory_reflected or not str(reference).strip():
        raise WarehouseAssistantError('ابتدا رسید وارنگر و بازخوانی موجودی را تأیید و شماره رسید را وارد کنید.')
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        detail = fulfillment_detail(conn, preorder_id)
        if detail is None:
            raise WarehouseAssistantError('این سفارش ارسال موفق ندارد.')
        if detail['revision'] != expected_revision:
            raise WarehouseAssistantError('دریافت این سفارش تغییر کرده است؛ صندوق را بازخوانی کنید.')
        if not detail['manual_receive_allowed']:
            raise WarehouseAssistantError('این سفارش دریافت از چک‌بار یا ماندهٔ بسته‌شده دارد؛ دریافت بعدی را از چک‌بار ثبت کنید تا دوبار حساب نشود.')
        snapshot = conn.execute('SELECT id,imported_at FROM warehouse_snapshots ORDER BY id DESC LIMIT 1').fetchone()
        if snapshot is None or snapshot['id'] != snapshot_id:
            raise WarehouseAssistantError('موجودی تغییر کرده است؛ صفحه را بازخوانی کنید.')
        try:
            current = datetime.fromisoformat(snapshot['imported_at'])
            sent = datetime.fromisoformat(detail['sent_at'])
            if current < sent:
                raise ValueError('old snapshot')
        except (ValueError, TypeError):
            raise WarehouseAssistantError('بعد از ثبت رسید در وارنگر، ابتدا موجودی را بازخوانی کنید.') from None
        by_code = {line['product_code']: line for line in detail['lines']}
        seen, changes = set(), []
        for line in lines:
            code = str(line['product_code'])
            total = float(line['received_qty'])
            if code in seen or code not in by_code or not math.isfinite(total):
                raise WarehouseAssistantError('اقلام دریافت نامعتبر یا تکراری هستند.')
            seen.add(code)
            before = by_code[code]
            if total < before['received_qty'] or total > before['order_quantity']:
                raise WarehouseAssistantError('دریافت تجمعی باید بین دریافت قبلی و تعداد سفارش باشد.')
            if total > before['received_qty']:
                changes.append((preorder_id, code, total-before['received_qty'], snapshot_id,
                                str(reference).strip()[:200], username[:100], _now()))
        if not changes:
            raise WarehouseAssistantError('مقدار دریافت جدیدی وارد نشده است.')
        conn.executemany("""INSERT INTO warehouse_fulfillment_receipts
            (preorder_id,product_code,quantity,snapshot_id,reference,recorded_by,recorded_at)
            VALUES(?,?,?,?,?,?,?)""", changes)
        return fulfillment_detail(conn, preorder_id)
