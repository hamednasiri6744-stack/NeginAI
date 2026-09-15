"""Supplier-facing order cartable with isolated accounts and audited proposals.

Supplier edits never mutate an operational order directly.  A staff user must
accept a submitted response before quantities are applied and the order is
approved.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from copy import copy
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from io import BytesIO
from typing import Any

from openpyxl import Workbook

from app.auth_service import hash_password, verify_password
from app.warehouse_assistant_service import (
    WarehouseAssistantError,
    _now,
    _order_from_row,
    _automatic_preorder_from_row,
    ensure_cycle_allowed,
    _sync_manual_order_fulfillment_projection,
    _supplier_portal_order_status,
    get_automatic_preorder,
    get_supplier_order,
    init_warehouse_store,
    transition_automatic_preorder,
    transition_supplier_order,
    update_automatic_preorder_lines,
    warehouse_connection,
)

SESSION_SECONDS = 12 * 60 * 60
USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{2,99}$")


def _supplier_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().replace("ي", "ی").replace("ك", "ک")).casefold()


def _init(settings: Any) -> None:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS warehouse_supplier_portal_accounts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL COLLATE NOCASE UNIQUE,
              password_hash TEXT NOT NULL,
              supplier_name TEXT NOT NULL,
              supplier_key TEXT NOT NULL,
              mobile TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
              must_change_password INTEGER NOT NULL DEFAULT 1 CHECK(must_change_password IN (0,1)),
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              last_login_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_portal_accounts_supplier
              ON warehouse_supplier_portal_accounts(supplier_key, active);
            CREATE TABLE IF NOT EXISTS warehouse_supplier_portal_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              token_hash TEXT NOT NULL UNIQUE,
              account_id INTEGER NOT NULL REFERENCES warehouse_supplier_portal_accounts(id) ON DELETE CASCADE,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              last_seen_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_portal_sessions_expiry
              ON warehouse_supplier_portal_sessions(expires_at);
            CREATE TABLE IF NOT EXISTS warehouse_supplier_portal_assignments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              document_kind TEXT NOT NULL CHECK(document_kind IN ('supplier_order','automatic_preorder')),
              document_id INTEGER NOT NULL,
              supplier_name TEXT NOT NULL,
              supplier_key TEXT NOT NULL,
              requested_delivery_date TEXT NOT NULL,
              proposed_delivery_date TEXT,
              status TEXT NOT NULL DEFAULT 'awaiting_supplier'
                CHECK(status IN ('awaiting_supplier','draft','submitted','changes_requested','accepted','rejected','cancelled')),
              revision INTEGER NOT NULL DEFAULT 0,
              supplier_comment TEXT NOT NULL DEFAULT '',
              manager_comment TEXT NOT NULL DEFAULT '',
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              submitted_at TEXT,
              decided_by TEXT,
              decided_at TEXT,
              UNIQUE(document_kind, document_id)
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_portal_assignments_supplier
              ON warehouse_supplier_portal_assignments(supplier_key, status, id DESC);
            CREATE TABLE IF NOT EXISTS warehouse_supplier_portal_response_lines (
              assignment_id INTEGER NOT NULL REFERENCES warehouse_supplier_portal_assignments(id) ON DELETE CASCADE,
              product_code TEXT NOT NULL,
              original_cartons INTEGER NOT NULL,
              proposed_cartons INTEGER NOT NULL,
              line_status TEXT NOT NULL DEFAULT 'confirmed'
                CHECK(line_status IN ('confirmed','changed','unavailable')),
              supplier_note TEXT NOT NULL DEFAULT '',
              PRIMARY KEY(assignment_id, product_code)
            );
            CREATE TABLE IF NOT EXISTS warehouse_supplier_portal_comments (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              assignment_id INTEGER NOT NULL REFERENCES warehouse_supplier_portal_assignments(id) ON DELETE CASCADE,
              author_kind TEXT NOT NULL CHECK(author_kind IN ('supplier','staff')),
              author_name TEXT NOT NULL,
              body TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_portal_comments_assignment
              ON warehouse_supplier_portal_comments(assignment_id, id);
            CREATE TABLE IF NOT EXISTS warehouse_supplier_portal_sms_attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              assignment_id INTEGER NOT NULL REFERENCES warehouse_supplier_portal_assignments(id),
              recipient TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('sent','failed','unknown')),
              provider_message_id TEXT,
              requested_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              error TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS warehouse_supplier_portal_email_attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              assignment_id INTEGER NOT NULL REFERENCES warehouse_supplier_portal_assignments(id),
              recipient TEXT NOT NULL,
              sender TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('sending','sent','failed','unknown')),
              message_id TEXT NOT NULL UNIQUE,
              requested_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              completed_at TEXT,
              error TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_portal_email_assignment
              ON warehouse_supplier_portal_email_attempts(assignment_id,id DESC);
            """
        )


        from app.warehouse_portal_publication import init_schema as init_publication_schema
        init_publication_schema(conn)
        from app.warehouse_portal_access import init_schema as init_access_schema
        init_access_schema(conn)


def _document(settings: Any, kind: str, document_id: int) -> dict[str, Any]:
    if kind == "supplier_order":
        doc = get_supplier_order(settings, document_id, "", include_all=True)
        doc = {**doc, "document_kind": kind, "number": doc["order_number"]}
    elif kind == "automatic_preorder":
        doc = get_automatic_preorder(settings, document_id)
        doc = {**doc, "document_kind": kind, "number": doc["preorder_number"]}
    else:
        raise WarehouseAssistantError("نوع سفارش معتبر نیست.")
    if doc.get("deleted") or doc.get("status") in {"cancelled", "superseded"}:
        raise WarehouseAssistantError("سفارش حذف یا لغو شده است.")
    return doc


def _supplier_document(settings: Any, kind: str, document_id: int) -> dict[str, Any]:
    """Read saved order content for the supplier, without inventory forecasting."""
    if kind == "supplier_order":
        table, line_table, parent, number = "supplier_orders", "supplier_order_lines", "order_id", "order_number"
    elif kind == "automatic_preorder":
        table, line_table, parent, number = "warehouse_automatic_preorders", "warehouse_automatic_preorder_lines", "preorder_id", "preorder_number"
    else:
        raise WarehouseAssistantError("نوع سفارش معتبر نیست.")
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN")
        row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (document_id,)).fetchone()
        if row is None:
            raise WarehouseAssistantError("سفارش تأمین‌کننده پیدا نشد.")
        doc = dict(row)
        if doc["status"] in {"cancelled", "superseded"}:
            raise WarehouseAssistantError("سفارش حذف یا لغو شده است.")
        doc["number"] = doc[number]
        warehouse_join = "l.warehouse_code" if kind == "automatic_preorder" else "?"
        params = [doc["snapshot_id"]]
        if kind == "supplier_order":
            params.append(doc["warehouse_code"])
        params.append(document_id)
        ordering = "l.brand,l.product_name" if kind == "automatic_preorder" else "l.id"
        doc["lines"] = [dict(line) for line in conn.execute(f"""
            SELECT l.product_code,l.product_name,l.brand,l.conversion_rate,
                   l.order_quantity,l.cartons,l.manufacturer_price,l.consumer_price,
                   l.buy_price,l.estimated_value,i.manufacturer_product_code,i.barcode,
                   COALESCE(i.group_level3,'') AS group_level3
            FROM {line_table} l
            LEFT JOIN warehouse_snapshot_items i ON i.snapshot_id=?
                AND i.warehouse_code={warehouse_join} AND i.product_code=l.product_code
            WHERE l.{parent}=? ORDER BY {ordering}
        """, params).fetchall()]
        if kind == "supplier_order":
            contact = conn.execute("""SELECT contact_email FROM warehouse_supplier_auto_order_settings
                WHERE warehouse_code=? AND supplier=? COLLATE NOCASE LIMIT 1""",
                (doc["warehouse_code"], doc["supplier"])).fetchone()
            doc["contact_email"] = str(contact["contact_email"] or "") if contact else ""
        elif doc["status"] in {"awaiting_approval", "approved", "send_requested"}:
            locked = conn.execute("""SELECT 1 FROM warehouse_email_attempts WHERE preorder_id=?
                AND status IN ('sending','sent','unknown') LIMIT 1""", (document_id,)).fetchone()
            if not locked:
                contact = conn.execute("""SELECT contact_email FROM warehouse_supplier_auto_order_settings
                    WHERE id=? AND warehouse_code=?""",
                    (doc["supplier_setting_id"], doc["warehouse_code"])).fetchone()
                if contact:
                    doc["contact_email"] = contact["contact_email"]
    return doc


def create_account(settings: Any, staff: str, *, username: str, password: str,
                   supplier_name: str, mobile: str = "") -> dict[str, Any]:
    username = username.strip()
    supplier_name = re.sub(r"\s+", " ", supplier_name.strip())
    if not USERNAME_RE.fullmatch(username) and not re.fullmatch(r'09\d{9}',username):
        raise WarehouseAssistantError("نام کاربری باید با حرف انگلیسی شروع شود و حداقل ۳ نویسه باشد.")
    if password != '1' and (len(password) < 10 or len(password) > 200):
        raise WarehouseAssistantError("رمز موقت باید حداقل ۱۰ نویسه باشد.")
    if not supplier_name or len(supplier_name) > 200:
        raise WarehouseAssistantError("نام تأمین‌کننده معتبر نیست.")
    _init(settings)
    now = _now()
    try:
        with warehouse_connection(settings) as conn:
            account_id = conn.execute(
                """INSERT INTO warehouse_supplier_portal_accounts
                   (username,password_hash,supplier_name,supplier_key,mobile,created_by,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (username, hash_password(password), supplier_name, _supplier_key(supplier_name),
                 mobile.strip()[:30], staff[:100], now, now),
            ).lastrowid
            conn.execute('UPDATE warehouse_supplier_portal_accounts SET must_change_password=0 WHERE id=?',(account_id,))
            group=conn.execute('SELECT cartable_id FROM warehouse_portal_cartable_suppliers WHERE supplier_key=?',(_supplier_key(supplier_name),)).fetchone()
            if group:
                # A new shared-cartable user starts with no scope until staff
                # explicitly assigns responsibilities; never briefly grant all.
                conn.execute('INSERT INTO warehouse_portal_account_access VALUES(?,?,0,0)',(account_id,group['cartable_id']))
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise WarehouseAssistantError("این نام کاربری قبلاً ثبت شده است.") from None
        raise
    return {"id": int(account_id), "username": username, "supplier_name": supplier_name,
            "mobile": mobile.strip(), "active": True, "must_change_password": False}


def list_accounts(settings: Any) -> list[dict[str, Any]]:
    _init(settings)
    with warehouse_connection(settings) as conn:
        rows = conn.execute(
            """SELECT id,username,supplier_name,mobile,active,must_change_password,
                      created_at,last_login_at FROM warehouse_supplier_portal_accounts
               ORDER BY active DESC,supplier_name,username"""
        ).fetchall()
        from app.warehouse_portal_access import account_access
        return [dict(row, active=bool(row["active"]),access=account_access(conn,row['id']),
                     must_change_password=bool(row["must_change_password"])) for row in rows]


def authenticate(settings: Any, username: str, password: str) -> tuple[str, dict[str, Any]] | None:
    username=username.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789'))
    _init(settings)
    with warehouse_connection(settings) as conn:
        row = conn.execute("SELECT * FROM warehouse_supplier_portal_accounts WHERE username=? COLLATE NOCASE", (username.strip(),)).fetchone()
        if row is None or not row["active"] or not verify_password(password, row["password_hash"]):
            return None
        token = secrets.token_urlsafe(40)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        expires = now + timedelta(seconds=SESSION_SECONDS)
        conn.execute("DELETE FROM warehouse_supplier_portal_sessions WHERE expires_at<=?", (now.isoformat(),))
        conn.execute(
            """INSERT INTO warehouse_supplier_portal_sessions
               (token_hash,account_id,created_at,expires_at,last_seen_at) VALUES(?,?,?,?,?)""",
            (hashlib.sha256(token.encode("ascii")).hexdigest(), row["id"], now.isoformat(), expires.isoformat(), now.isoformat()),
        )
        conn.execute("UPDATE warehouse_supplier_portal_accounts SET last_login_at=?,updated_at=? WHERE id=?",
                     (now.isoformat(), now.isoformat(), row["id"]))
        profile = {"id": row["id"], "username": row["username"], "supplier_name": row["supplier_name"],
                   "supplier_key": row["supplier_key"], "mobile": row["mobile"],
                   "must_change_password": bool(row["must_change_password"])}
        from app.warehouse_portal_access import account_access
        profile['access']=account_access(conn,row['id'])
        return token, profile


def session_profile(settings: Any, token: str) -> dict[str, Any] | None:
    if not token or len(token) > 100:
        return None
    _init(settings)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = _now()
    with warehouse_connection(settings) as conn:
        row = conn.execute(
            """SELECT a.* FROM warehouse_supplier_portal_sessions s
               JOIN warehouse_supplier_portal_accounts a ON a.id=s.account_id
               WHERE s.token_hash=? AND s.expires_at>? AND a.active=1""", (token_hash, now)
        ).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE warehouse_supplier_portal_sessions SET last_seen_at=? WHERE token_hash=?", (now, token_hash))
        from app.warehouse_portal_access import account_access
        return {"id": row["id"], "username": row["username"], "supplier_name": row["supplier_name"],
                "supplier_key": row["supplier_key"], "mobile": row["mobile"],
                "must_change_password": bool(row["must_change_password"]),"access":account_access(conn,row['id'])}


def logout(settings: Any, token: str) -> None:
    if token:
        _init(settings)
        with warehouse_connection(settings) as conn:
            conn.execute("DELETE FROM warehouse_supplier_portal_sessions WHERE token_hash=?",
                         (hashlib.sha256(token.encode("utf-8")).hexdigest(),))


def change_password(settings: Any, account_id: int, current: str, new: str) -> None:
    if len(new) < 10 or len(new) > 200 or new == current:
        raise WarehouseAssistantError("رمز جدید باید حداقل ۱۰ نویسه و با رمز فعلی متفاوت باشد.")
    _init(settings)
    with warehouse_connection(settings) as conn:
        row = conn.execute("SELECT password_hash FROM warehouse_supplier_portal_accounts WHERE id=? AND active=1", (account_id,)).fetchone()
        if row is None or not verify_password(current, row["password_hash"]):
            raise WarehouseAssistantError("رمز فعلی صحیح نیست.")
        conn.execute("UPDATE warehouse_supplier_portal_accounts SET password_hash=?,must_change_password=0,updated_at=? WHERE id=?",
                     (hash_password(new), _now(), account_id))


def _approved_document(conn, kind, document_id, expected_token=None, *, enforce_cycle=True):
    table = 'supplier_orders' if kind == 'supplier_order' else 'warehouse_automatic_preorders'
    row = conn.execute(f'SELECT * FROM {table} WHERE id=?', (document_id,)).fetchone()
    if row is None:
        raise WarehouseAssistantError('سفارش پیدا نشد.')
    doc = _order_from_row(conn, row) if kind == 'supplier_order' else _automatic_preorder_from_row(conn, row)
    approved = doc.get('is_approved') if kind == 'supplier_order' else doc['status'] in {'approved', 'send_requested'}
    if not approved or doc.get('deleted') or doc['status'] in {'cancelled', 'superseded'}:
        raise WarehouseAssistantError('ابتدا سفارش را در دستیار انبار تأیید کنید.')
    if expected_token is not None and expected_token != doc['email_send_token']:
        raise WarehouseAssistantError('سفارش تغییر کرده؛ پنجره ارسال را دوباره باز کنید.')
    if enforce_cycle:
        ensure_cycle_allowed(conn, doc['warehouse_code'], [line['product_code'] for line in doc['lines']])
    return doc


def _validate_invitation(conn, assignment, expected_token=None, expected_revision=None, *, enforce_cycle=True):
    from app.warehouse_portal_publication import require_available
    require_available(conn,assignment['id'])
    fresh = conn.execute('SELECT * FROM warehouse_supplier_portal_assignments WHERE id=?', (assignment['id'],)).fetchone()
    if fresh is None or fresh['revision'] != assignment['revision'] or (expected_revision is not None and fresh['revision'] != expected_revision):
        raise WarehouseAssistantError('کارتابل تغییر کرده؛ پنجره ارسال را دوباره باز کنید.')
    if fresh['status'] not in {'awaiting_supplier', 'changes_requested', 'draft'}:
        raise WarehouseAssistantError('این کارتابل دیگر منتظر ارسال نیست.')
    doc = _approved_document(conn, fresh['document_kind'], fresh['document_id'], expected_token, enforce_cycle=enforce_cycle)
    if doc.get('staff_delivery_date') and doc['staff_delivery_date'] != fresh['requested_delivery_date']:
        raise WarehouseAssistantError('تاریخ کارتابل با سفارش یکسان نیست؛ لینک را از سفارش به‌روز بسازید.')
    original = {r['product_code']: r['original_cartons'] for r in conn.execute(
        'SELECT product_code,original_cartons FROM warehouse_supplier_portal_response_lines WHERE assignment_id=?', (fresh['id'],))}
    if original != {line['product_code']: line['cartons'] for line in doc['lines']}:
        raise WarehouseAssistantError('اقلام کارتابل با سفارش یکسان نیست؛ لینک را از سفارش به‌روز بسازید.')
    return doc


def _clean_portal_date(value):
    from datetime import date
    from app.warehouse_purchase_contracts import digits
    from app.warehouse_order_delivery import clean_delivery_date
    value = digits(value or '').strip()
    if '/' in value:
        return clean_delivery_date(value)
    # Preserve previously supported ISO dates on legacy assignments.
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError
        date.fromisoformat(value)
    except ValueError as exc:
        raise WarehouseAssistantError('تاریخ تحویل معتبر نیست؛ مانند ۱۴۰۵/۰۶/۲۵ وارد کنید.') from exc
    return value


def create_assignment(settings: Any, staff: str, *, document_kind: str, document_id: int,
                      requested_delivery_date: str, expected_token: str | None = None,
                      publish: bool = False, portal_username: str = '') -> dict[str, Any]:
    requested_delivery_date = _clean_portal_date(requested_delivery_date)
    doc = _document(settings, document_kind, document_id)
    internally_approved = (
        bool(doc.get("is_approved")) if document_kind == "supplier_order"
        else doc.get("status") in {"approved", "send_requested"}
    )
    if not internally_approved:
        raise WarehouseAssistantError(
            "ابتدا سفارش را در دستیار انبار تأیید کنید؛ سپس لینک کارتابل را بسازید."
        )
    _init(settings)
    now = _now()
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        doc = _approved_document(conn, document_kind, document_id, expected_token)
        if publish:
            from app.warehouse_portal_publication import ensure_phone_account
            login_mobile=portal_username or doc.get('contact_mobile') or ''
            if not login_mobile:
                from app.warehouse_portal_access import default_login
                login_mobile=default_login(conn,_supplier_key(doc['supplier']),doc['warehouse_code'])
            login_mobile=ensure_phone_account(conn,doc['supplier'],login_mobile,staff,warehouse_code=doc['warehouse_code'])
            publication_account_id=conn.execute('SELECT id FROM warehouse_supplier_portal_accounts WHERE username=?',(login_mobile,)).fetchone()['id']
        if doc.get('staff_delivery_date') and doc['staff_delivery_date'] != requested_delivery_date.strip():
            raise WarehouseAssistantError('تاریخ تحویل باید همان تاریخ ثبت‌شده در سفارش باشد؛ ابتدا تاریخ جدید را در سفارش ذخیره کنید، سپس آن را در کارتابل قرار دهید.')
        if (doc.get('supplier_portal') or {}).get('dispatch_locked'):
            raise WarehouseAssistantError('پس از شروع ارسال، اقلام یا تاریخ کارتابل مستقیم قابل تغییر نیست.')
        existing = conn.execute("SELECT id,status FROM warehouse_supplier_portal_assignments WHERE document_kind=? AND document_id=?",
                                (document_kind, document_id)).fetchone()
        if existing and existing["status"] in {"submitted", "accepted"}:
            raise WarehouseAssistantError("این سفارش پاسخ ثبت‌شده دارد و تاریخ آن مستقیم قابل تغییر نیست.")
        if existing:
            assignment_id = int(existing["id"])
            conn.execute("""UPDATE warehouse_supplier_portal_assignments SET requested_delivery_date=?,
                supplier_name=?,supplier_key=?,updated_at=?,revision=revision+1 WHERE id=?""",
                (requested_delivery_date.strip(), doc["supplier"], _supplier_key(doc["supplier"]), now, assignment_id))
            conn.execute("DELETE FROM warehouse_supplier_portal_response_lines WHERE assignment_id=?", (assignment_id,))
        else:
            assignment_id = int(conn.execute(
                """INSERT INTO warehouse_supplier_portal_assignments
                   (document_kind,document_id,supplier_name,supplier_key,requested_delivery_date,created_by,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (document_kind, document_id, doc["supplier"], _supplier_key(doc["supplier"]),
                 requested_delivery_date.strip(), staff[:100], now, now),
            ).lastrowid)
        conn.executemany(
            """INSERT INTO warehouse_supplier_portal_response_lines
               (assignment_id,product_code,original_cartons,proposed_cartons,line_status)
               VALUES(?,?,?,?, 'confirmed')""",
            [(assignment_id, str(line["product_code"]), int(line["cartons"]), int(line["cartons"])) for line in doc["lines"]],
        )
        if publish:
            from app.warehouse_portal_publication import mark_published
            mark_published(conn,assignment_id,staff,publication_account_id)
    return get_assignment(settings, assignment_id, staff=True)


def _assignment_row(settings: Any, assignment_id: int, supplier_key: str | None = None):
    _init(settings)
    with warehouse_connection(settings) as conn:
        if supplier_key is None:
            return conn.execute("SELECT * FROM warehouse_supplier_portal_assignments WHERE id=?", (assignment_id,)).fetchone()
        return conn.execute("SELECT * FROM warehouse_supplier_portal_assignments WHERE id=? AND supplier_key=?",
                            (assignment_id, supplier_key)).fetchone()


def get_assignment(settings: Any, assignment_id: int, *, supplier_key: str | None = None,
                   staff: bool = False, account_id: int | None = None,
                   supplier_view: bool = False) -> dict[str, Any]:
    row = _assignment_row(settings, assignment_id, None if staff or account_id is not None else supplier_key)
    if row is None:
        raise WarehouseAssistantError("سفارش در کارتابل پیدا نشد.")
    if not staff:
        from app.warehouse_portal_publication import require_available
        with warehouse_connection(settings) as conn:
            require_available(conn,assignment_id)
            if account_id is not None:
                from app.warehouse_portal_access import require_assignment
                require_assignment(conn,account_id,row)
    document_reader = _supplier_document if supplier_view and not staff else _document
    doc = document_reader(settings, row["document_kind"], row["document_id"])
    with warehouse_connection(settings) as conn:
        response = {r["product_code"]: dict(r) for r in conn.execute(
            "SELECT * FROM warehouse_supplier_portal_response_lines WHERE assignment_id=?", (assignment_id,)).fetchall()}
        comments = [dict(r) for r in conn.execute(
            "SELECT id,author_kind,author_name,body,created_at FROM warehouse_supplier_portal_comments WHERE assignment_id=? ORDER BY id",
            (assignment_id,)).fetchall()]
        from app.warehouse_portal_publication import state as publication_state
        selected_account_id=(publication_state(conn,assignment_id) or {}).get('account_id')
        account = conn.execute(
            """SELECT username,mobile FROM warehouse_supplier_portal_accounts
               WHERE active=1 AND ((? IS NULL AND supplier_key=?) OR id=?) ORDER BY id LIMIT 1""",
            (selected_account_id,row["supplier_key"],selected_account_id)
        ).fetchone() if staff else None
        if account and selected_account_id:
            from app.warehouse_portal_access import can_access
            if not can_access(conn,selected_account_id,row['supplier_key'],doc['warehouse_code']):
                account=None
    lines = []
    seen_codes: set[str] = set()
    for line in doc["lines"]:
        code = str(line["product_code"])
        seen_codes.add(code)
        proposal = response.get(code, {})
        lines.append({**line, "original_cartons": int(proposal.get("original_cartons", line["cartons"])),
                      "proposed_cartons": int(proposal.get("proposed_cartons", line["cartons"])),
                      "line_status": proposal.get("line_status", "confirmed"),
                      "supplier_note": proposal.get("supplier_note", "")})
    # Accepted manual responses may remove unavailable lines from the operational
    # order. Reconstruct those rows from the immutable snapshot for portal audit.
    removed_codes = set(response).difference(seen_codes)
    if removed_codes:
        marks = ",".join("?" for _ in removed_codes)
        with warehouse_connection(settings) as conn:
            snapshots = conn.execute(
                f"""SELECT product_code,product_name,brand,group_level3,
                            manufacturer_product_code,barcode,conversion_rate
                     FROM warehouse_snapshot_items WHERE snapshot_id=? AND warehouse_code=?
                       AND product_code IN ({marks})""",
                (doc["snapshot_id"], doc["warehouse_code"], *sorted(removed_codes)),
            ).fetchall()
        by_code = {str(item["product_code"]): dict(item) for item in snapshots}
        for code in sorted(removed_codes):
            proposal = response[code]
            source = by_code.get(code, {"product_code": code, "product_name": "قلم حذف‌شده",
                                        "brand": "", "group_level3": "", "manufacturer_product_code": "",
                                        "barcode": "", "conversion_rate": 1})
            lines.append({**source, "original_cartons": int(proposal["original_cartons"]),
                          "proposed_cartons": int(proposal["proposed_cartons"]),
                          "line_status": proposal["line_status"], "supplier_note": proposal["supplier_note"]})
    result = {**dict(row), "document": {k: doc.get(k) for k in ("number","supplier","warehouse_name","total_cartons","total_quantity","contact_email")},
              "lines": lines, "comments": comments}
    result["has_changes"] = (
        bool(result.get("proposed_delivery_date"))
        and str(result.get("proposed_delivery_date")) != str(result.get("requested_delivery_date"))
    ) or any(int(line["proposed_cartons"]) != int(line["original_cartons"]) for line in lines)
    if staff:
        result["portal_account"] = dict(account) if account else None
    with warehouse_connection(settings) as conn:
        workflow = _supplier_portal_order_status(
            conn, str(row["document_kind"]), int(row["document_id"])
        )
    result["workflow_status"] = (workflow or {}).get("workflow_status", "awaiting_link")
    result["dispatch_sent"] = bool((workflow or {}).get("dispatch_sent"))
    for field in ('published_at','first_viewed_at','can_withdraw','publication_epoch','publication_state','notification_status'):
        result[field]=(workflow or {}).get(field)
    result['delivery_date'] = (result.get('proposed_delivery_date') or result['requested_delivery_date']) if result['status'] == 'accepted' else result['requested_delivery_date']
    result['pending_delivery_date'] = result.get('proposed_delivery_date') if result['status'] == 'submitted' and result.get('proposed_delivery_date') != result['requested_delivery_date'] else ''
    return result


def list_assignment_summaries(settings: Any, *, account_id: int) -> list[dict[str, Any]]:
    """List authorized headers without hydrating inventory/lines or disclosing an order."""
    from app.warehouse_portal_access import can_access
    _init(settings)
    with warehouse_connection(settings) as conn:
        # Keep scope checks and headers in the same read snapshot.
        conn.execute('BEGIN')
        candidates = conn.execute('''
            SELECT a.*, d.number, d.supplier, d.warehouse_code, d.warehouse_name,
                   d.total_quantity, d.total_cartons, d.contact_email
            FROM warehouse_supplier_portal_assignments a
            JOIN (
                SELECT 'automatic_preorder' kind, id, preorder_number number,
                       supplier, warehouse_code, warehouse_name, total_quantity,
                       total_cartons, contact_email, status
                FROM warehouse_automatic_preorders
                UNION ALL
                SELECT 'supplier_order', id, order_number, supplier,
                       warehouse_code, warehouse_name, total_quantity, NULL,
                       COALESCE((SELECT contact_email FROM warehouse_supplier_auto_order_settings s
                          WHERE s.warehouse_code=o.warehouse_code
                          AND s.supplier=o.supplier COLLATE NOCASE LIMIT 1), ''), status
                FROM supplier_orders o
            ) d ON d.kind=a.document_kind AND d.id=a.document_id
            LEFT JOIN warehouse_portal_publications p ON p.assignment_id=a.id
            WHERE p.withdrawn_at IS NULL AND d.status NOT IN ('cancelled','superseded')
            ORDER BY a.id DESC
        ''').fetchall()
        result = []
        for row in candidates:
            if not can_access(conn, account_id, row['supplier_key'], row['warehouse_code']):
                continue
            item = {key: row[key] for key in ('id', 'status', 'requested_delivery_date', 'proposed_delivery_date')}
            item['delivery_date'] = (row['proposed_delivery_date'] or row['requested_delivery_date']) if row['status'] == 'accepted' else row['requested_delivery_date']
            item['document'] = {key: row[key] for key in ('number', 'supplier', 'warehouse_name', 'total_cartons', 'total_quantity', 'contact_email')}
            result.append(item)
            if len(result) == 200:
                break
        return result


def list_assignments(settings: Any, *, supplier_key: str | None = None, staff: bool = False, account_id: int | None = None) -> list[dict[str, Any]]:
    _init(settings)
    with warehouse_connection(settings) as conn:
        if staff:
            rows = conn.execute("SELECT id FROM warehouse_supplier_portal_assignments ORDER BY CASE status WHEN 'submitted' THEN 0 WHEN 'changes_requested' THEN 1 ELSE 2 END,id DESC LIMIT 300").fetchall()
        elif account_id is not None:
            from app.warehouse_portal_access import can_access,assignment_warehouse
            candidates=conn.execute('SELECT * FROM warehouse_supplier_portal_assignments ORDER BY id DESC').fetchall()
            rows=[r for r in candidates if can_access(conn,account_id,r['supplier_key'],assignment_warehouse(conn,r))][:200]
        else:
            rows = conn.execute("SELECT id FROM warehouse_supplier_portal_assignments WHERE supplier_key=? ORDER BY id DESC LIMIT 200", (supplier_key,)).fetchall()
        from app.warehouse_portal_publication import state as publication_state
        rows=[row for row in rows if not (publication_state(conn,row['id']) or {}).get('withdrawn_at')]
    return [get_assignment(settings, int(row["id"]), supplier_key=supplier_key, staff=staff,account_id=account_id) for row in rows]


def save_response(settings: Any, account: dict[str, Any], assignment_id: int, *,
                  expected_revision: int, proposed_delivery_date: str,
                  supplier_comment: str, lines: list[dict[str, Any]], submit: bool,
                  confirmation_mode: str = "auto") -> dict[str, Any]:
    assignment = get_assignment(settings, assignment_id, supplier_key=account["supplier_key"],account_id=account.get('id'))
    if assignment["status"] in {"submitted", "accepted", "rejected", "cancelled"}:
        raise WarehouseAssistantError("این سفارش بسته شده و قابل تغییر نیست.")
    if not proposed_delivery_date.strip():
        proposed_delivery_date = assignment["requested_delivery_date"]
    proposed_delivery_date = _clean_portal_date(proposed_delivery_date)
    original = {str(line["product_code"]): line for line in assignment["lines"]}
    incoming: dict[str, dict[str, Any]] = {}
    for item in lines:
        code = str(item.get("product_code") or "").strip()
        if code not in original or code in incoming:
            raise WarehouseAssistantError("فهرست اقلام پاسخ با سفارش یکسان نیست.")
        cartons = item.get("proposed_cartons")
        if isinstance(cartons, bool) or not isinstance(cartons, int) or cartons < 0 or cartons > 1_000_000:
            raise WarehouseAssistantError("تعداد کارتن پیشنهادی معتبر نیست.")
        status = str(item.get("line_status") or "confirmed")
        if status not in {"confirmed", "changed", "unavailable"}:
            raise WarehouseAssistantError("وضعیت قلم معتبر نیست.")
        if status == "unavailable":
            cartons = 0
        elif cartons != int(original[code]["original_cartons"]):
            status = "changed"
        else:
            status = "confirmed"
        incoming[code] = {"cartons": cartons, "status": status,
                          "note": str(item.get("supplier_note") or "").strip()[:500]}
    if set(incoming) != set(original):
        raise WarehouseAssistantError("پاسخ همه اقلام سفارش باید ارسال شود.")
    has_changes = (
        proposed_delivery_date.strip() != str(assignment["requested_delivery_date"]).strip()
        or any(item["cartons"] != int(original[code]["original_cartons"])
               for code, item in incoming.items())
    )
    if confirmation_mode == "confirm" and has_changes:
        raise WarehouseAssistantError(
            "برای تأیید کامل، تاریخ و تعدادها باید مطابق سفارش باشند؛ درخواست تغییر را بزنید."
        )
    if confirmation_mode not in {"auto", "confirm", "request_change"}:
        raise WarehouseAssistantError("نوع پاسخ سفارش معتبر نیست.")
    next_status = "accepted" if submit and not has_changes else ("submitted" if submit else "draft")
    _init(settings)
    now = _now()
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _validate_invitation(conn, assignment, enforce_cycle=False)
        if account.get('id') is not None:
            from app.warehouse_portal_access import require_assignment
            require_assignment(conn,account['id'],assignment)
        changed = conn.execute(
            """UPDATE warehouse_supplier_portal_assignments SET status=?,proposed_delivery_date=?,
               supplier_comment=?,updated_at=?,submitted_at=?,revision=revision+1
               WHERE id=? AND supplier_key=? AND revision=? AND status NOT IN ('accepted','rejected','cancelled')""",
            (next_status, proposed_delivery_date.strip(), supplier_comment.strip()[:1000],
             now, now if submit else None, assignment_id, assignment["supplier_key"], expected_revision),
        ).rowcount
        if not changed:
            raise WarehouseAssistantError("پاسخ سفارش تغییر کرده است؛ صفحه را دوباره باز کنید.")
        conn.executemany(
            """UPDATE warehouse_supplier_portal_response_lines SET proposed_cartons=?,line_status=?,supplier_note=?
               WHERE assignment_id=? AND product_code=?""",
            [(item["cartons"], item["status"], item["note"], assignment_id, code) for code, item in incoming.items()],
        )
        if next_status == "accepted":
            conn.execute(
                """UPDATE warehouse_supplier_portal_assignments
                   SET decided_by=?,decided_at=?,manager_comment='' WHERE id=?""",
                (f"supplier:{account['username']}"[:100], now, assignment_id),
            )
    return get_assignment(settings, assignment_id, supplier_key=account["supplier_key"],account_id=account.get('id'))


def add_comment(settings: Any, assignment_id: int, *, author_kind: str, author_name: str,
                body: str, supplier_key: str | None = None, account_id: int | None = None) -> dict[str, Any]:
    body = re.sub(r"\s+", " ", body.strip())
    if not body or len(body) > 1000:
        raise WarehouseAssistantError("متن پیام باید بین ۱ تا ۱۰۰۰ نویسه باشد.")
    row = _assignment_row(settings, assignment_id, supplier_key if author_kind == "supplier" and account_id is None else None)
    if row is None:
        raise WarehouseAssistantError("سفارش در کارتابل پیدا نشد.")
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if author_kind=='supplier':
            from app.warehouse_portal_access import require_assignment
            from app.warehouse_portal_publication import require_available
            require_available(conn,assignment_id)
            if account_id is not None: require_assignment(conn,account_id,row)
        comment_id = conn.execute(
            "INSERT INTO warehouse_supplier_portal_comments(assignment_id,author_kind,author_name,body,created_at) VALUES(?,?,?,?,?)",
            (assignment_id, author_kind, author_name[:200], body, _now()),
        ).lastrowid
    return {"id": int(comment_id), "body": body}


def decide(settings: Any, staff: str, assignment_id: int, *, decision: str,
           expected_revision: int, manager_comment: str = "") -> dict[str, Any]:
    if decision not in {"accept", "changes_requested", "reject"}:
        raise WarehouseAssistantError("تصمیم معتبر نیست.")
    _init(settings)
    new_status = {"accept": "accepted", "changes_requested": "changes_requested", "reject": "rejected"}[decision]
    now = _now()
    with warehouse_connection(settings) as conn:
        # The response, operational quantities and manual projection commit together.
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM warehouse_supplier_portal_assignments WHERE id=?', (assignment_id,)).fetchone()
        if row is None or row['status'] != 'submitted':
            raise WarehouseAssistantError('فقط پاسخ ارسال‌شده قابل بررسی است.')
        if row['revision'] != expected_revision:
            raise WarehouseAssistantError('پاسخ تأمین‌کننده تغییر کرده است؛ صفحه را بازخوانی کنید.')
        assignment = dict(row)
        from app.warehouse_portal_publication import require_available
        require_available(conn, assignment_id)
        if decision == 'accept':
            # This order is already approved/published, possibly on a previous day.
            # Never send it through the daily draft approval transition again.
            doc = _approved_document(conn, assignment['document_kind'], assignment['document_id'], enforce_cycle=False)
            lines = conn.execute('SELECT * FROM warehouse_supplier_portal_response_lines WHERE assignment_id=?', (assignment_id,)).fetchall()
            original = {r['product_code']: int(r['original_cartons']) for r in lines}
            current = {str(r['product_code']): int(r['cartons']) for r in doc['lines']}
            if original != current:
                raise WarehouseAssistantError('تعداد سفارش اصلی تغییر کرده است؛ پیش از تأیید، مغایرت سفارش و پاسخ بررسی شود.')
            requested = [{'product_code': r['product_code'], 'cartons': int(r['proposed_cartons'])} for r in lines]
            positive = [item for item in requested if item['cartons'] > 0]
            if not positive:
                raise WarehouseAssistantError('همه اقلام ناموجود اعلام شده‌اند؛ سفارش را از بخش سفارش‌ها لغو کنید.')
            quantity_changed = any(r['original_cartons'] != r['proposed_cartons'] for r in lines)
            if quantity_changed:
                if assignment['document_kind'] == 'automatic_preorder':
                    update_automatic_preorder_lines(settings, staff, assignment['document_id'], requested,
                        expected_token=doc['email_send_token'], allow_approved_portal_response=True, _connection=conn)
                else:
                    ensure_cycle_allowed(conn, doc['warehouse_code'], [r['product_code'] for r in positive])
                    _apply_manual_response(settings, staff, assignment, positive, _connection=conn)
        changed = conn.execute(
            """UPDATE warehouse_supplier_portal_assignments SET status=?,manager_comment=?,decided_by=?,
               decided_at=?,updated_at=?,revision=revision+1 WHERE id=? AND revision=? AND status='submitted'""",
            (new_status, manager_comment.strip()[:1000], staff[:100], now, now, assignment_id, expected_revision),
        ).rowcount
        if not changed:
            raise WarehouseAssistantError("پاسخ هم‌زمان تغییر کرده است؛ وضعیت سفارش اصلی را بررسی کنید.")
    return get_assignment(settings, assignment_id, staff=True)


def _apply_manual_response(settings: Any, staff: str, assignment: dict[str, Any], positive: list[dict[str, Any]], *, _connection=None) -> None:
    order_id = int(assignment["document_id"])
    quantities = {str(item["product_code"]): int(item["cartons"]) for item in positive}
    with (warehouse_connection(settings) if _connection is None else nullcontext(_connection)) as conn:
        if _connection is None:
            conn.execute("BEGIN IMMEDIATE")
        order = conn.execute("SELECT * FROM supplier_orders WHERE id=?", (order_id,)).fetchone()
        if order is None or order["status"] != "prepared":
            raise WarehouseAssistantError("سفارش دستی دیگر در وضعیت قابل ویرایش نیست.")
        projection = conn.execute(
            "SELECT id FROM warehouse_automatic_preorders WHERE source_supplier_order_id=?",
            (order_id,),
        ).fetchone()
        if projection:
            activity = conn.execute(
                """SELECT 1 FROM warehouse_fulfillment_receipts WHERE preorder_id=?
                   UNION ALL SELECT 1 FROM warehouse_receipt_allocations WHERE preorder_id=?
                   UNION ALL SELECT 1 FROM warehouse_fulfillment_adjustments WHERE preorder_id=?
                   LIMIT 1""",
                (projection["id"], projection["id"], projection["id"]),
            ).fetchone()
            if activity:
                raise WarehouseAssistantError(
                    "برای این سفارش دریافت یا تعدیل ثبت شده و تغییر تعداد دیگر ممکن نیست."
                )
        rows = conn.execute("SELECT product_code,conversion_rate,buy_price FROM supplier_order_lines WHERE order_id=?", (order_id,)).fetchall()
        for row in rows:
            code = str(row["product_code"])
            if code not in quantities:
                conn.execute("DELETE FROM supplier_order_lines WHERE order_id=? AND product_code=?", (order_id, code))
                continue
            cartons = quantities[code]
            quantity = cartons * float(row["conversion_rate"])
            conn.execute("""UPDATE supplier_order_lines SET cartons=?,order_quantity=?,estimated_value=?
                          WHERE order_id=? AND product_code=?""",
                         (cartons, quantity, quantity * float(row["buy_price"]), order_id, code))
        conn.execute("""UPDATE supplier_orders SET total_quantity=(SELECT COALESCE(SUM(order_quantity),0) FROM supplier_order_lines WHERE order_id=?),
                     estimated_value=(SELECT COALESCE(SUM(estimated_value),0) FROM supplier_order_lines WHERE order_id=?),
                     edited_by=?,edited_at=? WHERE id=?""", (order_id, order_id, staff[:100], _now(), order_id))
        updated_row = conn.execute("SELECT * FROM supplier_orders WHERE id=?", (order_id,)).fetchone()
        updated_order = _order_from_row(conn, updated_row)
        if updated_order["is_approved"]:
            _sync_manual_order_fulfillment_projection(
                conn, updated_order, staff, active=True
            )


def response_workbook(settings: Any, assignment_id: int, *, supplier_key: str | None = None,
                      staff: bool = False, account_id: int | None = None) -> bytes:
    assignment = get_assignment(settings, assignment_id, supplier_key=supplier_key, staff=staff,account_id=account_id)
    wb = Workbook()
    ws = wb.active
    ws.title = "پاسخ سفارش"
    ws.sheet_view.rightToLeft = True
    ws.append(["شماره سفارش", "تأمین‌کننده", "انبار", "تاریخ تحویل درخواستی", "تاریخ تحویل تأمین‌کننده",
               "کد کالا", "کد تأمین‌کننده", "بارکد", "نام کالا", "گروه کالا", "برند", "تعداد در کارتن",
               "کارتن سفارش", "کارتن تأییدشده", "وضعیت قلم", "توضیح تأمین‌کننده"])
    labels = {"confirmed": "تأیید", "changed": "درخواست تغییر", "unavailable": "ناموجود/حذف"}
    for line in assignment["lines"]:
        ws.append([assignment["document"]["number"], assignment["supplier_name"], assignment["document"]["warehouse_name"],
                   assignment["requested_delivery_date"], assignment.get("proposed_delivery_date") or "",
                   line["product_code"], line.get("manufacturer_product_code") or "", line.get("barcode") or "",
                   line["product_name"], line.get("group_level3") or "", line.get("brand") or "", line["conversion_rate"],
                   line["original_cartons"], line["proposed_cartons"], labels[line["line_status"]], line["supplier_note"]])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        font = copy(cell.font)
        font.bold = True
        cell.font = font
    for column in ws.columns:
        ws.column_dimensions[column[0].column_letter].width = min(38, max(12, max(len(str(c.value or "")) for c in column) + 2))
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def send_invitation(settings: Any, staff: str, assignment_id: int, mobile: str, *, expected_token=None, expected_revision=None) -> dict[str, Any]:
    """Send the stable login URL; passwords are deliberately never included in SMS."""
    from app import warehouse_order_sms as sms
    assignment = get_assignment(settings, assignment_id, staff=True)
    account = assignment.get("portal_account")
    if not account:
        raise WarehouseAssistantError("ابتدا برای این تأمین‌کننده حساب کارتابل بسازید.")
    recipient = sms.normalize_mobile(mobile or account.get("mobile") or "")
    config = sms._provider_config()
    message = (f"نگین پخش\nسفارش {assignment['document']['number']} در کارتابل شما ثبت شد.\n"
               f"ورود: {sms.PUBLIC_BASE_URL}/supplier-portal\nنام کاربری: {account['username']}\n"
               "رمز عبور از مسیر امن جداگانه اعلام می‌شود.")
    # Claim before leaving the transaction: revocation/editing and concurrent
    # retries must see the uncertain attempt while the provider is running.
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        from app.warehouse_portal_publication import require_available, epoch
        require_available(conn,assignment_id)
        publication_epoch=epoch(conn,assignment_id)
        last = conn.execute('SELECT status FROM warehouse_supplier_portal_sms_attempts WHERE assignment_id=? AND recipient=? AND publication_epoch=? ORDER BY id DESC LIMIT 1', (assignment_id, recipient,publication_epoch)).fetchone()
        if last and last['status'] == 'sent':
            return {'send_status': 'sent', 'already_sent': True, 'external_delivery_performed': False}
        if last and last['status'] == 'unknown':
            raise WarehouseAssistantError('نتیجه ارسال قبلی قطعی نیست؛ دوباره ارسال نشد.')
        _validate_invitation(conn, assignment, expected_token, expected_revision)
        attempt_id = conn.execute('''INSERT INTO warehouse_supplier_portal_sms_attempts
            (assignment_id,recipient,status,requested_by,created_at,error,publication_epoch)
            VALUES(?,?,'unknown',?,?,?,?)''', (assignment_id, recipient, staff[:100], _now(), 'ارسال در جریان است؛ نتیجه هنوز قطعی نیست.',publication_epoch)).lastrowid
    outcome, provider_id, error = "sent", "", ""
    try:
        provider_id = sms._send_provider(config, recipient, message)
    except sms.SmsDeliveryFailure as exc:
        outcome, error = exc.status, str(exc)
    except Exception:
        outcome, error = "unknown", "نتیجهٔ ارسال پیامک نیازمند بررسی مدیر سیستم است."
    with warehouse_connection(settings) as conn:
        conn.execute('''UPDATE warehouse_supplier_portal_sms_attempts SET status=?,provider_message_id=?,error=? WHERE id=?''',
                     (outcome, provider_id or None, error, attempt_id))
    if outcome != "sent":
        raise WarehouseAssistantError(error)
    return {"send_status": "sent", "recipient_masked": recipient[:4] + "***" + recipient[-4:],
            "portal_url": f"{sms.PUBLIC_BASE_URL}/supplier-portal", "external_delivery_performed": True}


def send_email_invitation(
    settings: Any, staff: str, assignment_id: int, email: str = "", *, expected_token=None, expected_revision=None
) -> dict[str, Any]:
    """Send the supplier portal URL by email without ever including a password."""
    from app import warehouse_email as mail
    from app.warehouse_order_sms import PUBLIC_BASE_URL

    assignment = get_assignment(settings, assignment_id, staff=True)
    account = assignment.get("portal_account")
    if not account:
        raise WarehouseAssistantError("ابتدا برای این تأمین‌کننده حساب کارتابل بسازید.")
    recipient = mail._address(email.strip() or str(assignment["document"].get("contact_email") or "").strip())
    config = mail._config()
    _init(settings)
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        from app.warehouse_portal_publication import require_available, epoch
        require_available(conn,assignment_id)
        publication_epoch=epoch(conn,assignment_id)
        last = conn.execute(
            """SELECT status FROM warehouse_supplier_portal_email_attempts
               WHERE assignment_id=? AND recipient=? AND publication_epoch=? ORDER BY id DESC LIMIT 1""",
            (assignment_id, recipient,publication_epoch),
        ).fetchone()
        if last and last["status"] == "sent":
            return {
                "send_status": "sent", "recipient": recipient,
                "portal_url": f"{PUBLIC_BASE_URL}/supplier-portal",
                "external_delivery_performed": False, "already_sent": True,
            }
        if last and last["status"] in {"sending", "unknown"}:
            raise WarehouseAssistantError(
                "نتیجه ارسال قبلی هنوز قطعی نیست؛ برای جلوگیری از ارسال تکراری دوباره ارسال نشد."
            )
        _validate_invitation(conn, assignment, expected_token, expected_revision)
        message = EmailMessage()
        message["From"] = f"Negin Pakhsh Orders <{config['username']}>"
        message["To"] = recipient
        message["Subject"] = f"کارتابل سفارش نگین پخش - {assignment['document']['number']}"
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=config["username"].split("@")[1])
        message.set_content(
            f"سلام،\n\nسفارش {assignment['document']['number']} در کارتابل تأمین‌کننده ثبت شده است.\n"
            f"ورود به کارتابل: {PUBLIC_BASE_URL}/supplier-portal\n"
            f"نام کاربری: {account['username']}\n"
            "رمز عبور از مسیر امن جداگانه اعلام می‌شود.\n\nنگین پخش\n"
        )
        message.as_bytes()
        created = _now()
        attempt_id = conn.execute(
            """INSERT INTO warehouse_supplier_portal_email_attempts
               (assignment_id,recipient,sender,status,message_id,requested_by,created_at,publication_epoch)
               VALUES(?,?,?,'sending',?,?,?,?)""",
            (assignment_id, recipient, config["username"], message["Message-ID"], staff[:100], created,publication_epoch),
        ).lastrowid
    outcome, error = "sent", ""
    try:
        mail._smtp_send(config, message)
    except mail.MailDeliveryFailure as exc:
        outcome, error = exc.status, str(exc)
    except Exception:
        outcome, error = "unknown", "نتیجه ارسال ایمیل نیازمند بررسی مدیر سیستم است."
    with warehouse_connection(settings) as conn:
        conn.execute(
            """UPDATE warehouse_supplier_portal_email_attempts
               SET status=?,completed_at=?,error=? WHERE id=?""",
            (outcome, _now(), error, attempt_id),
        )
    if outcome != "sent":
        raise WarehouseAssistantError(error)
    return {
        "send_status": "sent", "recipient": recipient,
        "portal_url": f"{PUBLIC_BASE_URL}/supplier-portal",
        "external_delivery_performed": True, "already_sent": False,
    }
