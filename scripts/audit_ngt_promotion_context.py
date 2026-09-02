from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import get_settings
from app.ngt_previsit_service import _candidate_promotion_rules, _rows


def compact(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if value not in (None, "", 0, False)
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discount-id", type=int, required=True)
    parser.add_argument("--customer-id", type=int, required=True)
    parser.add_argument("--dealer-id", type=int, required=True)
    parser.add_argument("--product-id", type=int, default=4040)
    parser.add_argument(
        "--section",
        choices=("all", "columns", "order", "modules", "customer-schema", "product-schema", "candidates", "rule"),
        default="all",
    )
    args = parser.parse_args()
    settings = get_settings()

    if args.section == "candidates":
        rules = _candidate_promotion_rules(settings, [args.product_id])
        discount_ids = ",".join(str(rule["rule_id"]) for rule in rules) or "0"
        condition_rows = _rows(
            settings,
            f"SELECT * FROM SLE.tblDiscountCondition WHERE DiscountRef IN ({discount_ids})",
        )
        customer_rows = _rows(
            settings,
            f"""
SELECT customer.BackOfficeId AS CustRef, customer.DCRef,
       category.BackOfficeId AS CustCtgrRef,
       activity.BackOfficeId AS CustActRef,
       level_type.BackOfficeId AS CustLevelRef,
       main_sub.MainTypeRef AS MainCustTypeRef,
       main_sub.SubTypeRef AS SubCustTypeRef,
       customer.StateId AS StateRef, customer.CountyId AS CountyRef,
       customer.CityId, customer.CityAreaSDS AS AreaRef,
       customer.SaleZoneRefSDS AS SaleZoneRef,
       sale_office.BackOfficeId AS SaleOfficeRef,
       customer.CustGroupName
FROM NGT.Customers AS customer
LEFT JOIN NGT.CustomerCategories AS category ON category.Id=customer.CustomerCategoryUniqueId
LEFT JOIN NGT.CustomerActivities AS activity ON activity.Id=customer.CustomerActivityUniqueId
LEFT JOIN NGT.CustomerLevels AS level_type ON level_type.Id=customer.CustomerLevelUniqueId
LEFT JOIN NGT.CustomerMainSubTypes AS main_sub
  ON main_sub.CustRef=TRY_CONVERT(int, customer.BackOfficeId) AND ISNULL(main_sub.IsRemoved,0)=0
LEFT JOIN NGT.SaleOffices AS sale_office ON sale_office.Id=customer.SaleOfficeUniqueId
WHERE TRY_CONVERT(int, customer.BackOfficeId)={args.customer_id}
""".strip(),
        )
        print(json.dumps({
            "rules": rules,
            "conditions": [compact(row) for row in condition_rows],
            "customer_context": [compact(row) for row in customer_rows],
        }, ensure_ascii=False, default=str, indent=2))
        return

    queries = {
        "condition": (
            "SELECT * FROM SLE.tblDiscountCondition "
            f"WHERE DiscountRef={args.discount_id}"
        ),
        "discount": (
            "SELECT * FROM SLE.tblDiscount "
            f"WHERE ID={args.discount_id}"
        ),
        "discount_goods": (
            "SELECT * FROM SLE.tblDiscountGoods "
            f"WHERE DiscountRef={args.discount_id} ORDER BY ID"
        ),
        "product": (
            "SELECT TOP 1 * FROM GNR.tblGoods "
            f"WHERE ID={args.product_id}"
        ),
        "customer": (
            "SELECT TOP 1 * FROM NGT.Customers "
            f"WHERE TRY_CONVERT(int, BackOfficeId)={args.customer_id}"
        ),
        "recent_orders": (
            "SELECT TOP 10 * FROM NGT.CustomerCallOrders "
            f"WHERE DealerRefSDS={args.dealer_id} "
            "AND ISNULL(IsRemoved,0)=0 ORDER BY LastUpdate DESC"
        ),
        "order_no_columns": (
            "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE COLUMN_NAME LIKE '%OrderNo%' "
            "ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION"
        ),
        "matching_order": (
            "SELECT TOP 10 * FROM SLE.tblOrderHdr "
            "WHERE ID=54237 OR OrderNo='54237' OR TOrderNo='54237' "
            "ORDER BY ID DESC"
        ),
        "matching_order_items": (
            "SELECT TOP 50 * FROM SLE.tblOrderItm WHERE HdrRef=326966 ORDER BY ID"
        ),
        "discount_modules": (
            "SELECT SCHEMA_NAME(obj.schema_id) AS SchemaName, obj.name AS ObjectName, obj.type_desc "
            "FROM sys.sql_modules AS module "
            "INNER JOIN sys.objects AS obj ON obj.object_id=module.object_id "
            "WHERE module.definition LIKE '%tblDiscountCondition%' "
            "ORDER BY SchemaName, ObjectName"
        ),
        "customer_dimension_tables": (
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA='NGT' AND TABLE_NAME LIKE '%Customer%' "
            "ORDER BY TABLE_NAME"
        ),
        "customer_dimension_columns": (
            "SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='NGT' AND TABLE_NAME IN "
            "('Customers','CustomerActivities','CustomerCategories','CustomerLevels','CustomerMainSubTypes') "
            "ORDER BY TABLE_NAME, ORDINAL_POSITION"
        ),
        "order_item_columns": (
            "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='SLE' AND TABLE_NAME='tblOrderItm' "
            "ORDER BY ORDINAL_POSITION"
        ),
        "product_group_tables": (
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_NAME LIKE '%Product%Group%' OR TABLE_NAME LIKE '%Goods%Type%' "
            "OR TABLE_NAME LIKE '%Goods%Group%' ORDER BY TABLE_SCHEMA, TABLE_NAME"
        ),
        "product_group_columns": (
            "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME LIKE '%Product%Group%' OR TABLE_NAME LIKE '%Goods%Type%' "
            "OR TABLE_NAME LIKE '%Goods%Group%' ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION"
        ),
    }
    section_keys = {
        "columns": ("order_no_columns", "order_item_columns"),
        "order": ("matching_order", "matching_order_items"),
        "modules": ("discount_modules",),
        "customer-schema": ("customer_dimension_tables", "customer_dimension_columns"),
        "product-schema": ("product_group_tables", "product_group_columns"),
        "rule": ("discount", "condition", "discount_goods", "product"),
    }
    selected = queries if args.section == "all" else {key: queries[key] for key in section_keys[args.section]}
    result = {key: [compact(row) for row in _rows(settings, query)] for key, query in selected.items()}
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
