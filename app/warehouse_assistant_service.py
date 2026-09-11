"""Isolated inventory snapshot and replenishment suggestion service.

This module deliberately does not import the assistant, previsit, or Varanegar
order bridge.  It stores pilot data in a separate SQLite database and never
writes to the ERP.
"""

from __future__ import annotations

import hashlib
import math
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator
from zipfile import BadZipFile, ZipFile, is_zipfile

from openpyxl import load_workbook

from app.business_time import jalali_business_date, tehran_now
from app.database import sql_connection
from app.sql_guard import validate_read_only_sql


SOURCE_SHEET = "فایل انبار"
MAX_PRODUCT_ROWS = 50_000
MAX_ARCHIVE_ENTRIES = 2_048
MAX_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_ENTRY_BYTES = 32 * 1024 * 1024
MAX_COMPRESSION_RATIO = 100
MAX_SHEET_COLUMNS = 128
MAX_CELL_TEXT_CHARS = 10_000
MAX_IMPORT_ITEMS = 150_000

WAREHOUSES: dict[str, dict[str, Any]] = {
    "karaj": {
        "name": "انبار مرکزی کرج",
        "stock_dc_ref": 1,
        "stock_dc_code": "26",
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
              period_days INTEGER
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
              stock REAL NOT NULL DEFAULT 0,
              reserved REAL NOT NULL DEFAULT 0,
              period_out REAL NOT NULL DEFAULT 0,
              gross_out REAL NOT NULL DEFAULT 0,
              period_return REAL NOT NULL DEFAULT 0,
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
              buy_price REAL NOT NULL DEFAULT 0,
              estimated_value REAL NOT NULL DEFAULT 0,
              note TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(order_id) REFERENCES supplier_orders(id) ON DELETE CASCADE,
              UNIQUE(order_id, product_code)
            );
            CREATE INDEX IF NOT EXISTS idx_supplier_orders_recent
              ON supplier_orders(created_at DESC, id DESC);
            """
        )
        snapshot_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(warehouse_snapshots)")
        }
        snapshot_migrations = {
            "source_kind": "source_kind TEXT NOT NULL DEFAULT 'excel'",
            "period_start": "period_start TEXT",
            "period_end": "period_end TEXT",
            "period_days": "period_days INTEGER",
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
        }
        for column_name, definition in item_migrations.items():
            if column_name not in item_columns:
                conn.execute(
                    f"ALTER TABLE warehouse_snapshot_items ADD COLUMN {definition}"
                )


def _normalize_text(value: Any) -> str:
    if isinstance(value, str) and len(value) > MAX_CELL_TEXT_CHARS:
        raise WarehouseAssistantError("متن یکی از سلول‌های Excel بیش از حد مجاز است.")
    text = str(value or "").strip().replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"\s+", " ", text)


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
                if entry.flag_bits & 0x1:
                    raise WarehouseAssistantError("فایل Excel رمزگذاری‌شده قابل پردازش نیست.")
                if entry.file_size > MAX_ARCHIVE_ENTRY_BYTES:
                    raise WarehouseAssistantError("یک بخش از فایل Excel بیش از حد مجاز باز می‌شود.")
                if entry.file_size and (
                    entry.compress_size <= 0
                    or entry.file_size / entry.compress_size > MAX_COMPRESSION_RATIO
                ):
                    raise WarehouseAssistantError("نسبت فشرده‌سازی فایل Excel ناامن است.")
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
        if sheet.max_row > MAX_PRODUCT_ROWS + 1 or sheet.max_column > MAX_SHEET_COLUMNS:
            raise WarehouseAssistantError("ابعاد شیت Excel بیش از حد مجاز است.")
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
                        values["period_out"],
                        values["thirty_day_stock"],
                        values["sale_price"],
                        values["manufacturer_price"],
                        values["consumer_price"],
                        values["buy_price"],
                    )
                )
                if len(items) > MAX_IMPORT_ITEMS:
                    raise WarehouseAssistantError("تعداد اقلام قابل استخراج از Excel بیش از حد مجاز است.")
    finally:
        workbook.close()

    if not products:
        raise WarehouseAssistantError("هیچ کالای معتبری در شیت فایل انبار پیدا نشد.")

    imported_at = _now()
    with warehouse_connection(settings) as conn:
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
                stock, reserved, period_out, thirty_day_stock, sale_price,
                manufacturer_price, consumer_price, buy_price)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
    current = tehran_now()
    period_end = jalali_business_date(current)
    period_start = jalali_business_date(current - timedelta(days=period_days - 1))
    inventory_sql = f"""
WITH ranked_stock AS (
  SELECT stock.GoodsRef, stock.StockDCRef, stock.OnHandQty, stock.ReservedQty,
         ROW_NUMBER() OVER (
           PARTITION BY stock.GoodsRef, stock.StockDCRef
           ORDER BY stock.AccYear DESC, stock.ID DESC
         ) AS StockRank
  FROM GNR.tblStockGoods AS stock
  WHERE stock.StockDCRef IN ({stock_refs})
)
SELECT ranked.GoodsRef, goods.GoodsCode, goods.GoodsName,
       CASE WHEN ISNULL(goods.CartonType, 0) > 0 THEN goods.CartonType ELSE 1 END AS ConversionRate,
       ISNULL(manufacturer.ManufacturerName, '') AS ManufacturerName,
       ISNULL(brand.BrandName, '') AS BrandName,
       ranked.StockDCRef, stock_dc.StockDCName,
       ISNULL(ranked.OnHandQty, 0) AS OnHandQty,
       ISNULL(ranked.ReservedQty, 0) AS ReservedQty
FROM ranked_stock AS ranked
INNER JOIN GNR.tblGoods AS goods ON goods.ID = ranked.GoodsRef
INNER JOIN GNR.tblStockDC AS stock_dc ON stock_dc.ID = ranked.StockDCRef
LEFT JOIN GNR.tblManufacturer AS manufacturer ON manufacturer.ID = goods.ManufacturerRef
LEFT JOIN GNR.tblBrand AS brand ON brand.ID = goods.BrandRef
WHERE ranked.StockRank = 1
ORDER BY ranked.StockDCRef, goods.GoodsCode
""".strip()
    outflow_sql = f"""
SELECT sale.GoodsId AS GoodsRef, sale.StockDcID AS StockDCRef,
       SUM(ISNULL(sale.SellQty, 0)) AS GrossOutQty,
       SUM(ISNULL(sale.SellReturnQty, 0)) AS ReturnQty,
       SUM(ISNULL(sale.SellQty, 0) - ISNULL(sale.SellReturnQty, 0)) AS NetOutQty
FROM dbo.SalesReviewFast AS sale
WHERE sale.ReportDate BETWEEN N'{period_start}' AND N'{period_end}'
  AND sale.StockDcID IN ({stock_refs})
GROUP BY sale.GoodsId, sale.StockDcID
""".strip()
    inventory_sql = validate_read_only_sql(inventory_sql).sql
    outflow_sql = validate_read_only_sql(outflow_sql).sql

    try:
        with sql_connection(settings) as source:
            cursor = source.cursor()
            inventory_rows = _query_rows(cursor, inventory_sql)
            outflow_rows = _query_rows(cursor, outflow_sql)
    except Exception as exc:
        raise WarehouseAssistantError(
            "خواندن موجودی و روند خروج از ورانگر انجام نشد."
        ) from exc

    if not inventory_rows:
        raise WarehouseAssistantError("ورانگر هیچ ردیف موجودی معتبری برنگرداند.")

    warehouse_by_ref = {
        int(config["stock_dc_ref"]): (code, config)
        for code, config in WAREHOUSES.items()
    }
    outflow_by_key = {
        (int(row["GoodsRef"]), int(row["StockDCRef"])): row
        for row in outflow_rows
        if row.get("GoodsRef") is not None and row.get("StockDCRef") is not None
    }
    items: list[tuple[Any, ...]] = []
    products: set[str] = set()
    digest = hashlib.sha256(
        f"varanegar|{period_start}|{period_end}|{period_days}|".encode("utf-8")
    )
    for source_row, row in enumerate(inventory_rows, start=1):
        stock_ref = int(row.get("StockDCRef") or 0)
        warehouse_match = warehouse_by_ref.get(stock_ref)
        code = _product_code(row.get("GoodsCode"))
        if warehouse_match is None or not code:
            continue
        warehouse_code, config = warehouse_match
        goods_ref = int(row.get("GoodsRef") or 0)
        trend = outflow_by_key.get((goods_ref, stock_ref), {})
        conversion = max(1.0, _number(row.get("ConversionRate")))
        on_hand = _number(row.get("OnHandQty"))
        reserved = max(0.0, _number(row.get("ReservedQty")))
        gross_out = max(0.0, _number(trend.get("GrossOutQty")))
        period_return = max(0.0, _number(trend.get("ReturnQty")))
        net_out = _number(trend.get("NetOutQty"))
        item = (
            source_row,
            warehouse_code,
            config["name"],
            code,
            _normalize_text(row.get("GoodsName")),
            conversion,
            _normalize_text(row.get("ManufacturerName")),
            _normalize_text(row.get("BrandName")),
            on_hand,
            reserved,
            net_out,
            gross_out,
            period_return,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )
        items.append(item)
        products.add(code)
        digest.update(repr(item).encode("utf-8"))

    if not items:
        raise WarehouseAssistantError("ردیف‌های موجودی ورانگر قابل نگاشت به انبارها نبودند.")

    init_warehouse_store(settings)
    content_sha256 = digest.hexdigest()
    with warehouse_connection(settings) as conn:
        existing = conn.execute(
            "SELECT * FROM warehouse_snapshots WHERE content_sha256=?",
            (content_sha256,),
        ).fetchone()
        if existing:
            return _snapshot_from_row(existing, duplicate=True)

        imported_at = _now()
        cursor = conn.execute(
            """INSERT INTO warehouse_snapshots
               (source_filename, source_sheet, content_sha256, product_count,
                item_count, imported_by, imported_at, source_kind,
                period_start, period_end, period_days)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'varanegar', ?, ?, ?)""",
            (
                "ورانگر زنده (فقط‌خواندنی)",
                "GNR.tblStockGoods + dbo.SalesReviewFast",
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
                stock, reserved, period_out, gross_out, period_return,
                thirty_day_stock, sale_price, manufacturer_price,
                consumer_price, buy_price)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(snapshot_id, *item) for item in items],
        )
        snapshot = conn.execute(
            "SELECT * FROM warehouse_snapshots WHERE id=?", (snapshot_id,)
        ).fetchone()
    result = _snapshot_from_row(snapshot, duplicate=False)
    result["varanegar_write"] = False
    result["sources"] = ["GNR.tblStockGoods", "dbo.SalesReviewFast"]
    return result


def _clean_number(value: float) -> int | float:
    rounded = round(float(value), 4)
    return int(rounded) if rounded.is_integer() else rounded


def build_suggestions(
    settings: Any,
    *,
    warehouse: str,
    manufacturer: str = "",
    brand: str = "",
    search: str = "",
    target_days: int = 30,
    safety_days: int = 7,
    period_days: int = 60,
    only_needed: bool = True,
    limit: int = 200,
) -> dict[str, Any]:
    if warehouse not in WAREHOUSES:
        raise WarehouseAssistantError("انبار انتخاب‌شده معتبر نیست.")
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
        clauses.append("(product_code LIKE ? OR product_name LIKE ?)")
        needle = f"%{search.strip()}%"
        params.extend([needle, needle])
    with warehouse_connection(settings) as conn:
        rows = conn.execute(
            "SELECT * FROM warehouse_snapshot_items WHERE "
            + " AND ".join(clauses)
            + " ORDER BY manufacturer, brand, product_name LIMIT 5000",
            params,
        ).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        stock = float(item["stock"])
        reserved = max(0.0, float(item["reserved"]))
        period_out = max(0.0, float(item["period_out"]))
        conversion = max(1.0, float(item["conversion_rate"]))
        available = stock - reserved
        daily_out = period_out / effective_period_days
        target_quantity = daily_out * (target_days + safety_days)
        raw_requirement = max(0.0, target_quantity - available)
        cartons = math.ceil(raw_requirement / conversion) if raw_requirement > 0 else 0
        suggested = cartons * conversion
        coverage_days = available / daily_out if daily_out > 0 else None
        if only_needed and suggested <= 0:
            continue
        results.append(
            {
                "product_code": item["product_code"],
                "product_name": item["product_name"],
                "manufacturer": item["manufacturer"],
                "brand": item["brand"],
                "warehouse": item["warehouse_code"],
                "warehouse_name": item["warehouse_name"],
                "stock": _clean_number(stock),
                "reserved": _clean_number(reserved),
                "available_quantity": _clean_number(available),
                "period_out": _clean_number(period_out),
                "gross_out": _clean_number(item.get("gross_out") or period_out),
                "period_return": _clean_number(item.get("period_return") or 0),
                "average_daily_out": _clean_number(daily_out),
                "coverage_days": None if coverage_days is None else _clean_number(coverage_days),
                "conversion_rate": _clean_number(conversion),
                "suggested_quantity": _clean_number(suggested),
                "suggested_cartons": cartons,
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
            "target_days": target_days,
            "safety_days": safety_days,
            "period_days": effective_period_days,
            "only_needed": only_needed,
        },
        "summary": {
            "matched_items": len(results),
            "returned_items": len(visible),
            "suggested_quantity": _clean_number(
                sum(float(item["suggested_quantity"]) for item in results)
            ),
            "estimated_value": _clean_number(
                sum(float(item["estimated_value"]) for item in results)
            ),
        },
        "items": visible,
        "formula_version": "warehouse-replenishment-pilot-v1",
        "commit_enabled": False,
    }


def _order_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    order = dict(row)
    line_rows = conn.execute(
        """SELECT product_code, product_name, brand, conversion_rate,
                  requested_quantity, order_quantity, cartons, buy_price,
                  estimated_value, note
           FROM supplier_order_lines WHERE order_id=? ORDER BY id""",
        (order["id"],),
    ).fetchall()
    order["lines"] = [dict(line) for line in line_rows]
    return order


def create_supplier_orders(
    settings: Any,
    username: str,
    *,
    snapshot_id: int,
    warehouse: str,
    lines: list[dict[str, Any]],
    note: str = "",
) -> list[dict[str, Any]]:
    """Create one local prepared document per supplier; never writes to the ERP."""
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
        snapshot = conn.execute(
            "SELECT id FROM warehouse_snapshots WHERE id=?", (snapshot_id,)
        ).fetchone()
        if snapshot is None:
            raise WarehouseAssistantError("Snapshot انتخاب‌شده پیدا نشد.")
        rows = conn.execute(
            f"""SELECT product_code, product_name, brand, manufacturer,
                       conversion_rate, buy_price
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
                    "buy_price": buy_price,
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
            order_number = f"SUP-{created_at[:10].replace('-', '')}-{order_id:06d}"
            conn.execute(
                "UPDATE supplier_orders SET order_number=? WHERE id=?",
                (order_number, order_id),
            )
            conn.executemany(
                """INSERT INTO supplier_order_lines
                   (order_id, product_code, product_name, brand, conversion_rate,
                    requested_quantity, order_quantity, cartons, buy_price,
                    estimated_value, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
    settings: Any, username: str, *, include_all: bool = False, limit: int = 50
) -> list[dict[str, Any]]:
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        if include_all:
            rows = conn.execute(
                "SELECT * FROM supplier_orders ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM supplier_orders WHERE created_by=?
                   ORDER BY id DESC LIMIT ?""",
                (username, limit),
            ).fetchall()
        return [_order_from_row(conn, row) for row in rows]


def supplier_order_text(order: dict[str, Any]) -> str:
    lines = [
        "سفارش خرید نگین پخش",
        f"شماره سفارش: {order['order_number']}",
        f"تأمین‌کننده: {order['supplier']}",
        f"انبار مقصد: {order['warehouse_name']}",
        f"تاریخ آماده‌سازی: {order['created_at']}",
        "",
        "ردیف | کد کالا | نام کالا | برند | تعداد | کارتن",
    ]
    for index, item in enumerate(order["lines"], start=1):
        lines.append(
            f"{index} | {item['product_code']} | {item['product_name']} | "
            f"{item['brand'] or '-'} | {_clean_number(item['order_quantity'])} | {item['cartons']}"
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
