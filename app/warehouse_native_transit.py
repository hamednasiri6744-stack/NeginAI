"""Read-only native 65 -> 15 pipeline, published atomically with warehouse stock.

Do not query vwInventoryOnWay directly: it uses NOLOCK and removes a whole
credit when any receipt exists, even when that receipt is unconfirmed/partial.
Internal overlays hand over only in the SAME published inventory snapshot.
"""
import hashlib
import math


def init_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_native_transit_snapshots(
        snapshot_id INTEGER PRIMARY KEY REFERENCES warehouse_snapshots(id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_native_transit(
        snapshot_id INTEGER NOT NULL, voucher_id INTEGER NOT NULL, product_code TEXT NOT NULL,
        transfer_key TEXT NOT NULL, voucher_no INTEGER NOT NULL, source TEXT NOT NULL,
        destination TEXT NOT NULL, quantity REAL NOT NULL, received REAL NOT NULL,
        pending_receipt REAL NOT NULL, confirmed INTEGER NOT NULL, review INTEGER NOT NULL,
        PRIMARY KEY(snapshot_id,voucher_id,product_code))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_native_transit_handover(
        snapshot_id INTEGER NOT NULL,document_id INTEGER NOT NULL,fingerprint TEXT NOT NULL,
        PRIMARY KEY(snapshot_id,document_id))''')


def source_queries(cursor, year):
    from app.warehouse_receipt_reflection import _rows
    from app.warehouse_assistant_service import WAREHOUSES
    refs=','.join(str(int(w['stock_dc_ref'])) for w in WAREHOUSES.values())
    # Stock and these base tables are read under the caller's single SNAPSHOT.
    return _rows(cursor,f'''WITH native_transfer_credits AS (
        SELECT H.ID voucher_id,H.UniqueId transfer_key,H.VocherNo voucher_no,
          H.StockDCRef source_ref,H.TStockDCRef destination_ref,H.AccYear,
          I.GoodsRef,G.GoodsCode product_code,SUM(I.TotalQty) quantity,
          CASE WHEN H.ConfirmedBy IS NOT NULL AND NULLIF(LTRIM(RTRIM(H.ConfirmDate)),'') IS NOT NULL THEN 1 ELSE 0 END confirmed
        FROM inv.tblVocherHdr H JOIN inv.tblVocherItm I ON I.HdrRef=H.ID
        JOIN gnr.tblGoods G ON G.ID=I.GoodsRef
        WHERE H.VocherTypeCode=65 AND H.HealthCode=1 AND H.AccYear={int(year)}
          AND (H.StockDCRef IN({refs}) OR H.TStockDCRef IN({refs}))
        GROUP BY H.ID,H.UniqueId,H.VocherNo,H.StockDCRef,H.TStockDCRef,H.AccYear,
          I.GoodsRef,G.GoodsCode,H.ConfirmedBy,H.ConfirmDate
    ), native_transfer_receipts AS (
        SELECT C.voucher_id,C.GoodsRef,
          SUM(CASE WHEN R.ConfirmedBy IS NOT NULL AND NULLIF(LTRIM(RTRIM(R.ConfirmDate)),'') IS NOT NULL THEN I.TotalQty ELSE 0 END) received,
          SUM(CASE WHEN R.ConfirmedBy IS NULL OR NULLIF(LTRIM(RTRIM(R.ConfirmDate)),'') IS NULL THEN I.TotalQty ELSE 0 END) pending_receipt
        FROM native_transfer_credits C JOIN inv.tblVocherHdr R ON R.DocRef=C.voucher_id
          AND R.VocherTypeCode=15 AND R.HealthCode=1 AND R.AccYear=C.AccYear
          AND R.StockDCRef=C.destination_ref
        JOIN inv.tblVocherItm I ON I.HdrRef=R.ID AND I.GoodsRef=C.GoodsRef
        GROUP BY C.voucher_id,C.GoodsRef
    ) SELECT C.voucher_id,C.transfer_key,C.voucher_no,C.source_ref,C.destination_ref,
        C.product_code,C.quantity,C.confirmed,ISNULL(R.received,0) received,
        ISNULL(R.pending_receipt,0) pending_receipt
      FROM native_transfer_credits C LEFT JOIN native_transfer_receipts R
        ON R.voucher_id=C.voucher_id AND R.GoodsRef=C.GoodsRef
      ORDER BY C.voucher_id,C.product_code''')


def fingerprint(row):
    return hashlib.sha256((str(row['transfer_key'])+'\n'+row['payload_json']).encode()).hexdigest()


def apply(conn, rows, captured, snapshot_id):
    """Caller owns the inventory transaction; validate completely before replacing."""
    from app.warehouse_assistant_service import WAREHOUSES,WarehouseAssistantError
    refs={int(v['stock_dc_ref']):k for k,v in WAREHOUSES.items()}
    normalized=[];keys=set();identities=set()
    for r in rows:
        try:
            amounts=[float(r[k]) for k in ('quantity','received','pending_receipt')]
            if any(not math.isfinite(v) or v<0 for v in amounts):raise ValueError()
            if r['confirmed'] not in (0,1):raise ValueError()
            ident=int(r['voucher_id']);code=str(r['product_code']).strip()
            if not code or ident<=0 or (ident,code) in identities:raise ValueError()
            identities.add((ident,code))
            source=refs.get(int(r['source_ref']),str(int(r['source_ref'])))
            destination=refs.get(int(r['destination_ref']),str(int(r['destination_ref'])))
            if source==destination:raise ValueError()
            key=str(r['transfer_key'] or '').lower();keys.add(key)
            quantity,received,pending=amounts
            review=received>quantity or (not r['confirmed'] and received>0)
            if not review and (not r['confirmed'] or quantity<=received):
                continue  # Completed/native-inactive lines need no inbound overlay.
            normalized.append((snapshot_id,ident,code,key,int(r['voucher_no']),source,destination,
                               quantity,received,pending,int(r['confirmed']),int(review)))
        except (ValueError,TypeError,KeyError,OverflowError) as exc:
            raise WarehouseAssistantError('اطلاعات در راه ورانگر معتبر نیست؛ موجودی قبلی حفظ شد.') from exc
    init_schema(conn)
    # A successful historic write that is now missing/unconfirmed is ERP-owned,
    # not a new internal reservation. Pending writes hand over only if SQL saw them.
    handovers=[(snapshot_id,r['document_id'],fingerprint(r)) for r in captured
               if r['status']=='sent' or str(r['transfer_key']).lower() in keys]
    conn.execute('DELETE FROM warehouse_native_transit WHERE snapshot_id=?',(snapshot_id,))
    conn.execute('DELETE FROM warehouse_native_transit_handover WHERE snapshot_id=?',(snapshot_id,))
    conn.executemany('INSERT INTO warehouse_native_transit VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',normalized)
    conn.executemany('INSERT INTO warehouse_native_transit_handover VALUES(?,?,?)',handovers)
    conn.execute('INSERT OR IGNORE INTO warehouse_native_transit_snapshots VALUES(?)',(snapshot_id,))


def current_snapshot(conn):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_native_transit_snapshots'").fetchone():return None
    row=conn.execute('''SELECT n.snapshot_id FROM warehouse_native_transit_snapshots n
        JOIN warehouse_snapshots s ON s.id=n.snapshot_id
        WHERE n.snapshot_id=(SELECT MAX(id) FROM warehouse_snapshots) AND s.source_kind='varanegar' ''').fetchone()
    return row[0] if row else None


def handed_requests(conn):
    snapshot=current_snapshot(conn)
    if snapshot is None:return set()
    rows=conn.execute('''SELECT l.request_id,t.transfer_key,t.payload_json,h.fingerprint
        FROM warehouse_native_transit_handover h
        JOIN warehouse_transfer_bridge_intents t ON t.document_id=h.document_id
        JOIN warehouse_transfer_document_lines l ON l.document_id=t.document_id
        WHERE h.snapshot_id=? AND t.status<>'rejected' ''',(snapshot,))
    return {r['request_id'] for r in rows if fingerprint(r)==r['fingerprint']}


def position(conn, warehouse):
    snapshot=current_snapshot(conn)
    if snapshot is None:return {},set(),[]
    rows=[dict(r) for r in conn.execute('''SELECT * FROM warehouse_native_transit
        WHERE snapshot_id=? AND (source=? OR destination=?) ORDER BY voucher_id,product_code''',
        (snapshot,warehouse,warehouse))]
    quantities={};review=set()
    for r in rows:
        if r['review']:review.add(r['product_code'])
        if r['destination']==warehouse and r['confirmed']:
            remaining=max(0,r['quantity']-r['received'])
            if remaining:quantities[r['product_code']]=quantities.get(r['product_code'],0)+remaining
    return quantities,review,rows


def refresh_after_post(settings, username, result):
    """A committed credit stays committed even if its read-only refresh fails."""
    if result.get('status')!='sent' or not getattr(settings,'sql_configured',False):return result
    from app.warehouse_assistant_service import sync_varanegar_snapshot,latest_snapshot
    try:
        previous=latest_snapshot(settings)
        days=int((previous or {}).get('period_days') or 60)
        snapshot=sync_varanegar_snapshot(settings,username,period_days=max(7,min(365,days)))
        return dict(result,inventory_sync='synced',inventory_snapshot_id=snapshot['id'])
    except Exception:
        # No connection details and no new ERP request. Old coherent stock remains.
        return dict(result,inventory_sync='refresh_required',
                    inventory_message='سند ثبت شد؛ بازخوانی موجودی و در راه ورانگر کامل نشد. مبنای قبلی تا بازخوانی موفق حفظ می‌شود؛ سند را دوباره ثبت نکنید.')
