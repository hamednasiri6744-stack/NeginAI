"""Staff delivery dates, versioned with drafts; supplier proposals remain pending."""
import hashlib


def init_schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS warehouse_order_delivery_dates (
        document_kind TEXT NOT NULL CHECK(document_kind IN ('supplier_order','automatic_preorder')),
        document_id INTEGER NOT NULL,
        requested_delivery_date TEXT NOT NULL,
        updated_by TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(document_kind,document_id))''')


def clean_delivery_date(value, *, optional=False):
    from app.warehouse_purchase_contracts import clean_date, ContractError
    from app.warehouse_assistant_service import WarehouseAssistantError
    try:
        return clean_date(value, optional=optional)
    except ContractError as exc:
        raise WarehouseAssistantError(str(exc)) from exc


def saved_date(conn, kind, document_id):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='warehouse_order_delivery_dates' AND type='table'").fetchone():
        return ''
    row = conn.execute('SELECT requested_delivery_date FROM warehouse_order_delivery_dates WHERE document_kind=? AND document_id=?',
                       (kind, document_id)).fetchone()
    return row[0] if row else ''


def write_date(conn, kind, document_id, value, username, now):
    conn.execute('''INSERT INTO warehouse_order_delivery_dates VALUES (?,?,?,?,?)
        ON CONFLICT(document_kind,document_id) DO UPDATE SET
        requested_delivery_date=excluded.requested_delivery_date,
        updated_by=excluded.updated_by,updated_at=excluded.updated_at''',
                 (kind, document_id, value, username[:100], now))


def apply_delivery_date(conn, order, kind, document_id):
    portal = order.get('supplier_portal') or {}
    registered = saved_date(conn, kind, document_id)
    requested = registered or portal.get('requested_delivery_date') or ''
    proposed = portal.get('proposed_delivery_date') or ''
    order['staff_delivery_date'] = registered
    order['requested_delivery_date'] = requested
    order['delivery_date'] = (proposed or requested) if portal.get('status') == 'accepted' else requested
    order['pending_delivery_date'] = proposed if portal.get('status') == 'submitted' and proposed != requested else ''
    # Old undated drafts keep their tokens; supplier responses never alter this token.
    if registered and order.get('email_send_token'):
        order['email_send_token'] = hashlib.sha256(
            f"{order['email_send_token']}|delivery:{registered}".encode()).hexdigest()


def update_delivery_date(settings, username, kind, document_id, value, *, expected_token, include_all=False):
    from app.warehouse_assistant_service import (
        WarehouseAssistantError, init_warehouse_store, warehouse_connection,
        _order_from_row, _automatic_preorder_from_row, _now,
    )
    if kind not in {'supplier_order', 'automatic_preorder'}:
        raise WarehouseAssistantError('نوع سفارش معتبر نیست.')
    value = clean_delivery_date(value)
    init_warehouse_store(settings)
    table = 'supplier_orders' if kind == 'supplier_order' else 'warehouse_automatic_preorders'
    serialize = _order_from_row if kind == 'supplier_order' else _automatic_preorder_from_row
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute(f'SELECT * FROM {table} WHERE id=?', (document_id,)).fetchone()
        if row is None or (kind == 'supplier_order' and not include_all and row['created_by'] != username):
            raise WarehouseAssistantError('سفارش پیدا نشد.')
        order = serialize(conn, row)
        if kind == 'automatic_preorder' and order.get('source_supplier_order_id'):
            raise WarehouseAssistantError('تاریخ این سفارش را در پیش‌سفارش دستی ویرایش کنید.')
        if not order['can_edit_delivery_date']:
            raise WarehouseAssistantError('تاریخ فقط پیش از قرار دادن در کارتابل قابل ویرایش است.')
        if not expected_token or expected_token != order['email_send_token']:
            raise WarehouseAssistantError('سفارش تغییر کرده؛ پیش‌نمایش را دوباره باز کنید.')
        write_date(conn, kind, document_id, value, username, _now())
        return serialize(conn, row)
