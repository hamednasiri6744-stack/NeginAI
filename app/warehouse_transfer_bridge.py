"""Explicit internal document -> confirmed credit voucher; disabled by default.

An immutable submission is saved before network I/O. Unknown outcomes only retry
the same key/bytes; neither a timeout nor a refresh authorizes a new voucher.
"""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

import pytds
from pydantic import BaseModel, Field
from app.warehouse_rebalancing import _fail


class SubmitCredit(BaseModel):
    model_config = {'extra': 'forbid'}
    preview_token: str = Field(pattern=r'^[0-9a-f]{64}$')
    validation_token: str = Field(min_length=1, max_length=128)
    confirmed: bool = Field(strict=True)


def init_schema(conn):
    from app.warehouse_transfer_lifecycle import init_schema as lifecycle_schema
    lifecycle_schema(conn)
    from app.warehouse_transfer_stock_exclusions import init_schema as stock_schema
    stock_schema(conn)
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_bridge_intents(
        document_id INTEGER PRIMARY KEY REFERENCES warehouse_transfer_documents(id),
        transfer_key TEXT NOT NULL UNIQUE,payload_json TEXT NOT NULL,
        requested_by TEXT NOT NULL,requested_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','sent','rejected','blocked')),
        result_json TEXT,updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_bridge_attempts(
        id INTEGER PRIMARY KEY,document_id INTEGER NOT NULL,transfer_key TEXT NOT NULL,
        payload_json TEXT NOT NULL,requested_by TEXT NOT NULL,requested_at TEXT NOT NULL,
        status TEXT NOT NULL,result_json TEXT,updated_at TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_transfer_source_stock_state(
        document_id INTEGER PRIMARY KEY,status TEXT NOT NULL CHECK(status IN ('reflected','review')),
        snapshot_id INTEGER NOT NULL,evidence_json TEXT NOT NULL,updated_at TEXT NOT NULL)''')


def _json(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def _token(payload, validation):
    return hashlib.sha256(_json([payload,validation]).encode()).hexdigest()


def _document(conn, ident, username, include_all):
    row=conn.execute('SELECT * FROM warehouse_transfer_documents WHERE id=?',(ident,)).fetchone()
    if row is None or (not include_all and row['created_by']!=username):
        _fail('سند جابه‌جایی پیدا نشد یا به آن دسترسی ندارید.')
    if conn.execute('SELECT 1 FROM warehouse_transfer_document_deletions WHERE document_id=?',(ident,)).fetchone():
        _fail('این سند جابه‌جایی حذف شده است.')
    return dict(row)


def _payload(conn, doc):
    from app.warehouse_assistant_service import WAREHOUSES
    if doc['source'] not in WAREHOUSES or doc['destination'] not in WAREHOUSES or doc['source']==doc['destination']:
        _fail('مسیر سند جابه‌جایی معتبر نیست.')
    rows=conn.execute('''SELECT r.* FROM warehouse_transfer_document_lines l
        JOIN warehouse_rebalance_requests r ON r.id=l.request_id WHERE l.document_id=? ORDER BY r.id''',(doc['id'],)).fetchall()
    totals={}
    if not 1<=len(rows)<=500:
        _fail('سند باید بین ۱ تا ۵۰۰ قلم داشته باشد.')
    for row in rows:
        if row['source']!=doc['source'] or row['destination']!=doc['destination']:
            _fail('مسیر اقلام سند ناسازگار است.')
        for table in ('warehouse_rebalance_reflections','warehouse_rebalance_revocations','warehouse_rebalance_deletions'):
            if conn.execute(f'SELECT 1 FROM {table} WHERE request_id=?',(row['id'],)).fetchone():
                _fail('قلم حذف‌شده، لغوتأییدشده یا منعکس‌شده قابل ثبت دوباره نیست.')
        try:
            qty=Decimal(str(row['quantity']))
            if not qty.is_finite() or qty<=0 or qty>1_000_000_000 or qty!=qty.quantize(Decimal('.001')):
                raise InvalidOperation
        except (ValueError,InvalidOperation):
            _fail('تعداد قلم سند معتبر نیست.')
        totals[row['product_code']]=totals.get(row['product_code'],Decimal(0))+qty
    if any(v>1_000_000_000 for v in totals.values()):
        _fail('جمع تعداد کالا بیش از حد مجاز است.')
    return dict(version=1,document_number=f"TR-{doc['id']:06d}",
        source_stock_ref=WAREHOUSES[doc['source']]['stock_dc_ref'],
        destination_stock_ref=WAREHOUSES[doc['destination']]['stock_dc_ref'],
        voucher_date=doc['business_date'],
        lines=[dict(product_code=k,quantity=format(v,'f')) for k,v in sorted(totals.items())])


def _key(doc):
    return str(uuid5(NAMESPACE_URL,f"neginai:interwarehouse-credit:v1:{doc['issue_id']}:{doc['id']}:{doc['source']}:{doc['destination']}"))


def _existing(conn, ident):
    row=conn.execute('SELECT * FROM warehouse_transfer_bridge_intents WHERE document_id=?',(ident,)).fetchone()
    return dict(row) if row else None


def _state(row):
    return dict(status=row['status'],result=json.loads(row['result_json']) if row['result_json'] else None) if row else dict(status='not_sent',result=None)


def _enabled(settings, commit=False):
    if not getattr(settings,'varanegar_transfer_bridge_enabled',False):
        _fail('پل بستانکار جابه‌جایی هنوز نصب و فعال نشده است.')
    if commit and not getattr(settings,'varanegar_transfer_commit_enabled',False):
        _fail('پل فقط برای بررسی فعال است؛ ثبت و تأیید نهایی هنوز فعال نشده است.')


@contextmanager
def _connection(settings):
    values={k:getattr(settings,'varanegar_transfer_sql_'+k,'') for k in ('server','database','username','password')}
    if not all(values.values()):
        _fail('اتصال حساب محدود پل جابه‌جایی کامل نیست.')
    host,_,port=values['server'].partition(',')
    conn=pytds.connect(dsn=host,port=int(port) if port else None,database=values['database'],
        user=values['username'],password=values['password'],readonly=False,autocommit=True,
        validate_host=True,timeout=getattr(settings,'sql_query_timeout',30),login_timeout=10)
    try:
        yield conn
    finally:
        try:conn.rollback()
        finally:conn.close()


def _remote(settings,key,username,encoded,commit):
    _enabled(settings,commit)
    with _connection(settings) as conn:
        cursor=conn.cursor()
        cursor.execute('''EXEC NeginAI.usp_CreateInterwarehouseCredit
            @TransferKey=%s,@RequestedBy=%s,@PayloadJson=%s,@Commit=%s''',(key,username,encoded,commit))
        result=None
        while True:
            if cursor.description:
                names=[r[0] for r in cursor.description]
                if 'BridgeStatus' in names:
                    row=cursor.fetchone();result=dict(zip(names,row)) if row else None
                    break
            if not cursor.nextset():break
        return _validate_result(result,commit)


def _validate_result(result,commit):
    if not isinstance(result,dict) or result.get('BridgeStatus') not in ('ready','sent','blocked','rejected'):
        _fail('پاسخ معتبر از پل دریافت نشد؛ همان درخواست را پیگیری کنید.')
    if result['BridgeStatus']=='sent':
        if not commit or result.get('Confirmed') not in (1,True) or any(int(result.get(k) or 0)<=0 for k in ('VocherId','VocherNo','AccYear')):
            _fail('پاسخ ثبت با سند بستانکار تأییدشده سازگار نیست؛ پیگیری لازم است.')
    if commit and result['BridgeStatus']=='ready':
        _fail('نتیجهٔ ثبت قطعی دریافت نشد؛ پیگیری لازم است.')
    return result


def status(settings,username,ident,*,include_all=False,force=False):
    from app.warehouse_assistant_service import init_warehouse_store,warehouse_connection
    from app.warehouse_transfer_lifecycle import sync, get_cached
    init_warehouse_store(settings)
    sync(settings,username,ident,include_all=include_all,force=force)
    with warehouse_connection(settings) as conn:
        _document(conn,ident,username,include_all)
        result=_state(_existing(conn,ident))
        stock=conn.execute('SELECT status,snapshot_id FROM warehouse_transfer_source_stock_state WHERE document_id=?',(ident,)).fetchone()
        from app.warehouse_transfer_stock_exclusions import history
        exclusions=history(conn,ident)
        erp=get_cached(conn,ident)
    return dict(result,erp=erp,stock_exclusions=exclusions,source_stock=dict(stock) if stock else None,
        enabled=getattr(settings,'varanegar_transfer_bridge_enabled',False),
        commit_enabled=getattr(settings,'varanegar_transfer_commit_enabled',False))


def preview(settings,username,ident,*,include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store,warehouse_connection
    _enabled(settings);init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN')
        doc=_document(conn,ident,username,include_all)
        row=_existing(conn,ident)
        if row and row['status']!='rejected':
            _fail('این سند ثبت شده یا نتیجهٔ ثبت آن نیازمند پیگیری است.')
        payload=_payload(conn,doc)
    result=_validate_result(_remote(settings,_key(doc),username,_json(payload),False),False)
    if result['BridgeStatus']!='ready':
        from app.warehouse_transfer_stock_exclusions import exclude
        with warehouse_connection(settings) as conn:
            conn.execute('BEGIN IMMEDIATE')
            doc=_document(conn,ident,username,include_all)
            excluded=exclude(conn,doc,username,payload,result)
        if excluded:return excluded
        _fail(result.get('Message') or 'اطلاعات سند توسط ورانگر پذیرفته نشد.')
    validation=str(result.get('ValidationToken') or '')
    if not validation or len(validation)>128:_fail('توکن بررسی پل معتبر نیست.')
    return dict(payload=payload,validation_token=validation,preview_token=_token(payload,validation),message=result.get('Message',''))


def submit(settings,username,ident,request,*,include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store,warehouse_connection,_now
    _enabled(settings,True);init_warehouse_store(settings)
    if request.confirmed is not True:_fail('تأیید صریح ثبت و تأیید نهایی بستانکار لازم است.')
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        doc=_document(conn,ident,username,include_all)
        row=_existing(conn,ident)
        if row and row['status']!='rejected':
            return _state(row)  # A second click cannot start a second submission.
        payload=_payload(conn,doc)
        if _token(payload,request.validation_token)!=request.preview_token:
            _fail('سند با پیش‌نمایش یکسان نیست؛ بررسی اطلاعات را دوباره انجام دهید.')
        payload['validation_token']=request.validation_token
        now=_now()
        if row:
            conn.execute('''INSERT INTO warehouse_transfer_bridge_attempts
                (document_id,transfer_key,payload_json,requested_by,requested_at,status,result_json,updated_at)
                SELECT document_id,transfer_key,payload_json,requested_by,requested_at,status,result_json,updated_at
                FROM warehouse_transfer_bridge_intents WHERE document_id=?''',(ident,))
        conn.execute('''INSERT INTO warehouse_transfer_bridge_intents VALUES(?,?,?,?,?,'pending',NULL,?)
            ON CONFLICT(document_id) DO UPDATE SET payload_json=excluded.payload_json,requested_by=excluded.requested_by,
            requested_at=excluded.requested_at,status='pending',result_json=NULL,updated_at=excluded.updated_at''',
            (ident,_key(doc),_json(payload),username,now,now))
        row=_existing(conn,ident)
    return _deliver(settings,row)


def retry(settings,username,ident,*,include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store,warehouse_connection
    _enabled(settings,True);init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        _document(conn,ident,username,include_all)
        row=_existing(conn,ident)
        if not row or row['status'] not in ('pending','blocked'):
            _fail('درخواست نامشخصی برای پیگیری وجود ندارد.')
    return _deliver(settings,row)


def _deliver(settings,row):
    from app.warehouse_assistant_service import warehouse_connection,_now
    try:
        result=_validate_result(_remote(settings,row['transfer_key'],row['requested_by'],row['payload_json'],True),True)
    except Exception:
        # Connection errors can contain credentials; do not expose their text.
        return dict(status='pending',result=None,message='نتیجهٔ ثبت مشخص نیست؛ فقط «پیگیری ثبت» را بزنید. حذف سند قفل است.')
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current=_existing(conn,row['document_id'])
        if current['status']=='sent':return _state(current)
        if current['payload_json']!=row['payload_json']:
            return _state(current)
        conn.execute('''UPDATE warehouse_transfer_bridge_intents SET status=?,result_json=?,updated_at=?
            WHERE document_id=?''',(result['BridgeStatus'],_json(result),_now(),row['document_id']))
        if result['BridgeStatus']=='rejected':
            from app.warehouse_transfer_stock_exclusions import exclude
            doc=dict(conn.execute('SELECT * FROM warehouse_transfer_documents WHERE id=?',(row['document_id'],)).fetchone())
            excluded=exclude(conn,doc,row['requested_by'],json.loads(row['payload_json']),result)
            if excluded:
                return dict(excluded,status='rejected',result=result)
        return _state(_existing(conn,row['document_id']))
