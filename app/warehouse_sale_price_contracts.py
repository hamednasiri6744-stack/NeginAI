"""Dated assistant-side sale-price rules; ERP access is read-only."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
from uuid import uuid4

from app import warehouse_purchase_contracts as purchase


SalePriceError = purchase.ContractError


def connect(settings):
    return purchase.connect(settings)


def warehouse_options():
    from app.warehouse_assistant_service import WAREHOUSES
    return [
        {
            "code": code,
            "name": row["name"],
            "stock_id": row["stock_dc_ref"],
            "order_type_id": row["price_order_type_ref"],
            "order_type_name": row["price_order_type_name"],
        }
        for code, row in WAREHOUSES.items()
    ]


def initialize(settings):
    with connect(settings) as connection:
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS warehouse_sale_price_contracts (
          id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS warehouse_sale_price_contract_history (
          contract_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL,
          actor TEXT NOT NULL, saved_at TEXT NOT NULL,
          PRIMARY KEY(contract_id,revision));
        """)


def _contracts(connection):
    return [json.loads(row["payload"]) for row in connection.execute(
        "SELECT payload FROM warehouse_sale_price_contracts ORDER BY updated_at DESC,id"
    )]


def list_contracts(settings):
    initialize(settings)
    with connect(settings) as connection:
        return _contracts(connection)


def metadata(settings):
    catalog = purchase.catalog(settings)
    return {
        "manufacturers": catalog["manufacturers"],
        "catalog_updated_at": catalog["updated_at"],
        "today": catalog["today"],
        "warehouses": warehouse_options(),
    }


def _catalog_products(connection, manufacturer_id):
    products = {}
    for raw in connection.execute("SELECT payload FROM warehouse_purchase_catalog"):
        row = json.loads(raw[0])
        if row.get("manufacturer_id") != manufacturer_id:
            continue
        existing = products.get(row["product_code"])
        identity = (row.get("goods_id"), row.get("product_name"), row.get("brand_id"),
                    row.get("tax_rate"), row.get("tax_status"))
        if existing:
            previous = (existing.get("goods_id"), existing.get("product_name"), existing.get("brand_id"),
                        existing.get("tax_rate"), existing.get("tax_status"))
            if identity != previous:
                raise SalePriceError("مشخصات یک کالا بین طرف‌های خرید ناسازگار است؛ ابتدا فهرست را اصلاح کنید.")
        else:
            products[row["product_code"]] = row
    return {row["product_code"]: row for row in purchase.enrich_product_identities(connection, products.values())}


def selection(settings, manufacturer_id, brand_id=None, group_id=None):
    if type(manufacturer_id) is not int or manufacturer_id <= 0:
        raise SalePriceError("تولیدکننده معتبر نیست.")
    initialize(settings)
    with connect(settings) as connection:
        rows = list(_catalog_products(connection, manufacturer_id).values())
    if not rows:
        raise SalePriceError("برای این تولیدکننده کالایی در فهرست دستیار وجود ندارد.")
    brands = {row["brand_id"]: row["brand"] for row in rows if row.get("brand_id") is not None}
    if brand_id is not None:
        if type(brand_id) is not int or brand_id <= 0:
            raise SalePriceError("برند انتخاب‌شده معتبر نیست.")
        rows = [row for row in rows if row.get("brand_id") == brand_id]
    groups = {row["group_id"]: row["group_name"] for row in rows if row.get("group_id") is not None}
    if group_id is not None:
        if type(group_id) is not int or group_id <= 0:
            raise SalePriceError("گروه انتخاب‌شده معتبر نیست.")
        rows = [row for row in rows if row.get("group_id") == group_id]
    return {
        "items": sorted(rows, key=lambda row: row["product_code"]),
        "brands": [{"id": key, "name": value} for key, value in sorted(
            brands.items()
        )],
        "groups": [{"id": key, "name": value} for key, value in sorted(groups.items())],
    }


def _warehouse(code):
    return next((row for row in warehouse_options() if row["code"] == code), None)


def _validate(payload, connection, catalog_row=None):
    if not isinstance(payload, dict):
        raise SalePriceError("اطلاعات قرارداد قیمت فروش معتبر نیست.")
    warehouse = _warehouse(purchase.text(payload.get("warehouse_code")))
    if warehouse is None:
        raise SalePriceError("انبار و نوع درخواست مرتبط را انتخاب کنید.")
    try:
        manufacturer_id = int(payload.get("manufacturer_id", 0))
    except (TypeError, ValueError):
        raise SalePriceError("تولیدکننده معتبر نیست.") from None
    products = _catalog_products(connection, manufacturer_id)
    if not products:
        raise SalePriceError("تولیدکننده در فهرست کالاهای دستیار وجود ندارد.")
    scope = payload.get("scope")
    if scope not in ("manufacturer", "item"):
        raise SalePriceError("دامنهٔ قرارداد فروش باید تولیدکننده یا کالا باشد.")
    code = purchase.text(payload.get("product_code")) if scope == "item" else ""
    selected = catalog_row or products.get(code) if scope == "item" else next(iter(products.values()))
    if selected is None or (scope == "item" and code not in products):
        raise SalePriceError("کالای قرارداد متعلق به این تولیدکننده نیست.")
    title = purchase.text(payload.get("title"))
    note = purchase.text(payload.get("note"))
    if not title or len(title) > 160 or len(note) > 2000:
        raise SalePriceError("عنوان لازم است؛ عنوان حداکثر ۱۶۰ و توضیحات حداکثر ۲۰۰۰ حرف باشد.")
    start = purchase.clean_date(payload.get("start_date"))
    end = purchase.clean_date(payload.get("end_date"), True)
    if end and end < start:
        raise SalePriceError("پایان اعتبار نمی‌تواند قبل از شروع باشد.")
    status = payload.get("status")
    if status not in ("draft", "active"):
        raise SalePriceError("وضعیت قرارداد فروش معتبر نیست.")
    if type(payload.get("source_includes_tax")) is not bool:
        raise SalePriceError("وضعیت مالیات قیمت تولید مشخص نیست.")
    markup = purchase.number(payload.get("markup_percent"), "درصد افزایش قیمت فروش", 0, 100)
    return {
        "warehouse_code": warehouse["code"],
        "warehouse_name": warehouse["name"],
        "stock_id": warehouse["stock_id"],
        "order_type_id": warehouse["order_type_id"],
        "order_type_name": warehouse["order_type_name"],
        "manufacturer_id": manufacturer_id,
        "manufacturer": selected.get("manufacturer", ""),
        "scope": scope,
        "product_code": code,
        "product_name": selected.get("product_name", "") if scope == "item" else "",
        "brand_id": selected.get("brand_id") if scope == "item" else None,
        "brand": selected.get("brand", "") if scope == "item" else "",
        "title": title,
        "start_date": start,
        "end_date": end,
        "status": status,
        "basis": "manufacturer",
        "source_includes_tax": payload["source_includes_tax"],
        "markup_percent": str(markup),
        "note": note,
    }


def _write(connection, value, actor):
    now = datetime.now(timezone.utc).isoformat()
    encoded = json.dumps(value, ensure_ascii=False)
    connection.execute(
        "INSERT INTO warehouse_sale_price_contracts VALUES (?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET revision=excluded.revision,payload=excluded.payload,updated_at=excluded.updated_at",
        (value["id"], value["revision"], encoded, now, now),
    )
    connection.execute(
        "INSERT INTO warehouse_sale_price_contract_history VALUES (?,?,?,?,?)",
        (value["id"], value["revision"], encoded, actor[:100], now),
    )
    return value


def _overlaps(left, right):
    return left["start_date"] <= (right["end_date"] or "9999/12/31") and right["start_date"] <= (left["end_date"] or "9999/12/31")


def save_contract(settings, actor, payload, contract_id=None, expected_revision=None):
    initialize(settings)
    with connect(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        previous = None
        if contract_id:
            row = connection.execute("SELECT payload FROM warehouse_sale_price_contracts WHERE id=?", (contract_id,)).fetchone()
            if not row:
                raise SalePriceError("قرارداد قیمت فروش پیدا نشد.")
            previous = json.loads(row[0])
            if expected_revision != previous["revision"]:
                raise SalePriceError("قرارداد هم‌زمان تغییر کرده است؛ دوباره بازخوانی کنید.")
            if previous["status"] == "archived":
                raise SalePriceError("قرارداد بایگانی‌شده قابل ویرایش نیست؛ نسخهٔ جدید بسازید.")
        value = _validate(payload, connection)
        for other in _contracts(connection):
            if other["id"] == contract_id or other["status"] != "active" or value["status"] != "active":
                continue
            same = all(other.get(key) == value.get(key) for key in (
                "warehouse_code", "manufacturer_id", "scope", "product_code"
            ))
            if same and _overlaps(value, other):
                raise SalePriceError("تاریخ این قرارداد با قرارداد فعال دیگری در همین دامنه و انبار هم‌پوشانی دارد.")
        value.update(id=contract_id or str(uuid4()), revision=previous["revision"] + 1 if previous else 1)
        return _write(connection, value, actor)


def save_batch(settings, actor, payload):
    """Freeze the reviewed filtered product list into independent item rules."""
    codes = payload.get("product_codes")
    if not isinstance(codes, list) or not 1 <= len(codes) <= 10000 or any(not isinstance(code, str) for code in codes):
        raise SalePriceError("حداقل یک کالا از فهرست انتخاب کنید.")
    codes = [purchase.text(code) for code in codes]
    if len(codes) != len(set(codes)):
        raise SalePriceError("کالای تکراری انتخاب شده است.")
    try:
        manufacturer_id = int(payload.get("manufacturer_id", 0))
    except (TypeError, ValueError):
        raise SalePriceError("تولیدکننده معتبر نیست.") from None
    for key in ("filter_brand_id", "filter_group_id"):
        if payload.get(key) is not None and (type(payload[key]) is not int or payload[key] <= 0):
            raise SalePriceError("فیلتر انتخاب کالا معتبر نیست.")
    initialize(settings)
    result = []
    batch_id = str(uuid4())
    with connect(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        all_products = _catalog_products(connection, manufacturer_id)
        eligible = {code: row for code, row in all_products.items()
                    if (payload.get("filter_brand_id") is None or row.get("brand_id") == payload["filter_brand_id"])
                    and (payload.get("filter_group_id") is None or row.get("group_id") == payload["filter_group_id"])}
        if any(code not in eligible for code in codes):
            raise SalePriceError("یک یا چند کالا خارج از تولیدکننده، برند یا گروه انتخاب‌شده است؛ فهرست را بازخوانی کنید.")
        existing = _contracts(connection)
        for code in codes:
            value = _validate(dict(payload, scope="item", product_code=code), connection, eligible[code])
            if value["status"] == "active" and any(
                row["status"] == "active" and row["warehouse_code"] == value["warehouse_code"]
                and row["manufacturer_id"] == manufacturer_id and row["scope"] == "item"
                and row["product_code"] == code and _overlaps(value, row) for row in existing
            ):
                raise SalePriceError(f"کالای {code} در این انبار و تاریخ قاعدهٔ فعال دارد؛ هیچ قاعدهٔ جدیدی ذخیره نشد.")
            value.update(id=str(uuid4()), revision=1, batch_id=batch_id,
                         selection={"manufacturer_id": manufacturer_id,
                                    "brand_id": payload.get("filter_brand_id"),
                                    "group_id": payload.get("filter_group_id")})
            result.append(value)
        for value in result:
            _write(connection, value, actor)
    return {"contracts": result, "count": len(result), "batch_id": batch_id}


def archive(settings, actor, contract_id, revision, confirmed):
    if confirmed is not True:
        raise SalePriceError("بایگانی قرارداد قیمت فروش باید تأیید شود.")
    initialize(settings)
    with connect(settings) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT payload FROM warehouse_sale_price_contracts WHERE id=?", (contract_id,)).fetchone()
        if not row:
            raise SalePriceError("قرارداد قیمت فروش پیدا نشد.")
        previous = json.loads(row[0])
        if previous["revision"] != revision:
            raise SalePriceError("قرارداد هم‌زمان تغییر کرده است؛ دوباره بازخوانی کنید.")
        if previous["status"] == "archived":
            raise SalePriceError("قرارداد قبلاً بایگانی شده است.")
        return _write(connection, dict(previous, status="archived", revision=revision + 1), actor)


def history(settings, contract_id):
    initialize(settings)
    with connect(settings) as connection:
        return [
            {"contract": json.loads(row["payload"]), "actor": row["actor"], "saved_at": row["saved_at"]}
            for row in connection.execute(
                "SELECT * FROM warehouse_sale_price_contract_history WHERE contract_id=? ORDER BY revision DESC",
                (contract_id,),
            )
        ]


def _applicable(item, rules):
    candidates = [rule for rule in rules if rule["manufacturer_id"] == item.get("manufacturer_id") and (
        rule["scope"] == "manufacturer" or (rule["scope"] == "item" and rule["product_code"] == item["product_code"])
    )]
    candidates.sort(key=lambda rule: rule["scope"] == "item", reverse=True)
    return candidates[0] if candidates else None


def resolve_products(settings, manufacturer_id, warehouse_code, on_date):
    on_date = purchase.clean_date(on_date)
    warehouse = _warehouse(warehouse_code)
    if warehouse is None:
        raise SalePriceError("انبار و نوع درخواست مرتبط معتبر نیست.")
    initialize(settings)
    with connect(settings) as connection:
        products = list(_catalog_products(connection, manufacturer_id).values())
        rules = [rule for rule in _contracts(connection) if rule["warehouse_code"] == warehouse_code
                 and rule["status"] == "active" and rule["start_date"] <= on_date
                 and (not rule["end_date"] or on_date <= rule["end_date"])]
    for item in products:
        item["contract"] = _applicable(item, rules)
    return {"items": sorted(products, key=lambda row: row["product_code"]), "warehouse": warehouse,
            "on_date": on_date, "erp_write": False}


def calculate(rule, manufacturer_price, tax_rate):
    price = purchase.number(manufacturer_price, "قیمت تولید", 0, 1e15)
    if price <= 0:
        raise SalePriceError("قیمت تولید باید بزرگ‌تر از صفر باشد.")
    tax = purchase.number(tax_rate, "نرخ مالیات", 0, 100)
    net_source = price / (Decimal(1) + tax / 100) if rule["source_includes_tax"] else price
    net_source = net_source.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    markup_amount = (net_source * purchase.number(rule["markup_percent"], "درصد افزایش قیمت فروش") / 100).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    sale_price = net_source + markup_amount
    sale_tax = (sale_price * tax / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return {
        "manufacturer_price": str(price),
        "net_manufacturer_price": str(net_source),
        "markup_percent": str(purchase.number(rule["markup_percent"], "درصد افزایش قیمت فروش")),
        "markup_amount": str(markup_amount),
        "sale_price": str(sale_price),
        "tax": str(sale_tax),
        "sale_price_with_tax": str(sale_price + sale_tax),
    }
