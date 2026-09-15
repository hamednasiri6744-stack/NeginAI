"""Shared cartables with account-specific (supplier, warehouse) grants."""
import json
from app.warehouse_assistant_service import WarehouseAssistantError, warehouse_connection, _now


def init_schema(conn):
    for sql in (
        '''CREATE TABLE IF NOT EXISTS warehouse_portal_cartables (
            id INTEGER PRIMARY KEY,name TEXT NOT NULL,created_by TEXT NOT NULL,created_at TEXT NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS warehouse_portal_cartable_suppliers (
            supplier_key TEXT PRIMARY KEY,supplier_name TEXT NOT NULL,cartable_id INTEGER NOT NULL
            REFERENCES warehouse_portal_cartables(id))''',
        '''CREATE TABLE IF NOT EXISTS warehouse_portal_account_access (
            account_id INTEGER PRIMARY KEY REFERENCES warehouse_supplier_portal_accounts(id),
            cartable_id INTEGER NOT NULL REFERENCES warehouse_portal_cartables(id),
            all_orders INTEGER NOT NULL CHECK(all_orders IN (0,1)),revision INTEGER NOT NULL)''',
        '''CREATE TABLE IF NOT EXISTS warehouse_portal_account_scopes (
            account_id INTEGER NOT NULL REFERENCES warehouse_supplier_portal_accounts(id),
            supplier_key TEXT NOT NULL,warehouse_code TEXT NOT NULL,
            PRIMARY KEY(account_id,supplier_key,warehouse_code))''',
        '''CREATE TABLE IF NOT EXISTS warehouse_portal_access_events (
            id INTEGER PRIMARY KEY,actor TEXT NOT NULL,event TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL)''',
    ):
        conn.execute(sql)


def account_access(conn, account_id):
    row=conn.execute('''SELECT a.*,c.name AS cartable_name FROM warehouse_portal_account_access a
        JOIN warehouse_portal_cartables c ON c.id=a.cartable_id WHERE account_id=?''',(account_id,)).fetchone()
    if not row:
        return None
    result=dict(row)
    result['all_orders']=bool(result['all_orders'])
    result['scopes']=[dict(r) for r in conn.execute('''SELECT s.supplier_key,c.supplier_name,s.warehouse_code
        FROM warehouse_portal_account_scopes s JOIN warehouse_portal_cartable_suppliers c ON c.supplier_key=s.supplier_key
        WHERE s.account_id=? AND c.cartable_id=? ORDER BY c.supplier_name,s.warehouse_code''',(account_id,result['cartable_id']))]
    return result


def can_access(conn, account_id, supplier_key, warehouse_code):
    account=conn.execute('SELECT supplier_key,active FROM warehouse_supplier_portal_accounts WHERE id=?',(account_id,)).fetchone()
    if not account or not account['active']:
        return False
    access=conn.execute('SELECT * FROM warehouse_portal_account_access WHERE account_id=?',(account_id,)).fetchone()
    if not access:
        # Existing single-supplier accounts keep their original permission, never
        # inherit other suppliers merely because a new shared cartable exists.
        return account['supplier_key']==supplier_key
    member=conn.execute('SELECT 1 FROM warehouse_portal_cartable_suppliers WHERE cartable_id=? AND supplier_key=?',
                        (access['cartable_id'],supplier_key)).fetchone()
    if not member:
        return False
    if access['all_orders']:
        return True
    return bool(conn.execute("SELECT 1 FROM warehouse_portal_account_scopes WHERE account_id=? AND supplier_key=? AND warehouse_code IN (?, '*')",
                             (account_id,supplier_key,warehouse_code)).fetchone())


def assignment_warehouse(conn, assignment):
    table='supplier_orders' if assignment['document_kind']=='supplier_order' else 'warehouse_automatic_preorders'
    row=conn.execute(f'SELECT warehouse_code FROM {table} WHERE id=?',(assignment['document_id'],)).fetchone()
    return row['warehouse_code'] if row else None


def require_assignment(conn, account_id, assignment):
    warehouse=assignment_warehouse(conn,assignment) if assignment else None
    if not warehouse or not can_access(conn,account_id,assignment['supplier_key'],warehouse):
        raise WarehouseAssistantError('این سفارش در محدودهٔ دسترسی شما نیست.')


def default_login(conn,supplier_key,warehouse_code):
    # The current warehouse contact wins over a group-wide manager default.
    from app.warehouse_supplier_portal import _supplier_key
    from app.warehouse_order_sms import normalize_mobile
    for contact in conn.execute('SELECT supplier,contact_mobile FROM warehouse_supplier_auto_order_settings WHERE warehouse_code=?',(warehouse_code,)):
        if _supplier_key(contact['supplier'])!=supplier_key or not contact['contact_mobile']:
            continue
        try: phone=normalize_mobile(contact['contact_mobile'])
        except WarehouseAssistantError: continue
        account=conn.execute('SELECT id,username FROM warehouse_supplier_portal_accounts WHERE username=? AND active=1',(phone,)).fetchone()
        if account and can_access(conn,account['id'],supplier_key,warehouse_code):
            return account['username']
    candidates=[r for r in conn.execute('SELECT id,username FROM warehouse_supplier_portal_accounts WHERE active=1')
                if can_access(conn,r['id'],supplier_key,warehouse_code)]
    managers=[r for r in candidates if (account_access(conn,r['id']) or {}).get('all_orders')]
    preferred=managers or candidates
    return preferred[0]['username'] if len(preferred)==1 else ''


def sync_setting_phone(conn, setting, mobile, actor):
    """Rename in place under the caller's write transaction; never merge grants or reset a password."""
    if not mobile:
        return  # Clearing a contact is not authority to remove a shared person's account.
    from app.warehouse_supplier_portal import _supplier_key
    from app.warehouse_order_sms import normalize_mobile
    key=_supplier_key(setting['supplier'])
    candidates=[r for r in conn.execute('SELECT id,username,mobile FROM warehouse_supplier_portal_accounts WHERE active=1')
                if can_access(conn,r['id'],key,setting['warehouse_code'])]
    if not candidates:
        return  # New accounts are still provisioned by explicit cartable publication.
    phone=normalize_mobile(mobile)
    def normalized(value):
        try: return normalize_mobile(value)
        except WarehouseAssistantError: return str(value or '')
    old=normalized(setting['contact_mobile'])
    matches=[r for r in candidates if old and old in (normalized(r['username']),normalized(r['mobile']))]
    if not matches:
        matches=[r for r in candidates if r['username']==phone]
    if not matches and len(candidates)==1:
        matches=candidates
    if len(matches)!=1:
        raise WarehouseAssistantError('چند مسئول به این تأمین‌کننده دسترسی دارند؛ ابتدا حساب مربوط به شماره قبلی را مشخص کنید. شماره تغییر نکرد.')
    account=matches[0]
    collision=conn.execute('SELECT id FROM warehouse_supplier_portal_accounts WHERE username=? COLLATE NOCASE AND id<>?',(phone,account['id'])).fetchone()
    if collision:
        raise WarehouseAssistantError('شماره جدید متعلق به حساب دیگری است؛ نام کاربری و اطلاعات تماس تغییر نکرد.')
    if account['username']==phone and account['mobile']==phone:
        return
    now=_now()
    conn.execute('UPDATE warehouse_supplier_portal_accounts SET username=?,mobile=?,updated_at=? WHERE id=?',(phone,phone,now,account['id']))
    conn.execute('DELETE FROM warehouse_supplier_portal_sessions WHERE account_id=?',(account['id'],))
    # Keep other settings pointing to this same phone/account consistent, without
    # changing contacts for different warehouse representatives or expanding scope.
    prior={normalized(account['username']),normalized(account['mobile'])}-{''}
    linked=[]
    for row in conn.execute('SELECT id,supplier,warehouse_code,contact_mobile FROM warehouse_supplier_auto_order_settings').fetchall():
        if row['id']!=setting['id'] and normalized(row['contact_mobile']) in prior and can_access(conn,account['id'],_supplier_key(row['supplier']),row['warehouse_code']):
            conn.execute('UPDATE warehouse_supplier_auto_order_settings SET contact_mobile=?,updated_at=?,updated_by=? WHERE id=?',(phone,now,actor[:100],row['id']))
            linked.append(row['id'])
    _event(conn,actor,'account_phone_changed',{'account_id':account['id'],'setting_id':setting['id'],
        'previous_username':account['username'],'username':phone,'linked_setting_ids':linked,'sessions_revoked':True})


def _event(conn,actor,event,payload):
    conn.execute('INSERT INTO warehouse_portal_access_events(actor,event,payload,created_at) VALUES(?,?,?,?)',
                 (actor,event,json.dumps(payload,ensure_ascii=False),_now()))


def catalog(conn):
    suppliers={}
    from app.warehouse_supplier_portal import _supplier_key
    for row in conn.execute('''SELECT supplier FROM warehouse_supplier_auto_order_settings
        UNION SELECT supplier FROM supplier_orders UNION SELECT supplier_name FROM warehouse_supplier_portal_accounts'''):
        if row[0]: suppliers[_supplier_key(row[0])]=row[0]
    warehouses=[dict(r) for r in conn.execute('''SELECT warehouse_code,MAX(warehouse_name) AS warehouse_name
        FROM warehouse_snapshot_items GROUP BY warehouse_code ORDER BY warehouse_code''')]
    return suppliers,warehouses


def list_cartables(settings):
    from app.warehouse_supplier_portal import _init
    _init(settings)
    with warehouse_connection(settings) as conn:
        suppliers,warehouses=catalog(conn)
        groups=[]
        for row in conn.execute('SELECT * FROM warehouse_portal_cartables ORDER BY id'):
            groups.append(dict(row,suppliers=[dict(r) for r in conn.execute(
                'SELECT supplier_key,supplier_name FROM warehouse_portal_cartable_suppliers WHERE cartable_id=? ORDER BY supplier_name',(row['id'],))]))
        return {'cartables':groups,'suppliers':[{'supplier_key':k,'supplier_name':v} for k,v in sorted(suppliers.items())],
                'warehouses':warehouses}


def create_cartable(settings,actor,name,supplier_names,manager_account_id):
    from app.warehouse_supplier_portal import _init,_supplier_key
    name=name.strip()
    keys=[_supplier_key(n) for n in supplier_names]
    if not name or len(name)>200 or not keys or len(set(keys))!=len(keys):
        raise WarehouseAssistantError('نام کارتابل و تأمین‌کنندگان یکتا لازم است.')
    _init(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        known,_=catalog(conn)
        manager=conn.execute('SELECT * FROM warehouse_supplier_portal_accounts WHERE id=?',(manager_account_id,)).fetchone()
        if not manager or not manager['active'] or manager['supplier_key'] not in keys:
            raise WarehouseAssistantError('مسئول کل باید حساب فعال یکی از تأمین‌کنندگان همین کارتابل باشد.')
        if account_access(conn,manager_account_id):
            raise WarehouseAssistantError('این حساب قبلاً به کارتابل متصل شده است.')
        for key in keys:
            if key not in known or conn.execute('SELECT 1 FROM warehouse_portal_cartable_suppliers WHERE supplier_key=?',(key,)).fetchone():
                raise WarehouseAssistantError('تأمین‌کننده ناشناخته است یا قبلاً کارتابل مشترک دارد.')
        group_id=conn.execute('INSERT INTO warehouse_portal_cartables(name,created_by,created_at) VALUES(?,?,?)',(name,actor,_now())).lastrowid
        conn.executemany('INSERT INTO warehouse_portal_cartable_suppliers VALUES(?,?,?)',[(key,known[key],group_id) for key in keys])
        conn.execute('INSERT INTO warehouse_portal_account_access VALUES(?,?,1,1)',(manager_account_id,group_id))
        _event(conn,actor,'cartable_created',{'id':group_id,'suppliers':keys,'manager_account_id':manager_account_id})
        return {'id':group_id,'name':name}


def set_account_access(settings,actor,account_id,cartable_id,all_orders,scopes,expected_revision):
    from app.warehouse_supplier_portal import _init,_supplier_key
    _init(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        account=conn.execute('SELECT * FROM warehouse_supplier_portal_accounts WHERE id=?',(account_id,)).fetchone()
        members={r[0] for r in conn.execute('SELECT supplier_key FROM warehouse_portal_cartable_suppliers WHERE cartable_id=?',(cartable_id,))}
        old=account_access(conn,account_id)
        if not account or not members or account['supplier_key'] not in members:
            raise WarehouseAssistantError('حساب و کارتابل انتخاب‌شده هم‌خوان نیستند.')
        if (old['revision'] if old else 0)!=expected_revision:
            raise WarehouseAssistantError('دسترسی هم‌زمان تغییر کرده؛ بازخوانی کنید.')
        _,warehouses=catalog(conn)
        valid_wh={r['warehouse_code'] for r in warehouses}|{'*'}
        pairs=[(_supplier_key(s['supplier_name']),s['warehouse_code']) for s in scopes]
        if len(pairs)!=len(set(pairs)) or any(k not in members or w not in valid_wh for k,w in pairs):
            raise WarehouseAssistantError('ترکیب تأمین‌کننده و انبار معتبر یا یکتا نیست.')
        if all_orders and pairs:
            raise WarehouseAssistantError('برای مسئول کل، ردیف دسترسی محدود انتخاب نکنید.')
        conn.execute('''INSERT INTO warehouse_portal_account_access VALUES(?,?,?,?) ON CONFLICT(account_id)
            DO UPDATE SET cartable_id=excluded.cartable_id,all_orders=excluded.all_orders,revision=excluded.revision''',
            (account_id,cartable_id,int(all_orders),expected_revision+1))
        conn.execute('DELETE FROM warehouse_portal_account_scopes WHERE account_id=?',(account_id,))
        conn.executemany('INSERT INTO warehouse_portal_account_scopes VALUES(?,?,?)',[(account_id,k,w) for k,w in pairs])
        _event(conn,actor,'account_access_changed',{'account_id':account_id,'before':old,'after':account_access(conn,account_id)})
        return account_access(conn,account_id)
