"""Return a proven-deleted native credit's lines to approved local staging.

This is not native cancellation: remote access is SELECT-only. The original
sent intent and its UUID stay immutable, and the old document is tombstoned.
"""
from datetime import datetime
from decimal import Decimal
import hashlib
import json

from app import warehouse_transfer_bridge as bridge
from app import warehouse_transfer_lifecycle as lifecycle
from app.warehouse_rebalancing import _fail
from app.warehouse_assistant_service import WarehouseAssistantError
from app.warehouse_receipt_reflection import TRIGGER_HASHES, _rows, snapshot_cursor


class InventoryRefreshRequired(WarehouseAssistantError):
    """Only a stock prerequisite can request one automatic read-only refresh."""


def init_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_recovery_audit(
        document_id INTEGER PRIMARY KEY,
        restored_by TEXT NOT NULL, restored_at TEXT NOT NULL,
        evidence_json TEXT NOT NULL)''')


def _read_recovery_evidence(settings, captured):
    """Read both identities and every possible native receipt in one SNAPSHOT.

    DocRef is the current native type-15 link. Older conversion also populated
    TICAHdrRef; the complete reversed-route/year/type/number tuple covers legacy
    records. Do not filter on receipt confirmation, date or nullable DCRef.
    """
    from app.database import sql_connection
    if not all(getattr(settings, 'sql_' + field, '')
               for field in ('server', 'database', 'username', 'password')):
        raise ValueError('Reporting connection unavailable')
    payload, result, key = lifecycle._identity(captured)
    ident, number, year = (result[k] for k in ('VocherId', 'VocherNo', 'AccYear'))
    source, destination = payload['source_stock_ref'], payload['destination_stock_ref']
    with sql_connection(settings) as connection:
        cursor = snapshot_cursor(connection)
        headers = _rows(cursor, f'''SELECT H.ID,H.UniqueId FROM inv.tblVocherHdr H
            WHERE H.UniqueId='{key}' OR H.ID={ident}''')
        receipts = _rows(cursor, f'''SELECT R.ID,R.VocherNo,R.AccYear,R.StockDCRef,R.TStockDCRef,
            R.DocRef,R.TICAHdrRef,R.TVchTypeRef,R.TVocherTypeCode,R.TVocherNo,
            R.ConfirmedBy,R.ConfirmDate FROM inv.tblVocherHdr R
            WHERE R.VocherTypeCode=15 AND (R.DocRef={ident} OR R.TICAHdrRef={ident}
                OR (R.AccYear={year} AND R.StockDCRef={destination}
                    AND R.TStockDCRef={source} AND R.TVocherTypeCode=65
                    AND R.TVocherNo={number}))''')
    return dict(headers=headers, receipts=receipts)


def _valid_stock_evidence(evidence):
    contract = evidence.get('contract')
    return (isinstance(contract, dict) and contract.get('valid') is True
        and contract.get('configuration') == [dict(KeyValue='1')]
        and contract.get('effects') == [dict(CardexType=1, EffectOnHandQty=True, EffectType=1)]
        and contract.get('trigger_hashes') == TRIGGER_HASHES
        and evidence.get('effects') == [dict(CardexType=1, EffectOnHandQty=True, EffectType=-1)]
        and evidence.get('flags') == [dict(KeyValue='1')]
        and evidence.get('status') == 'review'
        and evidence.get('headers') == [] and evidence.get('items') == [])


def _same_payload(original, current):
    # The native intent includes the preflight token, not part of line identity.
    original = dict(original)
    original.pop('validation_token', None)
    current = dict(current)
    for payload in (original, current):
        quantities = {}
        for line in payload.pop('lines'):
            value = Decimal(str(line['quantity']))
            if not value.is_finite() or value <= 0:
                return False
            code = str(line['product_code'])
            quantities[code] = quantities.get(code, Decimal(0)) + value
        payload['lines'] = quantities
    return original == current


def _capture(conn, username, document_id, include_all):
    doc = bridge._document(conn, document_id, username, include_all)
    captured = lifecycle._capture(conn, username, document_id, include_all)
    if len(captured) != 1:
        _fail('فقط سند بستانکار با سابقهٔ ثبت قطعی قابل بازگرداندن است.')
    original = captured[0]
    cache_row = conn.execute('SELECT * FROM warehouse_transfer_erp_state WHERE document_id=?',
                             (document_id,)).fetchone()
    cache = dict(cache_row) if cache_row else {}
    published = lifecycle.get_cached(conn, document_id)
    generation_row = lifecycle._generation(conn, document_id)
    generation = dict(generation_row) if generation_row else None
    if (not published or published.get('status') != 'missing'
            or cache.get('fingerprint') != lifecycle._fingerprint(original)):
        _fail('حذف سند بستانکار از ورانگر تأیید نشده است؛ وضعیت را بازخوانی کنید.')
    try:
        payload, result, _ = lifecycle._identity(original)
        if not _same_payload(payload, bridge._payload(conn, doc)):
            _fail('اقلام سند با سابقهٔ ثبت بستانکار یکسان نیست؛ بررسی لازم است.')
        lifecycle_evidence = json.loads(cache['evidence_json'])
        if lifecycle_evidence.get('headers') != [] or lifecycle_evidence.get('items') != []:
            _fail('شواهد حذف سند کامل نیست؛ وضعیت را بازخوانی کنید.')
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError):
        _fail('سابقهٔ سند بستانکار معتبر نیست؛ بازگرداندن متوقف شد.')

    snapshot_row = conn.execute('SELECT * FROM warehouse_snapshots ORDER BY id DESC LIMIT 1').fetchone()
    stock_row = conn.execute('SELECT * FROM warehouse_transfer_source_stock_state WHERE document_id=?',
                             (document_id,)).fetchone()
    snapshot = dict(snapshot_row) if snapshot_row else {}
    stock = dict(stock_row) if stock_row else {}
    valid = (snapshot.get('source_kind') == 'varanegar'
             and stock.get('snapshot_id') == snapshot.get('id')
             and stock.get('status') == 'review'
             and str(snapshot.get('period_end') or '')[:4] == str(result['AccYear']))
    try:
        valid = (valid and _valid_stock_evidence(json.loads(stock['evidence_json']))
                 and datetime.fromisoformat(snapshot['imported_at']) >= datetime.fromisoformat(original['updated_at']))
    except (ValueError, TypeError, KeyError, AttributeError):
        valid = False
    if not valid:
        raise InventoryRefreshRequired('حذف بستانکار در آخرین تصویر موجودی تأیید نشده است؛ بازخوانی موجودی لازم است.')

    lines = [dict(row) for row in conn.execute('''SELECT * FROM warehouse_transfer_document_lines
        WHERE document_id=? ORDER BY request_id''', (document_id,))]
    requests = [dict(row) for row in conn.execute('''SELECT r.* FROM warehouse_rebalance_requests r
        JOIN warehouse_transfer_document_lines l ON l.request_id=r.id
        WHERE l.document_id=? ORDER BY r.id''', (document_id,))]
    # Include inventory contents, not just snapshot ID: a concurrent rewrite of
    # the same snapshot must not silently change the source reservation basis.
    products = sorted({row['product_code'] for row in requests})
    placeholders = ','.join('?' for _ in products)
    inventory = [dict(row) for row in conn.execute(f'''SELECT * FROM warehouse_snapshot_items
        WHERE snapshot_id=? AND warehouse_code IN (?,?) AND product_code IN ({placeholders}) ORDER BY id''',
        (snapshot['id'], doc['source'], doc['destination'], *products))]
    if not all(any(item['warehouse_code'] == warehouse and item['product_code'] == product
                   for item in inventory) for warehouse in (doc['source'], doc['destination']) for product in products):
        raise InventoryRefreshRequired('اقلام سند در تصویر موجودی هر دو انبار کامل نیست؛ موجودی را بازخوانی کنید.')
    return dict(original=original, document=doc, cache=cache, generation=generation, stock=stock,
                snapshot=snapshot, lines=lines, requests=requests, inventory=inventory)


def return_to_approved(settings, username, document_id, include_all=False):
    """Atomically detach lines only after fresh native and stock absence proof."""
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        init_schema(conn)
    # Force means a previous missing result or a previously successful probe is
    # never enough; ownership is also checked before making a remote request.
    states = lifecycle.sync(settings, username, document_id, include_all=include_all, force=True)
    if states.get(document_id, {}).get('status') != 'missing':
        _fail('سند بستانکار حذف‌شده نیست یا وضعیت آن قطعی نیست؛ بازگرداندن انجام نشد.')
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN')
        captured = _capture(conn, username, document_id, include_all)
    try:
        evidence = _read_recovery_evidence(settings, captured['original'])
    except Exception:
        # Driver errors can contain connection secrets. Never persist or expose.
        _fail('بررسی حذف بستانکار و نبود رسید مقصد در ورانگر انجام نشد؛ دوباره تلاش کنید.')
    if not isinstance(evidence, dict) or evidence.get('headers') != []:
        _fail('سند بستانکار هنوز در ورانگر وجود دارد یا شواهد نبود آن معتبر نیست.')
    if evidence.get('receipts') != []:
        _fail('رسید مقصد مرتبط وجود دارد یا بررسی آن قطعی نیست؛ بازگرداندن مجاز نیست.')
    checked_at = _now()
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current = _capture(conn, username, document_id, include_all)
        if current != captured:
            _fail('هم‌زمان سند، وضعیت یا موجودی تغییر کرده است؛ دوباره بررسی کنید.')
        conn.execute('''INSERT INTO warehouse_transfer_document_line_history
            SELECT request_id,document_id,estimated_unit_price,manufacturer,brand
            FROM warehouse_transfer_document_lines WHERE document_id=?''', (document_id,))
        restored_at = _now()
        proof = dict(reason='native_credit_deleted_no_destination_receipt',
            original_fingerprint=lifecycle._fingerprint(captured['original']),
            original_transfer_key=captured['original']['transfer_key'],
            original_result=json.loads(captured['original']['result_json']),
            snapshot_id=captured['snapshot']['id'], snapshot_hash=captured['snapshot']['content_sha256'],
            snapshot_imported_at=captured['snapshot']['imported_at'],
            stock_evidence=json.loads(captured['stock']['evidence_json']),
            lifecycle_evidence=json.loads(captured['cache']['evidence_json']),
            remote_checked_at=checked_at, remote_evidence=evidence,
            captured_fingerprint=hashlib.sha256(json.dumps(captured, ensure_ascii=False,
                sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            returned_request_ids=[line['request_id'] for line in captured['lines']])
        conn.execute('INSERT INTO warehouse_transfer_recovery_audit VALUES(?,?,?,?)',
                     (document_id, username, restored_at, json.dumps(proof, ensure_ascii=False, sort_keys=True)))
        conn.execute('INSERT INTO warehouse_transfer_document_deletions VALUES(?,?,?)',
                     (document_id, username, restored_at))
        conn.execute('DELETE FROM warehouse_transfer_document_lines WHERE document_id=?', (document_id,))
    return dict(document_id=document_id, returned_count=len(captured['lines']), status='returned_to_approved')


def recover_with_inventory_refresh(settings, username, document_id, include_all=False):
    """One user action; never auto-delete native records or bypass absence proof.

    Refresh stock only on its typed prerequisite failure. Then repeat the entire
    native/receipt/ownership/transaction verification, not just the local detach.
    No loop: if fresh stock still cannot prove safety the document stays intact.
    """
    from app.warehouse_assistant_service import latest_snapshot, sync_varanegar_snapshot
    try:
        return return_to_approved(settings, username, document_id, include_all=include_all)
    except InventoryRefreshRequired:
        pass
    try:
        previous = latest_snapshot(settings)
        days = max(7, min(365, int((previous or {}).get('period_days') or 60)))
        sync_varanegar_snapshot(settings, username, period_days=days)
    except Exception:
        _fail('به‌روزرسانی خودکار موجودی انجام نشد؛ سند و اقلام حفظ شدند. دوباره تلاش کنید.')
    try:
        return return_to_approved(settings, username, document_id, include_all=include_all)
    except InventoryRefreshRequired:
        _fail('موجودی خودکار بازخوانی شد، اما شواهد حذف سند یا موجودی دو انبار کامل نیست؛ سند و اقلام حفظ شدند و بررسی لازم است.')
