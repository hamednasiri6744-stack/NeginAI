from __future__ import annotations

import json
import os
import re
from datetime import date
from typing import Any
from uuid import uuid4

from app.config import get_settings
from app.database import sql_connection
from app.ngt_previsit_service import (
    PrevisitError,
    _live_customer_credit_control,
    _normalise_evc,
    _post_evc,
    previsit_context,
)
from app.seller_workspace_service import seller_route_customers, seller_routes


USERNAME = "A.kamran"
QUANTITY = 12.0


def _normalise(value: Any) -> str:
    text = str(value or "").replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"[^0-9a-zA-Z؀-ۿ]+", "", text).casefold()


def _product_score(product: dict[str, Any]) -> tuple[int, float]:
    haystack = _normalise(" ".join(
        str(product.get(key) or "")
        for key in ("name", "brand", "description", "manufacturer")
    ))
    needles = ("خمیردندان", "ضدزرد", "میسویک")
    score = sum(1 for needle in needles if needle in haystack)
    return score, float(product.get("available_qty") or 0)


def _candidate_key(item: dict[str, Any]) -> tuple[int, int, float, float, str]:
    has_combined_credit = bool(item.get("init_credit") and item.get("init_debit"))
    available = float(item.get("remain_credit") or 0) + float(item.get("remain_debit") or 0)
    return (
        0 if int(item.get("return_cheque_count") or 0) == 0 else 1,
        0 if has_combined_credit and available >= 50_000_000 else 1,
        available if available >= 50_000_000 else float("inf"),
        float(item.get("open_invoice_remaining") or 0),
        str(item.get("store_name") or item.get("name") or ""),
    )


def _attach_credit_profiles(settings: Any, candidates: list[dict[str, Any]]) -> None:
    ids = sorted({int(item["id"]) for item in candidates if str(item.get("id") or "").isdigit()})
    if not ids:
        return
    sql = f"""
SELECT TRY_CONVERT(int, BackOfficeId) AS CustomerId,
       InitCredit, RemainCredit, InitDebit, RemainDebit,
       ReturnChequeCount, ReturnChequeAmount
FROM NGT.Customers
WHERE TRY_CONVERT(int, BackOfficeId) IN ({','.join(str(item) for item in ids)})
  AND ISNULL(IsRemoved, 0) = 0
""".strip()
    with sql_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute(sql)
        columns = [str(item[0]) for item in cursor.description]
        profiles = {int(row[0]): dict(zip(columns, row)) for row in cursor.fetchall()}
    for candidate in candidates:
        profile = profiles.get(int(candidate["id"])) or {}
        candidate.update(
            {
                "init_credit": float(profile.get("InitCredit") or 0),
                "remain_credit": float(profile.get("RemainCredit") or 0),
                "init_debit": float(profile.get("InitDebit") or 0),
                "remain_debit": float(profile.get("RemainDebit") or 0),
                "return_cheque_count": int(profile.get("ReturnChequeCount") or 0),
                "return_cheque_amount": float(profile.get("ReturnChequeAmount") or 0),
            }
        )


def main() -> None:
    settings = get_settings()
    routes_payload = seller_routes(settings, USERNAME)
    candidates: list[dict[str, Any]] = []
    for route in routes_payload.get("routes") or []:
        payload = seller_route_customers(settings, USERNAME, str(route["id"]))
        for customer in payload.get("customers") or []:
            candidates.append({**customer, "route_id": str(route["id"]), "route_title": route["title"]})
    if not candidates:
        raise RuntimeError("هیچ مشتری فعالی در مسیرهای عارف کامران پیدا نشد.")

    _attach_credit_profiles(settings, candidates)
    candidates.sort(key=_candidate_key)
    credit_summary = {
        "customers_with_any_initialized_balance": sum(
            1 for item in candidates if item.get("init_credit") or item.get("init_debit")
        ),
        "customers_with_both_initialized_balances": sum(
            1 for item in candidates if item.get("init_credit") and item.get("init_debit")
        ),
        "customers_with_combined_remaining_at_least_50m": sum(
            1
            for item in candidates
            if item.get("init_credit")
            and item.get("init_debit")
            and float(item.get("remain_credit") or 0) + float(item.get("remain_debit") or 0) >= 50_000_000
        ),
        "customers_with_returned_cheque": sum(
            1 for item in candidates if int(item.get("return_cheque_count") or 0) > 0
        ),
    }
    if os.getenv("NGT_PILOT_CREDIT_SUMMARY_ONLY") == "1":
        print(json.dumps({"seller": routes_payload.get("seller"), "customer_count": len(candidates), "credit_summary": credit_summary}, ensure_ascii=False, indent=2))
        return
    seed = candidates[0]
    context = previsit_context(
        settings,
        USERNAME,
        seed["route_id"],
        str(seed["id"]),
        limit=1000,
    )
    products = sorted(context.get("products") or [], key=_product_score, reverse=True)
    product = products[0] if products else None
    if not product or _product_score(product)[0] < 3:
        near = [
            {key: item.get(key) for key in ("id", "code", "name", "brand", "stock_name", "available_qty")}
            for item in products[:10]
            if "میسویک" in _normalise(" ".join(str(item.get(key) or "") for key in ("name", "brand")))
        ]
        print(json.dumps({"seller": routes_payload.get("seller"), "near_products": near}, ensure_ascii=False, indent=2))
        raise RuntimeError("کالای دقیق خمیردندان ضد زردی میسویک پیدا نشد.")
    if float(product.get("available_qty") or 0) < QUANTITY:
        raise RuntimeError("موجودی انبار مجاز برای ۱۲ عدد کافی نیست.")

    order_types = context.get("order_types") or []
    payments = sorted(
        context.get("payment_types") or [],
        key=lambda item: (0 if item.get("check_credit") or item.get("check_debit") else 1, bool(item.get("is_cash"))),
    )
    preview_candidates: list[dict[str, Any]] = []
    for customer in candidates[:12]:
        selected: dict[str, Any] | None = None
        failures: list[str] = []
        for order_type in order_types:
            for payment in payments:
                try:
                    order_id = str(uuid4())
                    requested = [{"product_id": str(product["id"]), "quantity": QUANTITY}]
                    raw = _post_evc(
                        settings,
                        {
                            "CustRef": str(customer["id"]),
                            "OrderTypeRef": int(order_type["id"]),
                            "SaleOfficeRef": int(context["_bridge"]["sale_office_ref"]),
                            "OrderDate": "",
                            "DealerRef": int(context["seller"]["personnel_id"]),
                            "BuyTypeRef": int(payment["buy_type_ref"]),
                            "DisType": 2,
                            "PaymentUsanceRef": str(payment["id"]),
                            "EvcType": 1,
                            "RefId": 0,
                            "PreSaleEvcDetails": [
                                {
                                    "GoodsRef": str(product["id"]),
                                    "FreeReasonRef": None,
                                    "TotalQty": QUANTITY,
                                    "ReferenceNo": None,
                                    "SaleNo": None,
                                    "OrderDate": date.today().strftime("%Y/%m/%d"),
                                    "ReturnReasonId": None,
                                    "OrderLineId": str(uuid4()),
                                    "OrderId": order_id,
                                }
                            ],
                            "PreSaleEvcItemDetails": [],
                            "SelIds": None,
                        },
                        context["_bridge"]["subsystem_type_unique_id"],
                    )
                    preview = _normalise_evc(raw, requested)
                    preview["credit_control"] = _live_customer_credit_control(
                        settings,
                        customer_id=customer["id"],
                        payment_id=payment["id"],
                        dealer_ref=int(context["seller"]["personnel_id"]),
                        dc_ref=int(context["_bridge"]["dc_ref"]),
                        order_total=float(preview["totals"]["net"]),
                    )
                    preview["ok"] = bool(
                        preview.get("ok")
                        and preview["credit_control"]["allowed"]
                        and float(preview["totals"]["net"] or 0) >= 1_000_000
                    )
                except PrevisitError as exc:
                    failures.append(f"{order_type['name']} / {payment['name']}: {exc}")
                    continue
                summary = {
                    "order_type": order_type,
                    "payment_type": payment,
                    "ok": bool(preview.get("ok")),
                    "message": preview.get("message"),
                    "totals": preview.get("totals"),
                    "credit_control": preview.get("credit_control"),
                    "restrictions": preview.get("restrictions"),
                    "prizes": preview.get("prizes"),
                }
                if summary["ok"]:
                    selected = summary
                    break
                failures.append(
                    f"{order_type['name']} / {payment['name']}: "
                    f"{preview.get('message') or preview.get('credit_control', {}).get('message') or 'رد شد'}"
                )
            if selected:
                break
        preview_candidates.append(
            {
                "customer": {
                    key: customer.get(key)
                    for key in (
                        "id", "code", "name", "store_name", "route_id", "route_title",
                        "cardex_balance", "open_invoice_remaining", "open_invoice_count",
                        "init_credit", "remain_credit", "init_debit", "remain_debit",
                        "return_cheque_count", "return_cheque_amount",
                    )
                },
                "selected": selected,
                "failures": failures[:5],
            }
        )
        if selected and selected.get("credit_control", {}).get("mode") != "none":
            break

    print(
        json.dumps(
            {
                "seller": routes_payload.get("seller"),
                "route_count": len(routes_payload.get("routes") or []),
                "customer_count": len(candidates),
                "credit_summary": credit_summary,
                "product": {
                    key: product.get(key)
                    for key in (
                        "id", "unique_id", "code", "name", "brand", "stock_name", "stock_ref",
                        "unit", "available_qty", "min_order_qty", "max_order_qty", "indicative_price",
                    )
                },
                "quantity": QUANTITY,
                "allowed_order_types": order_types,
                "allowed_payment_types": payments,
                "preview_candidates": preview_candidates,
                "creates_order": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
