from __future__ import annotations

import json
import sys
from datetime import date
from uuid import uuid4

from app.config import get_settings
from app.ngt_previsit_service import _live_customer_credit_control, _normalise_evc, _post_evc


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    settings = get_settings()
    order_id = str(uuid4())
    requested = [{"product_id": "4014", "quantity": 12.0}]
    raw = _post_evc(
        settings,
        {
            "CustRef": "7494",
            "OrderTypeRef": 2,
            "SaleOfficeRef": 1,
            "OrderDate": "",
            "DealerRef": 22,
            "BuyTypeRef": 3,
            "DisType": 2,
            "PaymentUsanceRef": "401",
            "EvcType": 1,
            "RefId": 0,
            "PreSaleEvcDetails": [
                {
                    "GoodsRef": "4014",
                    "FreeReasonRef": None,
                    "TotalQty": 12.0,
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
        "7571d2c6-44ce-4b62-a45e-42ec8b1c670e",
    )
    normalised = _normalise_evc(raw, requested)
    credit_control = _live_customer_credit_control(
        settings,
        customer_id=7494,
        payment_id=401,
        dealer_ref=22,
        dc_ref=1,
        order_total=float(normalised["totals"]["net"]),
    )
    print(
        json.dumps(
            {
                "raw": raw,
                "normalised": normalised,
                "credit_control": credit_control,
                "creates_order": False,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
