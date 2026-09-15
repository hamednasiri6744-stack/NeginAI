"""Read-only ERP receipt evidence tied to the same SQL snapshot as stock.

The caller starts SNAPSHOT isolation before its inventory SELECT, then invokes
source_queries on that cursor. apply runs inside the local snapshot transaction.
No receipt is confirmed, edited, deleted, or recreated by this module.
"""
import hashlib
import json
from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from pytds.extensions import ISOLATION_LEVEL_SNAPSHOT


def snapshot_cursor(source):
    """Configure a fresh read connection before any inventory/evidence query.

    python-tds begins a transaction before executing SQL. Its isolation property
    rolls back that empty transaction and makes the next BEGIN use SNAPSHOT.
    Sending SET alone changes server state but leaves TDS BEGIN at its default.
    ODBC uses the existing SQL setup. Neither path commits or weakens isolation.
    """
    if hasattr(source, 'isolation_level'):
        source.isolation_level = ISOLATION_LEVEL_SNAPSHOT
        return source.cursor()
    cursor = source.cursor()
    cursor.execute('SET TRANSACTION ISOLATION LEVEL SNAPSHOT')
    return cursor


# Verified enabled definitions, including the blank ConfirmDate early return and
# confirmation/unconfirmation stock effects. An ERP upgrade requires re-review.
TRIGGER_HASHES = {
    'trg_tblVocherHdr_UpdateStockGoods': '26dcb28a1d0c31d409d98474a0170365754c303b42bcbb2922471b1cb4c3459e',
    'trg_tblVocherItm_UpdateStockGoods': '1c77af3da987f4026087cb98717a1cfff3eeac915b1aaacfa237db61f4827223',
}


def _fail(message):
    from app.warehouse_assistant_service import WarehouseAssistantError
    raise WarehouseAssistantError(message)


def _rows(cursor, sql):
    from app.sql_guard import validate_read_only_sql
    cursor.execute(validate_read_only_sql(sql).sql)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def capture(conn):
    rows = conn.execute('''SELECT t.document_id,t.transfer_key,t.payload_json,
        t.result_json,c.warehouse_code FROM warehouse_checkbar_transfers t
        JOIN warehouse_checkbars c ON c.id=t.document_id WHERE t.status='sent'
        ORDER BY t.document_id''')
    columns = [item[0] for item in rows.description]
    result = []
    for values in rows:
        row = dict(zip(columns, values))
        try:
            payload = json.loads(row['payload_json'])
            modern = payload.get('order_matching', {}).get('version') == 1
        except (ValueError, TypeError, AttributeError):
            _fail('سابقهٔ انتقال رسید خوانا نیست؛ بازخوانی موجودی متوقف شد.')
        if modern:
            result.append(row)
    # Detached generations remain evidence for the cached inventory until a new
    # transfer is sent. The same SQL snapshot proves that their stock is absent.
    archived = conn.execute('''SELECT h.document_id,h.transfer_key,h.payload_json,h.result_json,c.warehouse_code
        FROM warehouse_checkbar_transfer_history h JOIN warehouse_checkbars c ON c.id=h.document_id
        ORDER BY h.document_id,h.rowid''')
    names = [column[0] for column in archived.description]
    groups = defaultdict(list)
    for values in archived:
        old = dict(zip(names, values))
        groups[old['document_id']].append(old)
    current = {row['document_id']: row for row in result}
    for document_id, generations in groups.items():
        if document_id not in current:
            current[document_id] = dict(generations[-1], deleted_generation=True)
            result.append(current[document_id])
            generations = generations[:-1]
        predecessors=[]
        for r in generations:
            value=json.loads(r['result_json'])
            if value.get('PriceWorkflowVersion')==2:
                from app.warehouse_receipt_prices import documents
                predecessors.extend(dict(transfer_key=d['UniqueId'],vocher_id=d['VocherId']) for d in documents(value))
            else:
                predecessors.append(dict(transfer_key=r['transfer_key'],vocher_id=value['VocherId']))
        current[document_id]['predecessors']=predecessors
    return result


def verify_current(conn, captured):
    if capture(conn) != captured:
        _fail('هم‌زمان رسید دیگری منتقل شده است؛ موجودی را دوباره بازخوانی کنید.')


def _contract(cursor):
    config = _rows(cursor, "SELECT KeyValue FROM GNR.tblGeneralConfig WHERE KeyName='ConfirmVochersBeforeCloseDate'")
    effects = _rows(cursor, '''SELECT CardexType,EffectOnHandQty,EffectType FROM inv.tblCardexType
        WHERE VocherTypeCode=20 AND (HealthCode=1 OR HealthCode IS NULL)''')
    triggers = _rows(cursor, '''SELECT t.name,t.is_disabled,m.definition FROM sys.triggers t
        JOIN sys.sql_modules m ON m.object_id=t.object_id
        WHERE t.parent_id IN(OBJECT_ID('inv.tblVocherHdr'),OBJECT_ID('inv.tblVocherItm'))
          AND t.name IN('trg_tblVocherHdr_UpdateStockGoods','trg_tblVocherItm_UpdateStockGoods')''')
    hashes = {r['name']: hashlib.sha256((r['definition'] or '').encode('utf-8')).hexdigest() for r in triggers}
    valid = (config == [{'KeyValue': '1'}]
             and len(effects) == 1 and effects[0] == dict(CardexType=1, EffectOnHandQty=True, EffectType=1)
             and len(triggers) == 2 and not any(r['is_disabled'] for r in triggers)
             and hashes == TRIGGER_HASHES)
    return dict(valid=valid, configuration=config, effects=effects, trigger_hashes=hashes)


def _literal(value):
    return "N'" + str(value).replace("'", "''") + "'"


def _receipt(cursor, row):
    payload, result = json.loads(row['payload_json']), json.loads(row['result_json'])
    receipt_id = int(result['VocherId'])
    if receipt_id <= 0:
        raise ValueError('invalid receipt identity')
    headers = _rows(cursor, f'''SELECT H.ID,H.UniqueId,H.VocherNo,H.StockDCRef,H.AccYear,
        H.VocherTypeCode,H.HealthCodeType,H.HealthCode,H.SupplierRef,S.SupplierName,
        H.VocherDate,H.TVocherNo,H.ConfirmDate,H.ConfirmedBy,H.Comment,H.ChangeTimeStamp
        FROM inv.tblVocherHdr H LEFT JOIN gnr.tblSupplier S ON S.Id=H.SupplierRef
        WHERE H.ID={receipt_id} OR H.UniqueId='{UUID(row['transfer_key'])}' ''')
    items = _rows(cursor, f'''SELECT I.GoodsRef,G.GoodsCode,I.UnitRef,G.UnitRef AS BasicUnitRef,
        I.UnitCapacity,I.UnitQty,I.TotalQty,I.Comment
        FROM inv.tblVocherItm I LEFT JOIN gnr.tblGoods G ON G.ID=I.GoodsRef
        WHERE I.HdrRef={receipt_id} ORDER BY I.GoodsRef,I.UnitRef,I.Comment,I.ID''')
    date = _literal(payload['voucher_date'])
    years = _rows(cursor, f'SELECT AccYear FROM gnr.tblAccYear WHERE {date} BETWEEN StartDate AND EndDate')
    refs = [int(value) for value in payload['supplier_refs']]
    supplier_filter = ('S.Id IN (' + ','.join(str(value) for value in refs) + ')'
                       if refs else 'S.SupplierName=' + _literal(payload['supplier_name']))
    codes = ','.join(_literal(line['product_code']) for line in payload['lines'])
    suppliers = _rows(cursor, f'''SELECT S.Id FROM gnr.tblSupplier S WHERE S.Active=1
        AND {supplier_filter} AND NOT EXISTS(
            SELECT 1 FROM gnr.tblGoods G WHERE G.GoodsCode IN ({codes})
            AND NOT EXISTS(SELECT 1 FROM gnr.tblGoodsSupplier GS
                WHERE GS.GoodsRef=G.ID AND GS.SupplierRef=S.Id))''')
    return dict(headers=headers, items=items, years=years, suppliers=suppliers)


def _number(value):
    number = Decimal(str(value))
    if not number.is_finite() or number < 0:
        raise ValueError('invalid receipt quantity')
    return number


def _classify(row, evidence, contract):
    if not contract['valid']:
        return 'review', 'منطق تأیید و اثر موجودی ورانگر با قرارداد بررسی‌شده مطابقت ندارد.'
    payload, result = json.loads(row['payload_json']), json.loads(row['result_json'])
    reserve=result.get('Role')=='price_reserve'
    if len(evidence['headers']) != 1:
        return 'review', 'رسید انتقال‌یافته در ورانگر یافت نشد؛ احتمال حذف یا تغییر شناسه وجود دارد.'
    h = evidence['headers'][0]
    if (str(UUID(str(h['UniqueId']))) != str(UUID(row['transfer_key']))
            or int(h['ID']) != int(result['VocherId']) or int(h['VocherNo']) != int(result['VocherNo'])
            or int(h['StockDCRef']) != int(payload['stock_dc_ref'])
            or int(h['VocherTypeCode']) != (76 if reserve else 20) or int(h['HealthCodeType']) != (1009 if reserve else 12) or int(h['HealthCode']) != 1
            or h['VocherDate'].strip() != payload['voucher_date']
            or (not reserve and int(h['TVocherNo']) != int(payload['reference_no']))
            or (h['Comment'] or '').replace('ي','ی').replace('ك','ک') != payload['comment'].replace('ي','ی').replace('ك','ک')
            or evidence['years'] != [{'AccYear': h['AccYear']}]
            or (not reserve and evidence['suppliers'] != [{'Id': h['SupplierRef']}])
            or ('AccYear' in result and int(result['AccYear']) != int(h['AccYear']))):
        return 'review', 'هویت یا اطلاعات سربرگ رسید ورانگر تغییر کرده است.'
    expected, actual = defaultdict(Decimal), defaultdict(Decimal)
    for line in payload['lines']:
        expected[(line['product_code'], line['item_comment'])] += _number(line['quantity'])
    for item in evidence['items']:
        if (item['UnitRef'] != item['BasicUnitRef'] or item['BasicUnitRef'] is None
                or _number(item['UnitCapacity']) != 1
                or _number(item['UnitQty']) != _number(item['TotalQty'])):
            return 'review', 'واحد یا تعداد بسته‌بندی رسید با چک‌بار منطبق نیست.'
        actual[(item['GoodsCode'], item['Comment'])] += _number(item['TotalQty'])
    if actual != expected:
        return 'review', 'اقلام، تعداد یا توضیحات رسید ورانگر با چک‌بار منطبق نیست.'
    if (h['ConfirmDate'] is None) != (h['ConfirmedBy'] is None):
        return 'review', 'وضعیت تأیید رسید ورانگر ناسازگار است.'
    return ('waiting', 'رسید هنوز در ورانگر تأیید نشده است.') if h['ConfirmDate'] is None else ('reflected', 'رسید در همان تصویر موجودی تأیید شده است.')


def _bundle(cursor,row,contract):
    from app.warehouse_receipt_prices import documents, component_payload, validate_result
    payload,result=json.loads(row['payload_json']),json.loads(row['result_json'])
    validate_result(payload,result,True)
    effects=_rows(cursor,'''SELECT CardexType,EffectOnHandQty,EffectType FROM inv.tblCardexType
        WHERE VocherTypeCode=76 AND (HealthCode=1 OR HealthCode IS NULL) ORDER BY CardexType''')
    contract=dict(contract,valid=contract['valid'] and effects==[
        dict(CardexType=1,EffectOnHandQty=True,EffectType=-1),dict(CardexType=4,EffectOnHandQty=True,EffectType=1)])
    components=[];pending=[];states=[]
    for component in documents(result):
        part=component_payload(payload,component)
        child=dict(row,transfer_key=component['UniqueId'],payload_json=json.dumps(part),result_json=json.dumps(component))
        detail=_receipt(cursor,child)
        if row.get('deleted_generation'):
            state='waiting' if not detail['headers'] and not detail['items'] and contract['valid'] else 'review'
        else:
            state,_=_classify(child,detail,contract)
            if component['Role']!='unpriced_receipt' and state!='reflected':state='review'
        states.append(state)
        if state=='waiting' and component['Role']!='price_reserve':pending.extend(part['lines'])
        components.append(dict(component=component,status=state,**detail))
    status='review' if 'review' in states else 'waiting' if 'waiting' in states else 'reflected'
    return dict(status=status,message='وضعیت رسیدهای تفکیک‌شده و رزرو در تصویر موجودی بررسی شد.',
                components=components,pending_lines=pending,
                headers=[h for c in components for h in c['headers']])


def source_queries(cursor, captured):
    """Return {document_id: evidence}; SELECT failure aborts the stock import.

Requires the same cursor/SQL SNAPSHOT transaction used for inventory. No SET,
EXEC, write, grant, audit-table permission, or secondary connection is used.
"""
    if not captured:
        return {}
    try:
        contract = _contract(cursor)
        result = {}
        for row in captured:
            try:
                modern=json.loads(row['result_json']).get('PriceWorkflowVersion')==2
                detail = _bundle(cursor,row,contract) if modern else _receipt(cursor, row)
                if modern:
                    status,message=detail['status'],detail['message']
                elif row.get('deleted_generation') and not detail['headers'] and not detail['items'] and contract['valid']:
                    status,message='waiting','حذف رسید در تصویر تازهٔ موجودی تأیید شد؛ دریافت محلی هنوز نگهداری می‌شود.'
                elif row.get('deleted_generation'):
                    status,message='review','رسید حذف‌شده دوباره وجود دارد یا وضعیت آن نامشخص است؛ بررسی لازم است.'
                else:
                    status, message = _classify(row, detail, contract)
                # Every older generation must still be absent, even if a newer
                # replacement is valid. A restored old voucher can duplicate stock.
                detail['predecessors'] = []
                for prior in row.get('predecessors', []):
                    old_id, old_key = int(prior['vocher_id']), str(UUID(prior['transfer_key']))
                    headers = _rows(cursor, f"SELECT H.ID FROM inv.tblVocherHdr H WHERE H.ID={old_id} OR H.UniqueId='{old_key}'")
                    items = _rows(cursor, f'SELECT TOP (1) I.HdrRef FROM inv.tblVocherItm I WHERE I.HdrRef={old_id}')
                    detail['predecessors'].append(dict(**prior, headers=headers, items=items))
                    if headers or items:
                        status,message='review','یکی از سندهای قبلی دوباره در ورانگر وجود دارد؛ بررسی لازم است.'
            except (ValueError, TypeError, KeyError, ArithmeticError):
                detail, status, message = {}, 'review', 'اطلاعات رسید برای تطبیق معتبر نیست.'
            result[row['document_id']] = dict(status=status, message=message, contract=contract, **detail)
        # Freeze portable evidence for digest/storage; never include SQL credentials.
        return json.loads(json.dumps(result, ensure_ascii=False,
            default=lambda value: value.hex() if isinstance(value, bytes) else str(value)))
    except Exception as exc:
        from app.warehouse_assistant_service import WarehouseAssistantError
        if isinstance(exc, WarehouseAssistantError):
            raise
        raise WarehouseAssistantError('خواندن وضعیت رسیدهای منتقل‌شده انجام نشد؛ موجودی قبلی حفظ شد. دسترسی خواندن و ارتباط ورانگر را بررسی کنید.') from exc


def apply(conn, captured, evidence, snapshot_id):
    from app.warehouse_assistant_service import _now
    verify_current(conn, captured)
    snapshot = conn.execute('SELECT source_kind,period_end FROM warehouse_snapshots WHERE id=?', (snapshot_id,)).fetchone()
    if snapshot is None or snapshot[0] != 'varanegar':
        _fail('تطبیق رسید به تصویر موجودی زندهٔ ورانگر نیاز دارد.')
    if {str(key) for key in evidence} != {str(row['document_id']) for row in captured}:
        _fail('شواهد تطبیق همهٔ رسیدها کامل نیست؛ موجودی قبلی حفظ شد.')
    for row in captured:
        detail = dict(evidence.get(row['document_id'], evidence.get(str(row['document_id']))))
        status = detail['status']
        if status not in ('waiting', 'reflected', 'review'):
            _fail('وضعیت تطبیق رسید معتبر نیست.')
        headers = detail.get('headers', [])
        if headers and str(headers[0].get('AccYear')) != str(snapshot[1] or '')[:4]:
            status = detail['status'] = 'review'
            detail['message'] = 'سال مالی رسید با تصویر موجودی یکسان نیست؛ تطبیق دستی لازم است.'
        conn.execute('''INSERT INTO warehouse_receipt_stock_state
            (document_id,warehouse_code,status,snapshot_id,evidence_json,updated_at)
            VALUES(?,?,?,?,?,?) ON CONFLICT(document_id) DO UPDATE SET
            warehouse_code=excluded.warehouse_code,status=excluded.status,
            snapshot_id=excluded.snapshot_id,evidence_json=excluded.evidence_json,updated_at=excluded.updated_at''',
            (row['document_id'], row['warehouse_code'], status, snapshot_id,
             json.dumps(detail, ensure_ascii=False, sort_keys=True), _now()))
