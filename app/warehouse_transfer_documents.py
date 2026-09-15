"""Explicit issuance from confirmed staging. Never posts a movement to ERP.

Staging and issued lines share one reservation ledger; issuing must not add stock
a second time. A deletion tombstone releases only the unissued reservation.
"""
import hashlib
import json

from app.business_time import jalali_business_date, tehran_now
from app.warehouse_rebalancing import _fail


def _accessible_request(conn, ident, username, include_all):
    row = conn.execute('''SELECT r.*,b.created_by FROM warehouse_rebalance_requests r
        JOIN warehouse_rebalance_batches b ON b.id=r.batch_id WHERE r.id=?''', (ident,)).fetchone()
    if row is None or (not include_all and row['created_by'] != username):
        _fail('قلم جابه‌جایی پیدا نشد یا به آن دسترسی ندارید.')
    return row


def _check_unissued(conn, ident):
    if conn.execute('SELECT 1 FROM warehouse_rebalance_revocations WHERE request_id=?', (ident,)).fetchone():
        _fail('تأیید این قلم لغو شده است؛ پیشنهاد تازه را بررسی کنید.')
    if conn.execute('SELECT 1 FROM warehouse_transfer_document_lines WHERE request_id=?', (ident,)).fetchone():
        _fail('برای این قلم سند صادر شده است؛ فهرست را بازخوانی کنید.')
    if conn.execute('SELECT 1 FROM warehouse_rebalance_reflections WHERE request_id=?', (ident,)).fetchone():
        _fail('این قلم قبلاً در موجودی منعکس شده است.')


def delete_pending(settings, username, ident, *, include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        _accessible_request(conn, ident, username, include_all)
        previous = conn.execute('SELECT * FROM warehouse_rebalance_deletions WHERE request_id=?', (ident,)).fetchone()
        if previous:
            return dict(previous)
        _check_unissued(conn, ident)
        conn.execute('INSERT INTO warehouse_rebalance_deletions VALUES(?,?,?)', (ident, username, _now()))
        # Never restore a stale draft quantity: future calculations use the released
        # reservation and current demand. Original draft reductions remain audited.
        return dict(conn.execute('SELECT * FROM warehouse_rebalance_deletions WHERE request_id=?', (ident,)).fetchone())


def mutate_pending_batch(settings, username, request_ids, *, action, include_all=False):
    """One transaction, all-or-nothing; retries of the same action are harmless."""
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    if (action not in ('delete','revoke') or not isinstance(request_ids,list)
            or not 1<=len(request_ids)<=500 or any(type(i) is not int or i<=0 for i in request_ids)
            or len(set(request_ids))!=len(request_ids)):
        _fail('بین ۱ تا ۵۰۰ قلم یکتا و عملیات معتبر انتخاب کنید.')
    table='warehouse_rebalance_deletions' if action=='delete' else 'warehouse_rebalance_revocations'
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        pending=[]
        for ident in sorted(request_ids):
            _accessible_request(conn,ident,username,include_all)
            if conn.execute(f'SELECT 1 FROM {table} WHERE request_id=?',(ident,)).fetchone():
                continue
            _check_unissued(conn,ident)
            if conn.execute('SELECT 1 FROM warehouse_rebalance_deletions WHERE request_id=?',(ident,)).fetchone():
                _fail('یکی از اقلام حذف شده است؛ فهرست را بازخوانی کنید.')
            pending.append(ident)
        now=_now()
        conn.executemany(f'INSERT INTO {table} VALUES(?,?,?)',[(i,username,now) for i in pending])
        return dict(action=action,affected_count=len(pending),selected_count=len(request_ids))


def revoke_pending(settings, username, ident, *, include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        _accessible_request(conn, ident, username, include_all)
        previous=conn.execute('SELECT * FROM warehouse_rebalance_revocations WHERE request_id=?',(ident,)).fetchone()
        if previous:
            return dict(previous)
        _check_unissued(conn, ident)
        if conn.execute('SELECT 1 FROM warehouse_rebalance_deletions WHERE request_id=?',(ident,)).fetchone():
            _fail('این قلم حذف شده است.')
        conn.execute('INSERT INTO warehouse_rebalance_revocations VALUES(?,?,?)',(ident,username,_now()))
        return dict(conn.execute('SELECT * FROM warehouse_rebalance_revocations WHERE request_id=?',(ident,)).fetchone())


def delete_document(settings, username, document_id, *, include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        doc=conn.execute('SELECT * FROM warehouse_transfer_documents WHERE id=?',(document_id,)).fetchone()
        if doc is None or (not include_all and doc['created_by']!=username):
            _fail('سند جابه‌جایی پیدا نشد یا به آن دسترسی ندارید.')
        previous=conn.execute('SELECT * FROM warehouse_transfer_document_deletions WHERE document_id=?',(document_id,)).fetchone()
        if previous:
            return dict(previous)
        if conn.execute('''SELECT 1 FROM warehouse_transfer_document_lines l
                JOIN warehouse_rebalance_reflections r ON r.request_id=l.request_id WHERE l.document_id=?''',(document_id,)).fetchone():
            _fail('اقلام این سند در موجودی منعکس شده‌اند؛ حذف سند مجاز نیست.')
        # A future ERP submission must acquire its intent in this same local transaction domain.
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_transfer_bridge_intents'").fetchone():
            if conn.execute("SELECT 1 FROM warehouse_transfer_bridge_intents WHERE document_id=? AND status<>'rejected'",(document_id,)).fetchone():
                _fail('ثبت ورانگر برای این سند شروع شده است؛ تا تعیین تکلیف ثبت، حذف مجاز نیست.')
        conn.execute('''INSERT INTO warehouse_transfer_document_line_history
            SELECT request_id,document_id,estimated_unit_price,manufacturer,brand
            FROM warehouse_transfer_document_lines WHERE document_id=?''',(document_id,))
        conn.execute('INSERT INTO warehouse_transfer_document_deletions VALUES(?,?,?)',(document_id,username,_now()))
        conn.execute('DELETE FROM warehouse_transfer_document_lines WHERE document_id=?',(document_id,))
        return dict(conn.execute('SELECT * FROM warehouse_transfer_document_deletions WHERE document_id=?',(document_id,)).fetchone())


def create_documents(settings, username, request_ids, *, request_id, include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection
    if (not isinstance(request_id, str) or not 1 <= len(request_id.strip()) <= 100
            or not isinstance(request_ids, list) or not 1 <= len(request_ids) <= 500
            or any(type(i) is not int or i <= 0 for i in request_ids)
            or len(set(request_ids)) != len(request_ids)):
        _fail('بین ۱ تا ۵۰۰ قلم یکتا و شناسه درخواست معتبر انتخاب کنید.')
    ids = sorted(request_ids)
    digest = hashlib.sha256(json.dumps([username, ids]).encode()).hexdigest()
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        previous = conn.execute('SELECT * FROM warehouse_transfer_issues WHERE request_id=?', (request_id,)).fetchone()
        if previous:
            if previous['request_hash'] != digest:
                _fail('شناسه درخواست قبلاً برای انتخاب دیگری استفاده شده است؛ بازخوانی کنید.')
            for ident in ids:
                _accessible_request(conn, ident, username, include_all)
            return json.loads(previous['result_json'])
        routes = {}
        for ident in ids:
            row = _accessible_request(conn, ident, username, include_all)
            _check_unissued(conn, ident)
            if conn.execute('SELECT 1 FROM warehouse_rebalance_deletions WHERE request_id=?', (ident,)).fetchone():
                _fail('یکی از اقلام انتخاب‌شده حذف شده است؛ فهرست را بازخوانی کنید.')
            routes.setdefault((row['source'], row['destination']), []).append(row)
        now = tehran_now()
        business_date = jalali_business_date(now)
        conn.execute('INSERT INTO warehouse_transfer_issues VALUES(?,?,?)', (request_id, digest, '{}'))
        documents = []
        for (source, destination), rows in sorted(routes.items()):
            document_id = conn.execute('''INSERT INTO warehouse_transfer_documents
                (issue_id,source,destination,business_date,created_at,created_by) VALUES(?,?,?,?,?,?)''',
                (request_id, source, destination, business_date, now.isoformat(), username)).lastrowid
            for row in rows:
                conn.execute('''INSERT INTO warehouse_transfer_document_lines
                    (request_id,document_id,estimated_unit_price,manufacturer,brand) VALUES(?,?,
                    (SELECT buy_price FROM warehouse_snapshot_items WHERE snapshot_id=? AND warehouse_code=? AND product_code=? LIMIT 1),
                    (SELECT manufacturer FROM warehouse_snapshot_items WHERE snapshot_id=? AND warehouse_code=? AND product_code=? LIMIT 1),
                    (SELECT brand FROM warehouse_snapshot_items WHERE snapshot_id=? AND warehouse_code=? AND product_code=? LIMIT 1))''',
                    (row['id'], document_id, row['snapshot_id'], source, row['product_code'],
                     row['snapshot_id'], destination, row['product_code'], row['snapshot_id'], destination, row['product_code']))
            documents.append(dict(id=document_id, number=f'TR-{document_id:06d}', source=source,
                                  destination=destination, business_date=business_date, item_count=len(rows)))
        result = dict(documents=documents, item_count=len(ids), external_transfer_performed=False)
        conn.execute('UPDATE warehouse_transfer_issues SET result_json=? WHERE request_id=?',
                     (json.dumps(result, ensure_ascii=False), request_id))
        return result
