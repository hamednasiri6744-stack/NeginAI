"""Read-only current ERP state, separate from immutable successful submission.

A SQL snapshot ties header and lines together. A local fingerprint then prevents
that evidence being attached to a changed or deleted internal document.
"""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from uuid import UUID


def init_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_erp_state(
        document_id INTEGER PRIMARY KEY, status TEXT NOT NULL,
        message TEXT NOT NULL, voucher_no INTEGER, checked_at TEXT NOT NULL,
        evidence_json TEXT NOT NULL, fingerprint TEXT NOT NULL, confirmed_at TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_erp_refresh(
        document_id INTEGER PRIMARY KEY, generation INTEGER NOT NULL,
        published_generation INTEGER NOT NULL DEFAULT 0)''')


def _generation(conn, docid):
    return conn.execute('SELECT generation,published_generation FROM warehouse_transfer_erp_refresh WHERE document_id=?',
                        (docid,)).fetchone()


def _published(conn, docid):
    generation = _generation(conn, docid)
    return generation is None or generation['generation'] == generation['published_generation']


def _capture(conn, username, document_id, include_all):
    from app.warehouse_transfer_bridge import _document
    if document_id is not None:
        _document(conn, document_id, username, include_all)
    sql = '''SELECT i.*,d.created_by,d.source,d.destination,d.business_date,d.issue_id
        FROM warehouse_transfer_bridge_intents i
        JOIN warehouse_transfer_documents d ON d.id=i.document_id
        WHERE i.status='sent' AND NOT EXISTS(
            SELECT 1 FROM warehouse_transfer_document_deletions x WHERE x.document_id=d.id)'''
    args = []
    if document_id is not None:
        sql += ' AND d.id=?'; args.append(document_id)
    if not include_all:
        sql += ' AND d.created_by=?'; args.append(username)
    return [dict(row) for row in conn.execute(sql + ' ORDER BY d.id', args)]


def _fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def _public(row):
    return {k: row[k] for k in ('status', 'message', 'voucher_no', 'checked_at', 'confirmed_at')}


def get_cached(conn, docid):
    """Caller controls access; never return evidence for a changed submission."""
    captured = _capture(conn, '', None, True)
    original = next((r for r in captured if r['document_id'] == docid), None)
    if not original:
        return None
    row = conn.execute('SELECT * FROM warehouse_transfer_erp_state WHERE document_id=?', (docid,)).fetchone()
    return _public(row) if row and row['fingerprint'] == _fingerprint(original) and _published(conn, docid) else None


def _unknown():
    return dict(status='unknown', message='وضعیت فعلی سند ورانگر قابل بررسی نیست؛ دوباره وضعیت را بازخوانی کنید.',
                confirmed_at=None)


def _identity(row):
    payload = json.loads(row['payload_json'])
    result = json.loads(row['result_json'])
    key = str(UUID(row['transfer_key']))
    if (result.get('BridgeStatus') != 'sent' or result.get('Confirmed') not in (1, True)
            or any(type(result.get(k)) is not int or result[k] <= 0
                   for k in ('VocherId', 'VocherNo', 'AccYear'))
            or payload['voucher_date'] != row['business_date']):
        raise ValueError('Invalid captured identity')
    from app.warehouse_assistant_service import WAREHOUSES
    if (payload['source_stock_ref'] != WAREHOUSES[row['source']]['stock_dc_ref']
            or payload['destination_stock_ref'] != WAREHOUSES[row['destination']]['stock_dc_ref']
            or payload['source_stock_ref'] == payload['destination_stock_ref']
            or payload['document_number'] != f"TR-{row['document_id']:06d}"):
        raise ValueError('Invalid captured route')
    return payload, result, key


def _classify(row, detail):
    payload, result, key = _identity(row)
    headers = detail['headers']
    if not headers:
        return dict(status='missing', message='سند بستانکار در ورانگر یافت نشد؛ احتمالاً حذف شده است.', confirmed_at=None)
    changed = dict(status='changed', message='مشخصات یا اقلام سند در ورانگر تغییر کرده است؛ بررسی تطبیق لازم است.', confirmed_at=None)
    if len(headers) != 1:
        return changed
    h = headers[0]
    if (str(UUID(str(h['UniqueId']))) != key or h['ID'] != result['VocherId']
            or h['VocherNo'] != result['VocherNo'] or h['AccYear'] != result['AccYear']
            or h['StockDCRef'] != payload['source_stock_ref']
            or h['TStockDCRef'] != payload['destination_stock_ref']
            or (h['VocherTypeCode'], h['HealthCodeType'], h['HealthCode']) != (65, 1047, 1)
            or str(h['VocherDate']).strip() != payload['voucher_date']):
        return changed
    expected = defaultdict(Decimal)
    actual = defaultdict(Decimal)
    for line in payload['lines']:
        qty = Decimal(str(line['quantity']))
        if not qty.is_finite() or qty <= 0:
            raise ValueError('Invalid quantity')
        expected[str(line['product_code'])] += qty
    for line in detail['items']:
        qty = Decimal(str(line['TotalQty']))
        if (line['BasicUnitRef'] is None or line['UnitRef'] != line['BasicUnitRef']
                or Decimal(str(line['UnitCapacity'])) != 1
                or not qty.is_finite() or qty <= 0 or Decimal(str(line['UnitQty'])) != qty):
            return changed
        actual[str(line['GoodsCode'])] += qty
    if not expected or expected != actual:
        return changed
    if not h['ConfirmedBy'] or not h['ConfirmDate'] or not str(h['ConfirmDate']).strip():
        return dict(status='unconfirmed', message='تأیید سند بستانکار در ورانگر برداشته شده است؛ خروج قطعی نیست.', confirmed_at=None)
    return dict(status='confirmed', message='سند بستانکار در ورانگر موجود و تأییدشده است؛ دریافت مقصد جداست.',
                confirmed_at=str(h['ConfirmDate']))


def _read_many(settings, captured):
    """The only remote boundary; no integration credentials or ERP procedures."""
    from app.database import sql_connection
    from app.warehouse_receipt_reflection import snapshot_cursor, _rows
    if not all(getattr(settings, 'sql_' + name, '') for name in ('server', 'database', 'username', 'password')):
        raise ValueError('Report connection is unavailable')
    details = {}
    valid = []
    for row in captured:
        try:
            _, result, key = _identity(row)
            valid.append((row, result, key))
        except (ValueError, TypeError, KeyError, AttributeError):
            details[row['document_id']] = None
    if not valid:
        return details
    with sql_connection(settings) as source:
        cursor = snapshot_cursor(source)
        for row, result, key in valid:
            headers = _rows(cursor, f'''SELECT H.ID,H.UniqueId,H.VocherNo,H.StockDCRef,H.TStockDCRef,
                H.AccYear,H.VocherTypeCode,H.HealthCodeType,H.HealthCode,H.VocherDate,H.ConfirmedBy,H.ConfirmDate
                FROM inv.tblVocherHdr H WHERE H.UniqueId='{key}' OR H.ID={result['VocherId']}''')
            ids = ','.join(str(int(h['ID'])) for h in headers) or '0'
            items = _rows(cursor, f'''SELECT G.GoodsCode,I.UnitRef,G.UnitRef AS BasicUnitRef,
                I.UnitCapacity,I.UnitQty,I.TotalQty FROM inv.tblVocherItm I
                LEFT JOIN gnr.tblGoods G ON G.ID=I.GoodsRef WHERE I.HdrRef IN ({ids}) ORDER BY I.ID''')
            details[row['document_id']] = dict(headers=headers, items=items)
    return details


def sync(settings, username, document_id=None, *, include_all=False, force=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection, _now
    init_warehouse_store(settings)
    output = {}; refresh = []; generations = {}
    with warehouse_connection(settings) as conn:
        init_schema(conn)
        conn.execute('BEGIN IMMEDIATE')
        captured = _capture(conn, username, document_id, include_all)
        for row in captured:
            cached = conn.execute('SELECT * FROM warehouse_transfer_erp_state WHERE document_id=?', (row['document_id'],)).fetchone()
            age = 61
            if cached:
                try:
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(cached['checked_at'])).total_seconds()
                except (ValueError, TypeError):
                    pass
            if (not force and cached and cached['fingerprint'] == _fingerprint(row)
                    and 0 <= age < 60 and _published(conn, row['document_id'])):
                output[row['document_id']] = _public(cached)
            else:
                conn.execute('''INSERT INTO warehouse_transfer_erp_refresh(document_id,generation)
                    VALUES(?,1) ON CONFLICT(document_id) DO UPDATE SET generation=generation+1''',
                    (row['document_id'],))
                generations[row['document_id']] = _generation(conn, row['document_id'])['generation']
                refresh.append(row)
    if not refresh:
        return output
    try:
        evidence = _read_many(settings, refresh)
    except Exception:
        # Driver errors can expose connection credentials. Persist no exception text.
        evidence = {}
    checked_at = _now()
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current = {r['document_id']: r for r in _capture(conn, username, None, include_all)}
        for row in refresh:
            ident = row['document_id']; fingerprint = _fingerprint(row)
            if ident not in current or _fingerprint(current[ident]) != fingerprint:
                continue
            generation = _generation(conn, ident)
            if generation is None or generation['generation'] != generations[ident]:
                # A newer refresh owns publication even if its network call is
                # still running. Never publish an older SQL snapshot over it.
                current_cache = get_cached(conn, ident)
                try:
                    voucher_no = _identity(row)[1]['VocherNo']
                except (ValueError, TypeError, KeyError, AttributeError):
                    voucher_no = None
                output[ident] = current_cache or dict(_unknown(), voucher_no=voucher_no, checked_at=checked_at)
                continue
            detail = evidence.get(ident)
            try:
                state = _classify(row, detail) if detail is not None else _unknown()
            except (ValueError, TypeError, KeyError, ArithmeticError, AttributeError):
                state = _unknown()
            try:
                voucher_no = _identity(row)[1]['VocherNo']
            except (ValueError, TypeError, KeyError, AttributeError):
                voucher_no = None
            state.update(voucher_no=voucher_no, checked_at=checked_at)
            conn.execute('''INSERT INTO warehouse_transfer_erp_state
                (document_id,status,message,voucher_no,checked_at,evidence_json,fingerprint,confirmed_at)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET
                status=excluded.status,message=excluded.message,voucher_no=excluded.voucher_no,
                checked_at=excluded.checked_at,evidence_json=excluded.evidence_json,
                fingerprint=excluded.fingerprint,confirmed_at=excluded.confirmed_at''',
                (ident,state['status'],state['message'],voucher_no,checked_at,
                 json.dumps(detail, ensure_ascii=False, default=str),fingerprint,state['confirmed_at']))
            conn.execute('UPDATE warehouse_transfer_erp_refresh SET published_generation=? WHERE document_id=?',
                         (generations[ident], ident))
            output[ident] = state
    return output
