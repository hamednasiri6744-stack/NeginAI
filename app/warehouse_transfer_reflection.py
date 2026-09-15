"""Credit-voucher evidence in the exact SQL SNAPSHOT used to import stock.

Only the source leg is automatically reconciled. Destination receipt remains a
separate physical operation; a credit voucher never proves destination receipt.
"""
from collections import defaultdict
from decimal import Decimal
import json
from uuid import UUID
from app.warehouse_rebalancing import _fail
from app.warehouse_receipt_reflection import _rows, _contract


def capture(conn):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_transfer_bridge_intents'").fetchone():
        return []
    cursor=conn.execute('''SELECT document_id,transfer_key,payload_json,result_json,status
        FROM warehouse_transfer_bridge_intents t WHERE status<>'rejected'
        AND NOT EXISTS(SELECT 1 FROM warehouse_transfer_document_deletions x WHERE x.document_id=t.document_id)
        ORDER BY document_id''')
    columns=[v[0] for v in cursor.description]
    return [dict(zip(columns,row)) for row in cursor]


def verify_current(conn,captured):
    if capture(conn)!=captured:
        _fail('هم‌زمان وضعیت ثبت جابه‌جایی تغییر کرده است؛ موجودی را دوباره بازخوانی کنید.')


def _classify(row, detail, contract):
    if not contract:
        return 'review','منطق اثر موجودی ورانگر تغییر کرده است؛ تطبیق بستانکار نیازمند بررسی است.'
    if row['status']!='sent':
        return 'review','نتیجهٔ ثبت بستانکار هنوز نامشخص است؛ پیگیری ثبت لازم است.'
    payload=json.loads(row['payload_json']);result=json.loads(row['result_json'])
    headers=detail['headers']
    if len(headers)!=1:return 'review','سند بستانکار یافت نشد یا هویت آن یکتا نیست.'
    h=headers[0]
    if (str(UUID(str(h['UniqueId'])))!=str(UUID(row['transfer_key']))
        or h['ID']!=result['VocherId'] or h['VocherNo']!=result['VocherNo']
        or h['StockDCRef']!=payload['source_stock_ref'] or h['TStockDCRef']!=payload['destination_stock_ref']
        or h['VocherTypeCode']!=65 or h['HealthCodeType']!=1047 or h['HealthCode']!=1
        or h['AccYear']!=result['AccYear'] or h['VocherDate'].strip()!=payload['voucher_date']
        or h['ConfirmedBy'] is None or h['ConfirmDate'] is None):
        return 'review','سربرگ یا تأیید سند بستانکار تغییر کرده است.'
    expected=defaultdict(Decimal);actual=defaultdict(Decimal)
    for line in payload['lines']:expected[str(line['product_code'])]+=Decimal(str(line['quantity']))
    for line in detail['items']:
        if line['UnitRef']!=line['BasicUnitRef'] or line['BasicUnitRef'] is None or Decimal(str(line['UnitCapacity']))!=1 or Decimal(str(line['UnitQty']))!=Decimal(str(line['TotalQty'])):
            return 'review','واحد یا تعداد بسته‌بندی سند بستانکار تغییر کرده است.'
        actual[str(line['GoodsCode'])]+=Decimal(str(line['TotalQty']))
    if expected!=actual:return 'review','اقلام سند بستانکار با سند جابه‌جایی یکسان نیست.'
    return 'reflected','خروج بستانکار در همین تصویر موجودی منعکس شده است؛ دریافت مقصد جداست.'


def source_queries(cursor,captured):
    if not captured:return {}
    # The existing receipt contract pins the enabled stock triggers by hash.
    contract=_contract(cursor)
    effects=_rows(cursor,'''SELECT CardexType,EffectOnHandQty,EffectType FROM inv.tblCardexType
        WHERE VocherTypeCode=65 AND (HealthCode=1 OR HealthCode IS NULL)''')
    flags=_rows(cursor,"SELECT KeyValue FROM GNR.tblServerConfig WHERE LTRIM(RTRIM(KeyName))='IsConfirmVchEffectiveonOnHandQty'")
    valid=contract['valid'] and effects==[dict(CardexType=1,EffectOnHandQty=True,EffectType=-1)] and flags==[dict(KeyValue='1')]
    evidence={}
    for row in captured:
        key=str(UUID(row['transfer_key']))
        result=json.loads(row['result_json']) if row['result_json'] else {}
        ident=int(result.get('VocherId') or 0)
        detail={}
        detail['headers']=_rows(cursor,f'''SELECT H.ID,H.UniqueId,H.VocherNo,H.StockDCRef,H.TStockDCRef,
            H.AccYear,H.VocherTypeCode,H.HealthCodeType,H.HealthCode,H.VocherDate,H.ConfirmedBy,H.ConfirmDate
            FROM inv.tblVocherHdr H WHERE H.UniqueId='{key}' OR H.ID={ident}''')
        ids=','.join(str(int(h['ID'])) for h in detail['headers']) or '0'
        detail['items']=_rows(cursor,f'''SELECT G.GoodsCode,I.UnitRef,G.UnitRef AS BasicUnitRef,
            I.UnitCapacity,I.UnitQty,I.TotalQty FROM inv.tblVocherItm I
            LEFT JOIN gnr.tblGoods G ON G.ID=I.GoodsRef WHERE I.HdrRef IN ({ids}) ORDER BY I.ID''')
        try:
            state,message=_classify(row,detail,valid)
        except (ValueError,TypeError,KeyError,ArithmeticError):
            state,message='review','اطلاعات بستانکار برای تطبیق معتبر نیست.'
        evidence[row['document_id']]=dict(status=state,message=message,contract=contract,effects=effects,flags=flags,**detail)
    return json.loads(json.dumps(evidence,ensure_ascii=False,default=str))


def apply(conn,captured,evidence,snapshot_id):
    from app.warehouse_assistant_service import _now
    verify_current(conn,captured)
    if set(map(str,evidence))!={str(row['document_id']) for row in captured}:
        _fail('شواهد تطبیق جابه‌جایی کامل نیست.')
    snap=conn.execute('SELECT source_kind,period_end FROM warehouse_snapshots WHERE id=?',(snapshot_id,)).fetchone()
    if not snap or snap[0]!='varanegar':_fail('تطبیق بستانکار به موجودی مستقیم ورانگر نیاز دارد.')
    for row in captured:
        detail=dict(evidence.get(row['document_id'],evidence.get(str(row['document_id']))))
        state=detail['status']
        if state not in ('reflected','review'):_fail('وضعیت تطبیق بستانکار معتبر نیست.')
        if any(str(h.get('AccYear'))!=str(snap[1] or '')[:4] for h in detail.get('headers',[])):
            state=detail['status']='review';detail['message']='سال مالی سند با موجودی متفاوت است.'
        conn.execute('''INSERT INTO warehouse_transfer_source_stock_state VALUES(?,?,?,?,?)
            ON CONFLICT(document_id) DO UPDATE SET status=excluded.status,snapshot_id=excluded.snapshot_id,
            evidence_json=excluded.evidence_json,updated_at=excluded.updated_at''',
            (row['document_id'],state,snapshot_id,json.dumps(detail,ensure_ascii=False,sort_keys=True),_now()))


def review_codes(conn,warehouse):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_transfer_bridge_intents'").fetchone():return set()
    codes=set()
    for row in conn.execute('''SELECT t.status,t.payload_json,s.status AS stock_status,s.snapshot_id
        FROM warehouse_transfer_bridge_intents t JOIN warehouse_transfer_documents d ON d.id=t.document_id
        LEFT JOIN warehouse_transfer_source_stock_state s ON s.document_id=t.document_id
        WHERE t.status<>'rejected' AND (d.source=? OR d.destination=?)
        AND NOT EXISTS(SELECT 1 FROM warehouse_transfer_document_deletions x WHERE x.document_id=d.id)
        AND (t.status<>'sent' OR s.status IS NULL OR s.status<>'reflected'
            OR s.snapshot_id<>(SELECT MAX(id) FROM warehouse_snapshots))''',(warehouse,warehouse)):
        codes.update(line['product_code'] for line in json.loads(row['payload_json'])['lines'])
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_transfer_erp_state'").fetchone():
        for row in conn.execute('''SELECT t.payload_json FROM warehouse_transfer_bridge_intents t
            JOIN warehouse_transfer_documents d ON d.id=t.document_id
            LEFT JOIN warehouse_transfer_erp_state es ON es.document_id=d.id
            LEFT JOIN warehouse_transfer_erp_refresh er ON er.document_id=d.id
            WHERE t.status='sent' AND (es.status<>'confirmed' OR er.generation<>er.published_generation)
            AND (d.source=? OR d.destination=?)
            AND NOT EXISTS(SELECT 1 FROM warehouse_transfer_document_deletions x WHERE x.document_id=d.id)''',
            (warehouse,warehouse)):
            codes.update(line['product_code'] for line in json.loads(row['payload_json'])['lines'])
    return codes
