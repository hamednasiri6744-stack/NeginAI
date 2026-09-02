from __future__ import annotations

import json
import gzip
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from app.config import get_settings
from app.database import sql_connection
from app.ngt_previsit_service import _token


CUSTOMER_ID = "16640aa0-5502-4b14-aa5a-dfd4aee1e60d"
DEALER_ID = "73e773b9-7839-41c3-8d86-d02b4d358f1a"
PRODUCT_ID = "96522c6d-06da-446d-8339-4edf496d54ff"
ORDER_TYPE_ID = "951d530d-3aa1-446f-90bc-78561df45a3d"
PAYMENT_TYPE_ID = "f545f385-63e4-4f10-9428-ec3452187898"


def _headers(settings):
    result = {"Accept": "application/json", "Content-Type": "application/json"}
    token = _token(settings)
    if token:
        result["Authorization"] = f"Bearer {token}"
    scope = [str(UUID(value.strip())) for value in settings.ngt_api_scope.split(",")]
    result.update(dict(zip(("OwnerKey", "DataOwnerKey", "DataOwnerCenterKey"), scope)))
    return result


def _request(settings, path: str, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{settings.ngt_api_base_url}{path}",
        data=data,
        headers=_headers(settings),
        method="GET" if payload is None else "POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding", "").lower() == "gzip":
                raw = gzip.decompress(raw)
            body = raw.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body) if body else None
            except json.JSONDecodeError:
                parsed = body[:5000]
            return {"status": response.status, "body": parsed}
    except HTTPError as exc:
        return {
            "status": exc.code,
            "body": exc.read().decode("utf-8", errors="replace")[:2000],
        }


def main() -> None:
    settings = get_settings()
    with sql_connection(settings) as connection:
        cursor = connection.cursor()
        cursor.execute("""
SELECT 'order' AS Kind, TRY_CONVERT(varchar(20), BackOfficeId) AS BackOfficeRef,
       CONVERT(varchar(36), Id) AS UniqueId, OrderTypeName AS Title
FROM NGT.OrderTypes
WHERE TRY_CONVERT(int, BackOfficeId) IN (2, 3, 12) AND ISNULL(IsRemoved, 0) = 0
UNION ALL
SELECT 'payment', TRY_CONVERT(varchar(20), BackOfficeId),
       CONVERT(varchar(36), Id), PaymentTypeOrderName
FROM NGT.PaymentTypeOrders
WHERE TRY_CONVERT(int, BackOfficeId) IN (384, 401, 402, 409, 7) AND ISNULL(IsRemoved, 0) = 0
ORDER BY Kind, BackOfficeRef
""".strip())
        names = [str(item[0]) for item in cursor.description]
        mappings = [dict(zip(names, row)) for row in cursor.fetchall()]
    order_types = [item for item in mappings if item["Kind"] == "order"]
    payments = [item for item in mappings if item["Kind"] == "payment"]
    price_results = []
    for order_type in order_types:
        for payment in payments:
            price_results.append({
                "order": order_type,
                "payment": payment,
                "result": _request(
                    settings,
                    "/api/v2/ngt/price/productprice",
                    {
                        "CustomerUniqueId": CUSTOMER_ID,
                        "DcRef": 1,
                        "DealerUniqueId": DEALER_ID,
                        "OrderPDate": "1405/05/31",
                        "OrderTypeUniqueId": order_type["UniqueId"],
                        "PaymentTypeUniqueId": payment["UniqueId"],
                        "CustomerCallOrderUniqueId": str(uuid4()),
                        "ProductsMetaData": [{"ProductUniqueId": PRODUCT_ID, "Qty": 12}],
                    },
                ),
            })
    result = {
        "product_by_gnr_unique_id": _request(settings, f"/api/v2/ngt/product/{PRODUCT_ID}"),
        "product_search": _request(settings, "/api/v2/ngt/product/SearchProductList?searchText=364241208"),
        "mappings": mappings,
        "price_results": price_results,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
