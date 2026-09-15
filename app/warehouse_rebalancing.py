"""Approved inter-warehouse requests, separate from purchasing and ERP movements.

All quantities are base units. Acceptance reserves supply and reduces the draft in
one transaction. A request is NOT a posted ERP transfer or a physical receipt.
"""
import hashlib
import json
import math

PAIRS = {'karaj': 'tehran', 'tehran': 'karaj'}


def balance_preview(*args, **kwargs):
    from app.warehouse_balance_proposals import preview
    return preview(*args, **kwargs)


def accept_balance(*args, **kwargs):
    from app.warehouse_balance_proposals import accept
    return accept(*args, **kwargs)


def init_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_rebalance_batches (
        id INTEGER PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
        request_hash TEXT NOT NULL, document_kind TEXT NOT NULL,
        document_id INTEGER NOT NULL, created_by TEXT NOT NULL,
        created_at TEXT NOT NULL, result_json TEXT NOT NULL DEFAULT '{}')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_rebalance_requests (
        id INTEGER PRIMARY KEY, batch_id INTEGER NOT NULL REFERENCES warehouse_rebalance_batches(id),
        source TEXT NOT NULL, destination TEXT NOT NULL, product_code TEXT NOT NULL,
        product_name TEXT NOT NULL, cartons INTEGER NOT NULL CHECK(cartons>0),
        conversion_rate REAL NOT NULL CHECK(conversion_rate>0), quantity REAL NOT NULL CHECK(quantity>0),
        source_consumer_price REAL NOT NULL, destination_consumer_price REAL NOT NULL,
        daily_demand REAL NOT NULL, retained_quantity REAL NOT NULL, snapshot_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'requested' CHECK(status='requested'),
        CHECK(source<>destination), UNIQUE(batch_id,product_code))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_rebalance_reflections (
        request_id INTEGER PRIMARY KEY REFERENCES warehouse_rebalance_requests(id),
        snapshot_id INTEGER NOT NULL, confirmed_by TEXT NOT NULL,
        confirmed_at TEXT NOT NULL, source_document TEXT NOT NULL,
        destination_document TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_rebalance_deletions (
        request_id INTEGER PRIMARY KEY REFERENCES warehouse_rebalance_requests(id),
        deleted_by TEXT NOT NULL, deleted_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_issues (
        request_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL,
        result_json TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_documents (
        id INTEGER PRIMARY KEY, issue_id TEXT NOT NULL REFERENCES warehouse_transfer_issues(request_id),
        source TEXT NOT NULL, destination TEXT NOT NULL, business_date TEXT NOT NULL,
        created_at TEXT NOT NULL, created_by TEXT NOT NULL,
        CHECK(source<>destination), UNIQUE(issue_id,source,destination))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_document_lines (
        request_id INTEGER PRIMARY KEY REFERENCES warehouse_rebalance_requests(id),
        document_id INTEGER NOT NULL REFERENCES warehouse_transfer_documents(id),
        estimated_unit_price REAL, manufacturer TEXT, brand TEXT)''')
    conn.execute('CREATE INDEX IF NOT EXISTS ix_transfer_document_lines ON warehouse_transfer_document_lines(document_id)')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_rebalance_revocations (
        request_id INTEGER PRIMARY KEY REFERENCES warehouse_rebalance_requests(id),
        revoked_by TEXT NOT NULL, revoked_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_document_deletions (
        document_id INTEGER PRIMARY KEY REFERENCES warehouse_transfer_documents(id),
        deleted_by TEXT NOT NULL, deleted_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_document_line_history (
        request_id INTEGER NOT NULL,document_id INTEGER NOT NULL,
        estimated_unit_price REAL,manufacturer TEXT,brand TEXT,
        PRIMARY KEY(document_id,request_id))''')
    from app.warehouse_transfer_bridge import init_schema as bridge_schema
    bridge_schema(conn)
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_rebalance_approval_context(
        request_id INTEGER PRIMARY KEY REFERENCES warehouse_rebalance_requests(id),
        context_json TEXT NOT NULL)''')


def reservations(conn, warehouse):
    """Read-only, also compatible with stores not migrated yet."""
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_rebalance_requests'").fetchone():
        return {}, {}, []
    migrated = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_rebalance_reflections'").fetchone()
    active = ' AND NOT EXISTS (SELECT 1 FROM warehouse_rebalance_reflections f WHERE f.request_id=r.id)' if migrated else ''
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_rebalance_deletions'").fetchone():
        active += ' AND NOT EXISTS (SELECT 1 FROM warehouse_rebalance_deletions d WHERE d.request_id=r.id)'
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_rebalance_revocations'").fetchone():
        active += ' AND NOT EXISTS (SELECT 1 FROM warehouse_rebalance_revocations v WHERE v.request_id=r.id)'
    rows = [dict(r) for r in conn.execute('''SELECT id,source,destination,product_code,quantity,status
        FROM warehouse_rebalance_requests r WHERE (source=? OR destination=?)'''+active+' ORDER BY id', (warehouse, warehouse))]
    incoming, outgoing = {}, {}
    from app.warehouse_native_transit import handed_requests
    native_owned=handed_requests(conn)
    source_reflected=set()
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_transfer_source_stock_state'").fetchone():
        source_reflected={r[0] for r in conn.execute('''SELECT l.request_id FROM warehouse_transfer_document_lines l
            JOIN warehouse_transfer_source_stock_state s ON s.document_id=l.document_id
            WHERE s.status='reflected' AND s.snapshot_id=(SELECT MAX(id) FROM warehouse_snapshots)''')}
    for row in rows:
        if row['id'] in native_owned:
            continue  # Both legs now come from the same native stock/transit snapshot.
        if row['source']==warehouse and row['id'] in source_reflected:
            continue  # Confirmed credit is already inside this source-stock snapshot.
        target = incoming if row['destination'] == warehouse else outgoing
        code = row['product_code']
        target[code] = target.get(code, 0) + row['quantity']
    return incoming, outgoing, rows


def _fail(message):
    from app.warehouse_assistant_service import WarehouseAssistantError
    raise WarehouseAssistantError(message)


def availability(conn, destination, needs):
    """Uses the already adjusted demand snapshot, never raw sales or inbound stock."""
    from app.warehouse_assistant_service import LAST_STOCK_DEMAND_BASIS, ORDER_CYCLE_BLOCKED_SQL, ORDER_CYCLE_FORCED_SQL
    from app.warehouse_order_receipts import pending_stock
    source = PAIRS.get(destination)
    if not source:
        return [], None, []
    snapshot = conn.execute('SELECT * FROM warehouse_snapshots ORDER BY id DESC LIMIT 1').fetchone()
    if snapshot is None:
        return [], None, []
    inventory = {(r['warehouse_code'], r['product_code']): dict(r) for r in conn.execute(f'''
        SELECT *, CASE WHEN {ORDER_CYCLE_BLOCKED_SQL} THEN 1 ELSE 0 END AS cycle_blocked,
        CASE WHEN {ORDER_CYCLE_FORCED_SQL} THEN 1 ELSE 0 END AS cycle_forced
        FROM warehouse_snapshot_items WHERE snapshot_id=? AND warehouse_code IN (?,?)''',
        (snapshot['id'], source, destination))}
    _, outgoing, reserved_rows = reservations(conn, source)
    review = pending_stock(conn, source)[1] | pending_stock(conn, destination)[1]
    adjusted = snapshot['demand_basis'] in ('net_sales_stockout_adjusted', LAST_STOCK_DEMAND_BASIS)
    result, evidence = [], []
    for need in needs:
        code = need['product_code']
        donor, receiver = inventory.get((source, code)), inventory.get((destination, code))
        conversion = max(1, float(need['conversion_rate']))
        reason, daily, surplus, price, target_price = '', 0, 0, 0, 0
        if not donor or not receiver:
            reason = 'اطلاعات کالا در هر دو انبار موجود نیست.'
        else:
            days = max(0, int(donor['sales_rate_days'] or 0)) if adjusted else max(0, int(snapshot['period_days'] or 60))
            price, target_price = float(donor['consumer_price'] or 0), float(receiver['consumer_price'] or 0)
            blocked = any(r['cycle_blocked'] or (snapshot['demand_basis'] == LAST_STOCK_DEMAND_BASIS
                and not r['ordering_cycle_active'] and not r['cycle_forced']) for r in (donor, receiver))
            if blocked:
                reason = 'کالا خارج از چرخه سفارش است.'
            elif code in review:
                reason = 'رسید کالا نیازمند تطبیق است.'
            elif days == 0:
                reason = 'مبنای پیش‌بینی نیاز مبدأ مشخص نیست.'
            elif price <= 0 or target_price <= 0:
                reason = 'قیمت مصرف‌کننده در یکی از انبارها مشخص نیست.'
            elif price < target_price:
                reason = 'قیمت مصرف‌کننده مبدأ کمتر از مقصد است.'
            elif float(donor['conversion_rate'] or 0) != conversion or float(receiver['conversion_rate'] or 0) != conversion:
                reason = 'ضریب کارتن دو انبار و سفارش نیازمند بررسی است.'
            else:
                daily = max(0, float(donor['period_out'] or 0)) / days
                # Same physical procurement basis as ordering, minus existing reservations.
                free = float(donor['stock']) + max(0, float(donor['reserved'] or 0)) - max(0, float(donor['open_order'] or 0)) - outgoing.get(code, 0)
                surplus = max(0, free - daily * 50)
        cartons = min(max(0, int(need['cartons'])), max(0, math.floor((surplus + 1e-9) / conversion)))
        result.append(dict(product_code=code, product_name=need['product_name'], available_cartons=cartons,
            quantity=cartons*conversion, conversion_rate=conversion, daily_demand=daily,
            retained_quantity=daily*50, source_consumer_price=price, destination_consumer_price=target_price,
            reason=reason or ('' if cartons else 'مازاد قابل تأمین بالای نیاز ۵۰ روز وجود ندارد.')))
        evidence.append([donor, receiver, code in review])
    return result, snapshot['id'], [evidence, reserved_rows]


def _order(conn, kind, ident, username, include_all):
    from app.warehouse_assistant_service import _order_from_row, _automatic_preorder_from_row
    if kind not in ('supplier_order', 'automatic_preorder'):
        _fail('نوع سفارش معتبر نیست.')
    table = 'supplier_orders' if kind == 'supplier_order' else 'warehouse_automatic_preorders'
    row = conn.execute(f'SELECT * FROM {table} WHERE id=?', (ident,)).fetchone()
    if row is None or (kind == 'supplier_order' and not include_all and row['created_by'] != username):
        _fail('سفارش پیدا نشد.')
    if kind == 'automatic_preorder' and row['source_supplier_order_id'] is not None:
        _fail('این سفارش را از بخش دستی باز کنید.')
    return (_order_from_row if kind == 'supplier_order' else _automatic_preorder_from_row)(conn, row)


def _preview(conn, username, kind, ident, include_all):
    order = _order(conn, kind, ident, username, include_all)
    if not order['can_edit']:
        _fail('تأمین از انبار دیگر فقط برای پیش‌سفارش تأییدنشده و قبل از قرار دادن در کارتابل مجاز است؛ ابتدا لغو تأیید کنید.')
    if order['warehouse_code'] not in PAIRS:
        _fail('این مسیر فقط بین انبار تهران و کرج فعال است.')
    lines, snapshot, evidence = availability(conn, order['warehouse_code'], order['lines'])
    token = hashlib.sha256(json.dumps([order['email_send_token'], snapshot, lines, evidence],
        sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return dict(document_kind=kind, document_id=ident, source=PAIRS[order['warehouse_code']],
        destination=order['warehouse_code'], snapshot_id=snapshot, lines=lines, expected_token=token), order


def preview(settings, username, kind, ident, *, include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN')
        return _preview(conn, username, kind, ident, include_all)[0]


def accept(settings, username, kind, ident, lines, *, expected_token, request_id, include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    if not isinstance(request_id, str) or not 1 <= len(request_id) <= 100 or not lines or len(lines) > 500:
        _fail('شناسه درخواست و اقلام معتبر لازم است.')
    selected = {}
    for line in lines:
        code, count = str(line.get('product_code', '')).strip(), line.get('cartons')
        if not code or code in selected or type(count) is not int or not 1 <= count <= 1000000:
            _fail('تعداد انتقال باید کارتن کامل، مثبت و کد کالا یکتا باشد.')
        selected[code] = count
    digest = hashlib.sha256(json.dumps([username, kind, ident, selected, expected_token], sort_keys=True).encode()).hexdigest()
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        previous = conn.execute('SELECT * FROM warehouse_rebalance_batches WHERE request_id=?', (request_id,)).fetchone()
        if previous:
            if previous['request_hash'] != digest:
                _fail('شناسه درخواست قبلاً استفاده شده است؛ بازخوانی کنید.')
            return json.loads(previous['result_json'])
        data, order = _preview(conn, username, kind, ident, include_all)
        if data['expected_token'] != expected_token:
            _fail('موجودی، قیمت یا سفارش تغییر کرده است؛ مقادیر را بازخوانی و دوباره تأیید کنید.')
        available = {r['product_code']: r for r in data['lines']}
        if any(code not in available or count > available[code]['available_cartons'] for code, count in selected.items()):
            _fail('مقدار انتقال بیشتر از مازاد مجاز یا نیاز سفارش است.')
        now = _now()
        batch = conn.execute('''INSERT INTO warehouse_rebalance_batches
            (request_id,request_hash,document_kind,document_id,created_by,created_at) VALUES(?,?,?,?,?,?)''',
            (request_id, digest, kind, ident, username, now)).lastrowid
        manual = kind == 'supplier_order'
        table, parent = ('supplier_order_lines', 'order_id') if manual else ('warehouse_automatic_preorder_lines', 'preorder_id')
        quantity = value = total_cartons = item_count = 0
        for line in order['lines']:
            code = line['product_code']
            count = selected.get(code, 0)
            remaining = line['cartons'] - count
            if count:
                offer = available[code]
                conn.execute('''INSERT INTO warehouse_rebalance_requests
                    (batch_id,source,destination,product_code,product_name,cartons,conversion_rate,quantity,
                    source_consumer_price,destination_consumer_price,daily_demand,retained_quantity,snapshot_id)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (batch, data['source'], data['destination'], code, line['product_name'], count,
                     line['conversion_rate'], count*line['conversion_rate'], offer['source_consumer_price'],
                     offer['destination_consumer_price'], offer['daily_demand'], offer['retained_quantity'], data['snapshot_id']))
                if not remaining:
                    conn.execute(f'DELETE FROM {table} WHERE {parent}=? AND product_code=?', (ident, code))
                else:
                    units = remaining*line['conversion_rate']
                    conn.execute(f'UPDATE {table} SET cartons=?,order_quantity=?,estimated_value=?'
                        + (',requested_quantity=?' if manual else '') + f' WHERE {parent}=? AND product_code=?',
                        (remaining, units, units*line['buy_price'], *((units,) if manual else ()), ident, code))
            if remaining:
                item_count += 1
                total_cartons += remaining
                quantity += remaining*line['conversion_rate']
                value += remaining*line['conversion_rate']*line['buy_price']
        if manual:
            conn.execute('''UPDATE supplier_orders SET total_quantity=?,estimated_value=?,edited_by=?,edited_at=?,
                status=? WHERE id=?''', (quantity, value, username, now, 'prepared' if item_count else 'cancelled', ident))
            if not item_count:
                conn.execute('INSERT OR IGNORE INTO supplier_order_deletions VALUES(?,?,?)', (ident, username, now))
        else:
            conn.execute('''UPDATE warehouse_automatic_preorders SET total_quantity=?,estimated_value=?,total_cartons=?,
                item_count=?,edited_by=?,edited_at=?,status=? WHERE id=?''',
                (quantity, value, total_cartons, item_count, username, now, 'awaiting_approval' if item_count else 'cancelled', ident))
            if not item_count:
                conn.execute("UPDATE warehouse_automatic_preorders SET generation_key='transfer:'||id||':'||generation_key WHERE id=?", (ident,))
        result = dict(batch_id=batch, order=_order(conn, kind, ident, username, include_all), external_transfer_performed=False)
        conn.execute('UPDATE warehouse_rebalance_batches SET result_json=? WHERE id=?', (json.dumps(result, ensure_ascii=False), batch))
        return result


def list_requests(settings, username, *, include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        rows = [dict(r) for r in conn.execute('''SELECT r.*, b.document_kind,b.document_id,b.created_by,b.created_at,
            CASE WHEN dl.request_id IS NOT NULL THEN dl.manufacturer ELSE (SELECT i.manufacturer FROM warehouse_snapshot_items i WHERE i.snapshot_id=r.snapshot_id AND i.warehouse_code=r.destination AND i.product_code=r.product_code LIMIT 1) END AS manufacturer,
            CASE WHEN dl.request_id IS NOT NULL THEN dl.brand ELSE (SELECT i.brand FROM warehouse_snapshot_items i WHERE i.snapshot_id=r.snapshot_id AND i.warehouse_code=r.destination AND i.product_code=r.product_code LIMIT 1) END AS brand,
            CASE WHEN dl.request_id IS NOT NULL THEN dl.estimated_unit_price ELSE (SELECT i.buy_price FROM warehouse_snapshot_items i WHERE i.snapshot_id=r.snapshot_id AND i.warehouse_code=r.source AND i.product_code=r.product_code LIMIT 1) END AS estimated_unit_price,
            d.id AS issued_document_id,d.business_date AS issued_document_date,
            d.created_at AS issued_document_at,d.created_by AS issued_document_by,
            ac.context_json AS approval_context_json,
            t.status AS credit_status,t.result_json AS credit_result_json,
            (SELECT e.evidence_json FROM warehouse_transfer_stock_exclusions e WHERE e.request_id=r.id ORDER BY e.id DESC LIMIT 1) AS stock_exclusion_json,
            ss.status AS source_stock_status,ss.snapshot_id AS source_stock_snapshot_id,
            f.confirmed_at AS reflected_at,f.confirmed_by AS reflected_by,f.source_document,f.destination_document,
            (SELECT MAX(id) FROM warehouse_snapshots) AS current_snapshot_id
            FROM warehouse_rebalance_requests r JOIN warehouse_rebalance_batches b ON b.id=r.batch_id
            LEFT JOIN warehouse_rebalance_reflections f ON f.request_id=r.id
            LEFT JOIN warehouse_transfer_document_lines dl ON dl.request_id=r.id
            LEFT JOIN warehouse_transfer_documents d ON d.id=dl.document_id
            LEFT JOIN warehouse_transfer_bridge_intents t ON t.document_id=d.id
            LEFT JOIN warehouse_transfer_source_stock_state ss ON ss.document_id=d.id
            LEFT JOIN warehouse_rebalance_approval_context ac ON ac.request_id=r.id
            WHERE (? OR b.created_by=?) AND NOT EXISTS (
                SELECT 1 FROM warehouse_rebalance_deletions x WHERE x.request_id=r.id)
            AND NOT EXISTS (SELECT 1 FROM warehouse_rebalance_revocations v WHERE v.request_id=r.id)
            ORDER BY r.id DESC''', (include_all, username))]
        from app.warehouse_transfer_lifecycle import get_cached
        states={ident:get_cached(conn,ident) or {} for ident in
                {row['issued_document_id'] for row in rows if row['issued_document_id']}}
        for row in rows:
            encoded=row.pop('approval_context_json')
            row['approval_context']=json.loads(encoded) if encoded else None
            erp=states.get(row['issued_document_id'],{})
            row.update(erp_status=erp.get('status'),erp_message=erp.get('message'),
                       erp_checked_at=erp.get('checked_at'),erp_voucher_no=erp.get('voucher_no'))
        return rows


def reflect_in_stock(settings, username, request_id, *, snapshot_id, source_document,
                     destination_document, confirmed=False, include_all=False):
    """Explicit full-transfer reconciliation, never inferred from unrelated stock deltas.

    The operator confirms BOTH ERP movements are in the selected newer snapshot.
    No inventory or ERP document is written; history and original reservation remain.
    """
    from app.warehouse_assistant_service import init_warehouse_store,warehouse_connection,_now
    if confirmed is not True or not all(isinstance(x,str) and 1<=len(x.strip())<=100 for x in (source_document,destination_document)):
        _fail('شماره سند خروج و رسید و تأیید انعکاس کامل هر دو در موجودی لازم است.')
    init_warehouse_store(settings)
    from app.warehouse_transfer_lifecycle import sync, get_cached
    with warehouse_connection(settings) as conn:
        from app.warehouse_transfer_documents import _accessible_request
        _accessible_request(conn,request_id,username,include_all)
        linked=conn.execute('''SELECT t.document_id FROM warehouse_transfer_document_lines l
            JOIN warehouse_transfer_bridge_intents t ON t.document_id=l.document_id
            WHERE l.request_id=? AND t.status='sent' ''',(request_id,)).fetchone()
    verified={}
    if linked:
        verified=sync(settings,username,linked['document_id'],include_all=include_all,force=True)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('''SELECT r.*,b.created_by FROM warehouse_rebalance_requests r
            JOIN warehouse_rebalance_batches b ON b.id=r.batch_id WHERE r.id=?''',(request_id,)).fetchone()
        if row is None or (not include_all and row['created_by']!=username):
            _fail('جابه‌جایی پیدا نشد.')
        if conn.execute('SELECT 1 FROM warehouse_rebalance_deletions WHERE request_id=?',(request_id,)).fetchone():
            _fail('این قلم جابه‌جایی حذف شده است.')
        if conn.execute('SELECT 1 FROM warehouse_rebalance_revocations WHERE request_id=?',(request_id,)).fetchone():
            _fail('تأیید این قلم لغو شده است.')
        bridge=conn.execute('''SELECT t.document_id,t.status,t.result_json,s.status AS stock_status,s.snapshot_id
            FROM warehouse_transfer_document_lines l JOIN warehouse_transfer_bridge_intents t ON t.document_id=l.document_id
            LEFT JOIN warehouse_transfer_source_stock_state s ON s.document_id=l.document_id WHERE l.request_id=?''',(request_id,)).fetchone()
        if bridge and bridge['status']!='rejected':
            erp=get_cached(conn,bridge['document_id'])
            if not erp or erp['status']!='confirmed' or verified.get(bridge['document_id'])!=erp:
                _fail('وضعیت فعلی بستانکار ورانگر تأییدشده نیست یا قابل بررسی نیست؛ ابتدا وضعیت ورانگر را بازخوانی کنید.')
            if bridge['status']!='sent' or bridge['stock_status']!='reflected' or bridge['snapshot_id']!=snapshot_id:
                _fail('ابتدا ثبت بستانکار را پیگیری و موجودی مستقیم ورانگر را بازخوانی کنید.')
            if source_document.strip()!=str(json.loads(bridge['result_json'])['VocherNo']):
                _fail('شماره خروج باید همان شماره بستانکار ثبت‌شده با پل باشد.')
        previous=conn.execute('SELECT * FROM warehouse_rebalance_reflections WHERE request_id=?',(request_id,)).fetchone()
        if previous:
            return dict(previous)
        latest=conn.execute('SELECT MAX(id) FROM warehouse_snapshots').fetchone()[0]
        if type(snapshot_id) is not int or snapshot_id!=latest or snapshot_id<=row['snapshot_id']:
            _fail('ابتدا موجودی را پس از ثبت خروج و رسید به‌روز کنید و فهرست جابه‌جایی را بازخوانی کنید.')
        count=conn.execute('''SELECT COUNT(DISTINCT warehouse_code) FROM warehouse_snapshot_items
            WHERE snapshot_id=? AND product_code=? AND warehouse_code IN (?,?)''',
            (snapshot_id,row['product_code'],row['source'],row['destination'])).fetchone()[0]
        if count!=2:
            _fail('اطلاعات جدید کالا در هر دو انبار لازم است.')
        conn.execute('INSERT INTO warehouse_rebalance_reflections VALUES(?,?,?,?,?,?)',
            (request_id,snapshot_id,username,_now(),source_document.strip(),destination_document.strip()))
        return dict(conn.execute('SELECT * FROM warehouse_rebalance_reflections WHERE request_id=?',(request_id,)).fetchone())


def annotate_suggestions(settings, data):
    from app.warehouse_assistant_service import warehouse_connection
    warehouse = data['warehouse']['code']
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN')
        needs = [dict(item, cartons=item['suggested_cartons']) for item in data['items']]
        offers, _, _ = availability(conn, warehouse, needs)
        by_code = {r['product_code']: r for r in offers}
        for item in data['items']:
            item['transfer_offer'] = by_code.get(item['product_code'])
        data['transfer_source'] = PAIRS.get(warehouse)
    return data
