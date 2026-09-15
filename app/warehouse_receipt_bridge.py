"""Explicit checkbar -> atomic Varanegar receipts and price reservation.

The intent is committed locally before contacting SQL. An uncertain outcome keeps
that intent frozen; retries use exactly the same key and bytes. The SQL wrapper's
audit and receipt commit together. Local edits cannot race a pending transfer.
"""
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
import hashlib
import json
import logging
import re
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytds
from pydantic import BaseModel, Field, field_validator

from app.warehouse_assistant_service import (
    WAREHOUSES, WarehouseAssistantError, init_warehouse_store, warehouse_connection, _now,
)
from app.warehouse_checkbar import _current_document
from app.business_time import gregorian_to_jalali

log = logging.getLogger(__name__)


class ReceiptAllocation(BaseModel):
    model_config = {'extra': 'forbid'}
    source_row: int = Field(ge=1, le=500)
    preorder_id: int = Field(gt=0)
    quantity: float = Field(ge=0, le=1_000_000_000, allow_inf_nan=False)


class ReceiptRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    expected_revision: int = Field(ge=0)
    voucher_date: str = Field(pattern=r'^1[34][0-9]{2}/[01][0-9]/[0-3][0-9]$')
    reference_no: str = Field(default='', max_length=20)
    comment: str = Field(default='', max_length=220)
    preview_token: str = Field(default='', max_length=64)
    validation_token: str = Field(default='', max_length=64)
    allocations: list[ReceiptAllocation] | None = Field(default=None, max_length=5000)
    allocation_revision: str = Field(default='', max_length=64)
    matching_confirmed: bool = False
    accept_unallocated: bool = False

    @field_validator('voucher_date', 'reference_no', mode='before')
    @classmethod
    def normalize(cls, value):
        return str(value).strip().translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))

    @field_validator('voucher_date')
    @classmethod
    def valid_calendar_date(cls, value):
        target = tuple(map(int, value.split('/')))
        start = date(target[0]+621, 3, 19)
        if not any(gregorian_to_jalali(start+timedelta(days=i)) == target for i in range(370)):
            raise ValueError('تاریخ شمسی رسید معتبر نیست.')
        return value


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _token(payload):
    return hashlib.sha256(_json(payload).encode('utf-8')).hexdigest()


def _number(value, label):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or number > Decimal('1000000000000000'):
            raise InvalidOperation
        return number
    except (InvalidOperation, ValueError, TypeError):
        raise WarehouseAssistantError(f'{label} باید عدد معتبر و غیرمنفی باشد.') from None


def _text(number):
    return format(number, 'f').rstrip('0').rstrip('.') if '.' in format(number, 'f') else format(number, 'f')


def _payload(conn, doc, request):
    if doc.get('worksheet_workflow') and not doc.get('receipt_confirmed'):
        raise WarehouseAssistantError('ابتدا انباردار شمارش، قیمت‌ها و تطبیق چک‌بار را ثبت و تأیید کند؛ برگه اولیه قابل تبدیل به سند انبار نیست.')
    if doc.get('deleted'):
        raise WarehouseAssistantError('چک بار حذف‌شده قابل انتقال نیست.')
    if doc['revision'] != request.expected_revision:
        raise WarehouseAssistantError('ابتدا نسخهٔ جدید چک بار را باز کنید؛ سند تغییر کرده است.')
    # Healthy supplier receipts need TVocherNo to enable the native item editor.
    # reference_no is the supplier document number, not an invented local ID.
    if (not re.fullmatch(r'[0-9]{1,10}', request.reference_no)
            or not 1 <= int(request.reference_no) <= 2147483647):
        raise WarehouseAssistantError('شمارهٔ سند عطف تأمین‌کننده الزامی است؛ عدد صحیح بین ۱ و ۲۱۴۷۴۸۳۶۴۷ وارد کنید.')
    errors, lines, zero_rows = [], [], []
    for index, line in enumerate(doc['lines'], 1):
        label = f"ردیف {index} ({line['product_code']})"
        if line.get('actual_qty') is None:
            errors.append(label + ': تعداد خالی است؛ چک بار را اصلاح کنید.')
            continue
        try:
            qty = _number(line['actual_qty'], label + ' تعداد')
            if qty == 0:
                zero_rows.append(index)
                continue
            if qty > Decimal('1000000000') or qty != qty.quantize(Decimal('.001')):
                raise WarehouseAssistantError(label + ': تعداد باید حداکثر سه رقم اعشار داشته باشد.')
            from app.warehouse_receipt_prices import price_fields
            prices = price_fields(line, _number, _text, label)
            identity={key:line[key] for key in ('manufacturer_product_code','barcode','group_level3') if line.get(key)}
            lines.append(dict(product_code=line['product_code'], quantity=_text(qty),
                              source_row=index,**identity,**prices))
        except WarehouseAssistantError as exc:
            errors.append(str(exc))
    if not lines and not errors:
        errors.append('حداقل یک ردیف با تعداد بیشتر از صفر برای رسید لازم است.')
    if errors:
        raise WarehouseAssistantError('\n'.join(errors))
    refs = set()
    for row in conn.execute('''SELECT source_supplier_refs_json FROM warehouse_supply_scope
            WHERE warehouse_code=? AND supplier=? AND enabled=1''', (doc['warehouse'], doc['supplier'])):
        refs.update(int(ref) for ref in json.loads(row[0]) if str(ref).isdigit() and int(ref)>0)
    from app.warehouse_order_receipts import matching
    plan = doc['order_matching'] if doc.get('receipt_confirmed') else matching(conn, doc, None if request.allocations is None else [a.model_dump() for a in request.allocations], request.allocation_revision)
    from app.warehouse_receipt_lifecycle import replacements
    prior = replacements(conn, doc['id'])
    return dict(price_workflow_version=2,checkbar_number=doc['number'], revision=doc['revision'], order_matching=plan,
                **({'replaces_receipts': prior,'root_transfer_key':prior[0]['transfer_key']} if prior else {}),
                stock_dc_ref=WAREHOUSES[doc['warehouse']]['stock_dc_ref'],
                supplier_name=doc['supplier'], supplier_refs=sorted(refs),
                voucher_date=request.voucher_date, reference_no=request.reference_no,
                comment=f"{doc['number']} / v{doc['revision']}" + (' / ' + request.comment if request.comment else ''),
                lines=lines, zero_rows=zero_rows)


def _enabled(settings, commit=False):
    if not getattr(settings, 'varanegar_receipt_bridge_enabled', False):
        raise WarehouseAssistantError('اتصال مستقل رسید ورانگر هنوز فعال نشده است؛ تنظیم و آزمون پل لازم است.')
    if commit and not getattr(settings, 'varanegar_receipt_commit_enabled', False):
        raise WarehouseAssistantError('اتصال فقط برای بررسی فعال است؛ ارسال رسید هنوز فعال نشده است.')


@contextmanager
def _connection(settings):
    fields = ['server', 'database', 'username', 'password']
    values = {f: getattr(settings, 'varanegar_receipt_sql_' + f, '') for f in fields}
    if not all(values.values()):
        raise WarehouseAssistantError('اتصال حساب محدود رسید ورانگر کامل نیست.')
    server, _, port = values['server'].partition(',')
    conn = pytds.connect(dsn=server, port=int(port) if port else None,
                        database=values['database'], user=values['username'], password=values['password'],
                        readonly=False, autocommit=True, validate_host=True,
                        timeout=getattr(settings, 'sql_query_timeout', 30), login_timeout=10)
    try:
        yield conn
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


def _remote(settings, key, username, encoded, commit):
    """Fixed procedure only; never accepts SQL, identities, or confirmation from UI."""
    _enabled(settings, commit)
    payload=json.loads(encoded)
    modern=payload.get('price_workflow_version')==2
    if commit and payload.get('replaces_receipts') and not modern:
        capability=_remote(settings,key,username,encoded,False)
        if capability.get('ReplacementSupported') != 1 or capability['BridgeStatus'] not in ('ready','blocked'):
            raise WarehouseAssistantError('پل رسید برای صدور مجدد ایمن آماده نیست؛ نصب نسخهٔ جدید و بررسی سند قبلی لازم است.')
    with _connection(settings) as conn:
        cursor = conn.cursor()
        procedure='NeginAI.usp_CreateCheckbarReceiptV2' if modern else 'NeginAI.usp_CreateCheckbarReceipt'
        cursor.execute(f'''EXEC {procedure}
            @TransferKey=%s,@RequestedBy=%s,@PayloadJson=%s,@Commit=%s''',
                       (str(key), username, encoded, bool(commit)))
        result = None
        while True:
            if cursor.description:
                columns = [c[0] for c in cursor.description]
                if 'BridgeStatus' in columns:
                    row = cursor.fetchone()
                    result = dict(zip(columns, row)) if row else None
                    break
            if not cursor.nextset():
                break
        if result is None or result.get('BridgeStatus') not in ('ready','sent','rejected','blocked'):
            raise WarehouseAssistantError('پاسخ معتبر از پل رسید دریافت نشد؛ همان انتقال را پیگیری کنید.')
        if modern and result['BridgeStatus'] in ('ready','sent'):
            from app.warehouse_receipt_prices import validate_result
            try:
                validate_result(payload,result,commit)
            except (ValueError,KeyError,TypeError):
                raise WarehouseAssistantError('پل تفکیک رسید و رزرو قیمت آماده نیست یا نتیجه کامل نیست؛ پیگیری لازم است.') from None
        elif result['BridgeStatus'] == 'sent':
            if (not commit or int(result.get('VocherId') or 0) <= 0
                    or int(result.get('VocherNo') or 0) <= 0
                    or result.get('Confirmed') not in (False, 0)):
                raise WarehouseAssistantError('پاسخ رسید با قرارداد تأییدنشده سازگار نیست؛ پیگیری لازم است.')
        # The fixed wrapper owns its entire transaction. Autocommit avoids an
        # ambient transaction/legacy ROLLBACK mismatch. A lost reply is replayed
        # from its atomic SQL audit; client rollback cannot undo a sent receipt.
        return result


def _existing(conn, document_id):
    row = conn.execute('SELECT * FROM warehouse_checkbar_transfers WHERE document_id=?', (document_id,)).fetchone()
    return dict(row) if row else None


def _state(row):
    if not row:
        return {'status': 'not_sent'}
    return dict(status=row['status'], revision=row['revision'], requested_by=row['requested_by'],
                order_matching=json.loads(row['payload_json']).get('order_matching'),
                result=json.loads(row['result_json']) if row['result_json'] else None)


def transfer_status(settings, document_id):
    from app.warehouse_receipt_lifecycle import inspect, history
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        _current_document(conn, document_id, include_deleted=True)
        receipt = inspect(conn,settings,document_id)
        doc = _current_document(conn, document_id, include_deleted=True)
        state = _state(_existing(conn, document_id))
        past = [dict(revision=r['revision'],deleted_at=r['deleted_at'],result=json.loads(r['result_json'])) for r in history(conn,document_id)]
    return dict(state, current_revision=doc['revision'],
                receipt=receipt, transfer_history=past,
                enabled=getattr(settings, 'varanegar_receipt_bridge_enabled', False),
                commit_enabled=getattr(settings, 'varanegar_receipt_commit_enabled', False))


def order_matching(settings, document_id):
    from app.warehouse_order_receipts import matching
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN')
        doc = _current_document(conn, document_id)
        row = _existing(conn, document_id)
        if row and row['status'] in ('sent','pending'):
            raise WarehouseAssistantError('این چک‌بار قبلاً منتقل شده یا انتقال در حال پیگیری دارد.')
        return doc['order_matching'] if doc.get('receipt_confirmed') else matching(conn, doc)


def preview(settings, username, document_id, request):
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        from app.warehouse_receipt_lifecycle import inspect
        inspect(conn, settings, document_id, strict=True)
        row = _existing(conn, document_id)
        if row and row['status'] in ('pending','sent'):
            return _state(row)
        doc = _current_document(conn, document_id)
        payload = _payload(conn, doc, request)
    # Local validation still works when the deployment is not configured.
    result = {'BridgeStatus': 'rejected', 'Message': ''}
    try:
        result = _remote(settings, str(uuid4()), username, _json(payload), False)
        if payload.get('price_workflow_version')==2 and result.get('PriceWorkflowVersion')!=2:
            result={'BridgeStatus':'blocked','Message':'نسخهٔ جدید پل تفکیک رسید و رزرو قیمت هنوز روی ورانگر نصب یا فعال نشده است.'}
        if payload.get('replaces_receipts') and result.get('ReplacementSupported') != 1:
            result = {'BridgeStatus':'blocked','Message':'برای صدور دوبارهٔ رسید حذف‌شده، نسخهٔ جدید پل رسید باید روی سرور نصب شود.'}
    except WarehouseAssistantError as exc:
        result['Message'] = str(exc)
    except Exception:
        log.warning('Receipt preflight unavailable for checkbar %s', document_id)
        result['Message'] = 'بررسی رسید انجام نشد؛ نصب نسخهٔ جدید پل تفکیک رسید و رزرو قیمت، دسترسی اجرا و ارتباط با ورانگر را بررسی کنید.'
    return dict(status='ready' if result['BridgeStatus']=='ready' else 'invalid',
                preview_token=_token(payload), payload=payload, result=result,
                commit_enabled=getattr(settings, 'varanegar_receipt_commit_enabled', False))


def submit(settings, username, document_id, request=None):
    """request=None is recovery only: it can never create a new intent."""
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = _existing(conn, document_id)
        if row and row['status'] == 'sent':
            return _state(row)
        if not row or row['status'] == 'rejected':
            from app.warehouse_receipt_lifecycle import inspect
            inspect(conn, settings, document_id, strict=True)
        _enabled(settings, True)
        if not row or row['status'] == 'rejected':
            if request is None:
                raise WarehouseAssistantError('انتقال در انتظار پیگیری وجود ندارد.')
            doc = _current_document(conn, document_id)
            payload = _payload(conn, doc, request)
            if not doc.get('receipt_confirmed') and not request.matching_confirmed:
                raise WarehouseAssistantError('تطبیق تعداد شمارش‌شده با سفارش‌های در راه را تأیید کنید.')
            if not doc.get('receipt_confirmed') and payload['order_matching']['unallocated_qty'] > 0 and not request.accept_unallocated:
                raise WarehouseAssistantError('مقدار اضافه بر سفارش یا بدون سفارش را صریحاً تأیید کنید.')
            if not request.preview_token or request.preview_token != _token(payload):
                raise WarehouseAssistantError('ابتدا اطلاعات رسید را بررسی و پیش‌نمایش تازه را تأیید کنید.')
            if not re.fullmatch('[A-Fa-f0-9]{64}', request.validation_token):
                raise WarehouseAssistantError('ابتدا اعتبارسنجی تازه از ورانگر دریافت کنید.')
            payload['validation_token'] = request.validation_token
            # Original issuance identity survives restoration of a database backup
            # taken before the first transfer. Never mint a new key from a revision
            # or from a newly-created local transfer ledger.
            original = dict(conn.execute('''SELECT id,created_at,created_by,request_id,request_hash
                FROM warehouse_checkbars WHERE id=?''', (document_id,)).fetchone())
            key = str(uuid5(NAMESPACE_URL, 'urn:neginai:checkbar:' + _json(original)))
            if payload.get('replaces_receipts'):
                key = str(uuid5(NAMESPACE_URL, key + ':after:' + payload['replaces_receipts'][-1]['transfer_key']))
            conn.execute('''INSERT INTO warehouse_checkbar_transfers
                (document_id,transfer_key,revision,requested_by,payload_json,status,updated_at)
                VALUES(?,?,?,?,?,'pending',?) ON CONFLICT(document_id) DO UPDATE SET
                revision=excluded.revision,requested_by=excluded.requested_by,payload_json=excluded.payload_json,
                transfer_key=excluded.transfer_key,status='pending',result_json=NULL,updated_at=excluded.updated_at''',
                (document_id,key,doc['revision'],username,_json(payload),_now()))
            from app.warehouse_order_receipts import reserve
            reserve(conn, document_id, payload['order_matching'])
        # Commit intent before remote transaction. A crash is recoverable from this row.
    try:
        with warehouse_connection(settings) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = _existing(conn, document_id)
            if row['status'] != 'pending':
                return _state(row)
            result = _remote(settings,row['transfer_key'],row['requested_by'],row['payload_json'],True)
            state = {'sent':'sent', 'rejected':'rejected'}.get(result['BridgeStatus'], 'pending')
            if state == 'sent':
                from app.warehouse_order_receipts import sent
                sent(conn, row)
            conn.execute('UPDATE warehouse_checkbar_transfers SET status=?,result_json=?,updated_at=? WHERE document_id=?',
                         (state,_json(result),_now(),document_id))
            return _state(_existing(conn, document_id))
    except Exception:
        # Neither a timeout nor an application crash proves SQL rollback. Keep intent.
        log.warning('Receipt outcome uncertain for checkbar %s; frozen intent retained', document_id)
        return dict(status='pending', revision=row['revision'], result={
            'Message':'نتیجهٔ انتقال مشخص نشد. «پیگیری انتقال» همان درخواست را بدون ساخت رسید تکراری دنبال می‌کند.'})
