from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from app.config import get_settings
from app.database import sql_connection
from app.models import PrevisitPreviewRequest
from app.ngt_previsit_service import PrevisitError, _post_evc, _token, preview_previsit
from app.seller_workspace_service import seller_route_customers


USERNAME = "A.kamran"
SELLER_REF = 22
CUSTOMER_REF = 7494
PRODUCT_REF = 4014
QUANTITY = 12.0
ORDER_TYPE_REF = 2
PAYMENT_REF = "401"
ROUTE_ID = "47645b16-1126-4ab3-9d54-03ac2abfd686"
STOCK_REF = 1
MARKER = "NEGINAI-PILOT-AR22-C7494-20260822-A"
LOCAL_PAPER_NO = "NAI22082601"
STATE_PATH = Path("data") / "pilot_order_state" / f"{MARKER}.json"
VISIT_STATUS_UNIQUE_ID = "87448538-def7-475a-9ad0-aa881ba97f95"
UTC_PLUS_0330 = timezone(timedelta(hours=3, minutes=30))


class PilotSafetyError(RuntimeError):
    pass


class PilotRejectedError(PilotSafetyError):
    pass


def _rows(settings: Any, sql: str) -> list[dict[str, Any]]:
    with sql_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        names = [str(item[0]) for item in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]


def _json_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_state(value: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(temporary, STATE_PATH)


def _read_state() -> dict[str, Any] | None:
    if not STATE_PATH.exists():
        return None
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _external_matches(settings: Any) -> list[dict[str, Any]]:
    marker = MARKER.replace("'", "''")
    local_paper = LOCAL_PAPER_NO.replace("'", "''")
    return _rows(
        settings,
        f"""
SELECT header.Id AS NgtOrderId, header.LocalPaperNo, header.Comment,
       header.BackOfficeOrderId, header.BackOfficeOrderNo,
       header.SendToConsoleDate, header.IsCanceled, header.LastUpdate,
       customer.BackOfficeId AS CustomerRef, header.DealerRefSDS,
       line.ProductUniqueId, line.RequestAmount
FROM NGT.CustomerCallOrders AS header
INNER JOIN NGT.CustomerCalls AS call ON call.Id = header.CustomerCallUniqueId
INNER JOIN NGT.Customers AS customer ON customer.Id = call.CustomerUniqueId
LEFT JOIN NGT.CustomerCallOrderLines AS line
  ON line.CustomerCallOrderUniqueId = header.Id AND ISNULL(line.IsRemoved, 0) = 0
WHERE (header.Comment = N'{marker}' OR header.LocalPaperNo = N'{local_paper}' OR call.Description = N'{marker}')
  AND ISNULL(header.IsRemoved, 0) = 0
ORDER BY header.LastUpdate DESC
""".strip(),
    )


def _identifier_context(settings: Any) -> dict[str, Any]:
    rows = _rows(
        settings,
        f"""
SELECT TOP 1 personnel.Id AS DealerUniqueId,
       customer.Id AS CustomerUniqueId,
       product.UniqueId AS ProductUniqueId,
       unit.UniqueId AS ProductUnitUniqueId,
       order_type.Id AS OrderTypeUniqueId,
       payment.Id AS PaymentTypeUniqueId,
       stock.Id AS StockUniqueId,
       device.DeviceSettingNo, device.SubSystemTypeUniqueId,
       COALESCE(recent_order.SaleOfficeRefSDS, 1) AS SaleOfficeRef,
       COALESCE(recent_order.DcRefSDS, 1) AS DcRef
FROM NGT.Personnels AS personnel
INNER JOIN NGT.Customers AS customer ON TRY_CONVERT(int, customer.BackOfficeId) = {CUSTOMER_REF}
INNER JOIN GNR.tblGoods AS product ON product.ID = {PRODUCT_REF}
INNER JOIN GNR.tblUnit AS unit ON unit.ID = product.UnitRef
INNER JOIN NGT.OrderTypes AS order_type ON TRY_CONVERT(int, order_type.BackOfficeId) = {ORDER_TYPE_REF}
INNER JOIN NGT.PaymentTypeOrders AS payment ON TRY_CONVERT(int, payment.BackOfficeId) = {PAYMENT_REF}
INNER JOIN NGT.Stocks AS stock ON TRY_CONVERT(int, stock.BackOfficeId) = {STOCK_REF}
INNER JOIN NGT.Users AS app_user ON app_user.BackOfficePersonnelId = {SELLER_REF} AND ISNULL(app_user.IsRemoved, 0) = 0
INNER JOIN NGT.DeviceUsers AS device_user ON device_user.UserUniqueId = app_user.Id AND ISNULL(device_user.IsRemoved, 0) = 0
INNER JOIN NGT.DeviceSettings AS device ON device.Id = device_user.DeviceSettingUniqueId AND ISNULL(device.IsRemoved, 0) = 0
OUTER APPLY (
  SELECT TOP 1 header.SaleOfficeRefSDS, header.DcRefSDS
  FROM NGT.CustomerCallOrders AS header
  WHERE TRY_CONVERT(int, header.DealerRefSDS) = {SELLER_REF}
    AND ISNULL(header.IsRemoved, 0) = 0
  ORDER BY header.LastUpdate DESC
) AS recent_order
WHERE TRY_CONVERT(int, personnel.BackOfficeId) = {SELLER_REF}
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(customer.IsRemoved, 0) = 0
ORDER BY device.LastUpdate DESC
""".strip(),
    )
    if len(rows) != 1:
        raise PilotSafetyError("شناسه‌های یکتای NGT برای پایلوت کامل نیستند")
    result = rows[0]
    for key in (
        "DealerUniqueId", "CustomerUniqueId", "ProductUniqueId", "ProductUnitUniqueId",
        "OrderTypeUniqueId", "PaymentTypeUniqueId", "StockUniqueId", "SubSystemTypeUniqueId",
    ):
        result[key] = str(UUID(str(result[key])))
    return result


def _minimum_order_amount(settings: Any, dc_ref: int) -> float:
    rows = _rows(
        settings,
        f"""
SELECT TOP 1 TRY_CONVERT(decimal(18, 2), MinOrderAmount) AS MinOrderAmount
FROM GNR.tblServerConfigDC
WHERE DcRef = {int(dc_ref)}
""".strip(),
    )
    if not rows or rows[0].get("MinOrderAmount") is None:
        rows = _rows(
            settings,
            "SELECT MAX(TRY_CONVERT(decimal(18, 2), MinOrderAmount)) AS MinOrderAmount FROM GNR.SdsNet_serverConfig",
        )
    if not rows or rows[0].get("MinOrderAmount") is None:
        raise PilotSafetyError("حداقل مبلغ سفارش از تنظیمات ورانگر خوانده نشد")
    return float(rows[0]["MinOrderAmount"])


def _cprice_unique_id(settings: Any, cprice_ref: Any) -> str | None:
    if cprice_ref is None:
        return None
    rows = _rows(
        settings,
        f"SELECT TOP 1 UniqueId FROM SLE.tblCPrice WHERE ID = {int(cprice_ref)}",
    )
    return str(UUID(str(rows[0]["UniqueId"]))) if rows and rows[0].get("UniqueId") else None


def _prepare(settings: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    matches = _external_matches(settings)
    if matches:
        raise PilotSafetyError(f"این پایلوت قبلاً در NGT دیده می‌شود: {matches[0]}")

    route = seller_route_customers(settings, USERNAME, ROUTE_ID)
    customer = next((item for item in route["customers"] if str(item["id"]) == str(CUSTOMER_REF)), None)
    if not customer:
        raise PilotSafetyError("مشتری دیگر در مسیر مجاز عارف کامران نیست")

    identifiers = _identifier_context(settings)
    preview = preview_previsit(
        settings,
        USERNAME,
        PrevisitPreviewRequest(
            route_id=ROUTE_ID,
            customer_id=str(CUSTOMER_REF),
            order_type_ref=ORDER_TYPE_REF,
            payment_usance_ref=PAYMENT_REF,
            lines=[{"product_id": str(PRODUCT_REF), "quantity": QUANTITY}],
        ),
    )
    if not preview.get("ok"):
        raise PilotSafetyError(str(preview.get("message") or "پیش‌نمایش رسمی NGT سفارش را رد کرد"))
    if not preview.get("credit_control", {}).get("allowed"):
        raise PilotSafetyError(str(preview["credit_control"].get("message") or "کنترل اعتبار رد شد"))
    totals = preview.get("totals") or {}
    minimum_amount = _minimum_order_amount(settings, int(identifiers["DcRef"]))
    if float(totals.get("net") or 0) < minimum_amount:
        raise PilotSafetyError(
            f"مبلغ خالص {float(totals.get('net') or 0):,.0f} از حداقل {minimum_amount:,.0f} کمتر است"
        )

    product_context = next(
        (item for item in preview_previsit_context(settings) if str(item["id"]) == str(PRODUCT_REF)),
        None,
    )
    if not product_context or float(product_context.get("available_qty") or 0) < QUANTITY:
        raise PilotSafetyError("موجودی انبار مجاز برای ۱۲ عدد کافی نیست")
    if int(float(product_context.get("stock_ref") or 0)) != STOCK_REF:
        raise PilotSafetyError("انبار کالای مجاز با انبار پایلوت یکسان نیست")

    order_id = str(uuid4())
    line_id = str(uuid4())
    qty_id = str(uuid4())
    call_id = str(uuid4())
    now = datetime.now(UTC_PLUS_0330).replace(microsecond=0)
    raw = _post_evc(
        settings,
        {
            "CustRef": str(CUSTOMER_REF), "OrderTypeRef": ORDER_TYPE_REF,
            "SaleOfficeRef": int(identifiers["SaleOfficeRef"]), "OrderDate": "",
            "DealerRef": SELLER_REF, "BuyTypeRef": 3, "DisType": 2,
            "PaymentUsanceRef": PAYMENT_REF, "EvcType": 1, "RefId": 0,
            "PreSaleEvcDetails": [{
                "GoodsRef": str(PRODUCT_REF), "FreeReasonRef": None, "TotalQty": QUANTITY,
                "ReferenceNo": None, "SaleNo": None, "OrderDate": now.strftime("%Y/%m/%d"),
                "ReturnReasonId": None, "OrderLineId": line_id, "OrderId": order_id,
            }],
            "PreSaleEvcItemDetails": [], "SelIds": None,
        },
        identifiers["SubSystemTypeUniqueId"],
    )
    items = raw.get("items") or raw.get("Items") or []
    if len(items) != 1:
        raise PilotSafetyError("پاسخ رسمی EVC دقیقاً یک ردیف کالا ندارد")
    item = items[0]
    if int(item.get("goodsRef") or item.get("GoodsRef") or 0) != PRODUCT_REF:
        raise PilotSafetyError("کالای پاسخ EVC با کالای پایلوت یکسان نیست")
    if float(item.get("amountNut") or item.get("AmountNut") or 0) != float(totals["net"]):
        raise PilotSafetyError("مبلغ EVC نهایی با پیش‌نمایش کنترل‌شده یکسان نیست")
    cprice_unique_id = _cprice_unique_id(settings, item.get("cPriceRef") or item.get("CPriceRef"))
    statutes = raw.get("itemStatute") or raw.get("ItemStatute") or []
    promotions = [
        {
            "UniqueId": str(uuid4()),
            "CustomerCallOrderLineUniqueId": line_id,
            "DiscountRef": str(entry.get("disRef") or entry.get("DisRef") or ""),
            "DiscountAmount": float(entry.get("discount") or entry.get("Discount") or 0),
            "AddAmount": float(entry.get("addAmount") or entry.get("AddAmount") or 0),
            "SupAmount": float(entry.get("supAmount") or entry.get("SupAmount") or 0),
        }
        for entry in statutes
    ]
    line = {
        "UniqueId": line_id,
        "CustomerCallOrderUniqueId": order_id,
        "ProductUniqueId": identifiers["ProductUniqueId"],
        "UnitPrice": float(item.get("custPrice") or item.get("CustPrice") or 0),
        "IsRequestPrizeItem": False,
        "CPriceUniqueId": cprice_unique_id,
        "PriceUniqueId": "00000000-0000-0000-0000-000000000000",
        "Comment": MARKER,
        "Description": "NeginAI controlled pilot",
        "EditReasonUniqueId": None,
        "FreeReasonUniqueId": None,
        "StockUniqueId": identifiers["StockUniqueId"],
        "SortId": 1,
        "RequestAmount": float(item.get("amount") or item.get("Amount") or 0),
        "RequestAdd1Amount": float(item.get("evcItemAdd1") or item.get("EvcItemAdd1") or 0),
        "RequestAdd2Amount": float(item.get("evcItemAdd2") or item.get("EvcItemAdd2") or 0),
        "RequestTaxAmount": float(item.get("tax") or item.get("Tax") or 0),
        "RequestChargeAmount": float(item.get("charge") or item.get("Charge") or 0),
        "RequestDis1Amount": float(item.get("evcItemDis1") or item.get("EvcItemDis1") or 0),
        "RequestDis2Amount": float(item.get("evcItemDis2") or item.get("EvcItemDis2") or 0),
        "RequestDis3Amount": float(item.get("evcItemDis3") or item.get("EvcItemDis3") or 0),
        "RequestOtherDiscountAmount": float(item.get("evcItemDisOther") or item.get("EvcItemDisOther") or 0),
        "RequestOtherAddAmount": float(item.get("evcItemAddOther") or item.get("EvcItemAddOther") or 0),
        "InvoiceAmount": 0, "InvoiceAdd1Amount": 0, "InvoiceAdd2Amount": 0,
        "InvoiceTaxAmount": 0, "InvoiceChargeAmount": 0,
        "InvoiceOtherDiscountAmount": 0, "InvoiceOtherAddAmount": 0,
        "InvoiceDis1Amount": 0, "InvoiceDis2Amount": 0, "InvoiceDis3Amount": 0,
        "PayDuration": int(item.get("payDuration") or item.get("PayDuration") or 0),
        "RuleNo": int(item.get("ruleNo") or item.get("RuleNo") or 0),
        "CustomerCallOrderLineOrderQtyDetails": [{
            "UniqueId": qty_id,
            "CustomerCallOrderLineUniqueId": line_id,
            "ProductUnitUniqueId": identifiers["ProductUnitUniqueId"],
            "Qty": QUANTITY,
        }],
        "CustomerCallOrderLineInvoiceQtyDetails": [],
        "CustomerCallOrderLinePromotions": promotions,
        "CustomerCallOrderLineBatchQtyDetails": [],
        "CustomerCallInvoiceLineBatchQtyDetails": [],
        "IsRequestFreeItem": False,
        "IsRecommended": False,
        "RowNo": 1,
    }
    order = {
        "UniqueId": order_id,
        "CustomerCallUniqueId": call_id,
        "SubSystemTypeUniqueId": identifiers["SubSystemTypeUniqueId"],
        "DistributionDeliveryStatusUniqueId": None,
        "ReturnReasonUniqueId": None,
        "UndeliveredReasonUniqueId": None,
        "OrderTypeUniqueId": identifiers["OrderTypeUniqueId"],
        "OrderPaymentTypeUniqueId": identifiers["PaymentTypeUniqueId"],
        "Comment": MARKER,
        "LocalPaperNo": LOCAL_PAPER_NO,
        "OrderRoundAmount": float(item.get("amount") or 0),
        "OrderOtherRoundDiscount": float(item.get("evcItemDisOther") or 0),
        "OrderRoundDis1": float(item.get("evcItemDis1") or 0),
        "OrderRoundDis2": float(item.get("evcItemDis2") or 0),
        "OrderRoundDis3": float(item.get("evcItemDis3") or 0),
        "OrderRoundTax": float(item.get("tax") or 0),
        "OrderRoundCharge": float(item.get("charge") or 0),
        "OrderRoundAdd1": float(item.get("evcItemAdd1") or 0),
        "OrderRoundAdd2": float(item.get("evcItemAdd2") or 0),
        "CallDate": now.isoformat(),
        "DeliveryDate": None,
        "PriceClassUniqueId": None,
        "InvoicePaymentTypeUniqueId": None,
        "InvoiceStartTime": None, "InvoiceEndTime": None, "PrintCount": 0,
        "OrderLines": [line], "OrderPrizes": [], "SellPrizes": [], "PromotionsPreview": [],
        "DistBackOfficeId": None,
        "DisType": 2,
        "SaleDate": now.isoformat(),
        "SaleTypeUniqueId": None,
        "BackOfficeOrderId": None,
        "BackOfficeOrderTypeId": None,
        "SellTypeStatusTypeUniqueId": None,
        "StockId": identifiers["StockUniqueId"],
    }
    payload = {
        "TourUniqueId": "00000000-0000-0000-0000-000000000000",
        "DealerId": identifiers["DealerUniqueId"],
        "ApkVersion": "5.9.0.0.27",
        "SendDate": now.isoformat(),
        "CustomerCalls": [{
            "CustomerCallUniqueId": call_id,
            "CustomerUniqueId": identifiers["CustomerUniqueId"],
            "VisitStatusUniqueId": VISIT_STATUS_UNIQUE_ID,
            "NoSaleReasonUniqueId": None,
            "VisitTemplatePathUniqueId": ROUTE_ID,
            "Description": MARKER,
            "CallDate": now.isoformat(),
            "StartTime": (now - timedelta(minutes=2)).isoformat(),
            "EndTime": now.isoformat(),
            "ManualStartTime": None, "ManualEndTime": None, "ManualVisitDuration": None,
            "Longitude": 0, "Latitude": 0, "VisitDuration": 120,
            "IsNewCustomer": False, "HasLicense": None, "RoleCode": None,
            "CustomerCallOrders": [order],
            "CustomerCallCatalogs": [], "CustomerCallReturns": [], "CustomerCallPayments": [],
            "CustomerCallQuestionnaires": [], "CustomerCallPictures": [], "CustomerCallStockLevels": [],
            "SyncCustomer": None,
        }],
        "CancelInvoices": [], "CustomerUpdates": [], "CustomerLocations": [],
        "RequestItemLines": [], "SaleForecastLines": [],
    }
    summary = {
        "marker": MARKER,
        "seller": {"ref": SELLER_REF, "name": "عارف کامران"},
        "customer": {"ref": CUSTOMER_REF, "code": customer["code"], "name": customer["name"], "store": customer["store_name"]},
        "route": {"id": ROUTE_ID, "title": route["route"]["title"]},
        "product": {"ref": PRODUCT_REF, "code": product_context["code"], "name": product_context["name"], "quantity": QUANTITY},
        "stock": {"ref": STOCK_REF, "name": product_context["stock_name"], "available_qty": product_context["available_qty"]},
        "order_type_ref": ORDER_TYPE_REF,
        "payment_ref": PAYMENT_REF,
        "minimum_order_amount": minimum_amount,
        "totals": totals,
        "credit_control": preview["credit_control"],
        "device_setting_code": int(identifiers["DeviceSettingNo"]),
        "payload_hash": _json_hash(payload),
    }
    return payload, summary


def preview_previsit_context(settings: Any) -> list[dict[str, Any]]:
    from app.ngt_previsit_service import previsit_context

    return previsit_context(settings, USERNAME, ROUTE_ID, str(CUSTOMER_REF), limit=1000)["products"]


def _api_headers(settings: Any) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    token = _token(settings)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    owners = [item.strip() for item in settings.ngt_api_scope.split(",")]
    if len(owners) != 3:
        raise PilotSafetyError("شناسه‌های سازمانی API کامل نیستند")
    owners = [str(UUID(item)) for item in owners]
    headers.update(dict(zip(("OwnerKey", "DataOwnerKey", "DataOwnerCenterKey"), owners)))
    return headers


def _official_price_preflight(settings: Any, payload: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    call = payload["CustomerCalls"][0]
    order = call["CustomerCallOrders"][0]
    line = order["OrderLines"][0]
    qty = line["CustomerCallOrderLineOrderQtyDetails"][0]["Qty"]
    body = {
        "CustomerUniqueId": call["CustomerUniqueId"],
        "DcRef": 1,
        "DealerUniqueId": payload["DealerId"],
        "OrderPDate": "1405/05/31",
        "OrderTypeUniqueId": order["OrderTypeUniqueId"],
        "PaymentTypeUniqueId": order["OrderPaymentTypeUniqueId"],
        "CustomerCallOrderUniqueId": order["UniqueId"],
        "ProductsMetaData": [{"ProductUniqueId": line["ProductUniqueId"], "Qty": qty}],
    }
    request = Request(
        f"{settings.ngt_api_base_url}/api/v2/ngt/price/productprice",
        data=json.dumps(body).encode("utf-8"),
        headers=_api_headers(settings),
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            result = json.loads(raw) if raw else []
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise PilotRejectedError(f"کنترل رسمی قیمت NGT رد کرد (HTTP {exc.code}): {raw[:1000]}") from exc
    except (URLError, TimeoutError) as exc:
        raise PilotSafetyError("نتیجه کنترل رسمی قیمت نامشخص است؛ ارسال متوقف شد") from exc
    items = result if isinstance(result, list) else result.get("data") or result.get("items") or []
    if not any(str(item.get("productUniqueId") or item.get("ProductUniqueId")).lower() == str(line["ProductUniqueId"]).lower() for item in items):
        raise PilotRejectedError("کنترل رسمی قیمت NGT برای کالای پایلوت قیمت معتبر برنگرداند")
    return {"status": 200, "items": len(items), "product_ref": summary["product"]["ref"]}


def _send(settings: Any, payload: dict[str, Any], device_setting_code: int) -> dict[str, Any]:
    if not settings.ngt_pilot_send_enabled:
        raise PilotSafetyError("فلگ موقت NGT_PILOT_SEND_ENABLED برای این اجرا فعال نشده است")
    query = urlencode({"deviceSettingCode": int(device_setting_code)})
    request = Request(
        f"{settings.ngt_api_base_url}/api/v2/ngt/tour/sync/RequestSaveTourData?{query}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=_api_headers(settings),
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            body = response.read().decode("utf-8", errors="replace")
            return {"status": int(response.status), "body": body[:2000]}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise PilotRejectedError(f"NGT HTTP {exc.code}: {body[:1000]}") from exc
    except (URLError, TimeoutError) as exc:
        raise PilotSafetyError("نتیجه ارسال نامشخص است؛ برای جلوگیری از تکرار، ارسال خودکار تکرار نمی‌شود") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    settings = get_settings()

    existing = _external_matches(settings)
    if existing:
        print(json.dumps({"status": "already_exists", "matches": existing}, ensure_ascii=False, indent=2, default=str))
        return
    state = _read_state()
    if state and state.get("phase") in {"sending", "accepted", "unknown", "verified"}:
        raise PilotSafetyError(f"وضعیت قبلی {state.get('phase')} است؛ ارسال دوباره متوقف شد")
    if state and state.get("payload"):
        payload = state["payload"]
        summary = state["summary"]
    else:
        payload, summary = _prepare(settings)
        state = {"phase": "prepared", "prepared_at": datetime.now(UTC_PLUS_0330).isoformat(), "summary": summary, "payload": payload}
        _write_state(state)

    try:
        price_preflight = _official_price_preflight(settings, payload, summary)
    except PilotRejectedError as exc:
        state["phase"] = "rejected"
        state["error"] = str(exc)
        state["failed_at"] = datetime.now(UTC_PLUS_0330).isoformat()
        _write_state(state)
        print(json.dumps({"status": "blocked_by_ngt_price", "error": str(exc), "summary": summary}, ensure_ascii=False, indent=2, default=str))
        return

    if not args.execute:
        print(json.dumps({"status": "dry_run_ready", "state_path": str(STATE_PATH), "price_preflight": price_preflight, "summary": summary}, ensure_ascii=False, indent=2, default=str))
        return

    state["phase"] = "sending"
    state["sending_at"] = datetime.now(UTC_PLUS_0330).isoformat()
    _write_state(state)
    try:
        response = _send(settings, payload, int(summary["device_setting_code"]))
    except PilotRejectedError as exc:
        state["phase"] = "rejected"
        state["error"] = str(exc)
        state["failed_at"] = datetime.now(UTC_PLUS_0330).isoformat()
        _write_state(state)
        raise
    except Exception as exc:
        state["phase"] = "unknown"
        state["error"] = str(exc)
        state["failed_at"] = datetime.now(UTC_PLUS_0330).isoformat()
        _write_state(state)
        raise
    state["phase"] = "accepted"
    state["accepted_at"] = datetime.now(UTC_PLUS_0330).isoformat()
    state["response"] = response
    _write_state(state)
    matches = _external_matches(settings)
    if matches:
        state["phase"] = "verified"
        state["verified_at"] = datetime.now(UTC_PLUS_0330).isoformat()
        state["matches"] = matches
        _write_state(state)
    print(json.dumps({"status": state["phase"], "response": response, "matches": matches, "summary": summary}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
