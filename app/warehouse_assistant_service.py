"""Isolated inventory snapshot and replenishment suggestion service.

This module deliberately does not import the assistant, previsit, or Varanegar
order bridge.  It stores pilot data in a separate SQLite database and never
writes to the ERP.
"""

from __future__ import annotations

import hashlib
from app.warehouse_fulfillment import supply_position
from app.warehouse_order_receipts import pending_stock, ensure_orderable, ensure_cycle_allowed
import json
import math
import re
import sqlite3
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterator
from uuid import uuid4
from zipfile import BadZipFile, ZipFile, is_zipfile

from openpyxl import load_workbook

from app.business_time import jalali_business_date, tehran_now
from app.database import sql_connection
from app.sql_guard import validate_read_only_sql


SOURCE_SHEET = "فایل انبار"
MAX_PRODUCT_ROWS = 100_000
MAX_ARCHIVE_ENTRIES = 5_000
MAX_UNCOMPRESSED_BYTES = 1_000 * 1024 * 1024
EXCLUDED_REPLENISHMENT_DEALER_ID = 7
EXCLUDED_REPLENISHMENT_DEALER_NAME = "ایمان شریف پور"
# GNR.tblCustGroup.ID; chain-sales category IDs are not customer membership.
AMIRAN_CUSTOMER_GROUP_ID = 2
AMIRAN_CUSTOMER_GROUP_NAME = "گروه مشتری امیران"
ONLINE_WAREHOUSE_STOCK_DC_REF = 7
DEMAND_OUTLIER_MIN_AVAILABLE_DAYS = 14
DEMAND_OUTLIER_MIN_POSITIVE_DAYS = 4
DEMAND_OUTLIER_MEDIAN_MULTIPLIER = 3.0
DEMAND_OUTLIER_PERCENTILE = 0.90
DEMAND_RECURRING_PATTERN_SHARE = 0.10
DEMAND_CUSTOMER_CONCENTRATION_SHARE = 0.80
DEMAND_CUSTOMER_HISTORY_DAYS = 180
DEMAND_RECURRING_MIN_CUSTOMERS = 3
ORDER_CYCLE_STALE_DAYS = 90
LAST_STOCK_DEMAND_BASIS = "net_sales_last_stock_window"
AUTO_ORDER_DEFAULT_REORDER_DAYS = 10
AUTO_ORDER_DEFAULT_TARGET_DAYS = 20
SUPPLY_SCOPE_RECEIPT_DAYS = 90
AUTOMATIC_REFRESH_INTERVAL_SECONDS = 60 * 60
AUTOMATIC_REFRESH_LOCK_MINUTES = 30
PURCHASE_PRICE_CACHE_TTL_SECONDS = 24 * 60 * 60

WAREHOUSES: dict[str, dict[str, Any]] = {
    "karaj": {
        "name": "انبار مرکزی کرج",
        "stock_dc_ref": 1,
        "stock_dc_code": "26",
        "price_order_type_ref": 2,
        "price_order_type_name": "پیش ویزیت",
        "columns": {
            "stock": "stock karaj",
            "reserved": "reserved karaj",
            "period_out": "two month out karaj",
            "thirty_day_stock": "karaj 30 days stock",
            "sale_price": "sale price karaj",
            "manufacturer_price": "manufacturer price karaj",
            "consumer_price": "consumer price karaj",
            "buy_price": "buy price karaj",
        },
    },
    "tehran": {
        "name": "انبار تهران",
        "stock_dc_ref": 2,
        "stock_dc_code": "27",
        "price_order_type_ref": 10,
        "price_order_type_name": "پیش ویزیت تهران",
        "columns": {
            "stock": "stock tehran",
            "reserved": "reserved tehran",
            "period_out": "two month out tehran",
            "thirty_day_stock": "tehran 30 days stock",
            "sale_price": "sale price tehran",
            "manufacturer_price": "manufacturer price tehran",
            "consumer_price": "consumer price tehran",
            "buy_price": "buy price tehran",
        },
    },
    "gilan": {
        "name": "انبار گیلان",
        "stock_dc_ref": 9,
        "stock_dc_code": "34",
        "price_order_type_ref": 13,
        "price_order_type_name": "پیش ویزیت گیلان",
        "columns": {
            "stock": "stock gilan",
            "reserved": "reserved gilan",
            "period_out": "two month out gilan",
            "thirty_day_stock": "gilan 30 days stock",
            "sale_price": "sale price gilan",
            "manufacturer_price": "manufacturer price gilan",
            "consumer_price": "consumer price gilan",
            "buy_price": "buy price gilan",
        },
    },
}

INVENTORY_COLUMN_KEYS = (
    "product_code", "product_name", "warehouse_name", "manufacturer", "brand", "group_level3",
    "barcode", "manufacturer_product_code", "tax_rate", "conversion_rate", "on_hand_qty",
    "reserved_qty", "owned_procurement_qty", "open_customer_order_qty",
    "unconfirmed_free_invoice_qty", "legacy_open_order_qty", "open_order_qty",
    "pending_sale_voucher_qty", "effective_procurement_qty", "in_transit_qty", "pending_receipt_qty", "damaged_qty",
    "period_out_qty", "online_transfer_out_qty", "last_in_stock_date", "days_since_last_stock",
    "sales_window_start", "sales_window_end", "sale_price",
    "manufacturer_price", "consumer_price", "ordering_cycle_active",
)

TABLE_PREFERENCE_COLUMNS: dict[str, tuple[str, ...]] = {
    "ordering": (
        "product_code", "manufacturer_product_code", "barcode", "product_name",
        "conversion_rate", "manufacturer", "brand", "group_level3", "on_hand_qty", "reserved_qty",
        "open_order_qty", "effective_procurement_qty", "in_transit_qty", "pending_receipt_qty", "inventory_position_qty", "effective_cartons",
        "average_daily_out", "period_out_qty", "online_transfer_out_qty",
        "gross_sales_qty", "sales_return_qty",
        "excluded_seller_qty", "sales_rate_days", "stockout_days", "last_in_stock_date",
        "days_since_last_stock", "sales_window_start", "sales_window_end",
        "coverage_days", "suggested_quantity", "final_order_cartons", "transfer_supply",
    ),
    "automatic_settings": (
        "enabled", "warehouse", "supplier", "product_count", "reorder_coverage_days",
        "target_days", "minimum_cartons", "contact_first_name", "contact_last_name",
        "contact_email", "contact_mobile", "status", "actions",
    ),
    "automatic_preorders": (
        "status", "warehouse", "supplier", "preorder_number", "item_count",
        "total_cartons", "reorder_coverage_days", "target_days", "contact",
        "contact_email", "created_at", "delivery_date", "documents", "actions",
    ),
    "supply_scope": (
        "enabled", "warehouse", "supplier", "brand", "product_count",
        "receipt_count", "receipt_quantity", "last_receipt_date",
        "evidence", "updated_by",
    ),
}

INVENTORY_FILTER_SQL = {
    "tax_rate": "warehouse_tax_label(product_code)",
    "product_code": "product_code",
    "product_name": "product_name",
    "warehouse_name": "warehouse_name",
    "manufacturer": "manufacturer",
    "brand": "brand",
    "group_level3": "group_level3",
    "barcode": "barcode",
    "manufacturer_product_code": "manufacturer_product_code",
    "conversion_rate": "conversion_rate",
    "on_hand_qty": "stock",
    "reserved_qty": "reserved",
    "owned_procurement_qty": "(stock + reserved)",
    "open_customer_order_qty": "open_customer_order",
    "unconfirmed_free_invoice_qty": "unconfirmed_free_invoice",
    "legacy_open_order_qty": "legacy_open_order",
    "open_order_qty": "open_order",
    "pending_sale_voucher_qty": "pending_sale_voucher",
    "effective_procurement_qty": "(stock + reserved - open_order + warehouse_in_transit(warehouse_code, product_code) + warehouse_pending_receipt(warehouse_code, product_code))",
    "pending_receipt_qty": "warehouse_pending_receipt(warehouse_code, product_code)",
    "in_transit_qty": "warehouse_in_transit(warehouse_code, product_code)",
    "damaged_qty": "damaged",
    "period_out_qty": "period_out",
    "online_transfer_out_qty": "online_transfer_out",
    "last_in_stock_date": "last_in_stock_date",
    "days_since_last_stock": "days_since_last_stock",
    "sales_window_start": "sales_window_start",
    "sales_window_end": "sales_window_end",
    "sale_price": "sale_price",
    "manufacturer_price": "manufacturer_price",
    "consumer_price": "consumer_price",
}

ORDER_CYCLE_FORCED_SQL = """EXISTS (
  SELECT 1 FROM warehouse_order_cycle_overrides AS cycle_override
  WHERE cycle_override.warehouse_code=warehouse_snapshot_items.warehouse_code
    AND cycle_override.product_code=warehouse_snapshot_items.product_code
    AND cycle_override.forced_active=1
)"""
ORDER_CYCLE_BLOCKED_SQL = ORDER_CYCLE_FORCED_SQL.replace("forced_active=1", "forced_active=0")
EFFECTIVE_ORDER_CYCLE_SQL = (
    f"(NOT {ORDER_CYCLE_BLOCKED_SQL} AND (ordering_cycle_active = 1 OR {ORDER_CYCLE_FORCED_SQL}))"
)
INVENTORY_FILTER_SQL["ordering_cycle_active"] = (
    f"CASE WHEN {EFFECTIVE_ORDER_CYCLE_SQL} THEN 'فعال' ELSE 'خارج از چرخه' END"
)


class WarehouseAssistantError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def warehouse_database_path(settings: Any) -> Path:
    return Path(settings.sqlite_path).with_name("warehouse-assistant.db")


@contextmanager
def warehouse_connection(settings: Any) -> Iterator[sqlite3.Connection]:
    path = warehouse_database_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_warehouse_store(settings: Any) -> None:
    with warehouse_connection(settings) as conn:
        current = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).casefold()
        if current != "wal":
            conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS warehouse_snapshots (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_filename TEXT NOT NULL,
              source_sheet TEXT NOT NULL,
              content_sha256 TEXT NOT NULL UNIQUE,
              product_count INTEGER NOT NULL,
              item_count INTEGER NOT NULL,
              imported_by TEXT NOT NULL,
              imported_at TEXT NOT NULL,
              source_kind TEXT NOT NULL DEFAULT 'excel',
              period_start TEXT,
              period_end TEXT,
              period_days INTEGER,
              demand_basis TEXT NOT NULL DEFAULT 'legacy_period_out'
            );
            CREATE TABLE IF NOT EXISTS warehouse_snapshot_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              snapshot_id INTEGER NOT NULL,
              source_row INTEGER NOT NULL,
              warehouse_code TEXT NOT NULL,
              warehouse_name TEXT NOT NULL,
              product_code TEXT NOT NULL,
              product_name TEXT NOT NULL,
              conversion_rate REAL NOT NULL,
              manufacturer TEXT NOT NULL DEFAULT '',
              brand TEXT NOT NULL DEFAULT '',
              group_level3 TEXT NOT NULL DEFAULT '',
              manufacturer_product_code TEXT NOT NULL DEFAULT '',
              barcode TEXT NOT NULL DEFAULT '',
              barcode2 TEXT NOT NULL DEFAULT '',
              barcode_list TEXT NOT NULL DEFAULT '',
              stock REAL NOT NULL DEFAULT 0,
              reserved REAL NOT NULL DEFAULT 0,
              damaged REAL NOT NULL DEFAULT 0,
              undelivered REAL NOT NULL DEFAULT 0,
              open_customer_order REAL NOT NULL DEFAULT 0,
              unconfirmed_free_invoice REAL NOT NULL DEFAULT 0,
              legacy_open_order REAL NOT NULL DEFAULT 0,
              open_order REAL NOT NULL DEFAULT 0,
              pending_sale_voucher REAL NOT NULL DEFAULT 0,
              period_out REAL NOT NULL DEFAULT 0,
              raw_period_out REAL NOT NULL DEFAULT 0,
              amiran_period_out REAL NOT NULL DEFAULT 0,
              exceptional_period_out REAL NOT NULL DEFAULT 0,
              online_transfer_out REAL NOT NULL DEFAULT 0,
              demand_anomaly_days INTEGER NOT NULL DEFAULT 0,
              demand_daily_cap REAL,
              demand_recurring_pattern INTEGER NOT NULL DEFAULT 0,
              demand_recurring_pattern_days INTEGER NOT NULL DEFAULT 0,
              gross_out REAL NOT NULL DEFAULT 0,
              period_return REAL NOT NULL DEFAULT 0,
              excluded_seller_qty REAL NOT NULL DEFAULT 0,
              sales_rate_days INTEGER NOT NULL DEFAULT 0,
              stockout_days INTEGER NOT NULL DEFAULT 0,
              last_in_stock_date TEXT,
              sales_window_start TEXT,
              sales_window_end TEXT,
              days_since_last_stock INTEGER,
              ordering_cycle_active INTEGER NOT NULL DEFAULT 1,
              thirty_day_stock REAL NOT NULL DEFAULT 0,
              sale_price REAL NOT NULL DEFAULT 0,
              manufacturer_price REAL NOT NULL DEFAULT 0,
              consumer_price REAL NOT NULL DEFAULT 0,
              buy_price REAL NOT NULL DEFAULT 0,
              FOREIGN KEY(snapshot_id) REFERENCES warehouse_snapshots(id) ON DELETE CASCADE,
              UNIQUE(snapshot_id, warehouse_code, product_code)
            );
            CREATE INDEX IF NOT EXISTS idx_warehouse_items_lookup
              ON warehouse_snapshot_items(snapshot_id, warehouse_code, brand, manufacturer);
            CREATE INDEX IF NOT EXISTS idx_warehouse_items_product
              ON warehouse_snapshot_items(snapshot_id, product_code);
            CREATE TABLE IF NOT EXISTS warehouse_purchase_price_cache (
              goods_ref INTEGER PRIMARY KEY,
              approximate_price REAL NOT NULL,
              purchase_date TEXT NOT NULL DEFAULT '',
              invoice_id INTEGER,
              refreshed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS warehouse_purchase_price_cache_state (
              id INTEGER PRIMARY KEY CHECK(id=1),
              refreshed_at TEXT NOT NULL,
              source_row_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS warehouse_order_cycle_overrides (
              warehouse_code TEXT NOT NULL,
              product_code TEXT NOT NULL,
              forced_active INTEGER NOT NULL DEFAULT 1
                CHECK(forced_active IN (0, 1)),
              updated_by TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(warehouse_code, product_code)
            );
            CREATE TABLE IF NOT EXISTS warehouse_inventory_views (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL COLLATE NOCASE,
              name TEXT NOT NULL COLLATE NOCASE,
              is_default INTEGER NOT NULL DEFAULT 0,
              visible_columns_json TEXT NOT NULL,
              filters_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_warehouse_inventory_views_name
              ON warehouse_inventory_views(username, name);
            CREATE INDEX IF NOT EXISTS idx_warehouse_inventory_views_user
              ON warehouse_inventory_views(username, is_default DESC, name);
            CREATE TABLE IF NOT EXISTS warehouse_table_preferences (
              username TEXT NOT NULL COLLATE NOCASE,
              table_key TEXT NOT NULL,
              visible_columns_json TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(username, table_key)
            );
            CREATE TABLE IF NOT EXISTS warehouse_supply_scope (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              warehouse_code TEXT NOT NULL,
              warehouse_name TEXT NOT NULL,
              supplier TEXT NOT NULL COLLATE NOCASE,
              brand TEXT NOT NULL COLLATE NOCASE,
              enabled INTEGER NOT NULL DEFAULT 0,
              observed_in_recent_receipts INTEGER NOT NULL DEFAULT 0,
              receipt_count INTEGER NOT NULL DEFAULT 0,
              receipt_quantity REAL NOT NULL DEFAULT 0,
              first_receipt_date TEXT,
              last_receipt_date TEXT,
              source_supplier_refs_json TEXT NOT NULL DEFAULT '[]',
              source_supplier_names_json TEXT NOT NULL DEFAULT '[]',
              is_user_override INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              updated_by TEXT NOT NULL DEFAULT 'system',
              UNIQUE(warehouse_code, supplier, brand)
            );
            CREATE INDEX IF NOT EXISTS idx_warehouse_supply_scope_active
              ON warehouse_supply_scope(
                warehouse_code, enabled, supplier COLLATE NOCASE,
                brand COLLATE NOCASE
              );
            CREATE TABLE IF NOT EXISTS warehouse_supply_scope_state (
              id INTEGER PRIMARY KEY CHECK(id=1),
              strict_enabled INTEGER NOT NULL DEFAULT 0,
              source_kind TEXT NOT NULL,
              evidence_window_start TEXT,
              evidence_window_end TEXT,
              refreshed_at TEXT NOT NULL,
              refreshed_by TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS supplier_orders (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              order_number TEXT UNIQUE,
              snapshot_id INTEGER NOT NULL,
              warehouse_code TEXT NOT NULL,
              warehouse_name TEXT NOT NULL,
              supplier TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'prepared'
                CHECK(status IN ('prepared', 'cancelled')),
              delivery_mode TEXT NOT NULL DEFAULT 'supplier_document',
              note TEXT NOT NULL DEFAULT '',
              total_quantity REAL NOT NULL DEFAULT 0,
              estimated_value REAL NOT NULL DEFAULT 0,
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(snapshot_id) REFERENCES warehouse_snapshots(id)
            );
            CREATE TABLE IF NOT EXISTS supplier_order_lines (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              order_id INTEGER NOT NULL,
              product_code TEXT NOT NULL,
              product_name TEXT NOT NULL,
              brand TEXT NOT NULL DEFAULT '',
              conversion_rate REAL NOT NULL,
              requested_quantity REAL NOT NULL,
              order_quantity REAL NOT NULL,
              cartons INTEGER NOT NULL,
              manufacturer_price REAL NOT NULL DEFAULT 0,
              consumer_price REAL NOT NULL DEFAULT 0,
              buy_price REAL NOT NULL DEFAULT 0,
              estimated_value REAL NOT NULL DEFAULT 0,
              note TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(order_id) REFERENCES supplier_orders(id) ON DELETE CASCADE,
              UNIQUE(order_id, product_code)
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_orders_recent
              ON supplier_orders(created_at DESC, id DESC);
            CREATE TABLE IF NOT EXISTS warehouse_supplier_order_email_attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              order_id INTEGER NOT NULL REFERENCES supplier_orders(id),
              recipient TEXT NOT NULL,
              sender TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('sending','sent','failed','unknown')),
              message_id TEXT NOT NULL UNIQUE,
              attachment_sha256 TEXT NOT NULL,
              requested_by TEXT NOT NULL,
              started_at TEXT NOT NULL,
              completed_at TEXT,
              error TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_order_email_attempts_order
              ON warehouse_supplier_order_email_attempts(order_id, id DESC);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_supplier_order_email_no_duplicate
              ON warehouse_supplier_order_email_attempts(order_id)
              WHERE status IN ('sending','sent','unknown');
            CREATE TABLE IF NOT EXISTS warehouse_supplier_auto_order_settings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              warehouse_code TEXT NOT NULL,
              warehouse_name TEXT NOT NULL,
              supplier TEXT NOT NULL COLLATE NOCASE,
              enabled INTEGER NOT NULL DEFAULT 1,
              reorder_coverage_days INTEGER NOT NULL DEFAULT 10,
              target_days INTEGER NOT NULL DEFAULT 20,
              minimum_cartons INTEGER NOT NULL DEFAULT 0,
              contact_first_name TEXT NOT NULL DEFAULT '',
              contact_last_name TEXT NOT NULL DEFAULT '',
              contact_email TEXT NOT NULL DEFAULT '',
              contact_mobile TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              updated_by TEXT NOT NULL DEFAULT 'system',
              UNIQUE(warehouse_code, supplier)
            );
            CREATE INDEX IF NOT EXISTS idx_warehouse_supplier_auto_order_lookup
              ON warehouse_supplier_auto_order_settings(
                warehouse_code, supplier COLLATE NOCASE
              );
            CREATE TABLE IF NOT EXISTS warehouse_automatic_preorders (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              preorder_number TEXT UNIQUE,
              generation_key TEXT NOT NULL UNIQUE,
              snapshot_id INTEGER NOT NULL,
              supplier_setting_id INTEGER NOT NULL,
              warehouse_code TEXT NOT NULL,
              warehouse_name TEXT NOT NULL,
              supplier TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'awaiting_approval'
                CHECK(status IN (
                  'awaiting_approval', 'approved', 'send_requested',
                  'cancelled', 'superseded'
                )),
              reorder_coverage_days INTEGER NOT NULL,
              target_days INTEGER NOT NULL,
              minimum_cartons INTEGER NOT NULL DEFAULT 0,
              item_count INTEGER NOT NULL DEFAULT 0,
              total_quantity REAL NOT NULL DEFAULT 0,
              total_cartons INTEGER NOT NULL DEFAULT 0,
              estimated_value REAL NOT NULL DEFAULT 0,
              contact_first_name TEXT NOT NULL DEFAULT '',
              contact_last_name TEXT NOT NULL DEFAULT '',
              contact_email TEXT NOT NULL DEFAULT '',
              contact_mobile TEXT NOT NULL DEFAULT '',
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              business_date TEXT,
              last_refreshed_at TEXT,
              refresh_trigger TEXT NOT NULL DEFAULT 'manual',
              approved_by TEXT,
              approved_at TEXT,
              send_requested_by TEXT,
              send_requested_at TEXT,
              edited_by TEXT,
              edited_at TEXT,
              source_supplier_order_id INTEGER UNIQUE REFERENCES supplier_orders(id),
              FOREIGN KEY(snapshot_id) REFERENCES warehouse_snapshots(id),
              FOREIGN KEY(supplier_setting_id)
                REFERENCES warehouse_supplier_auto_order_settings(id)
            );
            CREATE INDEX IF NOT EXISTS idx_warehouse_automatic_preorders_queue
              ON warehouse_automatic_preorders(status, id DESC);
            CREATE INDEX IF NOT EXISTS idx_warehouse_automatic_preorders_supplier
              ON warehouse_automatic_preorders(supplier_setting_id, id DESC);
            CREATE TABLE IF NOT EXISTS warehouse_email_attempts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              preorder_id INTEGER NOT NULL REFERENCES warehouse_automatic_preorders(id),
              recipient TEXT NOT NULL,
              sender TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('sending','sent','failed','unknown')),
              message_id TEXT NOT NULL UNIQUE,
              attachment_sha256 TEXT NOT NULL,
              requested_by TEXT NOT NULL,
              started_at TEXT NOT NULL,
              completed_at TEXT,
              error TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_warehouse_email_attempts_order
              ON warehouse_email_attempts(preorder_id, id DESC);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_warehouse_email_no_duplicate
              ON warehouse_email_attempts(preorder_id)
              WHERE status IN ('sending','sent','unknown');
            CREATE TABLE IF NOT EXISTS warehouse_automatic_preorder_lines (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              preorder_id INTEGER NOT NULL,
              warehouse_code TEXT NOT NULL,
              warehouse_name TEXT NOT NULL,
              product_code TEXT NOT NULL,
              product_name TEXT NOT NULL,
              brand TEXT NOT NULL DEFAULT '',
              conversion_rate REAL NOT NULL,
              system_suggested_cartons INTEGER NOT NULL DEFAULT 0,
              unadjusted_suggested_cartons INTEGER NOT NULL DEFAULT 0,
              order_quantity REAL NOT NULL,
              cartons INTEGER NOT NULL,
              manufacturer_price REAL NOT NULL DEFAULT 0,
              consumer_price REAL NOT NULL DEFAULT 0,
              buy_price REAL NOT NULL DEFAULT 0,
              estimated_value REAL NOT NULL DEFAULT 0,
              FOREIGN KEY(preorder_id)
                REFERENCES warehouse_automatic_preorders(id) ON DELETE CASCADE,
              UNIQUE(preorder_id, warehouse_code, product_code)
            );
            CREATE TABLE IF NOT EXISTS warehouse_automatic_refresh_state (
              id INTEGER PRIMARY KEY CHECK(id=1),
              last_started_at TEXT,
              last_completed_at TEXT,
              last_success_at TEXT,
              last_trigger TEXT,
              last_error TEXT,
              last_result_json TEXT,
              lock_token TEXT,
              lock_expires_at TEXT
            );
            CREATE TABLE IF NOT EXISTS warehouse_fulfillment_receipts (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              preorder_id INTEGER NOT NULL REFERENCES warehouse_automatic_preorders(id),
              product_code TEXT NOT NULL,
              quantity REAL NOT NULL CHECK(quantity>0),
              snapshot_id INTEGER NOT NULL REFERENCES warehouse_snapshots(id),
              reference TEXT NOT NULL,
              recorded_by TEXT NOT NULL,
              recorded_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_warehouse_fulfillment_order
              ON warehouse_fulfillment_receipts(preorder_id,product_code);
            CREATE TABLE IF NOT EXISTS warehouse_checkbars (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              created_by TEXT NOT NULL,
              warehouse_code TEXT NOT NULL,
              supplier TEXT NOT NULL,
              request_id TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              document_json TEXT NOT NULL,
              UNIQUE(created_by,request_id)
            );
            CREATE TABLE IF NOT EXISTS warehouse_checkbar_revisions (
              document_id INTEGER NOT NULL REFERENCES warehouse_checkbars(id),
              revision INTEGER NOT NULL,
              operation TEXT NOT NULL CHECK(operation IN ('edit','delete')),
              created_at TEXT NOT NULL,
              created_by TEXT NOT NULL,
              request_id TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              document_json TEXT NOT NULL,
              PRIMARY KEY(document_id,revision),
              UNIQUE(document_id,created_by,request_id)
            );
            CREATE TABLE IF NOT EXISTS warehouse_checkbar_transfers (
              document_id INTEGER PRIMARY KEY REFERENCES warehouse_checkbars(id),
              transfer_key TEXT NOT NULL UNIQUE,
              revision INTEGER NOT NULL,
              requested_by TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('pending','sent','rejected')),
              result_json TEXT,
              updated_at TEXT NOT NULL
            );
            """
        )
        from app.warehouse_order_receipts import init_schema as init_receipt_schema
        init_receipt_schema(conn)
        from app.warehouse_receipt_lifecycle import init_schema as init_lifecycle_schema
        init_lifecycle_schema(conn)
        from app.warehouse_order_delivery import init_schema as init_delivery_schema
        init_delivery_schema(conn)
        from app.warehouse_rebalancing import init_schema as init_rebalance_schema
        init_rebalance_schema(conn)
        from app.warehouse_native_transit import init_schema as init_native_transit
        init_native_transit(conn)
        snapshot_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(warehouse_snapshots)")
        }
        snapshot_migrations = {
            "source_kind": "source_kind TEXT NOT NULL DEFAULT 'excel'",
            "period_start": "period_start TEXT",
            "period_end": "period_end TEXT",
            "period_days": "period_days INTEGER",
            "demand_basis": "demand_basis TEXT NOT NULL DEFAULT 'legacy_period_out'",
        }
        for column_name, definition in snapshot_migrations.items():
            if column_name not in snapshot_columns:
                conn.execute(
                    f"ALTER TABLE warehouse_snapshots ADD COLUMN {definition}"
                )
        item_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(warehouse_snapshot_items)")
        }
        item_migrations = {
            "gross_out": "gross_out REAL NOT NULL DEFAULT 0",
            "period_return": "period_return REAL NOT NULL DEFAULT 0",
            "excluded_seller_qty": "excluded_seller_qty REAL NOT NULL DEFAULT 0",
            "sales_rate_days": "sales_rate_days INTEGER NOT NULL DEFAULT 0",
            "stockout_days": "stockout_days INTEGER NOT NULL DEFAULT 0",
            "last_in_stock_date": "last_in_stock_date TEXT",
            "sales_window_start": "sales_window_start TEXT",
            "sales_window_end": "sales_window_end TEXT",
            "days_since_last_stock": "days_since_last_stock INTEGER",
            "ordering_cycle_active": "ordering_cycle_active INTEGER NOT NULL DEFAULT 1",
            "damaged": "damaged REAL NOT NULL DEFAULT 0",
            "undelivered": "undelivered REAL NOT NULL DEFAULT 0",
            "open_customer_order": "open_customer_order REAL NOT NULL DEFAULT 0",
            "unconfirmed_free_invoice": "unconfirmed_free_invoice REAL NOT NULL DEFAULT 0",
            "legacy_open_order": "legacy_open_order REAL NOT NULL DEFAULT 0",
            "open_order": "open_order REAL NOT NULL DEFAULT 0",
            "pending_sale_voucher": "pending_sale_voucher REAL NOT NULL DEFAULT 0",
            "raw_period_out": "raw_period_out REAL NOT NULL DEFAULT 0",
            "amiran_period_out": "amiran_period_out REAL NOT NULL DEFAULT 0",
            "exceptional_period_out": "exceptional_period_out REAL NOT NULL DEFAULT 0",
            "online_transfer_out": "online_transfer_out REAL NOT NULL DEFAULT 0",
            "demand_anomaly_days": "demand_anomaly_days INTEGER NOT NULL DEFAULT 0",
            "demand_daily_cap": "demand_daily_cap REAL",
            "demand_recurring_pattern": "demand_recurring_pattern INTEGER NOT NULL DEFAULT 0",
            "demand_recurring_pattern_days": "demand_recurring_pattern_days INTEGER NOT NULL DEFAULT 0",
            "manufacturer_product_code": "manufacturer_product_code TEXT NOT NULL DEFAULT ''",
            "group_level3": "group_level3 TEXT NOT NULL DEFAULT ''",
            "barcode": "barcode TEXT NOT NULL DEFAULT ''",
            "barcode2": "barcode2 TEXT NOT NULL DEFAULT ''",
            "barcode_list": "barcode_list TEXT NOT NULL DEFAULT ''",
        }
        for column_name, definition in item_migrations.items():
            if column_name not in item_columns:
                conn.execute(
                    f"ALTER TABLE warehouse_snapshot_items ADD COLUMN {definition}"
                )
        conn.execute(
            """UPDATE warehouse_snapshot_items
               SET raw_period_out=period_out
               WHERE raw_period_out=0 AND period_out<>0"""
        )
        preorder_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(warehouse_automatic_preorders)")
        }
        for column_name, definition in {
            "edited_by": "edited_by TEXT",
            "edited_at": "edited_at TEXT",
            "business_date": "business_date TEXT",
            "last_refreshed_at": "last_refreshed_at TEXT",
            "refresh_trigger": "refresh_trigger TEXT NOT NULL DEFAULT 'manual'",
            "source_supplier_order_id": "source_supplier_order_id INTEGER REFERENCES supplier_orders(id)",
        }.items():
            if column_name not in preorder_columns:
                conn.execute(
                    f"ALTER TABLE warehouse_automatic_preorders ADD COLUMN {definition}"
                )
        conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_automatic_preorder_manual_source
                        ON warehouse_automatic_preorders(source_supplier_order_id)
                        WHERE source_supplier_order_id IS NOT NULL""")
        conn.execute(
            """UPDATE warehouse_automatic_preorders
               SET business_date=COALESCE(business_date, SUBSTR(created_at, 1, 10)),
                   last_refreshed_at=COALESCE(last_refreshed_at, created_at)
               WHERE business_date IS NULL OR last_refreshed_at IS NULL"""
        )
        preorder_line_columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(warehouse_automatic_preorder_lines)"
            )
        }
        if "system_suggested_cartons" not in preorder_line_columns:
            conn.execute(
                "ALTER TABLE warehouse_automatic_preorder_lines "
                "ADD COLUMN system_suggested_cartons INTEGER NOT NULL DEFAULT 0"
            )
            conn.execute(
                "UPDATE warehouse_automatic_preorder_lines "
                "SET system_suggested_cartons=cartons"
            )
        if "unadjusted_suggested_cartons" not in preorder_line_columns:
            conn.execute(
                "ALTER TABLE warehouse_automatic_preorder_lines "
                "ADD COLUMN unadjusted_suggested_cartons INTEGER NOT NULL DEFAULT 0"
            )
            conn.execute(
                "UPDATE warehouse_automatic_preorder_lines "
                "SET unadjusted_suggested_cartons=system_suggested_cartons"
            )
        for column_name in ("manufacturer_price", "consumer_price"):
            if column_name not in preorder_line_columns:
                conn.execute(
                    "ALTER TABLE warehouse_automatic_preorder_lines "
                    f"ADD COLUMN {column_name} REAL NOT NULL DEFAULT 0"
                )
                conn.execute(
                    f"""UPDATE warehouse_automatic_preorder_lines
                        SET {column_name}=COALESCE((
                          SELECT item.{column_name}
                          FROM warehouse_automatic_preorders AS preorder
                          INNER JOIN warehouse_snapshot_items AS item
                                  ON item.snapshot_id=preorder.snapshot_id
                                 AND item.warehouse_code=
                                     warehouse_automatic_preorder_lines.warehouse_code
                                 AND item.product_code=
                                     warehouse_automatic_preorder_lines.product_code
                          WHERE preorder.id=
                                warehouse_automatic_preorder_lines.preorder_id
                          LIMIT 1
                        ), 0)"""
                )
        supplier_line_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(supplier_order_lines)")
        }
        for column_name in ("manufacturer_price", "consumer_price"):
            if column_name not in supplier_line_columns:
                conn.execute(
                    "ALTER TABLE supplier_order_lines "
                    f"ADD COLUMN {column_name} REAL NOT NULL DEFAULT 0"
                )
                conn.execute(
                    f"""UPDATE supplier_order_lines
                        SET {column_name}=COALESCE((
                          SELECT item.{column_name}
                          FROM supplier_orders AS supplier_order
                          INNER JOIN warehouse_snapshot_items AS item
                                  ON item.snapshot_id=supplier_order.snapshot_id
                                 AND item.warehouse_code=
                                     supplier_order.warehouse_code
                                 AND item.product_code=
                                     supplier_order_lines.product_code
                          WHERE supplier_order.id=supplier_order_lines.order_id
                          LIMIT 1
                        ), 0)"""
                )
        supplier_order_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(supplier_orders)")
        }
        for column_name, definition in {
            "approved_by": "approved_by TEXT",
            "approved_at": "approved_at TEXT",
            "edited_by": "edited_by TEXT",
            "edited_at": "edited_at TEXT",
            "receipt_review_override_by": "receipt_review_override_by TEXT",
            "receipt_review_override_at": "receipt_review_override_at TEXT",
            "receipt_review_override_reason": "receipt_review_override_reason TEXT NOT NULL DEFAULT ''",
        }.items():
            if column_name not in supplier_order_columns:
                conn.execute(f"ALTER TABLE supplier_orders ADD COLUMN {definition}")
        for table_name, warehouse_expression, parent_table, parent_key in (
            (
                "warehouse_automatic_preorder_lines",
                "warehouse_automatic_preorder_lines.warehouse_code",
                "warehouse_automatic_preorders",
                "preorder_id",
            ),
            (
                "supplier_order_lines",
                "(SELECT supplier_order.warehouse_code FROM supplier_orders "
                "AS supplier_order WHERE supplier_order.id="
                "supplier_order_lines.order_id)",
                "supplier_orders",
                "order_id",
            ),
        ):
            for column_name in (
                "manufacturer_price",
                "consumer_price",
                "buy_price",
            ):
                conn.execute(
                    f"""UPDATE {table_name}
                        SET {column_name}=COALESCE(NULLIF({column_name}, 0), (
                          SELECT item.{column_name}
                          FROM warehouse_snapshot_items AS item
                          WHERE item.snapshot_id=(
                                  SELECT MAX(id) FROM warehouse_snapshots
                                )
                            AND item.warehouse_code={warehouse_expression}
                            AND item.product_code={table_name}.product_code
                            AND item.{column_name}>0
                          LIMIT 1
                        ), 0)
                        WHERE {column_name}=0"""
                )
            conn.execute(
                f"""UPDATE {table_name}
                    SET estimated_value=order_quantity*buy_price
                    WHERE estimated_value<>order_quantity*buy_price"""
            )
            conn.execute(
                f"""UPDATE {parent_table}
                    SET estimated_value=COALESCE((
                      SELECT SUM(line.estimated_value)
                      FROM {table_name} AS line
                      WHERE line.{parent_key}={parent_table}.id
                    ), 0)"""
            )


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"\s+", " ", text)


def _inventory_view_values(
    *, name: str, is_default: bool, visible_columns: list[str], filters: dict[str, str]
) -> dict[str, Any]:
    clean_name = _normalize_text(name)
    if not clean_name or len(clean_name) > 100:
        raise WarehouseAssistantError("نام طرح باید بین ۱ تا ۱۰۰ نویسه باشد.")
    if not isinstance(visible_columns, list) or not visible_columns:
        raise WarehouseAssistantError("حداقل یک ستون باید در طرح نمایش باقی بماند.")
    clean_columns: list[str] = []
    for raw_key in visible_columns:
        key = str(raw_key or "").strip()
        if key not in INVENTORY_COLUMN_KEYS:
            raise WarehouseAssistantError(f"ستون ناشناخته است: {key}")
        if key not in clean_columns:
            clean_columns.append(key)
    if len(clean_columns) > len(INVENTORY_COLUMN_KEYS):
        raise WarehouseAssistantError("تعداد ستون‌های طرح نامعتبر است.")
    if not isinstance(filters, dict) or len(filters) > len(INVENTORY_COLUMN_KEYS):
        raise WarehouseAssistantError("فیلترهای طرح نامعتبر است.")
    clean_filters: dict[str, str] = {}
    for raw_key, raw_value in filters.items():
        key = str(raw_key or "").strip()
        if key not in INVENTORY_FILTER_SQL:
            raise WarehouseAssistantError(f"ستون فیلتر ناشناخته است: {key}")
        value = _normalize_text(raw_value)
        if len(value) > 200:
            raise WarehouseAssistantError("مقدار هر فیلتر باید حداکثر ۲۰۰ نویسه باشد.")
        if value:
            clean_filters[key] = value
    return {
        "name": clean_name,
        "is_default": bool(is_default),
        "visible_columns": clean_columns,
        "filters": clean_filters,
    }


def _inventory_view_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "is_default": bool(row["is_default"]),
        "visible_columns": json.loads(row["visible_columns_json"]),
        "filters": json.loads(row["filters_json"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def list_inventory_views(settings: Any, username: str) -> list[dict[str, Any]]:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        rows = conn.execute(
            """SELECT * FROM warehouse_inventory_views
               WHERE username=? ORDER BY is_default DESC, name COLLATE NOCASE""",
            (username[:100],),
        ).fetchall()
    return [_inventory_view_from_row(row) for row in rows]


def save_inventory_view(
    settings: Any,
    username: str,
    *,
    name: str,
    is_default: bool,
    visible_columns: list[str],
    filters: dict[str, str],
) -> tuple[dict[str, Any], bool]:
    values = _inventory_view_values(
        name=name,
        is_default=is_default,
        visible_columns=visible_columns,
        filters=filters,
    )
    init_warehouse_store(settings)
    normalized_username = username[:100]
    now = _now()
    with warehouse_connection(settings) as conn:
        existing = conn.execute(
            """SELECT id FROM warehouse_inventory_views
               WHERE username=? AND name=?""",
            (normalized_username, values["name"]),
        ).fetchone()
        view_id = str(existing["id"]) if existing else str(uuid4())
        if values["is_default"]:
            conn.execute(
                "UPDATE warehouse_inventory_views SET is_default=0, updated_at=? WHERE username=? AND id<>? AND is_default=1",
                (now, normalized_username, view_id),
            )
        columns_json = json.dumps(
            values["visible_columns"], ensure_ascii=False, separators=(",", ":")
        )
        filters_json = json.dumps(
            values["filters"], ensure_ascii=False, separators=(",", ":")
        )
        if existing:
            conn.execute(
                """UPDATE warehouse_inventory_views
                   SET is_default=?, visible_columns_json=?, filters_json=?, updated_at=?
                   WHERE id=? AND username=?""",
                (
                    int(values["is_default"]), columns_json, filters_json, now,
                    view_id, normalized_username,
                ),
            )
        else:
            conn.execute(
                """INSERT INTO warehouse_inventory_views
                   (id, username, name, is_default, visible_columns_json,
                    filters_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    view_id, normalized_username, values["name"],
                    int(values["is_default"]), columns_json, filters_json, now, now,
                ),
            )
        row = conn.execute(
            "SELECT * FROM warehouse_inventory_views WHERE id=? AND username=?",
            (view_id, normalized_username),
        ).fetchone()
    return _inventory_view_from_row(row), existing is None


def delete_inventory_view(settings: Any, username: str, view_id: str) -> bool:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        cursor = conn.execute(
            "DELETE FROM warehouse_inventory_views WHERE id=? AND username=?",
            (view_id, username[:100]),
        )
    return cursor.rowcount == 1


def list_table_preferences(settings: Any, username: str) -> dict[str, list[str]]:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        rows = conn.execute(
            "SELECT table_key, visible_columns_json FROM warehouse_table_preferences WHERE username=?",
            (username[:100],),
        ).fetchall()
    result: dict[str, list[str]] = {}
    for row in rows:
        table_key = str(row["table_key"])
        if table_key not in TABLE_PREFERENCE_COLUMNS:
            continue
        try:
            values = json.loads(row["visible_columns_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        allowed = set(TABLE_PREFERENCE_COLUMNS[table_key])
        cleaned = [str(value) for value in values if str(value) in allowed]
        if cleaned:
            result[table_key] = cleaned
    return result


def save_table_preference(
    settings: Any, username: str, table_key: str, visible_columns: list[str]
) -> dict[str, Any]:
    if table_key not in TABLE_PREFERENCE_COLUMNS:
        raise WarehouseAssistantError("جدول انتخاب‌شده برای تنظیم ستون معتبر نیست.")
    allowed = TABLE_PREFERENCE_COLUMNS[table_key]
    cleaned = list(dict.fromkeys(str(value).strip() for value in visible_columns))
    if not cleaned or any(value not in allowed for value in cleaned):
        raise WarehouseAssistantError("حداقل یک ستون معتبر باید برای جدول انتخاب شود.")
    now = _now()
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute(
            """INSERT INTO warehouse_table_preferences
               (username, table_key, visible_columns_json, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(username, table_key) DO UPDATE SET
                 visible_columns_json=excluded.visible_columns_json,
                 updated_at=excluded.updated_at""",
            (
                username[:100], table_key,
                json.dumps(cleaned, ensure_ascii=False, separators=(",", ":")), now,
            ),
        )
    return {"table_key": table_key, "visible_columns": cleaned, "updated_at": now}


def _normalize_header(value: Any) -> str:
    return _normalize_text(value).casefold()


def _product_code(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return _normalize_text(value)


def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return number if math.isfinite(number) else 0.0
    text = _normalize_text(value).translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )
    text = text.replace(",", "").replace("٬", "").replace("٫", ".")
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    try:
        number = float(text)
    except ValueError:
        return 0.0
    return -number if negative else number


def _validate_archive(path: Path) -> None:
    if not is_zipfile(path):
        raise WarehouseAssistantError("فایل انتخاب‌شده یک فایل Excel معتبر نیست.")
    try:
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise WarehouseAssistantError("ساختار فایل Excel بیش از حد بزرگ است.")
            total = 0
            names: set[str] = set()
            for entry in entries:
                normalized = entry.filename.replace("\\", "/")
                if normalized.startswith("/") or ".." in normalized.split("/"):
                    raise WarehouseAssistantError("مسیر نامعتبر داخل فایل Excel پیدا شد.")
                total += int(entry.file_size)
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise WarehouseAssistantError("حجم بازشده فایل Excel بیش از حد مجاز است.")
                names.add(normalized)
            if "[Content_Types].xml" not in names or "xl/workbook.xml" not in names:
                raise WarehouseAssistantError("ساختار اصلی فایل Excel پیدا نشد.")
    except BadZipFile as exc:
        raise WarehouseAssistantError("فایل Excel خراب یا ناقص است.") from exc


def _snapshot_from_row(row: sqlite3.Row, *, duplicate: bool = False) -> dict[str, Any]:
    result = dict(row)
    result["duplicate"] = duplicate
    return result


def latest_snapshot(settings: Any) -> dict[str, Any] | None:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        row = conn.execute(
            "SELECT * FROM warehouse_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return _snapshot_from_row(row) if row else None


def import_inventory_snapshot(
    settings: Any,
    path: Path,
    source_filename: str,
    username: str,
) -> dict[str, Any]:
    init_warehouse_store(settings)
    _validate_archive(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with warehouse_connection(settings) as conn:
        from app.warehouse_receipt_reflection import capture
        from app.warehouse_transfer_reflection import capture as capture_transfers
        if capture_transfers(conn):
            raise WarehouseAssistantError('پس از ثبت بستانکار جابه‌جایی، موجودی را مستقیم از ورانگر بازخوانی کنید تا خروج دوباره کسر نشود.')
        if capture(conn) or conn.execute('SELECT 1 FROM warehouse_checkbar_confirmations WHERE active=1 LIMIT 1').fetchone():
            raise WarehouseAssistantError('پس از تأیید دریافت چک‌بار، موجودی را مستقیم از ورانگر بازخوانی کنید تا وضعیت تأیید رسیدها هم تطبیق داده شود. ورود فایل حواله به چک‌بار همچنان مجاز است.')
        existing = conn.execute(
            "SELECT * FROM warehouse_snapshots WHERE content_sha256=?", (digest,)
        ).fetchone()
    if existing:
        return _snapshot_from_row(existing, duplicate=True)

    try:
        workbook = load_workbook(
            path, read_only=True, data_only=True, keep_links=False
        )
    except Exception as exc:
        raise WarehouseAssistantError("فایل Excel قابل خواندن نیست.") from exc
    try:
        if SOURCE_SHEET not in workbook.sheetnames:
            raise WarehouseAssistantError(
                f"شیت الزامی «{SOURCE_SHEET}» در فایل پیدا نشد."
            )
        sheet = workbook[SOURCE_SHEET]
        first_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        header_indexes: dict[str, int] = {}
        for index, value in enumerate(first_row):
            normalized = _normalize_header(value)
            if normalized:
                header_indexes[normalized] = index

        def index_of(*names: str) -> int:
            for name in names:
                normalized = _normalize_header(name)
                if normalized in header_indexes:
                    return header_indexes[normalized]
            raise WarehouseAssistantError(
                f"ستون الزامی «{names[0]}» در شیت {SOURCE_SHEET} پیدا نشد."
            )

        base = {
            "product_code": index_of("کد کالا", "item code"),
            "product_name": index_of("item name", "نام کالا"),
            "conversion_rate": index_of("conversion rate", "ضریب تبدیل"),
            "manufacturer": index_of("manufacturer", "تولید کننده"),
            "brand": index_of("brand", "نام تجاری"),
        }
        # Legacy inventory M1 is "group 3". Missing levels stay blank: neither
        # brand nor a shallower leaf taxonomy is a level-three replacement.
        group_level3_index = next((
            header_indexes[_normalize_header(alias)]
            for alias in ("group 3", "group3", "group_level3", "گروه 3", "گروه ۳",
                          "گروه سطح 3", "گروه سطح ۳", "گروه سطح 3 کالا", "گروه سطح ۳ کالا")
            if _normalize_header(alias) in header_indexes
        ), None)
        warehouse_indexes: dict[str, dict[str, int]] = {}
        for code, config in WAREHOUSES.items():
            warehouse_indexes[code] = {
                key: index_of(header) for key, header in config["columns"].items()
            }

        items: list[tuple[Any, ...]] = []
        products: set[str] = set()
        blank_run = 0
        for source_row, row in enumerate(
            sheet.iter_rows(min_row=2, max_row=MAX_PRODUCT_ROWS + 1, values_only=True),
            start=2,
        ):
            code = _product_code(row[base["product_code"]] if base["product_code"] < len(row) else None)
            name = _normalize_text(row[base["product_name"]] if base["product_name"] < len(row) else None)
            if not code and not name:
                blank_run += 1
                if products and blank_run >= 200:
                    break
                continue
            blank_run = 0
            if not code:
                continue
            products.add(code)
            conversion = _number(row[base["conversion_rate"]])
            if conversion <= 0:
                conversion = 1.0
            manufacturer = _normalize_text(row[base["manufacturer"]])
            brand = _normalize_text(row[base["brand"]])
            group_level3 = (_normalize_text(row[group_level3_index])
                            if group_level3_index is not None and group_level3_index < len(row)
                            else "")
            for warehouse_code, config in WAREHOUSES.items():
                indexes = warehouse_indexes[warehouse_code]
                values = {key: _number(row[index]) for key, index in indexes.items()}
                items.append(
                    (
                        source_row,
                        warehouse_code,
                        config["name"],
                        code,
                        name,
                        conversion,
                        manufacturer,
                        brand,
                        values["stock"],
                        values["reserved"],
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        values["period_out"],
                        values["thirty_day_stock"],
                        values["sale_price"],
                        values["manufacturer_price"],
                        values["consumer_price"],
                        values["buy_price"],
                        group_level3,
                    )
                )
    finally:
        workbook.close()

    if not products:
        raise WarehouseAssistantError("هیچ کالای معتبری در شیت فایل انبار پیدا نشد.")

    imported_at = _now()
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        if capture(conn) or conn.execute('SELECT 1 FROM warehouse_checkbar_confirmations WHERE active=1 LIMIT 1').fetchone():
            raise WarehouseAssistantError('هم‌زمان دریافت چک‌بار تأیید شده است؛ موجودی را مستقیم از ورانگر بازخوانی کنید.')
        cursor = conn.execute(
            """INSERT INTO warehouse_snapshots
               (source_filename, source_sheet, content_sha256, product_count,
                item_count, imported_by, imported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                Path(source_filename).name[:180],
                SOURCE_SHEET,
                digest,
                len(products),
                len(items),
                username[:100],
                imported_at,
            ),
        )
        snapshot_id = int(cursor.lastrowid)
        conn.executemany(
            """INSERT INTO warehouse_snapshot_items
               (snapshot_id, source_row, warehouse_code, warehouse_name,
                product_code, product_name, conversion_rate, manufacturer, brand,
                stock, reserved, damaged, undelivered, open_customer_order,
                unconfirmed_free_invoice, legacy_open_order, open_order,
                pending_sale_voucher, period_out, thirty_day_stock, sale_price,
                manufacturer_price, consumer_price, buy_price, group_level3)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(snapshot_id, *item) for item in items],
        )
        row = conn.execute(
            "SELECT * FROM warehouse_snapshots WHERE id=?", (snapshot_id,)
        ).fetchone()
    return _snapshot_from_row(row, duplicate=False)


def _query_rows(cursor: Any, sql: str) -> list[dict[str, Any]]:
    cursor.execute(sql)
    columns = [str(column[0]) for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _supply_scope_state(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM warehouse_supply_scope_state WHERE id=1"
    ).fetchone()


def _supply_scope_is_strict(conn: sqlite3.Connection) -> bool:
    state = _supply_scope_state(conn)
    return bool(state and state["strict_enabled"])


def _receipt_scope_sql(*, stock_refs: str, window_start: str, window_end: str) -> str:
    return f"""
WITH ranked_goods AS (
  SELECT model.GoodsRef, model.StockDCRef, model.ManufacturerName,
         model.BrandName,
         ROW_NUMBER() OVER (
           PARTITION BY model.GoodsRef, model.StockDCRef
           ORDER BY model.AccYear DESC
         ) AS GoodsRank
  FROM FRU.StockGoodsModel AS model
  WHERE model.StockDCRef IN ({stock_refs})
)
SELECT receipt.StockDCRef, receipt.SupplierRef,
       ISNULL(supplier.SupplierName, '') AS SupplierName,
       ISNULL(goods.ManufacturerName, '') AS ManufacturerName,
       ISNULL(goods.BrandName, '') AS BrandName,
       COUNT(DISTINCT receipt.ID) AS ReceiptCount,
       SUM(ISNULL(item.TotalQty, 0)) AS ReceiptQuantity,
       MIN(receipt.VocherDate) AS FirstReceiptDate,
       MAX(receipt.VocherDate) AS LastReceiptDate
FROM Inv.tblVocherHdr AS receipt
INNER JOIN Inv.tblVocherItm AS item ON item.HdrRef = receipt.ID
INNER JOIN ranked_goods AS goods
        ON goods.GoodsRef = item.GoodsRef
       AND goods.StockDCRef = receipt.StockDCRef
       AND goods.GoodsRank = 1
LEFT JOIN GNR.tblSupplier AS supplier ON supplier.ID = receipt.SupplierRef
WHERE receipt.VocherTypeCode = 20
  AND receipt.ConfirmDate IS NOT NULL
  AND receipt.StockDCRef IN ({stock_refs})
  AND receipt.VocherDate BETWEEN N'{window_start}' AND N'{window_end}'
  AND LTRIM(RTRIM(ISNULL(goods.ManufacturerName, ''))) <> ''
GROUP BY receipt.StockDCRef, receipt.SupplierRef, supplier.SupplierName,
         goods.ManufacturerName, goods.BrandName
""".strip()


def _sync_supply_scope(
    conn: sqlite3.Connection,
    *,
    snapshot_id: int,
    receipt_rows: list[dict[str, Any]],
    window_start: str | None,
    window_end: str | None,
    username: str,
    strict: bool,
) -> dict[str, Any]:
    """Refresh evidence while preserving every explicit user override."""
    warehouse_by_ref = {
        int(config["stock_dc_ref"]): (code, config["name"])
        for code, config in WAREHOUSES.items()
    }
    evidence: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in receipt_rows:
        warehouse = warehouse_by_ref.get(int(row.get("StockDCRef") or 0))
        supplier = _normalize_text(row.get("ManufacturerName"))
        brand = _normalize_text(row.get("BrandName"))
        if warehouse is None or not supplier:
            continue
        key = (warehouse[0], supplier, brand)
        item = evidence.setdefault(
            key,
            {
                "warehouse_name": warehouse[1],
                "receipt_count": 0,
                "receipt_quantity": 0.0,
                "first_receipt_date": None,
                "last_receipt_date": None,
                "supplier_refs": set(),
                "supplier_names": set(),
            },
        )
        item["receipt_count"] += int(row.get("ReceiptCount") or 0)
        item["receipt_quantity"] += _number(row.get("ReceiptQuantity"))
        first_date = _normalize_text(row.get("FirstReceiptDate")) or None
        last_date = _normalize_text(row.get("LastReceiptDate")) or None
        if first_date and (
            item["first_receipt_date"] is None
            or first_date < item["first_receipt_date"]
        ):
            item["first_receipt_date"] = first_date
        if last_date and (
            item["last_receipt_date"] is None
            or last_date > item["last_receipt_date"]
        ):
            item["last_receipt_date"] = last_date
        if row.get("SupplierRef") is not None:
            item["supplier_refs"].add(str(row["SupplierRef"]))
        source_name = _normalize_text(row.get("SupplierName"))
        if source_name:
            item["supplier_names"].add(source_name)

    available_rows = conn.execute(
        """SELECT warehouse_code, warehouse_name, TRIM(manufacturer) AS supplier,
                  TRIM(brand) AS brand
           FROM warehouse_snapshot_items
           WHERE snapshot_id=? AND TRIM(manufacturer)<>''
           GROUP BY warehouse_code, warehouse_name, TRIM(manufacturer), TRIM(brand)""",
        (snapshot_id,),
    ).fetchall()
    available: dict[tuple[str, str, str], str] = {
        (str(row["warehouse_code"]), str(row["supplier"]), str(row["brand"])):
        str(row["warehouse_name"])
        for row in available_rows
    }
    all_keys = set(available) | set(evidence)
    existing_rows = conn.execute("SELECT * FROM warehouse_supply_scope").fetchall()
    existing = {
        (str(row["warehouse_code"]), str(row["supplier"]), str(row["brand"])): row
        for row in existing_rows
    }
    now = _now()

    for key, row in existing.items():
        if key in all_keys:
            continue
        enabled = int(row["enabled"]) if row["is_user_override"] else 0
        conn.execute(
            """UPDATE warehouse_supply_scope
               SET enabled=?, observed_in_recent_receipts=0, receipt_count=0,
                   receipt_quantity=0, first_receipt_date=NULL,
                   last_receipt_date=NULL, source_supplier_refs_json='[]',
                   source_supplier_names_json='[]', updated_at=?, updated_by=?
               WHERE id=?""",
            (enabled, now, username[:100], row["id"]),
        )

    for key in sorted(all_keys):
        warehouse_code, supplier, brand = key
        proof = evidence.get(key)
        old = existing.get(key)
        observed = proof is not None
        default_enabled = int(observed if strict else True)
        enabled = (
            int(old["enabled"])
            if old is not None and old["is_user_override"]
            else default_enabled
        )
        audit_time = (
            str(old["updated_at"])
            if old is not None and old["is_user_override"]
            else now
        )
        audit_user = (
            str(old["updated_by"])
            if old is not None and old["is_user_override"]
            else username[:100]
        )
        warehouse_name = available.get(key) or proof["warehouse_name"]
        values = (
            warehouse_name,
            enabled,
            int(observed),
            int(proof["receipt_count"]) if proof else 0,
            float(proof["receipt_quantity"]) if proof else 0.0,
            proof["first_receipt_date"] if proof else None,
            proof["last_receipt_date"] if proof else None,
            json.dumps(sorted(proof["supplier_refs"])) if proof else "[]",
            json.dumps(sorted(proof["supplier_names"]), ensure_ascii=False)
            if proof else "[]",
            audit_time,
            audit_user,
        )
        if old is None:
            conn.execute(
                """INSERT INTO warehouse_supply_scope
                   (warehouse_code, warehouse_name, supplier, brand, enabled,
                    observed_in_recent_receipts, receipt_count, receipt_quantity,
                    first_receipt_date, last_receipt_date,
                    source_supplier_refs_json, source_supplier_names_json,
                    is_user_override, created_at, updated_at, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
                (
                    warehouse_code, warehouse_name, supplier, brand,
                    enabled, int(observed),
                    int(proof["receipt_count"]) if proof else 0,
                    float(proof["receipt_quantity"]) if proof else 0.0,
                    proof["first_receipt_date"] if proof else None,
                    proof["last_receipt_date"] if proof else None,
                    json.dumps(sorted(proof["supplier_refs"])) if proof else "[]",
                    json.dumps(sorted(proof["supplier_names"]), ensure_ascii=False)
                    if proof else "[]",
                    now, now, username[:100],
                ),
            )
        else:
            conn.execute(
                """UPDATE warehouse_supply_scope
                   SET warehouse_name=?, enabled=?,
                       observed_in_recent_receipts=?, receipt_count=?,
                       receipt_quantity=?, first_receipt_date=?,
                       last_receipt_date=?, source_supplier_refs_json=?,
                       source_supplier_names_json=?, updated_at=?, updated_by=?
                   WHERE id=?""",
                (*values, old["id"]),
            )

    conn.execute(
        """INSERT INTO warehouse_supply_scope_state
           (id, strict_enabled, source_kind, evidence_window_start,
            evidence_window_end, refreshed_at, refreshed_by)
           VALUES (1, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET
             strict_enabled=excluded.strict_enabled,
             source_kind=excluded.source_kind,
             evidence_window_start=excluded.evidence_window_start,
             evidence_window_end=excluded.evidence_window_end,
             refreshed_at=excluded.refreshed_at,
             refreshed_by=excluded.refreshed_by""",
        (
            int(strict), "varanegar_receipts" if strict else "snapshot_fallback",
            window_start, window_end, now, username[:100],
        ),
    )
    return {
        "strict_enabled": strict,
        "active_pairs": sum(
            1
            for key in all_keys
            if (
                int(existing[key]["enabled"])
                if key in existing and existing[key]["is_user_override"]
                else int(key in evidence if strict else True)
            )
        ),
        "observed_pairs": len(evidence),
        "evidence_window_start": window_start,
        "evidence_window_end": window_end,
    }


def _stock_availability_timeline(
    *,
    current_on_hand: float,
    period_dates: list[str],
    daily_movement: dict[str, float],
    daily_gross_sales: dict[str, float],
) -> dict[str, bool]:
    """Rebuild daily sellability backwards from current healthy stock."""
    balance = float(current_on_hand)
    availability: dict[str, bool] = {}
    for date in reversed(period_dates):
        end_of_day = balance
        start_of_day = end_of_day - float(daily_movement.get(date, 0.0))
        availability[date] = (
            max(start_of_day, end_of_day) > 0
            or float(daily_gross_sales.get(date, 0.0)) > 0
        )
        balance = start_of_day
    return availability


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * min(1.0, max(0.0, percentile))
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    weight = position - lower_index
    return ordered[lower_index] * (1.0 - weight) + ordered[upper_index] * weight


def _robust_window_demand(
    *,
    window_dates: list[str],
    availability: dict[str, bool],
    selected_trends: list[dict[str, Any]],
    baseline_trends: list[dict[str, Any]] | None = None,
    history_dates: list[str] | None = None,
) -> dict[str, Any]:
    """Cap concentrated customer shocks outside Amiran with an audit trail."""
    amiran_by_date: dict[str, float] = {}
    online_transfer_by_date: dict[str, float] = {}
    other_by_customer_date: dict[tuple[str, str], float] = {}

    def customer_key(trend: dict[str, Any]) -> str:
        value = trend.get("CustomerId")
        return f"customer:{value}" if value is not None else "customer:unknown"

    for trend in selected_trends:
        date = _normalize_text(trend.get("ReportDate"))
        if not date:
            continue
        online_transfer_by_date[date] = online_transfer_by_date.get(
            date, 0.0
        ) + max(0.0, _number(trend.get("OnlineTransferOutQty")))
        amiran_value = _number(trend.get("AmiranNetOutQty"))
        other_value = (
            _number(trend.get("OtherCustomerNetOutQty"))
            if trend.get("OtherCustomerNetOutQty") is not None
            else _number(trend.get("NetOutQty")) - amiran_value
        )
        amiran_by_date[date] = amiran_by_date.get(date, 0.0) + amiran_value
        key = (date, customer_key(trend))
        other_by_customer_date[key] = (
            other_by_customer_date.get(key, 0.0) + other_value
        )

    sellable_dates = [date for date in window_dates if availability.get(date, False)]
    sellable_date_set = set(sellable_dates)
    positive_customer_days = [
        max(0.0, value)
        for (date, _customer), value in other_by_customer_date.items()
        if date in sellable_date_set and value > 0
    ]
    daily_cap: float | None = None
    recurring_pattern = False
    recurring_pattern_days = 0
    spike_events: dict[tuple[str, str], float] = {}
    if (
        len(sellable_dates) >= DEMAND_OUTLIER_MIN_AVAILABLE_DAYS
        and len(positive_customer_days) >= DEMAND_OUTLIER_MIN_POSITIVE_DAYS
    ):
        daily_cap = _percentile(
            positive_customer_days, DEMAND_OUTLIER_PERCENTILE
        )
        other_total_by_date: dict[str, float] = {}
        for (date, _customer), value in other_by_customer_date.items():
            if date in sellable_date_set:
                other_total_by_date[date] = other_total_by_date.get(date, 0.0) + max(
                    0.0, value
                )

        baseline_by_customer_date: dict[tuple[str, str], float] = {}
        for trend in baseline_trends or selected_trends:
            date = _normalize_text(trend.get("ReportDate"))
            if not date:
                continue
            amiran_value = _number(trend.get("AmiranNetOutQty"))
            other_value = (
                _number(trend.get("OtherCustomerNetOutQty"))
                if trend.get("OtherCustomerNetOutQty") is not None
                else _number(trend.get("NetOutQty")) - amiran_value
            )
            key = (date, customer_key(trend))
            baseline_by_customer_date[key] = (
                baseline_by_customer_date.get(key, 0.0) + other_value
            )
        ordered_history_dates = history_dates or window_dates
        history_index = {
            date: index for index, date in enumerate(ordered_history_dates)
        }
        history_values_by_customer: dict[str, list[tuple[int, float]]] = {}
        for (date, customer), value in baseline_by_customer_date.items():
            if value <= 0 or date not in history_index:
                continue
            history_values_by_customer.setdefault(customer, []).append(
                (history_index[date], float(value))
            )

        for (date, customer), value in other_by_customer_date.items():
            if date not in sellable_date_set or value <= 0:
                continue
            date_index = history_index.get(date)
            customer_reference = daily_cap
            if date_index is not None:
                prior_values = [
                    historical_value
                    for historical_index, historical_value
                    in history_values_by_customer.get(customer, [])
                    if max(0, date_index - DEMAND_CUSTOMER_HISTORY_DAYS)
                    <= historical_index
                    < date_index
                ]
                if len(prior_values) >= DEMAND_OUTLIER_MIN_POSITIVE_DAYS - 1:
                    customer_reference = max(
                        customer_reference, float(median(prior_values))
                    )
            daily_other_total = other_total_by_date.get(date, 0.0)
            customer_share = value / daily_other_total if daily_other_total > 0 else 0.0
            is_large = (
                customer_reference > 0
                and value
                > customer_reference * DEMAND_OUTLIER_MEDIAN_MULTIPLIER
            )
            is_concentrated = (
                customer_share >= DEMAND_CUSTOMER_CONCENTRATION_SHARE
            )
            if is_large and is_concentrated:
                spike_events[(date, customer)] = customer_reference

        candidate_dates = {date for date, _customer in spike_events}
        candidate_customers = {customer for _date, customer in spike_events}
        recurring_pattern = (
            len(candidate_dates)
            > len(sellable_dates) * DEMAND_RECURRING_PATTERN_SHARE
            and len(candidate_customers) >= DEMAND_RECURRING_MIN_CUSTOMERS
        )
        if recurring_pattern:
            recurring_pattern_days = len(candidate_dates)

    raw_amiran = sum(amiran_by_date.get(date, 0.0) for date in sellable_dates)
    raw_online_transfer = sum(
        online_transfer_by_date.get(date, 0.0) for date in sellable_dates
    )
    raw_other = sum(
        value
        for (date, _customer), value in other_by_customer_date.items()
        if date in sellable_date_set
    )
    adjusted_other = raw_other
    exceptional_out = 0.0
    anomaly_days = 0
    if spike_events and not recurring_pattern:
        adjusted_other = 0.0
        adjusted_dates: set[str] = set()
        for (date, customer), value in other_by_customer_date.items():
            if date not in sellable_date_set:
                continue
            event_cap = spike_events.get((date, customer))
            if event_cap is not None and value > event_cap:
                adjusted_other += event_cap
                exceptional_out += value - event_cap
                adjusted_dates.add(date)
            else:
                adjusted_other += value
        anomaly_days = len(adjusted_dates)

    return {
        "raw_net_out": max(0.0, raw_amiran + raw_other + raw_online_transfer),
        "adjusted_net_out": max(
            0.0, raw_amiran + adjusted_other + raw_online_transfer
        ),
        "amiran_net_out": max(0.0, raw_amiran),
        "online_transfer_out": max(0.0, raw_online_transfer),
        "exceptional_out": max(0.0, exceptional_out),
        "anomaly_days": anomaly_days,
        "daily_cap": daily_cap,
        "recurring_pattern": recurring_pattern,
        "recurring_pattern_days": recurring_pattern_days,
    }


def _last_stock_window_metrics(
    *,
    current_on_hand: float,
    history_dates: list[str],
    daily_movement: dict[str, float],
    trend_rows: list[dict[str, Any]],
    period_days: int,
) -> dict[str, Any]:
    """Measure demand in the period ending on the product's last sellable day."""
    daily_gross_sales: dict[str, float] = {}
    for trend in trend_rows:
        date = _normalize_text(trend.get("ReportDate"))
        if date:
            daily_gross_sales[date] = daily_gross_sales.get(date, 0.0) + max(
                0.0, _number(trend.get("AllGrossSalesQty"))
            ) + max(0.0, _number(trend.get("OnlineTransferOutQty")))
    availability = _stock_availability_timeline(
        current_on_hand=current_on_hand,
        period_dates=history_dates,
        daily_movement=daily_movement,
        daily_gross_sales=daily_gross_sales,
    )
    last_index = next(
        (
            index
            for index in range(len(history_dates) - 1, -1, -1)
            if availability.get(history_dates[index], False)
        ),
        None,
    )
    if last_index is None:
        return {
            "gross_out": 0.0,
            "period_return": 0.0,
            "net_out": 0.0,
            "raw_net_out": 0.0,
            "amiran_net_out": 0.0,
            "online_transfer_out": 0.0,
            "exceptional_out": 0.0,
            "anomaly_days": 0,
            "daily_cap": None,
            "recurring_pattern": False,
            "recurring_pattern_days": 0,
            "excluded_seller_qty": 0.0,
            "sales_rate_days": 0,
            "stockout_days": period_days,
            "last_in_stock_date": None,
            "sales_window_start": None,
            "sales_window_end": None,
            "days_since_last_stock": None,
            "ordering_cycle_active": False,
        }

    days_since_last_stock = len(history_dates) - 1 - last_index
    window_start_index = last_index - period_days + 1
    complete_window = window_start_index >= 0
    window_dates = (
        history_dates[window_start_index : last_index + 1]
        if complete_window
        else history_dates[: last_index + 1]
    )
    window_date_set = set(window_dates)
    selected_trends = [
        trend
        for trend in trend_rows
        if _normalize_text(trend.get("ReportDate")) in window_date_set
    ]
    sales_rate_days = sum(
        1 for date in window_dates if availability.get(date, False)
    )
    robust_demand = _robust_window_demand(
        window_dates=window_dates,
        availability=availability,
        selected_trends=selected_trends,
        baseline_trends=trend_rows,
        history_dates=history_dates,
    )
    return {
        "gross_out": max(
            0.0,
            sum(_number(trend.get("GrossOutQty")) for trend in selected_trends),
        ),
        "period_return": max(
            0.0,
            sum(_number(trend.get("ReturnQty")) for trend in selected_trends),
        ),
        "net_out": robust_demand["adjusted_net_out"],
        "raw_net_out": robust_demand["raw_net_out"],
        "amiran_net_out": robust_demand["amiran_net_out"],
        "online_transfer_out": robust_demand["online_transfer_out"],
        "exceptional_out": robust_demand["exceptional_out"],
        "anomaly_days": robust_demand["anomaly_days"],
        "daily_cap": robust_demand["daily_cap"],
        "recurring_pattern": robust_demand["recurring_pattern"],
        "recurring_pattern_days": robust_demand["recurring_pattern_days"],
        "excluded_seller_qty": max(
            0.0,
            sum(
                _number(trend.get("ExcludedSellerNetQty"))
                for trend in selected_trends
            ),
        ),
        "sales_rate_days": sales_rate_days,
        "stockout_days": max(0, period_days - sales_rate_days),
        "last_in_stock_date": history_dates[last_index],
        "sales_window_start": window_dates[0] if complete_window else None,
        "sales_window_end": history_dates[last_index],
        "days_since_last_stock": days_since_last_stock,
        "ordering_cycle_active": (
            complete_window and days_since_last_stock <= ORDER_CYCLE_STALE_DAYS
        ),
    }


def _purchase_price_cache_snapshot(
    settings: Any,
) -> tuple[dict[int, float], bool, str | None]:
    with warehouse_connection(settings) as conn:
        state = conn.execute(
            "SELECT refreshed_at FROM warehouse_purchase_price_cache_state WHERE id=1"
        ).fetchone()
        rows = conn.execute(
            "SELECT goods_ref, approximate_price FROM warehouse_purchase_price_cache"
        ).fetchall()
    refreshed_at = str(state["refreshed_at"]) if state else None
    fresh = False
    if refreshed_at:
        try:
            age_seconds = (
                datetime.now(timezone.utc) - datetime.fromisoformat(refreshed_at)
            ).total_seconds()
            fresh = 0 <= age_seconds < PURCHASE_PRICE_CACHE_TTL_SECONDS
        except ValueError:
            fresh = False
    return (
        {
            int(row["goods_ref"]): max(0.0, _number(row["approximate_price"]))
            for row in rows
        },
        fresh,
        refreshed_at,
    )


def _replace_purchase_price_cache(
    settings: Any, rows: list[dict[str, Any]]
) -> tuple[dict[int, float], str]:
    refreshed_at = _now()
    normalized: list[tuple[int, float, str, int | None, str]] = []
    for row in rows:
        goods_ref = int(row.get("GoodsRef") or 0)
        price = max(0.0, _number(row.get("ApproximatePrice")))
        if goods_ref <= 0 or price <= 0:
            continue
        invoice_id = int(row["InvoiceId"]) if row.get("InvoiceId") else None
        normalized.append(
            (
                goods_ref,
                price,
                _normalize_text(row.get("PurchaseDate")),
                invoice_id,
                refreshed_at,
            )
        )
    with warehouse_connection(settings) as conn:
        conn.execute("DELETE FROM warehouse_purchase_price_cache")
        conn.executemany(
            """INSERT INTO warehouse_purchase_price_cache
               (goods_ref, approximate_price, purchase_date, invoice_id,
                refreshed_at)
               VALUES (?, ?, ?, ?, ?)""",
            normalized,
        )
        conn.execute(
            """INSERT INTO warehouse_purchase_price_cache_state
               (id, refreshed_at, source_row_count) VALUES (1, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 refreshed_at=excluded.refreshed_at,
                 source_row_count=excluded.source_row_count""",
            (refreshed_at, len(normalized)),
        )
    return ({row[0]: row[1] for row in normalized}, refreshed_at)


def sync_varanegar_snapshot(
    settings: Any,
    username: str,
    *,
    period_days: int = 60,
) -> dict[str, Any]:
    """Read current stock and recent sales movement; never writes to Varanegar."""
    if not settings.sql_configured:
        raise WarehouseAssistantError("اتصال فقط‌خواندنی ورانگر تنظیم نشده است.")
    if period_days < 7 or period_days > 365:
        raise WarehouseAssistantError("بازه روند خروج باید بین ۷ تا ۳۶۵ روز باشد.")

    stock_refs = ",".join(
        str(int(config["stock_dc_ref"])) for config in WAREHOUSES.values()
    )
    price_order_type_refs = ", ".join(
        str(int(config["price_order_type_ref"]))
        for config in WAREHOUSES.values()
    )
    price_order_type_case = "CASE ranked.StockDCRef " + " ".join(
        f"WHEN {int(config['stock_dc_ref'])} THEN "
        f"{int(config['price_order_type_ref'])}"
        for config in WAREHOUSES.values()
    ) + " END"
    current = tehran_now()
    period_end = jalali_business_date(current)
    period_dates = [
        jalali_business_date(current - timedelta(days=offset))
        for offset in range(period_days - 1, -1, -1)
    ]
    period_start = period_dates[0]
    receipt_window_start = jalali_business_date(
        current - timedelta(days=SUPPLY_SCOPE_RECEIPT_DAYS - 1)
    )
    history_days = period_days + max(
        ORDER_CYCLE_STALE_DAYS, DEMAND_CUSTOMER_HISTORY_DAYS
    )
    history_dates = [
        jalali_business_date(current - timedelta(days=offset))
        for offset in range(history_days - 1, -1, -1)
    ]
    history_start = history_dates[0]
    acc_year = int(period_end[:4])
    inventory_sql = f"""
WITH server_flags AS (
  SELECT ISNULL(MAX(CASE WHEN KeyName = 'POrder_OnlyInsertOrder'
                         THEN TRY_CONVERT(int, KeyValue) END), 0) AS LegacyOrderEnabled
  FROM GNR.tblServerConfig
),
ranked_stock AS (
  SELECT stock.GoodsRef, stock.StockDCRef, stock.AccYear,
         stock.OnHandQty, stock.ReservedQty, stock.DamagedQty,
         stock.UnDeliveredQty,
         ROW_NUMBER() OVER (
           PARTITION BY stock.GoodsRef, stock.StockDCRef
           ORDER BY stock.AccYear DESC, stock.ID DESC
         ) AS StockRank
  FROM GNR.tblStockGoods AS stock
  WHERE stock.StockDCRef IN ({stock_refs})
),
stock_goods_model AS (
  SELECT model.GoodsRef, model.StockDCRef, model.AccYear,
         model.GoodsCode, model.GoodsName, model.CartonType,
         model.ManufacturerName, model.BrandName,
         model.ManufacturerGoodsCode, model.Barcode1, model.Barcode2,
         model.DefaultGoodsBarcode, model.GoodsBarcodeNameList,
         model.StockDCName
  FROM FRU.StockGoodsModel AS model
  WHERE model.StockDCRef IN ({stock_refs}) AND model.AccYear = {acc_year}
),
contract_price_candidates AS (
  SELECT TRY_CONVERT(int, contract_price.GoodsRef) AS GoodsRef,
         TRY_CONVERT(int, contract_price.OrderTypeRef) AS OrderTypeRef,
         contract_price.SalePrice,
         contract_price.UserPrice,
         source_price.ManufacturerPrice,
         ROW_NUMBER() OVER (
           PARTITION BY TRY_CONVERT(int, contract_price.GoodsRef),
                        TRY_CONVERT(int, contract_price.OrderTypeRef)
           ORDER BY contract_price.StartDate DESC,
                    contract_price.[LastUpdate] DESC,
                    contract_price.Priority DESC,
                    contract_price.Id DESC
         ) AS PriceRank
  FROM NGT.ContractPrices AS contract_price
  INNER JOIN NGT.OrderTypes AS order_type
          ON TRY_CONVERT(int, order_type.BackOfficeId) =
             TRY_CONVERT(int, contract_price.OrderTypeRef)
         AND ISNULL(order_type.IsRemoved, 0) = 0
  LEFT JOIN SLE.tblCPrice AS source_price
         ON source_price.UniqueId = contract_price.Id
  WHERE TRY_CONVERT(int, contract_price.OrderTypeRef) IN ({price_order_type_refs})
    AND ISNULL(contract_price.IsRemoved, 0) = 0
    AND contract_price.StartDate <= N'{period_end}'
    AND (
      contract_price.EndDate IS NULL OR contract_price.EndDate = ''
      OR contract_price.EndDate >= N'{period_end}'
    )
    AND NULLIF(contract_price.GoodsRef, '') IS NOT NULL
    AND NULLIF(contract_price.GoodsGroupRef, '') IS NULL
    AND NULLIF(contract_price.MainTypeRef, '') IS NULL
    AND NULLIF(contract_price.SubTypeRef, '') IS NULL
    AND NULLIF(contract_price.CustRef, '') IS NULL
    AND NULLIF(contract_price.CustCtgrRef, '') IS NULL
    AND NULLIF(contract_price.CustActRef, '') IS NULL
    AND NULLIF(contract_price.CustLevelRef, '') IS NULL
    AND ISNULL(contract_price.MainCustTypeRef, 0) = 0
    AND ISNULL(contract_price.SubCustTypeRef, 0) = 0
    AND NULLIF(contract_price.StateRef, '') IS NULL
    AND NULLIF(contract_price.CountyRef, '') IS NULL
    AND NULLIF(contract_price.AreaRef, '') IS NULL
    AND NULLIF(contract_price.BuyTypeRef, '') IS NULL
    AND ISNULL(contract_price.UsanceDay, 0) = 0
    AND NULLIF(contract_price.DealerCtgrRef, '') IS NULL
    AND NULLIF(contract_price.DCRef, '') IS NULL
    AND ISNULL(contract_price.SaleOfficeRef, 0) = 0
    AND ISNULL(contract_price.MinQty, 0) = 0
    AND ISNULL(contract_price.MaxQty, 0) = 0
    AND ISNULL(contract_price.BatchNoRef, 0) = 0
    AND NULLIF(contract_price.BatchNo, '') IS NULL
),
open_customer_order AS (
  SELECT header.StockDcRef, item.GoodsRef, header.AccYear,
         SUM(ISNULL(item.OrderQty, 0) * package.Qty) AS Qty
  FROM SLE.tblOrderHdr AS header
  INNER JOIN SLE.tblOrderItm AS item ON item.HdrRef = header.ID
  INNER JOIN GNR.tblPackage AS package
          ON package.GoodsRef = item.GoodsRef
         AND package.UnitRef = item.UnitRef
  INNER JOIN SLE.tblOrderType AS order_type ON order_type.ID = header.OrderType
  WHERE header.AccYear = {acc_year}
    AND header.StockDcRef IN ({stock_refs})
    AND header.CancelFlag = 0
    AND header.OrderType NOT IN (1003, 1007, 1008)
    AND header.SaleHdrRef IS NULL
    AND item.IsDeleted = 0
    AND package.ForSale = 1
    AND order_type.EffectOrderOnStockGoods = 0
  GROUP BY header.StockDcRef, item.GoodsRef, header.AccYear
),
unconfirmed_free_invoice AS (
  SELECT header.StockDcRef, item.GoodsRef, header.AccYear,
         SUM(ISNULL(item.TotalQty, 0)) AS Qty
  FROM SLE.tblFreeInvoiceHdr AS header
  INNER JOIN SLE.tblFreeInvoiceItm AS item ON item.HdrRef = header.ID
  WHERE header.AccYear = {acc_year}
    AND header.StockDcRef IN ({stock_refs})
    AND header.CancelFlag = 0
    AND header.ConfirmDate IS NULL
  GROUP BY header.StockDcRef, item.GoodsRef, header.AccYear
),
legacy_open_order AS (
  SELECT item.PStockId AS StockDcRef, item.PGoodsId AS GoodsRef,
         TRY_CONVERT(int, LEFT(header.OrderDate, 4)) AS AccYear,
         SUM(ISNULL(item.Quantity, 0)) AS Qty
  FROM dbo.POrderLine2 AS item
  INNER JOIN dbo.POrder2 AS header ON header.POrderId = item.POrderId
  CROSS JOIN server_flags
  WHERE item.PStockId IN ({stock_refs})
    AND header.SaleId = 0
    AND header.IsCanceled = 0
    AND server_flags.LegacyOrderEnabled = 1
    AND TRY_CONVERT(int, LEFT(header.OrderDate, 4)) = {acc_year}
  GROUP BY item.PStockId, item.PGoodsId, TRY_CONVERT(int, LEFT(header.OrderDate, 4))
),
pending_sale_voucher AS (
  SELECT header.StockDcRef, item.GoodsRef, header.AccYear,
         SUM(ISNULL(item.TotalQty, 0)) AS Qty
  FROM SLE.tblSaleHdr AS header
  INNER JOIN SLE.tblSaleItm AS item ON item.HdrRef = header.ID
  WHERE header.AccYear = {acc_year}
    AND header.StockDcRef IN ({stock_refs})
    AND header.CancelFlag = 0
    AND header.SaleVocherNo IS NOT NULL
    AND header.SaleNo IS NULL
    AND ISNULL(item.IsDeleted, 0) = 0
  GROUP BY header.StockDcRef, item.GoodsRef, header.AccYear
)
SELECT ranked.GoodsRef, model.GoodsCode, model.GoodsName,
       CASE WHEN ISNULL(model.CartonType, 0) > 0 THEN model.CartonType ELSE 1 END AS ConversionRate,
       ISNULL(model.ManufacturerName, '') AS ManufacturerName,
       ISNULL(model.BrandName, '') AS BrandName,
       ISNULL(group_level3.GoodsGroupName, '') AS GroupLevel3,
       ISNULL(model.ManufacturerGoodsCode, '') AS ManufacturerGoodsCode,
       ISNULL(model.Barcode1, '') AS Barcode1,
       ISNULL(model.Barcode2, '') AS Barcode2,
       ISNULL(model.DefaultGoodsBarcode, '') AS DefaultGoodsBarcode,
       ISNULL(model.GoodsBarcodeNameList, '') AS GoodsBarcodeNameList,
       ranked.StockDCRef, model.StockDCName,
       ISNULL(ranked.OnHandQty, 0) AS OnHandQty,
       ISNULL(ranked.ReservedQty, 0) AS ReservedQty,
       ISNULL(ranked.DamagedQty, 0) AS DamagedQty,
       ISNULL(ranked.UnDeliveredQty, 0) AS UnDeliveredQty,
       ISNULL(customer_order.Qty, 0) AS OpenCustomerOrderQty,
       ISNULL(free_invoice.Qty, 0) AS UnconfirmedFreeInvoiceQty,
       ISNULL(legacy_order.Qty, 0) AS LegacyOpenOrderQty,
       ISNULL(customer_order.Qty, 0) + ISNULL(free_invoice.Qty, 0)
         + ISNULL(legacy_order.Qty, 0) AS OpenOrderQty,
       ISNULL(sale_voucher.Qty, 0) AS PendingSaleVoucherQty,
       ISNULL(contract_price.SalePrice, 0) AS SalePrice,
       ISNULL(contract_price.ManufacturerPrice, 0) AS ManufacturerPrice,
       ISNULL(contract_price.UserPrice, 0) AS ConsumerPrice
FROM ranked_stock AS ranked
LEFT JOIN GNR.tblGoods AS goods ON goods.ID = ranked.GoodsRef
LEFT JOIN GNR.tblGoodsGroup AS goods_group ON goods_group.ID = goods.GoodsGroupRef
LEFT JOIN GNR.tblGoodsGroup AS group_level3
       ON group_level3.NLevel = 3
      AND goods_group.NLeft >= group_level3.NLeft
      AND goods_group.NRight <= group_level3.NRight
INNER JOIN stock_goods_model AS model
        ON model.GoodsRef = ranked.GoodsRef
       AND model.StockDCRef = ranked.StockDCRef
       AND model.AccYear = ranked.AccYear
LEFT JOIN open_customer_order AS customer_order
       ON customer_order.StockDcRef = ranked.StockDCRef
      AND customer_order.GoodsRef = ranked.GoodsRef
      AND customer_order.AccYear = ranked.AccYear
LEFT JOIN unconfirmed_free_invoice AS free_invoice
       ON free_invoice.StockDcRef = ranked.StockDCRef
      AND free_invoice.GoodsRef = ranked.GoodsRef
      AND free_invoice.AccYear = ranked.AccYear
LEFT JOIN legacy_open_order AS legacy_order
       ON legacy_order.StockDcRef = ranked.StockDCRef
      AND legacy_order.GoodsRef = ranked.GoodsRef
      AND legacy_order.AccYear = ranked.AccYear
LEFT JOIN pending_sale_voucher AS sale_voucher
       ON sale_voucher.StockDcRef = ranked.StockDCRef
      AND sale_voucher.GoodsRef = ranked.GoodsRef
      AND sale_voucher.AccYear = ranked.AccYear
LEFT JOIN contract_price_candidates AS contract_price
       ON contract_price.GoodsRef = ranked.GoodsRef
      AND contract_price.OrderTypeRef = {price_order_type_case}
      AND contract_price.PriceRank = 1
WHERE ranked.StockRank = 1 AND ranked.AccYear = {acc_year}
ORDER BY ranked.StockDCRef, model.GoodsCode
""".strip()
    outflow_sql = f"""
WITH sales_demand AS (
  SELECT sale.GoodsId AS GoodsRef, sale.StockDcID AS StockDCRef,
         sale.ReportDate, sale.CustomerId, sale.CustomerCategoryId,
         SUM(CASE WHEN COALESCE(sale.DealerId, -1) <> {EXCLUDED_REPLENISHMENT_DEALER_ID}
                  THEN ISNULL(sale.SellQty, 0) ELSE 0 END) AS GrossOutQty,
         SUM(CASE WHEN COALESCE(sale.DealerId, -1) <> {EXCLUDED_REPLENISHMENT_DEALER_ID}
                  THEN ISNULL(sale.SellReturnQty, 0) ELSE 0 END) AS ReturnQty,
         SUM(CASE WHEN COALESCE(sale.DealerId, -1) <> {EXCLUDED_REPLENISHMENT_DEALER_ID}
                  THEN ISNULL(sale.SellQty, 0) - ISNULL(sale.SellReturnQty, 0)
                  ELSE 0 END) AS NetOutQty,
         SUM(CASE WHEN COALESCE(sale.DealerId, -1) <> {EXCLUDED_REPLENISHMENT_DEALER_ID}
                       AND customer.CustGroupRef = {AMIRAN_CUSTOMER_GROUP_ID}
                  THEN ISNULL(sale.SellQty, 0) - ISNULL(sale.SellReturnQty, 0)
                  ELSE 0 END) AS AmiranNetOutQty,
         SUM(CASE WHEN COALESCE(sale.DealerId, -1) <> {EXCLUDED_REPLENISHMENT_DEALER_ID}
                       AND COALESCE(customer.CustGroupRef, -1) <> {AMIRAN_CUSTOMER_GROUP_ID}
                  THEN ISNULL(sale.SellQty, 0) - ISNULL(sale.SellReturnQty, 0)
                  ELSE 0 END) AS OtherCustomerNetOutQty,
         SUM(CASE WHEN sale.DealerId = {EXCLUDED_REPLENISHMENT_DEALER_ID}
                  THEN ISNULL(sale.SellQty, 0) - ISNULL(sale.SellReturnQty, 0)
                  ELSE 0 END) AS ExcludedSellerNetQty,
         SUM(ISNULL(sale.SellQty, 0)) AS AllGrossSalesQty,
         CAST(0 AS decimal(38, 3)) AS OnlineTransferOutQty
  FROM dbo.SalesReviewFast AS sale
  LEFT JOIN GNR.tblCust AS customer ON customer.ID = sale.CustomerId
  WHERE sale.ReportDate BETWEEN N'{history_start}' AND N'{period_end}'
    AND sale.StockDcID IN ({stock_refs})
  GROUP BY sale.GoodsId, sale.StockDcID, sale.ReportDate,
           sale.CustomerId, sale.CustomerCategoryId
),
online_transfer_demand AS (
  SELECT item.GoodsRef, transfer.StockDCRef,
         transfer.VocherDate AS ReportDate,
         CAST(NULL AS int) AS CustomerId,
         CAST(NULL AS int) AS CustomerCategoryId,
         CAST(0 AS decimal(38, 3)) AS GrossOutQty,
         CAST(0 AS decimal(38, 3)) AS ReturnQty,
         CAST(0 AS decimal(38, 3)) AS NetOutQty,
         CAST(0 AS decimal(38, 3)) AS AmiranNetOutQty,
         CAST(0 AS decimal(38, 3)) AS OtherCustomerNetOutQty,
         CAST(0 AS decimal(38, 3)) AS ExcludedSellerNetQty,
         CAST(0 AS decimal(38, 3)) AS AllGrossSalesQty,
         SUM(ISNULL(item.TotalQty, 0)) AS OnlineTransferOutQty
  FROM inv.tblVocherHdr AS transfer
  INNER JOIN inv.tblVocherItm AS item ON item.HdrRef = transfer.ID
  WHERE transfer.VocherTypeCode = 65
    AND transfer.ConfirmDate IS NOT NULL
    AND transfer.TStockDCRef = {ONLINE_WAREHOUSE_STOCK_DC_REF}
    AND transfer.StockDCRef IN ({stock_refs})
    AND transfer.VocherDate BETWEEN N'{history_start}' AND N'{period_end}'
  GROUP BY item.GoodsRef, transfer.StockDCRef, transfer.VocherDate
)
SELECT GoodsRef, StockDCRef, ReportDate, CustomerId, CustomerCategoryId,
       GrossOutQty, ReturnQty, NetOutQty, AmiranNetOutQty,
       OtherCustomerNetOutQty, ExcludedSellerNetQty, AllGrossSalesQty,
       OnlineTransferOutQty
FROM sales_demand
UNION ALL
SELECT GoodsRef, StockDCRef, ReportDate, CustomerId, CustomerCategoryId,
       GrossOutQty, ReturnQty, NetOutQty, AmiranNetOutQty,
       OtherCustomerNetOutQty, ExcludedSellerNetQty, AllGrossSalesQty,
       OnlineTransferOutQty
FROM online_transfer_demand
""".strip()
    cardex_sql = f"""
SELECT cardex.GoodsRef, cardex.StockDCRef, cardex.VocherDate,
       SUM(ISNULL(cardex.TotalQty, 0)) AS NetMovementQty
FROM inv.vwGoodsCardex AS cardex
WHERE cardex.VocherDate BETWEEN N'{history_start}' AND N'{period_end}'
  AND cardex.StockDCRef IN ({stock_refs})
  AND cardex.HFlag = 1
  AND cardex.CardexType = 1
GROUP BY cardex.GoodsRef, cardex.StockDCRef, cardex.VocherDate
""".strip()
    receipt_scope_sql = _receipt_scope_sql(
        stock_refs=stock_refs,
        window_start=receipt_window_start,
        window_end=period_end,
    )
    purchase_price_sql = """
WITH ranked_purchase AS (
  SELECT purchase_item.GoodsRef,
         purchase_item.Price AS ApproximatePrice,
         purchase_header.VchDate AS PurchaseDate,
         purchase_header.ID AS InvoiceId,
         ROW_NUMBER() OVER (
           PARTITION BY purchase_item.GoodsRef
           ORDER BY purchase_header.VchDate DESC,
                    purchase_header.ID DESC,
                    purchase_item.ID DESC
         ) AS PurchaseRank
  FROM ICA.TblSupInvoiceHdr AS purchase_header
  INNER JOIN ICA.TblSupInvoiceItm AS purchase_item
          ON purchase_item.HdrRef = purchase_header.ID
  WHERE purchase_header.Status = 1
    AND purchase_header.ConfirmDate IS NOT NULL
    AND ISNULL(purchase_item.Qty, 0) > 0
    AND ISNULL(purchase_item.Price, 0) > 0
)
SELECT GoodsRef, ApproximatePrice, PurchaseDate, InvoiceId
FROM ranked_purchase
WHERE PurchaseRank = 1
""".strip()
    init_warehouse_store(settings)
    purchase_prices, purchase_cache_fresh, purchase_cache_refreshed_at = (
        _purchase_price_cache_snapshot(settings)
    )
    inventory_sql = validate_read_only_sql(inventory_sql).sql
    outflow_sql = validate_read_only_sql(outflow_sql).sql
    cardex_sql = validate_read_only_sql(cardex_sql).sql
    receipt_scope_sql = validate_read_only_sql(receipt_scope_sql).sql
    purchase_price_sql = validate_read_only_sql(purchase_price_sql).sql
    from app import warehouse_receipt_reflection as receipt_reflection
    from app import warehouse_transfer_reflection as transfer_reflection
    from app import warehouse_native_transit as native_transit
    with warehouse_connection(settings) as conn:
        receipt_capture = receipt_reflection.capture(conn)
        transfer_capture = transfer_reflection.capture(conn)

    try:
        with sql_connection(settings) as source:
            # Configure the driver's BEGIN before stock and receipt evidence reads.
            cursor = receipt_reflection.snapshot_cursor(source)
            inventory_rows = _query_rows(cursor, inventory_sql)
            native_transit_rows = native_transit.source_queries(cursor, acc_year)
            receipt_evidence = receipt_reflection.source_queries(cursor, receipt_capture) if receipt_capture else {}
            transfer_evidence = transfer_reflection.source_queries(cursor, transfer_capture) if transfer_capture else {}
            outflow_rows = _query_rows(cursor, outflow_sql)
            cardex_rows = _query_rows(cursor, cardex_sql)
            receipt_scope_rows = _query_rows(cursor, receipt_scope_sql)
            purchase_price_rows = (
                []
                if purchase_cache_fresh
                else _query_rows(cursor, purchase_price_sql)
            )
    except WarehouseAssistantError:
        raise
    except Exception as exc:
        raise WarehouseAssistantError(
            "خواندن موجودی و روند خروج از ورانگر انجام نشد."
        ) from exc

    if not inventory_rows:
        raise WarehouseAssistantError("ورانگر هیچ ردیف موجودی معتبری برنگرداند.")

    purchase_cache_refreshed = False
    if purchase_price_rows:
        purchase_prices, purchase_cache_refreshed_at = (
            _replace_purchase_price_cache(settings, purchase_price_rows)
        )
        purchase_cache_refreshed = True

    warehouse_by_ref = {
        int(config["stock_dc_ref"]): (code, config)
        for code, config in WAREHOUSES.items()
    }
    outflow_by_key: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in outflow_rows:
        if row.get("GoodsRef") is None or row.get("StockDCRef") is None:
            continue
        key = (int(row["GoodsRef"]), int(row["StockDCRef"]))
        outflow_by_key.setdefault(key, []).append(row)
    cardex_by_key: dict[tuple[int, int], dict[str, float]] = {}
    for row in cardex_rows:
        if row.get("GoodsRef") is None or row.get("StockDCRef") is None:
            continue
        key = (int(row["GoodsRef"]), int(row["StockDCRef"]))
        date = _normalize_text(row.get("VocherDate"))
        if date:
            daily = cardex_by_key.setdefault(key, {})
            daily[date] = daily.get(date, 0.0) + _number(
                row.get("NetMovementQty")
            )
    items: list[tuple[Any, ...]] = []
    products: set[str] = set()
    digest = hashlib.sha256(
        f"varanegar|robust-demand-v9-customer-membership|online-transfer-target-{ONLINE_WAREHOUSE_STOCK_DC_REF}|excluded-dealer-{EXCLUDED_REPLENISHMENT_DEALER_ID}|amiran-customer-group-{AMIRAN_CUSTOMER_GROUP_ID}|customer-p{DEMAND_OUTLIER_PERCENTILE}-multiplier-{DEMAND_OUTLIER_MEDIAN_MULTIPLIER}-share-{DEMAND_CUSTOMER_CONCENTRATION_SHARE}-history-{DEMAND_CUSTOMER_HISTORY_DAYS}-recurring-{DEMAND_RECURRING_PATTERN_SHARE}-customers-{DEMAND_RECURRING_MIN_CUSTOMERS}|stale-{ORDER_CYCLE_STALE_DAYS}|{history_start}|{period_end}|{period_days}|".encode("utf-8")
    )
    for source_row, row in enumerate(inventory_rows, start=1):
        stock_ref = int(row.get("StockDCRef") or 0)
        warehouse_match = warehouse_by_ref.get(stock_ref)
        code = _product_code(row.get("GoodsCode"))
        if warehouse_match is None or not code:
            continue
        warehouse_code, config = warehouse_match
        goods_ref = int(row.get("GoodsRef") or 0)
        trend_rows = outflow_by_key.get((goods_ref, stock_ref), [])
        conversion = max(1.0, _number(row.get("ConversionRate")))
        on_hand = _number(row.get("OnHandQty"))
        reserved = max(0.0, _number(row.get("ReservedQty")))
        damaged = max(0.0, _number(row.get("DamagedQty")))
        undelivered = max(0.0, _number(row.get("UnDeliveredQty")))
        open_customer_order = max(0.0, _number(row.get("OpenCustomerOrderQty")))
        unconfirmed_free_invoice = max(
            0.0, _number(row.get("UnconfirmedFreeInvoiceQty"))
        )
        legacy_open_order = max(0.0, _number(row.get("LegacyOpenOrderQty")))
        open_order = max(0.0, _number(row.get("OpenOrderQty")))
        pending_sale_voucher = max(
            0.0, _number(row.get("PendingSaleVoucherQty"))
        )
        demand = _last_stock_window_metrics(
            current_on_hand=on_hand,
            history_dates=history_dates,
            daily_movement=cardex_by_key.get((goods_ref, stock_ref), {}),
            trend_rows=trend_rows,
            period_days=period_days,
        )
        item = (
            source_row,
            warehouse_code,
            config["name"],
            code,
            _normalize_text(row.get("GoodsName")),
            conversion,
            _normalize_text(row.get("ManufacturerName")),
            _normalize_text(row.get("BrandName")),
            _normalize_text(row.get("ManufacturerGoodsCode")),
            _normalize_text(
                row.get("DefaultGoodsBarcode") or row.get("Barcode1")
            ),
            _normalize_text(row.get("Barcode2")),
            _normalize_text(row.get("GoodsBarcodeNameList")),
            on_hand,
            reserved,
            damaged,
            undelivered,
            open_customer_order,
            unconfirmed_free_invoice,
            legacy_open_order,
            open_order,
            pending_sale_voucher,
            demand["net_out"],
            demand["raw_net_out"],
            demand["amiran_net_out"],
            demand["exceptional_out"],
            demand["online_transfer_out"],
            demand["anomaly_days"],
            demand["daily_cap"],
            int(demand["recurring_pattern"]),
            demand["recurring_pattern_days"],
            demand["gross_out"],
            demand["period_return"],
            demand["excluded_seller_qty"],
            demand["sales_rate_days"],
            demand["stockout_days"],
            demand["last_in_stock_date"],
            demand["sales_window_start"],
            demand["sales_window_end"],
            demand["days_since_last_stock"],
            int(demand["ordering_cycle_active"]),
            0.0,
            _number(row.get("SalePrice")),
            _number(row.get("ManufacturerPrice")),
            _number(row.get("ConsumerPrice")),
            purchase_prices.get(goods_ref, 0.0),
            _normalize_text(row.get("GroupLevel3")),
        )
        items.append(item)
        products.add(code)
        digest.update(repr(item).encode("utf-8"))

    if not items:
        raise WarehouseAssistantError("ردیف‌های موجودی ورانگر قابل نگاشت به انبارها نبودند.")

    if receipt_capture:
        digest.update(json.dumps(receipt_evidence,sort_keys=True,ensure_ascii=False).encode('utf-8'))
    if transfer_capture:
        digest.update(json.dumps(transfer_evidence,sort_keys=True,ensure_ascii=False).encode('utf-8'))
    digest.update(json.dumps(native_transit_rows,sort_keys=True,ensure_ascii=False,default=str).encode('utf-8'))
    content_sha256 = digest.hexdigest()
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        receipt_reflection.verify_current(conn, receipt_capture)
        transfer_reflection.verify_current(conn, transfer_capture)
        existing = conn.execute(
            "SELECT * FROM warehouse_snapshots WHERE content_sha256=?",
            (content_sha256,),
        ).fetchone()
        if existing and existing['id'] != conn.execute('SELECT MAX(id) FROM warehouse_snapshots').fetchone()[0]:
            # Reverted stock must become the latest snapshot, not point at an old one.
            content_sha256 = hashlib.sha256((content_sha256+uuid4().hex).encode()).hexdigest()
            existing = None
        if existing:
            if receipt_capture:
                receipt_reflection.apply(conn,receipt_capture,receipt_evidence,int(existing['id']))
            if transfer_capture:
                transfer_reflection.apply(conn,transfer_capture,transfer_evidence,int(existing['id']))
            native_transit.apply(conn,native_transit_rows,transfer_capture,int(existing['id']))
            result = _snapshot_from_row(existing, duplicate=True)
            result["supply_scope"] = _sync_supply_scope(
                conn,
                snapshot_id=int(existing["id"]),
                receipt_rows=receipt_scope_rows,
                window_start=receipt_window_start,
                window_end=period_end,
                username=username,
                strict=True,
            )
            result["varanegar_write"] = False
            result["purchase_price_cache"] = {
                "refreshed": purchase_cache_refreshed,
                "refreshed_at": purchase_cache_refreshed_at,
                "row_count": len(purchase_prices),
            }
            return result

        imported_at = _now()
        cursor = conn.execute(
            """INSERT INTO warehouse_snapshots
               (source_filename, source_sheet, content_sha256, product_count,
                item_count, imported_by, imported_at, source_kind,
                period_start, period_end, period_days, demand_basis)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'varanegar', ?, ?, ?,
                       'net_sales_last_stock_window')""",
            (
                "ورانگر زنده (فقط‌خواندنی)",
                "موجودی، تعهدات، فروش خالص، انتقال آنلاین و روزهای موجودی ورانگر",
                content_sha256,
                len(products),
                len(items),
                username[:100],
                imported_at,
                period_start,
                period_end,
                period_days,
            ),
        )
        snapshot_id = int(cursor.lastrowid)
        conn.executemany(
            """INSERT INTO warehouse_snapshot_items
               (snapshot_id, source_row, warehouse_code, warehouse_name,
                product_code, product_name, conversion_rate, manufacturer, brand,
                manufacturer_product_code, barcode, barcode2, barcode_list,
                stock, reserved, damaged, undelivered, open_customer_order,
                unconfirmed_free_invoice, legacy_open_order, open_order,
                pending_sale_voucher, period_out, raw_period_out,
                amiran_period_out, exceptional_period_out, online_transfer_out,
                demand_anomaly_days, demand_daily_cap,
                demand_recurring_pattern, demand_recurring_pattern_days,
                gross_out, period_return,
                excluded_seller_qty, sales_rate_days, stockout_days,
                last_in_stock_date, sales_window_start, sales_window_end,
                days_since_last_stock, ordering_cycle_active,
                thirty_day_stock, sale_price, manufacturer_price,
                consumer_price, buy_price, group_level3)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(snapshot_id, *item) for item in items],
        )
        if receipt_capture:
            receipt_reflection.apply(conn,receipt_capture,receipt_evidence,snapshot_id)
        if transfer_capture:
            transfer_reflection.apply(conn,transfer_capture,transfer_evidence,snapshot_id)
        native_transit.apply(conn,native_transit_rows,transfer_capture,snapshot_id)
        supply_scope = _sync_supply_scope(
            conn,
            snapshot_id=snapshot_id,
            receipt_rows=receipt_scope_rows,
            window_start=receipt_window_start,
            window_end=period_end,
            username=username,
            strict=True,
        )
        snapshot = conn.execute(
            "SELECT * FROM warehouse_snapshots WHERE id=?", (snapshot_id,)
        ).fetchone()
    result = _snapshot_from_row(snapshot, duplicate=False)
    result["supply_scope"] = supply_scope
    result["varanegar_write"] = False
    result["purchase_price_cache"] = {
        "refreshed": purchase_cache_refreshed,
        "refreshed_at": purchase_cache_refreshed_at,
        "row_count": len(purchase_prices),
    }
    result["sources"] = [
        "FRU.StockGoodsModel",
        "GNR.tblStockGoods",
        "GNR.tblGoods",
        "GNR.tblGoodsGroup",
        "SLE.tblOrderHdr",
        "SLE.tblFreeInvoiceHdr",
        "SLE.tblSaleHdr",
        "dbo.POrder2",
        "dbo.SalesReviewFast",
        "inv.vwGoodsCardex",
        "Inv.tblVocherHdr",
        "Inv.tblVocherItm",
        "GNR.tblSupplier",
        "ICA.TblSupInvoiceHdr",
        "ICA.TblSupInvoiceItm",
    ]
    return result


def _clean_number(value: float) -> int | float:
    rounded = round(float(value), 4)
    return int(rounded) if rounded.is_integer() else rounded


def _inventory_information_item(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    on_hand = float(item.get("stock") or 0)
    reserved = max(0.0, float(item.get("reserved") or 0))
    open_order = max(0.0, float(item.get("open_order") or 0))
    owned_procurement = on_hand + reserved
    physical_procurement = owned_procurement - open_order - float(item.get('transfer_reserved_qty') or 0)
    in_transit = max(0.0, float(item.get("in_transit_qty") or 0))
    pending_receipt = max(0.0, float(item.get("pending_receipt_qty") or 0))
    effective_procurement = physical_procurement + in_transit + pending_receipt
    adjusted_period_out = float(item.get("period_out") or 0)
    raw_period_out = float(item.get("raw_period_out") or adjusted_period_out)
    return {
        "warehouse": item["warehouse_code"],
        "warehouse_name": item["warehouse_name"],
        "product_code": item["product_code"],
        "product_name": item["product_name"],
        "manufacturer": item["manufacturer"],
        "brand": item["brand"],
        "tax_rate": item.get('tax_rate'),
        "tax_status": item.get('tax_status') or 'unknown',
        "tax_updated_at": item.get('tax_updated_at'),
        "purchase_price_validation": item.get('purchase_price_validation'),
        "group_level3": item.get("group_level3") or "",
        "manufacturer_product_code": item.get("manufacturer_product_code") or "",
        "barcode": item.get("barcode") or "",
        "barcode2": item.get("barcode2") or "",
        "barcode_list": item.get("barcode_list") or "",
        "conversion_rate": _clean_number(item["conversion_rate"]),
        "on_hand_qty": _clean_number(on_hand),
        "reserved_qty": _clean_number(reserved),
        "damaged_qty": _clean_number(item.get("damaged") or 0),
        "undelivered_qty": _clean_number(item.get("undelivered") or 0),
        "open_customer_order_qty": _clean_number(
            item.get("open_customer_order") or 0
        ),
        "unconfirmed_free_invoice_qty": _clean_number(
            item.get("unconfirmed_free_invoice") or 0
        ),
        "legacy_open_order_qty": _clean_number(item.get("legacy_open_order") or 0),
        "open_order_qty": _clean_number(open_order),
        "pending_sale_voucher_qty": _clean_number(
            item.get("pending_sale_voucher") or 0
        ),
        "owned_procurement_qty": _clean_number(owned_procurement),
        "effective_procurement_qty": _clean_number(effective_procurement),
        "physical_procurement_qty": _clean_number(physical_procurement),
        "in_transit_qty": _clean_number(in_transit),
        "pending_receipt_qty": _clean_number(pending_receipt),
        "receipt_review_required": bool(item.get('receipt_review_required')),
        "period_out_qty": _clean_number(adjusted_period_out),
        "raw_period_out_qty": _clean_number(raw_period_out),
        "amiran_period_out_qty": _clean_number(item.get("amiran_period_out") or 0),
        "exceptional_period_out_qty": _clean_number(
            item.get("exceptional_period_out") or 0
        ),
        "online_transfer_out_qty": _clean_number(
            item.get("online_transfer_out") or 0
        ),
        "demand_anomaly_days": max(0, int(item.get("demand_anomaly_days") or 0)),
        "demand_daily_cap": (
            None
            if item.get("demand_daily_cap") is None
            else _clean_number(item["demand_daily_cap"])
        ),
        "demand_recurring_pattern": bool(
            item.get("demand_recurring_pattern") or 0
        ),
        "demand_recurring_pattern_days": max(
            0, int(item.get("demand_recurring_pattern_days") or 0)
        ),
        "gross_out_qty": _clean_number(item.get("gross_out") or 0),
        "period_return_qty": _clean_number(item.get("period_return") or 0),
        "sales_rate_days": max(0, int(item.get("sales_rate_days") or 0)),
        "sale_price": _clean_number(item.get("sale_price") or 0),
        "manufacturer_price": _clean_number(item.get("manufacturer_price") or 0),
        "consumer_price": _clean_number(item.get("consumer_price") or 0),
        "last_in_stock_date": item.get("last_in_stock_date"),
        "days_since_last_stock": item.get("days_since_last_stock"),
        "sales_window_start": item.get("sales_window_start"),
        "sales_window_end": item.get("sales_window_end"),
        "system_ordering_cycle_active": bool(
            item.get("ordering_cycle_active", 1)
        ),
        "order_cycle_forced_active": bool(
            item.get("order_cycle_forced_active", 0)
        ),
        "order_cycle_forced_inactive": bool(item.get("order_cycle_forced_inactive", 0)),
        "ordering_cycle_active": bool(
            not item.get("order_cycle_forced_inactive", 0)
            and (item.get("ordering_cycle_active", 1)
                 or item.get("order_cycle_forced_active", 0))
        ),
    }


def _normalize_search_text(value: Any) -> str:
    """Normalize search comparisons without changing persisted product data."""
    text = str(value if value is not None else "").translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫", "01234567890123456789.")
    )
    text = text.translate(str.maketrans({'ي': 'ی', 'ك': 'ک', '\u200c': ' '}))
    text = re.sub(r"(?<=[0-9])[,٬](?=[0-9])", "", text)
    return ' '.join(text.split()).lower()


def list_inventory_information(
    settings: Any,
    *,
    warehouse: str = "",
    search: str = "",
    column_filters: dict[str, str] | None = None,
    limit: int = 250,
    offset: int = 0,
    sort_by: str = "",
    sort_direction: str = "desc",
) -> dict[str, Any]:
    if sort_by and sort_by not in INVENTORY_FILTER_SQL:
        raise WarehouseAssistantError('ستون مرتب‌سازی معتبر نیست.')
    if sort_direction not in ('asc', 'desc'):
        raise WarehouseAssistantError('جهت مرتب‌سازی معتبر نیست.')
    order_sql = 'product_code, warehouse_code'
    if sort_by:
        expression = ('warehouse_tax_rate(product_code)' if sort_by == 'tax_rate'
                      else INVENTORY_FILTER_SQL[sort_by])
        # All expressions come from the fixed allowlist; sort before pagination.
        order_sql = f'({expression} IS NULL), {expression} {sort_direction.upper()}, product_code, warehouse_code'
    if warehouse and warehouse not in WAREHOUSES:
        raise WarehouseAssistantError("انبار انتخاب‌شده معتبر نیست.")
    snapshot = latest_snapshot(settings)
    if snapshot is None:
        raise WarehouseAssistantError("ابتدا داده موجودی را از ورانگر دریافت کنید.")

    clauses = ["snapshot_id = ?"]
    params: list[Any] = [snapshot["id"]]
    if warehouse:
        clauses.append("warehouse_code = ?")
        params.append(warehouse)
    if search.strip():
        clauses.append(
            "(" + " OR ".join(
                f"instr(warehouse_search_text({column}), ?) > 0"
                for column in ("product_code", "product_name", "brand", "manufacturer", "barcode", "manufacturer_product_code", "group_level3")
            ) + ")"
        )
        needle = _normalize_search_text(search)
        params.extend([needle] * 7)
    clean_filters = _inventory_view_values(
        name="فیلتر موقت",
        is_default=False,
        visible_columns=["product_code"],
        filters=column_filters or {},
    )["filters"]
    for key, value in clean_filters.items():
        expression = INVENTORY_FILTER_SQL[key]
        if key=='tax_rate':
            clauses.append(f"{expression} = ?")
            params.append(_normalize_search_text(value))
            continue
        clauses.append(f"instr(warehouse_search_text({expression}), ?) > 0")
        params.append(_normalize_search_text(value))
    where_sql = " AND ".join(clauses)

    with warehouse_connection(settings) as conn:
        conn.create_function("warehouse_search_text", 1, _normalize_search_text, deterministic=True)
        # One consistent ledger view for rows, filters and totals, before pagination.
        # Reuse the ordering ledger; never add incoming goods to physical stock.
        conn.execute("BEGIN")
        from app.warehouse_purchase_contracts import inventory_tax_map
        taxes=inventory_tax_map(conn)
        def tax_value(code):
            value=taxes.get(code,{})
            return value.get('tax_rate') if value.get('tax_status')=='known' else None
        conn.create_function('warehouse_tax_rate',1,tax_value,deterministic=True)
        conn.create_function('warehouse_tax_label',1,lambda code: str(_clean_number(tax_value(code))) if tax_value(code) is not None else 'نامشخص',deterministic=True)
        conn.create_function('warehouse_tax_status',1,lambda code: taxes.get(code,{}).get('tax_status','unknown'),deterministic=True)
        conn.create_function('warehouse_tax_updated',1,lambda code: taxes.get(code,{}).get('updated_at'),deterministic=True)
        if conn.execute('SELECT MAX(id) FROM warehouse_snapshots').fetchone()[0] != snapshot['id']:
            raise WarehouseAssistantError('موجودی به‌روز شده است؛ صفحه را بازخوانی کنید.')
        incoming = {code: supply_position(conn, code)[0]
                    for code in ([warehouse] if warehouse else WAREHOUSES)}
        from app.warehouse_rebalancing import reservations
        outgoing = {code: reservations(conn, code)[1] for code in incoming}
        conn.create_function('warehouse_transfer_reserved', 2,
            lambda code, product: outgoing.get(code, {}).get(product, 0), deterministic=True)
        pending = {code: pending_stock(conn, code) for code in incoming}
        conn.create_function('warehouse_pending_receipt', 2,
            lambda code, product: pending.get(code, ({},set()))[0].get(product,0), deterministic=True)
        conn.create_function('warehouse_receipt_review', 2,
            lambda code, product: int(product in pending.get(code, ({},set()))[1]), deterministic=True)
        conn.create_function("warehouse_in_transit", 2,
            lambda code, product: incoming.get(code, {}).get(product, 0), deterministic=True)
        total_items = int(
            conn.execute(
                f"SELECT COUNT(*) FROM warehouse_snapshot_items WHERE {where_sql}",
                params,
            ).fetchone()[0]
        )
        rows = conn.execute(
            f"""SELECT warehouse_snapshot_items.*,
                       warehouse_tax_rate(product_code) AS tax_rate,
                       warehouse_tax_status(product_code) AS tax_status,
                       warehouse_tax_updated(product_code) AS tax_updated_at,
                       warehouse_in_transit(warehouse_code, product_code) AS in_transit_qty,
                       warehouse_transfer_reserved(warehouse_code, product_code) AS transfer_reserved_qty,
                       warehouse_pending_receipt(warehouse_code, product_code) AS pending_receipt_qty,
                       warehouse_receipt_review(warehouse_code, product_code) AS receipt_review_required,
                       CASE WHEN {ORDER_CYCLE_FORCED_SQL} THEN 1 ELSE 0 END
                         AS order_cycle_forced_active,
                       CASE WHEN {ORDER_CYCLE_BLOCKED_SQL} THEN 1 ELSE 0 END
                         AS order_cycle_forced_inactive
                FROM warehouse_snapshot_items
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?""",
            [*params, limit, offset],
        ).fetchall()
        from app.warehouse_purchase_contracts import inventory_contract_price_status
        price_checks = inventory_contract_price_status(conn, [dict(row) for row in rows], snapshot.get('period_end'))
        rows = [dict(row, purchase_price_validation=price_checks.get((row['warehouse_code'], row['product_code']))) for row in rows]
        totals = conn.execute(
            f"""SELECT
                    COALESCE(SUM(stock), 0) AS on_hand,
                    COALESCE(SUM(reserved), 0) AS reserved,
                    COALESCE(SUM(open_order), 0) AS open_order,
                    COALESCE(SUM(warehouse_in_transit(warehouse_code, product_code)), 0) AS in_transit,
                    COALESCE(SUM(warehouse_pending_receipt(warehouse_code, product_code)), 0) AS pending_receipt,
                    COALESCE(SUM(pending_sale_voucher), 0) AS pending_sale_voucher,
                    COALESCE(SUM(online_transfer_out), 0) AS online_transfer_out,
                    COALESCE(SUM(CASE WHEN NOT {EFFECTIVE_ORDER_CYCLE_SQL}
                                      THEN 1 ELSE 0 END), 0)
                        AS out_of_cycle
                FROM warehouse_snapshot_items WHERE {where_sql}""",
            params,
        ).fetchone()

    owned_total = float(totals["on_hand"]) + float(totals["reserved"])
    effective_total = owned_total - float(totals["open_order"]) + float(totals["in_transit"]) + float(totals["pending_receipt"])
    return {
        "snapshot": snapshot,
        "items": [_inventory_information_item(row) for row in rows],
        "summary": {
            "total_items": total_items,
            "returned_items": len(rows),
            "on_hand_qty": _clean_number(totals["on_hand"]),
            "reserved_qty": _clean_number(totals["reserved"]),
            "open_order_qty": _clean_number(totals["open_order"]),
            "pending_sale_voucher_qty": _clean_number(
                totals["pending_sale_voucher"]
            ),
            "online_transfer_out_qty": _clean_number(
                totals["online_transfer_out"]
            ),
            "effective_procurement_qty": _clean_number(effective_total),
            "in_transit_qty": _clean_number(totals["in_transit"]),
            "pending_receipt_qty": _clean_number(totals["pending_receipt"]),
            "out_of_cycle_items": int(totals["out_of_cycle"]),
        },
        "pagination": {
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(rows) < total_items,
        },
        "formula": "on_hand + reserved - open_order + in_transit + pending_receipt",
        "pending_sale_voucher_already_in_on_hand": True,
        "varanegar_write": False,
    }


def save_order_cycle_override(
    settings: Any,
    username: str,
    *,
    warehouse: str,
    product_code: str,
    mode: str,
) -> dict[str, Any]:
    if warehouse not in WAREHOUSES:
        raise WarehouseAssistantError("انبار انتخاب‌شده معتبر نیست.")
    code = _product_code(product_code)
    if not code:
        raise WarehouseAssistantError("کد کالا الزامی است.")
    if mode not in {"system", "force_active", "force_inactive"}:
        raise WarehouseAssistantError("حالت چرخه سفارش معتبر نیست.")

    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        source = conn.execute(
            """SELECT item.product_name, item.ordering_cycle_active
               FROM warehouse_snapshot_items AS item
               INNER JOIN (
                 SELECT MAX(id) AS snapshot_id FROM warehouse_snapshots
               ) AS latest ON latest.snapshot_id=item.snapshot_id
               WHERE item.warehouse_code=? AND item.product_code=?""",
            (warehouse, code),
        ).fetchone()
        if source is None:
            raise WarehouseAssistantError(
                "کالای انتخاب‌شده در آخرین اطلاعات این انبار پیدا نشد."
            )
        if mode != "system":
            conn.execute(
                """INSERT INTO warehouse_order_cycle_overrides
                     (warehouse_code, product_code, forced_active, updated_by, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(warehouse_code, product_code) DO UPDATE SET
                     forced_active=excluded.forced_active,
                     updated_by=excluded.updated_by,
                     updated_at=excluded.updated_at""",
                (warehouse, code, int(mode == "force_active"), username[:100], _now()),
            )
        else:
            conn.execute(
                """DELETE FROM warehouse_order_cycle_overrides
                   WHERE warehouse_code=? AND product_code=?""",
                (warehouse, code),
            )

    system_active = bool(source["ordering_cycle_active"])
    forced_active = mode == "force_active"
    return {
        "warehouse": warehouse,
        "warehouse_name": WAREHOUSES[warehouse]["name"],
        "product_code": code,
        "product_name": source["product_name"],
        "mode": mode,
        "system_ordering_cycle_active": system_active,
        "order_cycle_forced_active": forced_active,
        "order_cycle_forced_inactive": mode == "force_inactive",
        "ordering_cycle_active": mode != "force_inactive" and (system_active or forced_active),
        "updated_by": username,
    }


def _ensure_supply_scope(
    conn: sqlite3.Connection, snapshot_id: int, username: str = "system"
) -> None:
    if _supply_scope_state(conn) is None:
        _sync_supply_scope(
            conn,
            snapshot_id=snapshot_id,
            receipt_rows=[],
            window_start=None,
            window_end=None,
            username=username,
            strict=False,
        )


def refresh_supply_scope_from_varanegar(
    settings: Any, username: str
) -> dict[str, Any]:
    """Read the last 90 days of confirmed receipts and refresh local scope."""
    if not settings.sql_configured:
        raise WarehouseAssistantError("اتصال فقط‌خواندنی ورانگر تنظیم نشده است.")
    snapshot = latest_snapshot(settings)
    if snapshot is None:
        raise WarehouseAssistantError("ابتدا داده موجودی را از ورانگر دریافت کنید.")
    current = tehran_now()
    window_end = jalali_business_date(current)
    window_start = jalali_business_date(
        current - timedelta(days=SUPPLY_SCOPE_RECEIPT_DAYS - 1)
    )
    stock_refs = ",".join(
        str(int(config["stock_dc_ref"])) for config in WAREHOUSES.values()
    )
    sql = validate_read_only_sql(
        _receipt_scope_sql(
            stock_refs=stock_refs,
            window_start=window_start,
            window_end=window_end,
        )
    ).sql
    try:
        with sql_connection(settings) as source:
            receipt_rows = _query_rows(source.cursor(), sql)
    except Exception as exc:
        raise WarehouseAssistantError(
            "خواندن رسیدهای سه‌ماهه از ورانگر انجام نشد."
        ) from exc
    with warehouse_connection(settings) as conn:
        result = _sync_supply_scope(
            conn,
            snapshot_id=int(snapshot["id"]),
            receipt_rows=receipt_rows,
            window_start=window_start,
            window_end=window_end,
            username=username,
            strict=True,
        )
    result.update(
        receipt_days=SUPPLY_SCOPE_RECEIPT_DAYS,
        source="confirmed_stock_receipts_type_20",
        varanegar_write=False,
    )
    return result


def _supply_scope_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "warehouse_code": str(row["warehouse_code"]),
        "warehouse_name": str(row["warehouse_name"]),
        "supplier": str(row["supplier"]),
        "brand": str(row["brand"]),
        "enabled": bool(row["enabled"]),
        "observed_in_recent_receipts": bool(row["observed_in_recent_receipts"]),
        "receipt_count": int(row["receipt_count"]),
        "receipt_quantity": _clean_number(row["receipt_quantity"]),
        "first_receipt_date": row["first_receipt_date"],
        "last_receipt_date": row["last_receipt_date"],
        "source_supplier_refs": json.loads(row["source_supplier_refs_json"] or "[]"),
        "source_supplier_names": json.loads(row["source_supplier_names_json"] or "[]"),
        "is_user_override": bool(row["is_user_override"]),
        "product_count": int(row["product_count"]),
        "updated_at": str(row["updated_at"]),
        "updated_by": str(row["updated_by"]),
    }


def list_supply_scope(settings: Any, username: str = "system") -> dict[str, Any]:
    snapshot = latest_snapshot(settings)
    if snapshot is None:
        raise WarehouseAssistantError("ابتدا داده موجودی را از ورانگر دریافت کنید.")
    with warehouse_connection(settings) as conn:
        _ensure_supply_scope(conn, int(snapshot["id"]), username)
        state = _supply_scope_state(conn)
        rows = conn.execute(
            """SELECT scope.*,
                      COUNT(DISTINCT item.product_code) AS product_count
               FROM warehouse_supply_scope AS scope
               LEFT JOIN warehouse_snapshot_items AS item
                 ON item.snapshot_id=?
                AND item.warehouse_code=scope.warehouse_code
                AND item.manufacturer=scope.supplier COLLATE NOCASE
                AND item.brand=scope.brand COLLATE NOCASE
               GROUP BY scope.id
               ORDER BY scope.warehouse_code, scope.supplier COLLATE NOCASE,
                        scope.brand COLLATE NOCASE""",
            (snapshot["id"],),
        ).fetchall()
    return {
        "snapshot_id": int(snapshot["id"]),
        "strict_enabled": bool(state["strict_enabled"]),
        "source_kind": str(state["source_kind"]),
        "evidence_window_start": state["evidence_window_start"],
        "evidence_window_end": state["evidence_window_end"],
        "refreshed_at": str(state["refreshed_at"]),
        "rows": [_supply_scope_item(row) for row in rows],
        "varanegar_write": False,
    }


def _invalidate_supply_scope_preorders(
    conn: sqlite3.Connection, warehouse_code: str, supplier: str
) -> None:
    conn.execute(
        """UPDATE warehouse_automatic_preorders
           SET status='superseded'
           WHERE warehouse_code=? AND supplier=? COLLATE NOCASE
             AND status IN ('awaiting_approval', 'approved')
             AND source_supplier_order_id IS NULL""",
        (warehouse_code, supplier),
    )


def save_supply_scope_item(
    settings: Any, username: str, scope_id: int, *, enabled: bool
) -> dict[str, Any]:
    snapshot = latest_snapshot(settings)
    if snapshot is None:
        raise WarehouseAssistantError("ابتدا داده موجودی را از ورانگر دریافت کنید.")
    now = _now()
    with warehouse_connection(settings) as conn:
        row = conn.execute(
            "SELECT * FROM warehouse_supply_scope WHERE id=?", (scope_id,)
        ).fetchone()
        if row is None:
            raise WarehouseAssistantError("ترکیب انبار، تأمین‌کننده و برند پیدا نشد.")
        conn.execute(
            """UPDATE warehouse_supply_scope
               SET enabled=?, is_user_override=1, updated_at=?, updated_by=?
               WHERE id=?""",
            (int(enabled), now, username[:100], scope_id),
        )
        _invalidate_supply_scope_preorders(
            conn, str(row["warehouse_code"]), str(row["supplier"])
        )
        saved = conn.execute(
            """SELECT scope.*,
                      COUNT(DISTINCT item.product_code) AS product_count
               FROM warehouse_supply_scope AS scope
               LEFT JOIN warehouse_snapshot_items AS item
                 ON item.snapshot_id=? AND item.warehouse_code=scope.warehouse_code
                AND item.manufacturer=scope.supplier COLLATE NOCASE
                AND item.brand=scope.brand COLLATE NOCASE
               WHERE scope.id=? GROUP BY scope.id""",
            (snapshot["id"], scope_id),
        ).fetchone()
    return _supply_scope_item(saved)


def save_supplier_supply_scope(
    settings: Any,
    username: str,
    *,
    warehouse: str,
    supplier: str,
    enabled: bool,
) -> dict[str, Any]:
    if warehouse not in WAREHOUSES:
        raise WarehouseAssistantError("انبار انتخاب‌شده معتبر نیست.")
    clean_supplier = _normalize_text(supplier)
    if not clean_supplier:
        raise WarehouseAssistantError("نام تأمین‌کننده الزامی است.")
    now = _now()
    with warehouse_connection(settings) as conn:
        rows = conn.execute(
            """SELECT id FROM warehouse_supply_scope
               WHERE warehouse_code=? AND supplier=? COLLATE NOCASE""",
            (warehouse, clean_supplier),
        ).fetchall()
        if not rows:
            raise WarehouseAssistantError("برای این تأمین‌کننده برندی تعریف نشده است.")
        conn.execute(
            """UPDATE warehouse_supply_scope
               SET enabled=?, is_user_override=1, updated_at=?, updated_by=?
               WHERE warehouse_code=? AND supplier=? COLLATE NOCASE""",
            (int(enabled), now, username[:100], warehouse, clean_supplier),
        )
        _invalidate_supply_scope_preorders(conn, warehouse, clean_supplier)
    return {
        "warehouse_code": warehouse,
        "supplier": clean_supplier,
        "enabled": enabled,
        "updated_count": len(rows),
        "updated_by": username[:100],
    }


def list_ordering_catalog(settings: Any, warehouse: str = "") -> dict[str, Any]:
    if warehouse and warehouse not in WAREHOUSES:
        raise WarehouseAssistantError("انبار انتخاب‌شده معتبر نیست.")
    snapshot = latest_snapshot(settings)
    if snapshot is None:
        raise WarehouseAssistantError("ابتدا داده موجودی را از ورانگر دریافت کنید.")
    with warehouse_connection(settings) as conn:
        _ensure_supply_scope(conn, int(snapshot["id"]))
        strict = _supply_scope_is_strict(conn)
        clauses = ["item.snapshot_id=?", "TRIM(item.manufacturer)<>''"]
        params: list[Any] = [snapshot["id"]]
        if warehouse:
            clauses.append("item.warehouse_code=?")
            params.append(warehouse)
        if strict:
            clauses.append(
                """EXISTS (
                     SELECT 1 FROM warehouse_supply_scope AS scope
                     WHERE scope.warehouse_code=item.warehouse_code
                       AND scope.supplier=item.manufacturer COLLATE NOCASE
                       AND scope.brand=item.brand COLLATE NOCASE
                       AND scope.enabled=1
                   )"""
            )
        rows = conn.execute(
            """SELECT item.manufacturer, item.brand, item.product_code
               FROM warehouse_snapshot_items AS item
               WHERE """ + " AND ".join(clauses) +
            """ GROUP BY item.manufacturer, item.brand, item.product_code
                ORDER BY item.manufacturer COLLATE NOCASE,
                         item.brand COLLATE NOCASE,
                         item.product_code COLLATE NOCASE""",
            params,
        ).fetchall()
    grouped: dict[str, dict[str, set[str]]] = {}
    for row in rows:
        manufacturer = str(row["manufacturer"] or "").strip()
        brand = str(row["brand"] or "").strip()
        product_code = str(row["product_code"] or "")
        manufacturer_entry = grouped.setdefault(manufacturer, {})
        manufacturer_entry.setdefault(brand, set()).add(product_code)
    manufacturers: list[dict[str, Any]] = []
    for manufacturer, brand_map in grouped.items():
        product_codes = set().union(*brand_map.values()) if brand_map else set()
        brands = [
            {"name": brand, "product_count": len(codes)}
            for brand, codes in brand_map.items()
            if brand
        ]
        manufacturers.append(
            {
                "name": manufacturer,
                "product_count": len(product_codes),
                "brands": brands,
            }
        )
    return {
        "snapshot_id": snapshot["id"],
        "warehouse": warehouse,
        "manufacturers": manufacturers,
        "varanegar_write": False,
    }


def _seed_auto_order_settings(
    conn: sqlite3.Connection, snapshot_id: int, username: str
) -> None:
    now = _now()
    strict = _supply_scope_is_strict(conn)
    for warehouse_code, warehouse in WAREHOUSES.items():
        scope_clause = (
            """AND EXISTS (
                 SELECT 1 FROM warehouse_supply_scope AS scope
                 WHERE scope.warehouse_code=warehouse_snapshot_items.warehouse_code
                   AND scope.supplier=warehouse_snapshot_items.manufacturer COLLATE NOCASE
                   AND scope.brand=warehouse_snapshot_items.brand COLLATE NOCASE
                   AND scope.enabled=1
               )"""
            if strict else ""
        )
        conn.execute(
            f"""INSERT OR IGNORE INTO warehouse_supplier_auto_order_settings
               (warehouse_code, warehouse_name, supplier, enabled,
                reorder_coverage_days, target_days, minimum_cartons,
                contact_first_name, contact_last_name, contact_email,
                contact_mobile, created_at, updated_at, updated_by)
               SELECT DISTINCT ?, ?, TRIM(manufacturer), 1, ?, ?, 0,
                      '', '', '', '', ?, ?, ?
               FROM warehouse_snapshot_items
               WHERE snapshot_id=? AND warehouse_code=?
                 AND TRIM(manufacturer)<>'' {scope_clause}""",
            (
                warehouse_code,
                warehouse["name"],
                AUTO_ORDER_DEFAULT_REORDER_DAYS,
                AUTO_ORDER_DEFAULT_TARGET_DAYS,
                now,
                now,
                (username or "system")[:100],
                snapshot_id,
                warehouse_code,
            ),
        )


def _auto_order_setting_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "warehouse_code": str(row["warehouse_code"]),
        "warehouse_name": str(row["warehouse_name"]),
        "supplier": str(row["supplier"]),
        "enabled": bool(row["enabled"]),
        "reorder_coverage_days": int(row["reorder_coverage_days"]),
        "target_days": int(row["target_days"]),
        "minimum_cartons": int(row["minimum_cartons"]),
        "contact_first_name": str(row["contact_first_name"] or ""),
        "contact_last_name": str(row["contact_last_name"] or ""),
        "contact_email": str(row["contact_email"] or ""),
        "contact_mobile": str(row["contact_mobile"] or ""),
        "product_count": int(row["product_count"]),
        "updated_at": str(row["updated_at"]),
        "updated_by": str(row["updated_by"]),
    }


def list_auto_order_settings(
    settings: Any, username: str = "system"
) -> dict[str, Any]:
    """Return independent supplier settings for each warehouse."""
    snapshot = latest_snapshot(settings)
    if snapshot is None:
        raise WarehouseAssistantError("ابتدا داده موجودی را از ورانگر دریافت کنید.")
    with warehouse_connection(settings) as conn:
        _ensure_supply_scope(conn, int(snapshot["id"]), username)
        _seed_auto_order_settings(conn, int(snapshot["id"]), username)
        strict = _supply_scope_is_strict(conn)
        scope_clause = (
            """AND EXISTS (
                 SELECT 1 FROM warehouse_supply_scope AS scope
                 WHERE scope.warehouse_code=item.warehouse_code
                   AND scope.supplier=item.manufacturer COLLATE NOCASE
                   AND scope.brand=item.brand COLLATE NOCASE
                   AND scope.enabled=1
               )"""
            if strict else ""
        )
        rows = conn.execute(
            f"""SELECT cfg.*,
                      COUNT(DISTINCT item.product_code) AS product_count
               FROM warehouse_supplier_auto_order_settings AS cfg
               JOIN warehouse_snapshot_items AS item
                 ON item.snapshot_id=?
                AND item.warehouse_code=cfg.warehouse_code
                AND item.manufacturer=cfg.supplier COLLATE NOCASE
                {scope_clause}
               GROUP BY cfg.id
               ORDER BY cfg.warehouse_code, cfg.supplier COLLATE NOCASE""",
            (snapshot["id"],),
        ).fetchall()
    return {
        "snapshot_id": int(snapshot["id"]),
        "defaults": {
            "reorder_coverage_days": AUTO_ORDER_DEFAULT_REORDER_DAYS,
            "target_days": AUTO_ORDER_DEFAULT_TARGET_DAYS,
            "minimum_cartons": 0,
        },
        "settings": [_auto_order_setting_from_row(row) for row in rows],
        "scope": "supplier_per_warehouse",
        "varanegar_write": False,
    }


def _normalize_mobile(value: str) -> str:
    translated = _normalize_text(value).translate(
        str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    )
    return re.sub(r"[\s()\-]", "", translated)


def save_auto_order_setting(
    settings: Any,
    username: str,
    setting_id: int,
    *,
    enabled: bool,
    reorder_coverage_days: int,
    target_days: int,
    minimum_cartons: int,
    contact_first_name: str,
    contact_last_name: str,
    contact_email: str,
    contact_mobile: str,
) -> dict[str, Any]:
    if not 0 <= reorder_coverage_days <= 180:
        raise WarehouseAssistantError("کاوریج شروع سفارش باید بین صفر تا ۱۸۰ روز باشد.")
    if not 1 <= target_days <= 180 or target_days <= reorder_coverage_days:
        raise WarehouseAssistantError(
            "روز پوشش هدف باید از کاوریج شروع سفارش بیشتر و حداکثر ۱۸۰ باشد."
        )
    if not 0 <= minimum_cartons <= 1_000_000:
        raise WarehouseAssistantError("حداقل سفارش باید بین صفر تا یک میلیون کارتن باشد.")

    first_name = _normalize_text(contact_first_name)
    last_name = _normalize_text(contact_last_name)
    email = _normalize_text(contact_email).casefold()
    mobile = _normalize_mobile(contact_mobile)
    if len(first_name) > 80 or len(last_name) > 100:
        raise WarehouseAssistantError("نام یا نام خانوادگی مسئول بیش از حد مجاز است.")
    if len(email) > 254 or (
        email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
    ):
        raise WarehouseAssistantError("ایمیل مسئول تأمین‌کننده معتبر نیست.")
    if mobile and not re.fullmatch(r"\+?\d{10,15}", mobile):
        raise WarehouseAssistantError("شماره موبایل باید ۱۰ تا ۱۵ رقم باشد.")

    from app.warehouse_supplier_portal import _init as init_portal
    init_portal(settings)
    now = _now()
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        current = conn.execute(
            "SELECT * FROM warehouse_supplier_auto_order_settings WHERE id=?",
            (setting_id,),
        ).fetchone()
        if current is None:
            raise WarehouseAssistantError("تنظیمات تأمین‌کننده پیدا نشد.")
        if _supply_scope_is_strict(conn):
            active = conn.execute(
                """SELECT 1 FROM warehouse_supply_scope
                   WHERE warehouse_code=? AND supplier=? COLLATE NOCASE
                     AND enabled=1 LIMIT 1""",
                (current["warehouse_code"], current["supplier"]),
            ).fetchone()
            if active is None:
                raise WarehouseAssistantError(
                    "این تأمین‌کننده برای انبار انتخاب‌شده فعال نیست."
                )
        from app.warehouse_portal_access import sync_setting_phone
        sync_setting_phone(conn,current,mobile,username)
        conn.execute(
            """UPDATE warehouse_supplier_auto_order_settings
               SET enabled=?, reorder_coverage_days=?, target_days=?,
                   minimum_cartons=?, contact_first_name=?, contact_last_name=?,
                   contact_email=?, contact_mobile=?, updated_at=?, updated_by=?
               WHERE id=?""",
            (
                int(enabled), reorder_coverage_days, target_days,
                minimum_cartons, first_name, last_name, email, mobile,
                now, username[:100], setting_id,
            ),
        )
        row = conn.execute(
            """SELECT cfg.*,
                      COALESCE((SELECT COUNT(DISTINCT item.product_code)
                                FROM warehouse_snapshot_items AS item
                                WHERE item.snapshot_id=(SELECT MAX(id) FROM warehouse_snapshots)
                                  AND item.warehouse_code=cfg.warehouse_code
                                  AND item.manufacturer=cfg.supplier COLLATE NOCASE
                                  AND EXISTS (
                                    SELECT 1 FROM warehouse_supply_scope AS scope
                                    WHERE scope.warehouse_code=item.warehouse_code
                                      AND scope.supplier=item.manufacturer COLLATE NOCASE
                                      AND scope.brand=item.brand COLLATE NOCASE
                                      AND scope.enabled=1
                                  )), 0)
                        AS product_count
               FROM warehouse_supplier_auto_order_settings AS cfg WHERE cfg.id=?""",
            (setting_id,),
        ).fetchone()
    return _auto_order_setting_from_row(row)


def preview_auto_orders(settings: Any, username: str, warehouse: str) -> dict[str, Any]:
    if warehouse not in WAREHOUSES:
        raise WarehouseAssistantError("انبار انتخاب‌شده معتبر نیست.")
    configuration = list_auto_order_settings(settings, username)
    suppliers: list[dict[str, Any]] = []
    for item in configuration["settings"]:
        if item["warehouse_code"] != warehouse:
            continue
        preview = dict(item)
        if not item["enabled"]:
            preview.update(
                suggested_items=0,
                suggested_cartons=0,
                minimum_shortfall_cartons=0,
                ready_to_prepare=False,
                readiness_status="disabled",
            )
        else:
            suggestions = build_suggestions(
                settings,
                warehouse=warehouse,
                manufacturer=str(item["supplier"]),
                reorder_coverage_days=int(item["reorder_coverage_days"]),
                target_days=int(item["target_days"]),
                safety_days=0,
                period_days=60,
                only_needed=True,
                limit=5000,
            )
            cartons = int(suggestions["summary"]["suggested_cartons"])
            minimum = int(item["minimum_cartons"])
            ready = cartons > 0 and cartons >= minimum
            status = "ready" if ready else ("no_need" if cartons == 0 else "below_minimum")
            preview.update(
                suggested_items=int(suggestions["summary"]["matched_items"]),
                suggested_cartons=cartons,
                minimum_shortfall_cartons=max(0, minimum - cartons),
                ready_to_prepare=ready,
                readiness_status=status,
            )
        suppliers.append(preview)
    return {
        "snapshot_id": configuration["snapshot_id"],
        "warehouse": {"code": warehouse, "name": WAREHOUSES[warehouse]["name"]},
        "suppliers": suppliers,
        "ready_suppliers": sum(1 for item in suppliers if item["ready_to_prepare"]),
        "documents_created": False,
        "varanegar_write": False,
    }


def _supplier_portal_order_status(
    conn: sqlite3.Connection, document_kind: str, document_id: int
) -> dict[str, Any] | None:
    table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_supplier_portal_assignments'"
    ).fetchone()
    if table is None:
        return None
    row = conn.execute(
        """SELECT id,status,requested_delivery_date,proposed_delivery_date,
                  revision,updated_at,submitted_at,decided_at,decided_by
           FROM warehouse_supplier_portal_assignments
           WHERE document_kind=? AND document_id=?""",
        (document_kind, document_id),
    ).fetchone()
    if row is None:
        return None
    result = dict(row)
    from app.warehouse_portal_publication import state as publication_state
    publication=publication_state(conn,result['id'])
    dispatched = False
    dispatch_locked = False
    for attempt_table in (
        "warehouse_supplier_portal_sms_attempts",
        "warehouse_supplier_portal_email_attempts",
    ):
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (attempt_table,)
        ).fetchone()
        if exists:
            epoch_filter=' AND publication_epoch=?' if publication else ''
            args=(result['id'],publication['epoch']) if publication else (result['id'],)
            attempts = conn.execute(
                f"SELECT status,created_at FROM {attempt_table} WHERE assignment_id=?"+epoch_filter,args
            ).fetchall()
            dispatched = dispatched or any(a["status"] == "sent" for a in attempts)
            dispatch_locked = dispatch_locked or any(a["status"] in {"sent", "sending", "unknown"} for a in attempts)
            dates = [a['created_at'] for a in attempts if a['status'] == 'sent']
            if dates:
                result['dispatch_at'] = min([result.get('dispatch_at') or min(dates), *dates])
    raw_status = str(result["status"])
    result['pending_quantity_changes'] = conn.execute(
        'SELECT COUNT(*) FROM warehouse_supplier_portal_response_lines WHERE assignment_id=? AND original_cartons<>proposed_cartons',
        (result['id'],)
    ).fetchone()[0] if raw_status == 'submitted' else 0
    if raw_status == "submitted":
        workflow_status = "awaiting_negin"
    elif raw_status == "accepted":
        workflow_status = (
            "supplier_confirmed"
            if str(result.get("decided_by") or "").startswith("supplier:")
            else "awaiting_delivery"
        )
    elif raw_status in {"draft", "changes_requested"}:
        workflow_status = "awaiting_supplier"
    elif raw_status == "rejected":
        workflow_status = "rejected"
    elif raw_status == "cancelled":
        workflow_status = "cancelled"
    else:
        workflow_status = "awaiting_supplier" if dispatched else "awaiting_link"
    # A response proves the supplier has accessed the order, even for legacy
    # invitations delivered outside this app. Failed delivery alone never does.
    responded = raw_status in {"draft", "submitted", "accepted", "changes_requested", "rejected"}
    result["dispatch_sent"] = dispatched or responded
    result["dispatch_locked"] = dispatch_locked or responded or raw_status == "cancelled"
    result["workflow_status"] = workflow_status
    result['first_viewed_at']=publication.get('first_viewed_at') if publication else None
    result['can_withdraw']=bool(publication and not publication['withdrawn_at'] and not publication['first_viewed_at'] and raw_status=='awaiting_supplier')
    result['notification_status']='sent' if dispatched else 'pending_or_unknown' if dispatch_locked else 'not_sent'
    if publication:
        active=not publication['withdrawn_at']
        result.update(published_at=publication['published_at'],publication_epoch=publication['epoch'],
                      publication_state='published' if active else 'withdrawn',dispatch_sent=active,dispatch_locked=active)
        result['dispatch_at']=publication['published_at'] if active else None
        if not active: result['workflow_status']='awaiting_link'
        elif raw_status=='awaiting_supplier': result['workflow_status']='awaiting_supplier'
    return result


def _apply_order_workflow(conn, order, document_kind, document_id):
    """Navigation stages, separate from approval and the incoming-stock ledger."""
    from app.warehouse_order_delivery import apply_delivery_date
    apply_delivery_date(conn, order, document_kind, document_id)
    portal = order.get("supplier_portal") or {}
    delivery = order.get("email_delivery") or {}
    statuses = {delivery.get("status")}
    email_table, id_column = (("warehouse_supplier_order_email_attempts", "order_id")
                             if document_kind == "supplier_order" else ("warehouse_email_attempts", "preorder_id"))
    statuses.update(r[0] for r in conn.execute(
        f"SELECT status FROM {email_table} WHERE {id_column}=?", (document_id,)))
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='warehouse_sms_downloads'").fetchone():
        statuses.update(r[0] for r in conn.execute(
            "SELECT status FROM warehouse_sms_downloads WHERE document_kind=? AND document_id=?",
            (document_kind, document_id)))
    sent = bool(portal.get("dispatch_sent")) or "sent" in statuses
    locked = bool(portal.get("dispatch_locked")) or bool(statuses & {"sent", "sending", "unknown"})
    order["dispatch_locked"] = locked
    order['dispatched_at'] = portal.get('dispatch_at') or (delivery.get('completed_at') if delivery.get('status') == 'sent' else None)
    if sent and not portal.get('dispatch_sent'):
        portal['legacy_delivery_sent'] = True
        order['supplier_portal'] = portal
    order["order_stage"] = "delivery" if portal.get("status") == "accepted" else "sent" if sent else "draft"
    approved = bool(order.get("approved_at")) if document_kind == "supplier_order" else order.get("status") in {"approved", "send_requested"}
    order["can_edit"] = not approved and not locked and not order.get("deleted") and order.get("status") in {"prepared", "awaiting_approval"}
    order['can_edit_delivery_date']=not locked and not order.get('deleted') and order.get('status') in {'prepared','awaiting_approval','approved','send_requested'}
    order["can_send_portal"] = approved and not locked and not order.get("deleted")
    order["can_delete"] = order.get("can_delete", not order.get("deleted")) and not locked
    order["can_revoke_approval"] = approved and not locked and not order.get("deleted")
    order["can_approve"] = not approved and not locked and not order.get("deleted")


def _automatic_preorder_from_row(
    conn: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, Any]:
    preorder = dict(row)
    from app.warehouse_rebalancing import reservations
    transfer_outgoing = reservations(conn, preorder['warehouse_code'])[1]
    in_transit_by_product, _position_revision = supply_position(
        conn, preorder["warehouse_code"]
    )
    pending_by_product, receipt_review = pending_stock(
        conn, preorder["warehouse_code"]
    )
    line_rows = conn.execute(
        """SELECT lines.warehouse_code, lines.warehouse_name,
                   lines.product_code, lines.product_name, lines.brand,
                   lines.conversion_rate, lines.system_suggested_cartons,
                   lines.unadjusted_suggested_cartons,
                  lines.order_quantity, lines.cartons,
                  lines.manufacturer_price, lines.consumer_price,
                  lines.buy_price, lines.buy_price AS approximate_price,
                  lines.estimated_value,
                  items.stock AS current_stock,
                  items.manufacturer_product_code, items.barcode, items.manufacturer,
                  COALESCE(items.group_level3, '') AS group_level3,
                  items.reserved AS current_reserved,
                  items.open_order AS current_open_order,
                  items.period_out AS current_period_out,
                  items.raw_period_out AS current_raw_period_out,
                  items.amiran_period_out AS current_amiran_period_out,
                  items.exceptional_period_out AS current_exceptional_period_out,
                  items.online_transfer_out AS current_online_transfer_out,
                  items.demand_anomaly_days AS current_demand_anomaly_days,
                  items.demand_daily_cap AS current_demand_daily_cap,
                  items.demand_recurring_pattern AS current_demand_recurring_pattern,
                  items.demand_recurring_pattern_days AS current_demand_recurring_pattern_days,
                  items.sales_rate_days AS current_sales_rate_days,
                  snapshots.period_days AS current_period_days,
                  snapshots.demand_basis AS current_demand_basis
           FROM warehouse_automatic_preorder_lines AS lines
           LEFT JOIN warehouse_snapshots AS snapshots
             ON snapshots.id=?
           LEFT JOIN warehouse_snapshot_items AS items
             ON items.snapshot_id=snapshots.id
            AND items.warehouse_code=lines.warehouse_code
            AND items.product_code=lines.product_code
           WHERE lines.preorder_id=?
           ORDER BY lines.brand, lines.product_name""",
        (preorder["snapshot_id"], preorder["id"]),
    ).fetchall()
    preorder_lines: list[dict[str, Any]] = []
    for line_row in line_rows:
        line = dict(line_row)
        stock = line.pop("current_stock")
        reserved = line.pop("current_reserved")
        open_order = line.pop("current_open_order")
        period_out = line.pop("current_period_out")
        raw_period_out = line.pop("current_raw_period_out")
        amiran_period_out = line.pop("current_amiran_period_out")
        exceptional_period_out = line.pop("current_exceptional_period_out")
        online_transfer_out = line.pop("current_online_transfer_out")
        demand_anomaly_days = line.pop("current_demand_anomaly_days")
        demand_daily_cap = line.pop("current_demand_daily_cap")
        demand_recurring_pattern = line.pop("current_demand_recurring_pattern")
        demand_recurring_pattern_days = line.pop(
            "current_demand_recurring_pattern_days"
        )
        recorded_rate_days = line.pop("current_sales_rate_days")
        period_days = line.pop("current_period_days")
        demand_basis = line.pop("current_demand_basis")
        if stock is None:
            line.update(
                effective_procurement_qty=None,
                physical_procurement_qty=None,
                in_transit_qty=None,
                pending_receipt_qty=None,
                inventory_position_qty=None,
                average_daily_out=None,
                sales_rate_days=0,
                period_out_qty=None,
                coverage_days=None,
                raw_period_out=None,
                adjusted_period_out=None,
                amiran_period_out=None,
                exceptional_period_out=None,
                online_transfer_out=None,
                demand_anomaly_days=0,
                demand_daily_cap=None,
                demand_recurring_pattern=False,
                demand_recurring_pattern_days=0,
            )
        else:
            physical_procurement = (
                float(stock)
                + max(0.0, float(reserved or 0))
                - max(0.0, float(open_order or 0))
            )
            product_code = str(line["product_code"])
            physical_procurement -= transfer_outgoing.get(product_code, 0)
            in_transit = max(
                0.0, float(in_transit_by_product.get(product_code) or 0)
            )
            pending_receipt = max(
                0.0, float(pending_by_product.get(product_code) or 0)
            )
            inventory_position = physical_procurement + in_transit + pending_receipt
            uses_adjusted_sales = demand_basis in {
                "net_sales_stockout_adjusted",
                LAST_STOCK_DEMAND_BASIS,
            }
            rate_days = (
                max(0, int(recorded_rate_days or 0))
                if uses_adjusted_sales
                else max(0, int(period_days or 60))
            )
            daily_out = (
                max(0.0, float(period_out or 0)) / rate_days
                if rate_days > 0
                else 0.0
            )
            coverage_days = (
                inventory_position / daily_out if daily_out > 0 else None
            )
            line.update(
                # Compatibility field: older clients used this as warehouse-only
                # availability. New clients show the complete breakdown below.
                effective_procurement_qty=_clean_number(physical_procurement),
                physical_procurement_qty=_clean_number(physical_procurement),
                in_transit_qty=_clean_number(in_transit),
                pending_receipt_qty=_clean_number(pending_receipt),
                inventory_position_qty=_clean_number(inventory_position),
                receipt_review_required=product_code in receipt_review,
                average_daily_out=_clean_number(daily_out),
                sales_rate_days=rate_days,
                period_out_qty=_clean_number(period_out or 0),
                # Keep precision for the strict <4-day Excel priority boundary.
                # Display formatting belongs to the client.
                coverage_days=coverage_days,
                raw_period_out=_clean_number(raw_period_out or period_out or 0),
                adjusted_period_out=_clean_number(period_out or 0),
                amiran_period_out=_clean_number(amiran_period_out or 0),
                exceptional_period_out=_clean_number(exceptional_period_out or 0),
                online_transfer_out=_clean_number(online_transfer_out or 0),
                demand_anomaly_days=max(0, int(demand_anomaly_days or 0)),
                demand_daily_cap=(
                    None
                    if demand_daily_cap is None
                    else _clean_number(demand_daily_cap)
                ),
                demand_recurring_pattern=bool(demand_recurring_pattern or 0),
                demand_recurring_pattern_days=max(
                    0, int(demand_recurring_pattern_days or 0)
                ),
            )
        preorder_lines.append(line)
    preorder["lines"] = preorder_lines
    delivery = conn.execute(
        """SELECT recipient, sender, status, message_id, requested_by, started_at,
                  completed_at, error,
                  (SELECT COUNT(*) FROM warehouse_email_attempts WHERE preorder_id=?) AS attempts
           FROM warehouse_email_attempts WHERE preorder_id=? ORDER BY id DESC LIMIT 1""",
        (preorder['id'], preorder['id']),
    ).fetchone()
    preorder['email_delivery'] = dict(delivery) if delivery else None
    delivery_locked = conn.execute(
        """SELECT 1 FROM warehouse_email_attempts WHERE preorder_id=?
           AND status IN ('sending', 'sent', 'unknown') LIMIT 1""",
        (preorder['id'],),
    ).fetchone() is not None
    # Contact details are live supplier configuration, not order quantities.
    # A delivery claim freezes the contact snapshot for historical/audit accuracy.
    if not delivery_locked and preorder['status'] in ('awaiting_approval', 'approved', 'send_requested'):
        contact = conn.execute(
            """SELECT contact_first_name, contact_last_name, contact_email, contact_mobile
               FROM warehouse_supplier_auto_order_settings
               WHERE id=? AND warehouse_code=?""",
            (preorder['supplier_setting_id'], preorder['warehouse_code']),
        ).fetchone()
        if contact is not None:
            preorder.update(dict(contact))
    preorder['can_revoke_approval'] = (
        preorder['status'] in ('approved', 'send_requested')
        and not delivery_locked
    )
    preorder['can_delete'] = (
        not delivery_locked
        and preorder['status'] in ('awaiting_approval', 'approved', 'send_requested')
        and (preorder['status'] in ('approved', 'send_requested') or preorder['business_date'] == jalali_business_date(tehran_now()))
    )
    # Confirm the exact approved content and recipient seen by the user.
    preorder['email_send_token'] = hashlib.sha256(json.dumps({
        'id': preorder['id'], 'email': preorder['contact_email'],
        'approved_at': preorder['approved_at'], 'generation_key': preorder['generation_key'],
        'lines': [(line['product_code'], line['cartons'], line['order_quantity'],
                   line['manufacturer_price'], line['consumer_price'], line['approximate_price'])
                  for line in preorder_lines],
    }, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    preorder["contact_full_name"] = " ".join(
        part
        for part in (
            str(preorder.get("contact_first_name") or "").strip(),
            str(preorder.get("contact_last_name") or "").strip(),
        )
        if part
    )
    source_supplier_order_id = preorder.get("source_supplier_order_id")
    portal_kind = "supplier_order" if source_supplier_order_id is not None else "automatic_preorder"
    portal_document_id = (
        int(source_supplier_order_id)
        if source_supplier_order_id is not None
        else int(preorder["id"])
    )
    preorder["supplier_portal"] = _supplier_portal_order_status(
        conn, portal_kind, portal_document_id
    )
    if preorder["supplier_portal"] is None and preorder.get("approved_at"):
        preorder["supplier_portal"] = {
            "status": "awaiting_link", "workflow_status": "awaiting_link",
            "dispatch_sent": False,
        }
    _apply_order_workflow(conn, preorder, portal_kind, portal_document_id)
    return preorder


def _replace_automatic_preorder_lines(
    conn: sqlite3.Connection,
    preorder_id: int,
    setting: dict[str, Any],
    suggestions: dict[str, Any],
) -> None:
    conn.execute(
        "DELETE FROM warehouse_automatic_preorder_lines WHERE preorder_id=?",
        (preorder_id,),
    )
    conn.executemany(
        """INSERT INTO warehouse_automatic_preorder_lines
           (preorder_id, warehouse_code, warehouse_name, product_code,
            product_name, brand, conversion_rate,
            system_suggested_cartons, unadjusted_suggested_cartons,
            order_quantity, cartons,
            manufacturer_price, consumer_price, buy_price, estimated_value)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                preorder_id,
                setting["warehouse_code"],
                setting["warehouse_name"],
                item["product_code"],
                item["product_name"],
                item["brand"],
                item["conversion_rate"],
                item["suggested_cartons"],
                item["unadjusted_suggested_cartons"],
                item["suggested_quantity"],
                item["suggested_cartons"],
                item["manufacturer_price"],
                item["consumer_price"],
                item["buy_price"],
                item["estimated_value"],
            )
            for item in suggestions["items"]
        ],
    )


def prepare_automatic_preorders(
    settings: Any, username: str, *, trigger: str = "manual"
) -> dict[str, Any]:
    """Upsert today's supplier drafts and remove obsolete open suggestions."""
    configuration = list_auto_order_settings(settings, username)
    snapshot_id = int(configuration["snapshot_id"])
    evaluations: list[dict[str, Any]] = []
    candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    position_revisions = {}

    for setting in configuration["settings"]:
        if not setting["enabled"]:
            evaluations.append(
                {
                    "setting_id": setting["id"],
                    "supplier": setting["supplier"],
                    "warehouse_code": setting["warehouse_code"],
                    "warehouse_name": setting["warehouse_name"],
                    "status": "disabled",
                    "suggested_items": 0,
                    "suggested_cartons": 0,
                    "minimum_cartons": setting["minimum_cartons"],
                }
            )
            continue
        suggestions = build_suggestions(
            settings,
            warehouse=str(setting["warehouse_code"]),
            manufacturer=str(setting["supplier"]),
            reorder_coverage_days=int(setting["reorder_coverage_days"]),
            target_days=int(setting["target_days"]),
            safety_days=0,
            period_days=60,
            only_needed=True,
            limit=5000,
        )
        revision = suggestions['parameters']['incoming_supply_revision']
        warehouse_code = str(setting['warehouse_code'])
        if warehouse_code in position_revisions and position_revisions[warehouse_code] != revision:
            raise WarehouseAssistantError('بار در راه هنگام محاسبه تغییر کرد؛ بازسازی را دوباره اجرا کنید.')
        position_revisions[warehouse_code] = revision
        cartons = int(suggestions["summary"]["suggested_cartons"])
        minimum = int(setting["minimum_cartons"])
        eligible = cartons > 0 and (minimum == 0 or cartons >= minimum)
        evaluation = {
            "setting_id": setting["id"],
            "supplier": setting["supplier"],
            "warehouse_code": setting["warehouse_code"],
            "warehouse_name": setting["warehouse_name"],
            "status": (
                "eligible"
                if eligible
                else ("no_need" if cartons == 0 else "below_minimum")
            ),
            "suggested_items": int(suggestions["summary"]["matched_items"]),
            "suggested_cartons": cartons,
            "minimum_cartons": minimum,
        }
        evaluations.append(evaluation)
        if eligible:
            candidates.append((setting, suggestions))

    created_ids: list[int] = []
    updated_ids: list[int] = []
    unchanged_ids: list[int] = []
    protected_sent_ids: list[int] = []
    removed_count = 0
    now = _now()
    business_date = jalali_business_date(tehran_now())
    clean_trigger = _normalize_text(trigger)[:30] or "manual"
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        for warehouse_code, revision in position_revisions.items():
            if supply_position(conn, warehouse_code)[1] != revision:
                raise WarehouseAssistantError('بار در راه هنگام محاسبه تغییر کرد؛ بازسازی را دوباره اجرا کنید.')
        # The active queue is strictly a same-business-day worklist.  Retire
        # every unfinished row from an earlier day before evaluating today's
        # settings, including rows whose supplier disappeared from the latest
        # snapshot and therefore no longer participates in evaluation.
        removed_count += conn.execute(
            """UPDATE warehouse_automatic_preorders
               SET status='superseded', last_refreshed_at=?, refresh_trigger=?
               WHERE status='awaiting_approval'
                 AND source_supplier_order_id IS NULL
                 AND COALESCE(business_date, '')<>?""",
            (now, clean_trigger, business_date),
        ).rowcount
        eligible_setting_ids = {int(setting["id"]) for setting, _ in candidates}
        for evaluation in evaluations:
            setting_id = int(evaluation["setting_id"])
            if setting_id not in eligible_setting_ids:
                removed_count += conn.execute(
                    """UPDATE warehouse_automatic_preorders
                       SET status='superseded'
                       WHERE supplier_setting_id=?
                         AND status='awaiting_approval'
                         AND source_supplier_order_id IS NULL""",
                    (setting_id,),
                ).rowcount

        for setting, suggestions in candidates:
            stable_lines = [
                (
                    str(item["product_code"]),
                    int(item["suggested_cartons"]),
                    _clean_number(item["suggested_quantity"]),
                )
                for item in suggestions["items"]
            ]
            stable_lines.sort()
            generation_payload = {
                "business_date": business_date,
                "setting_id": int(setting["id"]),
                "warehouse_code": setting["warehouse_code"],
                "reorder_coverage_days": int(setting["reorder_coverage_days"]),
                "target_days": int(setting["target_days"]),
                "minimum_cartons": int(setting["minimum_cartons"]),
                "lines": stable_lines,
            }
            if suggestions['parameters']['incoming_supply_revision']:
                generation_payload['incoming_supply_revision'] = suggestions['parameters']['incoming_supply_revision']
            generation_key = hashlib.sha256(
                json.dumps(
                    generation_payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            sent_today = conn.execute(
                """SELECT id FROM warehouse_automatic_preorders
                   WHERE supplier_setting_id=? AND business_date=?
                     AND source_supplier_order_id IS NULL
                     AND status='send_requested'
                     AND NOT EXISTS(SELECT 1 FROM warehouse_email_attempts e
                         WHERE e.preorder_id=warehouse_automatic_preorders.id AND e.status='sent')
                   ORDER BY id DESC LIMIT 1""",
                (setting["id"], business_date),
            ).fetchone()
            if sent_today is not None:
                protected_sent_ids.append(int(sent_today["id"]))
                continue

            existing = conn.execute(
                """SELECT * FROM warehouse_automatic_preorders
                   WHERE supplier_setting_id=? AND business_date=?
                     AND source_supplier_order_id IS NULL
                     AND status='awaiting_approval'
                   ORDER BY id DESC LIMIT 1""",
                (setting["id"], business_date),
            ).fetchone()
            if existing is not None:
                changed = str(existing["generation_key"]) != generation_key
                if changed:
                    conn.execute(
                        """UPDATE warehouse_automatic_preorders
                           SET generation_key=?, snapshot_id=?, status=?,
                               reorder_coverage_days=?, target_days=?,
                               minimum_cartons=?, item_count=?, total_quantity=?,
                               total_cartons=?, estimated_value=?,
                               contact_first_name=?, contact_last_name=?,
                               contact_email=?, contact_mobile=?,
                               last_refreshed_at=?, refresh_trigger=?,
                               approved_by=CASE WHEN ? THEN NULL ELSE approved_by END,
                               approved_at=CASE WHEN ? THEN NULL ELSE approved_at END
                           WHERE id=?""",
                        (
                            generation_key, snapshot_id,
                            existing["status"],
                            setting["reorder_coverage_days"], setting["target_days"],
                            setting["minimum_cartons"],
                            int(suggestions["summary"]["matched_items"]),
                            suggestions["summary"]["suggested_quantity"],
                            suggestions["summary"]["suggested_cartons"],
                            suggestions["summary"]["estimated_value"],
                            setting["contact_first_name"], setting["contact_last_name"],
                            setting["contact_email"], setting["contact_mobile"],
                            now, clean_trigger, 0, 0,
                            existing["id"],
                        ),
                    )
                    _replace_automatic_preorder_lines(
                        conn, int(existing["id"]), setting, suggestions
                    )
                    updated_ids.append(int(existing["id"]))
                else:
                    conn.execute(
                        """UPDATE warehouse_automatic_preorders
                           SET snapshot_id=?, contact_first_name=?,
                               contact_last_name=?, contact_email=?, contact_mobile=?,
                               last_refreshed_at=?, refresh_trigger=?
                           WHERE id=?""",
                        (
                            snapshot_id, setting["contact_first_name"],
                            setting["contact_last_name"], setting["contact_email"],
                            setting["contact_mobile"], now, clean_trigger,
                            existing["id"],
                        ),
                    )
                    unchanged_ids.append(int(existing["id"]))
                continue

            removed_count += conn.execute(
                """UPDATE warehouse_automatic_preorders
                   SET status='superseded'
                   WHERE supplier_setting_id=?
                     AND status='awaiting_approval'
                     AND source_supplier_order_id IS NULL""",
                (setting["id"],),
            ).rowcount
            cursor = conn.execute(
                """INSERT INTO warehouse_automatic_preorders
                   (generation_key, snapshot_id, supplier_setting_id,
                    warehouse_code, warehouse_name, supplier, status,
                    reorder_coverage_days, target_days, minimum_cartons,
                    item_count, total_quantity, total_cartons, estimated_value,
                    contact_first_name, contact_last_name, contact_email,
                    contact_mobile, created_by, created_at, business_date,
                    last_refreshed_at, refresh_trigger)
                   VALUES (?, ?, ?, ?, ?, ?, 'awaiting_approval', ?, ?, ?,
                           ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    generation_key,
                    snapshot_id,
                    setting["id"],
                    setting["warehouse_code"],
                    setting["warehouse_name"],
                    setting["supplier"],
                    setting["reorder_coverage_days"],
                    setting["target_days"],
                    setting["minimum_cartons"],
                    int(suggestions["summary"]["matched_items"]),
                    suggestions["summary"]["suggested_quantity"],
                    suggestions["summary"]["suggested_cartons"],
                    suggestions["summary"]["estimated_value"],
                    setting["contact_first_name"],
                    setting["contact_last_name"],
                    setting["contact_email"],
                    setting["contact_mobile"],
                    username[:100],
                    now,
                    business_date,
                    now,
                    clean_trigger,
                ),
            )
            preorder_id = int(cursor.lastrowid)
            preorder_number = f"AUTO-{now[:10].replace('-', '')}-{preorder_id:06d}"
            conn.execute(
                "UPDATE warehouse_automatic_preorders SET preorder_number=? WHERE id=?",
                (preorder_number, preorder_id),
            )
            _replace_automatic_preorder_lines(
                conn, preorder_id, setting, suggestions
            )
            created_ids.append(preorder_id)

        active_rows = conn.execute(
            """SELECT * FROM warehouse_automatic_preorders
               WHERE (business_date=? OR status IN ('approved', 'send_requested'))
                 AND source_supplier_order_id IS NULL
                 AND status IN ('awaiting_approval', 'approved', 'send_requested')
                 AND NOT EXISTS(SELECT 1 FROM warehouse_email_attempts e
                     WHERE e.preorder_id=warehouse_automatic_preorders.id AND e.status='sent')
               ORDER BY id DESC""",
            (business_date,),
        ).fetchall()
        preorders = [_automatic_preorder_from_row(conn, row) for row in active_rows]
        preorders = [order for order in preorders if order['order_stage'] == 'draft']
    return {
        "snapshot_id": snapshot_id,
        "evaluated_settings": len(evaluations),
        "eligible_settings": len(candidates),
        "created_count": len(created_ids),
        "updated_count": len(updated_ids),
        "reused_count": len(unchanged_ids),
        "removed_count": removed_count,
        "protected_sent_count": len(protected_sent_ids),
        "business_date": business_date,
        "trigger": clean_trigger,
        "evaluations": evaluations,
        "preorders": preorders,
        "external_delivery_performed": False,
        "varanegar_write": False,
    }


def automatic_refresh_status(settings: Any) -> dict[str, Any]:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        row = conn.execute(
            "SELECT * FROM warehouse_automatic_refresh_state WHERE id=1"
        ).fetchone()
    if row is None:
        return {
            "running": False,
            "last_started_at": None,
            "last_completed_at": None,
            "last_success_at": None,
            "last_trigger": None,
            "last_error": None,
            "last_result": None,
            "next_run_at": None,
            "interval_seconds": AUTOMATIC_REFRESH_INTERVAL_SECONDS,
        }
    now = _now()
    running = bool(
        row["lock_token"]
        and row["lock_expires_at"]
        and str(row["lock_expires_at"]) > now
    )
    next_run_at = None
    if row["last_completed_at"]:
        next_run_at = (
            datetime.fromisoformat(str(row["last_completed_at"]))
            + timedelta(seconds=AUTOMATIC_REFRESH_INTERVAL_SECONDS)
        ).isoformat()
    try:
        last_result = json.loads(row["last_result_json"] or "null")
    except json.JSONDecodeError:
        last_result = None
    return {
        "running": running,
        "last_started_at": row["last_started_at"],
        "last_completed_at": row["last_completed_at"],
        "last_success_at": row["last_success_at"],
        "last_trigger": row["last_trigger"],
        "last_error": row["last_error"],
        "last_result": last_result,
        "next_run_at": next_run_at,
        "interval_seconds": AUTOMATIC_REFRESH_INTERVAL_SECONDS,
    }


def automatic_refresh_due(settings: Any) -> bool:
    # Operator-controlled test pause; retain every supplier rule and allow manual tests.
    if warehouse_database_path(settings).with_name("warehouse-automatic-orders.paused").exists():
        return False
    status = automatic_refresh_status(settings)
    if status["running"]:
        return False
    last_completed = status["last_completed_at"]
    if not last_completed:
        return True
    return (
        datetime.now(timezone.utc) - datetime.fromisoformat(str(last_completed))
    ).total_seconds() >= AUTOMATIC_REFRESH_INTERVAL_SECONDS


def run_automatic_order_cycle(
    settings: Any,
    username: str,
    *,
    trigger: str,
    refresh_inventory: bool = True,
) -> dict[str, Any]:
    """Single-flight refresh of source data and today's automatic drafts."""
    init_warehouse_store(settings)
    token = uuid4().hex
    started_at = _now()
    lock_expires_at = (
        datetime.now(timezone.utc)
        + timedelta(minutes=AUTOMATIC_REFRESH_LOCK_MINUTES)
    ).replace(microsecond=0).isoformat()
    with warehouse_connection(settings) as conn:
        conn.execute(
            """INSERT OR IGNORE INTO warehouse_automatic_refresh_state
               (id, last_started_at, last_trigger)
               VALUES (1, NULL, NULL)"""
        )
        claimed = conn.execute(
            """UPDATE warehouse_automatic_refresh_state
               SET lock_token=?, lock_expires_at=?, last_started_at=?,
                   last_trigger=?, last_error=NULL
               WHERE id=1 AND (
                 lock_token IS NULL OR lock_expires_at IS NULL
                 OR lock_expires_at<=?
               )""",
            (token, lock_expires_at, started_at, trigger[:30], started_at),
        ).rowcount
    if not claimed:
        return {
            "skipped": True,
            "reason": "already_running",
            "status": automatic_refresh_status(settings),
            "varanegar_write": False,
        }

    try:
        snapshot_result = None
        if refresh_inventory and settings.sql_configured:
            snapshot_result = sync_varanegar_snapshot(
                settings, username, period_days=60
            )
        result = prepare_automatic_preorders(
            settings, username, trigger=trigger
        )
        result["snapshot_refreshed"] = snapshot_result is not None
        result["snapshot_duplicate"] = (
            bool(snapshot_result.get("duplicate")) if snapshot_result else None
        )
        completed_at = _now()
        summary = {
            key: result[key]
            for key in (
                "snapshot_id", "evaluated_settings", "eligible_settings",
                "created_count", "updated_count", "reused_count",
                "removed_count", "protected_sent_count", "business_date",
                "trigger", "snapshot_refreshed", "snapshot_duplicate",
            )
        }
        with warehouse_connection(settings) as conn:
            conn.execute(
                """UPDATE warehouse_automatic_refresh_state
                   SET last_completed_at=?, last_success_at=?, last_error=NULL,
                       last_result_json=?, lock_token=NULL, lock_expires_at=NULL
                   WHERE id=1 AND lock_token=?""",
                (
                    completed_at, completed_at,
                    json.dumps(summary, ensure_ascii=False), token,
                ),
            )
        result["skipped"] = False
        result["refresh_status"] = automatic_refresh_status(settings)
        return result
    except Exception as exc:
        completed_at = _now()
        with warehouse_connection(settings) as conn:
            conn.execute(
                """UPDATE warehouse_automatic_refresh_state
                   SET last_completed_at=?, last_error=?, last_result_json=NULL,
                       lock_token=NULL, lock_expires_at=NULL
                   WHERE id=1 AND lock_token=?""",
                (completed_at, str(exc)[:1000], token),
            )
        if isinstance(exc, WarehouseAssistantError):
            raise
        raise WarehouseAssistantError(
            "به‌روزرسانی خودکار سفارش‌ها انجام نشد."
        ) from exc


def list_automatic_preorders(settings: Any, limit: int = 200) -> list[dict[str, Any]]:
    init_warehouse_store(settings)
    business_date = jalali_business_date(tehran_now())
    with warehouse_connection(settings) as conn:
        rows = conn.execute(
            """SELECT * FROM warehouse_automatic_preorders
               WHERE (business_date=? OR status IN ('approved', 'send_requested'))
                 AND source_supplier_order_id IS NULL
                 AND status IN ('awaiting_approval', 'approved', 'send_requested')
                 AND NOT EXISTS(SELECT 1 FROM warehouse_email_attempts e
                     WHERE e.preorder_id=warehouse_automatic_preorders.id AND e.status='sent')
               ORDER BY id DESC""",
            (business_date,),
        ).fetchall()
        orders = []
        for row in rows:
            portal_status = _supplier_portal_order_status(conn, 'automatic_preorder', row['id']) or {}
            if portal_status.get('dispatch_sent'):
                continue
            order = _automatic_preorder_from_row(conn, row)
            if order['order_stage'] == 'draft':
                orders.append(order)
                if len(orders) >= limit:
                    break
        return orders


def get_automatic_preorder(settings: Any, preorder_id: int) -> dict[str, Any]:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        row = conn.execute(
            "SELECT * FROM warehouse_automatic_preorders WHERE id=?",
            (preorder_id,),
        ).fetchone()
        if row is None:
            raise WarehouseAssistantError("پیش‌سفارش اتوماتیک پیدا نشد.")
        return _automatic_preorder_from_row(conn, row)


def update_automatic_preorder_lines(
    settings: Any,
    username: str,
    preorder_id: int,
    lines: list[dict[str, Any]],
    *, expected_token: str | None = None,
    allow_approved_portal_response: bool = False,
    _connection: sqlite3.Connection | None = None,
    delivery_date: str | None = None,
) -> dict[str, Any]:
    """Update carton counts and totals; approved edits are reserved for portal review."""
    from app.warehouse_order_delivery import clean_delivery_date, write_date
    if delivery_date is not None:
        if not expected_token or allow_approved_portal_response:
            raise WarehouseAssistantError('ذخیرهٔ یکپارچه فقط برای پیش‌نویس با نسخهٔ معتبر مجاز است.')
        delivery_date = clean_delivery_date(delivery_date, optional=True)
    if not lines or len(lines) > 500:
        raise WarehouseAssistantError("اقلام پیش‌سفارش برای ویرایش معتبر نیستند.")
    requested: dict[str, int] = {}
    for line in lines:
        product_code = _product_code(line.get("product_code"))
        cartons = line.get("cartons")
        if not product_code or product_code in requested:
            raise WarehouseAssistantError("کد کالاهای پیش‌سفارش معتبر یا یکتا نیست.")
        if isinstance(cartons, bool) or not isinstance(cartons, int):
            raise WarehouseAssistantError("تعداد کارتن باید عدد صحیح باشد.")
        if cartons < 0 or cartons > 1_000_000:
            raise WarehouseAssistantError("تعداد کارتن هر قلم باید بین صفر تا یک میلیون باشد؛ صفر یعنی حذف قلم.")
        requested[product_code] = cartons
    if not any(cartons > 0 for cartons in requested.values()):
        raise WarehouseAssistantError("حداقل یک قلم باید در سفارش باقی بماند؛ برای حذف کل سفارش از دکمه حذف سفارش استفاده کنید.")

    if _connection is None:
        init_warehouse_store(settings)
    now = _now()
    with (warehouse_connection(settings) if _connection is None else nullcontext(_connection)) as conn:
        if _connection is None:
            conn.execute('BEGIN IMMEDIATE')
        preorder = conn.execute(
            "SELECT * FROM warehouse_automatic_preorders WHERE id=?",
            (preorder_id,),
        ).fetchone()
        if preorder is None:
            raise WarehouseAssistantError("پیش‌سفارش اتوماتیک پیدا نشد.")
        if preorder["source_supplier_order_id"] is not None:
            raise WarehouseAssistantError("سفارش دستی فقط از بخش سفارش‌های دستی قابل تغییر است.")
        approved_portal_edit = (
            allow_approved_portal_response
            and preorder["status"] in {"approved", "send_requested"}
        )
        if (
            not approved_portal_edit
            and str(preorder["business_date"] or "") != jalali_business_date(tehran_now())
        ):
            raise WarehouseAssistantError(
                "این پیش‌سفارش متعلق به روز جاری نیست؛ صف را به‌روزرسانی کنید."
            )
        if preorder["status"] != "awaiting_approval" and not approved_portal_edit:
            raise WarehouseAssistantError(
                "پیش‌سفارش فقط تا قبل از تأیید قابل ویرایش است."
            )
        from app.warehouse_preorder_catalog import ensure_editable, catalog_items
        if approved_portal_edit:
            fulfillment_activity = conn.execute(
                """SELECT 1 FROM warehouse_fulfillment_receipts WHERE preorder_id=?
                   UNION ALL SELECT 1 FROM warehouse_receipt_allocations WHERE preorder_id=?
                   UNION ALL SELECT 1 FROM warehouse_fulfillment_adjustments WHERE preorder_id=?
                   LIMIT 1""",
                (preorder_id, preorder_id, preorder_id),
            ).fetchone()
            if fulfillment_activity:
                raise WarehouseAssistantError(
                    "برای این سفارش دریافت یا تعدیل ثبت شده و تغییر تعداد دیگر ممکن نیست."
                )
        else:
            ensure_editable(conn, preorder)
        ensure_orderable(conn, preorder['warehouse_code'], [code for code, cartons in requested.items() if cartons > 0])
        current_token = _automatic_preorder_from_row(conn, preorder)['email_send_token']
        if expected_token is not None and expected_token != current_token:
            raise WarehouseAssistantError('سفارش تغییر کرده است؛ پیش‌نمایش را دوباره باز کنید.')
        existing = conn.execute(
            """SELECT product_code, conversion_rate, buy_price
               FROM warehouse_automatic_preorder_lines WHERE preorder_id=?""",
            (preorder_id,),
        ).fetchall()
        existing_codes = {str(row["product_code"]) for row in existing}
        if not existing_codes.issubset(requested):
            raise WarehouseAssistantError(
                "برای ذخیره پیش‌نمایش باید تعداد همه اقلام همین سفارش ارسال شود."
            )
        additions = {code for code, cartons in requested.items() if cartons > 0} - existing_codes
        if additions:
            if approved_portal_edit:
                raise WarehouseAssistantError(
                    "پاسخ تأمین‌کننده نمی‌تواند کالای تازه‌ای به سفارش تأییدشده اضافه کند."
                )
            if expected_token is None:
                raise WarehouseAssistantError('برای افزودن کالا، پیش‌نمایش جدید را باز کنید.')
            catalog = {item['product_code']: item for item in catalog_items(conn, preorder)}
            for code in additions:
                item = catalog.get(code)
                if item is None or not item['can_add']:
                    raise WarehouseAssistantError('کالای انتخاب‌شده در تأمین مجاز همین تأمین‌کننده و انبار نیست.')
                conn.execute('''INSERT INTO warehouse_automatic_preorder_lines
                    (preorder_id,warehouse_code,warehouse_name,product_code,product_name,brand,
                     conversion_rate,system_suggested_cartons,unadjusted_suggested_cartons,
                     order_quantity,cartons,manufacturer_price,consumer_price,buy_price,estimated_value)
                    VALUES(?,?,?,?,?,?,?,0,0,0,0,?,?,?,0)''',
                    (preorder_id,preorder['warehouse_code'],preorder['warehouse_name'],code,
                     item['product_name'],item['brand'],max(1, item['conversion_rate']),
                     item['manufacturer_price'],item['consumer_price'],item['approximate_price']))
            existing = conn.execute('SELECT product_code,conversion_rate,buy_price FROM warehouse_automatic_preorder_lines WHERE preorder_id=?', (preorder_id,)).fetchall()

        removed_codes = [code for code in existing_codes if requested[code] == 0]
        if removed_codes:
            marks = ",".join("?" for _ in removed_codes)
            conn.execute(
                f"DELETE FROM warehouse_automatic_preorder_lines WHERE preorder_id=? AND product_code IN ({marks})",
                (preorder_id, *removed_codes),
            )
            existing = [row for row in existing if str(row["product_code"]) not in removed_codes]

        total_quantity = 0.0
        total_cartons = 0
        estimated_value = 0.0
        for row in existing:
            product_code = str(row["product_code"])
            cartons = requested[product_code]
            conversion_rate = max(1.0, _number(row["conversion_rate"]))
            quantity = cartons * conversion_rate
            line_value = quantity * max(0.0, _number(row["buy_price"]))
            conn.execute(
                """UPDATE warehouse_automatic_preorder_lines
                   SET cartons=?, order_quantity=?, estimated_value=?
                   WHERE preorder_id=? AND product_code=?""",
                (cartons, quantity, line_value, preorder_id, product_code),
            )
            total_quantity += quantity
            total_cartons += cartons
            estimated_value += line_value
        conn.execute(
            """UPDATE warehouse_automatic_preorders
               SET total_quantity=?, total_cartons=?, estimated_value=?, item_count=?,
                   edited_by=?, edited_at=? WHERE id=?""",
            (
                total_quantity, total_cartons, estimated_value, len(existing),
                username[:100], now, preorder_id,
            ),
        )
        if delivery_date is not None:
            write_date(conn, 'automatic_preorder', preorder_id, delivery_date, username, now)
        updated = conn.execute(
            "SELECT * FROM warehouse_automatic_preorders WHERE id=?",
            (preorder_id,),
        ).fetchone()
        return _automatic_preorder_from_row(conn, updated)


def transition_automatic_preorder(
    settings: Any, username: str, preorder_id: int, action: str
) -> dict[str, Any]:
    if action not in {"approve", "request_send", "revoke_approval", "delete"}:
        raise WarehouseAssistantError("عملیات پیش‌سفارش معتبر نیست.")
    init_warehouse_store(settings)
    # Microseconds prevent reuse of a stale confirmation after rapid re-approval.
    now = datetime.now(timezone.utc).isoformat()
    with warehouse_connection(settings) as conn:
        # Serialize revocation against the SMTP delivery claim and refresh writes.
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT * FROM warehouse_automatic_preorders WHERE id=?",
            (preorder_id,),
        ).fetchone()
        if row is None:
            raise WarehouseAssistantError("پیش‌سفارش اتوماتیک پیدا نشد.")
        if row["source_supplier_order_id"] is not None:
            raise WarehouseAssistantError("سفارش دستی فقط از بخش سفارش‌های دستی قابل تغییر است.")
        if str(row["business_date"] or "") != jalali_business_date(tehran_now()) and not (action in {'revoke_approval', 'delete'} and row['status'] in {'approved', 'send_requested'}):
            raise WarehouseAssistantError(
                "این پیش‌سفارش متعلق به روز جاری نیست؛ صف را به‌روزرسانی کنید."
            )
        current_status = str(row["status"])
        if action in {"approve", "request_send"}:
            ensure_cycle_allowed(conn, row["warehouse_code"], [line[0] for line in conn.execute(
                "SELECT product_code FROM warehouse_automatic_preorder_lines WHERE preorder_id=?", (preorder_id,))])
        if action == "delete":
            if not _automatic_preorder_from_row(conn, row)['can_delete']:
                raise WarehouseAssistantError('سفارش ارسال‌شده، در حال ارسال یا با نتیجه نامشخص قابل حذف نیست.')
            # Preserve the entire record, freeing the old deterministic key so
            # the next rebuild may create the same requirement as a new draft.
            conn.execute("""UPDATE warehouse_automatic_preorders SET status='cancelled',
                generation_key=?,edited_by=?,edited_at=? WHERE id=?""",
                (f"deleted:{preorder_id}:{row['generation_key']}", username[:100], now, preorder_id))
        elif action == "revoke_approval":
            preorder = _automatic_preorder_from_row(conn, row)
            if not preorder['can_revoke_approval']:
                raise WarehouseAssistantError(
                    "لغو تأیید فقط پیش از ارسال ممکن است؛ سفارش ارسال‌شده، در حال ارسال یا با نتیجه نامشخص قابل بازگشت نیست."
                )
            conn.execute(
                """UPDATE warehouse_automatic_preorders
                   SET status='awaiting_approval', approved_by=NULL, approved_at=NULL,
                       send_requested_by=NULL, send_requested_at=NULL,
                       edited_by=?, edited_at=?, business_date=? WHERE id=?""",
                (username[:100], now, jalali_business_date(tehran_now()), preorder_id),
            )
        elif action == "approve":
            if current_status == "approved":
                return _automatic_preorder_from_row(conn, row)
            if current_status != "awaiting_approval":
                raise WarehouseAssistantError("این پیش‌سفارش دیگر منتظر تأیید نیست.")
            conn.execute(
                """UPDATE warehouse_automatic_preorders
                   SET status='approved', approved_by=?, approved_at=? WHERE id=?""",
                (username[:100], now, preorder_id),
            )
        else:
            if current_status == "send_requested":
                return _automatic_preorder_from_row(conn, row)
            if current_status != "approved":
                raise WarehouseAssistantError(
                    "ابتدا پیش‌سفارش را تأیید کنید و سپس دستور ارسال بدهید."
                )
            if not str(_automatic_preorder_from_row(conn, row)["contact_email"] or "").strip():
                raise WarehouseAssistantError(
                    "برای ثبت دستور ارسال، ابتدا ایمیل تأمین‌کننده را در تنظیمات وارد کنید."
                )
            conn.execute(
                """UPDATE warehouse_automatic_preorders
                   SET status='send_requested', send_requested_by=?,
                       send_requested_at=? WHERE id=?""",
                (username[:100], now, preorder_id),
            )
        updated = conn.execute(
            "SELECT * FROM warehouse_automatic_preorders WHERE id=?",
            (preorder_id,),
        ).fetchone()
        return _automatic_preorder_from_row(conn, updated)


def automatic_preorder_text(preorder: dict[str, Any]) -> str:
    lines = [
        "پیش‌سفارش خرید نگین پخش",
        f"شماره: {preorder['preorder_number']}",
        f"تأمین‌کننده: {preorder['supplier']}",
        f"انبار مقصد: {preorder['warehouse_name']}",
        f"تاریخ آماده‌سازی: {preorder['created_at']}",
        "",
        "ردیف | کد کالا | نام کالا | برند | تعداد | کارتن | قیمت تولیدکننده | قیمت مصرف‌کننده | قیمت حدودی | ارزش تخمینی",
    ]
    for index, item in enumerate(preorder["lines"], start=1):
        lines.append(
            f"{index} | {item['product_code']} | {item['product_name']} | "
            f"{item['brand'] or '-'} | {_clean_number(item['order_quantity'])} | "
            f"{item['cartons']} | {_clean_number(item['manufacturer_price'])} | "
            f"{_clean_number(item['consumer_price'])} | "
            f"{_clean_number(item['approximate_price'])} | "
            f"{_clean_number(item['estimated_value'])}"
        )
    lines.extend(
        [
            "",
            f"جمع تعداد: {_clean_number(preorder['total_quantity'])}",
            f"جمع کارتن: {preorder['total_cartons']}",
            f"ارزش تخمینی: {_clean_number(preorder['estimated_value'])}",
        ]
    )
    return "\n".join(lines)


def build_suggestions(
    settings: Any,
    *,
    warehouse: str,
    manufacturer: str = "",
    brand: str = "",
    search: str = "",
    reorder_coverage_days: int = 15,
    target_days: int = 30,
    safety_days: int = 0,
    period_days: int = 60,
    only_needed: bool = True,
    limit: int = 200,
) -> dict[str, Any]:
    if warehouse not in WAREHOUSES:
        raise WarehouseAssistantError("انبار انتخاب‌شده معتبر نیست.")
    if target_days + safety_days <= reorder_coverage_days:
        raise WarehouseAssistantError(
            "روز پوشش هدف باید از کاوریج شروع سفارش بیشتر باشد."
        )
    snapshot = latest_snapshot(settings)
    if snapshot is None:
        raise WarehouseAssistantError("ابتدا داده موجودی را از ورانگر دریافت کنید.")
    effective_period_days = int(snapshot.get("period_days") or period_days)

    clauses = ["snapshot_id=?", "warehouse_code=?"]
    params: list[Any] = [snapshot["id"], warehouse]
    if manufacturer.strip():
        clauses.append("manufacturer = ? COLLATE NOCASE")
        params.append(manufacturer.strip())
    if brand.strip():
        clauses.append("brand = ? COLLATE NOCASE")
        params.append(brand.strip())
    if search.strip():
        search_columns = ("product_code", "product_name", "manufacturer_product_code",
                          "barcode", "manufacturer", "brand", "group_level3")
        clauses.append("(" + " OR ".join(
            f"warehouse_search_text({column}) LIKE ?" for column in search_columns
        ) + ")")
        params.extend([f"%{_normalize_search_text(search)}%"] * len(search_columns))
    with warehouse_connection(settings) as conn:
        conn.create_function("warehouse_search_text", 1, _normalize_search_text, deterministic=True)
        conn.execute('BEGIN')
        if conn.execute('SELECT MAX(id) FROM warehouse_snapshots').fetchone()[0] != snapshot['id']:
            raise WarehouseAssistantError('موجودی به‌روز شده است؛ صفحه را بازخوانی کنید.')
        _ensure_supply_scope(conn, int(snapshot["id"]))
        if _supply_scope_is_strict(conn):
            clauses.append(
                """EXISTS (
                     SELECT 1 FROM warehouse_supply_scope AS scope
                     WHERE scope.warehouse_code=warehouse_snapshot_items.warehouse_code
                       AND scope.supplier=warehouse_snapshot_items.manufacturer COLLATE NOCASE
                       AND scope.brand=warehouse_snapshot_items.brand COLLATE NOCASE
                       AND scope.enabled=1
                   )"""
            )
        rows = conn.execute(
            "SELECT warehouse_snapshot_items.*, CASE WHEN "
            + ORDER_CYCLE_FORCED_SQL
            + " THEN 1 ELSE 0 END AS order_cycle_forced_active, CASE WHEN "
            + ORDER_CYCLE_BLOCKED_SQL
            + " THEN 1 ELSE 0 END AS order_cycle_forced_inactive "
            + "FROM warehouse_snapshot_items WHERE "
            + " AND ".join(clauses)
            + " ORDER BY manufacturer, brand, product_name LIMIT 5000",
            params,
        ).fetchall()

        incoming_by_product, incoming_revision = supply_position(conn, warehouse)
        from app.warehouse_rebalancing import reservations
        transfer_outgoing = reservations(conn, warehouse)[1]
        pending_by_product, receipt_review = pending_stock(conn, warehouse)

    uses_last_stock_window = (
        snapshot.get("demand_basis") == LAST_STOCK_DEMAND_BASIS
    )
    results: list[dict[str, Any]] = []
    excluded_stale_items = 0
    excluded_manual_items = 0
    for row in rows:
        item = dict(row)
        system_cycle_active = bool(item.get("ordering_cycle_active", 1))
        forced_cycle_active = bool(item.get("order_cycle_forced_active", 0))
        forced_cycle_inactive = bool(item.get("order_cycle_forced_inactive", 0))
        effective_cycle_active = not forced_cycle_inactive and (system_cycle_active or forced_cycle_active)
        if forced_cycle_inactive:
            excluded_manual_items += 1
            continue
        if uses_last_stock_window and not effective_cycle_active:
            excluded_stale_items += 1
            continue
        stock = float(item["stock"])
        reserved = max(0.0, float(item["reserved"]))
        open_order = max(0.0, float(item.get("open_order") or 0))
        period_out = max(0.0, float(item["period_out"]))
        raw_period_out = max(
            period_out, float(item.get("raw_period_out") or period_out)
        )
        amiran_period_out = max(0.0, float(item.get("amiran_period_out") or 0))
        exceptional_period_out = max(
            0.0, float(item.get("exceptional_period_out") or 0)
        )
        demand_anomaly_days = max(0, int(item.get("demand_anomaly_days") or 0))
        demand_daily_cap = item.get("demand_daily_cap")
        demand_recurring_pattern = bool(
            item.get("demand_recurring_pattern") or 0
        )
        demand_recurring_pattern_days = max(
            0, int(item.get("demand_recurring_pattern_days") or 0)
        )
        conversion = max(1.0, float(item["conversion_rate"]))
        owned_procurement = stock + reserved
        available = owned_procurement - open_order - transfer_outgoing.get(str(item['product_code']), 0)
        in_transit = incoming_by_product.get(str(item['product_code']), 0.0)
        pending_receipt = pending_by_product.get(str(item['product_code']), 0.0)
        ordering_blocked = str(item['product_code']) in receipt_review
        inventory_position = available + in_transit + pending_receipt
        recorded_rate_days = max(0, int(item.get("sales_rate_days") or 0))
        uses_adjusted_sales = (
            snapshot.get("demand_basis")
            in {"net_sales_stockout_adjusted", LAST_STOCK_DEMAND_BASIS}
        )
        sales_rate_days = (
            recorded_rate_days if uses_adjusted_sales else effective_period_days
        )
        daily_out = period_out / sales_rate_days if sales_rate_days > 0 else 0.0
        unadjusted_daily_out = (
            raw_period_out / sales_rate_days if sales_rate_days > 0 else 0.0
        )
        coverage_days = inventory_position / daily_out if daily_out > 0 else None
        unadjusted_coverage_days = (
            inventory_position / unadjusted_daily_out if unadjusted_daily_out > 0 else None
        )
        needs_reorder = (
            not ordering_blocked and coverage_days is not None
            and coverage_days < reorder_coverage_days
        )
        target_quantity = daily_out * (target_days + safety_days)
        raw_requirement = (
            max(0.0, target_quantity - inventory_position) if needs_reorder else 0.0
        )
        cartons = math.ceil(raw_requirement / conversion) if raw_requirement > 0 else 0
        unadjusted_needs_reorder = (
            not ordering_blocked and unadjusted_coverage_days is not None
            and unadjusted_coverage_days < reorder_coverage_days
        )
        unadjusted_target_quantity = unadjusted_daily_out * (
            target_days + safety_days
        )
        unadjusted_requirement = (
            max(0.0, unadjusted_target_quantity - inventory_position)
            if unadjusted_needs_reorder
            else 0.0
        )
        unadjusted_cartons = (
            math.ceil(unadjusted_requirement / conversion)
            if unadjusted_requirement > 0
            else 0
        )
        suggested = cartons * conversion
        if only_needed and not needs_reorder:
            continue
        results.append(
            {
                "product_code": item["product_code"],
                "product_name": item["product_name"],
                "manufacturer": item["manufacturer"],
                "brand": item["brand"],
                "group_level3": item.get("group_level3") or "",
                "manufacturer_product_code": item.get("manufacturer_product_code") or "",
                "barcode": item.get("barcode") or "",
                "warehouse": item["warehouse_code"],
                "warehouse_name": item["warehouse_name"],
                "stock": _clean_number(stock),
                "reserved": _clean_number(reserved),
                "damaged_qty": _clean_number(item.get("damaged") or 0),
                "undelivered_qty": _clean_number(item.get("undelivered") or 0),
                "open_customer_order_qty": _clean_number(
                    item.get("open_customer_order") or 0
                ),
                "unconfirmed_free_invoice_qty": _clean_number(
                    item.get("unconfirmed_free_invoice") or 0
                ),
                "legacy_open_order_qty": _clean_number(
                    item.get("legacy_open_order") or 0
                ),
                "open_order_qty": _clean_number(open_order),
                "pending_sale_voucher_qty": _clean_number(
                    item.get("pending_sale_voucher") or 0
                ),
                "owned_procurement_qty": _clean_number(owned_procurement),
                "effective_procurement_qty": _clean_number(available),
                "available_quantity": _clean_number(available),
                "in_transit_qty": _clean_number(in_transit),
                "inventory_position_qty": _clean_number(inventory_position),
                "pending_receipt_qty": _clean_number(pending_receipt),
                "receipt_review_required": ordering_blocked,
                "stock_coverage_days": available / daily_out if daily_out > 0 else None,
                "period_out": _clean_number(period_out),
                "raw_period_out": _clean_number(raw_period_out),
                "amiran_period_out": _clean_number(amiran_period_out),
                "exceptional_period_out": _clean_number(exceptional_period_out),
                "online_transfer_out_qty": _clean_number(
                    item.get("online_transfer_out") or 0
                ),
                "demand_anomaly_days": demand_anomaly_days,
                "demand_daily_cap": (
                    None
                    if demand_daily_cap is None
                    else _clean_number(demand_daily_cap)
                ),
                "demand_recurring_pattern": demand_recurring_pattern,
                "demand_recurring_pattern_days": demand_recurring_pattern_days,
                "gross_out": _clean_number(item.get("gross_out") or period_out),
                "period_return": _clean_number(item.get("period_return") or 0),
                "excluded_seller_qty": _clean_number(
                    item.get("excluded_seller_qty") or 0
                ),
                "sales_rate_days": sales_rate_days,
                "stockout_days": max(0, int(item.get("stockout_days") or 0)),
                "last_in_stock_date": item.get("last_in_stock_date"),
                "sales_window_start": item.get("sales_window_start"),
                "sales_window_end": item.get("sales_window_end"),
                "days_since_last_stock": item.get("days_since_last_stock"),
                "system_ordering_cycle_active": system_cycle_active,
                "order_cycle_forced_active": forced_cycle_active,
                "ordering_cycle_active": effective_cycle_active,
                "demand_basis": snapshot.get("demand_basis") or "legacy_period_out",
                "average_daily_out": _clean_number(daily_out),
                "coverage_days": None if coverage_days is None else _clean_number(coverage_days),
                "needs_reorder": needs_reorder,
                "conversion_rate": _clean_number(conversion),
                "effective_cartons": math.floor(available / conversion),
                "suggested_quantity": _clean_number(suggested),
                "suggested_cartons": cartons,
                "unadjusted_suggested_cartons": unadjusted_cartons,
                "sale_price": _clean_number(item.get("sale_price") or 0),
                "manufacturer_price": _clean_number(
                    item.get("manufacturer_price") or 0
                ),
                "consumer_price": _clean_number(
                    item.get("consumer_price") or 0
                ),
                "approximate_price": _clean_number(item["buy_price"]),
                "buy_price": _clean_number(item["buy_price"]),
                "estimated_value": _clean_number(suggested * float(item["buy_price"])),
                "calculation": {
                    "target_quantity": _clean_number(target_quantity),
                    "raw_requirement": _clean_number(raw_requirement),
                    "rounded_to_conversion_rate": _clean_number(conversion),
                },
            }
        )
    results.sort(
        key=lambda item: (
            -float(item["suggested_quantity"]),
            str(item["manufacturer"]),
            str(item["product_name"]),
        )
    )
    visible = results[:limit]
    return {
        "snapshot": snapshot,
        "warehouse": {"code": warehouse, "name": WAREHOUSES[warehouse]["name"]},
        "parameters": {
            "incoming_supply_revision": incoming_revision,
            "reorder_coverage_days": reorder_coverage_days,
            "target_days": target_days,
            "safety_days": safety_days,
            "period_days": effective_period_days,
            "only_needed": only_needed,
            "excluded_seller": (
                {
                    "dealer_id": EXCLUDED_REPLENISHMENT_DEALER_ID,
                    "name": EXCLUDED_REPLENISHMENT_DEALER_NAME,
                }
                if snapshot.get("demand_basis")
                in {"net_sales_stockout_adjusted", LAST_STOCK_DEMAND_BASIS}
                else None
            ),
            "stale_after_days": (
                ORDER_CYCLE_STALE_DAYS if uses_last_stock_window else None
            ),
            "demand_outlier_policy": (
                {
                    "method": "daily_p90_or_three_times_positive_median",
                    "protected_customer_category_id": None,
                    "protected_customer_group_id": AMIRAN_CUSTOMER_GROUP_ID,
                    "protected_customer_membership_source": "GNR.tblCust.CustGroupRef",
                    "protected_customer_group": AMIRAN_CUSTOMER_GROUP_NAME,
                    "recurring_pattern_share": DEMAND_RECURRING_PATTERN_SHARE,
                }
                if uses_last_stock_window
                else None
            ),
        },
        "summary": {
            "matched_items": len(results),
            "returned_items": len(visible),
            "excluded_stale_items": excluded_stale_items,
            "excluded_manual_items": excluded_manual_items,
            "suggested_quantity": _clean_number(
                sum(float(item["suggested_quantity"]) for item in results)
            ),
            "suggested_cartons": sum(
                int(item["suggested_cartons"]) for item in results
            ),
            "estimated_value": _clean_number(
                sum(float(item["estimated_value"]) for item in results)
            ),
            "raw_period_out": _clean_number(
                sum(float(item["raw_period_out"]) for item in results)
            ),
            "adjusted_period_out": _clean_number(
                sum(float(item["period_out"]) for item in results)
            ),
            "exceptional_period_out": _clean_number(
                sum(float(item["exceptional_period_out"]) for item in results)
            ),
            "amiran_period_out": _clean_number(
                sum(float(item["amiran_period_out"]) for item in results)
            ),
            "online_transfer_out": _clean_number(
                sum(float(item["online_transfer_out_qty"]) for item in results)
            ),
            "demand_anomaly_items": sum(
                1
                for item in results
                if float(item["exceptional_period_out"]) > 0
            ),
            "demand_recurring_pattern_items": sum(
                1 for item in results if item["demand_recurring_pattern"]
            ),
        },
        "items": visible,
        "formula_version": "warehouse-replenishment-robust-demand-v7",
        "commit_enabled": False,
    }


def _order_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    order = dict(row)
    deletion=conn.execute('SELECT deleted_by,deleted_at FROM supplier_order_deletions WHERE order_id=?',(order['id'],)).fetchone()
    order.update(deleted=order['status']=='cancelled',deletion=dict(deletion) if deletion else None)
    line_rows = conn.execute(
        """SELECT product_code, product_name, brand, conversion_rate,
                  COALESCE((SELECT i.group_level3 FROM warehouse_snapshot_items i
                   WHERE i.snapshot_id=? AND i.warehouse_code=? AND i.product_code=supplier_order_lines.product_code), '') AS group_level3,
                  (SELECT i.manufacturer_product_code FROM warehouse_snapshot_items i
                   WHERE i.snapshot_id=? AND i.warehouse_code=? AND i.product_code=supplier_order_lines.product_code) AS manufacturer_product_code,
                  (SELECT i.barcode FROM warehouse_snapshot_items i
                   WHERE i.snapshot_id=? AND i.warehouse_code=? AND i.product_code=supplier_order_lines.product_code) AS barcode,
                  requested_quantity, order_quantity, cartons,
                  manufacturer_price, consumer_price,
                  buy_price, buy_price AS approximate_price,
                  estimated_value, note
           FROM supplier_order_lines WHERE order_id=? ORDER BY id""",
        (order['snapshot_id'], order['warehouse_code'], order['snapshot_id'], order['warehouse_code'],
         order['snapshot_id'], order['warehouse_code'], order["id"]),
    ).fetchall()
    order["lines"] = [dict(line) for line in line_rows]
    contact = conn.execute(
        """SELECT contact_first_name,contact_last_name,contact_email,contact_mobile
           FROM warehouse_supplier_auto_order_settings
           WHERE warehouse_code=? AND supplier=? COLLATE NOCASE LIMIT 1""",
        (order["warehouse_code"], order["supplier"]),
    ).fetchone()
    for key in ("contact_first_name", "contact_last_name", "contact_email", "contact_mobile"):
        order[key] = str(contact[key] or "") if contact else ""
    delivery = conn.execute(
        """SELECT status,recipient,started_at,completed_at,error,
                  (SELECT COUNT(*) FROM warehouse_supplier_order_email_attempts WHERE order_id=?) AS attempts
           FROM warehouse_supplier_order_email_attempts WHERE order_id=? ORDER BY id DESC LIMIT 1""",
        (order["id"], order["id"]),
    ).fetchone()
    order["email_delivery"] = dict(delivery) if delivery else None
    order["is_approved"] = bool(order.get("approved_at"))
    order["can_approve"] = not order["deleted"] and not order["is_approved"] and not delivery
    order["can_revoke_approval"] = order["is_approved"] and not delivery
    order["can_send_email"] = order["is_approved"] and not order["deleted"] and not (
        delivery and delivery["status"] in ("sending", "sent", "unknown")
    )
    order["can_send_sms"] = order["is_approved"] and not order["deleted"]
    # Backward-compatible UI flag keeps both delivery choices visible after approval.
    # Email itself remains idempotent and returns already_sent after acceptance.
    order["can_send"] = order["can_send_sms"]
    token_payload = {
        "id": order["id"], "approved_at": order.get("approved_at"),
        "contact_email": order["contact_email"],
        "lines": [(line["product_code"], line["order_quantity"], line["cartons"]) for line in order["lines"]],
    }
    order["email_send_token"] = hashlib.sha256(
        json.dumps(token_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    # Use the same saved physical-stock coverage as the automatic preview.
    # No ERP query and no new order/in-transit quantity is counted as stock here.
    coverage_rows = conn.execute(
        """SELECT i.product_code, i.stock, i.reserved, i.open_order,
                  i.period_out, i.sales_rate_days, s.period_days, s.demand_basis
           FROM warehouse_snapshot_items i
           JOIN warehouse_snapshots s ON s.id=i.snapshot_id
           WHERE i.snapshot_id=? AND i.warehouse_code=?
             AND i.product_code IN
                 (SELECT product_code FROM supplier_order_lines WHERE order_id=?)""",
        (order['snapshot_id'], order['warehouse_code'], order['id']),
    ).fetchall()
    coverage_by_code = {}
    for item in coverage_rows:
        adjusted = item['demand_basis'] in {
            'net_sales_stockout_adjusted', LAST_STOCK_DEMAND_BASIS,
        }
        days = (max(0, int(item['sales_rate_days'] or 0)) if adjusted
                else max(0, int(item['period_days'] or 60)))
        daily = max(0.0, float(item['period_out'] or 0)) / days if days else 0
        available = (float(item['stock']) + max(0.0, float(item['reserved'] or 0))
                     - max(0.0, float(item['open_order'] or 0)))
        coverage_by_code[item['product_code']] = available / daily if daily > 0 else None
    for line in order['lines']:
        line['coverage_days'] = coverage_by_code.get(line['product_code'])
    order["supplier_portal"] = _supplier_portal_order_status(
        conn, "supplier_order", int(order["id"])
    )
    if order["supplier_portal"] is None and order.get("approved_at"):
        order["supplier_portal"] = {
            "status": "awaiting_link", "workflow_status": "awaiting_link",
            "dispatch_sent": False,
        }
    _apply_order_workflow(conn, order, "supplier_order", int(order["id"]))
    return order


def _sync_manual_order_fulfillment_projection(
    conn: sqlite3.Connection,
    order: dict[str, Any],
    username: str,
    *,
    active: bool,
) -> None:
    """Mirror an approved manual order into the existing fulfillment ledger."""
    existing = conn.execute(
        "SELECT * FROM warehouse_automatic_preorders WHERE source_supplier_order_id=?",
        (order["id"],),
    ).fetchone()
    now = _now()
    if not active:
        if existing is None:
            return
        has_receipt_activity = conn.execute(
            """SELECT 1
               FROM warehouse_fulfillment_receipts WHERE preorder_id=?
               UNION ALL SELECT 1
               FROM warehouse_receipt_allocations WHERE preorder_id=?
               UNION ALL SELECT 1
               FROM warehouse_fulfillment_adjustments WHERE preorder_id=?
               LIMIT 1""",
            (existing["id"], existing["id"], existing["id"]),
        ).fetchone()
        if has_receipt_activity:
            raise WarehouseAssistantError(
                "سفارش دستی وارد فرایند دریافت شده و تأیید آن دیگر قابل لغو نیست."
            )
        conn.execute(
            """UPDATE warehouse_automatic_preorders
               SET status='cancelled', edited_by=?, edited_at=? WHERE id=?""",
            (username[:100], now, existing["id"]),
        )
        return

    setting = conn.execute(
        """SELECT * FROM warehouse_supplier_auto_order_settings
           WHERE warehouse_code=? AND supplier=? COLLATE NOCASE LIMIT 1""",
        (order["warehouse_code"], order["supplier"]),
    ).fetchone()
    if setting is None:
        cursor = conn.execute(
            """INSERT INTO warehouse_supplier_auto_order_settings
               (warehouse_code,warehouse_name,supplier,enabled,
                reorder_coverage_days,target_days,minimum_cartons,
                contact_first_name,contact_last_name,contact_email,contact_mobile,
                created_at,updated_at,updated_by)
               VALUES(?,?,?,0,10,20,0,?,?,?,?,?,?,?)""",
            (
                order["warehouse_code"], order["warehouse_name"], order["supplier"],
                str(order.get("contact_first_name") or ""),
                str(order.get("contact_last_name") or ""),
                str(order.get("contact_email") or ""),
                str(order.get("contact_mobile") or ""),
                now, now, username[:100],
            ),
        )
        setting_id = int(cursor.lastrowid)
    else:
        setting_id = int(setting["id"])

    total_cartons = sum(max(0, int(line["cartons"] or 0)) for line in order["lines"])
    approved_at = str(order.get("approved_at") or now)
    values = (
        order["order_number"], f"manual-supplier-order:{order['id']}",
        order["snapshot_id"], setting_id, order["warehouse_code"],
        order["warehouse_name"], order["supplier"], len(order["lines"]),
        order["total_quantity"], total_cartons, order["estimated_value"],
        str(order.get("contact_first_name") or ""),
        str(order.get("contact_last_name") or ""),
        str(order.get("contact_email") or ""),
        str(order.get("contact_mobile") or ""),
        str(order.get("created_by") or username)[:100],
        str(order.get("created_at") or now), jalali_business_date(tehran_now()),
        now, str(order.get("approved_by") or username)[:100], approved_at,
        username[:100], now, order["id"],
    )
    if existing is None:
        cursor = conn.execute(
            """INSERT INTO warehouse_automatic_preorders
               (preorder_number,generation_key,snapshot_id,supplier_setting_id,
                warehouse_code,warehouse_name,supplier,status,
                reorder_coverage_days,target_days,minimum_cartons,
                item_count,total_quantity,total_cartons,estimated_value,
                contact_first_name,contact_last_name,contact_email,contact_mobile,
                created_by,created_at,business_date,last_refreshed_at,refresh_trigger,
                approved_by,approved_at,edited_by,edited_at,source_supplier_order_id)
               VALUES(?,?,?,?,?,?,?,'approved',10,20,0,?,?,?,?,?,?,?,?,?,?,?,?,
                      'manual_order',?,?,?,?,?)""",
            values,
        )
        preorder_id = int(cursor.lastrowid)
    else:
        preorder_id = int(existing["id"])
        conn.execute(
            """UPDATE warehouse_automatic_preorders
               SET preorder_number=?,generation_key=?,snapshot_id=?,supplier_setting_id=?,
                   warehouse_code=?,warehouse_name=?,supplier=?,status='approved',
                   reorder_coverage_days=10,target_days=20,minimum_cartons=0,
                   item_count=?,total_quantity=?,total_cartons=?,estimated_value=?,
                   contact_first_name=?,contact_last_name=?,contact_email=?,contact_mobile=?,
                   created_by=?,created_at=?,business_date=?,last_refreshed_at=?,
                   refresh_trigger='manual_order',approved_by=?,approved_at=?,
                   edited_by=?,edited_at=?,source_supplier_order_id=?
               WHERE id=?""",
            (*values, preorder_id),
        )
    conn.execute(
        "DELETE FROM warehouse_automatic_preorder_lines WHERE preorder_id=?", (preorder_id,)
    )
    conn.executemany(
        """INSERT INTO warehouse_automatic_preorder_lines
           (preorder_id,warehouse_code,warehouse_name,product_code,product_name,brand,
            conversion_rate,system_suggested_cartons,unadjusted_suggested_cartons,
            order_quantity,cartons,manufacturer_price,consumer_price,buy_price,estimated_value)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(
            preorder_id, order["warehouse_code"], order["warehouse_name"],
            line["product_code"], line["product_name"], line["brand"],
            line["conversion_rate"], line["cartons"], line["cartons"],
            line["order_quantity"], line["cartons"], line["manufacturer_price"],
            line["consumer_price"], line["buy_price"], line["estimated_value"],
        ) for line in order["lines"]],
    )


def transition_supplier_order(settings: Any, username: str, order_id: int, action: str,
                              *, include_all: bool = False) -> dict[str, Any]:
    if action not in {"approve", "revoke_approval"}:
        raise WarehouseAssistantError("عملیات سفارش دستی معتبر نیست.")
    init_warehouse_store(settings)
    now = datetime.now(timezone.utc).isoformat()
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM supplier_orders WHERE id=?", (order_id,)).fetchone()
        if row is None or (not include_all and row["created_by"] != username):
            raise WarehouseAssistantError("سفارش تأمین‌کننده پیدا نشد.")
        order = _order_from_row(conn, row)
        if order["deleted"]:
            raise WarehouseAssistantError("سفارش حذف‌شده قابل تأیید نیست.")
        if order['dispatch_locked'] and (action == 'revoke_approval' or not order['is_approved']):
            raise WarehouseAssistantError("پس از شروع ارسال لینک، تغییر یا لغو تأیید ممکن نیست.")
        if action == "approve":
            ensure_cycle_allowed(conn, order["warehouse_code"], [line["product_code"] for line in order["lines"]])
            if order["is_approved"]:
                _sync_manual_order_fulfillment_projection(conn, order, username, active=True)
                return order
            if order["dispatch_locked"]:
                raise WarehouseAssistantError("سفارش دارای سابقه ارسال است و قابل تأیید مجدد نیست.")
            conn.execute("UPDATE supplier_orders SET approved_by=?,approved_at=? WHERE id=?",
                         (username[:100], now, order_id))
            approved_row = conn.execute("SELECT * FROM supplier_orders WHERE id=?", (order_id,)).fetchone()
            _sync_manual_order_fulfillment_projection(
                conn, _order_from_row(conn, approved_row), username, active=True)
        else:
            if not order["is_approved"]:
                return order
            if order["dispatch_locked"]:
                raise WarehouseAssistantError("پس از شروع ارسال، لغو تأیید ممکن نیست.")
            conn.execute("""UPDATE supplier_orders SET approved_by=NULL,approved_at=NULL,
                         edited_by=?,edited_at=? WHERE id=?""", (username[:100], now, order_id))
            _sync_manual_order_fulfillment_projection(conn, order, username, active=False)
        updated = conn.execute("SELECT * FROM supplier_orders WHERE id=?", (order_id,)).fetchone()
        return _order_from_row(conn, updated)


def add_supplier_order_lines(settings: Any, username: str, order_id: int, lines: list[dict[str, Any]],
                             *, receipt_review_confirmed: bool = False,
                             reason: str = "", include_all: bool = False) -> dict[str, Any]:
    """Append new lines to an unsent manual order; receipt-review bypass is explicit and audited."""
    if not lines:
        raise WarehouseAssistantError("حداقل یک قلم برای افزودن لازم است.")
    requested: dict[str, tuple[float, str]] = {}
    for line in lines:
        code = _product_code(line.get("product_code"))
        amount = _number(line.get("quantity"))
        if not code or code in requested or amount <= 0 or amount > 1_000_000_000:
            raise WarehouseAssistantError("کد یا تعداد قلم افزوده‌شده معتبر نیست.")
        requested[code] = (amount, _normalize_text(line.get("note"))[:500])
    init_warehouse_store(settings)
    now = datetime.now(timezone.utc).isoformat()
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM supplier_orders WHERE id=?", (order_id,)).fetchone()
        if row is None or (not include_all and row["created_by"] != username):
            raise WarehouseAssistantError("سفارش تأمین‌کننده پیدا نشد.")
        order = _order_from_row(conn, row)
        if order["deleted"] or order["is_approved"] or order["dispatch_locked"]:
            raise WarehouseAssistantError("فقط سفارش دستیِ تأییدنشده و ارسال‌نشده قابل ویرایش است.")
        ensure_cycle_allowed(conn, order["warehouse_code"], requested)
        blocked = pending_stock(conn, order["warehouse_code"])[1].intersection(requested)
        if blocked and not receipt_review_confirmed:
            raise WarehouseAssistantError(
                "رسید این کالاها نیازمند پیگیری است؛ برای افزودن، عبور از هشدار را صریحاً تأیید کنید: "
                + "، ".join(sorted(blocked))
            )
        if blocked and not reason.strip():
            raise WarehouseAssistantError("علت عبور از هشدار رسید در انتظار بررسی الزامی است.")
        existing = {line["product_code"] for line in order["lines"]}
        duplicate = existing.intersection(requested)
        if duplicate:
            raise WarehouseAssistantError("این کالا قبلاً در سفارش وجود دارد: " + "، ".join(sorted(duplicate)))
        marks = ",".join("?" for _ in requested)
        sources = conn.execute(
            f"""SELECT * FROM warehouse_snapshot_items WHERE snapshot_id=? AND warehouse_code=?
                 AND product_code IN ({marks})""",
            (order["snapshot_id"], order["warehouse_code"], *requested),
        ).fetchall()
        by_code = {str(source["product_code"]): source for source in sources}
        missing = set(requested).difference(by_code)
        if missing:
            raise WarehouseAssistantError("کالا در Snapshot سفارش پیدا نشد: " + "، ".join(sorted(missing)))
        if any(_normalize_text(source["manufacturer"]).casefold() != order["supplier"].casefold()
               for source in sources):
            raise WarehouseAssistantError("همه اقلام افزوده‌شده باید متعلق به تأمین‌کننده همین سفارش باشند.")
        inserts = []
        for code, (amount, note) in requested.items():
            source = by_code[code]
            conversion = max(1.0, _number(source["conversion_rate"]))
            cartons = math.ceil(amount / conversion)
            quantity = cartons * conversion
            buy_price = max(0.0, _number(source["buy_price"]))
            inserts.append((order_id, code, _normalize_text(source["product_name"]),
                _normalize_text(source["brand"]), conversion, amount, quantity, cartons,
                max(0.0, _number(source["manufacturer_price"])),
                max(0.0, _number(source["consumer_price"])), buy_price,
                quantity * buy_price, note))
        conn.executemany("""INSERT INTO supplier_order_lines
            (order_id,product_code,product_name,brand,conversion_rate,requested_quantity,
             order_quantity,cartons,manufacturer_price,consumer_price,buy_price,estimated_value,note)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", inserts)
        conn.execute("""UPDATE supplier_orders SET
            total_quantity=(SELECT SUM(order_quantity) FROM supplier_order_lines WHERE order_id=?),
            estimated_value=(SELECT SUM(estimated_value) FROM supplier_order_lines WHERE order_id=?),
            approved_by=NULL,approved_at=NULL,edited_by=?,edited_at=?,
            receipt_review_override_by=?,receipt_review_override_at=?,receipt_review_override_reason=?
            WHERE id=?""", (order_id, order_id, username[:100], now,
            username[:100] if blocked else row["receipt_review_override_by"],
            now if blocked else row["receipt_review_override_at"],
            reason.strip()[:500] if blocked else row["receipt_review_override_reason"], order_id))
        updated = conn.execute("SELECT * FROM supplier_orders WHERE id=?", (order_id,)).fetchone()
        return _order_from_row(conn, updated)


def create_supplier_orders(
    settings: Any,
    username: str,
    *,
    snapshot_id: int,
    warehouse: str,
    lines: list[dict[str, Any]],
    note: str = "",
    delivery_date: str = "",
) -> list[dict[str, Any]]:
    """Create one local prepared document per supplier; never writes to the ERP."""
    from app.warehouse_order_delivery import clean_delivery_date, write_date
    delivery_date = clean_delivery_date(delivery_date, optional=True)
    if warehouse not in WAREHOUSES:
        raise WarehouseAssistantError("انبار انتخاب‌شده معتبر نیست.")
    if not lines:
        raise WarehouseAssistantError("حداقل یک قلم برای سفارش انتخاب کنید.")
    if len(lines) > 500:
        raise WarehouseAssistantError("هر درخواست حداکثر می‌تواند ۵۰۰ قلم داشته باشد.")

    requested: dict[str, dict[str, Any]] = {}
    for line in lines:
        code = _product_code(line.get("product_code"))
        if not code:
            raise WarehouseAssistantError("کد کالا برای همه اقلام الزامی است.")
        if code in requested:
            raise WarehouseAssistantError(f"کالای {code} بیش از یک بار انتخاب شده است.")
        quantity = _number(line.get("quantity"))
        if quantity <= 0 or quantity > 1_000_000_000:
            raise WarehouseAssistantError(f"تعداد سفارش کالای {code} معتبر نیست.")
        requested[code] = {
            "quantity": quantity,
            "note": _normalize_text(line.get("note"))[:500],
        }

    init_warehouse_store(settings)
    placeholders = ",".join("?" for _ in requested)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        ensure_orderable(conn, warehouse, requested)
        snapshot = conn.execute(
            "SELECT id, demand_basis FROM warehouse_snapshots WHERE id=?",
            (snapshot_id,),
        ).fetchone()
        if snapshot is None:
            raise WarehouseAssistantError("Snapshot انتخاب‌شده پیدا نشد.")
        rows = conn.execute(
            f"""SELECT product_code, product_name, brand, manufacturer,
                       conversion_rate, manufacturer_price, consumer_price,
                       buy_price, ordering_cycle_active,
                       CASE WHEN {ORDER_CYCLE_FORCED_SQL} THEN 1 ELSE 0 END
                         AS order_cycle_forced_active
                FROM warehouse_snapshot_items
                WHERE snapshot_id=? AND warehouse_code=?
                  AND product_code IN ({placeholders})""",
            [snapshot_id, warehouse, *requested.keys()],
        ).fetchall()
        found = {str(row["product_code"]): row for row in rows}
        missing = [code for code in requested if code not in found]
        if missing:
            raise WarehouseAssistantError(
                "کالای انتخاب‌شده در Snapshot این انبار پیدا نشد: " + "، ".join(missing[:10])
            )
        if snapshot["demand_basis"] == LAST_STOCK_DEMAND_BASIS:
            stale = [
                code
                for code, row in found.items()
                if not (
                    bool(row["ordering_cycle_active"])
                    or bool(row["order_cycle_forced_active"])
                )
            ]
            if stale:
                raise WarehouseAssistantError(
                    "کالاهای زیر بیش از ۹۰ روز موجود نبوده‌اند و خارج از چرخه سفارش هستند: "
                    + "، ".join(stale[:10])
                )
        _ensure_supply_scope(conn, snapshot_id)
        if _supply_scope_is_strict(conn):
            inactive = []
            for code, source in found.items():
                allowed = conn.execute(
                    """SELECT 1 FROM warehouse_supply_scope
                       WHERE warehouse_code=?
                         AND supplier=? COLLATE NOCASE
                         AND brand=? COLLATE NOCASE
                         AND enabled=1 LIMIT 1""",
                    (warehouse, source["manufacturer"], source["brand"]),
                ).fetchone()
                if allowed is None:
                    inactive.append(code)
            if inactive:
                raise WarehouseAssistantError(
                    "تأمین‌کننده یا برند این کالاها برای انبار فعال نیست: "
                    + "، ".join(inactive[:10])
                )

        grouped: dict[str, list[dict[str, Any]]] = {}
        for code, request_line in requested.items():
            source = found[code]
            supplier = _normalize_text(source["manufacturer"])
            if not supplier:
                raise WarehouseAssistantError(
                    f"تأمین‌کننده کالای {code} در Snapshot مشخص نشده است."
                )
            conversion = max(1.0, _number(source["conversion_rate"]))
            cartons = math.ceil(request_line["quantity"] / conversion)
            order_quantity = cartons * conversion
            buy_price = max(0.0, _number(source["buy_price"]))
            grouped.setdefault(supplier, []).append(
                {
                    "product_code": code,
                    "product_name": _normalize_text(source["product_name"]),
                    "brand": _normalize_text(source["brand"]),
                    "conversion_rate": conversion,
                    "requested_quantity": request_line["quantity"],
                    "order_quantity": order_quantity,
                    "cartons": cartons,
                    "manufacturer_price": max(
                        0.0, _number(source["manufacturer_price"])
                    ),
                    "consumer_price": max(
                        0.0, _number(source["consumer_price"])
                    ),
                    "buy_price": buy_price,
                    "approximate_price": buy_price,
                    "estimated_value": order_quantity * buy_price,
                    "note": request_line["note"],
                }
            )

        created: list[dict[str, Any]] = []
        created_at = _now()
        for supplier, supplier_lines in sorted(grouped.items()):
            total_quantity = sum(line["order_quantity"] for line in supplier_lines)
            estimated_value = sum(line["estimated_value"] for line in supplier_lines)
            cursor = conn.execute(
                """INSERT INTO supplier_orders
                   (snapshot_id, warehouse_code, warehouse_name, supplier, note,
                    total_quantity, estimated_value, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snapshot_id,
                    warehouse,
                    WAREHOUSES[warehouse]["name"],
                    supplier,
                    _normalize_text(note)[:1000],
                    total_quantity,
                    estimated_value,
                    username[:100],
                    created_at,
                ),
            )
            order_id = int(cursor.lastrowid)
            if delivery_date:
                write_date(conn, 'supplier_order', order_id, delivery_date, username, created_at)
            order_number = f"SUP-{created_at[:10].replace('-', '')}-{order_id:06d}"
            conn.execute(
                "UPDATE supplier_orders SET order_number=? WHERE id=?",
                (order_number, order_id),
            )
            conn.executemany(
                """INSERT INTO supplier_order_lines
                   (order_id, product_code, product_name, brand, conversion_rate,
                    requested_quantity, order_quantity, cartons,
                    manufacturer_price, consumer_price, buy_price,
                    estimated_value, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        order_id,
                        line["product_code"],
                        line["product_name"],
                        line["brand"],
                        line["conversion_rate"],
                        line["requested_quantity"],
                        line["order_quantity"],
                        line["cartons"],
                        line["manufacturer_price"],
                        line["consumer_price"],
                        line["buy_price"],
                        line["estimated_value"],
                        line["note"],
                    )
                    for line in supplier_lines
                ],
            )
            order_row = conn.execute(
                "SELECT * FROM supplier_orders WHERE id=?", (order_id,)
            ).fetchone()
            created.append(_order_from_row(conn, order_row))
    return created


def get_supplier_order(
    settings: Any, order_id: int, username: str, *, include_all: bool = False
) -> dict[str, Any]:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        if include_all:
            row = conn.execute(
                "SELECT * FROM supplier_orders WHERE id=?", (order_id,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM supplier_orders WHERE id=? AND created_by=?",
                (order_id, username),
            ).fetchone()
        if row is None:
            raise WarehouseAssistantError("سفارش تأمین‌کننده پیدا نشد.")
        return _order_from_row(conn, row)


def list_supplier_orders(
    settings: Any, username: str, *, include_all: bool = False, limit: int = 50, include_deleted: bool = False, stage: str = ''
) -> list[dict[str, Any]]:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        if include_all:
            rows = conn.execute(
                "SELECT * FROM supplier_orders WHERE ? OR status<>'cancelled' ORDER BY id DESC LIMIT ?", (include_deleted, -1 if stage else limit)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM supplier_orders WHERE created_by=? AND (? OR status<>'cancelled')
                   ORDER BY id DESC LIMIT ?""",
                (username, include_deleted, -1 if stage else limit),
            ).fetchall()
        orders = []
        for row in rows:
            portal_status = _supplier_portal_order_status(conn, 'supplier_order', row['id']) or {}
            if stage == 'draft' and portal_status.get('dispatch_sent'):
                continue
            order = _order_from_row(conn, row)
            if not stage or order['order_stage'] == stage:
                orders.append(order)
                if len(orders) >= limit:
                    break
        return orders


def delete_supplier_order(settings, username, order_id, *, include_all=False):
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM supplier_orders WHERE id=?',(order_id,)).fetchone()
        if row is None or (not include_all and row['created_by']!=username):
            raise WarehouseAssistantError('سفارش تأمین‌کننده پیدا نشد.')
        if row['status'] not in ('prepared','cancelled'):
            raise WarehouseAssistantError('این سفارش قابل حذف نیست.')
        order = _order_from_row(conn, row)
        if order['dispatch_locked']:
            raise WarehouseAssistantError('سفارش ارسال‌شده یا با نتیجه ارسال نامشخص قابل حذف نیست.')
        if order.get('is_approved'):
            _sync_manual_order_fulfillment_projection(
                conn, order, username, active=False
            )
        conn.execute('INSERT OR IGNORE INTO supplier_order_deletions(order_id,deleted_by,deleted_at) VALUES(?,?,?)',(order_id,username,_now()))
        conn.execute("UPDATE supplier_orders SET status='cancelled' WHERE id=?",(order_id,))
        return dict(id=order_id,deleted=True)


def supplier_order_text(order: dict[str, Any]) -> str:
    lines = [
        "سفارش خرید نگین پخش",
        f"شماره سفارش: {order['order_number']}",
        f"تأمین‌کننده: {order['supplier']}",
        f"انبار مقصد: {order['warehouse_name']}",
        f"تاریخ آماده‌سازی: {order['created_at']}",
        "",
        "ردیف | کد کالا | نام کالا | برند | تعداد | کارتن | قیمت تولیدکننده | قیمت مصرف‌کننده | قیمت حدودی | ارزش تخمینی",
    ]
    for index, item in enumerate(order["lines"], start=1):
        lines.append(
            f"{index} | {item['product_code']} | {item['product_name']} | "
            f"{item['brand'] or '-'} | {_clean_number(item['order_quantity'])} | "
            f"{item['cartons']} | {_clean_number(item['manufacturer_price'])} | "
            f"{_clean_number(item['consumer_price'])} | "
            f"{_clean_number(item['approximate_price'])} | "
            f"{_clean_number(item['estimated_value'])}"
        )
    lines.extend(
        [
            "",
            f"جمع تعداد: {_clean_number(order['total_quantity'])}",
            f"ارزش تخمینی: {_clean_number(order['estimated_value'])}",
        ]
    )
    if order.get("note"):
        lines.append(f"توضیحات: {order['note']}")
    return "\n".join(lines)
