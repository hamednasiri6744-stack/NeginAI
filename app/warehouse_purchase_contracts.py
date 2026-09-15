"""Dated purchase agreements and read-only ERP product/tax catalog.

Only the assistant's dedicated contract/catalog tables are changed. This module
never posts invoices, adjusts orders/stock, or executes an ERP procedure.
"""
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import lru_cache
import json
import re
from uuid import uuid4

from app.business_time import jalali_business_date, gregorian_to_jalali
from app.database import sql_connection
from app.sql_guard import validate_read_only_sql


class ContractError(ValueError):
    pass


CATALOG_SQL = """SELECT g.ID GoodsRef,g.GoodsCode,
 CONVERT(varbinary(max),g.GoodsName) GoodsName,g.BrandRef,
 CONVERT(varbinary(max),b.BrandName) BrandName,gs.SupplierRef,
 CONVERT(varbinary(max),s.SupplierName) SupplierName,g.ManufacturerRef,
 CONVERT(varbinary(max),m.ManufacturerName) ManufacturerName,level3.ID GroupRef,
 CONVERT(varbinary(max),level3.GoodsGroupName) GroupName,
 CONVERT(varbinary(max),mt.MainName) TaxGroupName,
 CONVERT(varbinary(max),st.SubName) TaxLabel
FROM GNR.tblGoods g
LEFT JOIN GNR.tblBrand b ON b.ID=g.BrandRef
LEFT JOIN GNR.tblGoodsSupplier gs ON gs.GoodsRef=g.ID
LEFT JOIN GNR.tblSupplier s ON s.ID=gs.SupplierRef
LEFT JOIN GNR.tblManufacturer m ON m.ID=g.ManufacturerRef
LEFT JOIN GNR.tblGoodsGroup gg ON gg.ID=g.GoodsGroupRef
LEFT JOIN GNR.tblGoodsGroup level3 ON level3.NLevel=3 AND gg.NLeft>=level3.NLeft AND gg.NRight<=level3.NRight
LEFT JOIN GNR.tblGoodsMainSubType ms ON ms.GoodsRef=g.ID AND ms.MainTypeRef=1
LEFT JOIN GNR.tblMainType mt ON mt.ID=ms.MainTypeRef
LEFT JOIN GNR.tblSubType st ON st.ID=ms.SubTypeRef AND st.MainTypeRef=ms.MainTypeRef
ORDER BY g.GoodsCode,gs.SupplierRef,st.ID"""


def connect(settings):
    from app.warehouse_assistant_service import warehouse_connection
    return warehouse_connection(settings)


def enrich_product_identities(connection, rows):
    """Attach the latest local snapshot identity without changing catalog scope."""
    rows = list(rows)
    has_snapshots = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_snapshots'").fetchone()
    latest = connection.execute('SELECT id FROM warehouse_snapshots ORDER BY id DESC LIMIT 1').fetchone() if has_snapshots else None
    identities = {}
    if latest:
        for item in connection.execute('''SELECT product_code,manufacturer_product_code,barcode,group_level3
                FROM warehouse_snapshot_items WHERE snapshot_id=? ORDER BY id''', (latest['id'],)):
            identity = identities.setdefault(str(item['product_code']), {})
            for key in ('manufacturer_product_code', 'barcode', 'group_level3'):
                if not identity.get(key) and item[key]:
                    identity[key] = item[key]
    for row in rows:
        identity = identities.get(str(row.get('product_code')), {})
        row['manufacturer_product_code'] = row.get('manufacturer_product_code') or identity.get('manufacturer_product_code', '')
        row['barcode'] = row.get('barcode') or identity.get('barcode', '')
        row['group_level3'] = row.get('group_level3') or identity.get('group_level3') or row.get('group_name', '')
    return rows


def initialize(settings):
    with connect(settings) as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS warehouse_purchase_contracts (
          id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL,
          seed_key TEXT UNIQUE, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS warehouse_purchase_contract_history (
          contract_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL,
          actor TEXT NOT NULL, saved_at TEXT NOT NULL,
          PRIMARY KEY(contract_id,revision));
        CREATE TABLE IF NOT EXISTS warehouse_purchase_contract_usage (
          transfer_key TEXT NOT NULL, contract_id TEXT NOT NULL, revision INTEGER NOT NULL,
          product_code TEXT NOT NULL, stock_id INTEGER, invoice_date TEXT NOT NULL,
          PRIMARY KEY(transfer_key,contract_id,product_code));
        CREATE TABLE IF NOT EXISTS warehouse_purchase_catalog (
          supplier_id INTEGER NOT NULL, product_code TEXT NOT NULL, payload TEXT NOT NULL,
          PRIMARY KEY(supplier_id,product_code));
        CREATE TABLE IF NOT EXISTS warehouse_goods_tax (
          product_code TEXT PRIMARY KEY, tax_rate REAL, tax_status TEXT NOT NULL,
          updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS warehouse_purchase_catalog_state (
          id INTEGER PRIMARY KEY CHECK(id=1), updated_at TEXT NOT NULL, row_count INTEGER NOT NULL);
        ''')


def text(value):
    if isinstance(value, bytes): value=value.decode('cp1256')
    return re.sub(r'\s+', ' ', str(value or '').replace('ي','ی').replace('ك','ک')).strip()


def digits(value):
    return str(value).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫','01234567890123456789.'))


@lru_cache(maxsize=256)
def _new_year(year):
    for day in range(19,24):
        d=date(year+621,3,day)
        if gregorian_to_jalali(d)==(year,1,1):return d
    raise ContractError('تاریخ شمسی معتبر نیست.')


def clean_date(value,optional=False):
    v=digits(value or '').strip()
    if optional and not v:return ''
    if not re.fullmatch(r'\d{4}/\d{2}/\d{2}',v):raise ContractError('تاریخ را به صورت ۱۴۰۵/۰۶/۱۷ وارد کنید.')
    y,m,d=map(int,v.split('/'))
    if not 1300<=y<=1500 or not 1<=m<=12 or not 1<=d<=31:raise ContractError('تاریخ شمسی معتبر نیست.')
    offset=(m-1)*31 if m<=7 else 186+(m-7)*30
    if gregorian_to_jalali(_new_year(y)+timedelta(days=offset+d-1))!=(y,m,d):raise ContractError('روز انتخاب‌شده در این ماه وجود ندارد.')
    return v


def number(value,label,lo=0,hi=100):
    if value is None or isinstance(value,bool) or str(value).strip()=='':raise ContractError(f'{label} را وارد کنید؛ خالی با صفر متفاوت است.')
    try:n=Decimal(digits(value))
    except (InvalidOperation,ValueError):raise ContractError(f'{label} معتبر نیست.') from None
    if not n.is_finite() or not Decimal(str(lo))<=n<=Decimal(str(hi)):raise ContractError(f'{label} باید بین {lo} و {hi} باشد.')
    return n


def normalize_catalog(rows):
    grouped={}
    for r in rows:
        code=text(r.get('GoodsCode'))
        if not code:continue
        entry=grouped.setdefault(code,{'rows':{},'tax':set(),'goods':set()})
        entry['goods'].add(r['GoodsRef'])
        root=text(r.get('TaxGroupName'))
        label=text(r.get('TaxLabel'))
        entry['tax'].add(label if root=='وضعیت مالیات' else '')
        sid=int(r.get('SupplierRef') or 0)
        entry['rows'][sid]=dict(product_code=code,product_name=text(r.get('GoodsName')),goods_id=r['GoodsRef'],
            brand_id=r.get('BrandRef'),brand=text(r.get('BrandName')),supplier_id=sid,supplier=text(r.get('SupplierName')),
            manufacturer_id=r.get('ManufacturerRef'),manufacturer=text(r.get('ManufacturerName')),
            group_id=r.get('GroupRef'),group_name=text(r.get('GroupName')))
    result=[]
    for group in grouped.values():
        labels=group['tax']; rate=None
        status='conflict' if len(labels)>1 or len(group['goods'])>1 else 'unknown'
        if len(labels)==1 and len(group['goods'])==1:
            label=next(iter(labels))
            try:rate=float(number(label,'گروه مالیات'))
            except ContractError:pass
            else:status='known'
        for row in group['rows'].values():result.append(dict(row,tax_rate=rate,tax_status=status))
    return result


def replace_catalog(settings,rows):
    if not rows or len(rows)>100000:raise ContractError('فهرست کالا و مالیات خالی یا بیش از حد مجاز است؛ اطلاعات قبلی حفظ شد.')
    keys=[(r['supplier_id'],r['product_code']) for r in rows]
    if len(keys)!=len(set(keys)):raise ContractError('کالای تکراری در فهرست تأمین‌کننده وجود دارد.')
    initialize(settings)
    now=datetime.now(timezone.utc).isoformat()
    taxes={}
    for r in rows:
        previous=taxes.get(r['product_code'])
        pair=(r['tax_rate'],r['tax_status'])
        if previous and previous!=pair:raise ContractError('مالیات یک کالا در منابع مختلف ناسازگار است.')
        taxes[r['product_code']]=pair
    with connect(settings) as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('DELETE FROM warehouse_purchase_catalog')
        c.executemany('INSERT INTO warehouse_purchase_catalog VALUES (?,?,?)',[(r['supplier_id'],r['product_code'],json.dumps(r,ensure_ascii=False)) for r in rows])
        c.execute('DELETE FROM warehouse_goods_tax')
        c.executemany('INSERT INTO warehouse_goods_tax VALUES (?,?,?,?)',[(code,*values,now) for code,values in taxes.items()])
        c.execute('INSERT OR REPLACE INTO warehouse_purchase_catalog_state VALUES (1,?,?)',(now,len(rows)))
    return {'updated_at':now,'products':len(taxes),'tax_counts':{str(rate):sum(v[0]==rate and v[1]=='known' for v in taxes.values()) for rate in sorted({v[0] for v in taxes.values() if v[0] is not None})},
            'unknown':sum(v[1]!='known' for v in taxes.values()),'varanegar_write':False}


def refresh_catalog(settings):
    try:
        with sql_connection(settings) as source:
            cur=source.cursor();cur.execute(validate_read_only_sql(CATALOG_SQL).sql)
            cols=[d[0] for d in cur.description]
            raw=cur.fetchmany(100001)
            if len(raw)>100000:raise ContractError('فهرست منبع بیش از حد مجاز است.')
            rows=normalize_catalog([dict(zip(cols,r)) for r in raw])
    except ContractError:raise
    except Exception:raise ContractError('خواندن فهرست تأمین‌کنندگان و مالیات از ورانگر انجام نشد؛ اطلاعات قبلی حفظ شد.') from None
    return replace_catalog(settings,rows)


def _contracts(c):
    return [json.loads(r['payload']) for r in c.execute('SELECT payload FROM warehouse_purchase_contracts ORDER BY updated_at DESC,id')]


def list_contracts(settings):
    initialize(settings)
    with connect(settings) as c:return _contracts(c)


def _write(c,payload,actor,seed_key=None):
    now=datetime.now(timezone.utc).isoformat()
    payload=dict(payload,seed_key=seed_key)
    encoded=json.dumps(payload,ensure_ascii=False)
    c.execute('INSERT INTO warehouse_purchase_contracts VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at',
              (payload['id'],payload['revision'],encoded,seed_key,now,now))
    c.execute('INSERT INTO warehouse_purchase_contract_history VALUES (?,?,?,?,?)',(payload['id'],payload['revision'],encoded,actor[:100],now))
    return payload


def seed_defaults(settings):
    initialize(settings)
    with connect(settings) as c:
        if grouped_structure(c):return
        c.execute('BEGIN IMMEDIATE')
        for sid,name,key in [(17,'شرکت کامان','kaman'),(15,'سیلانه سبز','silaneh')]:
            if c.execute('SELECT 1 FROM warehouse_purchase_contracts WHERE seed_key=?',(key,)).fetchone():continue
            _write(c,dict(id=str(uuid4()),revision=1,supplier_id=sid,supplier=name,scope='supplier',brand_id=None,brand='',product_code='',product_name='',
                title='قرارداد خرید '+name,start_date=jalali_business_date(),end_date='',status='draft',basis='manufacturer',includes_tax=True,
                adjustment_percent='0',discount_percent='18',tail_discount_percent='8.95',note='قاعدهٔ اولیه طبق توضیح کاربر؛ تاریخ اعتبار را بررسی و سپس فعال کنید.'),'initial_configuration',key)


def purchase_stocks():
    from app.warehouse_assistant_service import WAREHOUSES
    return [{'id':s['stock_dc_ref'],'name':s['name'],'code':code} for code,s in WAREHOUSES.items()]


def validate_stock(stock_id):
    if stock_id is not None and (type(stock_id) is not int or stock_id not in {s['id'] for s in purchase_stocks()}):
        raise ContractError('انبار قرارداد معتبر نیست؛ انبار را از فهرست انتخاب کنید.')
    return stock_id


def stock_scopes_overlap(first,second):
    return first.get('stock_id') is None or second.get('stock_id') is None or first['stock_id']==second['stock_id']


def supply_memberships(c,rows):
    """Use the same enabled manufacturer/brand scope as replenishment.

    Receipt supplier IDs disambiguate purchasing parties where available.
    An absent scope is unknown, never evidence that every warehouse is active.
    """
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_supply_scope' AND type='table'").fetchone():return False,{}
    from app.warehouse_assistant_service import _normalize_text
    stocks={s['code']:s['id'] for s in purchase_stocks()};members={}
    by_brand={}
    for item in rows:
        by_brand.setdefault((_normalize_text(item.get('manufacturer','')),_normalize_text(item.get('brand',''))),[]).append(item)
    for scope in c.execute('SELECT * FROM warehouse_supply_scope WHERE enabled=1'):
        if scope['warehouse_code'] not in stocks:continue
        refs={str(v) for v in json.loads(scope['source_supplier_refs_json'] or '[]')}
        for sid in {item['supplier_id'] for item in rows if str(item['supplier_id']) in refs}:
            members.setdefault((sid,stocks[scope['warehouse_code']]),set())
        for item in by_brand.get((_normalize_text(scope['supplier']),_normalize_text(scope['brand'])),[]):
            if refs and str(item['supplier_id']) not in refs:continue
            if not refs and _normalize_text(item['supplier'])!=_normalize_text(scope['supplier']):continue
            members.setdefault((item['supplier_id'],stocks[scope['warehouse_code']]),set()).add(item['product_code'])
    return True,members


def catalog(settings,stock_id=1):
    validate_stock(stock_id)
    initialize(settings)
    today=jalali_business_date()
    with connect(settings) as c:
        c.execute('BEGIN')
        rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id>0')]
        state=c.execute('SELECT * FROM warehouse_purchase_catalog_state WHERE id=1').fetchone()
        contracts=_contracts(c);rules=active_contracts_on(contracts,today)
        scope_known,members=supply_memberships(c,rows)
    suppliers={}
    for r in rows:
        supplier=suppliers.setdefault(r['supplier_id'],{'id':r['supplier_id'],'name':r['supplier'],'brands':{},'product_count':0,'covered_product_count':0,'uncovered_product_count':0})
        supplier['product_count']+=1
        supplier['covered_product_count' if _applicable_contract(r,rules,stock_id) else 'uncovered_product_count']+=1
        if r['brand_id'] is not None:supplier['brands'][r['brand_id']]=r['brand']
    by_supplier={sid:[r for r in rows if r['supplier_id']==sid] for sid in suppliers}
    for sid,supplier in suppliers.items():
        warehouses=[]
        for stock in purchase_stocks():
            codes=members.get((sid,stock['id']),set())
            items=[r for r in by_supplier[sid] if r['product_code'] in codes]
            covered=sum(_applicable_contract(r,rules,stock['id']) is not None for r in items)
            applicable=[r for r in contracts if r['supplier_id']==sid and not r.get('materialized') and (r.get('stock_id') is None or r['stock_id']==stock['id'])]
            warehouses.append(dict(stock,active=(sid,stock['id']) in members,product_count=len(items),covered_product_count=covered,
                uncovered_product_count=len(items)-covered,contract_count=len(applicable),active_contract_count=len(active_contracts_on(applicable,today))))
        supplier['warehouses']=warehouses
        supplier['active_warehouse_count']=sum(w['active'] for w in warehouses)
    manufacturers={r['manufacturer_id']:r.get('manufacturer','') for r in rows if r.get('manufacturer_id') is not None}
    return {'suppliers':[dict(s,brands=[{'id':bid,'name':name} for bid,name in sorted(s['brands'].items())]) for s in sorted(suppliers.values(),key=lambda x:x['name'])],
            'manufacturers':[{'id':mid,'name':name} for mid,name in sorted(manufacturers.items(),key=lambda x:x[1])],
            'updated_at':state['updated_at'] if state else None,'today':today,
            'contract_structure':'supplier_contracts','stock_id':stock_id,'stocks':purchase_stocks(),'supply_scope_known':scope_known}


def _validate(payload,c,rows=None):
    if not isinstance(payload,dict):raise ContractError('اطلاعات قرارداد معتبر نیست.')
    stock_id=validate_stock(payload.get('stock_id'))
    try:sid=int(payload.get('supplier_id',0))
    except (TypeError,ValueError):raise ContractError('تأمین‌کننده معتبر نیست.') from None
    if rows is None:rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=?',(sid,))]
    if not rows:raise ContractError('تأمین‌کننده در فهرست دریافت‌شده وجود ندارد؛ ابتدا فهرست را به‌روز کنید.')
    scope=payload.get('scope');brand_id=payload.get('brand_id');code=text(payload.get('product_code'))
    if scope not in ('supplier','brand','item','collection'):raise ContractError('دامنهٔ قرارداد معتبر نیست.')
    codes=[]
    if scope=='collection':
        codes=payload.get('product_codes')
        if not isinstance(codes,list) or not 1<=len(codes)<=10000 or any(not isinstance(v,str) or not text(v) for v in codes):
            raise ContractError('حداقل یک کالا از فهرست تأمین‌کننده انتخاب کنید.')
        codes=[text(v) for v in codes]
        if len(set(codes))!=len(codes):raise ContractError('کالای تکراری در قرارداد وجود دارد.')
        available={r['product_code']:r for r in rows}
        missing=set(codes)-available.keys()
        if missing:raise ContractError('کالا خارج از فهرست تأمین‌کننده است: '+', '.join(sorted(missing)[:10]))
        codes=sorted(codes);selected=available[codes[0]];brand_id=None;code=''
    elif scope=='brand':
        try:brand_id=int(brand_id)
        except (TypeError,ValueError):raise ContractError('برند را انتخاب کنید.') from None
        selected=next((r for r in rows if r['brand_id']==brand_id),None)
        if not selected:raise ContractError('برند متعلق به این تأمین‌کننده نیست.')
        code=''
    elif scope=='item':
        selected=next((r for r in rows if r['product_code']==code),None)
        if not selected:raise ContractError('کالا متعلق به این تأمین‌کننده نیست.')
        brand_id=None
    else:selected=rows[0];brand_id=None;code=''
    start=clean_date(payload.get('start_date'));end=clean_date(payload.get('end_date'),True)
    if end and end<start:raise ContractError('پایان اعتبار نمی‌تواند قبل از شروع باشد.')
    status=payload.get('status')
    if status not in ('draft','active'):raise ContractError('وضعیت قرارداد معتبر نیست.')
    basis=payload.get('basis')
    if basis not in ('manufacturer','consumer','announcement'):raise ContractError('مبنای قیمت معتبر نیست.')
    if type(payload.get('includes_tax')) is not bool:raise ContractError('وضعیت مالیات قیمت مبنا مشخص نیست.')
    title=text(payload.get('title'));note=text(payload.get('note'))
    agreement_reference=text(payload.get('agreement_reference'))
    source_mode=payload.get('source_mode') or 'manual'
    evidence_run_id=text(payload.get('evidence_run_id'))
    if not title or len(title)>160 or len(note)>2000:raise ContractError('عنوان لازم است؛ عنوان حداکثر ۱۶۰ و توضیحات حداکثر ۲۰۰۰ حرف باشد.')
    if len(agreement_reference)>120:raise ContractError('مرجع قرارداد حداکثر ۱۲۰ حرف باشد.')
    if source_mode not in ('manual','discovered','migrated') or len(evidence_run_id)>80:
        raise ContractError('منبع تنظیم قرارداد معتبر نیست.')
    if source_mode=='discovered' and not evidence_run_id:
        raise ContractError('شناسهٔ شواهد پیشنهاد کشف‌شده لازم است.')
    tail=tail_settings(payload)
    steps=discount_steps(payload)
    return dict(supplier_id=sid,supplier=selected['supplier'],stock_id=stock_id,scope=scope,brand_id=brand_id,brand=selected['brand'] if scope in ('brand','item') else '',
        manufacturer_id=None if scope=='collection' else selected.get('manufacturer_id'),manufacturer='' if scope=='collection' else selected.get('manufacturer',''),group_id=None if scope=='collection' else selected.get('group_id'),group_name='' if scope=='collection' else selected.get('group_name',''),
        product_code=code,product_name=selected['product_name'] if scope=='item' else '',title=title,start_date=start,end_date=end,status=status,basis=basis,
        includes_tax=payload['includes_tax'],adjustment_percent=str(number(payload.get('adjustment_percent'),'تغییر تجاری قیمت',-100,100)),
        discount_percent=steps[0]['percent'],tail_discount_percent=tail['value'] if tail['kind']=='percent' else '0',tail_discount=tail,note=note,
        agreement_reference=agreement_reference,source_mode=source_mode,evidence_run_id=evidence_run_id,
        **({'discount_steps':steps} if 'discount_steps' in payload else {}),
        **({'product_codes':codes} if scope=='collection' else {}))


def save_contract(settings,actor,payload,contract_id=None,expected_revision=None,*,member_end_dates=None):
    initialize(settings)
    with connect(settings) as c:
        c.execute('BEGIN IMMEDIATE')
        previous=None
        if contract_id:
            row=c.execute('SELECT payload FROM warehouse_purchase_contracts WHERE id=?',(contract_id,)).fetchone()
            if not row:raise ContractError('قرارداد پیدا نشد.')
            previous=json.loads(row[0])
            if expected_revision!=previous['revision']:raise ContractError('قرارداد هم‌زمان تغییر کرده است؛ دوباره بازخوانی کنید.')
            if previous['status']=='archived':raise ContractError('قرارداد بایگانی‌شده قابل ویرایش نیست؛ نسخهٔ جدید بسازید.')
            if len(previous.get('discount_steps',[]))>1 and 'discount_steps' not in payload:
                raise ContractError('این قرارداد تخفیف چندمرحله‌ای دارد؛ فرم را بازخوانی کنید تا مراحل حذف نشوند.')
            if previous.get('stock_id') is not None and 'stock_id' not in payload:
                raise ContractError('انبار قرارداد مشخص است؛ فرم را بازخوانی کنید تا دامنهٔ انبار تغییر نکند.')
        value=_validate(payload,c)
        if grouped_structure(c) and value['scope']!='collection':
            raise ContractError('ساختار قراردادها تغییر کرده است؛ صفحه را بازخوانی و قرارداد چندکالایی را ویرایش کنید.')
        if previous and previous['scope']=='collection' and value['supplier_id']!=previous['supplier_id']:
            raise ContractError('تأمین‌کنندهٔ قرارداد قابل تغییر نیست؛ قرارداد جدید بسازید.')
        if value['scope']=='collection':
            catalog_rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=?',(value['supplier_id'],))]
            known,members=supply_memberships(c,catalog_rows)
            if known:
                allowed=set().union(*(codes for (sid,stock),codes in members.items() if sid==value['supplier_id'] and (value['stock_id'] is None or stock==value['stock_id'])))
                kept=set(previous.get('product_codes',[])) if previous and previous.get('stock_id')==value['stock_id'] else set()
                if set(value['product_codes'])-allowed-kept:raise ContractError('کالاهای جدید قرارداد باید در دامنهٔ تأمین مجاز این انبار باشند؛ انبار یا انتخاب کالا را اصلاح کنید.')
        if previous and previous['scope']=='collection':
            if value['scope']!='collection' or set(previous['product_codes'])-set(value.get('product_codes',[])):
                raise ContractError('حذف سابقهٔ کالا مجاز نیست؛ در مدیریت کالاها، تاریخ پایان اعتبار کالا را ثبت کنید.')
            value['product_end_dates']=dict(previous.get('product_end_dates',{}))
            if any(end<value['start_date'] for end in value['product_end_dates'].values()):
                raise ContractError('شروع قرارداد نمی‌تواند بعد از پایان اعتبار یکی از کالاهای آن باشد.')
        if previous and value['end_date'] and value['end_date']<(previous['end_date'] or '9999/12/31'):
            from app.warehouse_purchase_membership import check_invoice_usage
            for code in previous.get('product_codes',[previous.get('product_code')]):
                if code and member_end(previous,code)>=value['end_date']:
                    check_invoice_usage(c,previous,code,value['end_date'])
        if member_end_dates is not None:
            from app.warehouse_purchase_membership import apply_end_dates
            apply_end_dates(c,value,previous,member_end_dates)
        if value['scope']=='collection':
            kept=set(previous.get('product_codes',[])) if previous and previous.get('stock_id')==value['stock_id'] else set()
            additions=set(value['product_codes'])-kept
            if additions:
                check_membership_conflicts(c,dict(value,status='active',product_codes=sorted(additions)),exclude={contract_id})
            check_membership_conflicts(c,value,exclude={contract_id})
        if value['status']=='active':
            for other in _contracts(c):
                if other['id']==contract_id or other['status']!='active' or not stock_scopes_overlap(value,other):continue
                if value['scope']=='collection':continue
                if all(other[k]==value[k] for k in ('supplier_id','scope','brand_id','product_code')):
                    if value['start_date']<=(other['end_date'] or '9999/12/31') and other['start_date']<=(value['end_date'] or '9999/12/31'):
                        raise ContractError('تاریخ این قرارداد با قرارداد فعال دیگری در همین دامنه هم‌پوشانی دارد؛ تاریخ پایان قبلی را مشخص کنید.')
        value.update(id=contract_id or str(uuid4()),revision=previous['revision']+1 if previous else 1)
        value['batch_id']=previous.get('batch_id') if previous else None
        value['deduction_group']=(previous.get('deduction_group') if previous and tail_settings(previous)==value['tail_discount'] else None) or value['id']
        if previous and previous.get('legacy_contract_ids'):value['legacy_contract_ids']=previous['legacy_contract_ids']
        return _write(c,value,actor,previous.get('seed_key') if previous else None)


def update_members(settings,actor,contract_id,revision,codes,end_dates=None):
    """Change membership only; use the normal atomic scope/conflict/revision guards."""
    initialize(settings)
    with connect(settings) as c:
        row=c.execute('SELECT payload FROM warehouse_purchase_contracts WHERE id=?',(contract_id,)).fetchone()
        if not row:raise ContractError('قرارداد پیدا نشد.')
        previous=json.loads(row[0])
    if previous['scope']!='collection':raise ContractError('ابتدا قرارداد را به ساختار چندکالایی تبدیل کنید.')
    return save_contract(settings,actor,dict(previous,product_codes=codes),contract_id,revision,member_end_dates=end_dates)


def end_contract(settings,actor,contract_id,revision,end_date):
    end_date=clean_date(end_date)
    initialize(settings)
    with connect(settings) as c:
        row=c.execute('SELECT payload FROM warehouse_purchase_contracts WHERE id=?',(contract_id,)).fetchone()
        if not row:raise ContractError('قرارداد پیدا نشد.')
        previous=json.loads(row[0])
    if previous['scope']!='collection':raise ContractError('ابتدا قرارداد را به ساختار چندکالایی تبدیل کنید.')
    return save_contract(settings,actor,dict(previous,end_date=end_date),contract_id,revision)


def archive(settings,actor,contract_id,revision,confirmed):
    if confirmed is not True:raise ContractError('بایگانی قرارداد باید تأیید شود؛ ممکن است قاعدهٔ عمومی جایگزین شود.')
    initialize(settings)
    with connect(settings) as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT payload FROM warehouse_purchase_contracts WHERE id=?',(contract_id,)).fetchone()
        if not row:raise ContractError('قرارداد پیدا نشد.')
        previous=json.loads(row[0])
        if previous['revision']!=revision:raise ContractError('نسخهٔ قرارداد تغییر کرده است؛ بازخوانی کنید.')
        if previous['status']=='archived':raise ContractError('قرارداد قبلاً بایگانی شده است.')
        return _write(c,dict(previous,status='archived',revision=revision+1),actor,previous.get('seed_key'))


def history(settings,contract_id):
    initialize(settings)
    with connect(settings) as c:
        return [dict(contract=json.loads(r['payload']),actor=r['actor'],saved_at=r['saved_at']) for r in c.execute(
            'SELECT * FROM warehouse_purchase_contract_history WHERE contract_id=? ORDER BY revision DESC',(contract_id,))]


def member_end(rule,code):
    return min(rule.get('end_date') or '9999/12/31',rule.get('product_end_dates',{}).get(code) or '9999/12/31')


def active_contracts_on(rules,on_date):
    result=[]
    for rule in rules:
        if rule['status']!='active' or rule['start_date']>on_date or (rule['end_date'] and on_date>rule['end_date']):continue
        if rule['scope']=='collection':
            codes=[code for code in rule['product_codes'] if on_date<=member_end(rule,code)]
            if not codes:continue
            rule=dict(rule,product_codes=codes)
        result.append(rule)
    return result


def _applicable_contract(item, rules, stock_id=None):
    candidates=[r for r in rules if r['supplier_id']==item['supplier_id'] and (
        r['scope']=='supplier' or (r['scope']=='brand' and r['brand_id']==item.get('brand_id'))
        or (r['scope']=='item' and r['product_code']==item['product_code'])
        or (r['scope']=='collection' and item['product_code'] in r['product_codes']))]
    if stock_id is None and any(r.get('stock_id') is not None for r in candidates):
        raise ContractError('برای تعیین قرارداد و تخفیف این کالا، انبار را انتخاب کنید.')
    candidates=[r for r in candidates if r.get('stock_id') is None or r['stock_id']==stock_id]
    if len(candidates)>1 and any(r['scope']=='collection' for r in candidates):
        raise ContractError('کالای '+item['product_code']+' در این تاریخ عضو بیش از یک قرارداد است.')
    candidates.sort(key=lambda r:{'supplier':0,'brand':1,'item':2,'collection':2}[r['scope']],reverse=True)
    return candidates[0] if candidates else None


def resolve_products(settings,supplier_id,on_date,stock_id=None,*,include_prices=True,supply_only=False):
    validate_stock(stock_id)
    on_date=clean_date(on_date);initialize(settings)
    with connect(settings) as c:
        c.execute('BEGIN')
        rows=enrich_product_identities(c,[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=? ORDER BY product_code',(supplier_id,))])
        rules=[r for r in active_contracts_on(_contracts(c),on_date) if r['supplier_id']==supplier_id]
        if supply_only:
            if stock_id is None:raise ContractError('انبار را انتخاب کنید.')
            known,members=supply_memberships(c,rows)
            if not known:raise ContractError('دامنهٔ تأمین انبارها مشخص نیست؛ ابتدا تأمین مجاز انبار را تنظیم کنید.')
            rows=[r for r in rows if r['product_code'] in members.get((supplier_id,stock_id),set())]
    for item in rows:
        item['contract']=_applicable_contract(item,rules,stock_id)
    if stock_id is not None and include_prices:
        from app.warehouse_purchase_prices import resolve_source_prices,source_price_status
        ids=[item['goods_id'] for item in rows if item['contract'] and item['contract']['basis'] in ('manufacturer','consumer')]
        prices=resolve_source_prices(settings,ids,on_date,stock_id)
        for item in rows:
            item['price_validation']=source_price_status(item['contract'],item,prices.get(item['goods_id']))
    return {'on_date':on_date,'stock_id':stock_id,'items':rows,'varanegar_write':False}


def inventory_contract_price_status(conn,rows,on_date):
    """Annotate snapshot prices at its own date; this is not live invoice validation.

    Different supplier rules are resolved independently. A missing producer price
    must not be concealed by a different supplier's consumer-price contract.
    No tables are created or updated by this helper.
    """
    from app.warehouse_purchase_prices import LABELS,positive_price
    rows=[dict(row) for row in rows]
    def key(row):return (row.get('warehouse_code',row.get('warehouse')),row['product_code'])
    result={key(row):dict(status='not_required',message='',required_bases=[],on_date=on_date) for row in rows}
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('warehouse_purchase_contracts','warehouse_purchase_catalog')")}
    if len(tables)!=2:return result
    try:on_date=clean_date(on_date)
    except ContractError:
        return {k:dict(v,status='unverified',message='تاریخ دریافت قیمت‌های اطلاعات انبار مشخص نیست؛ اطلاعات را از ورانگر دریافت کنید.') for k,v in result.items()}
    rules=active_contracts_on(_contracts(conn),on_date)
    codes={row['product_code'] for row in rows};catalog_by_code={}
    for raw in conn.execute('SELECT payload FROM warehouse_purchase_catalog'):
        item=json.loads(raw[0])
        if item['product_code'] not in codes:continue
        catalog_by_code.setdefault(item['product_code'],[]).append(item)
    stock_codes={s['code']:s['id'] for s in purchase_stocks()}
    for row in rows:
        stock_id=stock_codes.get(row.get('warehouse_code',row.get('warehouse')))
        required=set()
        try:
            for item in catalog_by_code.get(row['product_code'],[]):
                rule=_applicable_contract(item,rules,stock_id)
                if rule and rule['basis'] in LABELS:required.add(rule['basis'])
        except ContractError as exc:
            result[key(row)]=dict(status='unverified',message=str(exc),required_bases=[],on_date=on_date)
            continue
        bases=sorted(required)
        if not bases:continue
        missing=[LABELS[basis] for basis in bases if positive_price(row.get(basis+'_price')) is None]
        message=(f"کالای {text(row.get('product_name'))} ({row['product_code']}) در اطلاعات انبار به تاریخ {on_date} "
                 f"{' و '.join(missing)} معتبر ندارد.") if missing else ''
        result[key(row)]=dict(status='missing' if missing else 'ready',message=message,required_bases=bases,on_date=on_date)
    return result


def discount_steps(rule):
    """Column discounts in order, each applied to the previous remaining amount."""
    first=number(rule.get('discount_percent'),'تخفیف ستون')
    raw=rule.get('discount_steps',[{'percent':str(first)}])
    if not isinstance(raw,list) or not 1<=len(raw)<=5 or any(not isinstance(s,dict) for s in raw):
        raise ContractError('بین یک تا پنج مرحلهٔ تخفیف ستون وارد کنید.')
    steps=[{'percent':str(number(s.get('percent'),'درصد مرحلهٔ تخفیف'))} for s in raw]
    if Decimal(steps[0]['percent'])!=first:
        raise ContractError('مرحلهٔ اول تخفیف باید با تخفیف ستون یکسان باشد.')
    return steps


def calculate(rule,*,price,quantity,tax_rate):
    p=number(price,'قیمت مبنا',0,1e15);q=number(quantity,'تعداد',0,1e9)
    tax=number(tax_rate,'نرخ مالیات',0,100)
    unit=p/(1+tax/100) if rule['includes_tax'] else p
    unit=(unit*(1+number(rule['adjustment_percent'],'تغییر تجاری',-100,100)/100)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
    gross=(unit*q).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
    net=gross;stages=[]
    for step in discount_steps(rule):
        amount=(net*Decimal(step['percent'])/100).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
        stages.append(dict(percent=step['percent'],base=str(net),amount=str(amount),remaining=str(net-amount)))
        net-=amount
    discount=gross-net
    tax_amount=(net*tax/100).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
    settings=tail_settings(rule)
    base={'net_before_tax':net,'gross':gross,'after_tax':net+tax_amount,'invoice':net+tax_amount,'unit':unit}[settings['basis']]
    tail=(base*Decimal(settings['value'])/100 if settings['kind']=='percent' else Decimal(settings['value'])*(q if settings['basis']=='unit' else 1)).quantize(Decimal('1'),rounding=ROUND_HALF_UP)
    if tail>net+tax_amount:raise ContractError('تخفیف انتهایی از مبلغ قابل پرداخت بیشتر است.')
    result={k:str(v) for k,v in dict(unit_price=unit,gross=gross,discount=discount,net_before_tax=net,tax=tax_amount,tail_base=base,tail_discount=tail,total=net+tax_amount-tail).items()}
    # The purchase-invoice bridge needs every stage, including a single zero
    # stage, so SQL can independently replay and validate contract arithmetic.
    result['discount_stages']=stages
    return result


def tail_settings(rule):
    tail=rule.get('tail_discount')
    if tail is None:tail={'kind':'percent','basis':'net_before_tax','value':rule.get('tail_discount_percent')}
    if not isinstance(tail,dict):raise ContractError('تنظیم تخفیف انتهایی معتبر نیست.')
    kind=tail.get('kind');basis=tail.get('basis')
    allowed={'percent':('net_before_tax','gross','after_tax'),'fixed':('invoice','unit')}
    if kind not in allowed or basis not in allowed[kind]:raise ContractError('نوع یا مبنای تخفیف انتهایی معتبر نیست.')
    return {'kind':kind,'basis':basis,'value':str(number(tail.get('value'),'مقدار تخفیف انتهایی',0,100 if kind=='percent' else 1e15))}


def selection(settings,manufacturer_id,brand_id=None,group_id=None,supplier_id=None):
    initialize(settings)
    with connect(settings) as c:
        rows=enrich_product_identities(c,[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id>0')])
        known,members=supply_memberships(c,rows)
        if known:
            for r in rows:r['eligible_stock_ids']=[s['id'] for s in purchase_stocks() if r['product_code'] in members.get((r['supplier_id'],s['id']),set())]
    if manufacturer_id is None and supplier_id is None:raise ContractError('تأمین‌کننده یا تولیدکننده را انتخاب کنید.')
    if supplier_id is not None:rows=[r for r in rows if r['supplier_id']==supplier_id]
    manufacturers={r['manufacturer_id']:r.get('manufacturer','') for r in rows if r.get('manufacturer_id') is not None}
    if manufacturer_id is not None:rows=[r for r in rows if r.get('manufacturer_id')==manufacturer_id]
    brands={r['brand_id']:r['brand'] for r in rows if r['brand_id'] is not None}
    if brand_id is not None:rows=[r for r in rows if r['brand_id']==brand_id]
    groups={r['group_id']:r['group_name'] for r in rows if r.get('group_id') is not None}
    if group_id is not None:rows=[r for r in rows if r.get('group_id')==group_id]
    suppliers={r['supplier_id']:r['supplier'] for r in rows}
    if supplier_id is not None:rows=[r for r in rows if r['supplier_id']==supplier_id]
    products={}
    for r in rows:
        entry=products.setdefault(r['product_code'],dict(r,supplier_ids=[]))
        entry['supplier_ids'].append(r['supplier_id'])
    if len(products)>10000:raise ContractError('بیش از ده هزار کالا؛ برند یا گروه را محدود کنید.')
    return {'items':sorted(products.values(),key=lambda r:r['product_code']),
            'manufacturers':[{'id':k,'name':v} for k,v in sorted(manufacturers.items())],
            'brands':[{'id':k,'name':v} for k,v in sorted(brands.items())],
            'groups':[{'id':k,'name':v} for k,v in sorted(groups.items())],
            'suppliers':[{'id':k,'name':v} for k,v in sorted(suppliers.items())]}


def save_batch(settings,actor,payload):
    """Materialize a reviewed product selection atomically; no future membership expansion."""
    codes=payload.get('product_codes')
    if not isinstance(codes,list) or not 1<=len(codes)<=10000 or any(not isinstance(code,str) for code in codes):
        raise ContractError('حداقل یک کالا از فهرست انتخاب کنید.')
    codes=[text(code) for code in codes]
    if len(set(codes))!=len(codes):raise ContractError('کالای تکراری انتخاب شده است.')
    mid=payload.get('manufacturer_id');sid=payload.get('supplier_id')
    if type(mid) is not int or mid<=0 or type(sid) is not int or sid<=0:raise ContractError('تولیدکننده و طرف خرید را انتخاب کنید.')
    for key in ('filter_brand_id','filter_group_id'):
        if payload.get(key) is not None and (type(payload[key]) is not int or payload[key]<=0):raise ContractError('فیلتر انتخاب کالا معتبر نیست.')
    initialize(settings)
    batch_id=str(uuid4());result=[]
    with connect(settings) as c:
        c.execute('BEGIN IMMEDIATE')
        if grouped_structure(c):raise ContractError('صفحه را بازخوانی کنید؛ برای کالاها یک قرارداد مشترک ثبت می‌شود.')
        all_rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=?',(sid,))]
        eligible={r['product_code']:r for r in all_rows if r.get('manufacturer_id')==mid
            and (payload.get('filter_brand_id') is None or r['brand_id']==payload['filter_brand_id'])
            and (payload.get('filter_group_id') is None or r.get('group_id')==payload['filter_group_id'])}
        if any(code not in eligible for code in codes):raise ContractError('یک یا چند کالا خارج از تولیدکننده، برند، گروه یا طرف خرید انتخاب‌شده است؛ فهرست را بازخوانی کنید.')
        existing=_contracts(c)
        for code in codes:
            value=_validate(dict(payload,scope='item',product_code=code,brand_id=None),c,[eligible[code]])
            if value['status']=='active' and any(r['status']=='active' and stock_scopes_overlap(value,r) and r['supplier_id']==sid and r['scope']=='item' and r['product_code']==code
                and value['start_date']<=(r['end_date'] or '9999/12/31') and r['start_date']<=(value['end_date'] or '9999/12/31') for r in existing):
                raise ContractError(f'کالای {code} در این تاریخ قرارداد فعال دارد؛ هیچ‌کدام از قراردادهای جدید ذخیره نشد.')
            value.update(id=str(uuid4()),revision=1,batch_id=batch_id,deduction_group=batch_id,
                         selection={'manufacturer_id':mid,'brand_id':payload.get('filter_brand_id'),'group_id':payload.get('filter_group_id')})
            result.append(_write(c,value,actor))
    return {'contracts':result,'count':len(result),'batch_id':batch_id}


def seed_item_defaults(settings):
    """Expand only the original untouched starter drafts, preserving their history."""
    seed_defaults(settings)
    with connect(settings) as c:
        c.execute('BEGIN IMMEDIATE')
        for parent in _contracts(c):
            if parent.get('seed_key') not in ('kaman','silaneh') or parent['status']!='draft' or parent['revision']!=1:continue
            rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=?',(parent['supplier_id'],))]
            # Identity verified in this ERP: producer 17 Kaman, 15 Silaneh.
            rows=[r for r in rows if r.get('manufacturer_id')==parent['supplier_id']]
            if not rows:continue
            for row in rows:
                value=_validate(dict(parent,scope='item',product_code=row['product_code']),c,[row])
                value.update(id=str(uuid4()),revision=1,batch_id=parent['id'],deduction_group=parent['id'],initial_template=parent['seed_key'])
                _write(c,value,'initial_item_configuration')
            _write(c,dict(parent,status='archived',revision=2,materialized=True),'initial_item_configuration',parent['seed_key'])


def update_item_batch(settings,actor,payload):
    versions=payload.get('contract_versions')
    if not isinstance(versions,dict) or not 1<=len(versions)<=10000 or any(type(v) is not int or v<1 for v in versions.values()):raise ContractError('نسخهٔ قراردادهای انتخاب‌شده لازم است.')
    initialize(settings);result=[];group=str(uuid4())
    with connect(settings) as c:
        c.execute('BEGIN IMMEDIATE');existing=_contracts(c);selected=[r for r in existing if r['id'] in versions]
        if grouped_structure(c):raise ContractError('صفحه را بازخوانی و قرارداد مشترک را ویرایش کنید.')
        if len(selected)!=len(versions) or any(r['revision']!=versions[r['id']] for r in selected):raise ContractError('یکی از قراردادها هم‌زمان تغییر کرده است؛ هیچ تغییری ذخیره نشد.')
        if any(r['scope']!='item' or r['status']=='archived' for r in selected):raise ContractError('فقط قراردادهای کالای بایگانی‌نشده قابل ویرایش مشترک‌اند.')
        if any(len(r.get('discount_steps',[]))>1 for r in selected) and 'discount_steps' not in payload:
            raise ContractError('قراردادها تخفیف چندمرحله‌ای دارند؛ فرم را بازخوانی کنید تا مراحل حذف نشوند.')
        if len({(r['supplier_id'],r.get('manufacturer_id')) for r in selected})!=1:raise ContractError('تولیدکننده و طرف خرید همهٔ اقلام باید یکسان باشد.')
        keep_group=len({r.get('deduction_group') for r in selected})==1 and all(tail_settings(r)==tail_settings(payload) for r in selected)
        rows={json.loads(r[0])['product_code']:json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=?',(selected[0]['supplier_id'],))}
        for old in selected:
            if old['product_code'] not in rows:raise ContractError('یک کالا از فهرست طرف خرید خارج شده است؛ هیچ تغییری ذخیره نشد.')
            if old.get('stock_id') is not None and 'stock_id' not in payload:raise ContractError('انبار قرارداد لازم است؛ فرم را بازخوانی کنید.')
            value=_validate(dict(payload,supplier_id=old['supplier_id'],scope='item',product_code=old['product_code'],brand_id=None),c,[rows[old['product_code']]])
            if value['status']=='active' and any(r['id'] not in versions and r['status']=='active' and stock_scopes_overlap(value,r) and r['scope']=='item' and r['supplier_id']==value['supplier_id'] and r['product_code']==value['product_code'] and value['start_date']<=(r['end_date'] or '9999/12/31') and r['start_date']<=(value['end_date'] or '9999/12/31') for r in existing):raise ContractError('قرارداد فعال دیگری در این انبار با تاریخ انتخاب‌شده هم‌پوشانی دارد؛ هیچ تغییری ذخیره نشد.')
            if value['status']=='active' and any(r['product_code']==value['product_code'] and stock_scopes_overlap(value,r) for r in result):raise ContractError('برای یک کالا در همین انبار بیش از یک قرارداد انتخاب شده است.')
            value.update(id=old['id'],revision=old['revision']+1,batch_id=old.get('batch_id') or group,
                         deduction_group=old.get('deduction_group') if keep_group else group)
            result.append(value)
        for value in result:_write(c,value,actor)
    return {'count':len(result),'contracts':result}


def calculate_invoice(lines):
    """Preview only: fixed invoice deductions are applied once per shared rule group."""
    if not lines:raise ContractError('حداقل یک قلم برای محاسبه لازم است.')
    results=[];groups={}
    for index,line in enumerate(lines):
        rule=line['rule'];tail=tail_settings(rule)
        fixed_invoice=tail['kind']=='fixed' and tail['basis']=='invoice'
        effective=dict(rule,tail_discount={'kind':'percent','basis':'net_before_tax','value':'0'}) if fixed_invoice else rule
        result=calculate(effective,price=line['price'],quantity=line['quantity'],tax_rate=line['tax_rate'])
        results.append(result)
        if fixed_invoice:
            key=rule.get('deduction_group') or rule.get('id')
            if not key:raise ContractError('شناسهٔ گروه تخفیف مبلغی لازم است.')
            group=groups.setdefault(key,{'amount':Decimal(tail['value']),'rows':[]})
            if group['amount']!=Decimal(tail['value']):raise ContractError('مبلغ تخفیف مشترک اقلام ناسازگار است.')
            group['rows'].append(index)
    for group in groups.values():
        total=sum(Decimal(results[i]['total']) for i in group['rows']);amount=group['amount'].quantize(Decimal('1'),rounding=ROUND_HALF_UP)
        if amount>total:raise ContractError('تخفیف مبلغی از جمع اقلام مربوط بیشتر است.')
        # Largest remainder allocates each rial exactly once, including mixed VAT.
        raw=[amount*Decimal(results[i]['total'])/total if total else Decimal(0) for i in group['rows']]
        allocated=[int(n) for n in raw];remainder=int(amount)-sum(allocated)
        for j in sorted(range(len(raw)),key=lambda j:raw[j]-allocated[j],reverse=True)[:remainder]:allocated[j]+=1
        for i,value in zip(group['rows'],allocated):
            results[i]['tail_discount']=str(value);results[i]['total']=str(Decimal(results[i]['total'])-value)
    return {'items':results,'total':str(sum(Decimal(r['total']) for r in results)), 'preview_only':True}


def inventory_tax_map(conn):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_goods_tax'").fetchone():return {}
    return {r['product_code']:dict(r) for r in conn.execute('SELECT * FROM warehouse_goods_tax')}


def grouped_structure(c):
    return bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_purchase_structure'").fetchone())


def member_codes(rule, rows):
    if rule['scope']=='collection':return set(rule['product_codes'])
    if rule['scope']=='item':return {rule['product_code']}
    return {r['product_code'] for r in rows if r['supplier_id']==rule['supplier_id']
            and (rule['scope']=='supplier' or r['brand_id']==rule['brand_id'])}


def check_membership_conflicts(c, value, exclude=None, rules=None):
    if value['status']!='active':return
    rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=?',(value['supplier_id'],))]
    codes=member_codes(value,rows)
    for other in (_contracts(c) if rules is None else rules):
        if other['id'] in (exclude or set()) or other['status']!='active' or other['supplier_id']!=value['supplier_id']:continue
        if not stock_scopes_overlap(value,other):continue
        if value['start_date']>(other['end_date'] or '9999/12/31') or other['start_date']>(value['end_date'] or '9999/12/31'):continue
        overlap={code for code in codes & member_codes(other,rows) if value['start_date']<=member_end(other,code) and other['start_date']<=member_end(value,code)}
        if overlap:
            raise ContractError('کالاهای '+', '.join(sorted(overlap)[:12])+' در این انبار و بازهٔ انتخابی عضو قرارداد «'+other['title']+'» هستند؛ انبار، تاریخ یا کالاهای قرارداد را اصلاح کنید.')


def migrate_supplier_contracts(settings, actor='supplier_contract_structure'):
    """Explicit, atomic migration. Retain all old rows/history and pricing groups.

    Called by the migration tool, never implicitly by a read/list endpoint.
    Contracts with different economic terms or deduction groups stay separate.
    """
    initialize(settings)
    with connect(settings) as c:
        c.execute('BEGIN IMMEDIATE')
        if grouped_structure(c):return {'migrated_rules':0,'contracts':[]}
        existing=_contracts(c)
        legacy=[r for r in existing if r['scope']!='collection' and not r.get('materialized')]
        catalog_rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM warehouse_purchase_catalog')]
        fields=('supplier_id','stock_id','batch_id','deduction_group','title','start_date','end_date','status','basis',
                'includes_tax','adjustment_percent','agreement_reference','source_mode','evidence_run_id','note')
        groups={}
        for r in legacy:
            signature={k:r.get(k) for k in fields}
            signature.update(discount_steps=discount_steps(r),tail_discount=tail_settings(r))
            # Missing deduction group historically means an independent per-rule deduction.
            if tail_settings(r)['kind']=='fixed' and not r.get('deduction_group'):signature['deduction_group']=r['id']
            groups.setdefault(json.dumps(signature,sort_keys=True,ensure_ascii=False),[]).append(r)
        planned=[]
        for members in groups.values():
            first=members[0];codes=sorted(set().union(*(member_codes(r,catalog_rows) for r in members)))
            if not codes:
                if first['status']=='archived':continue
                raise ContractError('قرارداد «'+first['title']+'» کالای قابل انتقال ندارد.')
            if first['status']=='active' and sum(len(member_codes(r,catalog_rows)) for r in members)!=len(codes):
                raise ContractError('عضویت تکراری در قراردادهای قبلی؛ انتقال انجام نشد.')
            parent=dict(first,id=str(uuid4()),revision=1,scope='collection',product_codes=codes,
                        product_code='',product_name='',brand_id=None,brand='',manufacturer_id=None,
                        manufacturer='',group_id=None,group_name='',batch_id=None,seed_key=None,
                        legacy_contract_ids=[r['id'] for r in members])
            parent['deduction_group']=first.get('deduction_group') or first['id']
            planned.append(parent)
        all_parents=[r for r in existing if r['scope']=='collection']+planned
        for parent in planned:check_membership_conflicts(c,parent,exclude={parent['id']},rules=all_parents)
        for parent in planned:
            _write(c,parent,actor)
            for old in legacy:
                if old['id'] in parent['legacy_contract_ids']:
                    _write(c,dict(old,status='archived',revision=old['revision']+1,
                                 materialized=True,replaced_by=parent['id']),actor,old.get('seed_key'))
        c.execute('CREATE TABLE warehouse_purchase_structure (version INTEGER PRIMARY KEY, migrated_at TEXT NOT NULL)')
        c.execute('INSERT INTO warehouse_purchase_structure VALUES (1,?)',(datetime.now(timezone.utc).isoformat(),))
        return {'migrated_rules':sum(len(r['legacy_contract_ids']) for r in planned),
                'contracts':[{'id':r['id'],'supplier':r['supplier'],'title':r['title'],'count':len(r['product_codes'])} for r in planned]}
