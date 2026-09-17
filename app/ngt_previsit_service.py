"""Read-only NGT catalogue and authoritative pre-sale calculation bridge.

The functions in this module may read NGT/Varanegar data and call the NGT EVC
calculation endpoint.  They never create an order.  Operational submission is
kept behind the separate ``NGT_PILOT_SEND_ENABLED`` guard.
"""

from __future__ import annotations

from copy import deepcopy
from collections import Counter
import gzip
import json
import re
from datetime import date
from threading import Lock
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from app.business_time import jalali_business_date
from app.database import sql_connection
from app.models import PrevisitPreviewRequest
from app.previsit_service import PrevisitError, get_visit_draft
from app.seller_workspace_service import (
    SellerDayRouteMismatch,
    _seller_profile,
    require_seller_day_route,
    seller_route_customers,
)


_CONTEXT_CACHE_TTL_SECONDS = 300
_CONTEXT_CACHE_MAX_ENTRIES = 12
_context_cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
_context_cache_lock = Lock()
_seller_context_cache: dict[tuple[Any, ...], tuple[float, dict[str, Any]]] = {}
_seller_context_cache_lock = Lock()
_seller_context_load_locks: dict[tuple[Any, ...], Lock] = {}


def _cached_context(key: tuple[Any, ...]) -> dict[str, Any] | None:
    now = monotonic()
    with _context_cache_lock:
        cached = _context_cache.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at <= now:
            _context_cache.pop(key, None)
            return None
        return deepcopy(value)


def _store_context(key: tuple[Any, ...], value: dict[str, Any]) -> None:
    now = monotonic()
    with _context_cache_lock:
        expired = [item_key for item_key, item in _context_cache.items() if item[0] <= now]
        for item_key in expired:
            _context_cache.pop(item_key, None)
        if len(_context_cache) >= _CONTEXT_CACHE_MAX_ENTRIES:
            oldest_key = min(_context_cache, key=lambda item_key: _context_cache[item_key][0])
            _context_cache.pop(oldest_key, None)
        _context_cache[key] = (now + _CONTEXT_CACHE_TTL_SECONDS, deepcopy(value))


def _cached_seller_context(key: tuple[Any, ...]) -> dict[str, Any] | None:
    now = monotonic()
    with _seller_context_cache_lock:
        cached = _seller_context_cache.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at <= now:
            _seller_context_cache.pop(key, None)
            return None
        return deepcopy(value)


def _store_seller_context(key: tuple[Any, ...], value: dict[str, Any]) -> None:
    now = monotonic()
    with _seller_context_cache_lock:
        expired = [item_key for item_key, item in _seller_context_cache.items() if item[0] <= now]
        for item_key in expired:
            _seller_context_cache.pop(item_key, None)
        if len(_seller_context_cache) >= _CONTEXT_CACHE_MAX_ENTRIES:
            oldest_key = min(_seller_context_cache, key=lambda item_key: _seller_context_cache[item_key][0])
            _seller_context_cache.pop(oldest_key, None)
        _seller_context_cache[key] = (now + _CONTEXT_CACHE_TTL_SECONDS, deepcopy(value))


def _seller_context_load_lock(key: tuple[Any, ...]) -> Lock:
    with _seller_context_cache_lock:
        return _seller_context_load_locks.setdefault(key, Lock())


_VOICE_VOCABULARY_IGNORED_WORDS = {
    "برای", "این", "آن", "کالا", "مدل", "نوع", "عدد", "دانه", "بسته", "کارتن",
    "محصول", "شرکت", "تولید", "کننده", "مناسب", "دارای", "بدون", "استفاده", "شده",
    "گرم", "میل", "میلی", "لیتر", "سانتی", "متر", "رنگ", "جدید", "بزرگ", "کوچک",
}


def _clean_voice_vocabulary_term(value: Any, *, max_length: int = 140) -> str:
    """Keep ERP catalogue text useful as prompt data, never as prompt instructions."""
    term = str(value or "").replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    term = term.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    term = term.replace("_", " ").replace("\u200f", " ").replace("\u200e", " ")
    term = re.sub(r"[^0-9A-Za-zآ-ی\u200c٪%+./()\- ]+", " ", term)
    term = re.sub(r"\s+", " ", term).strip(" .،؛:-")
    return term[:max_length].strip()


def _unique_voice_terms(values: Any) -> list[str]:
    unique: dict[str, str] = {}
    for value in values:
        term = _clean_voice_vocabulary_term(value)
        key = term.casefold().replace("\u200c", " ")
        if len(key) >= 2 and key not in unique:
            unique[key] = term
    return list(unique.values())


def _voice_vocabulary_section(title: str, terms: list[str], max_chars: int) -> str:
    if max_chars <= len(title) + 4:
        return ""
    selected: list[str] = []
    used = len(title) + 2
    for term in terms:
        addition = len(term) + (2 if selected else 0)
        if used + addition > max_chars:
            break
        selected.append(term)
        used += addition
    return f"{title}: " + "، ".join(selected) if selected else ""


def build_previsit_voice_vocabulary(
    products: list[dict[str, Any]],
    *,
    max_chars: int = 7_800,
) -> str:
    """Build a bounded, structured Persian order vocabulary for the transcription model."""
    limit = max(800, min(int(max_chars), 8_000))
    products = [item for item in products if isinstance(item, dict)]
    ordered_products = sorted(
        products,
        key=lambda item: (
            0 if float(item.get("available_qty") or 0) > 0 else 1,
            str(item.get("brand") or "").casefold(),
            str(item.get("group") or "").casefold(),
            str(item.get("name") or "").casefold(),
        ),
    )
    brands = sorted(_unique_voice_terms(item.get("brand") for item in products), key=str.casefold)
    groups = sorted(_unique_voice_terms(item.get("group") for item in products), key=str.casefold)
    manufacturers = sorted(
        _unique_voice_terms(item.get("manufacturer") for item in products),
        key=str.casefold,
    )
    product_names = _unique_voice_terms(item.get("name") for item in ordered_products)

    word_frequency: Counter[str] = Counter()
    word_display: dict[str, str] = {}
    for item in ordered_products:
        searchable = " ".join(
            _clean_voice_vocabulary_term(item.get(field))
            for field in ("name", "description", "group", "manufacturer")
        )
        for word in re.findall(r"[0-9A-Za-zآ-ی\u200c-]{2,}", searchable):
            key = word.casefold().replace("\u200c", " ")
            if key in _VOICE_VOCABULARY_IGNORED_WORDS or key.isdigit():
                continue
            word_frequency[key] += 1
            word_display.setdefault(key, word)
    keywords = [
        word_display[key]
        for key, _count in sorted(
            word_frequency.items(),
            key=lambda item: (-item[1], -len(item[0]), item[0]),
        )
    ]

    fixed = (
        "این فهرست فقط واژگان مجاز کاتالوگ است. "
        "واحدهای سفارش: عدد یعنی دانه یا دونه یا تا؛ بسته یعنی پک؛ کارتن یعنی کارتون یا کرتن. "
        "صورت معیار را عدد، بسته یا کارتن بنویس و مقدار گفته‌شده را تغییر نده"
    )
    remaining = max(0, limit - len(fixed) - 8)
    budgets = {
        "brands": max(140, int(remaining * 0.13)),
        "groups": max(120, int(remaining * 0.10)),
        "manufacturers": max(100, int(remaining * 0.07)),
        "keywords": max(300, int(remaining * 0.25)),
    }
    brand_section = _voice_vocabulary_section("برندهای مجاز", brands, budgets["brands"])
    group_section = _voice_vocabulary_section("گروه‌های مجاز", groups, budgets["groups"])
    manufacturer_section = _voice_vocabulary_section(
        "تولیدکنندگان", manufacturers, budgets["manufacturers"]
    )
    keyword_section = _voice_vocabulary_section(
        "واژه‌های شاخص کالا", keywords, budgets["keywords"]
    )
    # Small catalogues rarely consume the reserved brand/group budgets. Give
    # every unused character to exact SKU names, which provide the strongest
    # hint when several products differ only by size, scent or pack count.
    non_product_sections = [
        section
        for section in (brand_section, group_section, manufacturer_section, keyword_section)
        if section
    ]
    product_budget = max(
        300,
        limit - len(fixed) - sum(map(len, non_product_sections)) - 2 * len(non_product_sections) - 4,
    )
    product_section = _voice_vocabulary_section(
        "نام کامل کالاهای مجاز", product_names, product_budget
    )
    sections = [fixed]
    for section in (
        brand_section,
        group_section,
        manufacturer_section,
        product_section,
        keyword_section,
    ):
        if section:
            sections.append(section)
    return ". ".join(sections)[:limit].rstrip(" .،")


def cached_previsit_vocabulary(
    settings: Any,
    username: str,
    path_id: str,
    customer_id: str,
    *,
    max_chars: int = 7_800,
) -> str:
    """Return safe catalogue words for speech recognition without another SQL query."""
    try:
        clean_path_id = str(UUID(str(path_id)))
    except (ValueError, TypeError, AttributeError):
        return ""
    key = (
        id(settings),
        str(username).casefold(),
        clean_path_id,
        str(customer_id),
        "",
        1000,
    )
    context = _cached_context(key)
    if context is None:
        return ""
    return build_previsit_voice_vocabulary(context.get("products") or [], max_chars=max_chars)


def _rows(settings: Any, sql: str) -> list[dict[str, Any]]:
    # A busy SQL Server occasionally drops the first catalogue request at the
    # configured query timeout. Reconnect and retry this read-only query once.
    for attempt in range(2):
        try:
            with sql_connection(settings) as connection:
                cursor = connection.cursor()
                cursor.execute(sql)
                columns = [str(item[0]) for item in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except TimeoutError:
            if attempt:
                raise
    return []


def _grouped_catalogs(settings: Any, products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return visual catalogues restricted to the seller's allowed SKUs."""
    products_by_unique_id = {
        str(item.get("unique_id") or "").casefold(): item
        for item in products
        if item.get("unique_id")
    }
    if not products_by_unique_id:
        return []
    rows = _rows(
        settings,
        """
SELECT catalog.Id AS CatalogId, catalog.CatalogName,
       catalog.ProductMainGroupUniqueId, catalog.RowIndex AS CatalogOrder,
       image_info.ImageName, link.ProductUniqueId, link.OrderOf AS ProductOrder
FROM NGT.Catalogs AS catalog
INNER JOIN NGT.CatalogProducts AS link
  ON link.CatalogUniqueId = catalog.Id AND ISNULL(link.IsRemoved, 0) = 0
OUTER APPLY (
  SELECT TOP 1 image_row.ImageName
  FROM NGT.ImageInfoes AS image_row
  WHERE image_row.TokenId = catalog.Id
    AND image_row.ImageType = N'CatalogLarge'
    AND ISNULL(image_row.IsRemoved, 0) = 0
  ORDER BY image_row.IsDefault DESC, image_row.LastUpdate DESC
) AS image_info
WHERE ISNULL(catalog.IsRemoved, 0) = 0
  AND ISNULL(catalog.IsActive, 1) = 1
ORDER BY catalog.RowIndex, catalog.CatalogName, link.OrderOf
""".strip(),
    )
    grouped: dict[str, dict[str, Any]] = {}
    product_order: dict[str, list[tuple[int, str]]] = {}
    for row in rows:
        product = products_by_unique_id.get(str(row.get("ProductUniqueId") or "").casefold())
        if product is None:
            continue
        catalog_id = str(row.get("CatalogId") or "").lower()
        if not catalog_id:
            continue
        image_name = str(row.get("ImageName") or "").strip()
        group = grouped.setdefault(
            catalog_id,
            {
                "id": catalog_id,
                "name": str(row.get("CatalogName") or "").strip(),
                "main_group_unique_id": str(row.get("ProductMainGroupUniqueId") or "").lower(),
                "row_index": int(row.get("CatalogOrder") or 0),
                "image_url": (
                    f"/seller-workspace/previsit/catalog-images/{catalog_id}/{image_name}?size=thumb"
                    if image_name else ""
                ),
                "product_ids": [],
                "brands": [],
                "group_ids": [],
            },
        )
        product_order.setdefault(catalog_id, []).append(
            (int(row.get("ProductOrder") or 0), str(product["id"]))
        )
        brand = str(product.get("brand") or "").strip()
        group_id = str(product.get("group_id") or "").strip()
        if brand and brand not in group["brands"]:
            group["brands"].append(brand)
        if group_id and group_id not in group["group_ids"]:
            group["group_ids"].append(group_id)
    result = list(grouped.values())
    for group in result:
        ordered_ids = sorted(product_order.get(group["id"], []), key=lambda item: (item[0], item[1]))
        group["product_ids"] = list(dict.fromkeys(product_id for _, product_id in ordered_ids))
        group["brands"].sort(key=str.casefold)
        group["group_ids"].sort()
    return sorted(result, key=lambda item: (item["row_index"], item["name"].casefold(), item["id"]))


def catalog_image(settings: Any, catalog_id: str, image_name: str, size: str = "thumb") -> tuple[bytes, str]:
    """Read a catalogue image through this app without exposing upstream URLs."""
    clean_id = str(UUID(str(catalog_id))).lower()
    clean_name = str(image_name or "").strip()
    match = re.fullmatch(
        r"([0-9a-f-]{36})\.(jpg|jpeg|png|webp)",
        clean_name,
        flags=re.IGNORECASE,
    )
    if not match or str(UUID(match.group(1))).lower() != clean_id:
        raise ValueError("تصویر کاتالوگ معتبر نیست")
    folders = {"thumb": "100x100", "display": "320x320", "original": "orginal"}
    image_folder = folders.get(str(size or "").casefold())
    if not image_folder:
        raise ValueError("اندازه تصویر کاتالوگ معتبر نیست")
    base_url = str(settings.ngt_api_base_url or "").rstrip("/")
    if not base_url:
        raise ValueError("سرویس تصاویر کاتالوگ تنظیم نشده است")
    image_url = (
        f"{base_url}/Content/Images/CatalogLarge/{image_folder}/"
        f"{clean_id}/{clean_name}"
    )
    request = Request(image_url, headers={"Accept": "image/avif,image/webp,image/*,*/*"})
    with urlopen(request, timeout=20) as response:
        content_type = str(response.headers.get_content_type() or "image/jpeg")
        return response.read(), content_type


def _validate_assignment(settings: Any, username: str, path_id: str, customer_id: str) -> dict[str, Any]:
    try:
        clean_path_id = str(UUID(str(path_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise PrevisitError("مسیر انتخاب‌شده معتبر نیست") from exc
    try:
        require_seller_day_route(settings, username, clean_path_id)
    except SellerDayRouteMismatch as exc:
        raise PrevisitError(str(exc)) from exc
    route = seller_route_customers(settings, username, clean_path_id)
    customer = next(
        (item for item in route["customers"] if str(item["id"]) == str(customer_id)),
        None,
    )
    if not customer:
        raise PrevisitError("مشتری در مسیر جاری این فروشنده نیست")
    return {"path_id": clean_path_id, "route": route, "customer": customer}


def _context_rows(settings: Any, personnel_id: int) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    device_sql = f"""
SELECT TOP 1 ds.DeviceSettingNo, ds.SubSystemTypeUniqueId,
       ds.ShowStockLevel, ds.OnlineRefreshStockLevel, ds.ApplyCurrentOrdersInInventory,
       ds.CustomerAdvancedCreditControl, ds.AllowCashWithoutAdvancedCreditControl,
       ds.SelectStockPreSale, ds.ListOfStockPreSale, ds.BoStockUniqueID,
       COALESCE(recent_order.SaleOfficeRefSDS, 1) AS SaleOfficeRef,
       COALESCE(recent_order.DcRefSDS, 1) AS DcRef
FROM NGT.Users AS app_user
INNER JOIN NGT.DeviceUsers AS device_user
  ON device_user.UserUniqueId = app_user.Id AND ISNULL(device_user.IsRemoved, 0) = 0
INNER JOIN NGT.DeviceSettings AS ds
  ON ds.Id = device_user.DeviceSettingUniqueId AND ISNULL(ds.IsRemoved, 0) = 0
OUTER APPLY (
  SELECT TOP 1 order_header.SaleOfficeRefSDS, order_header.DcRefSDS
  FROM NGT.CustomerCallOrders AS order_header
  WHERE order_header.DealerRefSDS = {personnel_id}
    AND order_header.SaleOfficeRefSDS IS NOT NULL
    AND ISNULL(order_header.IsRemoved, 0) = 0
  ORDER BY order_header.LastUpdate DESC
) AS recent_order
WHERE app_user.BackOfficePersonnelId = {personnel_id}
  AND ISNULL(app_user.IsRemoved, 0) = 0
  AND ISNULL(app_user.IsActive, 1) = 1
ORDER BY ds.LastUpdate DESC
""".strip()
    device_rows = _rows(settings, device_sql)
    if not device_rows:
        raise PrevisitError("تنظیمات اپ ویزیت این فروشنده در NGT پیدا نشد")
    device = device_rows[0]

    order_types_sql = f"""
SELECT DISTINCT order_type.BackOfficeId, order_type.OrderTypeName
FROM NGT.Users AS app_user
INNER JOIN NGT.DeviceUsers AS device_user
  ON device_user.UserUniqueId = app_user.Id AND ISNULL(device_user.IsRemoved, 0) = 0
INNER JOIN NGT.DeviceOrderTypes AS allowed
  ON allowed.DeviceSettingUniqueId = device_user.DeviceSettingUniqueId
 AND ISNULL(allowed.IsRemoved, 0) = 0
INNER JOIN NGT.OrderTypes AS order_type
  ON order_type.Id = allowed.OrderTypeUniqueId AND ISNULL(order_type.IsRemoved, 0) = 0
WHERE app_user.BackOfficePersonnelId = {personnel_id}
  AND ISNULL(app_user.IsRemoved, 0) = 0
ORDER BY order_type.BackOfficeId
""".strip()
    payment_types_sql = f"""
SELECT DISTINCT payment_order.BackOfficeId, payment_order.PaymentTypeOrderName,
       payment_type.BackOfficeId AS BuyTypeRef,
       payment_order.PaymentDeadLine, payment_order.PaymentTime, payment_order.IsCash,
       payment_order.CheckCredit, payment_order.CheckDebit
FROM NGT.Personnels AS personnel
INNER JOIN NGT.DealerPaymentTypes AS allowed
  ON allowed.DealerUniqueId = personnel.Id AND ISNULL(allowed.IsRemoved, 0) = 0
INNER JOIN NGT.PaymentTypeOrders AS payment_order
  ON payment_order.Id = allowed.PaymentTypeOrderUniqueId
 AND ISNULL(payment_order.IsRemoved, 0) = 0
INNER JOIN NGT.PaymentTypes AS payment_type
  ON payment_type.Id = payment_order.PaymentTypeUniqueId
 AND ISNULL(payment_type.IsRemoved, 0) = 0
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND ISNULL(personnel.IsRemoved, 0) = 0
ORDER BY payment_order.BackOfficeId
""".strip()
    return device, _rows(settings, order_types_sql), _rows(settings, payment_types_sql)


def _device_warehouse_ids(device: dict[str, Any]) -> list[str]:
    raw_values = str(device.get("ListOfStockPreSale") or "").split(",")
    if device.get("BoStockUniqueID"):
        raw_values.append(str(device["BoStockUniqueID"]))
    values: list[str] = []
    for raw_value in raw_values:
        try:
            value = str(UUID(raw_value.strip()))
        except (ValueError, AttributeError):
            continue
        if value not in values:
            values.append(value)
    return values


def _device_warehouses(settings: Any, device: dict[str, Any]) -> list[dict[str, Any]]:
    warehouse_ids = _device_warehouse_ids(device)
    if not warehouse_ids:
        return []
    ids_sql = ",".join(f"N'{warehouse_id}'" for warehouse_id in warehouse_ids)
    rows = _rows(
        settings,
        f"""
SELECT stock.Id, stock.BackOfficeId, stock.StockName, stock_dc.DCRef
FROM NGT.Stocks AS stock
LEFT JOIN GNR.tblStockDC AS stock_dc
  ON stock_dc.ID = TRY_CONVERT(int, stock.BackOfficeId)
WHERE stock.Id IN ({ids_sql})
  AND ISNULL(stock.IsRemoved, 0) = 0
""".strip(),
    )
    by_id = {str(row["Id"]).casefold(): row for row in rows}
    return [
        {
            "id": warehouse_id,
            "ref": int(by_id[warehouse_id.casefold()]["BackOfficeId"]),
            "name": str(by_id[warehouse_id.casefold()].get("StockName") or "").strip(),
            "dc_ref": int(by_id[warehouse_id.casefold()].get("DCRef") or 0),
        }
        for warehouse_id in warehouse_ids
        if warehouse_id.casefold() in by_id
        and str(by_id[warehouse_id.casefold()].get("BackOfficeId") or "").isdigit()
    ]


def _product_warehouse_inventory(
    settings: Any,
    product_ids: list[int],
    warehouses: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, float]]]:
    safe_product_ids = sorted({int(product_id) for product_id in product_ids if int(product_id) > 0})
    safe_stock_refs = sorted({int(item["ref"]) for item in warehouses if int(item.get("ref") or 0) > 0})
    if not safe_product_ids or not safe_stock_refs:
        return {}
    rows = _rows(
        settings,
        f"""
WITH ranked_stock AS (
  SELECT qty.GoodsRef, qty.StockDCRef, qty.OnHandQty, qty.ReservedQty,
         ROW_NUMBER() OVER (
           PARTITION BY qty.GoodsRef, qty.StockDCRef
           ORDER BY qty.AccYear DESC
         ) AS StockRank
  FROM GNR.tblStockGoods AS qty
  WHERE qty.GoodsRef IN ({','.join(str(value) for value in safe_product_ids)})
    AND qty.StockDCRef IN ({','.join(str(value) for value in safe_stock_refs)})
)
SELECT GoodsRef, StockDCRef, ISNULL(OnHandQty, 0) AS OnHandQty,
       ISNULL(ReservedQty, 0) AS ReservedQty,
       CASE WHEN ISNULL(OnHandQty, 0) - ISNULL(ReservedQty, 0) < 0
            THEN 0 ELSE ISNULL(OnHandQty, 0) - ISNULL(ReservedQty, 0) END AS AvailableQty
FROM ranked_stock
WHERE StockRank = 1
""".strip(),
    )
    inventory: dict[str, dict[str, dict[str, float]]] = {}
    for row in rows:
        product_id = str(int(row["GoodsRef"]))
        stock_ref = str(int(row["StockDCRef"]))
        inventory.setdefault(product_id, {})[stock_ref] = {
            "on_hand_qty": float(row.get("OnHandQty") or 0),
            "reserved_qty": float(row.get("ReservedQty") or 0),
            "available_qty": float(row.get("AvailableQty") or 0),
        }
    return inventory


def _product_order_type_prices(
    settings: Any,
    product_ids: list[int],
    order_type_refs: list[int],
    business_date: str,
) -> dict[str, dict[str, dict[str, float]]]:
    """Read one generic base-price row per product/order type.

    These values make catalogue cards react to the selected order type. They
    remain indicative: customer/payment/quantity rules are only authoritative
    after the official NGT EVC preview.
    """
    clean_products = sorted({int(value) for value in product_ids if int(value) > 0})
    clean_order_types = sorted({int(value) for value in order_type_refs if int(value) > 0})
    if not clean_products or not clean_order_types:
        return {}
    product_sql = ",".join(str(value) for value in clean_products)
    order_type_sql = ",".join(str(value) for value in clean_order_types)
    rows = _rows(
        settings,
        f"""
WITH ranked_price AS (
  SELECT TRY_CONVERT(int, history.GoodsRef) AS GoodsRef,
         TRY_CONVERT(int, history.OrderTypeRef) AS OrderTypeRef,
         history.SalePrice, history.UserPrice,
         source_price.ManufacturerPrice,
         ROW_NUMBER() OVER (
           PARTITION BY TRY_CONVERT(int, history.GoodsRef), TRY_CONVERT(int, history.OrderTypeRef)
           ORDER BY history.StartDate DESC, history.LastUpdate DESC
         ) AS PriceRank
  FROM NGT.ContractPrices AS history
  LEFT JOIN SLE.tblCPrice AS source_price ON source_price.UniqueId = history.Id
  WHERE TRY_CONVERT(int, history.GoodsRef) IN ({product_sql})
    AND TRY_CONVERT(int, history.OrderTypeRef) IN ({order_type_sql})
    AND ISNULL(history.IsRemoved, 0) = 0
    AND history.StartDate <= N'{business_date}'
    AND (history.EndDate IS NULL OR history.EndDate = '' OR history.EndDate >= N'{business_date}')
    AND (history.CustRef IS NULL OR history.CustRef = '')
    AND (history.CustCtgrRef IS NULL OR history.CustCtgrRef = '')
    AND (history.CustActRef IS NULL OR history.CustActRef = '')
    AND (history.CustLevelRef IS NULL OR history.CustLevelRef = '')
    AND (history.MainCustTypeRef IS NULL OR history.MainCustTypeRef = 0)
    AND (history.SubCustTypeRef IS NULL OR history.SubCustTypeRef = 0)
    AND (history.StateRef IS NULL OR history.StateRef = '')
    AND (history.CountyRef IS NULL OR history.CountyRef = '')
    AND (history.AreaRef IS NULL OR history.AreaRef = '')
    AND (history.BuyTypeRef IS NULL OR history.BuyTypeRef = '')
    AND (history.UsanceDay IS NULL OR history.UsanceDay = 0)
    AND (history.DealerCtgrRef IS NULL OR history.DealerCtgrRef = '')
    AND (history.DCRef IS NULL OR history.DCRef = '')
    AND (history.SaleOfficeRef IS NULL OR history.SaleOfficeRef = 0)
)
SELECT GoodsRef, OrderTypeRef, SalePrice, UserPrice, ManufacturerPrice
FROM ranked_price
WHERE PriceRank = 1
""".strip(),
    )
    result: dict[str, dict[str, dict[str, float]]] = {}
    for row in rows:
        product_key = str(int(row["GoodsRef"]))
        order_key = str(int(row["OrderTypeRef"]))
        result.setdefault(product_key, {})[order_key] = {
            "indicative_price": float(row.get("SalePrice") or 0),
            "consumer_price": float(row.get("UserPrice") or 0),
            "manufacturer_price": float(row.get("ManufacturerPrice") or 0),
        }
    return result


def _catalog_sale_units(row: dict[str, Any]) -> list[dict[str, Any]]:
    """Return sale units with their authoritative base-unit conversion factor."""
    raw_units = row.get("SaleUnitsJson") or "[]"
    try:
        parsed_units = json.loads(raw_units) if isinstance(raw_units, str) else list(raw_units)
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed_units = []

    units: list[dict[str, Any]] = []
    seen: set[tuple[Any, str, float]] = set()

    def append_unit(ref: Any, name: Any, factor: Any, is_default: Any = False) -> None:
        try:
            numeric_factor = float(factor)
        except (TypeError, ValueError):
            return
        if numeric_factor <= 0:
            return
        numeric_ref = None
        try:
            if ref not in (None, ""):
                numeric_ref = int(ref)
        except (TypeError, ValueError):
            numeric_ref = None
        unit_name = str(name or "").strip() or ("عدد" if numeric_factor == 1 else "واحد فروش")
        identity = (numeric_ref, unit_name.casefold(), numeric_factor)
        if identity in seen:
            return
        seen.add(identity)
        units.append(
            {
                "ref": numeric_ref,
                "name": unit_name,
                "factor": numeric_factor,
                "is_default": bool(is_default),
            }
        )

    for unit in parsed_units if isinstance(parsed_units, list) else []:
        if isinstance(unit, dict):
            append_unit(unit.get("ref"), unit.get("name"), unit.get("factor"), unit.get("is_default"))

    if not any(unit["factor"] == 1 for unit in units):
        append_unit(row.get("BaseUnitRef"), row.get("UnitName") or "عدد", 1)

    carton_factor = float(row.get("sdpmsCartonQty") or row.get("CartonType") or 0)
    if carton_factor > 1 and not any(unit["factor"] == carton_factor for unit in units):
        append_unit(None, "کارتن", carton_factor)

    return sorted(units, key=lambda unit: (unit["factor"], unit["name"].casefold()))


def _build_previsit_context(
    settings: Any,
    username: str,
    path_id: str,
    customer_id: str,
    *,
    search: str = "",
    limit: int = 250,
) -> dict[str, Any]:
    assignment = _validate_assignment(settings, username, path_id, customer_id)
    cache_key = (
        id(settings),
        str(username).casefold(),
        assignment["path_id"],
        str(customer_id),
        search.strip().casefold(),
        max(1, min(int(limit), 1000)),
    )
    cached = _cached_context(cache_key)
    if cached is not None:
        return cached
    profile = _seller_profile(settings, username)
    personnel_id = int(profile["personnel_id"])
    device, order_type_rows, payment_rows = _context_rows(settings, personnel_id)
    default_order_type_ref = int(order_type_rows[0]["BackOfficeId"]) if order_type_rows else 0
    allowed_order_type_refs = sorted({
        int(row["BackOfficeId"])
        for row in order_type_rows
        if row.get("BackOfficeId") is not None
    })
    business_date = jalali_business_date()

    catalog_sql = f"""
WITH ranked_price AS (
  SELECT TRY_CONVERT(int, history.GoodsRef) AS GoodsRef,
         history.SalePrice, history.UserPrice,
         source_price.ManufacturerPrice,
         ROW_NUMBER() OVER (
           PARTITION BY TRY_CONVERT(int, history.GoodsRef)
           ORDER BY history.StartDate DESC, history.LastUpdate DESC
         ) AS PriceRank
  FROM NGT.ContractPrices AS history
  LEFT JOIN SLE.tblCPrice AS source_price ON source_price.UniqueId = history.Id
  WHERE TRY_CONVERT(int, history.OrderTypeRef) = {default_order_type_ref}
    AND ISNULL(history.IsRemoved, 0) = 0
    AND history.StartDate <= N'{business_date}'
    AND (history.EndDate IS NULL OR history.EndDate = '' OR history.EndDate >= N'{business_date}')
    AND (history.CustRef IS NULL OR history.CustRef = '')
    AND (history.CustCtgrRef IS NULL OR history.CustCtgrRef = '')
    AND (history.CustActRef IS NULL OR history.CustActRef = '')
    AND (history.CustLevelRef IS NULL OR history.CustLevelRef = '')
    AND (history.MainCustTypeRef IS NULL OR history.MainCustTypeRef = 0)
    AND (history.SubCustTypeRef IS NULL OR history.SubCustTypeRef = 0)
    AND (history.StateRef IS NULL OR history.StateRef = '')
    AND (history.CountyRef IS NULL OR history.CountyRef = '')
    AND (history.AreaRef IS NULL OR history.AreaRef = '')
    AND (history.BuyTypeRef IS NULL OR history.BuyTypeRef = '')
    AND (history.UsanceDay IS NULL OR history.UsanceDay = 0)
    AND (history.DealerCtgrRef IS NULL OR history.DealerCtgrRef = '')
    AND (history.DCRef IS NULL OR history.DCRef = '')
    AND (history.SaleOfficeRef IS NULL OR history.SaleOfficeRef = 0)
)
SELECT product.ID AS GoodsRef, product.UniqueId AS ProductUniqueId,
       product.GoodsCode, product.GoodsName, product.Barcode,
       COALESCE(NULLIF(product.TechSpec, N''), NULLIF(product.PolDescription, N''), N'') AS ProductDescription,
       product.GoodsGroupRef, goods_group.GoodsGroupName,
       goods_group.ParentRef AS ParentGoodsGroupRef,
       parent_goods_group.GoodsGroupName AS ParentGoodsGroupName,
       product.MainGroupRef, product.SubGroupRef,
       product.UnitRef AS BaseUnitRef, product.CartonType, product.sdpmsCartonQty,
       product.MinOrderCount, product.MaxOrderCount,
       product.Tax, product.Charge, product.CartonPrizeQty,
       product.CanBeFree, product.UseBatchPackage,
       brand.BrandName, manufacturer.ManufacturerName,
       stock.Id AS StockUniqueId, stock.StockName, stock.BackOfficeId AS StockRef, unit.UnitName,
       (SELECT TRY_CONVERT(int, sale_unit.BackOfficeId) AS [ref],
               sale_unit.UnitName AS [name],
               product_unit.ConvertFactor AS [factor],
               product_unit.IsDefault AS [is_default]
        FROM NGT.ProductUnits AS product_unit
        INNER JOIN NGT.Units AS sale_unit ON sale_unit.Id = product_unit.UnitUniqueId
        WHERE product_unit.ProductUniqueId = product.UniqueId
          AND ISNULL(product_unit.IsRemoved, 0) = 0
          AND ISNULL(product_unit.IsForSale, 1) = 1
        ORDER BY product_unit.ConvertFactor, sale_unit.UnitName
        FOR JSON PATH) AS SaleUnitsJson,
       ISNULL(stock_qty.OnHandQty, 0) AS OnHandQty,
       ISNULL(stock_qty.ReservedQty, 0) AS ReservedQty,
       CASE WHEN ISNULL(stock_qty.OnHandQty, 0) - ISNULL(stock_qty.ReservedQty, 0) < 0
            THEN 0 ELSE ISNULL(stock_qty.OnHandQty, 0) - ISNULL(stock_qty.ReservedQty, 0) END AS AvailableQty,
       ISNULL(price.SalePrice, 0) AS IndicativePrice,
       ISNULL(price.UserPrice, 0) AS ConsumerPrice,
       ISNULL(price.ManufacturerPrice, 0) AS ManufacturerPrice,
       ISNULL(catalog_tax.MainTypeRef, 0) AS CatalogTaxMainTypeRef,
       ISNULL(catalog_tax.SubTypeRef, 0) AS CatalogTaxSubTypeRef,
       ISNULL(catalog_tax.TaxPercent, 0) AS CatalogTaxPercent
FROM NGT.Personnels AS personnel
INNER JOIN NGT.VisitTemplates AS visit_template ON visit_template.Id = personnel.VisitTemplateUniqueId
INNER JOIN NGT.ProductTemplates AS product_template
  ON product_template.Id = COALESCE(personnel.ProductTemplateUniqueId, visit_template.ProductTemplateUniqueId)
INNER JOIN NGT.ProductTemplateDetails AS template_line
  ON template_line.ProductTemplateUniqueId = product_template.Id
INNER JOIN GNR.tblGoods AS product ON product.UniqueId = template_line.ProductUniqueId
LEFT JOIN GNR.tblBrand AS brand ON brand.Id = product.BrandRef
LEFT JOIN GNR.tblManufacturer AS manufacturer ON manufacturer.Id = product.ManufacturerRef
LEFT JOIN GNR.tblGoodsGroup AS goods_group ON goods_group.ID = product.GoodsGroupRef
LEFT JOIN GNR.tblGoodsGroup AS parent_goods_group ON parent_goods_group.ID = goods_group.ParentRef
LEFT JOIN NGT.Stocks AS stock ON stock.Id = template_line.StockUniqueId
LEFT JOIN GNR.tblUnit AS unit ON unit.ID = product.UnitRef
LEFT JOIN ranked_price AS price
  ON price.GoodsRef = product.ID AND price.PriceRank = 1
OUTER APPLY (
  SELECT TOP 1 qty.OnHandQty, qty.ReservedQty
  FROM GNR.tblStockGoods AS qty
  WHERE qty.GoodsRef = product.ID
    AND qty.StockDCRef = TRY_CONVERT(int, stock.BackOfficeId)
  ORDER BY qty.AccYear DESC
) AS stock_qty
OUTER APPLY (
  SELECT TOP 1 goods_tax.MainTypeRef, goods_tax.SubTypeRef,
         TRY_CONVERT(decimal(9, 4), tax_subtype.SubName) AS TaxPercent
  FROM GNR.tblGoodsMainSubType AS goods_tax
  INNER JOIN GNR.tblMainType AS tax_main_type
    ON tax_main_type.Id = goods_tax.MainTypeRef
   AND tax_main_type.LookUpId = 501
  INNER JOIN GNR.tblSubType AS tax_subtype
    ON tax_subtype.Id = goods_tax.SubTypeRef
   AND tax_subtype.MainTypeRef = tax_main_type.Id
  WHERE goods_tax.GoodsRef = product.ID
  ORDER BY goods_tax.Id DESC
) AS catalog_tax
WHERE personnel.BackOfficeId = N'{personnel_id}'
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(template_line.IsRemoved, 0) = 0
  AND ISNULL(product_template.IsRemoved, 0) = 0
  AND ISNULL(product.ShowInSale, 1) = 1
ORDER BY product.GoodsName
""".strip()
    products = []
    needle = search.strip().casefold()
    for row in _rows(settings, catalog_sql):
        haystack = " ".join(
            str(row.get(key) or "") for key in ("GoodsRef", "GoodsCode", "GoodsName", "BrandName")
        ).casefold()
        if needle and needle not in haystack:
            continue
        indicative_price = float(row.get("IndicativePrice") or 0)
        catalog_tax_percent = float(row.get("CatalogTaxPercent") or 0)
        products.append(
            {
                "id": str(row["GoodsRef"]),
                "unique_id": str(row["ProductUniqueId"]),
                "code": str(row.get("GoodsCode") or ""),
                "name": str(row.get("GoodsName") or "").strip(),
                "brand": str(row.get("BrandName") or "").strip(),
                "barcode": str(row.get("Barcode") or "").strip(),
                "description": str(row.get("ProductDescription") or "").strip(),
                "group_id": str(row.get("GoodsGroupRef") or ""),
                "group": str(row.get("GoodsGroupName") or "").strip(),
                "group_parent_id": str(row.get("ParentGoodsGroupRef") or ""),
                "group_parent": str(row.get("ParentGoodsGroupName") or "").strip(),
                "smallest_group_id": str(row.get("GoodsGroupRef") or ""),
                "smallest_group": str(row.get("GoodsGroupName") or "").strip(),
                "main_group_ref": str(row.get("MainGroupRef") or ""),
                "sub_group_ref": str(row.get("SubGroupRef") or ""),
                "manufacturer": str(row.get("ManufacturerName") or "").strip(),
                "stock_name": str(row.get("StockName") or "").strip(),
                "stock_unique_id": str(row.get("StockUniqueId") or ""),
                "stock_ref": str(row.get("StockRef") or ""),
                "unit": str(row.get("UnitName") or "عدد").strip(),
                "sale_units": _catalog_sale_units(row),
                "on_hand_qty": float(row.get("OnHandQty") or 0),
                "reserved_qty": float(row.get("ReservedQty") or 0),
                "available_qty": float(row.get("AvailableQty") or 0),
                "carton_size": float(row.get("sdpmsCartonQty") or row.get("CartonType") or 0),
                "min_order_qty": float(row.get("MinOrderCount") or 0),
                "max_order_qty": float(row.get("MaxOrderCount") or 0),
                "tax_percent": float(row.get("Tax") or 0),
                "charge_percent": float(row.get("Charge") or 0),
                "carton_prize_qty": float(row.get("CartonPrizeQty") or 0),
                "can_be_free": bool(row.get("CanBeFree")),
                "has_batch": bool(row.get("UseBatchPackage")),
                "indicative_price": indicative_price,
                "consumer_price": float(row.get("ConsumerPrice") or 0),
                "manufacturer_price": float(row.get("ManufacturerPrice") or 0),
                "catalog_tax_main_type_ref": int(row.get("CatalogTaxMainTypeRef") or 0),
                "catalog_tax_sub_type_ref": int(row.get("CatalogTaxSubTypeRef") or 0),
                "catalog_tax_percent": catalog_tax_percent,
                "catalog_tax_inclusive_price": round(
                    indicative_price * (1 + catalog_tax_percent / 100)
                ) if indicative_price > 0 and catalog_tax_percent > 0 else indicative_price,
                "price_status": "active_base_contract_until_ngt_preview",
                "consumer_price_status": "active_contract_when_available",
                "manufacturer_price_status": "matched_source_contract_when_available",
                "indicative_order_type_ref": default_order_type_ref,
            }
        )
        if len(products) >= max(1, min(int(limit), 1000)):
            break

    price_matrix = _product_order_type_prices(
        settings,
        [int(item["id"]) for item in products],
        allowed_order_type_refs,
        business_date,
    )
    for product in products:
        prices = price_matrix.get(str(product["id"])) or {}
        product["indicative_prices"] = {
            order_ref: values["indicative_price"] for order_ref, values in prices.items()
        }
        product["consumer_prices"] = {
            order_ref: values["consumer_price"] for order_ref, values in prices.items()
        }
        product["manufacturer_prices"] = {
            order_ref: values["manufacturer_price"] for order_ref, values in prices.items()
        }

    grouped_catalogs = _grouped_catalogs(settings, products)

    brands = sorted({item["brand"] for item in products if item["brand"]})
    groups_by_id = {
        item["group_id"]: {"id": item["group_id"], "name": item["group"]}
        for item in products
        if item["group"]
    }
    groups = sorted(groups_by_id.values(), key=lambda item: item["name"])

    order_types = [
        {"id": int(row["BackOfficeId"]), "name": str(row["OrderTypeName"] or "").strip()}
        for row in order_type_rows
    ]
    payments = [
        {
            "id": str(row["BackOfficeId"]),
            "name": str(row["PaymentTypeOrderName"] or "").strip(),
            "buy_type_ref": int(row["BuyTypeRef"]),
            "payment_deadline": int(row.get("PaymentDeadLine") or 0),
            "payment_time": int(row.get("PaymentTime") or 0),
            "is_cash": bool(row.get("IsCash")),
            "check_credit": bool(row.get("CheckCredit")),
            "check_debit": bool(row.get("CheckDebit")),
        }
        for row in payment_rows
    ]
    warehouses = _device_warehouses(settings, device)
    if not warehouses:
        fallback_by_ref = {
            item["stock_ref"]: {
                "id": item["stock_unique_id"],
                "ref": int(item["stock_ref"]),
                "name": item["stock_name"],
                "dc_ref": int(device.get("DcRef") or 0),
            }
            for item in products
            if str(item.get("stock_ref") or "").isdigit()
        }
        warehouses = list(fallback_by_ref.values())
    warehouse_inventory = _product_warehouse_inventory(
        settings,
        [int(item["id"]) for item in products],
        warehouses,
    )
    for product in products:
        product_inventory = warehouse_inventory.get(str(product["id"]), {})
        if not product_inventory and product.get("stock_ref"):
            product_inventory[str(product["stock_ref"])] = {
                "on_hand_qty": product["on_hand_qty"],
                "reserved_qty": product["reserved_qty"],
                "available_qty": product["available_qty"],
            }
        product["warehouse_inventory"] = product_inventory
    default_warehouse_ref = int(warehouses[0]["ref"]) if warehouses else 0
    result = {
        "seller": {"personnel_id": personnel_id, "full_name": profile["full_name"]},
        "route": {"id": assignment["path_id"], "title": assignment["route"]["route"]["title"]},
        "customer": assignment["customer"],
        "order_types": order_types,
        "payment_types": payments,
        "warehouses": warehouses,
        "warehouse_selection": {
            "enabled": bool(device.get("SelectStockPreSale")) and len(warehouses) > 1,
            "default_ref": default_warehouse_ref,
            "source": "NGT.DeviceSettings.ListOfStockPreSale",
        },
        "products": products,
        "grouped_catalogs": grouped_catalogs,
        "grouped_catalog_count": len(grouped_catalogs),
        "catalog_count": len(products),
        "catalog_filters": {"brands": brands, "groups": groups},
        "inventory": {
            "show_stock_level": bool(device.get("ShowStockLevel")),
            "online_refresh": bool(device.get("OnlineRefreshStockLevel")),
            "applies_current_orders": bool(device.get("ApplyCurrentOrdersInInventory")),
            "source": "NGT product template + GNR.tblStockGoods",
        },
        "preview": {
            "available": bool(settings.ngt_api_base_url),
            "authoritative": True,
            "creates_order": False,
        },
        "pricing": {
            "catalog_kind": "indicative_base_contract",
            "catalog_order_type_ref": default_order_type_ref,
            "catalog_cache_seconds": _CONTEXT_CACHE_TTL_SECONDS,
            "official_preview_depends_on": [
                "customer", "order_type", "payment_type", "warehouse", "quantity"
            ],
            "official_source": "NGT EVC presale",
        },
        "credit_control": {
            "checked_on_registration": True,
            "advanced_control": bool(device.get("CustomerAdvancedCreditControl")),
            "allow_cash_without_advanced_control": bool(
                device.get("AllowCashWithoutAdvancedCreditControl")
            ),
            "source": "NGT customer balance + Varanegar order credit settings",
        },
        "_bridge": {
            "sale_office_ref": int(device.get("SaleOfficeRef") or 1),
            "dc_ref": int(device.get("DcRef") or 1),
            "subsystem_type_unique_id": str(device["SubSystemTypeUniqueId"]),
        },
    }
    _store_context(cache_key, result)
    return result


def previsit_context(
    settings: Any,
    username: str,
    path_id: str,
    customer_id: str,
    *,
    search: str = "",
    limit: int = 250,
) -> dict[str, Any]:
    """Return customer context while sharing the expensive seller catalogue.

    Assignment is deliberately revalidated for every customer. Only the seller's
    NGT device settings, allowed order/payment types, catalogue, stock and base
    prices are shared for five minutes. A per-seller lock prevents simultaneous
    cold requests from running the same catalogue query more than once.
    """
    assignment = _validate_assignment(settings, username, path_id, customer_id)
    clean_search = search.strip().casefold()
    clean_limit = max(1, min(int(limit), 1000))
    context_key = (
        id(settings),
        str(username).casefold(),
        assignment["path_id"],
        str(customer_id),
        clean_search,
        clean_limit,
    )
    cached = _cached_context(context_key)
    if cached is not None:
        return cached

    seller_key = (
        id(settings),
        str(username).casefold(),
        jalali_business_date(),
    )
    shared = _cached_seller_context(seller_key)
    if shared is None:
        with _seller_context_load_lock(seller_key):
            shared = _cached_seller_context(seller_key)
            if shared is None:
                loaded = _build_previsit_context(
                    settings,
                    username,
                    assignment["path_id"],
                    customer_id,
                    search="",
                    limit=1000,
                )
                shared = deepcopy(loaded)
                shared.pop("route", None)
                shared.pop("customer", None)
                _store_seller_context(seller_key, shared)

    result = deepcopy(shared)
    result["route"] = {
        "id": assignment["path_id"],
        "title": assignment["route"]["route"]["title"],
    }
    result["customer"] = assignment["customer"]
    products = result.get("products") or []
    if clean_search:
        products = [
            item for item in products
            if clean_search in " ".join(
                str(item.get(key) or "") for key in ("id", "code", "name", "brand")
            ).casefold()
        ]
    products = products[:clean_limit]
    result["products"] = products
    visible_product_ids = {str(item.get("id") or "") for item in products}
    grouped_catalogs = []
    for group in result.get("grouped_catalogs") or []:
        visible_ids = [
            product_id for product_id in group.get("product_ids") or []
            if str(product_id) in visible_product_ids
        ]
        if visible_ids:
            group["product_ids"] = visible_ids
            grouped_catalogs.append(group)
    result["grouped_catalogs"] = grouped_catalogs
    result["grouped_catalog_count"] = len(grouped_catalogs)
    result["catalog_count"] = len(products)
    result["catalog_filters"] = {
        "brands": sorted({item["brand"] for item in products if item.get("brand")}),
        "groups": sorted(
            {
                item["group_id"]: {"id": item["group_id"], "name": item["group"]}
                for item in products
                if item.get("group")
            }.values(),
            key=lambda item: item["name"],
        ),
    }
    _store_context(context_key, result)
    return result


def warm_previsit_route(settings: Any, username: str, path_id: str) -> dict[str, Any]:
    """Prime seller catalogue, order conditions and inventory without returning them."""
    route = seller_route_customers(settings, username, path_id)
    customers = route.get("customers") or []
    if not customers:
        raise PrevisitError("مسیر روز مشتری فعالی برای آماده‌سازی ندارد")
    customer_id = str(customers[0]["id"])
    context = previsit_context(settings, username, path_id, customer_id, limit=1000)
    return {
        "ready": True,
        "route_id": str(path_id),
        "catalog_count": int(context.get("catalog_count") or 0),
        "warehouse_count": len(context.get("warehouses") or []),
        "order_type_count": len(context.get("order_types") or []),
        "payment_type_count": len(context.get("payment_types") or []),
        "cache_seconds": _CONTEXT_CACHE_TTL_SECONDS,
        "source": "NGT seller context warmup",
    }


def _token(settings: Any) -> str:
    if (
        not settings.ngt_api_username
        or not settings.ngt_api_password
        or not settings.ngt_api_scope
    ):
        return ""
    body = urlencode(
        {
            "grant_type": "password",
            "username": settings.ngt_api_username,
            "password": settings.ngt_api_password,
            "scope": settings.ngt_api_scope,
        }
    ).encode("utf-8")
    request = Request(
        settings.ngt_api_base_url + "/" + settings.ngt_api_token_path.lstrip("/"),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("access_token") or payload.get("token") or "")


def _post_evc(
    settings: Any,
    payload: dict[str, Any],
    subsystem_id: str,
    *,
    calc_discount: bool = True,
    calc_sale_restriction: bool = False,
    calc_payment_type: bool = False,
) -> dict[str, Any]:
    if not settings.ngt_api_base_url:
        raise PrevisitError("آدرس API ورانگر برای پیش‌نمایش تنظیم نشده است")
    query = urlencode(
        {
            "calcDiscount": str(bool(calc_discount)).lower(),
            "calcSaleRestriction": str(bool(calc_sale_restriction)).lower(),
            "calcPaymentType": str(bool(calc_payment_type)).lower(),
            "SubSystemTypeUniqueId": subsystem_id,
        }
    )
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        token = _token(settings)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        owner_values = [value.strip() for value in settings.ngt_api_scope.split(",")]
        if len(owner_values) != 3 or any(not value for value in owner_values):
            raise PrevisitError("سه شناسه سازمانی API ورانگر کامل تنظیم نشده است")
        try:
            owner_values = [str(UUID(value)) for value in owner_values]
        except ValueError as exc:
            raise PrevisitError("شناسه‌های سازمانی API ورانگر معتبر نیستند") from exc
        headers.update(
            dict(zip(("OwnerKey", "DataOwnerKey", "DataOwnerCenterKey"), owner_values))
        )
        request = Request(
            f"{settings.ngt_api_base_url}/api/v2/ngt/evc/presale?{query}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            if str(response.headers.get("Content-Encoding") or "").casefold() == "gzip":
                raw = gzip.decompress(raw)
            result = json.loads(raw.decode("utf-8"))
            return result if isinstance(result, dict) else {"items": result}
    except HTTPError as exc:
        message = ""
        try:
            error = json.loads(exc.read().decode("utf-8"))
            message = str(error.get("message") or error.get("Message") or "")
        except (ValueError, UnicodeDecodeError):
            pass
        if exc.code in {401, 403} or (exc.code == 400 and not settings.ngt_api_username):
            raise PrevisitError("حساب سرویس API ورانگر برای محاسبه رسمی تنظیم نشده است") from exc
        raise PrevisitError(message or f"محاسبه رسمی NGT با خطای {exc.code} متوقف شد") from exc
    except (URLError, TimeoutError) as exc:
        raise PrevisitError("ارتباط با سرویس محاسبه تخفیف NGT برقرار نشد") from exc


def _lookup(mapping: dict[str, Any], *names: str, default: Any = None) -> Any:
    folded = {str(key).casefold(): value for key, value in mapping.items()}
    for name in names:
        if name.casefold() in folded:
            return folded[name.casefold()]
    return default


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _collect_lists(mapping: dict[str, Any], *names: str) -> list[Any]:
    folded = {str(key).casefold(): value for key, value in mapping.items()}
    values: list[Any] = []
    for name in names:
        values.extend(_as_list(folded.get(name.casefold())))
    return values


def _normalise_condition_value(value: Any) -> str:
    if value in (None, "", False):
        return ""
    try:
        numeric = float(value)
        return str(int(numeric)) if numeric.is_integer() else str(numeric)
    except (TypeError, ValueError):
        return str(value).strip().casefold()


def _promotion_customer_context(settings: Any, customer_id: int) -> dict[str, Any]:
    rows = _rows(
        settings,
        f"""
SELECT customer.BackOfficeId AS CustRef, customer.DCRef,
       category.BackOfficeId AS CustCtgrRef,
       activity.BackOfficeId AS CustActRef,
       level_type.BackOfficeId AS CustLevelRef,
       main_sub.MainTypeRef AS MainCustTypeRef,
       main_sub.SubTypeRef AS SubCustTypeRef,
       customer.StateId AS StateRef, customer.CountyId AS CountyRef,
       customer.CityAreaSDS AS AreaRef, customer.SaleZoneRefSDS AS SaleZoneRef
FROM NGT.Customers AS customer
LEFT JOIN NGT.CustomerCategories AS category ON category.Id=customer.CustomerCategoryUniqueId
LEFT JOIN NGT.CustomerActivities AS activity ON activity.Id=customer.CustomerActivityUniqueId
LEFT JOIN NGT.CustomerLevels AS level_type ON level_type.Id=customer.CustomerLevelUniqueId
LEFT JOIN NGT.CustomerMainSubTypes AS main_sub
  ON main_sub.CustRef=TRY_CONVERT(int, customer.BackOfficeId)
 AND ISNULL(main_sub.IsRemoved,0)=0
WHERE TRY_CONVERT(int, customer.BackOfficeId)={int(customer_id)}
""".strip(),
    )
    if not rows:
        return {"CustRef": int(customer_id)}
    # A customer can have more than one main/sub type. Keep every value so a
    # rule is not rejected merely because a different mapping was read first.
    context: dict[str, Any] = {}
    for field in rows[0]:
        values = {
            _normalise_condition_value(row.get(field))
            for row in rows
            if _normalise_condition_value(row.get(field))
        }
        context[field] = values
    return context


def _evaluate_promotion_conditions(
    condition_rows: list[dict[str, Any]],
    actual_context: dict[str, Any],
    condition_labels: dict[str, str],
) -> tuple[str, list[str]]:
    # NGT treats each tblDiscountCondition row as an alternative eligibility
    # path. Non-empty fields inside one row are conjunctive, but a match on any
    # complete row makes the rule eligible. Collapsing all rows by field would
    # incorrectly turn alternatives such as customer-category 4 OR order-type
    # 13 into customer-category 4 AND order-type 13.
    if not condition_rows:
        return "eligible", []

    mismatches: list[str] = []
    unknown_paths: list[str] = []
    has_effective_condition = False
    for condition in condition_rows:
        required_fields = [
            (field, _normalise_condition_value(condition.get(field)))
            for field in condition_labels
            if _normalise_condition_value(condition.get(field))
        ]
        if not required_fields:
            return "eligible", []
        has_effective_condition = True

        path_mismatches: list[str] = []
        path_unknowns: list[str] = []
        for field, required in required_fields:
            actual_raw = actual_context.get(field)
            if isinstance(actual_raw, set):
                actual = {_normalise_condition_value(value) for value in actual_raw}
            elif isinstance(actual_raw, (list, tuple)):
                actual = {_normalise_condition_value(value) for value in actual_raw}
            else:
                value = _normalise_condition_value(actual_raw)
                actual = {value} if value else set()
            if required in actual:
                continue

            label = condition_labels[field]
            if field == "OrderNo":
                path_mismatches.append(f"مخصوص سفارش {required}؛ سفارش فعلی جدید است")
            elif field == "OrderRef":
                path_mismatches.append(f"مخصوص شناسه سفارش {required}؛ سفارش فعلی جدید است")
            elif field == "CustGroupRef" and not actual:
                path_unknowns.append("گروه پویای مشتری در زمینه فعلی قابل احراز نیست")
            elif not actual:
                path_mismatches.append(f"{label} موردنیاز {required}؛ برای مشتری فعلی ثبت نشده")
            else:
                actual_text = " یا ".join(sorted(actual, key=lambda item: (len(item), item)))
                path_mismatches.append(f"{label} موردنیاز {required}؛ مقدار فعلی {actual_text}")

        if not path_mismatches and not path_unknowns:
            return "eligible", []
        mismatches.extend(path_mismatches)
        if not path_mismatches:
            unknown_paths.extend(path_unknowns)

    if not has_effective_condition:
        return "eligible", []
    if unknown_paths:
        return "unknown", list(dict.fromkeys(unknown_paths))
    return "ineligible", list(dict.fromkeys(mismatches))


def _candidate_promotion_rules(
    settings: Any,
    product_ids: list[int],
    *,
    customer_id: int | str | None = None,
    order_type_ref: int | None = None,
    payment_usance_ref: int | str | None = None,
    buy_type_ref: int | None = None,
    sale_office_ref: int | None = None,
) -> list[dict[str, Any]]:
    safe_product_ids = sorted({int(product_id) for product_id in product_ids if int(product_id) > 0})
    if not safe_product_ids:
        return []
    ids_sql = ",".join(str(product_id) for product_id in safe_product_ids)
    business_date = jalali_business_date()
    rule_sql = f"""
WITH relevant_rules AS (
  SELECT product.ID AS ProductId, discount.ID AS DiscountId,
         discount.Code, discount.DisGroup, discount.Priority, discount.PrizeType,
         discount.DisType, discount.DisAccRef,
         discount.StartDate, discount.EndDate, discount.MinQty, discount.MaxQty,
         discount.MinAmount, discount.MaxAmount, discount.PrizeQty, discount.PrizeRef,
         discount.PrizeStep, discount.PrizeUnit, discount.DisPerc, discount.DisPrice,
         discount.Comment, discount.IsSelfPrize, prize.GoodsName AS PrizeName,
         ROW_NUMBER() OVER (
           PARTITION BY product.ID, discount.DisGroup
           ORDER BY discount.StartDate DESC, discount.Priority DESC, discount.ID DESC
         ) AS RuleRank
  FROM GNR.tblGoods AS product
  INNER JOIN SLE.tblDiscount AS discount ON 1 = 1
  LEFT JOIN SLE.tblDiscountGoods AS discount_goods
    ON discount_goods.DiscountRef = discount.ID
   AND discount_goods.GoodsRef = product.ID
  LEFT JOIN GNR.tblGoods AS prize
    ON prize.ID = discount.PrizeRef
  WHERE product.ID IN ({ids_sql})
    AND ISNULL(discount.IsActive, 0) = 1
    AND discount.StartDate <= N'{business_date}'
    AND (NULLIF(discount.EndDate, '') IS NULL OR discount.EndDate >= N'{business_date}')
    AND (
      discount_goods.ID IS NOT NULL
      OR discount.GoodsRefOld = product.ID
      OR discount.GoodsGroupRef = product.GoodsGroupRef
      OR discount.ManufacturerRef = product.ManufacturerRef
      OR discount.BrandRef = product.BrandRef
      OR EXISTS (
        SELECT 1
        FROM GNR.tblGoodsMainSubType AS goods_type
        WHERE goods_type.GoodsRef = product.ID
          AND goods_type.MainTypeRef = discount.MainTypeRef
          AND (discount.SubTypeRef IS NULL OR goods_type.SubTypeRef = discount.SubTypeRef)
      )
    )
)
SELECT ProductId, DiscountId, Code, DisGroup, Priority, PrizeType, DisType, DisAccRef,
       StartDate, EndDate, MinQty, MaxQty, MinAmount, MaxAmount,
       PrizeQty, PrizeRef, PrizeStep, PrizeUnit, DisPerc, DisPrice,
       Comment, IsSelfPrize, PrizeName
FROM relevant_rules
WHERE RuleRank = 1
ORDER BY ProductId, Priority, Code
""".strip()
    rules = _rows(settings, rule_sql)
    if not rules:
        return []

    discount_ids = ",".join(str(int(row["DiscountId"])) for row in rules)
    condition_sql = f"""
SELECT DiscountRef, DCRef, CustCtgrRef, CustActRef, CustLevelRef,
       PayType, PaymentUsanceRef, OrderType, SaleOfficeRef, CustGroupRef,
       CustRef, OrderNo, StateRef, CountyRef, AreaRef, SaleZoneRef,
       MainCustTypeRef, SubCustTypeRef, OrderRef
FROM SLE.tblDiscountCondition
WHERE DiscountRef IN ({discount_ids})
""".strip()
    conditions_by_rule: dict[int, list[dict[str, Any]]] = {}
    condition_labels = {
        "DCRef": "انبار",
        "CustCtgrRef": "گروه مشتری",
        "CustActRef": "فعالیت مشتری",
        "CustLevelRef": "سطح مشتری",
        "PayType": "نوع پرداخت",
        "PaymentUsanceRef": "روش پرداخت",
        "OrderType": "نوع سفارش",
        "SaleOfficeRef": "دفتر فروش",
        "CustGroupRef": "گروه پویای مشتری",
        "CustRef": "مشتری",
        "OrderNo": "سفارش مرجع",
        "StateRef": "استان",
        "CountyRef": "شهرستان",
        "AreaRef": "منطقه",
        "SaleZoneRef": "منطقه فروش",
        "MainCustTypeRef": "نوع اصلی مشتری",
        "SubCustTypeRef": "نوع فرعی مشتری",
        "OrderRef": "شناسه سفارش",
    }
    for condition in _rows(settings, condition_sql):
        discount_id = int(condition["DiscountRef"])
        conditions_by_rule.setdefault(discount_id, []).append(condition)

    actual_context: dict[str, Any] = {}
    if customer_id is not None:
        actual_context.update(_promotion_customer_context(settings, int(customer_id)))
    actual_context.update(
        {
            "CustRef": customer_id,
            "PayType": buy_type_ref,
            "PaymentUsanceRef": payment_usance_ref,
            "OrderType": order_type_ref,
            "SaleOfficeRef": sale_office_ref,
            # Previewing creates a new order, so reference-specific rules are
            # definitely not eligible at this stage.
            "OrderNo": None,
            "OrderRef": None,
        }
    )

    result = []
    for row in rules:
        prize_qty = float(row.get("PrizeQty") or 0)
        prize_step = float(row.get("PrizeStep") or 0)
        discount_percent = float(row.get("DisPerc") or 0)
        discount_price = float(row.get("DisPrice") or 0)
        details = []
        if prize_qty and prize_step:
            details.append(f"خرید {prize_step:g}، جایزه {prize_qty:g}")
        if discount_percent:
            details.append(f"{discount_percent:g} درصد تخفیف")
        if discount_price:
            details.append(f"{discount_price:g} ریال تخفیف")
        if row.get("MinQty"):
            details.append(f"حداقل {float(row['MinQty']):g} عدد")
        if row.get("MinAmount"):
            details.append(f"حداقل مبلغ {float(row['MinAmount']):g} ریال")
        rule_conditions = conditions_by_rule.get(int(row["DiscountId"]), [])
        labels = sorted(
            {
                label
                for condition in rule_conditions
                for field, label in condition_labels.items()
                if condition.get(field) not in (None, "", 0, False)
            }
        )
        eligibility_status, eligibility_reasons = _evaluate_promotion_conditions(
            rule_conditions,
            actual_context,
            condition_labels,
        )
        result.append(
            {
                "product_id": str(row["ProductId"]),
                "rule_id": int(row["DiscountId"]),
                "rule_code": int(row["Code"]),
                "kind": "prize" if prize_qty or int(row.get("PrizeType") or 0) == 1 else "discount",
                "title": str(row.get("Comment") or "").strip() or f"قانون {row['Code']}",
                "details": " · ".join(details),
                "discount_account_ref": int(row.get("DisAccRef") or 0),
                "discount_category": {1: "cash", 2: "volume", 3: "goods"}.get(
                    int(row.get("DisAccRef") or 0), "other"
                ),
                "configured_discount_percent": discount_percent,
                "configured_discount_amount": discount_price,
                "prize_quantity": prize_qty,
                "prize_product_id": str(row.get("PrizeRef") or ""),
                "prize_product_name": str(row.get("PrizeName") or "").strip(),
                "prize_step": prize_step,
                "prize_unit": float(row.get("PrizeUnit") or 0),
                "is_self_prize": bool(row.get("IsSelfPrize")),
                "prize_type": int(row.get("PrizeType") or 0),
                "discount_type": int(row.get("DisType") or 0),
                "condition_summary": "، ".join(labels),
                "eligibility_status": eligibility_status,
                "eligible": eligibility_status == "eligible",
                "eligibility_reasons": eligibility_reasons,
                "start_date": str(row.get("StartDate") or ""),
                "end_date": str(row.get("EndDate") or ""),
                "applied": False,
                "source": "Varanegar active discount definition",
            }
        )
    return result


def _applied_rule_references(raw: Any) -> set[str]:
    references: set[str] = set()
    reference_fields = {"ruleno", "ruleid", "discountref", "disref"}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).casefold() in reference_fields and child not in (None, "", 0, False):
                    references.add(str(child))
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(raw)
    return references


def _normalise_prize_lines(prizes: list[Any]) -> list[dict[str, Any]]:
    """Expose official NGT prize rows as a stable display contract.

    NGT installations use a few names for the same fields. Only rows returned
    by the EVC service are normalised here; no client-side promotion is created.
    """
    normalised: list[dict[str, Any]] = []
    for prize in prizes:
        if not isinstance(prize, dict):
            continue
        product_id = str(
            _lookup(prize, "GoodsRef", "ProductRef", "PrizeRef", default="") or ""
        )
        quantity = _number(
            _lookup(prize, "TotalQty", "PrizeQty", "Quantity", "UnitQty", default=0)
        )
        if not product_id or quantity <= 0:
            continue
        unit_price = _number(
            _lookup(prize, "CustPrice", "UserPrice", "UnitPrice", "Price", default=0)
        )
        gross = _number(
            _lookup(prize, "GrossAmount", "Amount", default=quantity * unit_price)
        )
        discount = _number(
            _lookup(
                prize,
                "Discount",
                "DiscountAmount",
                "PrizeAmount",
                default=gross,
            )
        )
        normalised.append(
            {
                "product_id": product_id,
                "parent_product_id": str(
                    _lookup(
                        prize,
                        "BaseGoodsRef",
                        "SourceGoodsRef",
                        "OrderGoodsRef",
                        "ParentGoodsRef",
                        default="",
                    )
                    or ""
                ),
                "title": str(
                    _lookup(prize, "GoodsName", "ProductName", "PrizeName", default="")
                    or ""
                ).strip(),
                "quantity": quantity,
                "unit_price": round(unit_price, 2),
                "gross_amount": round(gross, 2),
                "discount_amount": round(discount, 2),
                "discount_percent": 100.0,
                "net_amount": 0.0,
                "source": "NGT official prize",
            }
        )
    return normalised


def _normalise_evc(raw: dict[str, Any], requested_lines: list[dict[str, Any]]) -> dict[str, Any]:
    envelope = _lookup(raw, "Data", "Result", default=raw)
    result = envelope if isinstance(envelope, dict) else raw
    items = _as_list(_lookup(result, "Items", "PreSaleEvcDetails", default=[]))
    normalised_items = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        fallback = requested_lines[index] if index < len(requested_lines) else {}
        quantity = float(_lookup(item, "TotalQty", "UnitQty", default=fallback.get("quantity", 0)) or 0)
        unit_price = float(_lookup(item, "CustPrice", "UserPrice", "UnitPrice", default=0) or 0)
        discount = float(_lookup(item, "Discount", "DiscountAmount", default=0) or 0)
        base_tax = float(_lookup(item, "Tax", default=0) or 0)
        charge = float(_lookup(item, "Charge", default=0) or 0)
        # Varanegar tax rule 5014 is returned as a positive invoice addition
        # (AddAmount/EvcItemAdd1), while the ordinary Tax field remains zero.
        # AddAmount is the aggregate of Add1/Add2/AddOther, so use it when
        # present and only fall back to the components to avoid double-counting.
        addition_components = sum(
            float(_lookup(item, field, default=0) or 0)
            for field in ("EvcItemAdd1", "EvcItemAdd2", "EvcItemAddOther")
        )
        additions = float(_lookup(item, "AddAmount", default=0) or addition_components)
        tax = base_tax + additions
        net = float(_lookup(item, "AmountNut", "NetAmount", default=(quantity * unit_price - discount + tax + charge)) or 0)
        gross = quantity * unit_price
        tax_and_charge = tax + charge
        discount_percent = round((discount / gross) * 100, 2) if gross else 0.0
        # The official NGT EVC response separates discount accounts on every
        # invoice line: account 1=cash, 2=volume, 3=goods.
        cash_discount = float(_lookup(item, "EvcItemDis1", "Dis1", default=0) or 0)
        volume_discount = float(_lookup(item, "EvcItemDis2", "Dis2", default=0) or 0)
        goods_discount = float(_lookup(item, "EvcItemDis3", "Dis3", default=0) or 0)
        other_discount = float(
            _lookup(item, "EvcItemOtherDiscount", "OtherDiscount", default=0) or 0
        )
        classified_discount = cash_discount + volume_discount + goods_discount + other_discount
        unclassified_discount = max(discount - classified_discount, 0.0)

        def discount_part(amount: float) -> dict[str, float]:
            return {
                "amount": round(amount, 2),
                "percent": round((amount / gross) * 100, 2) if gross else 0.0,
            }

        normalised_items.append(
            {
                "product_id": str(_lookup(item, "GoodsRef", default=fallback.get("product_id", "")) or ""),
                "quantity": quantity,
                "unit_price": unit_price,
                "discount_amount": discount,
                "discount_percent": discount_percent,
                "discount_breakdown": {
                    "cash": discount_part(cash_discount),
                    "volume": discount_part(volume_discount),
                    "goods": discount_part(goods_discount),
                    "other": discount_part(other_discount),
                    "unclassified": discount_part(unclassified_discount),
                },
                "gross_amount": round(gross, 2),
                "tax_amount": tax,
                "charge_amount": charge,
                "tax_and_charge_amount": round(tax_and_charge, 2),
                "net_amount": net,
                "rule_no": str(_lookup(item, "RuleNo", default="") or ""),
            }
        )
    prizes = _collect_lists(result, "OrderPrize", "DiscountEvcPrize", "SellPrize")
    return {
        "ok": not bool(_lookup(result, "ErrorCode", default=0)),
        "error_code": _lookup(result, "ErrorCode", default=0),
        "message": str(_lookup(result, "Message", default="") or ""),
        "evc_id": _lookup(result, "EvcId"),
        "items": normalised_items,
        "totals": {
            "gross": round(sum(item["quantity"] * item["unit_price"] for item in normalised_items), 2),
            "discount": round(sum(item["discount_amount"] for item in normalised_items), 2),
            "tax": round(sum(item["tax_amount"] for item in normalised_items), 2),
            "charge": round(sum(item["charge_amount"] for item in normalised_items), 2),
            "net": round(sum(item["net_amount"] for item in normalised_items), 2),
        },
        "prizes": prizes,
        "gift_lines": _normalise_prize_lines(prizes),
        "restrictions": _collect_lists(result, "ItemStatute", "ReturnDisItems"),
        "payment": {
            "id": _lookup(result, "PaymentUsanceId"),
            "name": str(_lookup(result, "PaymentUsanceName", default="") or ""),
            "cash_duration": _lookup(result, "CashDuration"),
            "check_duration": _lookup(result, "CheckDuration"),
        },
        "source": "NGT EVC presale",
        "creates_order": False,
    }


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _calculate_ngt_credit_control(
    customer: dict[str, Any],
    payment: dict[str, Any],
    *,
    order_total: float,
    pending_order_total: float = 0,
    order_asn_limit: int = 0,
    order_bed_limit: int = 0,
) -> dict[str, Any]:
    """Apply the same Bed/Asn branches used by NGT presale 5.9.

    NGT adds every current order for the customer before comparing it with the
    synced remaining balances.  ``pending_order_total`` represents current,
    not-yet-sent NGT orders; ``order_total`` is this draft's official EVC net.
    """
    init_credit = _number(customer.get("InitCredit"))
    remain_credit = _number(customer.get("RemainCredit"))
    init_debit = _number(customer.get("InitDebit"))
    remain_debit = _number(customer.get("RemainDebit"))
    check_credit = bool(payment.get("CheckCredit", payment.get("check_credit", False)))
    check_debit = bool(payment.get("CheckDebit", payment.get("check_debit", False)))
    asn_enabled = int(order_asn_limit or 0) != 0
    bed_enabled = int(order_bed_limit or 0) != 0
    current_amount = max(_number(order_total), 0.0)
    pending_amount = max(_number(pending_order_total), 0.0)
    evaluated_total = current_amount + pending_amount

    mode = "none"
    available_amount: float | None = None
    if (
        asn_enabled
        and bed_enabled
        and check_credit
        and check_debit
        and init_credit != 0
        and init_debit != 0
    ):
        mode = "combined"
        available_amount = remain_credit + remain_debit
    elif asn_enabled and check_credit and not check_debit and init_credit != 0:
        mode = "credit"
        available_amount = remain_credit
    elif bed_enabled and check_debit and not check_credit and init_debit != 0:
        mode = "debit"
        available_amount = remain_debit

    allowed = available_amount is None or evaluated_total <= available_amount
    deficit = max(evaluated_total - available_amount, 0.0) if available_amount is not None else 0.0
    mode_label = {
        "combined": "مجموع مانده اعتبار و بدهکاری",
        "credit": "مانده اعتبار مشتری",
        "debit": "مانده بدهکاری مشتری",
        "none": "بدون کنترل مانده برای این روش پرداخت",
    }[mode]
    if available_amount is None:
        message = "طبق تنظیمات NGT برای این روش پرداخت، کنترل مانده‌ای اعمال نمی‌شود."
    elif allowed:
        message = (
            f"کنترل اعتبار NGT تأیید شد؛ {mode_label} "
            f"{available_amount:,.0f} ریال و مبلغ کنترل‌شده {evaluated_total:,.0f} ریال است."
        )
    else:
        message = (
            f"ثبت سفارش مجاز نیست؛ مبلغ کنترل‌شده {evaluated_total:,.0f} ریال از "
            f"{mode_label} به مبلغ {available_amount:,.0f} ریال بیشتر است و "
            f"{deficit:,.0f} ریال کسری دارد."
        )

    return {
        "allowed": allowed,
        "blocking": not allowed,
        "mode": mode,
        "mode_label": mode_label,
        "message": message,
        "current_order_amount": round(current_amount, 2),
        "pending_ngt_order_amount": round(pending_amount, 2),
        "evaluated_total": round(evaluated_total, 2),
        "available_amount": round(available_amount, 2) if available_amount is not None else None,
        "deficit": round(deficit, 2),
        "payment_checks": {"credit": check_credit, "debit": check_debit},
        "settings": {
            "order_asn_limit": int(order_asn_limit or 0),
            "order_bed_limit": int(order_bed_limit or 0),
        },
        "balances": {
            "initial_credit": round(init_credit, 2),
            "remaining_credit": round(remain_credit, 2),
            "initial_debit": round(init_debit, 2),
            "remaining_debit": round(remain_debit, 2),
            "combined_remaining": round(remain_credit + remain_debit, 2),
        },
        "financials": {
            "customer_remaining": round(_number(customer.get("CustomerRemain")), 2),
            "open_invoice_count": int(_number(customer.get("OpenInvoiceCount"))),
            "open_invoice_amount": round(_number(customer.get("OpenInvoiceAmount")), 2),
            "open_cheque_count": int(_number(customer.get("OpenChequeCount"))),
            "open_cheque_amount": round(_number(customer.get("OpenChequeAmount")), 2),
            "returned_cheque_count": int(_number(customer.get("ReturnChequeCount"))),
            "returned_cheque_amount": round(_number(customer.get("ReturnChequeAmount")), 2),
        },
        "source": "NGT presale credit-control parity",
    }


def _live_customer_credit_control(
    settings: Any,
    *,
    customer_id: int | str,
    payment_id: int | str,
    dealer_ref: int,
    dc_ref: int,
    order_total: float,
) -> dict[str, Any]:
    try:
        safe_customer_id = int(customer_id)
        safe_payment_id = int(payment_id)
        safe_dealer_ref = int(dealer_ref)
        safe_dc_ref = int(dc_ref)
    except (TypeError, ValueError) as exc:
        raise PrevisitError("شناسه‌های لازم برای کنترل اعتبار NGT معتبر نیست") from exc

    rows = _rows(
        settings,
        f"""
WITH credit_config AS (
  SELECT
    COALESCE(
      (SELECT TOP 1 TRY_CONVERT(int, cfg.OrderAsnLimit)
       FROM GNR.tblServerConfigDC AS cfg WHERE cfg.DcRef = {safe_dc_ref}),
      (SELECT MAX(TRY_CONVERT(int, cfg.OrderAsnLimit)) FROM GNR.SdsNet_serverConfig AS cfg),
      0
    ) AS OrderAsnLimit,
    COALESCE(
      (SELECT TOP 1 TRY_CONVERT(int, cfg.OrderBedLimit)
       FROM GNR.tblServerConfigDC AS cfg WHERE cfg.DcRef = {safe_dc_ref}),
      (SELECT MAX(TRY_CONVERT(int, cfg.OrderBedLimit)) FROM GNR.SdsNet_serverConfig AS cfg),
      0
    ) AS OrderBedLimit
), pending_orders AS (
  SELECT ISNULL(SUM(
    CASE WHEN ISNULL(line.IsRequestFreeItem, 0) = 1 THEN 0 ELSE
      ISNULL(line.RequestAmount, 0)
      - ISNULL(line.RequestDis1Amount, 0)
      - ISNULL(line.RequestDis2Amount, 0)
      - ISNULL(line.RequestDis3Amount, 0)
      - ISNULL(line.RequestOtherDiscountAmount, 0)
      + ISNULL(line.RequestAdd1Amount, 0)
      + ISNULL(line.RequestAdd2Amount, 0)
      + ISNULL(line.RequestOtherAddAmount, 0)
      + ISNULL(line.RequestChargeAmount, 0)
      + ISNULL(line.RequestTaxAmount, 0)
    END
  ), 0) AS PendingOrderAmount
  FROM NGT.CustomerCallOrders AS order_header
  INNER JOIN NGT.CustomerCalls AS customer_call
    ON customer_call.Id = order_header.CustomerCallUniqueId
   AND ISNULL(customer_call.IsRemoved, 0) = 0
  INNER JOIN NGT.Customers AS pending_customer
    ON pending_customer.Id = customer_call.CustomerUniqueId
   AND ISNULL(pending_customer.IsRemoved, 0) = 0
  INNER JOIN NGT.CustomerCallOrderLines AS line
    ON line.CustomerCallOrderUniqueId = order_header.Id
   AND ISNULL(line.IsRemoved, 0) = 0
  WHERE TRY_CONVERT(int, pending_customer.BackOfficeId) = {safe_customer_id}
    AND TRY_CONVERT(int, order_header.DealerRefSDS) = {safe_dealer_ref}
    AND NULLIF(order_header.BackOfficeOrderId, N'') IS NULL
    AND order_header.SendToConsoleDate IS NULL
    AND ISNULL(order_header.IsCanceled, 0) = 0
    AND ISNULL(order_header.IsRemoved, 0) = 0
)
SELECT TOP 1 customer.InitCredit, customer.RemainCredit,
       customer.InitDebit, customer.RemainDebit, customer.CustomerRemain,
       customer.OpenInvoiceCount, customer.OpenInvoiceAmount,
       customer.OpenChequeCount, customer.OpenChequeAmount,
       customer.ReturnChequeCount, customer.ReturnChequeAmount,
       payment_order.CheckCredit, payment_order.CheckDebit,
       credit_config.OrderAsnLimit, credit_config.OrderBedLimit,
       pending_orders.PendingOrderAmount
FROM NGT.Customers AS customer
INNER JOIN NGT.PaymentTypeOrders AS payment_order
  ON TRY_CONVERT(int, payment_order.BackOfficeId) = {safe_payment_id}
 AND ISNULL(payment_order.IsRemoved, 0) = 0
CROSS JOIN credit_config
CROSS JOIN pending_orders
WHERE TRY_CONVERT(int, customer.BackOfficeId) = {safe_customer_id}
  AND ISNULL(customer.IsRemoved, 0) = 0
ORDER BY customer.LastUpdate DESC
""".strip(),
    )
    if not rows:
        raise PrevisitError("اطلاعات مانده اعتبار مشتری یا نوع پرداخت در NGT پیدا نشد")
    row = rows[0]
    return _calculate_ngt_credit_control(
        row,
        row,
        order_total=order_total,
        pending_order_total=_number(row.get("PendingOrderAmount")),
        order_asn_limit=int(row.get("OrderAsnLimit") or 0),
        order_bed_limit=int(row.get("OrderBedLimit") or 0),
    )


def _available_quantity_for_warehouse(product: dict[str, Any], warehouse_ref: int) -> float | None:
    inventory = product.get("warehouse_inventory") or {}
    if inventory and warehouse_ref:
        warehouse_stock = inventory.get(str(warehouse_ref))
        if warehouse_stock is None:
            return 0.0
        return max(0.0, float(warehouse_stock.get("available_qty") or 0))
    if warehouse_ref and product.get("stock_ref") and str(product.get("stock_ref")) != str(warehouse_ref):
        return 0.0
    if "available_qty" not in product:
        return None
    return max(0.0, float(product.get("available_qty") or 0))


def preview_previsit(
    settings: Any,
    username: str,
    payload: PrevisitPreviewRequest,
    *,
    include_submission_contract: bool = False,
) -> dict[str, Any]:
    context = previsit_context(
        settings,
        username,
        payload.route_id,
        payload.customer_id,
        # The browser catalogue is loaded with the service maximum (1000).
        # Revalidate against the same product set so a legitimate item after
        # row 500 is not rejected as outside the seller visit template.
        limit=1000,
    )
    order_types = {int(item["id"]): item for item in context["order_types"]}
    payments = {str(item["id"]): item for item in context["payment_types"]}
    products = {str(item["id"]): item for item in context["products"]}
    warehouses = {int(item["ref"]): item for item in context.get("warehouses") or []}
    if payload.order_type_ref not in order_types:
        raise PrevisitError("نوع سفارش برای تنظیمات اپ این فروشنده مجاز نیست")
    payment = payments.get(str(payload.payment_usance_ref))
    if not payment:
        raise PrevisitError("روش پرداخت برای این فروشنده مجاز نیست")
    warehouse_ref = int(
        payload.warehouse_ref
        or context.get("warehouse_selection", {}).get("default_ref")
        or 0
    )
    if warehouses and warehouse_ref not in warehouses:
        raise PrevisitError("انبار انتخاب‌شده در تنظیمات NGT این فروشنده مجاز نیست")
    selected_warehouse = warehouses.get(warehouse_ref)
    selected_dc_ref = int(
        (selected_warehouse or {}).get("dc_ref")
        or context["_bridge"]["dc_ref"]
    )
    requested = [line.model_dump() for line in payload.lines]
    unknown = [line["product_id"] for line in requested if str(line["product_id"]) not in products]
    if unknown:
        raise PrevisitError("یک یا چند کالا خارج از سبد کالای این فروشنده است")
    for line in requested:
        product = products[str(line["product_id"])]
        available = _available_quantity_for_warehouse(product, warehouse_ref)
        if available is not None and float(line["quantity"]) > available + 1e-9:
            product_name = str(product.get("name") or line["product_id"])
            available_text = f"{available:g}"
            raise PrevisitError(
                f"موجودی {product_name} در انبار انتخاب‌شده فقط {available_text} عدد است"
            )

    # The Android client serialises line dates using Locale.ENGLISH, producing
    # Gregorian yyyy/MM/dd. Its online header intentionally sends an empty date.
    line_order_date = date.today().strftime("%Y/%m/%d")
    order_unique_id = str(uuid4())
    evc_payload = {
        "CustRef": str(payload.customer_id),
        "OrderTypeRef": int(payload.order_type_ref),
        "SaleOfficeRef": int(context["_bridge"]["sale_office_ref"]),
        "OrderDate": "",
        "DealerRef": int(context["seller"]["personnel_id"]),
        "BuyTypeRef": int(payment["buy_type_ref"]),
        "DisType": 2,
        "PaymentUsanceRef": str(payload.payment_usance_ref),
        "EvcType": 1,
        "RefId": 0,
        "PreSaleEvcDetails": [
            {
                "GoodsRef": str(line["product_id"]),
                "FreeReasonRef": None,
                "TotalQty": float(line["quantity"]),
                "ReferenceNo": None,
                "SaleNo": None,
                "OrderDate": line_order_date,
                "ReturnReasonId": None,
                "OrderLineId": str(uuid4()),
                "OrderId": order_unique_id,
            }
            for line in requested
        ],
        "PreSaleEvcItemDetails": [],
        "SelIds": None,
    }
    raw = _post_evc(settings, evc_payload, context["_bridge"]["subsystem_type_unique_id"])
    result = _normalise_evc(raw, requested)
    related_rules = _candidate_promotion_rules(
        settings,
        [int(line["product_id"]) for line in requested],
        customer_id=payload.customer_id,
        order_type_ref=payload.order_type_ref,
        payment_usance_ref=payload.payment_usance_ref,
        buy_type_ref=int(payment["buy_type_ref"]),
        sale_office_ref=int(context["_bridge"]["sale_office_ref"]),
    )
    applied_references = _applied_rule_references(raw)
    official_gift_product_ids = {
        str(gift.get("product_id") or "") for gift in result.get("gift_lines", [])
    }
    for rule in related_rules:
        prize_matches = bool(
            rule.get("kind") == "prize"
            and str(rule.get("prize_product_id") or rule.get("product_id") or "")
            in official_gift_product_ids
        )
        rule["applied"] = bool(
            {str(rule["rule_id"]), str(rule["rule_code"])} & applied_references
            or prize_matches
        )
        if rule["applied"]:
            # The EVC response is authoritative. Never show a locally inferred
            # rejection beside a rule that NGT actually applied.
            rule["eligibility_status"] = "eligible"
            rule["eligible"] = True
            rule["eligibility_reasons"] = []
    requested_product_ids = [str(line["product_id"]) for line in requested]
    for gift in result.get("gift_lines", []):
        gift_product_id = str(gift.get("product_id") or "")
        matching_rules = [
            rule
            for rule in related_rules
            if rule.get("kind") == "prize"
            and (
                str(rule.get("prize_product_id") or "") == gift_product_id
                or (
                    rule.get("is_self_prize")
                    and str(rule.get("product_id") or "") == gift_product_id
                )
            )
        ]
        applied_rule = next((rule for rule in matching_rules if rule.get("applied")), None)
        selected_rule = applied_rule or (matching_rules[0] if matching_rules else None)
        if not gift.get("parent_product_id"):
            if selected_rule:
                gift["parent_product_id"] = str(selected_rule.get("product_id") or "")
            elif gift_product_id in requested_product_ids:
                gift["parent_product_id"] = gift_product_id
            elif len(requested_product_ids) == 1:
                gift["parent_product_id"] = requested_product_ids[0]
        product = products.get(gift_product_id) or {}
        if not gift.get("title"):
            gift["title"] = str(
                product.get("name")
                or (selected_rule or {}).get("prize_product_name")
                or f"کالای اشانتیون {gift_product_id}"
            )
        if not gift.get("unit_price"):
            matching_item = next(
                (
                    item
                    for item in result.get("items", [])
                    if str(item.get("product_id") or "") == gift_product_id
                ),
                None,
            )
            if matching_item:
                gift["unit_price"] = float(matching_item.get("unit_price") or 0)
                gift["gross_amount"] = round(
                    float(gift["quantity"]) * float(gift["unit_price"]), 2
                )
                gift["discount_amount"] = gift["gross_amount"]
    result["related_rules"] = related_rules
    result["order_type"] = order_types[payload.order_type_ref]
    result["payment_type"] = payment
    result["warehouse"] = selected_warehouse
    result["credit_control"] = _live_customer_credit_control(
        settings,
        customer_id=payload.customer_id,
        payment_id=payload.payment_usance_ref,
        dealer_ref=int(context["seller"]["personnel_id"]),
        dc_ref=selected_dc_ref,
        order_total=float(result["totals"]["net"]),
    )
    result["ok"] = bool(result["ok"] and result["credit_control"]["allowed"])
    try:
        from app.operational_notification_service import observe_credit_block, observe_official_quote
        observe_credit_block(
            settings, username, route_id=str(payload.route_id), customer_id=str(payload.customer_id),
            credit_control=result["credit_control"],
        )
        observe_official_quote(
            settings, username, route_id=str(payload.route_id), customer_id=str(payload.customer_id),
            order_type_ref=payload.order_type_ref, payment_usance_ref=payload.payment_usance_ref,
            warehouse_ref=warehouse_ref, requested_lines=requested, result=result,
        )
    except Exception:
        # Operational alerting is best-effort and must never block official NGT preview.
        pass
    if include_submission_contract:
        raw_envelope = _lookup(raw, "Data", "Result", default=raw)
        raw_result = raw_envelope if isinstance(raw_envelope, dict) else raw
        raw_items = _as_list(_lookup(raw_result, "Items", "PreSaleEvcDetails", default=[]))
        official_by_product: dict[str, list[dict[str, Any]]] = {}
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            product_key = str(_lookup(raw_item, "GoodsRef", default="") or "")
            official_by_product.setdefault(product_key, []).append(raw_item)
        contract_lines: list[dict[str, Any]] = []
        for index, requested_line in enumerate(requested):
            product_key = str(requested_line["product_id"])
            product = products[product_key]
            candidates = official_by_product.get(product_key, [])
            raw_item = candidates.pop(0) if candidates else (
                raw_items[index]
                if index < len(raw_items) and isinstance(raw_items[index], dict)
                else {}
            )
            normalised_item = result["items"][index] if index < len(result["items"]) else {}
            contract_lines.append(
                {
                    "product_ref": int(product_key),
                    "product_unique_id": str(product.get("unique_id") or ""),
                    "stock_ref": warehouse_ref or int(product.get("stock_ref") or 0),
                    "quantity": float(requested_line["quantity"]),
                    "unit_price": float(normalised_item.get("unit_price") or 0),
                    "cprice_ref": _lookup(
                        raw_item,
                        "CPriceRef",
                        "CpriceRef",
                        "CPriceUniqueId",
                        "CpriceUniqueId",
                    ),
                    "acc_year": int(_lookup(raw_item, "AccYear", default=0) or 0),
                    "unit_ref": int(_lookup(raw_item, "UnitRef", default=0) or 0),
                    "pay_duration": int(_lookup(raw_item, "PayDuration", default=0) or 0),
                    "pay_discount_ref": _lookup(raw_item, "PayDisRef", "PayDiscountRef"),
                }
            )
        result["_submission_contract"] = {
            "customer_ref": int(payload.customer_id),
            "dealer_ref": int(context["seller"]["personnel_id"]),
            "order_type_ref": int(payload.order_type_ref),
            "payment_usance_ref": int(payload.payment_usance_ref),
            "sale_office_ref": int(context["_bridge"]["sale_office_ref"]),
            "dc_ref": selected_dc_ref,
            "warehouse_ref": warehouse_ref,
            "route_id": str(payload.route_id),
            "lines": contract_lines,
            "has_prizes": bool(result.get("prizes")),
        }
    return result


def validate_order_draft(settings: Any, username: str, visit_id: str) -> dict[str, Any]:
    """Recalculate EVC and credit from server-owned draft data before closing it."""
    draft = get_visit_draft(settings, username, visit_id)
    if draft.get("visit_status") != "active":
        raise PrevisitError("این ویزیت قبلاً بسته شده است")
    if not draft.get("lines"):
        raise PrevisitError("ثبت سفارش حداقل به یک ردیف کالا نیاز دارد")
    context = previsit_context(
        settings,
        username,
        str(draft["route_id"]),
        str(draft["customer_id"]),
        limit=1000,
    )
    payment = next(
        (item for item in context["payment_types"] if item["name"] == draft.get("payment_type")),
        None,
    )
    order_type = next(
        (item for item in context["order_types"] if item["name"] == draft.get("order_type")),
        None,
    )
    if not payment:
        raise PrevisitError("روش پرداخت ذخیره‌شده دیگر در دسترسی NGT این فروشنده نیست")
    if not order_type:
        raise PrevisitError("نوع سفارش ذخیره‌شده دیگر در دسترسی NGT این فروشنده نیست")
    preview_payload = PrevisitPreviewRequest(
        route_id=str(draft["route_id"]),
        customer_id=str(draft["customer_id"]),
        order_type_ref=int(order_type["id"]),
        payment_usance_ref=str(payment["id"]),
        warehouse_ref=(
            int(draft["warehouse_ref"])
            if draft.get("warehouse_ref") is not None
            else None
        ),
        lines=[
            {"product_id": str(line["product_id"]), "quantity": float(line["quantity"])}
            for line in draft["lines"]
        ],
    )
    if settings.varanegar_order_bridge_enabled:
        preview = preview_previsit(
            settings,
            username,
            preview_payload,
            include_submission_contract=True,
        )
    else:
        preview = preview_previsit(settings, username, preview_payload)
    if not preview.get("credit_control", {}).get("allowed"):
        raise PrevisitError(
            str(preview.get("credit_control", {}).get("message") or "کنترل اعتبار NGT ثبت سفارش را رد کرد")
        )
    if not preview.get("ok"):
        raise PrevisitError(str(preview.get("message") or "محاسبه رسمی NGT ثبت سفارش را تأیید نکرد"))
    if settings.varanegar_order_bridge_enabled:
        preview["_draft"] = draft
    return preview
