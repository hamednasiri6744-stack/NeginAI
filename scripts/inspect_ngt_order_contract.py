from __future__ import annotations

import json
import os

from app.config import get_settings
from app.database import sql_connection


SELLER_REF = 22
CUSTOMER_REF = 7494
PRODUCT_REF = 4014
ORDER_TYPE_REF = 2
PAYMENT_REF = 401
STOCK_REF = 1


def rows(cursor, sql: str) -> list[dict[str, object]]:
    cursor.execute(sql)
    names = [str(item[0]) for item in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def main() -> None:
    settings = get_settings()
    with sql_connection(settings) as connection:
        cursor = connection.cursor()
        identifiers = rows(
            cursor,
            f"""
SELECT TOP 1 personnel.Id AS DealerUniqueId, personnel.BackOfficeId AS DealerRef,
       customer.Id AS CustomerUniqueId, customer.BackOfficeId AS CustomerRef,
       product.UniqueId AS ProductUniqueId, product.ID AS ProductRef,
       unit.UniqueId AS ProductUnitUniqueId, unit.ID AS ProductUnitRef,
       order_type.Id AS OrderTypeUniqueId, order_type.BackOfficeId AS OrderTypeRef,
       payment.Id AS PaymentTypeUniqueId, payment.BackOfficeId AS PaymentRef,
       stock.Id AS StockUniqueId, stock.BackOfficeId AS StockRef,
       device.DeviceSettingNo, device.SubSystemTypeUniqueId
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
WHERE TRY_CONVERT(int, personnel.BackOfficeId) = {SELLER_REF}
  AND ISNULL(personnel.IsRemoved, 0) = 0
  AND ISNULL(customer.IsRemoved, 0) = 0
ORDER BY device.LastUpdate DESC
""".strip(),
        )
        recent_headers = rows(
            cursor,
            f"""
SELECT TOP 5 header.Id, header.CustomerCallUniqueId, call.CustomerUniqueId,
       call.VisitStatusUniqueId, call.CallDate, call.StartTime, call.EndTime,
       call.Longitude, call.Latitude, header.SubSystemTypeUniqueId,
       header.OrderTypeUniqueId, header.OrderPaymentTypeUniqueId,
       header.InvoicePaymentTypeUniqueId,
       header.LocalPaperNo, header.DisType, header.SaleDate,
       header.SaleTypeUniqueId,
       header.DcRefSDS, header.SaleOfficeRefSDS, header.DealerRefSDS,
       header.BackOfficeOrderId, header.BackOfficeOrderNo,
       header.SendToConsoleDate, header.IsCanceled
FROM NGT.CustomerCallOrders AS header
INNER JOIN NGT.CustomerCalls AS call ON call.Id = header.CustomerCallUniqueId
WHERE TRY_CONVERT(int, header.DealerRefSDS) = {SELLER_REF}
  AND ISNULL(header.IsRemoved, 0) = 0
  AND ISNULL(call.IsRemoved, 0) = 0
ORDER BY header.LastUpdate DESC
""".strip(),
        )
        recent_lines = rows(
            cursor,
            f"""
SELECT TOP 5 line.Id, line.CustomerCallOrderUniqueId, line.ProductUniqueId,
       line.UnitPrice, line.PriceUniqueId, line.CPriceUniqueId, line.StockUniqueId,
       line.RequestAmount, line.RequestAdd1Amount,
       line.RequestAdd2Amount, line.RequestTaxAmount, line.RequestChargeAmount,
       line.RequestDis1Amount, line.RequestDis2Amount, line.RequestDis3Amount,
       line.RequestOtherDiscountAmount, line.RequestOtherAddAmount,
       line.PayDuration, line.RuleNo, line.IsRequestFreeItem, line.IsRequestPrizeItem
FROM NGT.CustomerCallOrderLines AS line
INNER JOIN NGT.CustomerCallOrders AS header ON header.Id = line.CustomerCallOrderUniqueId
WHERE TRY_CONVERT(int, header.DealerRefSDS) = {SELLER_REF}
  AND ISNULL(line.IsRemoved, 0) = 0
  AND ISNULL(header.IsRemoved, 0) = 0
ORDER BY line.LastUpdate DESC
""".strip(),
        )
        qty_tables = rows(
            cursor,
            """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = 'NGT'
  AND TABLE_NAME LIKE '%OrderLine%Qty%'
ORDER BY TABLE_NAME
""".strip(),
        )
        min_order_columns = rows(
            cursor,
            """
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE (COLUMN_NAME LIKE '%Min%Order%' OR COLUMN_NAME LIKE '%Order%Min%')
ORDER BY TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
""".strip(),
        )
        min_order_settings = rows(
            cursor,
            """
SELECT TOP 1 DcRef, MinOrderAmount, OrderRowLimitMin, OrderAsnLimit, OrderBedLimit
FROM GNR.tblServerConfigDC
WHERE DcRef = 1
""".strip(),
        )
        visit_status = rows(
            cursor,
            """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME LIKE '%VisitStatus%'
ORDER BY TABLE_SCHEMA, TABLE_NAME
""".strip(),
        )
        subsystem_tables = rows(
            cursor,
            """
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE (TABLE_NAME LIKE '%SubSystem%' OR COLUMN_NAME LIKE '%SubSystemType%')
  AND TABLE_SCHEMA IN ('NGT', 'GNR', 'dbo')
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
""".strip(),
        )
        recent_product_orders = rows(
            cursor,
            f"""
SELECT TOP 10 header.Id, header.DealerRefSDS, header.SubSystemTypeUniqueId,
       header.OrderTypeUniqueId, header.OrderPaymentTypeUniqueId,
       header.DisType, header.DcRefSDS, header.SaleOfficeRefSDS,
       header.BackOfficeOrderId, header.BackOfficeOrderNo,
       line.UnitPrice, line.PriceUniqueId, line.CPriceUniqueId,
       line.StockUniqueId, line.RequestAmount, line.LastUpdate
FROM NGT.CustomerCallOrderLines AS line
INNER JOIN NGT.CustomerCallOrders AS header ON header.Id = line.CustomerCallOrderUniqueId
WHERE line.ProductUniqueId = (
    SELECT TOP 1 UniqueId FROM GNR.tblGoods WHERE ID = {PRODUCT_REF}
)
  AND ISNULL(line.IsRemoved, 0) = 0
  AND ISNULL(header.IsRemoved, 0) = 0
ORDER BY line.LastUpdate DESC
""".strip(),
        )
        product_identity_columns = rows(
            cursor,
            """
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'NGT'
  AND TABLE_NAME IN ('Products', 'ProductPrices', 'ContractPrices')
ORDER BY TABLE_NAME, ORDINAL_POSITION
""".strip(),
        )
        product_identities = []
        contract_price_candidates = rows(
            cursor,
            f"""
SELECT TOP 50 Id, GoodsRef, MinQty, MaxQty, SalePrice,
       StartDate, EndDate, CustRef, CustCtgrRef, DealerCtgrRef,
       OrderTypeRef, BuyTypeRef, DCRef, UsanceDay, Priority,
       CPriceType, Code, UnitRef, SaleOfficeRef, IsRemoved, LastUpdate
FROM NGT.ContractPrices
WHERE TRY_CONVERT(int, GoodsRef) = {PRODUCT_REF}
ORDER BY IsRemoved, Priority, LastUpdate DESC
""".strip(),
        )
    if os.getenv("NGT_CONTRACT_SUMMARY_ONLY") == "1":
        print(json.dumps({
            "min_order_settings": min_order_settings,
            "visit_status_tables": visit_status,
            "subsystem_tables": subsystem_tables,
            "recent_product_orders": recent_product_orders,
            "product_identities": product_identities,
            "contract_price_candidates": contract_price_candidates,
        }, ensure_ascii=False, indent=2, default=str))
        return
    print(
        json.dumps(
            {
                "identifiers": identifiers,
                "recent_headers": recent_headers,
                "recent_lines": recent_lines,
                "qty_tables": qty_tables,
                "min_order_columns": min_order_columns,
                "min_order_settings": min_order_settings,
                "visit_status": visit_status,
                "subsystem_tables": subsystem_tables,
                "recent_product_orders": recent_product_orders,
                "product_identity_columns": product_identity_columns,
                "product_identities": product_identities,
                "contract_price_candidates": contract_price_candidates,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
