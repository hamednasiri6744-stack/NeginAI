"""Explicit operator-only account migration requested by the customer; never automatic."""
from collections import Counter
from app.warehouse_assistant_service import warehouse_connection, WarehouseAssistantError, _now
from app.warehouse_order_sms import normalize_mobile


def plan(conn):
    rows=conn.execute('SELECT id,username,mobile,supplier_name FROM warehouse_supplier_portal_accounts').fetchall()
    proposed=[];issues=[]
    for row in rows:
        try: mobile=normalize_mobile(row['mobile'] or row['username'])
        except WarehouseAssistantError:
            issues.append({'id':row['id'],'supplier':row['supplier_name'],'reason':'missing_or_invalid_mobile'})
            continue
        proposed.append({'id':row['id'],'username':mobile})
    counts=Counter(item['username'] for item in proposed)
    for item in proposed:
        if counts[item['username']]>1:
            issues.append({'id':item['id'],'reason':'duplicate_mobile'})
    return proposed,issues


def reset_all(settings, actor, *, confirmed=False):
    if not confirmed:
        raise WarehouseAssistantError('تأیید صریح تغییر همه حساب‌ها لازم است.')
    from app.warehouse_supplier_portal import _init
    from app.auth_service import hash_password
    _init(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        proposed,issues=plan(conn)
        if issues:
            raise WarehouseAssistantError('شماره خالی یا تکراری وجود دارد؛ هیچ حسابی تغییر نکرد.')
        # Two-phase rename avoids collisions when two old logins exchange numbers.
        import secrets
        prefix='migration-'+secrets.token_hex(12)+'-'
        for item in proposed:
            conn.execute('UPDATE warehouse_supplier_portal_accounts SET username=? WHERE id=?',(prefix+str(item['id']),item['id']))
        now=_now()
        for item in proposed:
            conn.execute('UPDATE warehouse_supplier_portal_accounts SET username=?,mobile=?,password_hash=?,must_change_password=0,updated_at=? WHERE id=?',
                         (item['username'],item['username'],hash_password('1'),now,item['id']))
            conn.execute('DELETE FROM warehouse_supplier_portal_sessions WHERE account_id=?',(item['id'],))
        conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_portal_account_reset_audit (
            id INTEGER PRIMARY KEY,actor TEXT NOT NULL,account_count INTEGER NOT NULL,created_at TEXT NOT NULL)''')
        conn.execute('INSERT INTO warehouse_portal_account_reset_audit(actor,account_count,created_at) VALUES(?,?,?)',(actor,len(proposed),now))
        return {'accounts_updated':len(proposed),'sessions_revoked':True}
