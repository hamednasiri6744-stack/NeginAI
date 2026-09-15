"""Per-product agreement expiry; retained history and invoice usage guards."""
import json
from app import warehouse_purchase_contracts as contracts


def apply_end_dates(c,value,previous,changes):
    if not previous or previous['scope']!='collection' or not isinstance(changes,dict):
        raise contracts.ContractError('پایان اعتبار باید برای کالای موجود در قرارداد ثبت شود.')
    ends=dict(previous.get('product_end_dates',{}))
    for code,raw in changes.items():
        if code not in previous['product_codes']:
            raise contracts.ContractError('پایان اعتبار فقط برای کالای عضو قرارداد قابل ثبت است.')
        end=contracts.clean_date(raw)
        if end<value['start_date'] or (value['end_date'] and end>value['end_date']):
            raise contracts.ContractError('پایان اعتبار کالا باید در بازهٔ اعتبار قرارداد باشد: '+code)
        if ends.get(code)==end:continue
        # Once recorded, shortening or extending the date is another audited revision.
        check_invoice_usage(c,previous,code,end)
        ends[code]=end
    value['product_end_dates']=ends


def check_invoice_usage(c,rule,code,end):
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_purchase_invoice_attempts' AND type='table'").fetchone():return
    catalog=c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=? AND product_code=?',(rule['supplier_id'],code)).fetchone()
    goods_id=json.loads(catalog[0]).get('goods_id') if catalog else None
    groups={rule.get('deduction_group') or rule['id']}
    for raw in c.execute('SELECT payload FROM warehouse_purchase_contract_history WHERE contract_id=?',(rule['id'],)):
        old=json.loads(raw[0]);groups.add(old.get('deduction_group') or old['id'])
    for attempt in c.execute("SELECT * FROM warehouse_purchase_invoice_attempts WHERE status IN ('pending','sent')"):
        payload=json.loads(attempt['payload_json'])
        on_date=payload.get('supplier_invoice_date','')
        if on_date<end:continue
        usage=c.execute('SELECT contract_id,product_code FROM warehouse_purchase_contract_usage WHERE transfer_key=?',(attempt['transfer_key'],)).fetchall()
        if usage:
            used=any(row['contract_id']==rule['id'] and row['product_code']==code for row in usage)
        else:
            # Older bridge payloads retain the exact discount group and goods identity.
            used=goods_id is not None and any(line.get('goods_id')==goods_id and line.get('tail_group') in groups for line in payload.get('lines',[]))
        if used:
            result=json.loads(attempt['result_json'] or '{}')
            number=result.get('InvoiceNo') or payload.get('supplier_invoice_no') or attempt['receipt_id']
            state='در حال ثبت یا پیگیری' if attempt['status']=='pending' else 'ثبت‌شده'
            raise contracts.ContractError(f'کالای {code}: فاکتور خرید {number} ({state}) به تاریخ {on_date} از این قانون استفاده کرده است؛ پایان اعتبار باید بعد از این تاریخ باشد.')


def member_history(settings,contract_id,code):
    events=[]
    prior=None
    for entry in reversed(contracts.history(settings,contract_id)):
        rule=entry['contract']
        present=code in rule.get('product_codes',[rule.get('product_code')])
        current=(present,rule.get('product_end_dates',{}).get(code),rule['start_date'],rule['end_date'],rule.get('stock_id'))
        if current!=prior and (present or (prior and prior[0])):
            events.append(dict(entry,product_code=code,member_end_date=current[1],member_present=present))
        prior=current
    return list(reversed(events))
