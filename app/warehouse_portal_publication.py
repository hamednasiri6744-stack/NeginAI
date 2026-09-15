"""Publication, first disclosure and withdrawal share one SQLite write boundary."""
from app.warehouse_assistant_service import WarehouseAssistantError, warehouse_connection, _now


def init_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_portal_publications (
        assignment_id INTEGER PRIMARY KEY,
        epoch INTEGER NOT NULL,
        published_at TEXT NOT NULL,
        published_by TEXT NOT NULL,
        first_viewed_at TEXT,
        withdrawn_at TEXT,
        withdrawn_by TEXT)''')
    if 'account_id' not in {r[1] for r in conn.execute('PRAGMA table_info(warehouse_portal_publications)')}:
        conn.execute('ALTER TABLE warehouse_portal_publications ADD COLUMN account_id INTEGER')
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_portal_publication_events (
        id INTEGER PRIMARY KEY,assignment_id INTEGER NOT NULL,epoch INTEGER NOT NULL,
        event TEXT NOT NULL,actor TEXT NOT NULL,created_at TEXT NOT NULL)''')
    for table in ('warehouse_supplier_portal_sms_attempts','warehouse_supplier_portal_email_attempts'):
        if 'publication_epoch' not in {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN publication_epoch INTEGER NOT NULL DEFAULT 0')


def state(conn, assignment_id):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_portal_publications'").fetchone():
        return None
    row=conn.execute('SELECT * FROM warehouse_portal_publications WHERE assignment_id=?',(assignment_id,)).fetchone()
    return dict(row) if row else None


def epoch(conn, assignment_id):
    current=state(conn,assignment_id)
    return current['epoch'] if current else 0


def require_available(conn, assignment_id):
    current=state(conn,assignment_id)
    if current and current['withdrawn_at']:
        raise WarehouseAssistantError('این سفارش از کارتابل برداشته شده است؛ صفحه را بازخوانی کنید.')
    return current


def mark_published(conn, assignment_id, actor, account_id=None):
    current=state(conn,assignment_id)
    if current and not current['withdrawn_at']:
        return
    version=(current['epoch'] if current else 0)+1
    now=_now()
    conn.execute('''INSERT INTO warehouse_portal_publications
        (assignment_id,epoch,published_at,published_by,first_viewed_at,withdrawn_at,withdrawn_by,account_id)
        VALUES(?,?,?,?,NULL,NULL,NULL,?)
        ON CONFLICT(assignment_id) DO UPDATE SET epoch=excluded.epoch,published_at=excluded.published_at,
        published_by=excluded.published_by,first_viewed_at=NULL,withdrawn_at=NULL,withdrawn_by=NULL,
        account_id=excluded.account_id''',
        (assignment_id,version,now,actor,account_id))
    conn.execute('INSERT INTO warehouse_portal_publication_events(assignment_id,epoch,event,actor,created_at) VALUES(?,?,?,?,?)',
                 (assignment_id,version,'published',actor,now))


def mark_viewed(settings, assignment_id, supplier_key=None, *, account_id=None):
    from app.warehouse_supplier_portal import _init
    _init(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM warehouse_supplier_portal_assignments WHERE id=? AND (? IS NOT NULL OR supplier_key=?)',
                         (assignment_id,account_id,supplier_key)).fetchone()
        if row is None:
            raise WarehouseAssistantError('سفارش در کارتابل پیدا نشد.')
        if account_id is not None:
            from app.warehouse_portal_access import require_assignment
            require_assignment(conn,account_id,row)
            supplier_key=f'account:{account_id}'
        current=require_available(conn,assignment_id)
        if current is None:
            # Legacy invitations have no trustworthy historical first-view timestamp.
            conn.execute('INSERT INTO warehouse_portal_publications (assignment_id,epoch,published_at,published_by) VALUES(?,0,?,?)',
                         (assignment_id,row['created_at'],'legacy-view-tracking'))
            current=state(conn,assignment_id)
        if not current['first_viewed_at']:
            now=_now()
            conn.execute('UPDATE warehouse_portal_publications SET first_viewed_at=? WHERE assignment_id=?',(now,assignment_id))
            conn.execute('INSERT INTO warehouse_portal_publication_events(assignment_id,epoch,event,actor,created_at) VALUES(?,?,?,?,?)',
                         (assignment_id,current['epoch'],'viewed',supplier_key,now))


def withdraw(settings, actor, assignment_id, expected_revision):
    from app.warehouse_supplier_portal import _init
    _init(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM warehouse_supplier_portal_assignments WHERE id=?',(assignment_id,)).fetchone()
        current=state(conn,assignment_id)
        if not row or not current or current['withdrawn_at'] or current['first_viewed_at'] or row['status']!='awaiting_supplier':
            raise WarehouseAssistantError('برداشتن فقط پیش از اولین مشاهده ممکن است؛ برای سفارش قدیمی با سابقه نامشخص نیز مجاز نیست.')
        if row['revision']!=expected_revision:
            raise WarehouseAssistantError('کارتابل تغییر کرده؛ فهرست را بازخوانی کنید.')
        for table in ('warehouse_supplier_portal_email_attempts','warehouse_supplier_portal_sms_attempts'):
            if conn.execute(f"SELECT 1 FROM {table} WHERE assignment_id=? AND publication_epoch=? AND (status='sending' OR (status='unknown' AND error=?))",
                            (assignment_id,current['epoch'],'ارسال در جریان است؛ نتیجه هنوز قطعی نیست.')).fetchone():
                raise WarehouseAssistantError('اطلاع‌رسانی در جریان است؛ پس از پایان دوباره بررسی کنید.')
        now=_now()
        conn.execute('UPDATE warehouse_portal_publications SET withdrawn_at=?,withdrawn_by=? WHERE assignment_id=?',(now,actor,assignment_id))
        conn.execute('UPDATE warehouse_supplier_portal_assignments SET revision=revision+1,updated_at=? WHERE id=?',(now,assignment_id))
        conn.execute('INSERT INTO warehouse_portal_publication_events(assignment_id,epoch,event,actor,created_at) VALUES(?,?,?,?,?)',
                     (assignment_id,current['epoch'],'withdrawn',actor,now))
        return {'withdrawn':True,'document_kind':row['document_kind'],'document_id':row['document_id'],'order_stage':'draft'}


def ensure_phone_account(conn, supplier_name, mobile, actor, *, warehouse_code=None):
    from app.warehouse_order_sms import normalize_mobile
    from app.warehouse_supplier_portal import _supplier_key
    from app.auth_service import hash_password
    mobile=normalize_mobile(mobile)
    key=_supplier_key(supplier_name)
    existing=conn.execute('SELECT * FROM warehouse_supplier_portal_accounts WHERE username=? COLLATE NOCASE',(mobile,)).fetchone()
    if existing:
        from app.warehouse_portal_access import can_access
        allowed=can_access(conn,existing['id'],key,warehouse_code)
        if not allowed:
            raise WarehouseAssistantError('این شماره متعلق به حساب دیگری است یا غیرفعال است؛ حساب‌ها را بررسی کنید.')
        return mobile
    retired=conn.execute("""SELECT 1 FROM warehouse_portal_access_events
        WHERE event='account_phone_changed' AND json_extract(payload,'$.previous_username')=? LIMIT 1""",(mobile,)).fetchone()
    if retired:
        raise WarehouseAssistantError('این نام کاربری قبلی غیرفعال شده است؛ شماره جدید مسئول را از تنظیمات بازخوانی کنید.')
    if conn.execute('SELECT 1 FROM warehouse_portal_cartable_suppliers WHERE supplier_key=?',(key,)).fetchone():
        raise WarehouseAssistantError('ابتدا حساب مسئول و دسترسی او را در کارتابل مشترک تنظیم کنید.')
    now=_now()
    conn.execute('''INSERT INTO warehouse_supplier_portal_accounts
        (username,password_hash,supplier_name,supplier_key,mobile,must_change_password,created_by,created_at,updated_at)
        VALUES(?,?,?,?,?,0,?,?,?)''',(mobile,hash_password('1'),supplier_name,key,mobile,actor,now,now))
    return mobile
