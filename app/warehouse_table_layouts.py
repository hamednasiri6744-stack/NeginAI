"""Personal display layouts only; never modifies warehouse or order data."""
from datetime import datetime, timezone
import json
from uuid import uuid4
import re

from app.warehouse_assistant_service import (
    INVENTORY_COLUMN_KEYS, TABLE_PREFERENCE_COLUMNS, WarehouseAssistantError,
    init_warehouse_store, warehouse_connection,
)

LAYOUT_COLUMNS = {
    **TABLE_PREFERENCE_COLUMNS,
    "inventory": INVENTORY_COLUMN_KEYS,
    "preorder_preview": (
        "product_code", "manufacturer_product_code", "barcode", "product_name",
        "brand", "manufacturer", "conversion_rate", "effective_procurement_qty", "physical_procurement_qty",
        "in_transit_qty", "pending_receipt_qty", "inventory_position_qty",
        "average_daily_out", "coverage_days", "unadjusted_suggested_cartons",
        "system_suggested_cartons", "final_order_cartons", "order_quantity",
        "manufacturer_price", "consumer_price", "approximate_price", "estimated_value", "group_level3", "transfer_supply",
    ),
}

_UI_TABLE_KEY = re.compile(r"ui_[a-z0-9_]{1,96}")
_UI_COLUMN_KEY = re.compile(r"[a-z][a-z0-9_]{0,95}")


def _ensure_store(settings):
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS warehouse_table_layouts (
            id TEXT PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE,
            table_key TEXT NOT NULL, name TEXT NOT NULL COLLATE NOCASE,
            is_default INTEGER NOT NULL DEFAULT 0,
            column_order_json TEXT NOT NULL, visible_columns_json TEXT NOT NULL,
            filters_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            UNIQUE(username, table_key, name))""")
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(warehouse_table_layouts)")}
        if "widths_json" not in columns:
            conn.execute("ALTER TABLE warehouse_table_layouts ADD COLUMN widths_json TEXT NOT NULL DEFAULT '{}'")


def _record(row):
    return dict(id=row["id"], table_key=row["table_key"], name=row["name"],
                is_default=bool(row["is_default"]),
                column_order=json.loads(row["column_order_json"]),
                visible_columns=json.loads(row["visible_columns_json"]),
                filters=json.loads(row["filters_json"]), widths=json.loads(row["widths_json"]),
                updated_at=row["updated_at"])


def list_layouts(settings, username):
    _ensure_store(settings)
    with warehouse_connection(settings) as conn:
        return [_record(row) for row in conn.execute(
            "SELECT * FROM warehouse_table_layouts WHERE username=? ORDER BY table_key, name",
            (username,),
        )]


def save_layout(settings, username, table_key, *, name, is_default=False,
                column_order, visible_columns, filters, widths=None):
    widths = {} if widths is None else widths
    allowed = LAYOUT_COLUMNS.get(table_key)
    # Tables inside editors and previews are registered by the UI. They contain
    # display preferences only; keep their keys tightly bounded and user-scoped.
    if allowed is None and _UI_TABLE_KEY.fullmatch(table_key or ""):
        requested = [*column_order, *visible_columns, *filters.keys(), *widths.keys()]
        if (not requested or len(set(requested)) > 80
                or any(not isinstance(key, str) or not _UI_COLUMN_KEY.fullmatch(key) for key in requested)):
            raise WarehouseAssistantError("ستون‌های طرح نمایش معتبر نیستند.")
        allowed = tuple(dict.fromkeys([*column_order, *visible_columns]))
    name = name.strip()
    if not allowed or not name or len(name) > 100:
        raise WarehouseAssistantError("نام طرح یا جدول معتبر نیست.")
    if not column_order or not visible_columns or any(
        key not in allowed for key in [*column_order, *visible_columns]
    ):
        raise WarehouseAssistantError("ستون‌های طرح نمایش معتبر نیستند.")
    if len(filters) > len(allowed) or any(
        key not in allowed or not isinstance(value, str) or len(value) > 200
        for key, value in filters.items()
    ):
        raise WarehouseAssistantError("فیلترهای طرح نمایش معتبر نیستند.")
    if not isinstance(widths, dict) or len(widths) > len(allowed) or any(
        key not in allowed or type(value) is not int or not 56 <= value <= 640
        for key, value in widths.items()
    ):
        raise WarehouseAssistantError("عرض ستون‌های طرح نمایش معتبر نیست.")
    # Keep hidden columns in the order too; new schema columns are appended.
    order = list(dict.fromkeys([*column_order, *allowed]))
    visible = list(dict.fromkeys(visible_columns))
    _ensure_store(settings)
    now = datetime.now(timezone.utc).isoformat()
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            "SELECT id FROM warehouse_table_layouts WHERE username=? AND table_key=? AND name=?",
            (username, table_key, name),
        ).fetchone()
        identifier = existing["id"] if existing else str(uuid4())
        if is_default:
            conn.execute("UPDATE warehouse_table_layouts SET is_default=0 WHERE username=? AND table_key=?",
                         (username, table_key))
        conn.execute("""INSERT INTO warehouse_table_layouts
            (id,username,table_key,name,is_default,column_order_json,visible_columns_json,
             filters_json,created_at,updated_at,widths_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(username,table_key,name) DO UPDATE SET
            is_default=excluded.is_default,column_order_json=excluded.column_order_json,
            visible_columns_json=excluded.visible_columns_json,filters_json=excluded.filters_json,
            updated_at=excluded.updated_at,widths_json=excluded.widths_json""",
            (identifier, username, table_key, name, int(is_default), json.dumps(order),
             json.dumps(visible), json.dumps(filters), now, now, json.dumps(widths)))
        row = conn.execute("SELECT * FROM warehouse_table_layouts WHERE id=?", (identifier,)).fetchone()
        return _record(row), existing is None


def delete_layout(settings, username, table_key, identifier):
    _ensure_store(settings)
    with warehouse_connection(settings) as conn:
        return bool(conn.execute(
            "DELETE FROM warehouse_table_layouts WHERE id=? AND username=? AND table_key=?",
            (identifier, username, table_key),
        ).rowcount)
