"""Receipt-to-purchase-invoice preview and a fixed, disabled-by-default writer.

Never accepts SQL, factors, prices or ERP user identities from the browser.
Durable attempts retain identical bytes across uncertain network outcomes.
"""
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from app import warehouse_purchase_contracts as contracts
from app.warehouse_purchase_prices import resolve_source_prices, require_source_price
from app.database import sql_connection
from app.sql_guard import validate_read_only_sql
from app.warehouse_assistant_service import warehouse_connection


class InvoiceError(ValueError):
    pass


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def token(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def source_query(receipt_id):
    if type(receipt_id) is not int or receipt_id <= 0:
        raise InvoiceError('شناسهٔ رسید معتبر نیست.')
    return f"""SELECT h.ID receipt_id,h.VocherNo receipt_no,h.AccYear fiscal_year,
      h.VocherDate receipt_date,h.VocherTypeCode receipt_type,h.SupplierRef supplier_id,
      h.StockDCRef stock_id,s.DCRef dc_id,h.ConfirmDate confirmed_at,
      h.TVocherNo supplier_reference,CONVERT(varbinary(max),h.Comment) comment,
      CONVERT(varbinary(max),p.SupplierName) supplier_name,
      CONVERT(varbinary(max),s.StockDCName) stock_name,
      CASE WHEN EXISTS(SELECT 1 FROM ICA.tblSupInvInvoiceRelation r WHERE r.InvVchHdrRef=h.ID) THEN 1 ELSE 0 END linked,
      i.ID receipt_item_id,i.GoodsRef goods_id,i.UnitRef unit_ref,i.UnitCapacity unit_capacity,
      i.TotalQty quantity,i.UnitQty unit_quantity,g.GoodsCode product_code,
      CONVERT(varbinary(max),g.GoodsName) product_name,
      CONVERT(varbinary(max),i.Comment) item_comment
      FROM Inv.tblVocherHdr h JOIN GNR.tblStockDC s ON s.ID=h.StockDCRef
      JOIN GNR.tblSupplier p ON p.ID=h.SupplierRef
      JOIN Inv.tblVocherItm i ON i.HdrRef=h.ID
      JOIN GNR.tblGoods g ON g.ID=i.GoodsRef
      WHERE h.ID={receipt_id} ORDER BY i.RowOrder,i.ID"""


def read_receipt(settings, receipt_id):
    try:
        with sql_connection(settings) as c:
            cur=c.cursor();cur.execute(validate_read_only_sql(source_query(receipt_id)).sql)
            columns=[d[0] for d in cur.description];rows=cur.fetchmany(501)
        if not rows:raise InvoiceError('رسید دارای اقلام پیدا نشد.')
        if len(rows)>500:raise InvoiceError('رسید بیش از ۵۰۰ قلم دارد.')
        result=[]
        for row in rows:
            item=dict(zip(columns,row))
            for field in ('supplier_name','stock_name','comment','product_name','item_comment','product_code'):
                item[field]=contracts.text(item[field])
            for field in ('quantity','unit_quantity','unit_capacity'):
                item[field]=str(item[field]) if item[field] is not None else None
            item['confirmed_at']=str(item['confirmed_at']) if item['confirmed_at'] else None
            result.append(item)
        return result
    except InvoiceError:raise
    except Exception:raise InvoiceError('خواندن رسید از ورانگر انجام نشد؛ هیچ فاکتوری ثبت نشد.') from None


def receipt_ids(value):
    ids=[value] if type(value) is int else value
    if not isinstance(ids,list) or not 1<=len(ids)<=20:
        raise InvoiceError('بین ۱ تا ۲۰ رسید انتخاب کنید.')
    if any(type(i) is not int or i<=0 or i>2147483647 for i in ids) or len(set(ids))!=len(ids):
        raise InvoiceError('شناسهٔ رسیدها باید معتبر و بدون تکرار باشد.')
    return sorted(ids)


def selected_receipts(settings,selection):
    ids=receipt_ids(selection)
    groups=[read_receipt(settings,i) for i in ids]
    head=groups[0][0];summaries=[]
    for group in groups:
        current=group[0]
        if current['receipt_type']!=20 or not current['confirmed_at'] or current['linked']:
            raise InvoiceError('فقط رسید خرید تأییدشده و بدون ارتباط فاکتور قابل انتخاب است.')
        if any(current[k]!=head[k] for k in ('supplier_id','stock_id','fiscal_year','dc_id')):
            raise InvoiceError('رسیدها باید برای یک تأمین‌کننده، یک انبار و یک سال مالی باشند.')
        if len({r['goods_id'] for r in group})!=len(group):
            raise InvoiceError('رسید برای یک کالا چند ردیف دارد؛ ادغام قیمت‌ها باید جدا بررسی شود.')
        summaries.append({k:current[k] for k in ('receipt_id','receipt_no','receipt_date','supplier_id','supplier_name','stock_id','stock_name','fiscal_year')})
    original=[r for g in groups for r in g]
    if len(original)>500:raise InvoiceError('مجموع اقلام رسیدهای انتخاب‌شده بیش از ۵۰۰ ردیف است.')
    if len(ids)==1:return ids,summaries,original,original
    combined={}
    for row in original:
        if not row['unit_ref'] or Decimal(row['unit_capacity'] or '0')!=1:
            raise InvoiceError('ادغام رسیدها فقط با واحد پایه و ضریب ۱ ممکن است.')
        qty=contracts.number(row['quantity'],'تعداد '+row['product_code'],0.001,1000000000)
        goods=row['goods_id']
        if goods not in combined:
            combined[goods]=dict(row,quantity='0',receipt_sources=[])
        item=combined[goods]
        if item['unit_ref']!=row['unit_ref']:raise InvoiceError('واحد کالای مشترک در رسیدها یکسان نیست.')
        item['quantity']=str(Decimal(item['quantity'])+qty)
        item['receipt_sources'].append(dict(receipt_id=row['receipt_id'],receipt_no=row['receipt_no'],quantity=str(qty)))
    return ids,summaries,original,[combined[g] for g in sorted(combined)]


def clean_invoice_date(value):
    # Older desktop pages appended Intl's Persian-calendar era to this field.
    # Accept that exact representation, then retain full calendar validation.
    value=contracts.digits(value or '').strip()
    if re.fullmatch(r'\d{4}/\d{2}/\d{2}\s+AP',value):
        value=value.split()[0]
    return contracts.clean_date(value)


def invoice_presentation(details,calculation,total):
    """Display exact server amounts without recalculating prices in the browser."""
    items=[]
    for detail,line in zip(details,calculation):
        rule=line['rule']
        amounts=detail.get('amounts')
        display_amounts=dict(amounts,after_tax=str(Decimal(amounts['net_before_tax'])+Decimal(amounts['tax']))) if amounts else None
        items.append(dict(detail,amounts=display_amounts,pricing=dict(basis=rule['basis'],includes_tax=rule['includes_tax'],
            adjustment_percent=rule['adjustment_percent'],discount_percent=rule['discount_percent'],
            discount_steps=contracts.discount_steps(rule),tail=contracts.tail_settings(rule))))
    if total is None:return items,None
    fields=('gross','discount','net_before_tax','tax','tail_discount')
    sums={field:sum(Decimal(d['amounts'][field]) for d in details) for field in fields}
    sums['after_tax']=sums['net_before_tax']+sums['tax']
    sums['total']=Decimal(total)
    groups={}
    for item in items:
        tail=item['pricing']['tail'];key=(tail['kind'],tail['basis'],tail['value'])
        group=groups.setdefault(key,dict(tail,base=Decimal(0),amount=Decimal(0)))
        group['base']+=Decimal(item['amounts']['tail_base'])
        group['amount']+=Decimal(item['amounts']['tail_discount'])
    summary={k:str(v) for k,v in sums.items()}
    summary['tail_discounts']=[dict(g,base=str(g['base']),amount=str(g['amount'])) for g in groups.values()]
    return items,summary


def prepare(settings, receipt_id, request):
    """Fresh source prices, receipt quantities and dated rules; no ERP writes."""
    try:
        invoice_date=clean_invoice_date(request.get('supplier_invoice_date'))
        voucher_date=clean_invoice_date(request.get('voucher_date'))
        invoice_no=contracts.number(request.get('supplier_invoice_no'),'شماره فاکتور تأمین‌کننده',1,2147483647)
        if invoice_no != int(invoice_no):raise InvoiceError('شماره فاکتور باید عدد صحیح باشد.')
        ids,receipts,original_rows,rows=selected_receipts(settings,receipt_id);head=rows[0]
        receipt_id=ids[0]
        if head['receipt_type']!=20 or not head['confirmed_at'] or head['linked']:
            raise InvoiceError('فقط رسید خرید تأییدشده و بدون ارتباط فاکتور قابل انتخاب است.')
        if head['stock_id'] not in (1,2,9):
            raise InvoiceError('پل خرید فقط برای انبارهای تعریف‌شده فعال است.')
        if int(invoice_date[:4])!=head['fiscal_year'] or int(voucher_date[:4])!=head['fiscal_year']:
            raise InvoiceError('سال مالی رسید و تاریخ‌های فاکتور باید یکسان باشند.')
        if len({r['goods_id'] for r in rows})!=len(rows):
            raise InvoiceError('رسید برای یک کالا چند ردیف دارد؛ ادغام قیمت‌ها باید جدا بررسی شود.')
        products={r['goods_id']:r for r in contracts.resolve_products(settings,head['supplier_id'],invoice_date,stock_id=head['stock_id'],include_prices=False)['items']}
        sources=resolve_source_prices(settings,[r['goods_id'] for r in rows],invoice_date,head['stock_id'])
        errors=[];calculation=[];details=[]
        for row in rows:
            item=products.get(row['goods_id']);rule=item.get('contract') if item else None
            label=f"{row['product_code']} · {row['product_name']}"
            try:
                if not rule:raise InvoiceError(label+': قرارداد خرید معتبر در تاریخ فاکتور ندارد.')
                if item['tax_status']!='known':raise InvoiceError(label+': نرخ مالیات نامشخص یا ناسازگار است.')
                price=require_source_price(rule,item,sources.get(row['goods_id']))
                qty=contracts.number(row['quantity'],'تعداد '+label,0.001,1000000000)
                if not row['unit_ref'] or Decimal(row['unit_capacity'] or '0')!=1:
                    raise InvoiceError(label+': نسخهٔ اول پل فقط واحد پایه با ضریب ۱ را می‌پذیرد.')
                tail=contracts.tail_settings(rule)
                steps=contracts.discount_steps(rule)
                if len(steps)>2:
                    raise InvoiceError(label+': بیش از دو مرحله تخفیف ستونی در ورانگر برای این پل تعریف نشده است.')
                if tail['kind']!='percent' or tail['basis']!='net_before_tax':
                    raise InvoiceError(label+': نوع تخفیف انتهایی این قرارداد هنوز در پل ورانگر قابل ثبت نیست.')
                calculation.append(dict(rule=rule,price=price,quantity=str(qty),tax_rate=item['tax_rate']))
                details.append(dict(row,contract_id=rule['id'],contract_revision=rule['revision'],
                    source_price=price,price_basis=rule['basis'],price_source=sources.get(row['goods_id']),tax_rate=item['tax_rate'],
                    manufacturer_product_code=item.get('manufacturer_product_code',''),barcode=item.get('barcode',''),
                    group_level3=item.get('group_level3') or item.get('group_name','')))
            except (contracts.ContractError,InvoiceError) as exc:errors.append(str(exc))
        payload=None;total=None
        if not errors:
            result=contracts.calculate_invoice(calculation)
            # Percentage tail factors are invoice-level ERP factors. Round once
            # per contract deduction group and allocate every rial deterministically.
            tail_groups={}
            for index,(line,detail) in enumerate(zip(calculation,details)):
                tail=contracts.tail_settings(line['rule'])
                key=(line['rule'].get('deduction_group') or line['rule']['id'],tail['value'])
                tail_groups.setdefault(key,[]).append(index)
                detail['tail_group']=str(key[0])
            for (group,value),indices in tail_groups.items():
                raw=[Decimal(result['items'][i]['net_before_tax'])*Decimal(value)/100 for i in indices]
                allocated=[int(amount) for amount in raw]
                target=int(sum(raw).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
                for j in sorted(range(len(raw)),key=lambda j:raw[j]-allocated[j],reverse=True)[:target-sum(allocated)]:allocated[j]+=1
                for i,tail_amount in zip(indices,allocated):
                    amounts=result['items'][i]
                    amounts['tail_discount']=str(tail_amount)
                    amounts['total']=str(Decimal(amounts['net_before_tax'])+Decimal(amounts['tax'])-tail_amount)
            total=str(sum(Decimal(r['total']) for r in result['items']));lines=[]
            for detail,amounts in zip(details,result['items']):
                detail['amounts']=amounts
                rule=next(line['rule'] for line in calculation if line['rule']['id']==detail['contract_id'])
                tail=contracts.tail_settings(rule)
                lines.append(dict(goods_id=detail['goods_id'],quantity=detail['quantity'],unit_ref=detail['unit_ref'],
                    unit_price=amounts['unit_price'],gross_amount=amounts['gross'],column_discount=amounts['discount'],
                    tax_amount=amounts['tax'],tail_discount=amounts['tail_discount'],tax_rate=detail['tax_rate'],
                    discount_steps=contracts.discount_steps(rule),tail_value=tail['value'],tail_group=detail['tail_group']))
            payload=dict(receipt_id=receipt_id,voucher_date=voucher_date,supplier_invoice_date=invoice_date,
                supplier_invoice_no=int(invoice_no),comment=contracts.text(request.get('comment'))[:200],lines=lines)
        if payload and len(ids)>1:payload['receipt_ids']=ids
        basis=dict(payload=payload,receipt=original_rows,details=details)
        bridge_ready=False
        bridge_message='پل ثبت فاکتور خرید هنوز فعال نشده است.'
        if payload and getattr(settings,'varanegar_purchase_bridge_enabled',False):
            validation=preflight(settings,payload)
            bridge_ready=validation['ready']
            bridge_message=validation['message']
        display_items,summary=invoice_presentation(details,calculation,total)
        return dict(receipt_id=receipt_id,receipt_ids=ids,receipt_nos=[r['receipt_no'] for r in receipts],receipts=receipts,receipt_no=head['receipt_no'],supplier=head['supplier_name'],stock=head['stock_name'],
            contract_usage=[dict(contract_id=d['contract_id'],revision=d['contract_revision'],product_code=d['product_code'],stock_id=head['stock_id'],invoice_date=invoice_date) for d in details],items=display_items,summary=summary,errors=errors,total=total,payload=payload,preview_token=token(basis) if payload else '',
            ready=not errors,bridge_ready=bridge_ready,bridge_message=bridge_message,
            commit_enabled=bool(getattr(settings,'varanegar_purchase_commit_enabled',False)) and bridge_ready,
            bridge_enabled=bool(getattr(settings,'varanegar_purchase_bridge_enabled',False)),varanegar_write=False)
    except contracts.ContractError as exc:raise InvoiceError(str(exc)) from None


def initialize(settings):
    with warehouse_connection(settings) as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('''CREATE TABLE IF NOT EXISTS warehouse_purchase_invoice_attempts (
          transfer_key TEXT PRIMARY KEY, receipt_id INTEGER NOT NULL, actor TEXT NOT NULL,
          preview_token TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL,
          result_json TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('CREATE TABLE IF NOT EXISTS warehouse_purchase_invoice_receipts (receipt_id INTEGER PRIMARY KEY,transfer_key TEXT NOT NULL REFERENCES warehouse_purchase_invoice_attempts(transfer_key))')
        # Backfill legacy attempts and retain every receipt across uncertain outcomes.
        for row in c.execute("SELECT transfer_key,payload_json,receipt_id FROM warehouse_purchase_invoice_attempts WHERE status IN ('pending','sent')").fetchall():
            payload=json.loads(row['payload_json'])
            for rid in receipt_ids(payload.get('receipt_ids',row['receipt_id'])):
                found=c.execute('SELECT transfer_key FROM warehouse_purchase_invoice_receipts WHERE receipt_id=?',(rid,)).fetchone()
                if found and found[0]!=row['transfer_key']:raise InvoiceError('سابقهٔ رسیدها هم‌پوشانی دارد؛ نیاز به بررسی است.')
                c.execute('INSERT OR IGNORE INTO warehouse_purchase_invoice_receipts(receipt_id,transfer_key) VALUES(?,?)',(rid,row['transfer_key']))
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS warehouse_purchase_invoice_active_receipt ON warehouse_purchase_invoice_attempts(receipt_id) WHERE status IN ('pending','sent')")


def preflight(settings,payload):
    # @Commit=0 runs the same SQL validation before native IDs or writes.
    try:
        result=remote(settings,str(uuid4()),'Negin assistant validation',encoded(payload),commit=False)
    except Exception:
        return dict(ready=False,message='اتصال یا مجوز اجرای پل خرید آماده نیست؛ تنظیم اتصال و مجوز پل باید بررسی شود.')
    if result['BridgeStatus']=='ready':
        return dict(ready=True,message='اتصال و مجوز پل بررسی شد؛ فاکتور به‌صورت تأییدنشده ثبت می‌شود.')
    if result.get('ErrorCode')==51201 and len(payload.get('receipt_ids',[]))>1:
        message='پل ورانگر برای چند رسید به‌روزرسانی نشده است؛ پیش‌نمایش آماده است اما ثبت به به‌روزرسانی پل نیاز دارد.'
    elif result.get('ErrorCode')==51217:
        message='پل هنوز در حالت آزمایشیِ مجوز هر فاکتور است؛ استفادهٔ روزمره برای این انبار باید یک‌بار روی سرور فعال شود.'
    elif result.get('ErrorCode')==51204:
        message='ثبت فاکتور برای این حساب و انبار هنوز فعال نشده است.'
    elif result.get('ErrorCode')==51206 and 'retained transfer history' in str(result.get('Message','')):
        message='این رسید قبلاً به فاکتور متصل شده یا سابقهٔ ثبت دارد؛ اگر فاکتور در ورانگر حذف شده، سابقهٔ انتقال باید بررسی شود. فاکتور جدید ثبت نشد.'
    else:
        message='کنترل ورانگر اجازهٔ ثبت نداد: '+str(result.get('Message') or 'وضعیت پل را بررسی کنید.')
    return dict(ready=False,message=message)


def remote(settings,key,actor,payload,commit=True):
    # Reuses the dedicated limited connection; it has no purchase permission until
    # the fixed wrapper is deliberately installed and verified on a separate DB.
    from app.warehouse_receipt_bridge import _connection
    with _connection(settings) as c:
        cur=c.cursor();cur.execute('''EXEC NeginAI.usp_CreatePurchaseInvoiceFromReceipt
          @TransferKey=%s,@RequestedBy=%s,@PayloadJson=%s,@Commit=%s''',(key,actor,payload,commit))
        while True:
            if cur.description:
                columns=[d[0] for d in cur.description]
                if 'BridgeStatus' in columns:
                    row=cur.fetchone();result=dict(zip(columns,row)) if row else {}
                    if result.get('BridgeStatus')=='sent' and (int(result.get('InvoiceId') or 0)<=0 or int(result.get('InvoiceNo') or 0)<=0 or result.get('Confirmed') not in (0,False)):
                        raise InvoiceError('پاسخ ثبت فاکتور نیاز به پیگیری دارد؛ دوباره سند نسازید.')
                    if result.get('BridgeStatus') not in (('sent','blocked','rejected') if commit else ('ready','blocked','rejected')):
                        raise InvoiceError('وضعیت ثبت فاکتور مشخص نیست؛ همان انتقال باید پیگیری شود.')
                    return result
            if not cur.nextset():break
    raise InvoiceError('پاسخ معتبر از پل فاکتور دریافت نشد.')


def commit(settings,actor,receipt_id,request):
    if not getattr(settings,'varanegar_purchase_bridge_enabled',False) or not getattr(settings,'varanegar_purchase_commit_enabled',False):
        raise InvoiceError('پل ثبت فاکتور خرید هنوز نصب، آزمون و فعال نشده است؛ هیچ فاکتوری ثبت نشد.')
    if request.get('confirmed') is not True or not request.get('preview_token'):
        raise InvoiceError('پیش‌نمایش فاکتور و تأیید صریح کاربر لازم است.')
    ids=receipt_ids(receipt_id);receipt_id=ids[0]
    placeholders=','.join('?' for _ in ids)
    initialize(settings)
    with warehouse_connection(settings) as c:
        existing=c.execute(f'SELECT DISTINCT a.* FROM warehouse_purchase_invoice_attempts a JOIN warehouse_purchase_invoice_receipts r ON r.transfer_key=a.transfer_key WHERE r.receipt_id IN ({placeholders})',ids).fetchall()
    if len(existing)>1:raise InvoiceError('رسیدها در انتقال‌های متفاوت استفاده شده‌اند؛ فاکتور جدید ایجاد نشد.')
    previous=existing[0] if existing else None
    if previous:
        attempt=dict(previous)
        saved=json.loads(attempt['payload_json'])
        if receipt_ids(saved.get('receipt_ids',attempt['receipt_id']))!=ids:
            raise InvoiceError('یک یا چند رسید قبلاً در انتقال دیگری استفاده شده‌اند؛ همان مجموعه را پیگیری کنید.')
        if attempt['actor']!=actor or attempt['preview_token']!=request['preview_token']:
            raise InvoiceError('این رسید انتقال ثبت‌شده یا در حال پیگیری دارد؛ فاکتور دوم ایجاد نشد.')
        if attempt['status']=='sent':return json.loads(attempt['result_json'])
    else:
        preview=prepare(settings,ids,request)
        if not preview['ready']:raise InvoiceError('\n'.join(preview['errors']))
        if not preview['bridge_ready']:raise InvoiceError(preview['bridge_message'])
        if preview['preview_token']!=request['preview_token']:raise InvoiceError('رسید، قیمت یا قرارداد تغییر کرده است؛ پیش‌نمایش را دوباره بررسی کنید.')
        attempt=dict(transfer_key=str(uuid4()),receipt_id=receipt_id,actor=actor,preview_token=preview['preview_token'],payload_json=encoded(preview['payload']))
        with warehouse_connection(settings) as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute(f'SELECT 1 FROM warehouse_purchase_invoice_receipts WHERE receipt_id IN ({placeholders})',ids).fetchone():
                raise InvoiceError('انتقال دیگری برای این رسید آغاز شده است؛ همان انتقال را پیگیری کنید.')
            for used in preview['contract_usage']:
                current=c.execute('SELECT revision FROM warehouse_purchase_contracts WHERE id=?',(used['contract_id'],)).fetchone()
                if not current or current[0]!=used['revision']:
                    raise InvoiceError('قرارداد یا پایان اعتبار کالا هم‌زمان تغییر کرد؛ پیش‌نمایش فاکتور را دوباره بگیرید.')
                c.execute('INSERT OR IGNORE INTO warehouse_purchase_contract_usage VALUES(?,?,?,?,?,?)',
                    (attempt['transfer_key'],used['contract_id'],used['revision'],used['product_code'],used['stock_id'],used['invoice_date']))
            c.execute('INSERT INTO warehouse_purchase_invoice_attempts(transfer_key,receipt_id,actor,preview_token,payload_json,status) VALUES(?,?,?,?,?,?)',
                (attempt['transfer_key'],receipt_id,actor,attempt['preview_token'],attempt['payload_json'],'pending'))
            c.executemany('INSERT INTO warehouse_purchase_invoice_receipts(receipt_id,transfer_key) VALUES(?,?)',[(i,attempt['transfer_key']) for i in ids])
    try:result=remote(settings,attempt['transfer_key'],actor,attempt['payload_json'])
    except Exception:
        raise InvoiceError('نتیجهٔ انتقال مشخص نیست؛ درخواست محفوظ است. پیگیری مجدد با همان مشخصات انجام شود؛ سند جدید نسازید.') from None
    with warehouse_connection(settings) as c:
        c.execute('UPDATE warehouse_purchase_invoice_attempts SET status=?,result_json=? WHERE transfer_key=?',
            (result['BridgeStatus'],encoded(result),attempt['transfer_key']))
        if result['BridgeStatus'] in ('blocked','rejected'):
            c.execute('DELETE FROM warehouse_purchase_invoice_receipts WHERE transfer_key=?',(attempt['transfer_key'],))
    return result
