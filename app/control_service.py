"""Offline-safe personnel, position, and permission management in local SQLite."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.auth_service import revoke_user_credentials_in_transaction
from app.database import execute_query, sqlite_connection
from app.sql_guard import validate_read_only_sql


PERMISSIONS = (
    ("control.manage", "مدیریت پرسنل و دسترسی‌ها", "ورود و اعمال تغییر در کنسول کنترل", "مدیریت"),
    ("planning.manage", "برنامه‌ریزی و بودجه", "مدیریت سناریوها و بودجه‌های داخلی", "مدیریت"),
    ("organization.manage", "ساختار سازمانی", "مدیریت ساختار تیم و پیشنهادهای سازمانی", "مدیریت"),
    ("reports.full", "گزارش‌های کامل", "مشاهده گزارش‌های مدیریتی بدون محدودیت فروشنده", "گزارش"),
    ("seller.workspace", "میزکار فروشنده", "دسترسی به مسیر، مشتری و پیش‌ویزیت فروشنده", "فروش"),
    ("warehouse.assistant.view", "مشاهده دستیار انبار", "ورود به ماژول مستقل دستیار انبار", "انبار"),
    ("warehouse.order.suggest", "پیشنهاد سفارش انبار", "محاسبه پیشنهاد تجدید موجودی بدون ثبت عملیاتی", "انبار"),
    ("warehouse.order.draft", "پیش‌نویس سفارش انبار", "ساخت و ویرایش پیش‌نویس سفارش تأمین", "انبار"),
    ("warehouse.data.refresh", "به‌روزرسانی داده انبار", "همگام‌سازی فقط‌خواندنی موجودی و روند خروج از ورانگر", "انبار"),
)
ADMIN_ROLES = {"admin", "administrator", "مدیر", "مدیر سیستم", "مدیر سامانه"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
CODE_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,80}$")
PERMISSION_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{1,99}$")
PERSONNEL_DIRECTORY_COLUMNS = (
    ("personnel_code", "کد پرسنلی", "PersCode"),
    ("personnel_id", "شناسه رکورد", "ID"),
    ("full_name", "نام کامل", "FullName"),
    ("first_name", "نام", "FirstName"),
    ("last_name", "نام خانوادگی", "LastName"),
    ("status_title", "وضعیت در ورانگر", "StatusTitle"),
    ("personnel_type", "نوع پرسنل", "PersTypeTitle"),
    ("mobile", "موبایل", "PersMobile"),
)
MAX_PERSONNEL_DIRECTORY_ROWS = 100_000
PERSONNEL_DIRECTORY_KEYS = frozenset(column[0] for column in PERSONNEL_DIRECTORY_COLUMNS)
PERSONNEL_VIEW_PAGE_SIZES = frozenset({50, 100, 500, 1000})
PERSONNEL_VIEW_STATUS_FILTERS = frozenset({"all", "active", "inactive"})
CONTROL_BRANCHES = (
    ("alborz", "البرز"),
    ("tehran", "تهران"),
    ("qazvin", "قزوین"),
    ("rasht", "رشت"),
    ("headquarters", "ستاد"),
)
CONTROL_BRANCH_CODES = frozenset(branch[0] for branch in CONTROL_BRANCHES)


class ControlError(ValueError):
    pass


class ControlConflict(ControlError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _legacy_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.casefold().encode("utf-8")).hexdigest()[:20]
    return f"{prefix}-{digest}"


def _clean(value: Any, field: str, *, required: bool = False, limit: int = 200) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise ControlError(f"{field} الزامی است.")
    if len(result) > limit:
        raise ControlError(f"{field} بیش از حد طولانی است.")
    return result


def _bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    return bool(value)


def _ensure_defaults_conn(conn: Any) -> None:
    now = _now()
    conn.executemany(
        """INSERT INTO control_permissions
           (key, title, description, category, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET
             title=excluded.title, description=excluded.description,
             category=excluded.category, updated_at=excluded.updated_at""",
        [(*permission, now, now) for permission in PERMISSIONS],
    )
    users = conn.execute(
        """SELECT username, personnel_id, full_name, role, branch, sales_line, phone, active
           FROM users ORDER BY username COLLATE NOCASE"""
    ).fetchall()
    for user in users:
        username = str(user["username"])
        role = str(user["role"] or "").strip() or "بدون سمت"
        position_id = _legacy_id("position", role)
        position_code = f"legacy-{hashlib.sha256(role.casefold().encode('utf-8')).hexdigest()[:12]}"
        conn.execute(
            """INSERT OR IGNORE INTO control_positions
               (id, code, title, description, active, revision, created_at, updated_at)
               VALUES (?, ?, ?, '', 1, 1, ?, ?)""",
            (position_id, position_code, role, now, now),
        )
        role_key = role.casefold()
        defaults: tuple[str, ...] = ()
        if username.casefold() == "admin" or role_key in ADMIN_ROLES:
            defaults = ("control.manage", "planning.manage", "organization.manage", "reports.full")
        elif role_key == "فروشنده":
            defaults = ("seller.workspace",)
        conn.executemany(
            """INSERT OR IGNORE INTO control_position_permissions
               (position_id, permission_key, created_at) VALUES (?, ?, ?)""",
            [(position_id, key, now) for key in defaults],
        )
        personnel_value = user["personnel_id"]
        person_id = (
            f"personnel-{int(personnel_value)}"
            if personnel_value is not None
            else _legacy_id("user", username)
        )
        personnel_code = str(personnel_value) if personnel_value is not None else username
        conn.execute(
            """INSERT OR IGNORE INTO control_personnel
               (id, personnel_code, full_name, position_id, username, phone, branch,
                sales_line, active, source, revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'local', 1, ?, ?)""",
            (
                person_id,
                personnel_code,
                str(user["full_name"] or username),
                position_id,
                username,
                str(user["phone"] or ""),
                str(user["branch"] or ""),
                str(user["sales_line"] or ""),
                int(bool(user["active"])),
                now,
                now,
            ),
        )


def ensure_control_defaults(settings: Any) -> None:
    with sqlite_connection(settings.sqlite_path) as conn:
        _ensure_defaults_conn(conn)


def personnel_directory(settings: Any) -> dict[str, Any]:
    """Return the complete canonical Varanegar personnel view without writing to it."""
    page_size = max(1, min(int(settings.sql_max_rows), 1000))
    select_list = ",\n  ".join(
        f"{source} AS {key}" for key, _title, source in PERSONNEL_DIRECTORY_COLUMNS
    )
    rows: list[dict[str, Any]] = []
    offset = 0
    truncated = False
    while offset < MAX_PERSONNEL_DIRECTORY_ROWS:
        sql = f"""SELECT
  {select_list}
FROM GNR.vwPersonnel
ORDER BY ID
OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY"""
        result = execute_query(settings, validate_read_only_sql(sql))
        result_columns = [str(column) for column in result["columns"]]
        batch = [dict(zip(result_columns, values)) for values in result["rows"]]
        rows.extend(
            {
                key: source_row.get(key)
                for key, _title, _source in PERSONNEL_DIRECTORY_COLUMNS
            }
            for source_row in batch
        )
        if len(batch) < page_size:
            break
        offset += len(batch)
    else:
        truncated = True
    return {
        "columns": [
            {"key": key, "title": title, "source": source}
            for key, title, source in PERSONNEL_DIRECTORY_COLUMNS
        ],
        "rows": rows,
        "row_count": len(rows),
        "source": "GNR.vwPersonnel",
        "read_only": True,
        "truncated": truncated,
        "fetched_at": _now(),
    }


def permission_keys_for_user(settings: Any, username: str) -> list[str]:
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT cpp.permission_key
               FROM control_personnel cp
               JOIN control_positions pos ON pos.id=cp.position_id
               JOIN control_position_permissions cpp ON cpp.position_id=pos.id
               WHERE cp.username=? AND cp.active=1 AND cp.deleted_at IS NULL
                 AND pos.active=1 AND pos.deleted_at IS NULL
               ORDER BY cpp.permission_key""",
            (username,),
        ).fetchall()
    return [str(row["permission_key"]) for row in rows]


def position_for_user(settings: Any, username: str) -> dict[str, str] | None:
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            """SELECT pos.id, pos.code, pos.title
               FROM control_personnel cp
               JOIN control_positions pos ON pos.id=cp.position_id
               WHERE cp.username=? AND cp.deleted_at IS NULL AND pos.deleted_at IS NULL""",
            (username,),
        ).fetchone()
    return dict(row) if row else None


def can_manage_control(settings: Any, username: str) -> bool:
    if username.casefold() == "admin":
        return True
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute("SELECT role FROM users WHERE username=? AND active=1", (username,)).fetchone()
    if row and str(row["role"] or "").strip().casefold() in ADMIN_ROLES:
        return True
    return "control.manage" in permission_keys_for_user(settings, username)


def control_snapshot(settings: Any, username: str) -> dict[str, Any]:
    with sqlite_connection(settings.sqlite_path) as conn:
        _ensure_defaults_conn(conn)
        permission_rows = conn.execute(
            "SELECT key, title, description, category FROM control_permissions ORDER BY category, title"
        ).fetchall()
        position_rows = conn.execute(
            """SELECT * FROM control_positions WHERE deleted_at IS NULL
               ORDER BY active DESC, title COLLATE NOCASE"""
        ).fetchall()
        personnel_rows = conn.execute(
            """SELECT cp.*, pos.title AS position_title
               FROM control_personnel cp
               JOIN control_positions pos ON pos.id=cp.position_id
               WHERE cp.deleted_at IS NULL
               ORDER BY cp.active DESC, cp.full_name COLLATE NOCASE"""
        ).fetchall()
        permission_links = conn.execute(
            """SELECT position_id, permission_key FROM control_position_permissions
               ORDER BY permission_key"""
        ).fetchall()
        personnel_view_rows = conn.execute(
            """SELECT id, name, is_default, page_size, status_filter,
                      visible_columns_json, filters_json, revision, created_at, updated_at
               FROM control_personnel_views
               WHERE username=? AND deleted_at IS NULL
               ORDER BY is_default DESC, name COLLATE NOCASE""",
            (username,),
        ).fetchall()
        branch_assignment_rows = conn.execute(
            """SELECT personnel_id, branch_code
               FROM control_branch_assignments ORDER BY personnel_id"""
        ).fetchall()
        branch_revision = int(
            conn.execute(
                "SELECT revision FROM control_branch_assignment_state WHERE id=1"
            ).fetchone()["revision"]
        )
        revision = conn.execute("SELECT COALESCE(MAX(id), 0) AS value FROM control_audit").fetchone()["value"]
    by_position: dict[str, list[str]] = {}
    for link in permission_links:
        by_position.setdefault(str(link["position_id"]), []).append(str(link["permission_key"]))
    positions = []
    for row in position_rows:
        item = dict(row)
        item["active"] = bool(item["active"])
        item["permission_keys"] = by_position.get(str(item["id"]), [])
        positions.append(item)
    personnel = []
    for row in personnel_rows:
        item = dict(row)
        item["active"] = bool(item["active"])
        personnel.append(item)
    personnel_views = []
    allowed_directory_columns = {item[0] for item in PERSONNEL_DIRECTORY_COLUMNS}
    for row in personnel_view_rows:
        item = dict(row)
        item["is_default"] = bool(item["is_default"])
        visible_columns = json.loads(str(item.pop("visible_columns_json")))
        filters = json.loads(str(item.pop("filters_json")))
        item["visible_columns"] = [
            key for key in visible_columns if key in allowed_directory_columns
        ] or [column[0] for column in PERSONNEL_DIRECTORY_COLUMNS]
        item["filters"] = {
            key: value for key, value in filters.items()
            if key in allowed_directory_columns
        }
        personnel_views.append(item)
    personnel_by_branch: dict[str, list[int]] = {code: [] for code, _title in CONTROL_BRANCHES}
    for row in branch_assignment_rows:
        branch_code = str(row["branch_code"])
        if branch_code in personnel_by_branch:
            personnel_by_branch[branch_code].append(int(row["personnel_id"]))
    branch_rosters = [
        {
            "code": code,
            "title": title,
            "personnel_ids": personnel_by_branch[code],
            "revision": branch_revision,
        }
        for code, title in CONTROL_BRANCHES
    ]
    return {
        "current_user": username,
        "revision": int(revision),
        "permissions": [dict(row) for row in permission_rows],
        "positions": positions,
        "personnel": personnel,
        "personnel_views": personnel_views,
        "branch_rosters": branch_rosters,
    }


def _assert_revision(row: Any, base_revision: int, label: str) -> None:
    current = int(row["revision"])
    if current != base_revision:
        raise ControlConflict(f"{label} از دستگاه دیگری تغییر کرده است؛ اطلاعات را تازه‌سازی کنید.")


def _upsert_position(conn: Any, operation: dict[str, Any], now: str) -> dict[str, Any]:
    entity_id = operation["entity_id"]
    payload = operation["payload"]
    code = _clean(payload.get("code"), "کد سمت", required=True, limit=80)
    if not CODE_PATTERN.fullmatch(code):
        raise ControlError("کد سمت فقط می‌تواند شامل حروف لاتین، عدد، نقطه، خط تیره یا زیرخط باشد.")
    title = _clean(payload.get("title"), "عنوان سمت", required=True)
    description = _clean(payload.get("description"), "شرح سمت", limit=1000)
    active = _bool(payload.get("active"))
    row = conn.execute("SELECT * FROM control_positions WHERE id=?", (entity_id,)).fetchone()
    if row is None:
        if int(operation["base_revision"]) != 0:
            raise ControlConflict("سمت مورد نظر دیگر وجود ندارد.")
        revision = 1
        conn.execute(
            """INSERT INTO control_positions
               (id, code, title, description, active, revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (entity_id, code, title, description, int(active), revision, now, now),
        )
    else:
        _assert_revision(row, int(operation["base_revision"]), "سمت")
        revision = int(row["revision"]) + 1
        conn.execute(
            """UPDATE control_positions SET code=?, title=?, description=?, active=?,
                 revision=?, updated_at=?, deleted_at=NULL WHERE id=?""",
            (code, title, description, int(active), revision, now, entity_id),
        )
        conn.execute(
            """UPDATE users SET role=?, updated_at=? WHERE username IN
               (SELECT username FROM control_personnel WHERE position_id=? AND username IS NOT NULL)""",
            (title, now, entity_id),
        )
    return {"revision": revision}


def _replace_position_permissions(conn: Any, operation: dict[str, Any], now: str) -> dict[str, Any]:
    entity_id = operation["entity_id"]
    row = conn.execute(
        "SELECT * FROM control_positions WHERE id=? AND deleted_at IS NULL", (entity_id,)
    ).fetchone()
    if row is None:
        raise ControlError("سمت مورد نظر پیدا نشد.")
    _assert_revision(row, int(operation["base_revision"]), "دسترسی‌های سمت")
    keys = operation["payload"].get("permission_keys", [])
    if not isinstance(keys, list) or len(keys) > 100:
        raise ControlError("فهرست دسترسی‌ها نامعتبر است.")
    normalized = sorted({_clean(key, "دسترسی", required=True, limit=100) for key in keys})
    if any(not PERMISSION_PATTERN.fullmatch(key) for key in normalized):
        raise ControlError("شناسه دسترسی نامعتبر است.")
    existing = {
        str(item["key"])
        for item in conn.execute("SELECT key FROM control_permissions").fetchall()
    }
    unknown = [key for key in normalized if key not in existing]
    if unknown:
        raise ControlError(f"دسترسی ناشناخته است: {unknown[0]}")
    conn.execute("DELETE FROM control_position_permissions WHERE position_id=?", (entity_id,))
    conn.executemany(
        """INSERT INTO control_position_permissions
           (position_id, permission_key, created_at) VALUES (?, ?, ?)""",
        [(entity_id, key, now) for key in normalized],
    )
    revision = int(row["revision"]) + 1
    conn.execute(
        "UPDATE control_positions SET revision=?, updated_at=? WHERE id=?",
        (revision, now, entity_id),
    )
    return {"revision": revision, "permission_keys": normalized}


def _upsert_personnel(conn: Any, operation: dict[str, Any], now: str) -> dict[str, Any]:
    entity_id = operation["entity_id"]
    payload = operation["payload"]
    personnel_code = _clean(payload.get("personnel_code"), "کد پرسنلی", required=True, limit=80)
    full_name = _clean(payload.get("full_name"), "نام و نام خانوادگی", required=True)
    position_id = _clean(payload.get("position_id"), "سمت", required=True, limit=100)
    username = _clean(payload.get("username"), "نام کاربری", limit=100) or None
    phone = _clean(payload.get("phone"), "شماره تماس", limit=30)
    branch = _clean(payload.get("branch"), "شعبه", limit=200)
    sales_line = _clean(payload.get("sales_line"), "لاین فروش", limit=200)
    active = _bool(payload.get("active"))
    position = conn.execute(
        "SELECT title FROM control_positions WHERE id=? AND deleted_at IS NULL", (position_id,)
    ).fetchone()
    if position is None:
        raise ControlError("سمت انتخاب‌شده پیدا نشد.")
    if username:
        user = conn.execute("SELECT username FROM users WHERE username=?", (username,)).fetchone()
        if user is None:
            raise ControlError("نام کاربری باید از قبل در سامانه ساخته شده باشد.")
        username = str(user["username"])
    row = conn.execute("SELECT * FROM control_personnel WHERE id=?", (entity_id,)).fetchone()
    if row is None:
        if int(operation["base_revision"]) != 0:
            raise ControlConflict("پرسنل مورد نظر دیگر وجود ندارد.")
        revision = 1
        conn.execute(
            """INSERT INTO control_personnel
               (id, personnel_code, full_name, position_id, username, phone, branch,
                sales_line, active, source, revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'local', ?, ?, ?)""",
            (
                entity_id, personnel_code, full_name, position_id, username, phone,
                branch, sales_line, int(active), revision, now, now,
            ),
        )
    else:
        _assert_revision(row, int(operation["base_revision"]), "اطلاعات پرسنل")
        old_username = str(row["username"] or "")
        if old_username and username != old_username:
            raise ControlError("نام کاربری متصل‌شده قابل جابه‌جایی نیست.")
        revision = int(row["revision"]) + 1
        conn.execute(
            """UPDATE control_personnel SET personnel_code=?, full_name=?, position_id=?,
                 username=?, phone=?, branch=?, sales_line=?, active=?, revision=?,
                 updated_at=?, deleted_at=NULL WHERE id=?""",
            (
                personnel_code, full_name, position_id, username, phone, branch,
                sales_line, int(active), revision, now, entity_id,
            ),
        )
    if username:
        conn.execute(
            """UPDATE users SET full_name=?, role=?, branch=?, sales_line=?, phone=?,
                 active=?, updated_at=? WHERE username=?""",
            (full_name, str(position["title"]), branch, sales_line, phone, int(active), now, username),
        )
    return {"revision": revision}


def _personnel_view_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = _clean(payload.get("name"), "نام طرح نمایش", required=True, limit=100)
    try:
        page_size = int(payload.get("page_size", 50))
    except (TypeError, ValueError) as exc:
        raise ControlError("تعداد نمایش در صفحه نامعتبر است.") from exc
    if page_size not in PERSONNEL_VIEW_PAGE_SIZES:
        raise ControlError("تعداد نمایش در صفحه باید یکی از ۵۰، ۱۰۰، ۵۰۰ یا ۱۰۰۰ باشد.")
    status_filter = _clean(
        payload.get("status_filter") or "all", "فیلتر وضعیت", required=True, limit=20
    )
    if status_filter not in PERSONNEL_VIEW_STATUS_FILTERS:
        raise ControlError("فیلتر وضعیت طرح نامعتبر است.")
    raw_columns = payload.get("visible_columns")
    if not isinstance(raw_columns, list) or not 1 <= len(raw_columns) <= len(PERSONNEL_DIRECTORY_KEYS):
        raise ControlError("حداقل یک ستون معتبر باید در طرح نمایش باقی بماند.")
    visible_columns: list[str] = []
    for value in raw_columns:
        key = _clean(value, "ستون طرح", required=True, limit=80)
        if key not in PERSONNEL_DIRECTORY_KEYS:
            raise ControlError(f"ستون ناشناخته است: {key}")
        if key not in visible_columns:
            visible_columns.append(key)
    raw_filters = payload.get("filters") or {}
    if not isinstance(raw_filters, dict) or len(raw_filters) > len(PERSONNEL_DIRECTORY_KEYS):
        raise ControlError("فیلترهای ستون‌ها نامعتبر است.")
    filters: dict[str, str] = {}
    for raw_key, raw_value in raw_filters.items():
        key = _clean(raw_key, "ستون فیلتر", required=True, limit=80)
        if key not in PERSONNEL_DIRECTORY_KEYS:
            raise ControlError(f"ستون فیلتر ناشناخته است: {key}")
        value = _clean(raw_value, "مقدار فیلتر", limit=200)
        if value:
            filters[key] = value
    return {
        "name": name,
        "is_default": _bool(payload.get("is_default"), default=False),
        "page_size": page_size,
        "status_filter": status_filter,
        "visible_columns": visible_columns,
        "filters": filters,
    }


def _upsert_personnel_view(
    conn: Any, operation: dict[str, Any], username: str, now: str
) -> dict[str, Any]:
    entity_id = operation["entity_id"]
    values = _personnel_view_payload(operation["payload"])
    row = conn.execute(
        "SELECT * FROM control_personnel_views WHERE id=?", (entity_id,)
    ).fetchone()
    if row is not None and str(row["username"]).casefold() != username.casefold():
        raise ControlError("طرح نمایش مورد نظر پیدا نشد.")
    recycled = None
    if row is None:
        recycled = conn.execute(
            """SELECT * FROM control_personnel_views
               WHERE username=? AND name=? AND deleted_at IS NOT NULL""",
            (username, values["name"]),
        ).fetchone()
    if values["is_default"]:
        conn.execute(
            """UPDATE control_personnel_views
               SET is_default=0, revision=revision+1, updated_at=?
               WHERE username=? AND id<>? AND is_default=1 AND deleted_at IS NULL""",
            (now, username, entity_id),
        )
    columns_json = json.dumps(values["visible_columns"], ensure_ascii=False, separators=(",", ":"))
    filters_json = json.dumps(values["filters"], ensure_ascii=False, separators=(",", ":"))
    if row is None and recycled is not None:
        if int(operation["base_revision"]) != 0:
            raise ControlConflict("طرح نمایش مورد نظر دیگر وجود ندارد.")
        revision = int(recycled["revision"]) + 1
        conn.execute(
            """UPDATE control_personnel_views
               SET id=?, name=?, is_default=?, page_size=?, status_filter=?,
                   visible_columns_json=?, filters_json=?, revision=?,
                   updated_at=?, deleted_at=NULL
               WHERE id=? AND username=?""",
            (
                entity_id, values["name"], int(values["is_default"]),
                values["page_size"], values["status_filter"], columns_json,
                filters_json, revision, now, str(recycled["id"]), username,
            ),
        )
    elif row is None:
        if int(operation["base_revision"]) != 0:
            raise ControlConflict("طرح نمایش مورد نظر دیگر وجود ندارد.")
        revision = 1
        conn.execute(
            """INSERT INTO control_personnel_views
               (id, username, name, is_default, page_size, status_filter,
                visible_columns_json, filters_json, revision, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity_id, username, values["name"], int(values["is_default"]),
                values["page_size"], values["status_filter"], columns_json,
                filters_json, revision, now, now,
            ),
        )
    else:
        _assert_revision(row, int(operation["base_revision"]), "طرح نمایش")
        revision = int(row["revision"]) + 1
        conn.execute(
            """UPDATE control_personnel_views
               SET name=?, is_default=?, page_size=?, status_filter=?,
                   visible_columns_json=?, filters_json=?, revision=?,
                   updated_at=?, deleted_at=NULL
               WHERE id=? AND username=?""",
            (
                values["name"], int(values["is_default"]), values["page_size"],
                values["status_filter"], columns_json, filters_json, revision,
                now, entity_id, username,
            ),
        )
    return {"revision": revision}


def _replace_branch_roster(
    conn: Any, operation: dict[str, Any], username: str, now: str
) -> dict[str, Any]:
    branch_code = operation["entity_id"]
    if branch_code not in CONTROL_BRANCH_CODES:
        raise ControlError("شعبه انتخاب‌شده معتبر نیست.")
    raw_ids = operation["payload"].get("personnel_ids")
    if not isinstance(raw_ids, list) or len(raw_ids) > MAX_PERSONNEL_DIRECTORY_ROWS:
        raise ControlError("فهرست پرسنل شعبه نامعتبر است.")
    personnel_ids: list[int] = []
    for raw_id in raw_ids:
        if isinstance(raw_id, bool):
            raise ControlError("شناسه پرسنل شعبه نامعتبر است.")
        try:
            personnel_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise ControlError("شناسه پرسنل شعبه نامعتبر است.") from exc
        if personnel_id < 0 or personnel_id > 2_147_483_647:
            raise ControlError("شناسه پرسنل شعبه نامعتبر است.")
        if personnel_id not in personnel_ids:
            personnel_ids.append(personnel_id)
    state = conn.execute(
        "SELECT revision FROM control_branch_assignment_state WHERE id=1"
    ).fetchone()
    current_revision = int(state["revision"])
    if current_revision != int(operation["base_revision"]):
        raise ControlConflict(
            "تخصیص پرسنل شعب از دستگاه دیگری تغییر کرده است؛ اطلاعات را تازه‌سازی کنید."
        )
    conn.execute("DELETE FROM control_branch_assignments WHERE branch_code=?", (branch_code,))
    conn.executemany(
        """INSERT INTO control_branch_assignments
           (personnel_id, branch_code, assigned_by, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(personnel_id) DO UPDATE SET
             branch_code=excluded.branch_code,
             assigned_by=excluded.assigned_by,
             updated_at=excluded.updated_at""",
        [(personnel_id, branch_code, username, now) for personnel_id in personnel_ids],
    )
    revision = current_revision + 1
    conn.execute(
        """UPDATE control_branch_assignment_state
           SET revision=?, updated_by=?, updated_at=? WHERE id=1""",
        (revision, username, now),
    )
    return {"revision": revision, "personnel_count": len(personnel_ids)}


def _delete_entity(conn: Any, operation: dict[str, Any], username: str, now: str) -> dict[str, Any]:
    entity = operation["entity"]
    entity_id = operation["entity_id"]
    if entity == "personnel_view":
        row = conn.execute(
            "SELECT * FROM control_personnel_views WHERE id=? AND username=?",
            (entity_id, username),
        ).fetchone()
        if row is None:
            raise ControlError("طرح نمایش مورد نظر پیدا نشد.")
        _assert_revision(row, int(operation["base_revision"]), "طرح نمایش")
        revision = int(row["revision"]) + 1
        conn.execute(
            """UPDATE control_personnel_views
               SET is_default=0, revision=?, updated_at=?, deleted_at=?
               WHERE id=? AND username=?""",
            (revision, now, now, entity_id, username),
        )
        return {"revision": revision, "deleted": True}
    if entity == "position":
        row = conn.execute("SELECT * FROM control_positions WHERE id=?", (entity_id,)).fetchone()
        if row is None:
            raise ControlError("سمت مورد نظر پیدا نشد.")
        _assert_revision(row, int(operation["base_revision"]), "سمت")
        assigned = conn.execute(
            "SELECT 1 FROM control_personnel WHERE position_id=? AND deleted_at IS NULL LIMIT 1",
            (entity_id,),
        ).fetchone()
        if assigned:
            raise ControlError("تا زمانی که پرسنل به این سمت متصل‌اند، حذف آن ممکن نیست.")
        revision = int(row["revision"]) + 1
        conn.execute(
            """UPDATE control_positions SET active=0, revision=?, updated_at=?, deleted_at=?
               WHERE id=?""",
            (revision, now, now, entity_id),
        )
        return {"revision": revision, "deleted": True}
    if entity == "personnel":
        row = conn.execute("SELECT * FROM control_personnel WHERE id=?", (entity_id,)).fetchone()
        if row is None:
            raise ControlError("پرسنل مورد نظر پیدا نشد.")
        _assert_revision(row, int(operation["base_revision"]), "اطلاعات پرسنل")
        if str(row["username"] or "").casefold() == username.casefold():
            raise ControlError("حذف حساب پرسنلی خودتان از همین نشست مجاز نیست.")
        revision = int(row["revision"]) + 1
        conn.execute(
            """UPDATE control_personnel SET active=0, revision=?, updated_at=?, deleted_at=?
               WHERE id=?""",
            (revision, now, now, entity_id),
        )
        if row["username"]:
            revoked_username = str(row["username"])
            conn.execute(
                "UPDATE users SET active=0, updated_at=? WHERE username=?",
                (now, revoked_username),
            )
            revoke_user_credentials_in_transaction(conn, revoked_username, now=now)
        return {"revision": revision, "deleted": True}
    raise ControlError("نوع موجودیت برای حذف پشتیبانی نمی‌شود.")


def _apply_operation(settings: Any, username: str, operation: dict[str, Any]) -> dict[str, Any]:
    operation_id = _clean(operation.get("id"), "شناسه عملیات", required=True, limit=100)
    entity = _clean(operation.get("entity"), "نوع موجودیت", required=True, limit=50)
    action = _clean(operation.get("action"), "نوع عملیات", required=True, limit=30)
    entity_id = _clean(operation.get("entity_id"), "شناسه موجودیت", required=True, limit=100)
    if not ID_PATTERN.fullmatch(operation_id) or not ID_PATTERN.fullmatch(entity_id):
        raise ControlError("شناسه عملیات یا موجودیت نامعتبر است.")
    try:
        base_revision = int(operation.get("base_revision", 0))
    except (TypeError, ValueError) as exc:
        raise ControlError("نسخه مبنا نامعتبر است.") from exc
    if base_revision < 0:
        raise ControlError("نسخه مبنا نامعتبر است.")
    payload = operation.get("payload") or {}
    if not isinstance(payload, dict):
        raise ControlError("داده عملیات نامعتبر است.")
    prepared = {
        "id": operation_id,
        "entity": entity,
        "action": action,
        "entity_id": entity_id,
        "base_revision": base_revision,
        "payload": payload,
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        # Serialize receipt lookup and mutation so two tabs replaying the same
        # operation concurrently cannot both pass the idempotency check.
        conn.execute("BEGIN IMMEDIATE")
        _ensure_defaults_conn(conn)
        receipt = conn.execute(
            "SELECT response_json FROM control_operation_receipts WHERE operation_id=?",
            (operation_id,),
        ).fetchone()
        if receipt:
            replay = json.loads(str(receipt["response_json"]))
            replay["status"] = "replayed"
            return replay
        now = _now()
        if entity == "position" and action == "upsert":
            details = _upsert_position(conn, prepared, now)
        elif entity == "position_permissions" and action == "replace":
            details = _replace_position_permissions(conn, prepared, now)
        elif entity == "personnel" and action == "upsert":
            details = _upsert_personnel(conn, prepared, now)
        elif entity == "personnel_view" and action == "upsert":
            details = _upsert_personnel_view(conn, prepared, username, now)
        elif entity == "branch_roster" and action == "replace":
            details = _replace_branch_roster(conn, prepared, username, now)
        elif action == "delete" and entity in {"position", "personnel", "personnel_view"}:
            details = _delete_entity(conn, prepared, username, now)
        else:
            raise ControlError("ترکیب موجودیت و عملیات پشتیبانی نمی‌شود.")
        response = {
            "id": operation_id,
            "status": "applied",
            "entity": entity,
            "entity_id": entity_id,
            **details,
        }
        response_json = json.dumps(response, ensure_ascii=False, separators=(",", ":"))
        conn.execute(
            """INSERT INTO control_operation_receipts
               (operation_id, username, entity, entity_id, response_json, applied_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (operation_id, username, entity, entity_id, response_json, now),
        )
        conn.execute(
            """INSERT INTO control_audit
               (operation_id, username, entity, entity_id, action, payload_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                operation_id, username, entity, entity_id, action,
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")), now,
            ),
        )
        return response


def sync_control_operations(
    settings: Any, username: str, operations: list[dict[str, Any]]
) -> dict[str, Any]:
    if not operations:
        raise ControlError("حداقل یک عملیات برای همگام‌سازی لازم است.")
    if len(operations) > 100:
        raise ControlError("در هر نوبت حداکثر ۱۰۰ عملیات قابل همگام‌سازی است.")
    results = []
    for operation in operations:
        operation_id = str(operation.get("id") or "")
        entity = str(operation.get("entity") or "")
        entity_id = str(operation.get("entity_id") or "")
        try:
            results.append(_apply_operation(settings, username, operation))
        except ControlConflict as exc:
            results.append(
                {"id": operation_id, "status": "conflict", "entity": entity,
                 "entity_id": entity_id, "detail": str(exc)}
            )
        except (ControlError, sqlite3.IntegrityError) as exc:
            detail = str(exc)
            if isinstance(exc, sqlite3.IntegrityError):
                detail = "کد، نام کاربری یا شناسه واردشده قبلاً استفاده شده است."
            results.append(
                {"id": operation_id, "status": "invalid", "entity": entity,
                 "entity_id": entity_id, "detail": detail}
            )
    return {"results": results}
