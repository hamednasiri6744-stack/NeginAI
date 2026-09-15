"""Receipt identity checks and retained transfer generations. ERP reads only."""
import json
from uuid import UUID


def init_schema(conn):
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS warehouse_checkbar_transfer_history (
          transfer_key TEXT PRIMARY KEY, document_id INTEGER NOT NULL REFERENCES warehouse_checkbars(id),
          revision INTEGER NOT NULL, requested_by TEXT NOT NULL, payload_json TEXT NOT NULL,
          result_json TEXT NOT NULL, updated_at TEXT NOT NULL, deleted_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_checkbar_transfer_history_document
          ON warehouse_checkbar_transfer_history(document_id,deleted_at);
        CREATE TABLE IF NOT EXISTS supplier_order_deletions (
          order_id INTEGER PRIMARY KEY REFERENCES supplier_orders(id),
          deleted_by TEXT NOT NULL, deleted_at TEXT NOT NULL
        );
    ''')


def history(conn, document_id):
    return [dict(r) for r in conn.execute('''SELECT * FROM warehouse_checkbar_transfer_history
        WHERE document_id=? ORDER BY rowid''', (document_id,))]


def probe(settings, row):
    from app.database import sql_connection
    from app.warehouse_receipt_reflection import _rows, snapshot_cursor
    result = json.loads(row['result_json'])
    if result.get('PriceWorkflowVersion') == 2:
        from app.warehouse_receipt_prices import documents
        components=[]
        for component in documents(result):
            identity=dict(row,transfer_key=component['UniqueId'],result_json=json.dumps(component))
            components.append(dict(component, evidence=probe(settings,identity)))
        states=[c['evidence']['state'] for c in components]
        status='deleted' if all(s=='deleted' for s in states) else 'exists' if all(s=='exists' for s in states) else 'review'
        return dict(state=status,number=result['VocherNo'],confirmed=bool(result['Confirmed']),documents=components)
    receipt_id = int(result['VocherId'])
    key = str(UUID(row['transfer_key']))
    if receipt_id <= 0:
        raise ValueError('Invalid receipt identity')
    with sql_connection(settings) as source:
        cursor = snapshot_cursor(source)
        # A failed SELECT is unknown, never absence. Check both identities and
        # orphan items, so a replaced header cannot silently unlock the checkbar.
        rows = _rows(cursor, f'''SELECT ID,UniqueId,VocherNo,ConfirmDate,ConfirmedBy,StockDCRef,VocherTypeCode
            FROM inv.tblVocherHdr WHERE ID={receipt_id} OR UniqueId='{key}' ''')
        items = _rows(cursor, f'SELECT TOP (1) HdrRef FROM inv.tblVocherItm WHERE HdrRef={receipt_id}')
    if not rows and not items:
        return dict(state='deleted', number=result['VocherNo'])
    if len(rows) == 1 and int(rows[0]['ID']) == receipt_id and str(UUID(str(rows[0]['UniqueId']))) == key:
        if result.get('Role') and (rows[0]['StockDCRef']!=result['StockDCRef'] or rows[0]['VocherTypeCode']!=result['VocherTypeCode']):
            return dict(state='review',number=result['VocherNo'])
        if result.get('Role') in ('confirmed_receipt','price_reserve') and (rows[0]['ConfirmDate'] is None or rows[0]['ConfirmedBy'] is None):
            return dict(state='review',number=result['VocherNo'])
        return dict(state='exists', number=rows[0]['VocherNo'],
                    confirmed=rows[0]['ConfirmDate'] is not None or rows[0]['ConfirmedBy'] is not None)
    return dict(state='review', number=result['VocherNo'])


def inspect(conn, settings, document_id, *, strict=False):
    from app.warehouse_assistant_service import WarehouseAssistantError, _now
    row = conn.execute('SELECT * FROM warehouse_checkbar_transfers WHERE document_id=?', (document_id,)).fetchone()
    if row and row['status'] == 'pending':
        state = dict(state='pending', locked=True)
    else:
        prior = history(conn, document_id)
        candidates = prior + ([dict(row)] if row and row['status'] == 'sent' else [])
        state = dict(state='not_sent', locked=False)
        for candidate in candidates:
            try:
                evidence = probe(settings, candidate)
            except Exception:
                evidence = dict(state='unknown', number=json.loads(candidate['result_json']).get('VocherNo'))
            state = dict(evidence, locked=evidence['state'] != 'deleted', checked_at=_now())
            if state['locked']:
                break
        if candidates and not state['locked'] and row and row['status'] == 'sent':
            now = _now()
            conn.execute('''INSERT INTO warehouse_checkbar_transfer_history
                (transfer_key,document_id,revision,requested_by,payload_json,result_json,updated_at,deleted_at)
                VALUES(?,?,?,?,?,?,?,?)''', tuple(row[k] for k in (
                    'transfer_key','document_id','revision','requested_by','payload_json','result_json','updated_at')) + (now,))
            # Keep physical receipt/allocation until the user edits or deletes.
            # Older transfers did not have a separate local confirmation.
            payload = json.loads(row['payload_json'])
            if payload.get('order_matching', {}).get('version') == 1:
                physical = json.dumps([dict(product_code=l['product_code'], quantity=float(l['quantity'])) for l in payload['lines']])
                conn.execute('''INSERT OR IGNORE INTO warehouse_checkbar_confirmations
                    (document_id,revision,active,physical_json,confirmed_by,confirmed_at) VALUES(?,?,1,?,?,?)''',
                    (document_id,row['revision'],physical,row['requested_by'],now))
            # Pre-matching legacy transfers were never locally allocated; do not
            # invent a retrospective physical confirmation for those documents.
            conn.execute('DELETE FROM warehouse_checkbar_transfers WHERE document_id=?', (document_id,))
            warehouse = conn.execute('SELECT warehouse_code FROM warehouse_checkbars WHERE id=?',(document_id,)).fetchone()[0]
            # A previously reflected receipt may still be inside the cached stock.
            # Keep purchasing blocked until a coherent inventory snapshot is read.
            conn.execute('''INSERT INTO warehouse_receipt_stock_state(document_id,warehouse_code,status,evidence_json,updated_at)
                VALUES(?,?,'review',?,?) ON CONFLICT(document_id) DO UPDATE SET
                status='review',evidence_json=excluded.evidence_json,updated_at=excluded.updated_at''',
                (document_id,warehouse,json.dumps({'message':'سند ورانگر حذف شده؛ موجودی را به‌روزرسانی کنید.'}),now))
    if strict and state['locked']:
        raise WarehouseAssistantError({
            'exists':f"سند ورانگر شماره {state.get('number')} وجود دارد؛ چک‌بار قفل است.",
            'pending':'ابتدا نتیجهٔ انتقال را با پیگیری انتقال مشخص کنید.',
        }.get(state['state'],'وجود یا حذف سند ورانگر قطعی نیست؛ چک‌بار تا بررسی موفق قفل می‌ماند.'))
    return state


def status(settings, document_id):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection
    from app.warehouse_checkbar import _current_document
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        _current_document(conn, document_id, include_deleted=True)
        return inspect(conn, settings, document_id)


def replacements(conn, document_id):
    return [dict(transfer_key=r['transfer_key'],vocher_id=json.loads(r['result_json'])['VocherId'])
            for r in history(conn, document_id)]
