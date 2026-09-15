"""Return price-reserve-dependent lines to staging after a known ERP rejection.

Never release ERP reserves or trim requested quantities. Unknown submissions are
immutable; only preflight or a confirmed rollback permits local exclusion.
"""
from decimal import Decimal, InvalidOperation
import json

from app.warehouse_rebalancing import _fail


def init_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_stock_exclusions(
        id INTEGER PRIMARY KEY,document_id INTEGER NOT NULL,request_id INTEGER NOT NULL,
        product_code TEXT NOT NULL,product_name TEXT NOT NULL,evidence_json TEXT NOT NULL,
        excluded_by TEXT NOT NULL,excluded_at TEXT NOT NULL,
        UNIQUE(document_id,request_id))''')


def history(conn, document_id):
    return [dict(json.loads(r['evidence_json']), product_code=r['product_code'],
                 product_name=r['product_name'], request_id=r['request_id'])
            for r in conn.execute('SELECT * FROM warehouse_transfer_stock_exclusions WHERE document_id=? ORDER BY id', (document_id,))]


def _issues(result, payload):
    if result.get('BridgeStatus')!='rejected' or result.get('ErrorCode')!=51515:
        return {}
    try:
        raw=json.loads(result.get('StockIssuesJson') or '[]')
        if not isinstance(raw,list) or len(raw)>500: raise ValueError
        expected={r['product_code']:Decimal(r['quantity']) for r in payload['lines']}
        issues={};seen=set()
        for item in raw:
            code=item['ProductCode']
            requested,on_hand,reserved,shortage=(Decimal(str(item[k])) for k in (
                'RequestedQuantity','OnHandQuantity','ReservedQuantity','ShortageQuantity'))
            if (code not in expected or code in seen or requested!=expected[code]
                    or not all(n.is_finite() for n in (requested,on_hand,reserved,shortage))
                    or on_hand<0 or reserved<0 or shortage<=0 or shortage!=requested-on_hand):
                raise ValueError
            seen.add(code)
            if reserved>0:
                issues[code]=dict(requested_quantity=float(requested),on_hand_quantity=float(on_hand),
                                  reserved_quantity=float(reserved),shortage_quantity=float(shortage))
        return issues
    except (ValueError,TypeError,KeyError,InvalidOperation):
        _fail('جزئیات کمبود موجودی معتبر نیست؛ هیچ قلمی از سند کنار گذاشته نشد.')


def exclude(conn, doc, username, payload, result):
    """Caller holds BEGIN IMMEDIATE and has checked document access."""
    from app.warehouse_transfer_bridge import _existing, _payload
    from app.warehouse_assistant_service import _now
    issues=_issues(result,payload)
    if not issues:return None
    current=_existing(conn,doc['id'])
    if current and current['status']!='rejected':
        _fail('ثبت این سند شروع شده است؛ تا تعیین تکلیف آن حذف قلم مجاز نیست.')
    # A preflight response cannot remove lines changed while SQL was running.
    expected={k:v for k,v in payload.items() if k!='validation_token'}
    if _payload(conn,doc)!=expected:
        _fail('اقلام سند هنگام بررسی تغییر کرده‌اند؛ بررسی را دوباره انجام دهید.')
    now=_now()
    rows=conn.execute('''SELECT r.id,r.product_code,r.product_name FROM warehouse_transfer_document_lines l
        JOIN warehouse_rebalance_requests r ON r.id=l.request_id WHERE l.document_id=? ORDER BY r.id''', (doc['id'],)).fetchall()
    removed_ids=set()
    for row in rows:
        issue=issues.get(row['product_code'])
        if issue is None:continue
        conn.execute('''INSERT INTO warehouse_transfer_document_line_history
            SELECT request_id,document_id,estimated_unit_price,manufacturer,brand
            FROM warehouse_transfer_document_lines WHERE document_id=? AND request_id=?''', (doc['id'],row['id']))
        conn.execute('''INSERT INTO warehouse_transfer_stock_exclusions
            (document_id,request_id,product_code,product_name,evidence_json,excluded_by,excluded_at)
            VALUES(?,?,?,?,?,?,?)''', (doc['id'],row['id'],row['product_code'],row['product_name'],
                                    json.dumps(issue,ensure_ascii=False,allow_nan=False),username,now))
        conn.execute('DELETE FROM warehouse_transfer_document_lines WHERE document_id=? AND request_id=?', (doc['id'],row['id']))
        removed_ids.add(row['id'])
    remaining=conn.execute('SELECT COUNT(*) FROM warehouse_transfer_document_lines WHERE document_id=?',(doc['id'],)).fetchone()[0]
    if not remaining:
        conn.execute('INSERT INTO warehouse_transfer_document_deletions VALUES(?,?,?)',(doc['id'],username,now))
    all_history=history(conn,doc['id'])
    return dict(status='stock_excluded',excluded_items=[r for r in all_history if r['request_id'] in removed_ids],
                stock_exclusions=all_history,remaining_item_count=remaining,
                document_deleted=not remaining,
                message='اقلام نیازمند آزادسازی رزرو از سند کنار گذاشته و به تأییدشده‌ها برگردانده شدند. '
                        'پس از ثبت سند آزادسازی رزرو در ورانگر، دوباره انتخابشان کنید.')
