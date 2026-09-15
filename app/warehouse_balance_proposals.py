"""Inventory-first balancing; proposals are read-only, acceptance is atomic.

Only editable purchase drafts may be reduced. Supplier commitments stay intact.
Transfers reserve source stock and enter the existing destination supply pipeline;
neither warehouse snapshot nor ERP is modified.
"""
import hashlib
import json
import math
from app import warehouse_rebalancing as ledger

MINIMUM_SOURCE_DAYS = 20
CENTRAL_RETAINED_DAYS = 30
GILAN_MINIMUM_DAYS = 20
WAREHOUSES = frozenset(('tehran', 'karaj', 'gilan'))


def _destination(source, destination):
    # Source-only callers retain the original Tehran/Karaj contract.
    if destination is None:
        destination = ledger.PAIRS.get(source)
    if source not in WAREHOUSES or destination not in WAREHOUSES or source == destination:
        ledger._fail('مسیر جابه‌جایی معتبر نیست؛ مبدأ و مقصد متفاوت را انتخاب کنید.')
    return destination


def _drafts(conn, warehouse, username, include_all):
    result=[]
    for kind,table in [('automatic_preorder','warehouse_automatic_preorders'),('supplier_order','supplier_orders')]:
        for row in conn.execute(f"SELECT * FROM {table} WHERE warehouse_code=? AND status IN ('prepared','awaiting_approval') ORDER BY id",(warehouse,)):
            if kind=='automatic_preorder' and row['source_supplier_order_id'] is not None:
                continue
            if kind=='supplier_order' and not include_all and row['created_by']!=username:
                continue
            order=ledger._order(conn,kind,row['id'],username,include_all)
            if order['can_edit']:
                result.append((kind,order))
    return result


def _preview(conn, username, source, include_all, destination=None):
    from app.warehouse_assistant_service import LAST_STOCK_DEMAND_BASIS, ORDER_CYCLE_BLOCKED_SQL, ORDER_CYCLE_FORCED_SQL
    from app.warehouse_fulfillment import supply_position
    from app.warehouse_order_receipts import pending_stock
    destination=_destination(source, destination)
    to_gilan=destination=='gilan'
    scope=tuple(sorted(WAREHOUSES)) if to_gilan else (source,destination)
    minimum_source_days=CENTRAL_RETAINED_DAYS if to_gilan else MINIMUM_SOURCE_DAYS
    shortage_days=GILAN_MINIMUM_DAYS if to_gilan else 15
    snapshot=conn.execute('SELECT * FROM warehouse_snapshots ORDER BY id DESC LIMIT 1').fetchone()
    if snapshot is None:
        ledger._fail('ابتدا اطلاعات موجودی انبار را دریافت کنید.')
    rows=[dict(r) for r in conn.execute(f'''SELECT *, CASE WHEN {ORDER_CYCLE_BLOCKED_SQL} THEN 1 ELSE 0 END AS blocked,
        CASE WHEN {ORDER_CYCLE_FORCED_SQL} THEN 1 ELSE 0 END AS forced
        FROM warehouse_snapshot_items WHERE snapshot_id=? AND warehouse_code IN ({','.join('?' for _ in scope)}) ORDER BY warehouse_code,product_code''',
        (snapshot['id'],*scope))]
    inventory={(r['warehouse_code'],r['product_code']):r for r in rows}
    outgoing={w:ledger.reservations(conn,w)[1] for w in scope}
    supplies={w:supply_position(conn,w) for w in scope}
    receipts={w:pending_stock(conn,w) for w in scope}
    review=set().union(*(receipts[w][1] for w in scope))
    adjusted=snapshot['demand_basis'] in ('net_sales_stockout_adjusted',LAST_STOCK_DEMAND_BASIS)
    lines=[]
    for donor in rows:
        code=donor['product_code'];receiver=inventory.get((destination,code))
        if donor['warehouse_code']!=source or not receiver or code in review:
            continue
        if any(r['blocked'] or (snapshot['demand_basis']==LAST_STOCK_DEMAND_BASIS and not r['ordering_cycle_active'] and not r['forced']) for r in (donor,receiver)):
            continue
        rate=float(donor['conversion_rate'] or 0)
        source_price=float(donor['consumer_price'] or 0);destination_price=float(receiver['consumer_price'] or 0)
        if rate<=0 or rate!=float(receiver['conversion_rate'] or 0) or min(source_price,destination_price)<=0 or source_price<destination_price:
            continue
        def daily(row):
            days=int(row['sales_rate_days'] or 0) if adjusted else int(snapshot['period_days'] or 60)
            return max(0,float(row['period_out'] or 0))/days if days>0 else 0
        sd,dd=daily(donor),daily(receiver)
        # Unknown/zero demand cannot establish comparable coverage; do not guess.
        if sd<=0 or dd<=0:
            continue
        def free(row):
            return float(row['stock'])+max(0,float(row['reserved'] or 0))-max(0,float(row['open_order'] or 0))-outgoing[row['warehouse_code']].get(code,0)
        physical=free(donor)
        sf=physical+supplies[source][0].get(code,0)+receipts[source][0].get(code,0)
        df=free(receiver)+supplies[destination][0].get(code,0)+receipts[destination][0].get(code,0)
        if sf/sd<=45 or df/dd>=shortage_days:
            continue
        minimum_cartons=1;other_central_days=None
        if to_gilan:
            # Distant shipment waits until BOTH central warehouses have thirty
            # days. The other warehouse's confirmed inbound counts, not drafts.
            other=inventory.get((ledger.PAIRS[source],code))
            if not other or daily(other)<=0:
                continue
            other_central_days=(free(other)+supplies[other['warehouse_code']][0].get(code,0)+receipts[other['warehouse_code']][0].get(code,0))/daily(other)
            if other_central_days<CENTRAL_RETAINED_DAYS:
                continue
            minimum_cartons=max(1,math.ceil((dd*GILAN_MINIMUM_DAYS-df)/rate))
            if (df+minimum_cartons*rate)/dd<GILAN_MINIMUM_DAYS:
                minimum_cartons+=1
        ideal=(sf*dd-df*sd)/(sd+dd)
        # Nearest full carton minimizes the coverage gap. Never reserve stock that
        # is only inbound: the planning basis includes it, physical availability does not.
        # Retain the route's floor on the same purchasing inventory basis, even when
        # equal coverage would require sending more. Never round this ceiling up.
        retained_cap=math.floor((sf-sd*minimum_source_days)/rate)
        maximum=max(0,min(math.floor((physical+1e-9)/rate),math.floor(ideal/rate+0.5),retained_cap))
        if maximum>0 and (sf-maximum*rate)/sd<minimum_source_days:
            maximum-=1  # Conservative protection against floating-point edge cases.
        if maximum<minimum_cartons:
            continue
        quantity=maximum*rate
        lines.append(dict(product_code=code,product_name=receiver['product_name'],manufacturer=receiver['manufacturer'],brand=receiver['brand'],conversion_rate=rate,
            available_cartons=maximum,minimum_cartons=minimum_cartons,other_central_days=other_central_days,quantity=quantity,source_before_days=sf/sd,destination_before_days=df/dd,
            source_after_days=(sf-quantity)/sd,destination_after_days=(df+quantity)/dd,
            source_daily_demand=sd,destination_daily_demand=dd,source_available=physical,source_position=sf,destination_position=df,
            source_consumer_price=source_price,destination_consumer_price=destination_price))
    drafts=_drafts(conn,destination,username,include_all)
    policy=dict(minimum_source_days=minimum_source_days,shortage_days=shortage_days,
                central_retained_days=CENTRAL_RETAINED_DAYS,gilan_minimum_days=GILAN_MINIMUM_DAYS,gilan_priority_version=1)
    evidence=[policy,source,destination,dict(snapshot),rows,supplies,{w:[v[0],sorted(v[1])] for w,v in receipts.items()},outgoing,
              [(kind,o['id'],o['email_send_token']) for kind,o in drafts]]
    token=hashlib.sha256(json.dumps(evidence,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return dict(source=source,destination=destination,snapshot_id=snapshot['id'],trigger_days=45,
                **policy,lines=lines,expected_token=token),drafts


def preview(settings,username,source,*,destination=None,include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store, warehouse_connection
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN')
        return _preview(conn,username,source,include_all,destination)[0]


def _reduce_draft(conn,kind,order,budget,rates,username,now):
    manual=kind=='supplier_order';ident=order['id']
    table,parent=('supplier_order_lines','order_id') if manual else ('warehouse_automatic_preorder_lines','preorder_id')
    units=value=cartons=items=0;changes=[]
    for line in order['lines']:
        code=line['product_code'];rate=float(line['conversion_rate'])
        count=min(int(line['cartons']),math.floor((budget.get(code,0)+1e-9)/rate)) if rate>0 and rates.get(code)==rate else 0
        remaining=line['cartons']-count
        if count:
            amount=count*rate;budget[code]-=amount
            changes.append(dict(product_code=code,quantity=amount,previous_cartons=line['cartons'],remaining_cartons=remaining))
            if not remaining:
                conn.execute(f'DELETE FROM {table} WHERE {parent}=? AND product_code=?',(ident,code))
            else:
                quantity=remaining*rate
                conn.execute(f'UPDATE {table} SET cartons=?,order_quantity=?,estimated_value=?'+(',requested_quantity=?' if manual else '')+f' WHERE {parent}=? AND product_code=?',
                    (remaining,quantity,quantity*line['buy_price'],*((quantity,) if manual else ()),ident,code))
        if remaining:
            items+=1;cartons+=remaining;units+=remaining*rate;value+=remaining*rate*line['buy_price']
    if not changes:
        return None
    if manual:
        conn.execute('UPDATE supplier_orders SET total_quantity=?,estimated_value=?,edited_by=?,edited_at=?,status=? WHERE id=?',
            (units,value,username,now,'prepared' if items else 'cancelled',ident))
        if not items:
            conn.execute('INSERT OR IGNORE INTO supplier_order_deletions VALUES(?,?,?)',(ident,username,now))
    else:
        conn.execute('UPDATE warehouse_automatic_preorders SET total_quantity=?,estimated_value=?,total_cartons=?,item_count=?,edited_by=?,edited_at=?,status=? WHERE id=?',
            (units,value,cartons,items,username,now,'awaiting_approval' if items else 'cancelled',ident))
        if not items:
            conn.execute("UPDATE warehouse_automatic_preorders SET generation_key='balance:'||id||':'||generation_key WHERE id=?",(ident,))
    return dict(document_kind=kind,document_id=ident,lines=changes)


def accept(settings,username,source,lines,*,expected_token,request_id,destination=None,include_all=False):
    from app.warehouse_assistant_service import init_warehouse_store,warehouse_connection,_now
    if not isinstance(request_id,str) or not 1<=len(request_id)<=100 or not lines or len(lines)>500:
        ledger._fail('شناسه درخواست و اقلام معتبر لازم است.')
    selected={}
    for line in lines:
        code=str(line.get('product_code','')).strip();count=line.get('cartons')
        if not code or code in selected or type(count) is not int or not 1<=count<=1000000:
            ledger._fail('مقدار جابه‌جایی باید کارتن کامل و مثبت باشد.')
        selected[code]=count
    destination=_destination(source,destination)
    digest=hashlib.sha256(json.dumps([username,'balance',source,destination,selected,expected_token],sort_keys=True).encode()).hexdigest()
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        old=conn.execute('SELECT * FROM warehouse_rebalance_batches WHERE request_id=?',(request_id,)).fetchone()
        if old:
            if old['request_hash']!=digest:
                ledger._fail('شناسه درخواست قبلاً استفاده شده است؛ بازخوانی کنید.')
            return json.loads(old['result_json'])
        data,drafts=_preview(conn,username,source,include_all,destination)
        if data['expected_token']!=expected_token:
            ledger._fail('موجودی، سفارش یا قیمت تغییر کرده است؛ پیشنهادها را بازخوانی کنید.')
        offers={r['product_code']:r for r in data['lines']}
        if any(c not in offers or n>offers[c]['available_cartons'] for c,n in selected.items()):
            ledger._fail('مقدار بیشتر از پیشنهاد مجاز است؛ بازخوانی کنید.')
        if any(n<offers[c]['minimum_cartons'] for c,n in selected.items()):
            ledger._fail('مقدار انتخابی گیلان را به حداقل ۲۰ روز نمی‌رساند؛ حداقل کارتن مجاز را انتخاب کنید.')
        now=_now()
        batch=conn.execute('INSERT INTO warehouse_rebalance_batches(request_id,request_hash,document_kind,document_id,created_by,created_at) VALUES(?,?,?,?,?,?)',
            (request_id,digest,'balance',0,username,now)).lastrowid
        budget={};rates={}
        for code,count in selected.items():
            o=offers[code];rate=o['conversion_rate'];quantity=count*rate;budget[code]=quantity;rates[code]=rate
            ident=conn.execute('''INSERT INTO warehouse_rebalance_requests(batch_id,source,destination,product_code,product_name,cartons,conversion_rate,quantity,
                source_consumer_price,destination_consumer_price,daily_demand,retained_quantity,snapshot_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (batch,source,data['destination'],code,o['product_name'],count,rate,quantity,o['source_consumer_price'],o['destination_consumer_price'],
                 o['source_daily_demand'],o['source_available']-quantity,data['snapshot_id'])).lastrowid
            context=dict(o,cartons=count,quantity=quantity,
                         source_after_days=(o['source_position']-quantity)/o['source_daily_demand'],
                         destination_after_days=(o['destination_position']+quantity)/o['destination_daily_demand'])
            conn.execute('INSERT INTO warehouse_rebalance_approval_context VALUES(?,?)',
                         (ident,json.dumps(context,ensure_ascii=False,allow_nan=False)))
        changes=[]
        for kind,order in drafts:
            change=_reduce_draft(conn,kind,order,budget,rates,username,now)
            if change:changes.append(change)
        result=dict(batch_id=batch,source=source,destination=data['destination'],draft_changes=changes,
            reduced_purchase_quantity=sum(l['quantity'] for o in changes for l in o['lines']),external_transfer_performed=False)
        conn.execute('UPDATE warehouse_rebalance_batches SET result_json=? WHERE id=?',(json.dumps(result,ensure_ascii=False),batch))
        return result
