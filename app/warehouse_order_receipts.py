"""Order allocations and auditable balance closures; all writes are local SQLite.

Pending allocations reserve capacity, but only a sent transfer consumes an order.
The frozen transfer is the authority for replay; no matching is redone on recovery.
"""
import hashlib
import json
from decimal import Decimal, InvalidOperation


def fail(message):
    from app.warehouse_assistant_service import WarehouseAssistantError
    raise WarehouseAssistantError(message)


def quantity(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or result > 1_000_000_000 or result != result.quantize(Decimal('.001')):
            raise ValueError()
        return result
    except (ValueError, InvalidOperation, TypeError):
        fail('مقدار تخصیص باید غیرمنفی و حداکثر سه رقم اعشار باشد.')


def remaining(row):
    return max(Decimal(0), (Decimal(str(row['order_quantity'])) - Decimal(str(row['received_qty'])) - Decimal(str(row['closed_qty']))).quantize(Decimal('.001')))


def init_schema(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS warehouse_receipt_allocations (
          document_id INTEGER NOT NULL REFERENCES warehouse_checkbars(id),
          source_row INTEGER NOT NULL,
          preorder_id INTEGER NOT NULL REFERENCES warehouse_automatic_preorders(id),
          product_code TEXT NOT NULL,
          quantity REAL NOT NULL CHECK(quantity>0),
          PRIMARY KEY(document_id,source_row,preorder_id)
        );
        CREATE INDEX IF NOT EXISTS idx_receipt_allocations_order
          ON warehouse_receipt_allocations(preorder_id,product_code);
        CREATE TABLE IF NOT EXISTS warehouse_fulfillment_adjustments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          preorder_id INTEGER NOT NULL REFERENCES warehouse_automatic_preorders(id),
          product_code TEXT NOT NULL, quantity REAL NOT NULL CHECK(quantity<>0),
          reason TEXT NOT NULL, recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL,
          request_id TEXT NOT NULL, request_hash TEXT NOT NULL,
          UNIQUE(preorder_id,request_id,product_code)
        );
        CREATE TABLE IF NOT EXISTS warehouse_delivery_completions (
          preorder_id INTEGER PRIMARY KEY REFERENCES warehouse_automatic_preorders(id),
          recorded_by TEXT NOT NULL, recorded_at TEXT NOT NULL,
          request_id TEXT NOT NULL, expected_revision INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS warehouse_receipt_stock_state (
          document_id INTEGER PRIMARY KEY REFERENCES warehouse_checkbars(id),
          warehouse_code TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('waiting','reflected','review')),
          snapshot_id INTEGER REFERENCES warehouse_snapshots(id),
          evidence_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS warehouse_checkbar_confirmations (
          document_id INTEGER PRIMARY KEY REFERENCES warehouse_checkbars(id),
          revision INTEGER NOT NULL,
          active INTEGER NOT NULL CHECK(active IN (0,1)),
          physical_json TEXT NOT NULL,
          confirmed_by TEXT NOT NULL, confirmed_at TEXT NOT NULL
        );
    ''')


def matching(conn, doc, requested=None, expected_revision='', exclude_document_id=None):
    from app.warehouse_fulfillment import supply_rows
    orders = [dict(r) for r in supply_rows(conn, doc['warehouse'])
              if r['supplier'] == doc['supplier'] and not r['delivery_ended']]
    if doc.get('remaining_order_id') is not None:
        orders = [r for r in orders if r['preorder_id'] == doc['remaining_order_id']]
    if exclude_document_id is not None:
        # Editing an untransferred confirmation can reuse its own consumed capacity.
        own = {(r['preorder_id'],r['product_code']):r['quantity'] for r in conn.execute('''
            SELECT a.preorder_id,a.product_code,SUM(a.quantity) AS quantity
            FROM warehouse_receipt_allocations a JOIN warehouse_checkbar_confirmations c ON c.document_id=a.document_id
            WHERE a.document_id=? AND c.active=1 GROUP BY a.preorder_id,a.product_code''',(exclude_document_id,))}
        for row in orders:
            row['received_qty'] -= own.get((row['preorder_id'],row['product_code']),0)
    orders.sort(key=lambda r: (r['sent_at'], r['preorder_id'], r['product_code']))
    revision = hashlib.sha256(json.dumps(orders, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if expected_revision and expected_revision != revision:
        fail('ماندهٔ سفارش‌ها تغییر کرده است؛ تطبیق سفارش‌ها را بازخوانی کنید.')
    available = {(r['preorder_id'], r['product_code']): max(Decimal(0), remaining(r)-Decimal(str(r['reserved_qty'])).quantize(Decimal('.001'))) for r in orders}
    physical = {i: line for i, line in enumerate(doc['lines'], 1) if line.get('actual_qty') is not None and quantity(line['actual_qty']) > 0}
    chosen = []
    if requested is None:
        for index, line in physical.items():
            left = quantity(line['actual_qty'])
            for order in orders:
                key = order['preorder_id'], order['product_code']
                if key[1] != line['product_code']:
                    continue
                take = min(left, available[key])
                if take:
                    chosen.append(dict(source_row=index, preorder_id=key[0], product_code=key[1], quantity=float(take)))
                    available[key] -= take
                    left -= take
    else:
        seen, totals = set(), {}
        for item in requested:
            index, order_id = item['source_row'], item['preorder_id']
            if (index, order_id) in seen or index not in physical:
                fail('تخصیص تکراری یا ردیف چک‌بار نامعتبر است.')
            seen.add((index, order_id))
            code = physical[index]['product_code']
            key = order_id, code
            amount = quantity(item['quantity'])
            if key not in available or amount > available[key]:
                fail('تخصیص از ماندهٔ آزاد سفارش بیشتر است یا سفارش متعلق به این کالا، انبار و تأمین‌کننده نیست.')
            totals[index] = totals.get(index, Decimal(0)) + amount
            if totals[index] > quantity(physical[index]['actual_qty']):
                fail('جمع تخصیص از تعداد شمارش‌شدهٔ چک‌بار بیشتر است.')
            available[key] -= amount
            if amount:
                chosen.append(dict(source_row=index, preorder_id=order_id, product_code=code, quantity=float(amount)))
    chosen.sort(key=lambda a: (a['source_row'], a['preorder_id']))
    rows = []
    for index, line in physical.items():
        allocated = sum((quantity(a['quantity']) for a in chosen if a['source_row'] == index), Decimal(0))
        candidates = [dict(preorder_id=r['preorder_id'], number=r['preorder_number'], sent_at=r['sent_at'],
                           remaining_qty=float(remaining(r)), reserved_qty=r['reserved_qty'], conversion_rate=r['conversion_rate'])
                      for r in orders if r['product_code'] == line['product_code'] and remaining(r) > 0]
        rows.append(dict(source_row=index, product_code=line['product_code'], product_name=line.get('product_name',''),
                         manufacturer_product_code=line.get('manufacturer_product_code',''), barcode=line.get('barcode',''),
                         group_level3=line.get('group_level3',''),
                         actual_qty=line['actual_qty'], unallocated_qty=float(quantity(line['actual_qty'])-allocated), orders=candidates))
    return dict(version=1, revision=revision, allocations=chosen, rows=rows,
                unallocated_qty=float(sum((quantity(r['unallocated_qty']) for r in rows), Decimal(0))))


def reserve(conn, document_id, plan):
    # Only called while creating/replacing a non-sent intent in BEGIN IMMEDIATE.
    conn.execute('DELETE FROM warehouse_receipt_allocations WHERE document_id=?', (document_id,))
    conn.executemany('''INSERT INTO warehouse_receipt_allocations
        (document_id,source_row,preorder_id,product_code,quantity) VALUES(?,?,?,?,?)''',
        [(document_id,a['source_row'],a['preorder_id'],a['product_code'],a['quantity']) for a in plan['allocations']])


def sent(conn, row):
    from app.warehouse_assistant_service import _now
    payload = json.loads(row['payload_json'])
    if 'order_matching' not in payload:
        return  # A legacy pending transfer is never retrospectively allocated.
    warehouse = conn.execute('SELECT warehouse_code FROM warehouse_checkbars WHERE id=?',(row['document_id'],)).fetchone()[0]
    conn.execute('''INSERT OR IGNORE INTO warehouse_receipt_stock_state
        (document_id,warehouse_code,status,updated_at) VALUES(?,?,'waiting',?)''', (row['document_id'],warehouse,_now()))


def pending_stock(conn, warehouse):
    quantities, review = {}, set()
    from app.warehouse_transfer_reflection import review_codes
    review.update(review_codes(conn,warehouse))
    from app.warehouse_native_transit import position
    review.update(position(conn,warehouse)[1])
    for row in conn.execute('''SELECT s.status,s.evidence_json,t.payload_json FROM warehouse_receipt_stock_state s
        JOIN warehouse_checkbar_transfers t ON t.document_id=s.document_id
        WHERE s.warehouse_code=? AND s.status<>'reflected' AND t.status='sent' ''', (warehouse,)):
        payload=json.loads(row['payload_json'])
        evidence=json.loads(row['evidence_json'] or '{}')
        lines=payload['lines']
        if payload.get('price_workflow_version')==2 and row['status']=='waiting':
            lines=evidence.get('pending_lines',[l for l in lines if l['price_mode']!='changed'])
        for line in lines:
            code = line['product_code']
            quantities[code] = quantities.get(code, 0) + float(line['quantity'])
            if row['status'] == 'review':
                review.add(code)
    for row in conn.execute('''SELECT c.physical_json FROM warehouse_checkbar_confirmations c
        JOIN warehouse_checkbars d ON d.id=c.document_id
        LEFT JOIN warehouse_checkbar_transfers t ON t.document_id=c.document_id
        WHERE c.active=1 AND d.warehouse_code=? AND (t.status IS NULL OR t.status<>'sent')''',(warehouse,)):
        for line in json.loads(row[0]):
            code=line['product_code']
            quantities[code]=quantities.get(code,0)+float(line['quantity'])
    for row in conn.execute("SELECT t.payload_json FROM warehouse_checkbar_transfers t JOIN warehouse_checkbars c ON c.id=t.document_id WHERE t.status='pending' AND c.warehouse_code=?", (warehouse,)):
        review.update(line['product_code'] for line in json.loads(row[0])['lines'])
    for row in conn.execute('''SELECT h.payload_json FROM warehouse_checkbar_transfer_history h
        JOIN warehouse_receipt_stock_state s ON s.document_id=h.document_id
        WHERE s.warehouse_code=? AND s.status='review' ''',(warehouse,)):
        review.update(line['product_code'] for line in json.loads(row[0])['lines'])
    return quantities, review


def confirm_checkbar(conn, document_id, doc, username):
    from app.warehouse_assistant_service import _now
    reserve(conn,document_id,doc['order_matching'])
    physical=[dict(product_code=line['product_code'],quantity=float(quantity(line['actual_qty'])))
              for line in doc['lines'] if line['actual_qty'] is not None and quantity(line['actual_qty'])>0]
    conn.execute('''INSERT INTO warehouse_checkbar_confirmations
        (document_id,revision,active,physical_json,confirmed_by,confirmed_at) VALUES(?,?,1,?,?,?)
        ON CONFLICT(document_id) DO UPDATE SET revision=excluded.revision,active=1,
        physical_json=excluded.physical_json,confirmed_by=excluded.confirmed_by,confirmed_at=excluded.confirmed_at''',
        (document_id,doc.get('revision',0),json.dumps(physical),username,_now()))


def ensure_cycle_allowed(conn, warehouse, codes):
    """A manual exclusion applies to new ordering, not to receiving existing stock."""
    requested = set(codes)
    blocked = {row[0] for row in conn.execute(
        "SELECT product_code FROM warehouse_order_cycle_overrides WHERE warehouse_code=? AND forced_active=0",
        (warehouse,))}.intersection(requested)
    if blocked:
        fail('این کالاها به‌صورت دستی خارج از چرخه سفارش هستند: ' + '، '.join(sorted(blocked)[:10]))


def ensure_orderable(conn, warehouse, codes):
    codes = set(codes)
    ensure_cycle_allowed(conn, warehouse, codes)
    blocked = pending_stock(conn, warehouse)[1].intersection(codes)
    if blocked:
        fail('رسید این کالاها نیازمند پیگیری یا تطبیق با ورانگر است؛ قبل از سفارش جدید بررسی کنید: ' + '، '.join(sorted(blocked)[:10]))


def adjust_balance(settings, username, preorder_id, *, expected_revision, request_id, reason, lines, reopen=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    from app.warehouse_fulfillment import fulfillment_detail
    reason = reason.strip()
    if not request_id or not lines:
        fail('شناسهٔ درخواست و اقلام مانده الزامی است.')
    encoded = json.dumps(dict(reason=reason,lines=lines,reopen=reopen,expected_revision=expected_revision),sort_keys=True)
    digest = hashlib.sha256(encoded.encode()).hexdigest()
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        old = conn.execute('SELECT request_hash FROM warehouse_fulfillment_adjustments WHERE preorder_id=? AND request_id=?',(preorder_id,request_id)).fetchone()
        if old:
            if old[0] != digest:
                fail('شناسهٔ درخواست قبلاً با اطلاعات دیگری استفاده شده است.')
            return fulfillment_detail(conn,preorder_id)
        info = fulfillment_detail(conn,preorder_id)
        if info is None or info['revision'] != expected_revision:
            fail('ماندهٔ سفارش تغییر کرده است؛ صفحه را بازخوانی کنید.')
        if info['delivery_ended']:
            fail('تحویل این سفارش پایان یافته است؛ بستن یا بازگشایی مانده مجاز نیست.')
        by_code = {r['product_code']:r for r in info['lines']}
        seen, changes = set(), []
        for line in lines:
            code, amount = line['product_code'], quantity(line['quantity'])
            if code in seen or code not in by_code or amount <= 0:
                fail('اقلام مانده نامعتبر یا تکراری هستند.')
            seen.add(code)
            before = by_code[code]
            if before['reserved_qty'] > 0:
                fail('این قلم انتقالِ در حال پیگیری دارد؛ ابتدا نتیجهٔ انتقال را مشخص کنید.')
            limit = Decimal(str(before['closed_qty'])).quantize(Decimal('.001')) if reopen else remaining(before)
            if amount > limit:
                fail('مقدار از ماندهٔ قابل بستن یا بازگشایی بیشتر است.')
            changes.append((preorder_id,code,float(-amount if reopen else amount),reason,username,_now(),request_id,digest))
        conn.executemany('''INSERT INTO warehouse_fulfillment_adjustments
            (preorder_id,product_code,quantity,reason,recorded_by,recorded_at,request_id,request_hash)
            VALUES(?,?,?,?,?,?,?,?)''',changes)
        return fulfillment_detail(conn,preorder_id)


def finish_delivery(settings, username, preorder_id, *, expected_revision, request_id):
    """Terminal decision independent of mutable receipts; never fabricates received stock."""
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    from app.warehouse_fulfillment import fulfillment_detail
    if not request_id or expected_revision < 0:
        fail('شناسه درخواست و نسخه سفارش الزامی است.')
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        info = fulfillment_detail(conn, preorder_id)
        if info is None:
            fail('سفارش قابل تحویل پیدا نشد.')
        if info['delivery_ended']:
            return info  # Replays never create another completion or alter its audit.
        if info['revision'] != expected_revision:
            fail('دریافت یا مانده سفارش تغییر کرده است؛ صفحه را بازخوانی کنید.')
        if any(r['status'] == 'pending' for r in info['linked_receipts']):
            fail('ابتدا نتیجه انتقال در حال پیگیری را مشخص کنید.')
        conn.execute('''INSERT INTO warehouse_delivery_completions
            (preorder_id,recorded_by,recorded_at,request_id,expected_revision) VALUES(?,?,?,?,?)''',
            (preorder_id,username,_now(),request_id,expected_revision))
        return fulfillment_detail(conn, preorder_id)
